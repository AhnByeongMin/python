"""
일일 매출 현황 비즈니스 로직 - 성능 최적화 버전

이 모듈은 일일 매출 현황을 처리하고 분석하는 비즈니스 로직을 포함합니다.
대용량 데이터 처리를 위한 최적화 기법이 적용되었습니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
import re
import xlsxwriter
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union, Tuple
import gc  # 가비지 컬렉션 명시적 제어
import functools  # 캐싱 데코레이터 사용
import time  # 성능 측정

# utils.py에서 필요한 함수 가져오기
from utils.utils import format_time, peek_file_content

# 캐싱 데코레이터 정의
def cache_with_timeout(seconds=3600):
    """
    함수 결과를 지정된 시간(초) 동안 캐싱하는 데코레이터
    """
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            
            # 캐시에 있고 만료되지 않았으면 캐시된 값 반환
            if key in cache and now - cache[key]["time"] < seconds:
                return cache[key]["result"]
            
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 결과 캐싱
            cache[key] = {"result": result, "time": now}
            
            # 캐시 크기 제한 (최대 20개 항목)
            if len(cache) > 20:
                oldest_key = min(cache.keys(), key=lambda k: cache[k]["time"])
                del cache[oldest_key]
                
            return result
        return wrapper
    return decorator

def process_approval_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    승인매출 엑셀 파일을 처리하는 함수 - 성능 최적화
    
    Args:
        file: 업로드된 승인매출 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    start_time = time.time()
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 엑셀 파일 읽기 - 필요한 컬럼만 지정하여 로드
        # 메모리 사용량 감소를 위해 dtype 명시적 지정
        dtypes = {
            "월 렌탈 금액": "float32",
            "약정 기간 값": "float32", 
            "총 패키지 할인 회차": "float32",
            "판매 금액": "float32", 
            "선납 렌탈 금액": "float32"
        }
        
        # 먼저 열 이름만 확인 (메모리 효율성)
        df_headers = pd.read_excel(file, nrows=0)
        file.seek(0)
        
        # 필요한 컬럼 확인 - 유사한 이름 미리 매핑
        column_mapping = {}
        required_columns = [
            "주문 일자", "판매인입경로", "일반회차 캠페인", "대분류", 
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        # 유사한 컬럼명 목록
        similar_cols_map = {
            "주문 일자": ["주문일자", "주문날짜", "계약일자", "승인일자"],
            "판매인입경로": ["판매 인입경로", "인입경로", "영업채널", "영업 채널"],
            "일반회차 캠페인": ["캠페인", "일반회차캠페인", "회차", "회차 캠페인"],
            "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"],
            "월 렌탈 금액": ["월렌탈금액", "렌탈 금액", "렌탈금액", "월 렌탈료"],
            "약정 기간 값": ["약정기간값", "약정 기간", "약정개월", "약정 개월"],
            "총 패키지 할인 회차": ["총패키지할인회차", "패키지 할인", "할인 회차", "패키지할인회차"],
            "판매 금액": ["판매금액", "매출 금액", "매출금액"],
            "선납 렌탈 금액": ["선납렌탈금액", "선납금액", "선납 금액"]
        }
        
        # 효율적인 컬럼 매핑 (미리 해결)
        for col in df_headers.columns:
            col_str = str(col).lower()
            for req_col, similar_names in similar_cols_map.items():
                if req_col.lower() in col_str or any(similar.lower() in col_str for similar in similar_names):
                    column_mapping[col] = req_col
                    break
        
        # 이미 있는 컬럼은 제외 (중복 매핑 방지)
        for req_col in required_columns:
            if req_col in df_headers.columns:
                # 이미 정확한 이름이 있으면 매핑에서 제거
                keys_to_remove = []
                for k, v in column_mapping.items():
                    if v == req_col:
                        keys_to_remove.append(k)
                
                for k in keys_to_remove:
                    del column_mapping[k]
        
        # 필요한 컬럼 또는 유사 이름의 컬럼만 로드 
        usecols = list(set(required_columns) | set(column_mapping.keys()))
        
        # 날짜 컬럼만 parse_dates로 지정 (모든 컬럼 변환 방지)
        date_cols = ["주문 일자"]
        if "주문 일자" not in df_headers.columns and "주문 일자" in column_mapping.values():
            # 매핑된 원래 컬럼명 찾기
            for k, v in column_mapping.items():
                if v == "주문 일자":
                    date_cols = [k]
                    break
        
        # 실제 엑셀 파일 로드 - 필요한 컬럼만
        df = pd.read_excel(
            file, 
            parse_dates=date_cols,
            usecols=lambda x: x in usecols if x in df_headers.columns else False,
            dtype={col: dtypes.get(col, "object") for col in usecols if col in dtypes}
        )
        
        # 컬럼명 변경
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # 필요한 컬럼 확인 재검사
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"승인매출 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}"
        
        # VAT 세율 설정 - 1.1%
        vat_rate = 0.011
        
        # 숫자형 변환 - 이미 dtype 지정했으므로 필요한 경우만 변환
        numeric_columns = [
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 총 패키지 할인 회차 데이터 정제 - 벡터화 연산으로 최적화
        # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
        zero_replacement_mask = df['총 패키지 할인 회차'].isin([39, 59, 60])
        df.loc[zero_replacement_mask, '총 패키지 할인 회차'] = 0
        
        # 일시불 판매 추가 할인 금액 컬럼이 있는지 확인
        has_discount_column = '일시불 판매 추가 할인 금액' in df.columns
        
        # 매출금액 계산 공식 - 벡터화 연산
        if has_discount_column:
            df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                          df['판매 금액'] - df['일시불 판매 추가 할인 금액'] + df['선납 렌탈 금액'])
        else:
            df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                          df['판매 금액'] + df['선납 렌탈 금액'])
        
        # VAT 제외 매출금액 계산 - 벡터화 연산
        df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
        
        # 처리 시간 기록
        processing_time = time.time() - start_time
        print(f"승인매출 파일 처리 시간: {processing_time:.2f}초")
        
        return df, None
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"승인매출 파일 처리 오류 (소요시간: {processing_time:.2f}초): {str(e)}")
        return None, f"승인매출 파일 처리 중 오류가 발생했습니다: {str(e)}"

def process_installation_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    설치매출 엑셀 파일을 처리하는 함수 - 성능 최적화
    
    Args:
        file: 업로드된 설치매출 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    start_time = time.time()
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 먼저 열 이름만 확인 (메모리 효율성)
        df_headers = pd.read_excel(file, nrows=0)
        file.seek(0)
        
        # 날짜 컬럼 추정 (여러 가능한 이름)
        date_column_candidates = [
            "설치 일자", "설치일자", "주문 일자", "주문일자", 
            "계약 일자", "계약일자", "완료 일자", "완료일자"
        ]
        
        date_column = None
        date_columns = []
        for col in df_headers.columns:
            col_str = str(col).lower()
            if any(candidate.lower() in col_str for candidate in date_column_candidates):
                date_column = col
                date_columns.append(col)
                break
        
        if date_column is None:
            # 날짜 포맷이 포함된 컬럼명 찾기 시도
            for col in df_headers.columns:
                col_str = str(col).lower()
                if "일자" in col_str or "날짜" in col_str or "date" in col_str:
                    date_column = col
                    date_columns.append(col)
                    break
        
        # 필요한 컬럼 확인 및 매핑
        required_columns = [
            "판매인입경로", "일반회차 캠페인", "대분류", 
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        # 유사한 컬럼명 매핑 테이블
        similar_cols_map = {
            "판매인입경로": ["판매 인입경로", "인입경로", "영업채널", "영업 채널"],
            "일반회차 캠페인": ["캠페인", "일반회차캠페인", "회차", "회차 캠페인"],
            "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"],
            "월 렌탈 금액": ["월렌탈금액", "렌탈 금액", "렌탈금액", "월 렌탈료"],
            "약정 기간 값": ["약정기간값", "약정 기간", "약정개월", "약정 개월"],
            "총 패키지 할인 회차": ["총패키지할인회차", "패키지 할인", "할인 회차", "패키지할인회차"],
            "판매 금액": ["판매금액", "매출 금액", "매출금액"],
            "선납 렌탈 금액": ["선납렌탈금액", "선납금액", "선납 금액"]
        }
        
        # 컬럼명 매핑 생성
        column_mapping = {}
        for col in df_headers.columns:
            col_str = str(col).lower()
            for req_col, similar_names in similar_cols_map.items():
                if req_col.lower() in col_str or any(similar.lower() in col_str for similar in similar_names):
                    column_mapping[col] = req_col
                    break
        
        # 이미 있는 컬럼은 제외 (중복 매핑 방지)
        for req_col in required_columns:
            if req_col in df_headers.columns:
                # 이미 정확한 이름이 있으면 매핑에서 제거
                keys_to_remove = []
                for k, v in column_mapping.items():
                    if v == req_col:
                        keys_to_remove.append(k)
                
                for k in keys_to_remove:
                    del column_mapping[k]

        # 필요한 컬럼 또는 유사 이름의 컬럼만 로드 
        usecols = list(set(required_columns) | set(column_mapping.keys()) | set(date_columns))
        
        # 데이터타입 설정
        dtypes = {
            "월 렌탈 금액": "float32",
            "약정 기간 값": "float32", 
            "총 패키지 할인 회차": "float32",
            "판매 금액": "float32", 
            "선납 렌탈 금액": "float32"
        }
        
        # 실제 엑셀 파일 로드 - 필요한 컬럼만
        df = pd.read_excel(
            file, 
            parse_dates=date_columns,
            usecols=lambda x: x in usecols if x in df_headers.columns else False,
            dtype={col: dtypes.get(col, "object") for col in usecols if col in dtypes}
        )
        
        # 컬럼명 변경
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # 필요한 컬럼 확인 재검사
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"설치매출 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}"
        
        # 날짜 컬럼 이름을 "주문 일자"로 표준화
        if date_column and date_column != "주문 일자":
            df["주문 일자"] = df[date_column]
        
        # VAT 세율 설정 - 1.1%
        vat_rate = 0.011
        
        # 숫자형 변환 - 이미 dtype 지정했으므로 필요한 경우만 변환
        numeric_columns = [
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        for col in numeric_columns:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 총 패키지 할인 회차 데이터 정제 - 벡터화 연산으로 최적화
        zero_replacement_mask = df['총 패키지 할인 회차'].isin([39, 59, 60]) 
        df.loc[zero_replacement_mask, '총 패키지 할인 회차'] = 0
        
        # 일시불 판매 추가 할인 금액 컬럼이 있는지 확인
        has_discount_column = '일시불 판매 추가 할인 금액' in df.columns
        
        # 매출금액 계산 공식 - 벡터화 연산
        if has_discount_column:
            df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                          df['판매 금액'] - df['일시불 판매 추가 할인 금액'] + df['선납 렌탈 금액'])
        else:
            df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                          df['판매 금액'] + df['선납 렌탈 금액'])
        
        # VAT 제외 매출금액 계산 - 벡터화 연산
        df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
        
        # 처리 시간 기록
        processing_time = time.time() - start_time
        print(f"설치매출 파일 처리 시간: {processing_time:.2f}초")
        
        return df, None
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"설치매출 파일 처리 오류 (소요시간: {processing_time:.2f}초): {str(e)}")
        return None, f"설치매출 파일 처리 중 오류가 발생했습니다: {str(e)}"

# 효율적인 데이터 분석을 위한 캐싱 적용
@cache_with_timeout(seconds=600)  # 10분 캐시
def analyze_sales_data(
    approval_df: pd.DataFrame, 
    installation_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    승인매출과 설치매출 데이터를 분석하는 함수 - 성능 최적화
    
    Args:
        approval_df: 승인매출 데이터프레임
        installation_df: 설치매출 데이터프레임 (선택사항)
        
    Returns:
        Dict[str, Any]: 분석 결과를 담은 딕셔너리
    """
    start_time = time.time()
    try:
        # 결과 딕셔너리 초기화
        results = {}
        
        # 데이터 검증
        if approval_df is None or approval_df.empty:
            return {"error": "승인매출 데이터가 비어 있습니다."}
        
        # 불필요한 컬럼 제거로 메모리 사용량 감소
        analysis_cols = [
            "주문 일자", "판매인입경로", "일반회차 캠페인", 
            "대분류", "매출금액(VAT제외)"
        ]
        
        approval_df_slim = approval_df[
            [col for col in analysis_cols if col in approval_df.columns]
        ].copy()
        
        # 최신 날짜 찾기 (주문 일자 필드가 있는 경우)
        latest_date = None
        if '주문 일자' in approval_df_slim.columns:
            try:
                # 날짜 열이 이미 datetime 형식인지 확인
                if not pd.api.types.is_datetime64_any_dtype(approval_df_slim['주문 일자']):
                    approval_df_slim['주문 일자'] = pd.to_datetime(approval_df_slim['주문 일자'], errors='coerce')
                
                # 최신 날짜 추출 (NaT 제외) - 더 빠른 연산
                valid_dates = approval_df_slim['주문 일자'].dropna()
                if not valid_dates.empty:
                    latest_date_obj = valid_dates.max()
                    # 날짜 포맷팅 (예: "3월25일")
                    latest_date = latest_date_obj.strftime("%m월%d일")
                    
                    # 날짜 객체도 저장 (필터링용)
                    latest_date_for_filter = latest_date_obj
            except Exception as e:
                print(f"날짜 처리 중 오류: {str(e)}")
                return {"error": f"날짜 처리 중 오류가 발생했습니다: {str(e)}"}
        
        if latest_date is None:
            latest_date = "최근 날짜"
            latest_date_for_filter = None
        
        # 1. 누적승인실적 분석
        cumulative_approval = analyze_approval_data_by_product(approval_df_slim)
        results["cumulative_approval"] = cumulative_approval
        
        # 2. 최신 날짜 기준 승인실적 분석
        daily_approval = pd.DataFrame()
        if latest_date_for_filter is not None:
            # 해당 날짜의 데이터만 필터링 - 벡터화 연산
            daily_df = approval_df_slim[
                approval_df_slim['주문 일자'].dt.date == latest_date_for_filter.date()
            ].copy()
            
            if not daily_df.empty:
                daily_approval = analyze_approval_data_by_product(daily_df)
                # 중간 데이터 명시적 삭제
                del daily_df
        
        results["daily_approval"] = daily_approval
        results["latest_date"] = latest_date
        
        # 3. 누적설치실적 분석 (설치매출 데이터가 있는 경우)
        cumulative_installation = None
        if installation_df is not None and not installation_df.empty:
            # 불필요한 컬럼 제거
            installation_df_slim = installation_df[
                [col for col in analysis_cols if col in installation_df.columns]
            ].copy()
            
            cumulative_installation = analyze_approval_data_by_product(installation_df_slim)
            # 중간 데이터 명시적 삭제
            del installation_df_slim
        
        results["cumulative_installation"] = cumulative_installation
        
        # 중간 데이터 명시적 삭제
        del approval_df_slim
        gc.collect()  # 메모리 정리 요청
        
        # 처리 시간 기록
        processing_time = time.time() - start_time
        print(f"매출 데이터 분석 시간: {processing_time:.2f}초")
        
        return results
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"매출 데이터 분석 오류 (소요시간: {processing_time:.2f}초): {str(e)}")
        return {"error": f"데이터 분석 중 오류가 발생했습니다: {str(e)}"}

# 성능 최적화 버전의 일별 승인 분석 함수
@cache_with_timeout(seconds=600)  # 10분 캐시
def analyze_daily_approval_by_date(approval_df: pd.DataFrame, selected_date: date) -> pd.DataFrame:
    """
    선택한 날짜에 대한 승인매출 데이터를 분석하는 함수 - 성능 최적화
    
    Args:
        approval_df: 승인매출 데이터프레임
        selected_date: 선택한 날짜 (datetime.date 객체)
        
    Returns:
        pd.DataFrame: 선택한 날짜에 대한 분석 결과 데이터프레임
    """
    start_time = time.time()
    try:
        # 데이터 검증
        if approval_df is None or approval_df.empty:
            return pd.DataFrame()  # 빈 데이터프레임 반환
        
        # 주문 일자 필드가 있는지 확인
        if '주문 일자' not in approval_df.columns:
            return pd.DataFrame()
        
        # 불필요한 컬럼 제거로 메모리 사용량 감소
        analysis_cols = [
            "주문 일자", "판매인입경로", "일반회차 캠페인", 
            "대분류", "매출금액(VAT제외)"
        ]
        
        slim_df = approval_df[
            [col for col in analysis_cols if col in approval_df.columns]
        ].copy()
        
        # datetime 형식으로 변환 (이미 변환되어 있을 수 있음)
        if not pd.api.types.is_datetime64_any_dtype(slim_df['주문 일자']):
            slim_df['주문 일자'] = pd.to_datetime(slim_df['주문 일자'], errors='coerce')
        
        # 선택한 날짜의 데이터만 필터링 - 벡터화 연산
        daily_df = slim_df[slim_df['주문 일자'].dt.date == selected_date].copy()
        
        # 중간 데이터 삭제
        del slim_df
        
        if daily_df.empty:
            return pd.DataFrame()  # 빈 데이터프레임 반환
        
        # 해당 날짜의 데이터 분석
        daily_approval = analyze_approval_data_by_product(daily_df)
        
        # 중간 데이터 삭제
        del daily_df
        gc.collect()  # 메모리 정리 요청
        
        # 처리 시간 기록
        processing_time = time.time() - start_time
        print(f"일별 승인실적 분석 시간: {processing_time:.2f}초")
        
        return daily_approval
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"일별 승인실적 분석 오류 (소요시간: {processing_time:.2f}초): {str(e)}")
        return pd.DataFrame()  # 오류 발생 시 빈 데이터프레임 반환

def analyze_approval_data_by_product(df: pd.DataFrame) -> pd.DataFrame:
    """
    제품별로 승인매출 데이터를 분석하는 함수 (요구된 표 형식에 맞춤) - 성능 최적화
    
    Args:
        df: 승인매출 데이터프레임
        
    Returns:
        pd.DataFrame: 분석 결과 데이터프레임
    """
    start_time = time.time()
    
    if df.empty:
        # 빈 결과 반환 - 메모리 효율적 생성
        return pd.DataFrame({
            "제품": ["안마의자", "라클라우드", "정수기", "총합계"],
            "총승인(본사/연계)_건수": [0, 0, 0, 0],
            "총승인(본사/연계)_매출액": [0, 0, 0, 0],
            "본사직접승인_건수": [0, 0, 0, 0],
            "본사직접승인_매출액": [0, 0, 0, 0],
            "연계승인_건수": [0, 0, 0, 0],
            "연계승인_매출액": [0, 0, 0, 0],
            "온라인_건수": [0, 0, 0, 0],
            "온라인_매출액": [0, 0, 0, 0]
        })
    
    # 제품 종류 정의
    products = ["안마의자", "라클라우드", "정수기"]
    
    # 모든 필터링 마스크를 한 번에 생성하여 재사용 (성능 향상)
    # Series 생성
    campaigns = df['일반회차 캠페인'].astype(str)
    inroutes = df['판매인입경로'].astype(str)
    categories = df['대분류'].astype(str)
    
    # 1. 본사/연계합계 마스크 생성: "CB-"로 시작하는 캠페인 제외
    not_cb_mask = ~campaigns.str.startswith('CB-')
    
    # 캠페인 마스크: "V-", "C-"로 시작하거나 "캠", "정규", "분배"를 포함
    v_or_c_mask = campaigns.str.startswith('V-') | campaigns.str.startswith('C-')
    kam_mask = campaigns.str.contains('캠')
    reguler_mask = campaigns.str.contains('정규')
    distrib_mask = campaigns.str.contains('분배')
    campaign_mask = v_or_c_mask | kam_mask | reguler_mask | distrib_mask
    
    # 본사/연계 전체 마스크 - 더 효율적인 마스크 재사용
    hq_link_mask = not_cb_mask & campaign_mask
    
    # 2. 본사 마스크: "CRM"을 포함하는 판매인입경로
    hq_mask = inroutes.str.contains('CRM')
    
    # 3. 연계 마스크: "CRM"을 포함하지 않는 판매인입경로
    link_mask = ~inroutes.str.contains('CRM')
    
    # 4. 온라인 마스크: "CB-"로 시작하는 캠페인
    online_mask = campaigns.str.startswith('CB-')
    
    # 결과를 위한 데이터 구조
    result_data = []
    
    # 각 제품별 집계 - 마스크를 재사용하여 효율성 증가
    for product in products:
        product_mask = categories.str.contains(product)
        
        # 제품별 결과 딕셔너리 직접 생성하여 할당 (더 빠름)
        product_row = {
            "제품": product,
            # 1. 총승인(본사/연계) - 마스크 결합으로 빠른 필터링
            "총승인(본사/연계)_건수": np.sum(hq_link_mask & product_mask),
            "총승인(본사/연계)_매출액": df.loc[hq_link_mask & product_mask, '매출금액(VAT제외)'].sum(),
            
            # 2. 본사직접승인 - 마스크 결합으로 빠른 필터링
            "본사직접승인_건수": np.sum(hq_link_mask & hq_mask & product_mask),
            "본사직접승인_매출액": df.loc[hq_link_mask & hq_mask & product_mask, '매출금액(VAT제외)'].sum(),
            
            # 3. 연계승인 - 마스크 결합으로 빠른 필터링
            "연계승인_건수": np.sum(hq_link_mask & link_mask & product_mask),
            "연계승인_매출액": df.loc[hq_link_mask & link_mask & product_mask, '매출금액(VAT제외)'].sum(),
            
            # 4. 온라인 - 마스크 결합으로 빠른 필터링
            "온라인_건수": np.sum(online_mask & product_mask),
            "온라인_매출액": df.loc[online_mask & product_mask, '매출금액(VAT제외)'].sum()
        }
        
        result_data.append(product_row)
    
    # 총합계 행 추가 - numpy 합산 사용으로 속도 향상
    total_row = {
        "제품": "총합계",
        "총승인(본사/연계)_건수": sum(row["총승인(본사/연계)_건수"] for row in result_data),
        "총승인(본사/연계)_매출액": sum(row["총승인(본사/연계)_매출액"] for row in result_data),
        "본사직접승인_건수": sum(row["본사직접승인_건수"] for row in result_data),
        "본사직접승인_매출액": sum(row["본사직접승인_매출액"] for row in result_data),
        "연계승인_건수": sum(row["연계승인_건수"] for row in result_data),
        "연계승인_매출액": sum(row["연계승인_매출액"] for row in result_data),
        "온라인_건수": sum(row["온라인_건수"] for row in result_data),
        "온라인_매출액": sum(row["온라인_매출액"] for row in result_data)
    }
    result_data.append(total_row)
    
    # 데이터프레임으로 변환
    result_df = pd.DataFrame(result_data)
    
    # 처리 시간 기록
    processing_time = time.time() - start_time
    print(f"제품별 매출 분석 시간: {processing_time:.2f}초")
    
    return result_df

def create_excel_report(
    cumulative_approval: pd.DataFrame,
    daily_approval: pd.DataFrame,
    cumulative_installation: Optional[pd.DataFrame],
    selected_date_str: str,
    original_approval_df: pd.DataFrame,
    original_installation_df: Optional[pd.DataFrame] = None,
    selected_date: Optional[date] = None
) -> Optional[bytes]:
    """
    분석 결과를 엑셀 파일로 변환하는 함수 - 성능 최적화 버전
    대용량 데이터 처리 최적화 및 메모리 사용량 감소
    
    Args:
        cumulative_approval: 누적 승인 실적 데이터프레임
        daily_approval: 일일 승인 실적 데이터프레임
        cumulative_installation: 누적 설치 실적 데이터프레임
        selected_date_str: 선택한 날짜 (문자열)
        original_approval_df: 원본 승인매출 데이터프레임
        original_installation_df: 원본 설치매출 데이터프레임 (선택사항)
        selected_date: 선택한 날짜 (date 객체, 선택사항)
        
    Returns:
        Optional[bytes]: 엑셀 바이너리 데이터 또는 None (오류 발생 시)
    """
    start_time = time.time()
    try:
        # 엑셀 파일 생성
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'constant_memory': True}})
        
        # 워크북과 워크시트 설정
        workbook = writer.book
        
        # 공통 스타일 정의 - 페이스북 스타일 파란색으로 변경
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#00498c',  # 페이스북 스타일 파란색
            'font_color': 'white',
            'border': 1,
            'border_color': '#D4D4D4'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#00498c',  # 페이스북 스타일 파란색
            'font_color': 'white',
            'border': 1
        })

        data_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D4D4D4'
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D4D4D4',
            'num_format': '#,##0'
        })

        # 헤더 형식 추가
        sub_header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#00498c',  # 페이스북 스타일 파란색
            'font_color': 'white',
            'border': 1
        })
        
        # 특수 데이터 형식 정의
        # 1. 모바일번호용 텍스트 형식 (앞에 ' 추가)
        mobile_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D4D4D4',
            'num_format': '@'  # 텍스트 형식
        })
        
        # 2. 날짜 형식 (YYYY-MM-DD)
        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D4D4D4',
            'num_format': 'yyyy-mm-dd'  # 날짜 형식
        })
        
        # 3. 시간 형식 (HH:MM:SS)
        time_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D4D4D4',
            'num_format': 'hh:mm:ss'  # 시간 형식
        })

        # 1. 매출현황 시트 (세로 레이아웃) - 선택한 날짜 기준
        worksheet1 = writer.sheets['매출현황'] = workbook.add_worksheet('매출현황')
        
        # 제목 추가 - 선택한 날짜 표시
        worksheet1.merge_range('A1:I1', f'일일 매출 현황 ({selected_date_str})', title_format)
        worksheet1.set_row(0, 25)  # 제목 행 높이 설정
        
        # 현재 행 인덱스
        current_row = 2  # 제목 다음 행부터 시작
        
        # 시트 속성 설정
        worksheet1.set_column(0, 0, 15)  # 구분 열 넓이
        worksheet1.set_column(1, 8, 12)  # 데이터 열 넓이
        
        # 1. 일일 승인실적 테이블 (선택한 날짜 기준) - 먼저 표시
        if not daily_approval.empty:
            # 헤더 작성
            worksheet1.merge_range(current_row, 0, current_row, 8, f'{selected_date_str} 실적', sub_header_format)
            current_row += 1
            
            # 주요 헤더
            worksheet1.write(current_row, 0, '구분', header_format)
            worksheet1.merge_range(current_row, 1, current_row, 2, '총승인(본사/연계)', header_format)
            worksheet1.merge_range(current_row, 3, current_row, 4, '본사직접승인', header_format)
            worksheet1.merge_range(current_row, 5, current_row, 6, '연계승인', header_format)
            worksheet1.merge_range(current_row, 7, current_row, 8, '온라인', header_format)
            current_row += 1
            
            # 서브 헤더
            worksheet1.write(current_row, 0, '', header_format)
            worksheet1.write(current_row, 1, '건수', header_format)
            worksheet1.write(current_row, 2, '매출액', header_format)
            worksheet1.write(current_row, 3, '건수', header_format)
            worksheet1.write(current_row, 4, '매출액', header_format)
            worksheet1.write(current_row, 5, '건수', header_format)
            worksheet1.write(current_row, 6, '매출액', header_format)
            worksheet1.write(current_row, 7, '건수', header_format)
            worksheet1.write(current_row, 8, '매출액', header_format)
            current_row += 1
            
            # 데이터 작성
            for idx, (_, row) in enumerate(daily_approval.iterrows()):
                worksheet1.write(current_row, 0, row['제품'], data_format)
                
                # 값 작성 - 백만 단위로 표시
                worksheet1.write(current_row, 1, row['총승인(본사/연계)_건수'], number_format)
                worksheet1.write(current_row, 2, row['총승인(본사/연계)_매출액'], number_format)
                worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
                worksheet1.write(current_row, 4, row['본사직접승인_매출액'], number_format)
                worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
                worksheet1.write(current_row, 6, row['연계승인_매출액'], number_format)
                worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
                worksheet1.write(current_row, 8, row['온라인_매출액'], number_format)
                current_row += 1
        else:
            # 데이터가 없는 경우 안내 메시지
            worksheet1.merge_range(current_row, 0, current_row, 8, f'{selected_date_str}에 해당하는 승인 데이터가 없습니다.', data_format)
            current_row += 2
        
        # 약간의 간격 추가
        current_row += 2
        
        # 2. 누적승인실적 테이블
        # 헤더 작성
        worksheet1.merge_range(current_row, 0, current_row, 8, '누적승인실적', sub_header_format)
        current_row += 1
        
        # 주요 헤더
        worksheet1.write(current_row, 0, '구분', header_format)
        worksheet1.merge_range(current_row, 1, current_row, 2, '총승인(본사/연계)', header_format)
        worksheet1.merge_range(current_row, 3, current_row, 4, '본사직접승인', header_format)
        worksheet1.merge_range(current_row, 5, current_row, 6, '연계승인', header_format)
        worksheet1.merge_range(current_row, 7, current_row, 8, '온라인', header_format)
        current_row += 1
        
        # 서브 헤더
        worksheet1.write(current_row, 0, '', header_format)
        worksheet1.write(current_row, 1, '건수', header_format)
        worksheet1.write(current_row, 2, '매출액', header_format)
        worksheet1.write(current_row, 3, '건수', header_format)
        worksheet1.write(current_row, 4, '매출액', header_format)
        worksheet1.write(current_row, 5, '건수', header_format)
        worksheet1.write(current_row, 6, '매출액', header_format)
        worksheet1.write(current_row, 7, '건수', header_format)
        worksheet1.write(current_row, 8, '매출액', header_format)
        current_row += 1
        
        # 데이터 작성
        for idx, (_, row) in enumerate(cumulative_approval.iterrows()):
            worksheet1.write(current_row, 0, row['제품'], data_format)
            
            # 값 작성 - 백만 단위로 표시
            worksheet1.write(current_row, 1, row['총승인(본사/연계)_건수'], number_format)
            worksheet1.write(current_row, 2, row['총승인(본사/연계)_매출액'], number_format)
            worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
            worksheet1.write(current_row, 4, row['본사직접승인_매출액'], number_format)
            worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
            worksheet1.write(current_row, 6, row['연계승인_매출액'], number_format)
            worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
            worksheet1.write(current_row, 8, row['온라인_매출액'], number_format)
            current_row += 1
        
        # 약간의 간격 추가
        current_row += 2
        
        # 3. 누적설치실적 테이블 (있는 경우)
        if cumulative_installation is not None and not cumulative_installation.empty:
            # 헤더 작성
            worksheet1.merge_range(current_row, 0, current_row, 8, '누적설치실적', sub_header_format)
            current_row += 1
            
            # 주요 헤더
            worksheet1.write(current_row, 0, '구분', header_format)
            worksheet1.merge_range(current_row, 1, current_row, 2, '총승인(본사/연계)', header_format)
            worksheet1.merge_range(current_row, 3, current_row, 4, '본사직접승인', header_format)
            worksheet1.merge_range(current_row, 5, current_row, 6, '연계승인', header_format)
            worksheet1.merge_range(current_row, 7, current_row, 8, '온라인', header_format)
            current_row += 1
            
            # 서브 헤더
            worksheet1.write(current_row, 0, '', header_format)
            worksheet1.write(current_row, 1, '건수', header_format)
            worksheet1.write(current_row, 2, '매출액', header_format)
            worksheet1.write(current_row, 3, '건수', header_format)
            worksheet1.write(current_row, 4, '매출액', header_format)
            worksheet1.write(current_row, 5, '건수', header_format)
            worksheet1.write(current_row, 6, '매출액', header_format)
            worksheet1.write(current_row, 7, '건수', header_format)
            worksheet1.write(current_row, 8, '매출액', header_format)
            current_row += 1
            
            # 데이터 작성
            for idx, (_, row) in enumerate(cumulative_installation.iterrows()):
                worksheet1.write(current_row, 0, row['제품'], data_format)
                
                # 값 작성 - 백만 단위로 표시
                worksheet1.write(current_row, 1, row['총승인(본사/연계)_건수'], number_format)
                worksheet1.write(current_row, 2, row['총승인(본사/연계)_매출액'], number_format)
                worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
                worksheet1.write(current_row, 4, row['본사직접승인_매출액'], number_format)
                worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
                worksheet1.write(current_row, 6, row['연계승인_매출액'], number_format)
                worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
                worksheet1.write(current_row, 8, row['온라인_매출액'], number_format)
                current_row += 1
        
        # 2. 승인매출 데이터 시트 - 원본 데이터 추가 (비어있는 열 제외, 매출금액(VAT제외) 제외)
        # 메모리 효율 개선: 대용량 데이터에서는 샘플링
        MAX_ROWS_EXPORT = 100000  # 최대 내보낼 행 수
        
        if original_approval_df is not None and not original_approval_df.empty:
            # 데이터가 너무 크면 샘플링 (행 수 제한)
            if len(original_approval_df) > MAX_ROWS_EXPORT:
                # 전체 행 수 기록
                total_rows = len(original_approval_df)
                
                # 필요한 경우에만 샘플 데이터 생성 (메모리 효율성)
                print(f"승인매출 데이터가 크므로 샘플링합니다. (총 {total_rows}행 중 {MAX_ROWS_EXPORT}행)")
                approval_data = original_approval_df.sample(MAX_ROWS_EXPORT, random_state=42).copy()
            else:
                approval_data = original_approval_df.copy()
                
            # 승인매출 시트 생성
            worksheet2 = writer.sheets['승인매출'] = workbook.add_worksheet('승인매출')
            
            # 원본 매출금액 대신 VAT제외 매출액을 사용
            if '매출금액' in approval_data.columns and '매출금액(VAT제외)' in approval_data.columns:
                # 매출금액(VAT제외) 컬럼을 매출금액 컬럼으로 복사
                approval_data['매출금액'] = approval_data['매출금액(VAT제외)']
            
            # 매출금액(VAT제외) 컬럼 제거
            if '매출금액(VAT제외)' in approval_data.columns:
                approval_data.drop('매출금액(VAT제외)', axis=1, inplace=True)
            
            # 1. 빈 열 확인 (효율적인 방법으로)
            empty_cols = []
            for col in approval_data.columns:
                # 첫 1000행만 검사하여 빠르게 처리
                col_data = approval_data[col].head(1000)
                if col_data.isna().all() or (col_data.astype(str).str.strip() == '').all():
                    # 전체 데이터에 대해 확인
                    if approval_data[col].isna().all() or (approval_data[col].astype(str).str.strip() == '').all():
                        empty_cols.append(col)
            
            # 비어있는 열 제거 (메모리 효율성)
            if empty_cols:
                approval_data.drop(empty_cols, axis=1, inplace=True)
            
            # 2. 특수 컬럼 타입 식별 - 효율적으로 상위 1000행만 확인
            mobile_columns = []  # 모바일 번호 컬럼
            date_columns = []    # 날짜 컬럼
            time_columns = []    # 시간 컬럼
            
            # 헤더 이름으로만 컬럼 분류
            for col in approval_data.columns:
                col_name = str(col).lower()
                
                # 모바일 번호 컬럼 식별
                if any(term in col_name for term in ["전화", "모바일", "휴대", "번호", "폰", "phone", "mobile", "cell", "연락처", "contact"]):
                    mobile_columns.append(col)
                
                # 날짜 컬럼 식별
                elif "일자" in col_name or "날짜" in col_name or "date" in col_name or "일시" in col_name:
                    date_columns.append(col)
                
                # 시간 컬럼 식별
                elif "시간" in col_name or "time" in col_name or "hour" in col_name:
                    time_columns.append(col)
            
            # 3. 엑셀 테이블 생성 - 최적화된 방식으로 데이터 쓰기
            # 행 블록 단위로 처리하여 메모리 효율성 개선
            BLOCK_SIZE = 10000  # 한번에 처리할 행 수
            
            # 컬럼명 쓰기
            for col_idx, col_name in enumerate(approval_data.columns):
                worksheet2.write(0, col_idx, col_name, header_format)
                
                # 컬럼 너비 자동 조정 (최적화: 상위 1000행만 사용)
                sample_data = approval_data[col_name].head(1000).astype(str)
                col_width = max(len(str(col_name)), sample_data.str.len().max() if not sample_data.empty else 0)
                worksheet2.set_column(col_idx, col_idx, min(col_width + 2, 30))  # 최대 너비 30
                
            # 블록 단위로 분할하여 데이터 쓰기
            total_rows = len(approval_data)
            for start_row in range(0, total_rows, BLOCK_SIZE):
                end_row = min(start_row + BLOCK_SIZE, total_rows)
                
                # 현재 블록 데이터 가져오기
                block_data = approval_data.iloc[start_row:end_row]
                
                # 블록 내 각 행 처리
                for row_offset, (_, row) in enumerate(block_data.iterrows()):
                    excel_row = start_row + row_offset + 1  # 엑셀 행 인덱스 (헤더 제외)
                    
                    # 최적화: 각 셀 타입에 따른 맞춤형 처리를 한 번에 결정
                    for col_idx, col_name in enumerate(block_data.columns):
                        value = row[col_name]
                        
                        # NaN 값 처리
                        if pd.isna(value):
                            worksheet2.write(excel_row, col_idx, "", data_format)
                            continue
                        
                        # 모바일 번호 처리 (텍스트 형식으로)
                        if col_name in mobile_columns:
                            # 숫자 값을 문자열로 변환
                            if isinstance(value, (int, float)):
                                mobile_str = str(int(value))  # 소수점 제거
                                # 10자리 숫자면 앞에 0 추가 (한국 휴대폰 번호 보정)
                                if len(mobile_str) == 10 and mobile_str.startswith('10'):
                                    mobile_str = '0' + mobile_str
                                worksheet2.write(excel_row, col_idx, mobile_str, mobile_format)
                            else:
                                # 문자열이면 그대로 사용
                                worksheet2.write(excel_row, col_idx, str(value), mobile_format)
                        
                        # 날짜 처리
                        elif col_name in date_columns:
                            # datetime 객체면 날짜 형식으로 처리
                            if isinstance(value, (datetime, pd.Timestamp)):
                                worksheet2.write_datetime(excel_row, col_idx, value, date_format)
                            # 숫자형 날짜면 Excel 날짜로 변환
                            elif isinstance(value, (int, float)) and 10000 < value < 100000:  # Excel 날짜 범위 체크
                                worksheet2.write(excel_row, col_idx, value, date_format)
                            else:
                                worksheet2.write(excel_row, col_idx, value, data_format)
                        
                        # 시간 처리
                        elif col_name in time_columns:
                            # datetime 객체면 시간 형식으로 처리
                            if isinstance(value, (datetime, pd.Timestamp)):
                                worksheet2.write_datetime(excel_row, col_idx, value, time_format)
                            # 숫자형 시간이면 Excel 시간으로 변환
                            elif isinstance(value, (int, float)) and 0 <= value < 1:  # Excel 시간 범위 체크 (0~1 사이)
                                worksheet2.write(excel_row, col_idx, value, time_format)
                            # 날짜형 숫자에 소수부분이 있으면 시간 포함 형식으로 처리
                            elif isinstance(value, (int, float)) and value % 1 != 0:
                                worksheet2.write(excel_row, col_idx, value, date_format)
                            else:
                                worksheet2.write(excel_row, col_idx, value, data_format)
                        
                        # 숫자 형식 지정
                        elif isinstance(value, (int, float)):
                            worksheet2.write(excel_row, col_idx, value, number_format)
                        
                        # 기타 데이터는 일반 형식으로 처리
                        else:
                            worksheet2.write(excel_row, col_idx, value, data_format)
                
                # 가비지 컬렉션 강제 실행으로 메모리 관리
                gc.collect()
                
            # 총 행수가 MAX_ROWS_EXPORT를 초과하는 경우 메시지 추가
            if len(original_approval_df) > MAX_ROWS_EXPORT:
                worksheet2.merge_range(total_rows + 2, 0, total_rows + 2, len(approval_data.columns) - 1, 
                    f"참고: 원본 데이터에는 총 {len(original_approval_df):,}행이 있지만, 성능을 위해 {MAX_ROWS_EXPORT:,}행만 내보냈습니다.", data_format)
        
        # 3. 설치매출 데이터 시트 - 원본 데이터 추가 (있는 경우)
        # 메모리 효율 개선: 대용량 데이터에서는 샘플링
        if original_installation_df is not None and not original_installation_df.empty:
            # 데이터가 너무 크면 샘플링 (행 수 제한)
            if len(original_installation_df) > MAX_ROWS_EXPORT:
                # 전체 행 수 기록
                total_rows = len(original_installation_df)
                
                # 샘플 데이터 생성
                print(f"설치매출 데이터가 크므로 샘플링합니다. (총 {total_rows}행 중 {MAX_ROWS_EXPORT}행)")
                installation_data = original_installation_df.sample(MAX_ROWS_EXPORT, random_state=42).copy()
            else:
                installation_data = original_installation_df.copy()
            
            # 설치매출 시트 생성
            worksheet3 = writer.sheets['설치매출'] = workbook.add_worksheet('설치매출')
            
            # 원본 매출금액 대신 VAT제외 매출액을 사용
            if '매출금액' in installation_data.columns and '매출금액(VAT제외)' in installation_data.columns:
                # 매출금액(VAT제외) 컬럼을 매출금액 컬럼으로 복사
                installation_data['매출금액'] = installation_data['매출금액(VAT제외)']
            
            # 매출금액(VAT제외) 컬럼 제거
            if '매출금액(VAT제외)' in installation_data.columns:
                installation_data.drop('매출금액(VAT제외)', axis=1, inplace=True)
            
            # 빈 열 확인 (효율적인 방법으로)
            empty_cols = []
            for col in installation_data.columns:
                # 첫 1000행만 검사하여 빠르게 처리
                col_data = installation_data[col].head(1000) 
                if col_data.isna().all() or (col_data.astype(str).str.strip() == '').all():
                    # 전체 데이터에 대해 확인
                    if installation_data[col].isna().all() or (installation_data[col].astype(str).str.strip() == '').all():
                        empty_cols.append(col)
            
            # 비어있는 열 제거
            if empty_cols:
                installation_data.drop(empty_cols, axis=1, inplace=True)
                
            # 특수 컬럼 타입 식별 - 최적화 (헤더 이름 기준만 사용)
            mobile_columns = []  # 모바일 번호 컬럼
            date_columns = []    # 날짜 컬럼
            time_columns = []    # 시간 컬럼
            
            # 헤더 이름으로만 컬럼 분류
            for col in installation_data.columns:
                col_name = str(col).lower()
                
                # 모바일 번호 컬럼 식별
                if any(term in col_name for term in ["전화", "모바일", "휴대", "번호", "폰", "phone", "mobile", "cell", "연락처", "contact"]):
                    mobile_columns.append(col)
                
                # 날짜 컬럼 식별
                elif "일자" in col_name or "날짜" in col_name or "date" in col_name or "일시" in col_name:
                    date_columns.append(col)
                
                # 시간 컬럼 식별
                elif "시간" in col_name or "time" in col_name or "hour" in col_name:
                    time_columns.append(col)
            
            # 컬럼명 쓰기
            for col_idx, col_name in enumerate(installation_data.columns):
                worksheet3.write(0, col_idx, col_name, header_format)
                
                # 컬럼 너비 자동 조정 (최적화: 상위 1000행만 사용)
                sample_data = installation_data[col_name].head(1000).astype(str)
                col_width = max(len(str(col_name)), sample_data.str.len().max() if not sample_data.empty else 0)
                worksheet3.set_column(col_idx, col_idx, min(col_width + 2, 30))  # 최대 너비 30
                
            # 블록 단위로 분할하여 데이터 쓰기
            total_rows = len(installation_data)
            for start_row in range(0, total_rows, BLOCK_SIZE):
                end_row = min(start_row + BLOCK_SIZE, total_rows)
                
                # 현재 블록 데이터 가져오기
                block_data = installation_data.iloc[start_row:end_row]
                
                # 블록 내 각 행 처리
                for row_offset, (_, row) in enumerate(block_data.iterrows()):
                    excel_row = start_row + row_offset + 1  # 엑셀 행 인덱스 (헤더 제외)
                    
                    # 최적화: 각 셀 타입에 따른 맞춤형 처리를 한 번에 결정
                    for col_idx, col_name in enumerate(block_data.columns):
                        value = row[col_name]
                        
                        # NaN 값 처리
                        if pd.isna(value):
                            worksheet3.write(excel_row, col_idx, "", data_format)
                            continue
                        
                        # 모바일 번호 처리 (텍스트 형식으로)
                        if col_name in mobile_columns:
                            # 숫자 값을 문자열로 변환
                            if isinstance(value, (int, float)):
                                mobile_str = str(int(value))  # 소수점 제거
                                # 10자리 숫자면 앞에 0 추가 (한국 휴대폰 번호 보정)
                                if len(mobile_str) == 10 and mobile_str.startswith('10'):
                                    mobile_str = '0' + mobile_str
                                worksheet3.write(excel_row, col_idx, mobile_str, mobile_format)
                            else:
                                # 문자열이면 그대로 사용
                                worksheet3.write(excel_row, col_idx, str(value), mobile_format)
                        
                        # 날짜 처리
                        elif col_name in date_columns:
                            # datetime 객체면 날짜 형식으로 처리
                            if isinstance(value, (datetime, pd.Timestamp)):
                                worksheet3.write_datetime(excel_row, col_idx, value, date_format)
                            # 숫자형 날짜면 Excel 날짜로 변환
                            elif isinstance(value, (int, float)) and 10000 < value < 100000:  # Excel 날짜 범위 체크
                                worksheet3.write(excel_row, col_idx, value, date_format)
                            else:
                                worksheet3.write(excel_row, col_idx, value, data_format)
                        
                        # 시간 처리
                        elif col_name in time_columns:
                            # datetime 객체면 시간 형식으로 처리
                            if isinstance(value, (datetime, pd.Timestamp)):
                                worksheet3.write_datetime(excel_row, col_idx, value, time_format)
                            # 숫자형 시간이면 Excel 시간으로 변환
                            elif isinstance(value, (int, float)) and 0 <= value < 1:  # Excel 시간 범위 체크 (0~1 사이)
                                worksheet3.write(excel_row, col_idx, value, time_format)
                            # 날짜형 숫자에 소수부분이 있으면 시간 포함 형식으로 처리
                            elif isinstance(value, (int, float)) and value % 1 != 0:
                                worksheet3.write(excel_row, col_idx, value, date_format)
                            else:
                                worksheet3.write(excel_row, col_idx, value, data_format)
                        
                        # 숫자 형식 지정
                        elif isinstance(value, (int, float)):
                            worksheet3.write(excel_row, col_idx, value, number_format)
                        
                        # 기타 데이터는 일반 형식으로 처리
                        else:
                            worksheet3.write(excel_row, col_idx, value, data_format)
                
                # 가비지 컬렉션 강제 실행으로 메모리 관리
                gc.collect()
                
            # 총 행수가 MAX_ROWS_EXPORT를 초과하는 경우 메시지 추가
            if len(original_installation_df) > MAX_ROWS_EXPORT:
                worksheet3.merge_range(total_rows + 2, 0, total_rows + 2, len(installation_data.columns) - 1, 
                    f"참고: 원본 데이터에는 총 {len(original_installation_df):,}행이 있지만, 성능을 위해 {MAX_ROWS_EXPORT:,}행만 내보냈습니다.", data_format)
        
        # 엑셀 파일 저장 완료
        writer.close()
        excel_data = output.getvalue()
        
        # 처리 시간 기록
        processing_time = time.time() - start_time
        print(f"엑셀 파일 생성 시간: {processing_time:.2f}초")
        
        return excel_data
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"엑셀 파일 생성 오류 (소요시간: {processing_time:.2f}초): {str(e)}")
        return None