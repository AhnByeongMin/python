"""
상담사 프로모션 현황 UI 모듈

이 모듈은 상담사 프로모션 현황 탭의 UI 요소와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta, date
import uuid
import json
import os
from typing import Dict, List, Optional, Any
import calendar

# 비즈니스 로직 가져오기
from logic.promotion_logic import (
    process_promotion_file, analyze_promotion_data, create_excel_report,
    save_promotion_config, load_promotion_config, list_promotion_configs
)

# CSS 스타일 가져오기
from styles.promotion_styles import (
    PROMOTION_TAB_STYLE, FORMAT_REWARD_SCRIPT,
    DOWNLOAD_BUTTON_STYLE, USAGE_GUIDE_MARKDOWN
)

# 자동 저장 파일명
AUTO_SAVE_NAME = "자동저장"

# 추가 CSS 스타일
DYNAMIC_REWARD_STYLE = """
<style>
.reward-config-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    gap: 10px;
}
.reward-amount {
    flex: 2;
}
.reward-count {
    flex: 1;
}
.reward-delete {
    flex: 0;
}
.config-actions {
    display: flex;
    gap: 10px;
    margin-top: 15px;
    margin-bottom: 15px;
}
.config-actions input {
    flex: 2;
}
.config-actions button, .config-actions select {
    flex: 1;
}
</style>
"""

# 조직 이름 매핑 - 여러 이름을 표준 이름으로 매핑
ORG_MAPPING = {
    "CRM팀": "CRM파트",
    "CRM파트": "CRM파트",
    "온라인팀": "온라인파트",
    "온라인파트": "온라인파트"
}

def get_date_range(option: str, min_date: date, max_date: date) -> tuple:
    """
    선택된 날짜 범위 옵션에 따른 시작일과 종료일을 반환합니다.
    
    Args:
        option: 날짜 범위 옵션 (예: "전체 기간", "최근 7일", "이번 달", 등)
        min_date: 데이터의 최소 날짜
        max_date: 데이터의 최대 날짜
    
    Returns:
        tuple: (시작일, 종료일) 튜플
    """
    today = datetime.now().date()
    
    if option == "전체 기간":
        return (min_date, max_date)
    
    elif option == "최근 7일":
        start_date = today - timedelta(days=6)
        return (max(start_date, min_date), min(today, max_date))
    
    elif option == "최근 30일":
        start_date = today - timedelta(days=29)
        return (max(start_date, min_date), min(today, max_date))
    
    elif option == "최근 90일":
        start_date = today - timedelta(days=89)
        return (max(start_date, min_date), min(today, max_date))
    
    elif option == "이번 달":
        start_date = date(today.year, today.month, 1)
        return (max(start_date, min_date), min(today, max_date))
    
    elif option == "지난 달":
        last_month = today.month - 1
        year = today.year
        if last_month == 0:
            last_month = 12
            year -= 1
        
        start_date = date(year, last_month, 1)
        _, last_day = calendar.monthrange(year, last_month)
        end_date = date(year, last_month, last_day)
        
        return (max(start_date, min_date), min(end_date, max_date))
    
    elif option == "이번 분기":
        current_quarter = (today.month - 1) // 3 + 1
        start_month = (current_quarter - 1) * 3 + 1
        start_date = date(today.year, start_month, 1)
        
        return (max(start_date, min_date), min(today, max_date))
    
    elif option == "지난 분기":
        current_quarter = (today.month - 1) // 3 + 1
        last_quarter = current_quarter - 1
        year = today.year
        
        if last_quarter == 0:
            last_quarter = 4
            year -= 1
        
        start_month = (last_quarter - 1) * 3 + 1
        start_date = date(year, start_month, 1)
        
        end_month = start_month + 2
        _, last_day = calendar.monthrange(year, end_month)
        end_date = date(year, end_month, last_day)
        
        return (max(start_date, min_date), min(end_date, max_date))
    
    elif option == "올해":
        start_date = date(today.year, 1, 1)
        return (max(start_date, min_date), min(today, max_date))
    
    elif option == "작년":
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
        return (max(start_date, min_date), min(end_date, max_date))
    
    # 사용자 정의 (기본값)
    return (min_date, max_date)

def load_consultants_data() -> Dict[str, List[str]]:
    """
    상담사 명단 파일(data/consultants.json)을 로드하는 함수
    
    Returns:
        Dict[str, List[str]]: 조직별 상담사 명단 (표준화된 조직명 사용)
    """
    try:
        # 상담사 명단 파일 경로
        file_path = "data/consultants.json"
        
        # 파일이 존재하는지 확인
        if not os.path.exists(file_path):
            # 존재하지 않으면 빈 딕셔너리 반환
            return {}
        
        # JSON 파일 불러오기
        with open(file_path, 'r', encoding='utf-8') as f:
            consultants_data = json.load(f)
        
        # 조직명 매핑 적용 (표준화)
        standardized_data = {}
        for org, consultants in consultants_data.items():
            # 조직명 매핑 적용 (알려진 조직명인 경우)
            std_org = ORG_MAPPING.get(org, org)
            standardized_data[std_org] = consultants
        
        return standardized_data
    except Exception as e:
        # 오류 발생 시 빈 딕셔너리 반환
        print(f"상담사 명단 로드 중 오류 발생: {str(e)}")
        return {}

def create_empty_consultant_dataframe(consultants: List[str]) -> pd.DataFrame:
    """
    상담사 목록으로 빈 데이터프레임을 생성하는 함수
    
    Args:
        consultants: 상담사 목록
    
    Returns:
        pd.DataFrame: 상담사 목록이 포함된 빈 데이터프레임
    """
    # 기본 컬럼 설정
    columns = ["상담사", "안마의자", "라클라우드", "정수기", "더케어", "멤버십", "누적승인(건)", "누적승인(액)"]
    data = []
    
    # 각 상담사마다 빈 행 생성
    for consultant in consultants:
        data.append({
            "상담사": consultant,
            "안마의자": 0,
            "라클라우드": 0,
            "정수기": 0,
            "더케어": 0,
            "멤버십": 0,
            "누적승인(건)": 0,
            "누적승인(액)": 0
        })
    
    return pd.DataFrame(data)

def calculate_tickets_by_count(df: pd.DataFrame, count_config: List[Dict[str, int]]) -> pd.DataFrame:
    """
    승인 건수를 기반으로 추첨권 수 계산 (승인 건수 기반 추첨권 계산 방식)
    
    Args:
        df: 결과 데이터프레임
        count_config: 승인 건수 기반 추첨권 설정
            [{"min_count": 2, "tickets": 1}, {"min_count": 5, "tickets": 2}, ...]
    
    Returns:
        pd.DataFrame: 추첨권 수가 계산된 데이터프레임
    """
    if df is None or df.empty or not count_config:
        return df
    
    # 데이터프레임 복사
    result_df = df.copy()
    
    # 기본 추첨권 0으로 초기화
    result_df["추첨권"] = 0
    
    # 승인 건수 기반 추첨권 계산
    # 주의: 각 구간별로 중첩 적용이 아니라, 가장 높은 구간 하나만 적용
    for i, consultant in result_df.iterrows():
        approval_count = consultant["누적승인(건)"]
        max_tickets = 0
        
        # 가장 많은, 적용 가능한 추첨권 찾기
        for config in sorted(count_config, key=lambda x: x["min_count"], reverse=True):
            if approval_count >= config["min_count"]:
                max_tickets = config["tickets"]
                break
        
        # 추첨권 설정
        result_df.at[i, "추첨권"] = max_tickets
    
    return result_df

def post_process_results(
    df: pd.DataFrame, 
    reward_config: List[Dict[str, int]], 
    min_condition: int, 
    promotion_type: str,
    lottery_method: str = "product_weight",
    lottery_count_config: List[Dict[str, int]] = None
) -> pd.DataFrame:
    """
    분석 결과를 후처리하여 기준 미충족 상담사에 대한 표시를 추가하는 함수
    
    Args:
        df: 결과 데이터프레임
        reward_config: 포상금 설정
        min_condition: 최소 건수 조건
        promotion_type: 프로모션 유형
        lottery_method: 추첨권 계산 방식 ("product_weight" 또는 "approval_count")
        lottery_count_config: 승인 건수 기반 추첨권 설정
    
    Returns:
        pd.DataFrame: 후처리된 데이터프레임
    """
    if df is None or df.empty:
        return df
    
    # 데이터프레임 복사
    result_df = df.copy()
    
    # 추첨권 프로모션이고 승인 건수 기반 방식인 경우, 추첨권 재계산
    if promotion_type == "추첨권" and lottery_method == "approval_count" and lottery_count_config:
        result_df = calculate_tickets_by_count(result_df, lottery_count_config)
    
    # 포상금 프로모션인 경우
    if promotion_type == "포상금":
        # 포상금 컬럼이 있는 경우
        if "포상금" in result_df.columns:
            # 기준 미충족 조건 확인 (최소 건수 미만)
            mask = result_df["누적승인(건)"] < min_condition
            # 기준 미충족인 경우 "기준 미충족"으로 표시
            result_df.loc[mask, "포상금"] = "기준 미충족"
        
        # 포상획득여부 컬럼이 있는 경우
        elif "포상획득여부" in result_df.columns:
            # 최소 건수 조건을 충족하지 않는 경우 "기준 미충족"으로 표시
            mask = result_df["누적승인(건)"] < min_condition
            result_df.loc[mask, "포상획득여부"] = "기준 미충족"
    
    # 추첨권 프로모션인 경우
    elif promotion_type == "추첨권":
        if "포상획득여부" in result_df.columns:
            # 기준 미충족 조건 확인 (최소 건수 미만)
            mask = result_df["누적승인(건)"] < min_condition
            # 기준 미충족인 경우 "기준 미충족"으로 표시
            result_df.loc[mask, "포상획득여부"] = "기준 미충족"
    
    return result_df

def modify_dataframe_to_include_all_consultants(df: pd.DataFrame, additional_consultants: List[str]) -> pd.DataFrame:
    """
    데이터프레임에 모든 상담사를 포함시키는 함수
    
    Args:
        df: 원본 데이터프레임
        additional_consultants: 추가할 상담사 목록
    
    Returns:
        pd.DataFrame: 수정된 데이터프레임
    """
    if df is None and not additional_consultants:
        return df
    
    # 데이터프레임이 없거나 비어있는 경우 새로 생성
    if df is None or df.empty:
        if additional_consultants:
            return create_empty_consultant_dataframe(additional_consultants)
        else:
            return df
    
    # 원본 데이터프레임 복사
    result_df = df.copy()
    
    # 현재 데이터프레임에 있는 상담사 목록
    existing_consultants = []
    if "상담사" in result_df.columns:
        existing_consultants = result_df["상담사"].unique().tolist()
    
    # 추가할 상담사 목록 필터링
    new_consultants = [c for c in additional_consultants if c not in existing_consultants]
    
    # 새 상담사가 없는 경우 원래 데이터프레임 반환
    if not new_consultants:
        return result_df
    
    # 새 상담사용 빈 데이터프레임 생성
    new_df = create_empty_consultant_dataframe(new_consultants)
    
    # 기존 데이터프레임과 새 데이터프레임 결합
    return pd.concat([result_df, new_df], ignore_index=True)

def get_sorted_results(df: pd.DataFrame, criteria: List[str]) -> pd.DataFrame:
    """
    결과를 정렬하는 함수 (동률 처리 포함)
    
    Args:
        df: 결과 데이터프레임
        criteria: 정렬 기준 목록
    
    Returns:
        pd.DataFrame: 정렬된 데이터프레임
    """
    if df is None or df.empty:
        return df
    
    # 데이터프레임 복사
    result_df = df.copy()
    
    # 정렬 기준 및 방식 설정
    sort_columns = []
    ascending_values = []
    
    # 기준에 따라 정렬 설정
    for criterion in criteria:
        if criterion == "승인건수":
            sort_columns.append("누적승인(건)")
            ascending_values.append(False)  # 내림차순
        elif criterion == "승인액":
            sort_columns.append("누적승인(액)")
            ascending_values.append(False)  # 내림차순
        elif criterion == "추첨권" and "추첨권" in result_df.columns:
            sort_columns.append("추첨권")
            ascending_values.append(False)  # 내림차순
    
    # 동률 처리를 위한 2차 기준 추가
    if "승인건수" in criteria and "승인액" not in criteria:
        # 승인건수는 있지만 승인액은 없는 경우, 승인액을 2차 기준으로 추가
        sort_columns.append("누적승인(액)")
        ascending_values.append(False)  # 내림차순
    
    # 정렬
    if sort_columns:
        result_df = result_df.sort_values(by=sort_columns, ascending=ascending_values)
    
    # 순위 재부여
    result_df["순위"] = range(1, len(result_df) + 1)
    
    return result_df

def auto_save_settings():
    """현재 설정을 자동으로 저장하는 함수"""
    try:
        # 포상금 설정 저장
        if st.session_state.promotion_type == "포상금":
            config_data = {
                "type": "reward",
                "data": st.session_state.reward_config,
                "settings": {
                    "promotion_type": st.session_state.promotion_type,
                    "include_products": st.session_state.include_products,
                    "include_services": st.session_state.include_services,
                    "direct_only": st.session_state.direct_only,
                    "criteria": st.session_state.criteria,
                    "min_condition": st.session_state.min_condition,
                    "include_all_consultants": st.session_state.include_all_consultants,
                    "date_range_option": st.session_state.date_range_option
                }
            }
        else:  # 추첨권 설정 저장
            config_data = {
                "type": "lottery",
                "data": st.session_state.lottery_weights,
                "lottery_method": st.session_state.lottery_method,
                "lottery_count_config": st.session_state.lottery_count_config if st.session_state.lottery_method == "approval_count" else [],
                "settings": {
                    "promotion_type": st.session_state.promotion_type,
                    "include_products": st.session_state.include_products,
                    "include_services": st.session_state.include_services,
                    "direct_only": st.session_state.direct_only,
                    "criteria": st.session_state.criteria,
                    "min_condition": st.session_state.min_condition,
                    "include_all_consultants": st.session_state.include_all_consultants,
                    "date_range_option": st.session_state.date_range_option
                }
            }
        
        # 자동 저장
        save_promotion_config(AUTO_SAVE_NAME, config_data)
    except Exception as e:
        print(f"자동 저장 중 오류 발생: {str(e)}")

def load_auto_saved_settings():
    """자동 저장된 설정을 불러오는 함수"""
    try:
        # 자동 저장된 설정 불러오기
        config_data, error = load_promotion_config(AUTO_SAVE_NAME)
        
        if error or not config_data:
            return False
        
        # 설정 타입에 따라 처리
        if config_data.get("type") == "reward":
            st.session_state.reward_config = config_data.get("data", [])
            st.session_state.promotion_type = "포상금"
        elif config_data.get("type") == "lottery":
            st.session_state.lottery_weights = config_data.get("data", {})
            st.session_state.promotion_type = "추첨권"
            
            # 추첨권 방식 불러오기
            if "lottery_method" in config_data:
                st.session_state.lottery_method = config_data["lottery_method"]
            # 승인 건수 기반 추첨권 설정 불러오기
            if "lottery_count_config" in config_data:
                st.session_state.lottery_count_config = config_data["lottery_count_config"]
        
        # 공통 설정 불러오기
        settings = config_data.get("settings", {})
        
        if "include_products" in settings:
            st.session_state.include_products = settings["include_products"]
        if "include_services" in settings:
            st.session_state.include_services = settings["include_services"]
        if "direct_only" in settings:
            st.session_state.direct_only = settings["direct_only"]
        if "criteria" in settings:
            st.session_state.criteria = settings["criteria"]
        if "min_condition" in settings:
            st.session_state.min_condition = settings["min_condition"]
        if "include_all_consultants" in settings:
            st.session_state.include_all_consultants = settings["include_all_consultants"]
        if "date_range_option" in settings:
            st.session_state.date_range_option = settings["date_range_option"]
        
        return True
    except Exception as e:
        print(f"자동 저장 설정 불러오기 중 오류 발생: {str(e)}")
        return False

def show():
    """상담사 프로모션 현황 탭 UI를 표시하는 메인 함수"""
    
    # 스타일 적용
    st.markdown(PROMOTION_TAB_STYLE, unsafe_allow_html=True)
    st.markdown(FORMAT_REWARD_SCRIPT, unsafe_allow_html=True)
    st.markdown(DYNAMIC_REWARD_STYLE, unsafe_allow_html=True)
    
    # 타이틀 및 설명
    st.title("🏆 상담사 프로모션 진행현황")
    st.markdown('<p>이 도구는 상담사별 프로모션 현황을 분석하고 커스터마이징할 수 있습니다. 다양한 기준으로 상담사들의 실적을 비교하고 포상 여부를 결정할 수 있습니다.</p>', unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if 'promotion_df' not in st.session_state:
        st.session_state.promotion_df = None
    if 'promotion_results' not in st.session_state:
        st.session_state.promotion_results = None
    if 'include_products' not in st.session_state:
        st.session_state.include_products = ["안마의자", "라클라우드", "정수기"]
    if 'include_services' not in st.session_state:
        st.session_state.include_services = True
    if 'direct_only' not in st.session_state:
        st.session_state.direct_only = False
    if 'criteria' not in st.session_state:
        st.session_state.criteria = ["승인건수"]
    if 'min_condition' not in st.session_state:
        st.session_state.min_condition = 8  # 기본값 8로 설정
    if 'reward_positions' not in st.session_state:
        st.session_state.reward_positions = 16  # 포상 순위 수는 최대 인원수로 설정
    if 'include_all_consultants' not in st.session_state:
        st.session_state.include_all_consultants = True
    if 'promotion_type' not in st.session_state:
        st.session_state.promotion_type = "포상금"
    if 'date_range' not in st.session_state:
        st.session_state.date_range = None
    if 'date_range_option' not in st.session_state:
        st.session_state.date_range_option = "전체 기간"
    # 상담사 조직 초기값 설정
    if 'consultant_org' not in st.session_state:
        st.session_state.consultant_org = "CRM파트"
    # 추첨권 방식 설정
    if 'lottery_method' not in st.session_state:
        st.session_state.lottery_method = "product_weight"  # 기본값은 제품별 가중치 방식
    if 'lottery_count_config' not in st.session_state:
        # 기본 승인 건수 기반 추첨권 설정
        st.session_state.lottery_count_config = [
            {"min_count": 2, "tickets": 1},
            {"min_count": 5, "tickets": 2},
            {"min_count": 10, "tickets": 3}
        ]
    
    # 새로운 포상금 설정 구조 (기존 reward_amounts 대신 reward_config 사용)
    if 'reward_config' not in st.session_state:
        # 기본 포상금 설정
        st.session_state.reward_config = [
            {"amount": 150000, "count": 2},  # 1~2등
            {"amount": 100000, "count": 4},  # 3~6등
            {"amount": 50000, "count": 3},   # 7~9등
            {"amount": 30000, "count": 4},   # 10~13등
            {"amount": 10000, "count": 3}    # 14~16등
        ]
    
    # 추첨권 가중치 설정
    if 'lottery_weights' not in st.session_state:
        st.session_state.lottery_weights = {"안마의자": 3, "라클라우드": 2, "정수기": 1, "더케어": 1, "멤버십": 1}
    
    # 제품별 추첨권 가중치 항목 리스트 초기화
    if 'product_weight_items' not in st.session_state:
        st.session_state.product_weight_items = [
            {"product": product, "weight": weight}
            for product, weight in st.session_state.lottery_weights.items()
            if weight > 0
        ]
    
    # 자동 저장된 설정이 있으면 불러오기 (최초 1회)
    if 'auto_save_loaded' not in st.session_state:
        st.session_state.auto_save_loaded = True
        # 자동 저장된 설정 불러오기
        load_auto_saved_settings()
    
    # 상담사 명단 불러오기
    consultants_data = load_consultants_data()
    
    # 파일 업로드 UI
    st.markdown('<div class="promotion-card">', unsafe_allow_html=True)
    st.subheader("데이터 파일 업로드")
    
    uploaded_file = st.file_uploader(
        "상담주문내역 엑셀 파일을 업로드하세요", 
        type=['xlsx', 'xls'],
        key="promotion_file_uploader"
    )
    
    # 업로드된 파일 처리
    if uploaded_file is not None:
        with st.spinner("파일 처리 중..."):
            df, error = process_promotion_file(uploaded_file)
            
            if error:
                st.error(error)
            else:
                # 세션 상태에 데이터프레임 저장
                st.session_state.promotion_df = df
                
                # 데이터 로드 성공 시 날짜 범위 설정
                if "주문 일자" in df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(df["주문 일자"]):
                        df["주문 일자"] = pd.to_datetime(df["주문 일자"], errors='coerce')
                    
                    # 유효한 날짜만 추출
                    valid_dates = df["주문 일자"].dropna()
                    if not valid_dates.empty:
                        min_date = valid_dates.min().date()
                        max_date = valid_dates.max().date()
                        
                        # 기본 날짜 범위 설정 (전체 데이터)
                        if st.session_state.date_range is None:
                            st.session_state.date_range = (min_date, max_date)
                
                st.success(f"파일 로드 완료! 총 {len(df)}개의 레코드가 처리되었습니다.")
                
                # 상담사 조직 목록 가져오기 (있는 경우)
                if "상담사 조직" in df.columns:
                    organizations = df["상담사 조직"].dropna().unique().tolist()
                    # 조직명 표준화
                    standardized_orgs = [ORG_MAPPING.get(org, org) for org in organizations]
                    # 기본값인 "CRM파트"가 목록에 없는 경우 추가
                    if "CRM파트" not in standardized_orgs:
                        standardized_orgs.append("CRM파트")
                    # 세션 상태에 조직 목록 저장
                    st.session_state.consultant_organizations = standardized_orgs
    
    st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 프로모션 설정 UI
    st.markdown('<div class="settings-card">', unsafe_allow_html=True)
    st.subheader("프로모션 설정")
    
    # 프로모션 유형 선택
    st.markdown("#### 프로모션 유형")
    promotion_type = st.radio(
        "프로모션 유형 선택",
        options=["포상금", "추첨권"],
        index=0 if st.session_state.promotion_type == "포상금" else 1,
        key="promotion_type_radio"
    )
    st.session_state.promotion_type = promotion_type
    
    # 날짜 범위 선택
    if st.session_state.promotion_df is not None and "주문 일자" in st.session_state.promotion_df.columns:
        st.markdown("#### 날짜 범위 선택")
        
        # 유효한 날짜 추출
        valid_dates = st.session_state.promotion_df["주문 일자"].dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            
            # 날짜 범위 옵션
            date_range_options = [
                "전체 기간", 
                "최근 7일", 
                "최근 30일", 
                "최근 90일", 
                "이번 달", 
                "지난 달", 
                "이번 분기", 
                "지난 분기", 
                "올해", 
                "작년", 
                "사용자 정의"
            ]
            
            # 날짜 범위 선택 위젯
            date_range_option = st.selectbox(
                "날짜 범위 옵션",
                options=date_range_options,
                index=date_range_options.index(st.session_state.date_range_option) if st.session_state.date_range_option in date_range_options else 0,
                key="date_range_option_select"
            )
            
            # 세션 상태에 저장
            st.session_state.date_range_option = date_range_option
            
            # 사용자 정의 선택 시 날짜 입력 필드 표시
            if date_range_option == "사용자 정의":
                # 초기 날짜 값 설정 (안전하게 처리)
                default_start = min_date
                default_end = max_date
                
                if st.session_state.date_range:
                    try:
                        # session_state에 저장된 값이 tuple이나 list인지 확인
                        if isinstance(st.session_state.date_range, (tuple, list)) and len(st.session_state.date_range) == 2:
                            # 각 요소가 date 객체인지 확인
                            if hasattr(st.session_state.date_range[0], 'strftime') and hasattr(st.session_state.date_range[1], 'strftime'):
                                default_start = st.session_state.date_range[0]
                                default_end = st.session_state.date_range[1]
                    except:
                        # 오류 발생 시 기본값 사용
                        pass
                
                # 날짜 선택 위젯 (2열 레이아웃)
                date_cols = st.columns(2)
                with date_cols[0]:
                    start_date = st.date_input(
                        "시작일",
                        value=default_start,
                        min_value=min_date,
                        max_value=max_date,
                        key="start_date_picker"
                    )
                
                with date_cols[1]:
                    end_date = st.date_input(
                        "종료일", 
                        value=default_end,
                        min_value=min_date,
                        max_value=max_date,
                        key="end_date_picker"
                    )
                
                # 선택된 날짜를 session_state에 저장
                st.session_state.date_range = (start_date, end_date)
            else:
                # 선택된 옵션에 따른 날짜 범위 계산
                date_range = get_date_range(date_range_option, min_date, max_date)
                st.session_state.date_range = date_range
                
                # 선택된 날짜 범위 표시
                st.info(f"선택된 날짜 범위: {date_range[0]} ~ {date_range[1]}")
    
    # 설정 섹션 - 2열 레이아웃
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="settings-section">', unsafe_allow_html=True)
        st.markdown("#### 대상 품목 선택")
        
        # 대상 품목 선택 (다중 선택)
        include_products = st.multiselect(
            "포함할 제품",
            options=["안마의자", "라클라우드", "정수기"],
            default=st.session_state.include_products,
            key="products_select"
        )
        
        # 서비스 품목 포함 여부
        include_services = st.checkbox(
            "서비스 품목 포함 (더케어, 멤버십)",
            value=st.session_state.include_services,
            key="services_checkbox"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="settings-section">', unsafe_allow_html=True)
        st.markdown("#### 판매 경로 및 조직 설정")
        
        # 직접/연계 포함 여부
        direct_only = st.checkbox(
            "직접 판매만 포함 (CRM 판매인입경로)",
            value=st.session_state.direct_only,
            key="direct_checkbox"
        )
        
        # 모든 상담사 포함 여부
        include_all_consultants = st.checkbox(
            "모든 상담사 포함 (승인없는 상담사 포함)",
            value=st.session_state.include_all_consultants,
            key="include_all_consultants_checkbox"
        )
        st.session_state.include_all_consultants = include_all_consultants
        
        # 상담사 조직 선택 (파일이 로드되었을 때 또는 JSON 명단이 있을 때)
        if consultants_data:
            # JSON 파일에서 불러온 조직 목록 사용
            org_options = list(consultants_data.keys())
            
            # 상담사 조직 선택 (기본값은 "CRM파트")
            default_idx = 0  # 기본값은 첫 번째 항목
            if "CRM파트" in org_options:
                default_idx = org_options.index("CRM파트")
                
            consultant_org = st.selectbox(
                "상담사 조직 선택",
                options=["전체"] + org_options,
                index=default_idx + 1,  # 첫 번째 항목은 "전체"
                key="consultant_org_select"
            )
            
            # 선택된 조직을 session_state에 저장
            st.session_state.consultant_org = consultant_org
        
        elif st.session_state.promotion_df is not None and "상담사 조직" in st.session_state.promotion_df.columns:
            # 데이터프레임에서 조직 목록 추출
            if 'consultant_organizations' in st.session_state:
                # 조직 목록이 있으면 사용
                org_options = st.session_state.consultant_organizations
            else:
                # 아니면 데이터프레임에서 추출하고 표준화
                orgs = st.session_state.promotion_df["상담사 조직"].dropna().unique().tolist()
                org_options = [ORG_MAPPING.get(org, org) for org in orgs]
                
                # "CRM파트"가 없으면 추가
                if "CRM파트" not in org_options:
                    org_options = ["CRM파트"] + org_options
            
            # 선택된 조직이 표준화된 이름인지 확인
            selected_org = st.session_state.consultant_org
            std_selected_org = ORG_MAPPING.get(selected_org, selected_org)
            
            # 표준화된 조직명으로 인덱스 찾기
            default_idx = 0
            if std_selected_org in org_options:
                default_idx = org_options.index(std_selected_org)
            
            # 상담사 조직 선택
            consultant_org = st.selectbox(
                "상담사 조직 선택",
                options=["전체"] + org_options,
                index=default_idx + 1,  # 첫 번째 항목은 "전체"
                key="consultant_org_select"
            )
            
            # 선택된 조직을 session_state에 저장
            st.session_state.consultant_org = consultant_org
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="settings-section">', unsafe_allow_html=True)
        st.markdown("#### 기준 설정")
        
        # 기준 선택 (다중 선택)
        criteria_options = ["승인건수", "승인액"]
        if st.session_state.promotion_type == "추첨권":
            criteria_options.append("추첨권")
            
        criteria = st.multiselect(
            "순위 기준 (동률 시 2차 기준으로 승인액 사용)",
            options=criteria_options,
            default=st.session_state.criteria,
            key="criteria_select"
        )
        
        # 최소 조건
        min_condition = st.number_input(
            "포상 최소 건수 조건 (이 이상만 포상 대상)",
            min_value=0,
            value=st.session_state.min_condition,
            step=1,
            key="min_condition_input"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 프로모션 유형별 추가 설정
    if st.session_state.promotion_type == "포상금":
        st.markdown("#### 등수별 포상금액 설정")
        
        # 동적으로 포상금 설정 관리를 위한 컨테이너
        reward_config_container = st.container()
        
        with reward_config_container:
            # 기존 포상금 설정 표시
            for i, config in enumerate(st.session_state.reward_config):
                cols = st.columns([3, 2, 1])
                with cols[0]:
                    amount = st.number_input(
                        "포상금액",
                        min_value=0,
                        value=config["amount"],
                        step=10000,
                        key=f"reward_amount_{i}"
                    )
                
                with cols[1]:
                    count = st.number_input(
                        "인원수",
                        min_value=1,
                        value=config["count"],
                        step=1,
                        key=f"reward_count_{i}"
                    )
                
                with cols[2]:
                    # 삭제 버튼 (첫 번째 항목은 삭제 불가능하게 할 수도 있음)
                    if st.button("삭제", key=f"delete_reward_{i}"):
                        st.session_state.reward_config.pop(i)
                        st.rerun()
                
                # 설정 업데이트
                st.session_state.reward_config[i]["amount"] = amount
                st.session_state.reward_config[i]["count"] = count
            
            # 새 포상금 설정 추가 버튼
            if st.button("+ 포상금 설정 추가", key="add_reward_btn"):
                st.session_state.reward_config.append({"amount": 50000, "count": 1})
                st.rerun()
            
            # 설정 저장/불러오기
            st.markdown("### 설정 저장/불러오기")
            
            config_cols = st.columns([3, 2, 2])
            
            with config_cols[0]:
                config_name = st.text_input("설정 이름", key="reward_config_name")
            
            with config_cols[1]:
                if st.button("저장", key="save_reward_config"):
                    if not config_name:
                        st.error("설정 이름을 입력하세요.")
                    else:
                        # 설정 저장
                        config_data = {
                            "type": "reward",
                            "data": st.session_state.reward_config,
                            "settings": {
                                "promotion_type": st.session_state.promotion_type,
                                "include_products": st.session_state.include_products,
                                "include_services": st.session_state.include_services,
                                "direct_only": st.session_state.direct_only,
                                "criteria": st.session_state.criteria,
                                "min_condition": st.session_state.min_condition,
                                "include_all_consultants": st.session_state.include_all_consultants,
                                "date_range_option": st.session_state.date_range_option
                            }
                        }
                        success, error = save_promotion_config(config_name, config_data)
                        if success:
                            st.success(f"'{config_name}' 설정이 저장되었습니다.")
                        else:
                            st.error(f"설정 저장 실패: {error}")
            
            with config_cols[2]:
                # 설정 목록 불러오기
                config_list = list_promotion_configs()
                selected_config = st.selectbox(
                    "설정 불러오기",
                    options=[""] + config_list,
                    key="load_reward_config"
                )
                
                if selected_config:
                    # 선택된 설정 불러오기
                    config_data, error = load_promotion_config(selected_config)
                    if error:
                        st.error(f"설정 불러오기 실패: {error}")
                    elif config_data and config_data.get("type") == "reward":
                        st.session_state.reward_config = config_data.get("data", [])
                        
                        # 설정 불러오기
                        settings = config_data.get("settings", {})
                        
                        if "include_products" in settings:
                            st.session_state.include_products = settings["include_products"]
                        if "include_services" in settings:
                            st.session_state.include_services = settings["include_services"]
                        if "direct_only" in settings:
                            st.session_state.direct_only = settings["direct_only"]
                        if "criteria" in settings:
                            st.session_state.criteria = settings["criteria"]
                        if "min_condition" in settings:
                            st.session_state.min_condition = settings["min_condition"]
                        if "include_all_consultants" in settings:
                            st.session_state.include_all_consultants = settings["include_all_consultants"]
                        if "date_range_option" in settings:
                            st.session_state.date_range_option = settings["date_range_option"]
                        
                        st.success(f"'{selected_config}' 설정을 불러왔습니다.")
                        st.rerun()
                    else:
                        st.error("선택한 설정이 포상금 설정이 아닙니다.")
    
    elif st.session_state.promotion_type == "추첨권":
        st.markdown("#### 추첨권 계산 방식 선택")
        
        # 추첨권 계산 방식 선택
        lottery_method = st.radio(
            "추첨권 계산 방식",
            options=["제품별 가중치 방식", "승인 건수 기반 방식"],
            index=0 if st.session_state.lottery_method == "product_weight" else 1,
            key="lottery_method_radio"
        )
        
        # 세션 상태에 계산 방식 저장
        st.session_state.lottery_method = "product_weight" if lottery_method == "제품별 가중치 방식" else "approval_count"
        
        # 선택된 방식에 따라 다른 UI 표시
        if st.session_state.lottery_method == "product_weight":
            st.markdown("#### 제품별 추첨권 가중치 설정")
            
            # 초기 제품 목록
            available_products = ["안마의자", "라클라우드", "정수기", "더케어", "멤버십"]
            
            # 세션 상태에 제품 가중치 목록이 없으면 초기화
            if 'product_weight_items' not in st.session_state:
                # 기존 lottery_weights에서 값을 가져와 초기화
                st.session_state.product_weight_items = [
                    {"product": product, "weight": st.session_state.lottery_weights.get(product, 0)}
                    for product in available_products
                    if st.session_state.lottery_weights.get(product, 0) > 0
                ]
                # 기존 항목이 없는 경우 기본 항목 추가
                if not st.session_state.product_weight_items:
                    st.session_state.product_weight_items = [
                        {"product": "안마의자", "weight": 3},
                        {"product": "라클라우드", "weight": 2},
                        {"product": "정수기", "weight": 1}
                    ]
            
            # 제품 가중치 추가 UI
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                new_product = st.selectbox(
                    "제품 선택",
                    options=available_products,
                    key="new_product_select"
                )
            
            with col2:
                new_weight = st.number_input(
                    "가중치",
                    min_value=0,
                    value=1,
                    step=1,
                    key="new_weight_input"
                )
            
            with col3:
                if st.button("추가", key="add_product_weight_btn"):
                    # 이미 있는 제품인지 확인
                    exists = False
                    for item in st.session_state.product_weight_items:
                        if item["product"] == new_product:
                            item["weight"] = new_weight  # 기존 제품이면 가중치 업데이트
                            exists = True
                            break
                    
                    # 새 제품이면 추가
                    if not exists:
                        st.session_state.product_weight_items.append({
                            "product": new_product,
                            "weight": new_weight
                        })
                    
                    # lottery_weights 업데이트
                    st.session_state.lottery_weights = {
                        item["product"]: item["weight"] 
                        for item in st.session_state.product_weight_items
                    }
                    
                    st.rerun()
            
            # 현재 설정된 제품별 가중치 목록
            st.markdown("##### 현재 설정된 제품별 가중치")
            for i, item in enumerate(st.session_state.product_weight_items):
                cols = st.columns([3, 2, 1])
                
                with cols[0]:
                    st.text(f"제품: {item['product']}")
                
                with cols[1]:
                    # 편집 가능한 가중치
                    updated_weight = st.number_input(
                        "가중치",
                        min_value=0,
                        value=item["weight"],
                        step=1,
                        key=f"weight_edit_{i}"
                    )
                    # 가중치 업데이트
                    st.session_state.product_weight_items[i]["weight"] = updated_weight
                
                with cols[2]:
                    if st.button("삭제", key=f"delete_product_{i}"):
                        # 항목 삭제
                        st.session_state.product_weight_items.pop(i)
                        # lottery_weights 업데이트
                        st.session_state.lottery_weights = {
                            item["product"]: item["weight"] 
                            for item in st.session_state.product_weight_items
                        }
                        st.rerun()
            
            # 모든 가중치 변경사항을 lottery_weights에 반영
            st.session_state.lottery_weights = {
                item["product"]: item["weight"] 
                for item in st.session_state.product_weight_items
            }
            
        else:  # 승인 건수 기반 방식
            st.markdown("#### 승인 건수 기반 추첨권 설정")
            st.markdown("총 승인 건수에 따라 추첨권을 부여하는 설정입니다. 상담사의 총 승인 건수가 기준을 충족하면 설정한 추첨권 수가 부여됩니다.")
            
            # 승인 건수 기준 추가 UI
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                new_min_count = st.number_input(
                    "최소 승인 건수",
                    min_value=1,
                    value=2,
                    step=1,
                    key="new_min_count_input"
                )
            
            with col2:
                new_tickets = st.number_input(
                    "추첨권 수",
                    min_value=1,
                    value=1,
                    step=1,
                    key="new_tickets_input"
                )
            
            with col3:
                if st.button("추가", key="add_count_criteria_btn"):
                    # 새 기준 추가
                    if 'lottery_count_config' not in st.session_state:
                        st.session_state.lottery_count_config = []
                    
                    # 이미 있는 기준인지 확인
                    exists = False
                    for i, config in enumerate(st.session_state.lottery_count_config):
                        if config["min_count"] == new_min_count:
                            # 기존 기준이면 업데이트
                            st.session_state.lottery_count_config[i]["tickets"] = new_tickets
                            exists = True
                            break
                    
                    # 새 기준이면 추가
                    if not exists:
                        st.session_state.lottery_count_config.append({
                            "min_count": new_min_count,
                            "tickets": new_tickets
                        })
                    
                    # 기준을 오름차순으로 정렬
                    st.session_state.lottery_count_config = sorted(
                        st.session_state.lottery_count_config,
                        key=lambda x: x["min_count"]
                    )
                    
                    st.rerun()
            
            # 기존 승인 건수 기반 추첨권 설정 표시
            st.markdown("##### 현재 설정된 승인 건수 기준")
            if not st.session_state.lottery_count_config:
                st.info("설정된 기준이 없습니다. 위에서 기준을 추가하세요.")
            else:
                for i, config in enumerate(st.session_state.lottery_count_config):
                    cols = st.columns([3, 2, 1])
                    
                    with cols[0]:
                        # 최소 승인 건수 표시 (편집 가능)
                        updated_min_count = st.number_input(
                            "최소 승인 건수",
                            min_value=1,
                            value=config["min_count"],
                            step=1,
                            key=f"min_count_edit_{i}"
                        )
                        st.session_state.lottery_count_config[i]["min_count"] = updated_min_count
                    
                    with cols[1]:
                        # 추첨권 수 표시 (편집 가능)
                        updated_tickets = st.number_input(
                            "추첨권 수",
                            min_value=0,
                            value=config["tickets"],
                            step=1,
                            key=f"tickets_edit_{i}"
                        )
                        st.session_state.lottery_count_config[i]["tickets"] = updated_tickets
                    
                    with cols[2]:
                        # 삭제 버튼
                        if st.button("삭제", key=f"delete_count_config_{i}"):
                            st.session_state.lottery_count_config.pop(i)
                            st.rerun()
            
            # 설정을 오름차순으로 정렬
            if st.session_state.lottery_count_config:
                st.session_state.lottery_count_config = sorted(
                    st.session_state.lottery_count_config,
                    key=lambda x: x["min_count"]
                )
            
            # 기준 적용 방식 설명
            st.markdown("""
            ##### 적용 방식 설명
            - 상담사의 총 승인 건수가 기준을 충족하면 해당 추첨권 수가 부여됩니다.
            - 여러 기준을 충족하는 경우, 가장 높은 추첨권 수만 적용됩니다.
            - 예) 총 승인 건수가 7건인 경우:
              - 2건 이상 → 1개 추첨권
              - 5건 이상 → 2개 추첨권
              - 최종적으로 **2개 추첨권**이 부여됩니다.
            """)
        
        # 설정 저장/불러오기
        st.markdown("### 설정 저장/불러오기")
        
        config_cols = st.columns([3, 2, 2])
        
        with config_cols[0]:
            config_name = st.text_input("설정 이름", key="lottery_config_name")
        
        with config_cols[1]:
            if st.button("저장", key="save_lottery_config"):
                if not config_name:
                    st.error("설정 이름을 입력하세요.")
                else:
                    # 설정 저장
                    config_data = {
                        "type": "lottery",
                        "data": st.session_state.lottery_weights,
                        "lottery_method": st.session_state.lottery_method,
                        "lottery_count_config": st.session_state.lottery_count_config if st.session_state.lottery_method == "approval_count" else [],
                        "settings": {
                            "promotion_type": st.session_state.promotion_type,
                            "include_products": st.session_state.include_products,
                            "include_services": st.session_state.include_services,
                            "direct_only": st.session_state.direct_only,
                            "criteria": st.session_state.criteria,
                            "min_condition": st.session_state.min_condition,
                            "include_all_consultants": st.session_state.include_all_consultants,
                            "date_range_option": st.session_state.date_range_option
                        }
                    }
                    success, error = save_promotion_config(config_name, config_data)
                    if success:
                        st.success(f"'{config_name}' 설정이 저장되었습니다.")
                    else:
                        st.error(f"설정 저장 실패: {error}")
        
        with config_cols[2]:
            # 설정 목록 불러오기
            config_list = list_promotion_configs()
            selected_config = st.selectbox(
                "설정 불러오기",
                options=[""] + config_list,
                key="load_lottery_config"
            )
            
            if selected_config:
                # 선택된 설정 불러오기
                config_data, error = load_promotion_config(selected_config)
                if error:
                    st.error(f"설정 불러오기 실패: {error}")
                elif config_data and config_data.get("type") == "lottery":
                    st.session_state.lottery_weights = config_data.get("data", {})
                    
                    # 추첨권 방식 불러오기
                    if "lottery_method" in config_data:
                        st.session_state.lottery_method = config_data["lottery_method"]
                    # 승인 건수 기반 추첨권 설정 불러오기
                    if "lottery_count_config" in config_data:
                        st.session_state.lottery_count_config = config_data["lottery_count_config"]
                    
                    # 제품 가중치 항목 다시 초기화
                    if st.session_state.lottery_method == "product_weight":
                        st.session_state.product_weight_items = [
                            {"product": product, "weight": weight}
                            for product, weight in st.session_state.lottery_weights.items()
                            if weight > 0
                        ]
                    
                    # 설정 불러오기
                    settings = config_data.get("settings", {})
                    
                    if "include_products" in settings:
                        st.session_state.include_products = settings["include_products"]
                    if "include_services" in settings:
                        st.session_state.include_services = settings["include_services"]
                    if "direct_only" in settings:
                        st.session_state.direct_only = settings["direct_only"]
                    if "criteria" in settings:
                        st.session_state.criteria = settings["criteria"]
                    if "min_condition" in settings:
                        st.session_state.min_condition = settings["min_condition"]
                    if "include_all_consultants" in settings:
                        st.session_state.include_all_consultants = settings["include_all_consultants"]
                    if "date_range_option" in settings:
                        st.session_state.date_range_option = settings["date_range_option"]
                    
                    st.success(f"'{selected_config}' 설정을 불러왔습니다.")
                    st.rerun()
                else:
                    st.error("선택한 설정이 추첨권 설정이 아닙니다.")
    
    # 설정 적용 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        apply_button = st.button(
            "설정 적용",
            key="apply_settings_button",
            use_container_width=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 설정 적용 및 결과 표시
    if apply_button and (st.session_state.promotion_df is not None or consultants_data):
        # 세션 상태 업데이트
        st.session_state.include_products = include_products
        st.session_state.include_services = include_services
        st.session_state.direct_only = direct_only
        st.session_state.criteria = criteria
        st.session_state.min_condition = min_condition
        
        # 자동 저장
        auto_save_settings()
        
        # 대상 품목이 최소 하나는 선택되어야 함
        if not include_products:
            st.error("최소한 하나 이상의 제품을 선택해야 합니다.")
        # 순위 기준이 최소 하나는 선택되어야 함
        elif not criteria:
            st.error("최소한 하나 이상의 순위 기준을 선택해야 합니다.")
        # 승인 건수 기반 추첨권 설정 유효성 검증
        elif st.session_state.promotion_type == "추첨권" and st.session_state.lottery_method == "approval_count" and not st.session_state.lottery_count_config:
            st.error("승인 건수 기반 추첨권 설정을 하나 이상 추가하세요.")
        else:
            with st.spinner("프로모션 분석 중..."):
                # 기본 데이터프레임 설정
                filtered_df = None
                if st.session_state.promotion_df is not None:
                    filtered_df = st.session_state.promotion_df.copy()
                
                # 선택된 조직명 표준화
                selected_org = st.session_state.consultant_org
                std_selected_org = ORG_MAPPING.get(selected_org, selected_org)
                
                # 상담사 목록 준비
                all_consultants = []
                
                # 선택된 조직의 상담사 목록 가져오기 (JSON 파일에서)
                if consultants_data:
                    if selected_org == "전체":
                        # 모든 조직의 상담사 목록
                        for org, consultants in consultants_data.items():
                            all_consultants.extend(consultants)
                    elif std_selected_org in consultants_data:
                        # 선택한 조직의 상담사 목록
                        all_consultants = consultants_data[std_selected_org]
                    # 표준화된 조직명으로도 확인
                    elif selected_org in consultants_data:
                        all_consultants = consultants_data[selected_org]
                
                # 상담사 조직 필터링 적용 (데이터프레임 기준)
                if filtered_df is not None and "상담사 조직" in filtered_df.columns and selected_org != "전체":
                    # 데이터프레임에서 조직명을 표준화하여 필터링
                    org_data = filtered_df["상담사 조직"].copy()
                    # 조직명 매핑 적용
                    org_data = org_data.apply(lambda x: ORG_MAPPING.get(x, x) if isinstance(x, str) else x)
                    
                    # 표준화된 조직명으로 필터링
                    filtered_df = filtered_df[org_data == std_selected_org]
                
                # 날짜 범위 변환
                start_date = None
                end_date = None
                if st.session_state.date_range:
                    start_date = pd.Timestamp(st.session_state.date_range[0])
                    end_date = pd.Timestamp(st.session_state.date_range[1])
                    # 종료일은 23:59:59로 설정하여 해당 일의 모든 데이터 포함
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                
                # 포상 순위 수 계산 (모든 설정의 인원수 합계)
                reward_positions = sum(config["count"] for config in st.session_state.reward_config)
                st.session_state.reward_positions = reward_positions
                
                # 분석 시 최소 조건은 0으로 설정하여 모든 상담사가 포함되도록 함
                analysis_min_condition = 0
                
                # 프로모션 분석 실행 (최소 조건 0으로 설정)
                results_df, error = analyze_promotion_data(
                    filtered_df,
                    include_products,
                    include_services,
                    direct_only,
                    criteria,
                    analysis_min_condition,  # 최소 조건 0으로 설정
                    reward_positions,
                    start_date,
                    end_date,
                    st.session_state.promotion_type,
                    st.session_state.reward_config if st.session_state.promotion_type == "포상금" else None,
                    st.session_state.lottery_weights if st.session_state.promotion_type == "추첨권" else None
                )
                
                if error:
                    st.error(error)
                    # 오류가 있지만 상담사 명단이 있는 경우, 빈 결과라도 생성
                    if st.session_state.include_all_consultants and all_consultants:
                        # 빈 데이터프레임 생성
                        results_df = create_empty_consultant_dataframe(all_consultants)
                else:
                    # 모든 상담사를 포함하도록 결과 데이터프레임 수정
                    if st.session_state.include_all_consultants and all_consultants:
                        results_df = modify_dataframe_to_include_all_consultants(results_df, all_consultants)
                    
                    # 승인 건수 기반 추첨권 방식인 경우, 추첨권 재계산
                    if st.session_state.promotion_type == "추첨권" and st.session_state.lottery_method == "approval_count":
                        results_df = calculate_tickets_by_count(results_df, st.session_state.lottery_count_config)
                    
                    # 동률 처리 (승인건수 기준 동률일 경우 승인액으로 정렬)
                    results_df = get_sorted_results(results_df, criteria)
                    
                    # 결과 후처리 (기준 미충족 상담사에 대한 표시 추가)
                    results_df = post_process_results(
                        results_df,
                        st.session_state.reward_config,
                        min_condition,  # 사용자가 설정한 최소 조건
                        st.session_state.promotion_type,
                        st.session_state.lottery_method,
                        st.session_state.lottery_count_config
                    )
                    
                    # 세션 상태에 결과 저장
                    st.session_state.promotion_results = results_df
                    st.success("프로모션 분석이 완료되었습니다!")
    
    # 결과 표시
    if st.session_state.promotion_results is not None:
        st.markdown('<div class="results-card">', unsafe_allow_html=True)
        st.subheader("프로모션 결과")
        
        # 현재 설정 요약 표시
        current_settings = []
        current_settings.append(f"프로모션 유형: {st.session_state.promotion_type}")
        if st.session_state.date_range:
            # 날짜 옵션도 표시
            current_settings.append(f"날짜 범위: {st.session_state.date_range_option} ({st.session_state.date_range[0]} ~ {st.session_state.date_range[1]})")
        current_settings.append(f"대상 품목: {', '.join(st.session_state.include_products)}")
        current_settings.append(f"서비스 품목 포함: {'예' if st.session_state.include_services else '아니오'}")
        current_settings.append(f"직접 판매만: {'예' if st.session_state.direct_only else '아니오'}")
        current_settings.append(f"모든 상담사 포함: {'예' if st.session_state.include_all_consultants else '아니오'}")
        current_settings.append(f"상담사 조직: {st.session_state.consultant_org}")
        
        # 1차/2차 기준 정보 표시
        primary_criteria = st.session_state.criteria.copy()
        if "승인건수" in primary_criteria and "승인액" not in primary_criteria:
            secondary_criteria = ["승인액"]
            criteria_str = f"1차 기준: {', '.join(primary_criteria)}, 2차 기준: {', '.join(secondary_criteria)}"
        else:
            criteria_str = f"기준: {', '.join(primary_criteria)}"
        
        current_settings.append(criteria_str)
        current_settings.append(f"포상 최소 건수 조건: {st.session_state.min_condition}")
        
        if st.session_state.promotion_type == "포상금":
            # 포상금 설정 요약
            positions = 1
            reward_summary = []
            for config in st.session_state.reward_config:
                amount = config["amount"]
                count = config["count"]
                end_position = positions + count - 1
                range_str = f"{positions}~{end_position}등" if count > 1 else f"{positions}등"
                reward_summary.append(f"{range_str}: {amount:,}원 ({count}명)")
                positions += count
                
            current_settings.append(f"포상금 설정: {', '.join(reward_summary)}")
        else:  # 추첨권
            # 추첨권 방식에 따라 다른 설명
            if st.session_state.lottery_method == "product_weight":
                current_settings.append(f"추첨권 방식: 제품별 가중치")
                current_settings.append(f"제품별 추첨권 가중치: {', '.join([f'{k}: {v}' for k, v in st.session_state.lottery_weights.items() if v > 0])}")
            else:  # approval_count
                current_settings.append(f"추첨권 방식: 승인 건수 기반")
                count_summary = []
                for config in sorted(st.session_state.lottery_count_config, key=lambda x: x["min_count"]):
                    count_summary.append(f"{config['min_count']}건 이상: {config['tickets']}개")
                current_settings.append(f"승인 건수별 추첨권: {', '.join(count_summary)}")
        
        with st.expander("현재 설정 보기", expanded=False):
            for setting in current_settings:
                st.write(setting)
        
        # 표 형식으로 결과 표시
        st.dataframe(
            st.session_state.promotion_results,
            use_container_width=True,
            hide_index=True
        )
        
        # 엑셀 다운로드 버튼
        st.markdown(DOWNLOAD_BUTTON_STYLE, unsafe_allow_html=True)
        
        try:
            # 현재 날짜와 UUID 생성
            today = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:4]  # UUID 앞 4자리만 사용
            file_prefix = f"{today}_{unique_id}_"
            
            # 엑셀 파일 생성
            excel_data = create_excel_report(
                st.session_state.promotion_results,
                st.session_state.promotion_df
            )
            
            if excel_data:
                # 다운로드 링크 생성
                b64 = base64.b64encode(excel_data).decode()
                href = f'<div class="download-button-container"><a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{file_prefix}상담사_프로모션결과.xlsx" class="download-button">엑셀 다운로드 (2시트)</a></div>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.error("엑셀 파일 생성에 실패했습니다.")
                
                # CSV 대체 다운로드 제공
                csv_data = st.session_state.promotion_results.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="CSV 다운로드 (결과만)",
                    data=csv_data,
                    file_name=f"{file_prefix}상담사_프로모션결과.csv", 
                    mime="text/csv",
                    key="csv_download_button"
                )
        except Exception as e:
            st.error(f"엑셀 파일 다운로드 준비 중 오류가 발생했습니다: {str(e)}")
            
            # CSV 다운로드 버튼 제공
            try:
                csv_data = st.session_state.promotion_results.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="CSV 다운로드 (결과만)",
                    data=csv_data,
                    file_name=f"{today}_{unique_id}_상담사_프로모션결과.csv", 
                    mime="text/csv"
                )
            except Exception as csv_error:
                st.error(f"CSV 다운로드 준비 중에도 오류가 발생했습니다: {str(csv_error)}")
        
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 파일이 업로드되지 않았을 때 안내 정보
    elif st.session_state.promotion_df is None and not consultants_data:
        st.info("상담주문내역 엑셀 파일을 업로드하고 프로모션 설정을 적용하세요.")
        st.markdown(USAGE_GUIDE_MARKDOWN)