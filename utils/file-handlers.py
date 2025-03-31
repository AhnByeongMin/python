"""
CRM 데이터 분석기 통합 파일 처리 모듈

이 모듈은 다양한 유형의 파일(승인매출, 설치매출, 상담주문계약내역, 콜타임)을 처리하는
표준화된 함수들을 제공합니다. 코드 중복을 제거하고 유지보수성을 높이기 위해 설계되었습니다.
"""

import pandas as pd
import numpy as np
import re
from io import BytesIO
from typing import Tuple, Dict, List, Optional, Any, Union
from datetime import datetime

# 설정 가져오기
from config import CONSULTANT_SETTINGS, SALES_ANALYSIS

# 개선된 유틸리티 함수 가져오기
from improved_utils import (
    read_excel_file, normalize_column_names, standardized_error_handler, 
    time_to_seconds, logger
)


@standardized_error_handler
def process_approval_file(file) -> pd.DataFrame:
    """
    승인매출 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 엑셀 파일 객체
        
    Returns:
        pd.DataFrame: 처리된 데이터프레임
    """
    # 엑셀 파일 읽기
    df, error = read_excel_file(file, parse_dates=['주문 일자'])
    if error:
        raise ValueError(error)
    
    # 필요한 컬럼 정의 및 매핑
    required_columns = [
        "주문 일자", "판매인입경로", "일반회차 캠페인", "대분류", 
        "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
        "판매 금액", "선납 렌탈 금액"
    ]
    
    # 컬럼명 매핑
    column_mapping = {
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
    
    # 컬럼명 정규화 및 필수 컬럼 확인
    df, missing_columns = normalize_column_names(df, column_mapping, required_columns)
    
    if missing_columns:
        raise ValueError(f"승인매출 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}")
    
    # VAT 세율 설정 - 1.1%
    vat_rate = SALES_ANALYSIS.get("VAT_RATE", 0.011)
    
    # 숫자형 변환 (대분류, 판매인입경로, 일반회차 캠페인 제외)
    numeric_columns = [
        "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
        "판매 금액", "선납 렌탈 금액"
    ]
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 총 패키지 할인 회차 데이터 정제
    # 특정 값들(39, 59, 60)은 0으로 대체 (비즈니스 규칙)
    zero_values = SALES_ANALYSIS.get("ZERO_PACKAGE_DISCOUNT_VALUES", [39, 59, 60])
    df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace(zero_values, 0)
    
    # 매출금액 계산 공식
    df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                  df['판매 금액'] + df['선납 렌탈 금액'])
    
    # VAT 제외 매출금액 계산
    df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
    
    return df


@standardized_error_handler
def process_installation_file(file) -> pd.DataFrame:
    """
    설치매출 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 설치매출 엑셀 파일 객체
        
    Returns:
        pd.DataFrame: 처리된 데이터프레임
    """
    # 엑셀 파일 읽기
    df, error = read_excel_file(file)
    if error:
        raise ValueError(error)
    
    # 날짜 컬럼 추정 (여러 가능한 이름)
    date_column_candidates = [
        "설치 일자", "설치일자", "주문 일자", "주문일자", 
        "계약 일자", "계약일자", "완료 일자", "완료일자"
    ]
    
    date_column = None
    for col in date_column_candidates:
        if col in df.columns:
            date_column = col
            break
    
    if date_column is None:
        # 날짜 포맷이 포함된 컬럼명 찾기 시도
        for col in df.columns:
            col_str = str(col).lower()
            if "일자" in col_str or "날짜" in col_str or "date" in col_str:
                date_column = col
                break
    
    if date_column:
        # 날짜 컬럼을 datetime 형식으로 변환
        try:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        except:
            pass  # 변환 실패 시 무시
    
    # 필요한 컬럼 및 매핑
    required_columns = [
        "판매인입경로", "일반회차 캠페인", "대분류", 
        "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
        "판매 금액", "선납 렌탈 금액"
    ]
    
    # 컬럼명 매핑
    column_mapping = {
        "판매인입경로": ["판매 인입경로", "인입경로", "영업채널", "영업 채널"],
        "일반회차 캠페인": ["캠페인", "일반회차캠페인", "회차", "회차 캠페인"],
        "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"],
        "월 렌탈 금액": ["월렌탈금액", "렌탈 금액", "렌탈금액", "월 렌탈료"],
        "약정 기간 값": ["약정기간값", "약정 기간", "약정개월", "약정 개월"],
        "총 패키지 할인 회차": ["총패키지할인회차", "패키지 할인", "할인 회차", "패키지할인회차"],
        "판매 금액": ["판매금액", "매출 금액", "매출금액"],
        "선납 렌탈 금액": ["선납렌탈금액", "선납금액", "선납 금액"]
    }
    
    # 컬럼명 정규화 및 필수 컬럼 확인
    df, missing_columns = normalize_column_names(df, column_mapping, required_columns)
    
    if missing_columns:
        raise ValueError(f"설치매출 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}")
    
    # 날짜 컬럼 이름을 "주문 일자"로 표준화
    if date_column and date_column != "주문 일자":
        df["주문 일자"] = df[date_column]
    
    # VAT 세율 설정 - 1.1%
    vat_rate = SALES_ANALYSIS.get("VAT_RATE", 0.011)
    
    # 숫자형 변환 (대분류, 판매인입경로, 일반회차 캠페인 제외)
    numeric_columns = [
        "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
        "판매 금액", "선납 렌탈 금액"
    ]
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 총 패키지 할인 회차 데이터 정제
    # 특정 값들(39, 59, 60)은 0으로 대체 (비즈니스 규칙)
    zero_values = SALES_ANALYSIS.get("ZERO_PACKAGE_DISCOUNT_VALUES", [39, 59, 60])
    df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace(zero_values, 0)
    
    # 매출금액 계산 공식
    df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                  df['판매 금액'] + df['선납 렌탈 금액'])
    
    # VAT 제외 매출금액 계산
    df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
    
    return df


@standardized_error_handler
def process_consultant_file(file) -> pd.DataFrame:
    """
    상담주문계약내역 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 엑셀 파일 객체
        
    Returns:
        pd.DataFrame: 처리된 데이터프레임
    """
    # 엑셀 파일 읽기 (헤더는 3행부터)
    df, error = read_excel_file(file, header=2)
    if error:
        raise ValueError(error)
    
    # 필요한 컬럼 정의 및 매핑
    required_columns = ["상담사", "상담사 조직", "대분류"]
    
    # 컬럼명 매핑
    column_mapping = {
        "상담사": ["상담원", "상담원명", "직원명", "사원명", "담당자"],
        "상담사 조직": ["조직", "부서", "팀", "상담팀", "부서명"],
        "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"]
    }
    
    # 컬럼명 정규화 및 필수 컬럼 확인
    df, missing_columns = normalize_column_names(df, column_mapping, required_columns)
    
    # 대분류 컬럼 특별 처리 - 중복이면 .0 버전 확인 (우리가 수동으로 부여한 인덱스)
    if "대분류" in missing_columns and "대분류.0" in df.columns:
        df["대분류"] = df["대분류.0"]
        missing_columns.remove("대분류")
    # 또는 .1 버전 확인 (pandas가 자동으로 부여한 인덱스)
    elif "대분류" in missing_columns and "대분류.1" in df.columns:
        df["대분류"] = df["대분류.1"]
        missing_columns.remove("대분류")
    
    if missing_columns:
        available_columns = ", ".join(df.columns.tolist()[:20]) + "..."  # 처음 20개만 표시
        raise ValueError(f"계약내역 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}\n사용 가능한 컬럼 일부: {available_columns}")
    
    # 필수 컬럼만 선택 (판매 유형 컬럼 포함)
    needed_columns = ["상담사", "상담사 조직", "대분류"]
    
    # 추가 컬럼 포함 여부 확인
    optional_columns = ['캠페인', '일반회차 캠페인', '판매 유형', '판매채널']
    for col in optional_columns:
        if col in df.columns:
            needed_columns.append(col)
    
    subset_df = df[needed_columns].copy()
    
    # NaN 값을 가진 행 제거
    subset_df = subset_df.dropna(subset=["상담사"])
    
    # 일반회차 캠페인 컬럼이 비어있는 값을 삭제
    if '일반회차 캠페인' in subset_df.columns:
        # NaN 또는 빈 문자열인 경우 필터링
        valid_rows = subset_df['일반회차 캠페인'].notna() & (subset_df['일반회차 캠페인'] != '')
        subset_df = subset_df[valid_rows]
    
    return subset_df


@standardized_error_handler
def process_calltime_file(file) -> pd.DataFrame:
    """
    콜타임 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 콜타임 엑셀 파일 객체
        
    Returns:
        pd.DataFrame: 처리된 데이터프레임
    """
    try:
        # 일반 엑셀 파일로 시도
        df, error = read_excel_file(file)
        
        if error or df is None:
            # 엑셀 파싱 실패, HTML 테이블로 시도
            return process_calltime_html(file)
            
        # 이미지에서 확인된 구조에 따라 필요한 컬럼 매핑
        # 상담원명은 B열(인덱스 1), 총 건수는 AA열, 총 시간은 AB열
        if len(df.columns) >= 28:  # AA와 AB 열이 존재하는지 확인 (A=0, B=1, ... Z=25, AA=26, AB=27)
            # 필요한 데이터 추출
            name_col = df.columns[1]  # 상담원명 (B열)
            count_col = df.columns[26]  # 총 건수 (AA열)
            time_col = df.columns[27]  # 총 시간 (AB열)
            
            # 필요한 데이터 추출
            result_df = pd.DataFrame({
                '상담원명': df[name_col],
                '총 건수': df[count_col],
                '총 시간': df[time_col]
            })
            
            # 데이터 정제
            result_df = clean_calltime_data(result_df)
            
            return result_df
        else:
            raise ValueError(f"필요한 컬럼을 찾을 수 없습니다. 컬럼 수: {len(df.columns)}")
            
    except Exception as e:
        # 모든 다른 예외 발생 시 HTML 처리 시도
        return process_calltime_html(file)


def process_calltime_html(file) -> pd.DataFrame:
    """
    HTML 형식의 콜타임 파일을 처리하는 함수
    
    Args:
        file: 업로드된 HTML 파일 객체
        
    Returns:
        pd.DataFrame: 처리된 데이터프레임
    """
    # 파일 포인터 초기화
    file.seek(0)
    file_bytes = file.read()
    
    try:
        content = file_bytes.decode('utf-8', errors='ignore')
        
        if '<table' not in content:
            raise ValueError("HTML 테이블을 찾을 수 없습니다.")
            
        # HTML에서 행 추출
        rows = re.findall(r'<tr.*?>(.*?)</tr>', content, re.DOTALL)
        
        # 모든 행과 셀 정보 수집
        all_rows = []
        for row in rows:
            cells = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL)
            if cells:
                all_rows.append(cells)
        
        if not all_rows:
            raise ValueError("HTML 테이블에서 데이터를 추출할 수 없습니다.")
        
        # 헤더 정보와 데이터 행 분리
        header_rows = all_rows[:2]  # 첫 두 행은 헤더
        data_rows = all_rows[2:]    # 나머지는 데이터
        
        # 각 데이터 행의 세번째 열부터는 시간 데이터, 마지막 두 열은 총 건수와 총 시간
        result_data = []
        for row in data_rows:
            if len(row) < 3:
                continue
            
            name = row[1]  # 두 번째 열은 상담원명
            
            # "합계" 행이나 공백 행은 건너뛰기
            if name.strip() in ['합계', '합 계', '총계', '총 계', ''] or '상담원' in name:
                continue
            
            # 마지막 두 열이 총 건수와 총 시간
            if len(row) >= 28:  # AA열(27)과 AB열(28)
                count = row[-2]  # AA열
                time = row[-1]   # AB열
                
                # 숫자와 시간 형식 검증
                try:
                    count = int(re.sub(r'[^\d]', '', count))
                    
                    # 0:00:00 시간은 제외
                    if time not in ['0:00:00', '00:00:00', '0']:
                        # 시간을 초로 변환
                        seconds = time_to_seconds(time)
                        
                        result_data.append({
                            '상담원명': name,
                            '총 건수': count,
                            '총 시간': time,
                            '총 시간_초': seconds
                        })
                except:
                    continue
        
        # 결과 데이터프레임 생성
        if result_data:
            result_df = pd.DataFrame(result_data)
            return result_df
        else:
            raise ValueError("유효한 상담원 데이터를 추출할 수 없습니다.")
            
    except Exception as e:
        raise ValueError(f"HTML 파일 처리 중 오류가 발생했습니다: {str(e)}")


def clean_calltime_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    콜타임 데이터를 정제하는 함수
    
    Args:
        df: 원본 콜타임 데이터프레임
        
    Returns:
        pd.DataFrame: 정제된 데이터프레임
    """
    # 숫자가 아닌 행 제거 (헤더, 합계 등)
    df = df[pd.to_numeric(df['총 건수'], errors='coerce').notnull()]
    
    # 누락된 데이터 행 제거
    df = df.dropna(subset=['상담원명'])
    
    # 유효하지 않은 상담원명 패턴 필터링
    invalid_patterns = CONSULTANT_SETTINGS.get("INVALID_CONSULTANT_PATTERNS", 
                                             ['휴식', '후처리', '대기', '기타', '합계', '00:00:00', '0:00:00'])
    
    for pattern in invalid_patterns:
        df = df[~df['상담원명'].astype(str).str.contains(pattern)]
    
    # 0:00:00이나 '0' 값을 가진 시간은 제거
    zero_time_patterns = CONSULTANT_SETTINGS.get("ZERO_TIME_PATTERNS", 
                                                ['0:00:00', '00:00:00', '0'])
    df = df[~df['총 시간'].astype(str).isin(zero_time_patterns)].copy()
    
    # 시간을 초로 변환
    df['총 시간_초'] = df['총 시간'].apply(time_to_seconds)
    
    return df