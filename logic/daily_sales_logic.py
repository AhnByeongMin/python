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

# 목표 데이터 정의 - 2025년 4월 기준 (설치매출 기준)
INSTALLATION_TARGET_DATA = {
    "안마의자": {
        "직접": {"건수": 58, "매출액": 308948532},  # 본사
        "연계": {"건수": 74, "매출액": 395939547},  # 연계
        "온라인": {"건수": None, "매출액": 923000000}  # 온라인 (건수 목표 없음)
    },
    "라클라우드": {
        "직접": {"건수": 60, "매출액": 94031407},  # 본사
        "연계": {"건수": 22, "매출액": 34651871},  # 연계
        "온라인": {"건수": None, "매출액": 55380000}  # 온라인 (건수 목표 없음)
    },
    "정수기": {
        "직접": {"건수": 480, "매출액": 227049802},  # 본사
        "연계": {"건수": 6, "매출액": 2952104},      # 연계
        "온라인": {"건수": None, "매출액": 923000000}  # 온라인 (건수 목표 없음)
    }
}

# 승인매출 목표 데이터 계산 (설치매출 목표의 105%)
TARGET_DATA = {}
for product, targets in INSTALLATION_TARGET_DATA.items():
    TARGET_DATA[product] = {
        "직접": {
            "건수": targets["직접"]["건수"],  # 건수는 동일
            "매출액": int(targets["직접"]["매출액"] * 1.05)  # 매출액은 105%
        },
        "연계": {
            "건수": targets["연계"]["건수"],  # 건수는 동일
            "매출액": int(targets["연계"]["매출액"] * 1.05)  # 매출액은 105%
        },
        "온라인": {
            "건수": targets["온라인"]["건수"],  # 건수는 동일
            "매출액": int(targets["온라인"]["매출액"] * 1.05)  # 매출액은 105%
        }
    }

# 월별 합계 목표 (상단 합계 행 계산용)
TOTAL_TARGET = {
    "직접": {"건수": sum(item["직접"]["건수"] for item in TARGET_DATA.values() if item["직접"]["건수"] is not None),
             "매출액": sum(item["직접"]["매출액"] for item in TARGET_DATA.values())},
    "연계": {"건수": sum(item["연계"]["건수"] for item in TARGET_DATA.values() if item["연계"]["건수"] is not None),
             "매출액": sum(item["연계"]["매출액"] for item in TARGET_DATA.values())},
    "온라인": {"건수": None,  # 온라인은 건수 목표 없음
              "매출액": sum(item["온라인"]["매출액"] for item in TARGET_DATA.values())}
}

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
            "판매 금액", "선납 렌탈 금액", "매출액"
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
                "판매 금액": ["판매금액", "매출 금액"],
                "선납 렌탈 금액": ["선납렌탈금액", "선납금액", "선납 금액"],
                "매출액": ["순매출액", "매출금액", "매출", "net_sales", "net_revenue"]
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
        
        # 필요한 컬럼 확인 재검사 (매출액 컬럼 없으면 VAT 계산 필요)
        missing_columns = [col for col in required_columns[:-1] if col not in df.columns]  # 매출액은 필수가 아니어도 됨
        if missing_columns:
            return None, f"승인매출 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}"
        
        # 숫자형 변환 (대분류, 판매인입경로, 일반회차 캠페인 제외)
        numeric_columns = [
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        if "매출액" in df.columns:
            numeric_columns.append("매출액")
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 총 패키지 할인 회차 데이터 정제
        # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
        if "총 패키지 할인 회차" in df.columns:
            df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace([39, 59, 60], 0)
        
        # 매출금액 계산 공식 (ERP에서 제공한 매출액 컬럼이 없는 경우에만 계산)
        if "매출액" not in df.columns:
            # 일시불 판매 추가 할인 금액 컬럼이 있는지 확인
            has_discount_column = "일시불 판매 추가 할인 금액" in df.columns
            
            # 매출금액 계산
            if has_discount_column:
                df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                              df['판매 금액'] - df['일시불 판매 추가 할인 금액'] + df['선납 렌탈 금액'])
            else:
                df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                              df['판매 금액'] + df['선납 렌탈 금액'])
            
            # VAT 세율 설정 - 10%
            vat_rate = 0.1
            
            # VAT 제외 매출금액 계산
            df['매출액'] = round(df['매출금액'] / (1 + vat_rate), 0)
        
        # 매출금액(VAT제외) 컬럼도 호환성을 위해 유지 (매출액 값으로 복사)
        df['매출금액(VAT제외)'] = df['매출액']
        
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
                "판매 금액": ["판매금액", "매출 금액"],
                "선납 렌탈 금액": ["선납렌탈금액", "선납금액", "선납 금액"],
                "매출액": ["순매출액", "매출금액", "매출", "net_sales", "net_revenue"],
                "품목명": ["상품명", "제품명", "상품 명", "제품 명", "품목 명"]
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
        
        # 숫자형 변환 (대분류, 판매인입경로, 일반회차 캠페인 제외)
        numeric_columns = [
            "월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
            "판매 금액", "선납 렌탈 금액"
        ]
        
        if "매출액" in df.columns:
            numeric_columns.append("매출액")
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 총 패키지 할인 회차 데이터 정제
        # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
        if "총 패키지 할인 회차" in df.columns:
            df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace([39, 59, 60], 0)
        
        # 매출금액 계산 공식 (ERP에서 제공한 매출액 컬럼이 없는 경우에만 계산)
        if "매출액" not in df.columns:
            # 일시불 판매 추가 할인 금액 컬럼이 있는지 확인
            has_discount_column = "일시불 판매 추가 할인 금액" in df.columns
            
            # 매출금액 계산
            if has_discount_column:
                df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                              df['판매 금액'] - df['일시불 판매 추가 할인 금액'] + df['선납 렌탈 금액'])
            else:
                df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                              df['판매 금액'] + df['선납 렌탈 금액'])
            
            # VAT 세율 설정 - 10%
            vat_rate = 0.1
            
            # VAT 제외 매출금액 계산
            df['매출액'] = round(df['매출금액'] / (1 + vat_rate), 0)
        
        # 매출금액(VAT제외) 컬럼도 호환성을 위해 유지 (매출액 값으로 복사)
        df['매출금액(VAT제외)'] = df['매출액']
        
        return df, None
        
    except Exception as e:
        return None, f"설치매출 파일 처리 중 오류가 발생했습니다: {str(e)}"

def analyze_installation_by_product_model(installation_df):
    """
    제품별 설치현황을 분석하는 함수 (안마의자 제품별 설치현황 표 생성)
    
    Args:
        installation_df: 설치매출 데이터프레임
        
    Returns:
        pd.DataFrame: 분석 결과 데이터프레임
    """
    if installation_df is None or installation_df.empty:
        # 빈 결과 반환
        return pd.DataFrame({
            "제품명": ["합계"],
            "직접": [0],
            "연계": [0],
            "총건": [0],
            "비율": ["100.0%"]
        })
    
    # 품목명 컬럼 확인
    product_name_col = None
    for col_name in ['품목명', '상품명', '제품명', '품목 명', '상품 명', '제품 명']:
        if col_name in installation_df.columns:
            product_name_col = col_name
            break
    
    if product_name_col is None:
        # 품목명 컬럼이 없는 경우 빈 결과 반환
        return pd.DataFrame({
            "제품명": ["합계"],
            "직접": [0],
            "연계": [0],
            "총건": [0],
            "비율": ["100.0%"]
        })
    
    # 1. 안마의자 필터링 - 대분류 열과 품목명 열을 모두 확인
    massage_chair_mask = installation_df["대분류"].astype(str).str.contains("안마의자", case=False, na=False)
    
    # 품목명에도 '안마'가 포함된 항목 추가 (대분류가 다른 경우를 위해)
    massage_chair_mask |= installation_df[product_name_col].astype(str).str.contains("안마", case=False, na=False)
    
    massage_chair_data = installation_df[massage_chair_mask].copy()
    
    if massage_chair_data.empty:
        # 빈 결과 반환
        return pd.DataFrame({
            "제품명": ["합계"],
            "직접": [0],
            "연계": [0],
            "총건": [0],
            "비율": ["100.0%"]
        })
    
    # 2. 캠페인 필터링 (본사/연계합계와 동일) - 유연하게 수정
    campaign_mask = (
        massage_chair_data['일반회차 캠페인'].astype(str).str.strip() != ""  # ① 공백이 아닌 경우
    ) & (
        massage_chair_data['일반회차 캠페인'].astype(str).str.contains(r'^C-|^V-|캠|정규|재분배', case=False, na=False)  # ② C-, V-, 캠, 정규, 재분배 포함
    ) & ~(
        massage_chair_data['일반회차 캠페인'].astype(str).str.startswith('CB-', na=False)  # ③ CB- 제외
    )

    
    filtered_data = massage_chair_data[campaign_mask].copy()
    
    if filtered_data.empty:
        # 빈 결과 반환
        return pd.DataFrame({
            "제품명": ["합계"],
            "직접": [0],
            "연계": [0],
            "총건": [0],
            "비율": ["100.0%"]
        })
    
    # 3. 품목명 정리 (괄호 제거) - 개선된 방식으로
    def clean_product_name(name):
        if pd.isna(name):
            return ""
            
        name_str = str(name).strip()
        
        # 괄호가 있으면 괄호 앞부분만 사용
        if '(' in name_str:
            return name_str.split('(')[0].strip()
        
        # 공백이 있다면 첫 단어만 추출 (ex: "팔코닉 B&O" -> "팔코닉")
        if ' ' in name_str and '+' not in name_str:  # '+' 기호가 없는 경우에만
            return name_str.split(' ')[0].strip()
            
        return name_str
    
    filtered_data['정리품목명'] = filtered_data[product_name_col].apply(clean_product_name)
    
    # 4. 직접/연계 분리 - 판매인입경로에 CRM이 포함된 경우 직접, 아닌 경우 연계
    direct_mask = filtered_data['판매인입경로'].astype(str).str.contains('CRM', case=False, na=False)
    direct_data = filtered_data[direct_mask]
    affiliate_data = filtered_data[~direct_mask]
    
    # 5. 결과 데이터프레임 생성
    result_data = []
    
    # 각 제품별 건수 집계
    product_models = filtered_data['정리품목명'].dropna().unique()
    
    for model in product_models:
        if not model:  # 빈 문자열 제외
            continue
            
        direct_count = len(direct_data[direct_data['정리품목명'] == model])
        affiliate_count = len(affiliate_data[affiliate_data['정리품목명'] == model])
        total_count = direct_count + affiliate_count
        
        if total_count == 0:  # 건수가 0인 경우 제외
            continue
            
        # 각 제품의 비율 계산
        percentage = (total_count / len(filtered_data)) * 100
        
        result_data.append({
            "제품명": model,
            "직접": direct_count,
            "연계": affiliate_count,
            "총건": total_count,
            "비율": f"{percentage:.1f}%"
        })
    
    # 정렬 (총건 기준 내림차순)
    result_data = sorted(result_data, key=lambda x: x["총건"], reverse=True)
    
    # 합계 추가
    total_direct = sum(item["직접"] for item in result_data)
    total_affiliate = sum(item["연계"] for item in result_data)
    total_count = total_direct + total_affiliate
    
    result_data.append({
        "제품명": "합계",
        "직접": total_direct,
        "연계": total_affiliate,
        "총건": total_count,
        "비율": "100.0%"
    })
    
    # 데이터프레임으로 변환
    result_df = pd.DataFrame(result_data)
    
    return result_df

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
            "목표_건수": [0, 0, 0, 0],
            "목표_매출액": [0, 0, 0, 0],
            "총승인(본사/연계)_건수": [0, 0, 0, 0],
            "총승인(본사/연계)_매출액": [0, 0, 0, 0],
            "달성률_건수": [0, 0, 0, 0],
            "달성률_매출액": [0, 0, 0, 0],
            "본사직접승인_건수": [0, 0, 0, 0],
            "본사직접승인_매출액": [0, 0, 0, 0],
            "연계승인_건수": [0, 0, 0, 0],
            "연계승인_매출액": [0, 0, 0, 0],
            "온라인_건수": [0, 0, 0, 0],
            "온라인_매출액": [0, 0, 0, 0],
            "온라인달성률_매출액": [0, 0, 0, 0]
        })
    
    # 제품 종류 정의
    products = ["안마의자", "라클라우드", "정수기"]
    
    # 매출 컬럼 결정 (매출액이 있으면 그것을 사용, 없으면 매출금액(VAT제외) 사용)
    revenue_column = "매출액" if "매출액" in df.columns else "매출금액(VAT제외)"
    
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
        # 목표 데이터 가져오기
        target_direct_count = TARGET_DATA[product]["직접"]["건수"]  # 본사 목표 건수
        target_direct_amount = TARGET_DATA[product]["직접"]["매출액"]  # 본사 목표 매출액
        target_affiliate_count = TARGET_DATA[product]["연계"]["건수"]  # 연계 목표 건수
        target_affiliate_amount = TARGET_DATA[product]["연계"]["매출액"]  # 연계 목표 매출액
        target_online_amount = TARGET_DATA[product]["온라인"]["매출액"]  # 온라인 목표 매출액
        
        # 목표 합계 계산
        target_total_count = (target_direct_count or 0) + (target_affiliate_count or 0)  # 건수 목표 합계
        target_total_amount = target_direct_amount + target_affiliate_amount  # 매출액 목표 합계
        
        # 제품 필터 마스크
        product_mask = df['대분류'].astype(str).str.contains(product)
        
        # 1. 총승인(본사/연계)
        hq_link_product = hq_link_df[hq_link_df['대분류'].astype(str).str.contains(product)]
        total_count = len(hq_link_product)
        total_amount = hq_link_product[revenue_column].sum()
        
        # 달성률 계산 (목표가 0인 경우 0으로 처리)
        count_achievement_rate = (total_count / target_total_count * 100) if target_total_count > 0 else 0
        amount_achievement_rate = (total_amount / target_total_amount * 100) if target_total_amount > 0 else 0
        
        # 2. 본사직접승인
        hq_product = hq_df[hq_df['대분류'].astype(str).str.contains(product)]
        direct_count = len(hq_product)
        direct_amount = hq_product[revenue_column].sum()
        
        # 3. 연계승인
        link_product = link_df[link_df['대분류'].astype(str).str.contains(product)]
        affiliate_count = len(link_product)
        affiliate_amount = link_product[revenue_column].sum()
        
        # 4. 온라인
        online_product = online_df[online_df['대분류'].astype(str).str.contains(product)]
        online_count = len(online_product)
        online_amount = online_product[revenue_column].sum()
        
        # 온라인 달성률 계산
        online_achievement_rate = (online_amount / target_online_amount * 100) if target_online_amount > 0 else 0
        
        # 결과 추가
        result_data.append({
            "제품": product,
            "목표_건수": target_total_count,
            "목표_매출액": target_total_amount,
            "총승인(본사/연계)_건수": total_count,
            "총승인(본사/연계)_매출액": total_amount,
            "달성률_건수": count_achievement_rate,
            "달성률_매출액": amount_achievement_rate,
            "본사직접승인_건수": direct_count,
            "본사직접승인_매출액": direct_amount,
            "연계승인_건수": affiliate_count,
            "연계승인_매출액": affiliate_amount,
            "온라인_건수": online_count,
            "온라인_매출액": online_amount,
            "온라인달성률_매출액": online_achievement_rate
        })
    
    # 총합계 행 추가
    # 목표 총합계
    target_total_count = sum(row["목표_건수"] for row in result_data)
    target_total_amount = sum(row["목표_매출액"] for row in result_data)
    target_total_online_amount = sum(TARGET_DATA[product]["온라인"]["매출액"] for product in products)
    
    # 실적 합계
    total_count_sum = sum(row["총승인(본사/연계)_건수"] for row in result_data)
    total_amount_sum = sum(row["총승인(본사/연계)_매출액"] for row in result_data)
    direct_count_sum = sum(row["본사직접승인_건수"] for row in result_data)
    direct_amount_sum = sum(row["본사직접승인_매출액"] for row in result_data)
    affiliate_count_sum = sum(row["연계승인_건수"] for row in result_data)
    affiliate_amount_sum = sum(row["연계승인_매출액"] for row in result_data)
    online_count_sum = sum(row["온라인_건수"] for row in result_data)
    online_amount_sum = sum(row["온라인_매출액"] for row in result_data)
    
    # 총 달성률 계산
    total_count_achievement_rate = (total_count_sum / target_total_count * 100) if target_total_count > 0 else 0
    total_amount_achievement_rate = (total_amount_sum / target_total_amount * 100) if target_total_amount > 0 else 0
    online_total_achievement_rate = (online_amount_sum / target_total_online_amount * 100) if target_total_online_amount > 0 else 0
    
    # 총합계 행 추가
    result_data.append({
        "제품": "총합계",
        "목표_건수": target_total_count,
        "목표_매출액": target_total_amount,
        "총승인(본사/연계)_건수": total_count_sum,
        "총승인(본사/연계)_매출액": total_amount_sum,
        "달성률_건수": total_count_achievement_rate,
        "달성률_매출액": total_amount_achievement_rate,
        "본사직접승인_건수": direct_count_sum,
        "본사직접승인_매출액": direct_amount_sum,
        "연계승인_건수": affiliate_count_sum,
        "연계승인_매출액": affiliate_amount_sum,
        "온라인_건수": online_count_sum,
        "온라인_매출액": online_amount_sum,
        "온라인달성률_매출액": online_total_achievement_rate
    })
    
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
            
            # 백만 단위로 변환하여 소수점 없이 반올림
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
                
                # 백만 단위로 변환하여 소수점 없이 반올림
                worksheet1.write(current_row, 2, row['총승인(본사/연계)_매출액'], number_format)
                
                worksheet1.write(current_row, 3, row['본사직접승인_건수'], number_format)
                
                worksheet1.write(current_row, 4, row['본사직접승인_매출액'], number_format)
                
                worksheet1.write(current_row, 5, row['연계승인_건수'], number_format)
                
                worksheet1.write(current_row, 6, row['연계승인_매출액'], number_format)
                
                worksheet1.write(current_row, 7, row['온라인_건수'], number_format)
                
                worksheet1.write(current_row, 8, row['온라인_매출액'], number_format)
                
                current_row += 1
            
            # 4. 안마의자 제품별 설치현황 추가 (설치매출 데이터가 있는 경우)
            if original_installation_df is not None and not original_installation_df.empty:
                # 안마의자 제품별 분석 실행
                massage_chair_model_df = analyze_installation_by_product_model(original_installation_df)
                
                if not massage_chair_model_df.empty:
                    # 약간의 간격 추가
                    current_row += 2
                    
                    # 헤더 작성
                    worksheet1.merge_range(current_row, 0, current_row, 4, '안마의자 제품별 설치현황', sub_header_format)
                    current_row += 1
                    
                    # 컬럼 헤더
                    worksheet1.write(current_row, 0, '제품명', header_format)
                    worksheet1.write(current_row, 1, '직접', header_format)
                    worksheet1.write(current_row, 2, '연계', header_format)
                    worksheet1.write(current_row, 3, '총건', header_format)
                    worksheet1.write(current_row, 4, '비율', header_format)
                    current_row += 1
                    
                    # 데이터 작성
                    for idx, (_, row) in enumerate(massage_chair_model_df.iterrows()):
                        is_total = row['제품명'] == '합계'
                        row_format = sub_header_format if is_total else data_format
                        
                        worksheet1.write(current_row, 0, row['제품명'], row_format)
                        worksheet1.write(current_row, 1, row['직접'], row_format)
                        worksheet1.write(current_row, 2, row['연계'], row_format)
                        worksheet1.write(current_row, 3, row['총건'], row_format)
                        worksheet1.write(current_row, 4, row['비율'], row_format)
                        
                        current_row += 1
        
        # 2. 승인매출 데이터 시트 - 원본 데이터 추가 (비어있는 열 제외, 매출금액(VAT제외) 제외)
        if original_approval_df is not None and not original_approval_df.empty:
            worksheet2 = writer.sheets['승인매출'] = workbook.add_worksheet('승인매출')
            
            # 원본 데이터에서 필요한 컬럼만 추출
            approval_data = original_approval_df.copy()
            
            # 매출액 컬럼이 없는 경우 호환성을 위해 매출금액(VAT제외)로부터 생성
            if '매출액' not in approval_data.columns and '매출금액(VAT제외)' in approval_data.columns:
                approval_data['매출액'] = approval_data['매출금액(VAT제외)']
            
            # 매출금액(VAT제외) 컬럼은 그대로 유지
            
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
                    
                    # 모바일 번호 및 일반 전화번호 처리 (텍스트 형식으로)
                    if col_name in mobile_columns:
                        # 숫자 값을 문자열로 변환
                        if isinstance(value, (int, float)):
                            phone_str = str(int(value))  # 소수점 제거
                            
                            # 한국 전화번호 보정
                            if len(phone_str) == 10 and phone_str.startswith('10'):  # 휴대폰 번호 (예: 1012345678)
                                # 휴대폰 번호면 앞에 0 추가
                                formatted_str = '0' + phone_str
                            elif len(phone_str) == 9:
                                if phone_str.startswith('2'):  # 서울 지역번호 (예: 212345678)
                                    # 서울 지역번호(02)인 경우 앞에 0 추가
                                    formatted_str = '0' + phone_str
                                elif phone_str.startswith('3') or phone_str.startswith('4') or phone_str.startswith('5') or phone_str.startswith('6'):
                                    # 기타 지역번호(031, 032, 033, 041 등)도 앞에 0 추가
                                    # 334392221 -> 0334392221 (033 지역번호)
                                    formatted_str = '0' + phone_str
                                else:
                                    # 그 외는 그대로 유지
                                    formatted_str = phone_str
                            elif len(phone_str) == 10 and (phone_str.startswith('31') or phone_str.startswith('32') or 
                                                        phone_str.startswith('33') or phone_str.startswith('41') or 
                                                        phone_str.startswith('42') or phone_str.startswith('43') or 
                                                        phone_str.startswith('51') or phone_str.startswith('52') or 
                                                        phone_str.startswith('53') or phone_str.startswith('54') or 
                                                        phone_str.startswith('55') or phone_str.startswith('61') or 
                                                        phone_str.startswith('62') or phone_str.startswith('63') or 
                                                        phone_str.startswith('64')):
                                # 지역번호인 경우 앞에 0 추가
                                formatted_str = '0' + phone_str
                            else:
                                # 서비스 번호(예: 15883082) 또는 기타 번호는 그대로 유지
                                formatted_str = phone_str
                                
                            worksheet2.write(row_idx, col_idx, formatted_str, mobile_format)
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
            
            # 매출액 컬럼이 없는 경우 호환성을 위해 매출금액(VAT제외)로부터 생성
            if '매출액' not in installation_data.columns and '매출금액(VAT제외)' in installation_data.columns:
                installation_data['매출액'] = installation_data['매출금액(VAT제외)']
            
            # 매출금액(VAT제외) 컬럼은 그대로 유지
            
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