"""
일일 매출 현황 비즈니스 로직

이 모듈은 일일 매출 현황을 처리하고 분석하는 비즈니스 로직을 포함합니다.
UI와 독립적으로 작동하여 단위 테스트가 가능하도록 설계되었습니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
import re
import xlsxwriter
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union, Tuple

# utils.py에서 필요한 함수 가져오기
from utils.utils import format_time, peek_file_content

def process_approval_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    승인매출 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 승인매출 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 엑셀 파일 읽기
        df = pd.read_excel(file, parse_dates=['주문 일자'])
        
        # 필요한 컬럼 확인
        required_columns = [
            "주문 일자", "판매인입경로", "일반회차 캠페인", "대분류", 
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        # 컬럼명이 비슷한 경우 매핑
        column_mapping = {}
        for req_col in required_columns:
            if req_col in df.columns:
                continue  # 이미 존재하면 매핑 불필요
                
            # 유사한 컬럼명 목록
            similar_cols = {
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
            
            if req_col in similar_cols:
                # 유사한 컬럼 찾기
                for col in df.columns:
                    col_str = str(col).lower()
                    if any(term.lower() in col_str for term in similar_cols[req_col]):
                        column_mapping[col] = req_col
                        break
        
        # 컬럼명 변경
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # 필요한 컬럼 확인 재검사
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"승인매출 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}"
        
        # VAT 세율 설정 - 1.1%
        vat_rate = 0.011
        
        # 숫자형 변환 (대분류, 판매인입경로, 일반회차 캠페인 제외)
        numeric_columns = [
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 총 패키지 할인 회차 데이터 정제
        # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
        df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace([39, 59, 60], 0)
        
        # 매출금액 계산 공식
        df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                      df['판매 금액'] + df['선납 렌탈 금액'])
        
        # VAT 제외 매출금액 계산
        df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
        
        return df, None
        
    except Exception as e:
        return None, f"승인매출 파일 처리 중 오류가 발생했습니다: {str(e)}"

def process_installation_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    설치매출 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 설치매출 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 엑셀 파일 읽기 (날짜 관련 컬럼을 날짜 형식으로 변환)
        df = pd.read_excel(file)
        
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
        
        # 필요한 컬럼 확인
        required_columns = [
            "판매인입경로", "일반회차 캠페인", "대분류", 
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        # 컬럼명이 비슷한 경우 매핑
        column_mapping = {}
        for req_col in required_columns:
            if req_col in df.columns:
                continue  # 이미 존재하면 매핑 불필요
                
            # 유사한 컬럼명 목록
            similar_cols = {
                "판매인입경로": ["판매 인입경로", "인입경로", "영업채널", "영업 채널"],
                "일반회차 캠페인": ["캠페인", "일반회차캠페인", "회차", "회차 캠페인"],
                "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"],
                "월 렌탈 금액": ["월렌탈금액", "렌탈 금액", "렌탈금액", "월 렌탈료"],
                "약정 기간 값": ["약정기간값", "약정 기간", "약정개월", "약정 개월"],
                "총 패키지 할인 회차": ["총패키지할인회차", "패키지 할인", "할인 회차", "패키지할인회차"],
                "판매 금액": ["판매금액", "매출 금액", "매출금액"],
                "선납 렌탈 금액": ["선납렌탈금액", "선납금액", "선납 금액"]
            }
            
            if req_col in similar_cols:
                # 유사한 컬럼 찾기
                for col in df.columns:
                    col_str = str(col).lower()
                    if any(term.lower() in col_str for term in similar_cols[req_col]):
                        column_mapping[col] = req_col
                        break
        
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
        
        # 숫자형 변환 (대분류, 판매인입경로, 일반회차 캠페인 제외)
        numeric_columns = [
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 총 패키지 할인 회차 데이터 정제
        # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
        df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace([39, 59, 60], 0)
        
        # 매출금액 계산 공식
        df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                      df['판매 금액'] + df['선납 렌탈 금액'])
        
        # VAT 제외 매출금액 계산
        df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
        
        return df, None
        
    except Exception as e:
        return None, f"설치매출 파일 처리 중 오류가 발생했습니다: {str(e)}"

def analyze_sales_data(
    approval_df: pd.DataFrame, 
    installation_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    승인매출과 설치매출 데이터를 분석하는 함수
    
    Args:
        approval_df: 승인매출 데이터프레임
        installation_df: 설치매출 데이터프레임 (선택사항)
        
    Returns:
        Dict[str, Any]: 분석 결과를 담은 딕셔너리
    """
    try:
        # 결과 딕셔너리 초기화
        results = {}
        
        # 데이터 검증
        if approval_df is None or approval_df.empty:
            return {"error": "승인매출 데이터가 비어 있습니다."}
        
        # 최신 날짜 찾기 (주문 일자 필드가 있는 경우)
        latest_date = None
        if '주문 일자' in approval_df.columns:
            try:
                # datetime 형식으로 변환
                approval_df['주문 일자'] = pd.to_datetime(approval_df['주문 일자'], errors='coerce')
                
                # 최신 날짜 추출 (NaT 제외)
                valid_dates = approval_df['주문 일자'].dropna()
                if not valid_dates.empty:
                    latest_date_obj = valid_dates.max()
                    # 날짜 포맷팅 (예: "2023년 3월 25일")
                    latest_date = latest_date_obj.strftime("%m월%d일")
                    
                    # 날짜 객체도 저장 (필터링용)
                    latest_date_for_filter = latest_date_obj
            except Exception as e:
                return {"error": f"날짜 처리 중 오류가 발생했습니다: {str(e)}"}
        
        if latest_date is None:
            latest_date = "최근 날짜"
            latest_date_for_filter = None
        
        # 1. 누적승인실적 분석
        cumulative_approval = analyze_approval_data_by_product(approval_df)
        results["cumulative_approval"] = cumulative_approval
        
        # 2. 최신 날짜 기준 승인실적 분석
        daily_approval = pd.DataFrame()
        if latest_date_for_filter is not None:
            # 해당 날짜의 데이터만 필터링
            daily_df = approval_df[approval_df['주문 일자'].dt.date == latest_date_for_filter.date()].copy()
            
            if not daily_df.empty:
                daily_approval = analyze_approval_data_by_product(daily_df)
        
        results["daily_approval"] = daily_approval
        results["latest_date"] = latest_date
        
        # 3. 누적설치실적 분석 (설치매출 데이터가 있는 경우)
        cumulative_installation = None
        if installation_df is not None and not installation_df.empty:
            cumulative_installation = analyze_approval_data_by_product(installation_df)
        
        results["cumulative_installation"] = cumulative_installation
        
        return results
        
    except Exception as e:
        return {"error": f"데이터 분석 중 오류가 발생했습니다: {str(e)}"}

def analyze_daily_approval_by_date(approval_df: pd.DataFrame, selected_date: date) -> pd.DataFrame:
    """
    선택한 날짜에 대한 승인매출 데이터를 분석하는 함수
    
    Args:
        approval_df: 승인매출 데이터프레임
        selected_date: 선택한 날짜 (datetime.date 객체)
        
    Returns:
        pd.DataFrame: 선택한 날짜에 대한 분석 결과 데이터프레임
    """
    try:
        # 데이터 검증
        if approval_df is None or approval_df.empty:
            return pd.DataFrame()  # 빈 데이터프레임 반환
        
        # 주문 일자 필드가 있는지 확인
        if '주문 일자' not in approval_df.columns:
            return pd.DataFrame()
        
        # datetime 형식으로 변환 (이미 변환되어 있을 수 있음)
        if not pd.api.types.is_datetime64_any_dtype(approval_df['주문 일자']):
            approval_df['주문 일자'] = pd.to_datetime(approval_df['주문 일자'], errors='coerce')
        
        # 선택한 날짜의 데이터만 필터링
        daily_df = approval_df[approval_df['주문 일자'].dt.date == selected_date].copy()
        
        if daily_df.empty:
            return pd.DataFrame()  # 빈 데이터프레임 반환
        
        # 해당 날짜의 데이터 분석
        daily_approval = analyze_approval_data_by_product(daily_df)
        
        return daily_approval
        
    except Exception as e:
        print(f"일일 승인실적 분석 중 오류: {str(e)}")  # 콘솔에 오류 출력
        return pd.DataFrame()  # 오류 발생 시 빈 데이터프레임 반환

def analyze_approval_data_by_product(df: pd.DataFrame) -> pd.DataFrame:
    """
    제품별로 승인매출 데이터를 분석하는 함수 (요구된 표 형식에 맞춤)
    
    Args:
        df: 승인매출 데이터프레임
        
    Returns:
        pd.DataFrame: 분석 결과 데이터프레임
    """
    if df.empty:
        # 빈 결과 반환
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
    
    # 필터링 조건 정의
    # 1. 본사/연계합계: "CB-"로 시작하는 캠페인 제외, "V-", "C-"로 시작하거나 "캠", "정규", "분배"를 포함하는 캠페인
    total_mask = df['일반회차 캠페인'].astype(str).str.match(r'^(?!CB-).*$')
    campaign_mask = (
        df['일반회차 캠페인'].astype(str).str.startswith('V-') | 
        df['일반회차 캠페인'].astype(str).str.startswith('C-') | 
        df['일반회차 캠페인'].astype(str).str.contains('캠') | 
        df['일반회차 캠페인'].astype(str).str.contains('정규') | 
        df['일반회차 캠페인'].astype(str).str.contains('분배')
    )
    hq_link_df = df[total_mask & campaign_mask].copy()
    
    # 2. 본사: "CRM"을 포함하는 판매인입경로
    hq_mask = hq_link_df['판매인입경로'].astype(str).str.contains('CRM')
    hq_df = hq_link_df[hq_mask].copy()
    
    # 3. 연계: "CRM"을 포함하지 않는 판매인입경로
    link_mask = ~hq_link_df['판매인입경로'].astype(str).str.contains('CRM')
    link_df = hq_link_df[link_mask].copy()
    
    # 4. 온라인: "CB-"로 시작하는 캠페인
    online_mask = df['일반회차 캠페인'].astype(str).str.startswith('CB-')
    online_df = df[online_mask].copy()
    
    # 결과 저장을 위한 데이터 구조
    result_data = []
    
    # 각 제품별 집계
    for product in products:
        product_row = {"제품": product}
        
        # 제품 필터 마스크
        product_mask = df['대분류'].astype(str).str.contains(product)
        
        # 1. 총승인(본사/연계)
        hq_link_product = hq_link_df[hq_link_df['대분류'].astype(str).str.contains(product)]
        product_row["총승인(본사/연계)_건수"] = len(hq_link_product)
        product_row["총승인(본사/연계)_매출액"] = hq_link_product['매출금액(VAT제외)'].sum()
        
        # 2. 본사직접승인
        hq_product = hq_df[hq_df['대분류'].astype(str).str.contains(product)]
        product_row["본사직접승인_건수"] = len(hq_product)
        product_row["본사직접승인_매출액"] = hq_product['매출금액(VAT제외)'].sum()
        
        # 3. 연계승인
        link_product = link_df[link_df['대분류'].astype(str).str.contains(product)]
        product_row["연계승인_건수"] = len(link_product)
        product_row["연계승인_매출액"] = link_product['매출금액(VAT제외)'].sum()
        
        # 4. 온라인
        online_product = online_df[online_df['대분류'].astype(str).str.contains(product)]
        product_row["온라인_건수"] = len(online_product)
        product_row["온라인_매출액"] = online_product['매출금액(VAT제외)'].sum()
        
        result_data.append(product_row)
    
    # 총합계 행 추가
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
    분석 결과를 엑셀 파일로 변환하는 함수 - 원본 데이터 전체 포함 및 형식 포맷팅 수정
    
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
    try:
        # 엑셀 파일 생성
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        
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
                
                # 백만 단위로 변환하여 소수점 없이 반올림
                total_amount = row['총승인(본사/연계)_매출액']
                if total_amount >= 1000000:
                    worksheet1.write(current_row, 2, round(total_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 2, total_amount, number_format)
                
                worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
                
                hq_amount = row['본사직접승인_매출액']
                if hq_amount >= 1000000:
                    worksheet1.write(current_row, 4, round(hq_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 4, hq_amount, number_format)
                
                worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
                
                link_amount = row['연계승인_매출액']
                if link_amount >= 1000000:
                    worksheet1.write(current_row, 6, round(link_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 6, link_amount, number_format)
                
                worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
                
                online_amount = row['온라인_매출액']
                if online_amount >= 1000000:
                    worksheet1.write(current_row, 8, round(online_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 8, online_amount, number_format)
                
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
            
            # 백만 단위로 변환하여 소수점 없이 반올림
            total_amount = row['총승인(본사/연계)_매출액']
            if total_amount >= 1000000:
                worksheet1.write(current_row, 2, round(total_amount/1000000), number_format)
            else:
                worksheet1.write(current_row, 2, total_amount, number_format)
            
            worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
            
            hq_amount = row['본사직접승인_매출액']
            if hq_amount >= 1000000:
                worksheet1.write(current_row, 4, round(hq_amount/1000000), number_format)
            else:
                worksheet1.write(current_row, 4, hq_amount, number_format)
            
            worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
            
            link_amount = row['연계승인_매출액']
            if link_amount >= 1000000:
                worksheet1.write(current_row, 6, round(link_amount/1000000), number_format)
            else:
                worksheet1.write(current_row, 6, link_amount, number_format)
            
            worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
            
            online_amount = row['온라인_매출액']
            if online_amount >= 1000000:
                worksheet1.write(current_row, 8, round(online_amount/1000000), number_format)
            else:
                worksheet1.write(current_row, 8, online_amount, number_format)
            
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
                
                # 백만 단위로 변환하여 소수점 없이 반올림
                total_amount = row['총승인(본사/연계)_매출액']
                if total_amount >= 1000000:
                    worksheet1.write(current_row, 2, round(total_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 2, total_amount, number_format)
                
                worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
                
                hq_amount = row['본사직접승인_매출액']
                if hq_amount >= 1000000:
                    worksheet1.write(current_row, 4, round(hq_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 4, hq_amount, number_format)
                
                worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
                
                link_amount = row['연계승인_매출액']
                if link_amount >= 1000000:
                    worksheet1.write(current_row, 6, round(link_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 6, link_amount, number_format)
                
                worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
                
                online_amount = row['온라인_매출액']
                if online_amount >= 1000000:
                    worksheet1.write(current_row, 8, round(online_amount/1000000), number_format)
                else:
                    worksheet1.write(current_row, 8, online_amount, number_format)
                
                current_row += 1
        
        # 2. 승인매출 데이터 시트 - 원본 데이터 추가 (비어있는 열 제외, 매출금액(VAT제외) 제외)
        if original_approval_df is not None and not original_approval_df.empty:
            worksheet2 = writer.sheets['승인매출'] = workbook.add_worksheet('승인매출')
            
            # 원본 데이터에서 필요한 컬럼만 추출
            approval_data = original_approval_df.copy()
            
            # 원본 매출금액 대신 VAT제외 매출액을 사용
            if '매출금액' in approval_data.columns and '매출금액(VAT제외)' in approval_data.columns:
                # 매출금액(VAT제외) 컬럼을 매출금액 컬럼으로 복사
                approval_data['매출금액'] = approval_data['매출금액(VAT제외)']
            
            # 매출금액(VAT제외) 컬럼 제거
            if '매출금액(VAT제외)' in approval_data.columns:
                approval_data.drop('매출금액(VAT제외)', axis=1, inplace=True)
            
            # 비어있는 열 확인하여 제거
            empty_cols = []
            for col in approval_data.columns:
                # 모든 값이 NaN이거나 빈 문자열인 경우
                if approval_data[col].isna().all() or (approval_data[col].astype(str).str.strip() == '').all():
                    empty_cols.append(col)
            
            # 비어있는 열 제거
            if empty_cols:
                approval_data.drop(empty_cols, axis=1, inplace=True)
                
            # 특수 컬럼 타입 식별
            mobile_columns = []  # 모바일 번호 컬럼
            date_columns = []    # 날짜 컬럼
            time_columns = []    # 시간 컬럼
            
            # 컬럼 타입 분류
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
            
            # 컬럼명 쓰기
            for col_idx, col_name in enumerate(approval_data.columns):
                worksheet2.write(0, col_idx, col_name, header_format)
                # 컬럼 너비 설정 (자동 조정)
                col_width = max(len(str(col_name)), 
                               approval_data[col_name].astype(str).str.len().max() if not approval_data[col_name].empty else 0)
                worksheet2.set_column(col_idx, col_idx, min(col_width + 2, 30))  # 최대 너비 30
            
            # 데이터 쓰기
            for row_idx, (_, row) in enumerate(approval_data.iterrows(), 1):
                for col_idx, col_name in enumerate(approval_data.columns):
                    value = row[col_name]
                    
                    # NaN 값 처리
                    if pd.isna(value):
                        value = ""
                        worksheet2.write(row_idx, col_idx, value, data_format)
                        continue
                    
                    # 모바일 번호 처리 (텍스트 형식으로)
                    if col_name in mobile_columns:
                        # 숫자 값을 문자열로 변환
                        if isinstance(value, (int, float)):
                            mobile_str = str(int(value))  # 소수점 제거
                            # 10자리 숫자면 앞에 0 추가 (한국 휴대폰 번호 보정)
                            if len(mobile_str) == 10 and mobile_str.startswith('10'):
                                mobile_str = '0' + mobile_str
                            worksheet2.write(row_idx, col_idx, mobile_str, mobile_format)
                        else:
                            # 문자열이면 그대로 사용
                            worksheet2.write(row_idx, col_idx, str(value), mobile_format)
                    
                    # 날짜 처리
                    elif col_name in date_columns:
                        # datetime 객체면 날짜 형식으로 처리
                        if isinstance(value, (datetime, pd.Timestamp)):
                            worksheet2.write_datetime(row_idx, col_idx, value, date_format)
                        # 숫자형 날짜면 Excel 날짜로 변환
                        elif isinstance(value, (int, float)) and 10000 < value < 100000:  # Excel 날짜 범위 체크
                            worksheet2.write(row_idx, col_idx, value, date_format)
                        else:
                            worksheet2.write(row_idx, col_idx, value, data_format)
                    
                    # 시간 처리
                    elif col_name in time_columns:
                        # datetime 객체면 시간 형식으로 처리
                        if isinstance(value, (datetime, pd.Timestamp)):
                            worksheet2.write_datetime(row_idx, col_idx, value, time_format)
                        # 숫자형 시간이면 Excel 시간으로 변환
                        elif isinstance(value, (int, float)) and 0 <= value < 1:  # Excel 시간 범위 체크 (0~1 사이)
                            worksheet2.write(row_idx, col_idx, value, time_format)
                        # 날짜형 숫자에 소수부분이 있으면 시간 포함 형식으로 처리
                        elif isinstance(value, (int, float)) and value % 1 != 0:
                            worksheet2.write(row_idx, col_idx, value, date_format)
                        else:
                            worksheet2.write(row_idx, col_idx, value, data_format)
                    
                    # 숫자 형식 지정
                    elif isinstance(value, (int, float)):
                        worksheet2.write(row_idx, col_idx, value, number_format)
                    
                    # 기타 데이터는 일반 형식으로 처리
                    else:
                        worksheet2.write(row_idx, col_idx, value, data_format)
        
        # 3. 설치매출 데이터 시트 - 원본 데이터 추가 (있는 경우)
        if original_installation_df is not None and not original_installation_df.empty:
            worksheet3 = writer.sheets['설치매출'] = workbook.add_worksheet('설치매출')
            
            # 원본 데이터에서 필요한 컬럼만 추출
            installation_data = original_installation_df.copy()
            
            # 원본 매출금액 대신 VAT제외 매출액을 사용
            if '매출금액' in installation_data.columns and '매출금액(VAT제외)' in installation_data.columns:
                # 매출금액(VAT제외) 컬럼을 매출금액 컬럼으로 복사
                installation_data['매출금액'] = installation_data['매출금액(VAT제외)']
            
            # 매출금액(VAT제외) 컬럼 제거
            if '매출금액(VAT제외)' in installation_data.columns:
                installation_data.drop('매출금액(VAT제외)', axis=1, inplace=True)
            
            # 비어있는 열 확인하여 제거
            empty_cols = []
            for col in installation_data.columns:
                # 모든 값이 NaN이거나 빈 문자열인 경우
                if installation_data[col].isna().all() or (installation_data[col].astype(str).str.strip() == '').all():
                    empty_cols.append(col)
            
            # 비어있는 열 제거
            if empty_cols:
                installation_data.drop(empty_cols, axis=1, inplace=True)
                
            # 특수 컬럼 타입 식별
            mobile_columns = []  # 모바일 번호 컬럼
            date_columns = []    # 날짜 컬럼
            time_columns = []    # 시간 컬럼
            
            # 컬럼 타입 분류
            for col in installation_data.columns:
                col_name = str(col).lower()
                
                # 모바일 번호 컬럼 식별
                if any(term in col_name for term in ["전화", "모바일", "휴대", "번호", "폰", "phone", "mobile", "cell"]):
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
                # 컬럼 너비 설정 (자동 조정)
                col_width = max(len(str(col_name)), 
                               installation_data[col_name].astype(str).str.len().max() if not installation_data[col_name].empty else 0)
                worksheet3.set_column(col_idx, col_idx, min(col_width + 2, 30))  # 최대 너비 30
            
            # 데이터 쓰기
            for row_idx, (_, row) in enumerate(installation_data.iterrows(), 1):
                for col_idx, col_name in enumerate(installation_data.columns):
                    value = row[col_name]
                    
                    # NaN 값 처리
                    if pd.isna(value):
                        value = ""
                        worksheet3.write(row_idx, col_idx, value, data_format)
                        continue
                    
                    # 모바일 번호 처리 (텍스트 형식으로)
                    if col_name in mobile_columns:
                        # 숫자 값을 문자열로 변환
                        if isinstance(value, (int, float)):
                            mobile_str = str(int(value))  # 소수점 제거
                            # 10자리 숫자면 앞에 0 추가 (한국 휴대폰 번호 보정)
                            if len(mobile_str) == 10 and mobile_str.startswith('10'):
                                mobile_str = '0' + mobile_str
                            worksheet3.write(row_idx, col_idx, mobile_str, mobile_format)
                        else:
                            # 문자열이면 그대로 사용
                            worksheet3.write(row_idx, col_idx, str(value), mobile_format)
                    
                    # 날짜 처리
                    elif col_name in date_columns:
                        # datetime 객체면 날짜 형식으로 처리
                        if isinstance(value, (datetime, pd.Timestamp)):
                            worksheet3.write_datetime(row_idx, col_idx, value, date_format)
                        # 숫자형 날짜면 Excel 날짜로 변환
                        elif isinstance(value, (int, float)) and 10000 < value < 100000:  # Excel 날짜 범위 체크
                            worksheet3.write(row_idx, col_idx, value, date_format)
                        else:
                            worksheet3.write(row_idx, col_idx, value, data_format)
                    
                    # 시간 처리
                    elif col_name in time_columns:
                        # datetime 객체면 시간 형식으로 처리
                        if isinstance(value, (datetime, pd.Timestamp)):
                            worksheet3.write_datetime(row_idx, col_idx, value, time_format)
                        # 숫자형 시간이면 Excel 시간으로 변환
                        elif isinstance(value, (int, float)) and 0 <= value < 1:  # Excel 시간 범위 체크 (0~1 사이)
                            worksheet3.write(row_idx, col_idx, value, time_format)
                        # 날짜형 숫자에 소수부분이 있으면 시간 포함 형식으로 처리
                        elif isinstance(value, (int, float)) and value % 1 != 0:
                            worksheet3.write(row_idx, col_idx, value, date_format)
                        else:
                            worksheet3.write(row_idx, col_idx, value, data_format)
                    
                    # 숫자 형식 지정
                    elif isinstance(value, (int, float)):
                        worksheet3.write(row_idx, col_idx, value, number_format)
                    
                    # 기타 데이터는 일반 형식으로 처리
                    else:
                        worksheet3.write(row_idx, col_idx, value, data_format)
        
        # 엑셀 파일 저장
        writer.close()
        excel_data = output.getvalue()
        return excel_data
    except Exception as e:
        print(f"엑셀 파일 생성 중 오류: {str(e)}")  # 디버깅용 출력
        return None