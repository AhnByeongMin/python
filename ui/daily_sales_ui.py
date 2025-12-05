"""
일일 매출 현황 UI 모듈 - 엑셀 내보내기 기능 업데이트

이 모듈은 일일 매출 현황 탭의 UI 요소와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Optional, Any, Tuple
import json
import os

# 비즈니스 로직 가져오기
from logic.daily_sales_logic import (
    process_approval_file, process_installation_file,
    analyze_sales_data, create_excel_report, analyze_daily_approval_by_date
)

# CSS 스타일 가져오기
from styles.daily_sales_styles import (
    DAILY_SALES_TAB_STYLE, DOWNLOAD_BUTTON_STYLE,
    USAGE_GUIDE_MARKDOWN, DARK_TABLE_STYLE
)

# 유틸리티 함수 가져오기
from utils.utils import format_time
from utils.db_manager import get_db_manager

def show():
    """일일 매출 현황 탭 UI를 표시하는 메인 함수"""
    
    # CSS 스타일 적용
    st.markdown(DAILY_SALES_TAB_STYLE, unsafe_allow_html=True)
    st.markdown(DARK_TABLE_STYLE, unsafe_allow_html=True)
    
    # 타이틀 및 설명
    st.title("📈 일일 매출 현황")
    st.markdown('<p>이 도구는 승인매출과 설치매출 데이터를 분석하여 일일 매출 현황을 보여줍니다. 판매인입경로와 캠페인 유형에 따라 매출을 분류합니다.</p>', unsafe_allow_html=True)
    
    # 파일에서 목표 값 로드 (앱 시작 시)
    targets = load_targets_from_file()
    
    # 세션 상태 초기화 - 한 번만 실행되도록 최적화
    session_defaults = {
        'daily_approval_df': None,
        'daily_installation_df': None,
        'cumulative_approval': None,
        'daily_approval': None,
        'cumulative_installation': None,
        'latest_date': None,
        'available_dates': [],
        'selected_date': None,
        'selected_date_str': None,
        'direct_target': targets['direct_target'],
        'affiliate_target': targets['affiliate_target'],
        'last_uploaded_files': None,  # 마지막 업로드된 파일 추적
        'processing': False  # 처리 중 상태 플래그
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # 이하 기존 코드...

    # 파일 업로드 UI
    st.markdown('<div class="material-card upload-card">', unsafe_allow_html=True)
    st.subheader("데이터 파일 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 승인매출 파일 첨부")
        # 다중 파일 업로드 가능하도록 accept_multiple_files=True 추가
        approval_files = st.file_uploader("승인매출 엑셀 파일을 업로드하세요 (여러 파일 선택 가능)", type=['xlsx', 'xls'], key="daily_approval_file", accept_multiple_files=True)

    with col2:
        st.markdown("### 설치매출 파일 첨부")
        # 다중 파일 업로드 가능하도록 accept_multiple_files=True 추가
        installation_files = st.file_uploader("설치매출 엑셀 파일을 업로드하세요 (여러 파일 선택 가능)", type=['xlsx', 'xls'], key="daily_installation_file", accept_multiple_files=True)
    
    # 분석 버튼
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    # 키 이름 변경: analyze_daily_sales -> analyze_daily_button
    analyze_button = st.button("분석 시작", key="analyze_daily_button")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 메인 로직
    if analyze_button and approval_files is not None and len(approval_files) > 0:
        # 처리 중 상태 설정
        st.session_state.processing = True

        # 파일 처리 진행 상태 표시
        with st.spinner('파일 분석 중...'):
            # 업로드된 파일 수 표시
            progress_placeholder = st.empty()
            progress_placeholder.info(f"승인매출 파일 {len(approval_files)}개 처리 중...")

            # 파일 위치 저장을 위해 seek(0)
            for approval_file in approval_files:
                approval_file.seek(0)

            if installation_files is not None and len(installation_files) > 0:
                progress_placeholder.info(f"설치매출 파일 {len(installation_files)}개 처리 중...")
                for installation_file in installation_files:
                    installation_file.seek(0)

            # 파일 처리 시도 - 다중 파일 지원
            progress_placeholder.info("데이터 분석 중... 잠시만 기다려주세요.")
            approval_df, approval_error = process_approval_file(approval_files)

            installation_df = None
            installation_error = None
            if installation_files is not None and len(installation_files) > 0:
                installation_df, installation_error = process_installation_file(installation_files)

            # 진행 상태 메시지 제거
            progress_placeholder.empty()
        
        # 오류 체크
        if approval_error:
            st.session_state.processing = False
            st.error(approval_error)
        elif installation_files is not None and installation_error:
            st.session_state.processing = False
            st.error(installation_error)
        else:
            # 세션 상태에 데이터프레임 저장
            st.session_state.daily_approval_df = approval_df
            st.session_state.daily_installation_df = installation_df
            
            # 분석 실행
            results = analyze_sales_data(approval_df, installation_df)

            if 'error' in results:
                st.session_state.processing = False
                st.error(results['error'])
            else:
                # 세션 상태에 결과 저장
                st.session_state.cumulative_approval = results['cumulative_approval']
                st.session_state.daily_approval = results['daily_approval']
                st.session_state.cumulative_installation = results['cumulative_installation']
                st.session_state.latest_date = results['latest_date']
                
                # 사용 가능한 날짜 목록 가져오기 (주문 일자 기준)
                if '주문 일자' in approval_df.columns:
                    # NaT 제거 후 날짜만 추출하여 고유값 가져오기
                    valid_dates = approval_df['주문 일자'].dropna()
                    if not valid_dates.empty:
                        # datetime 타입 변환
                        valid_dates = pd.to_datetime(valid_dates)
                        # 날짜만 추출하여 중복 제거 및 정렬
                        unique_dates = sorted(valid_dates.dt.date.unique(), reverse=True)
                        st.session_state.available_dates = unique_dates
                        
                        # 기본값으로 최신 날짜 선택
                        if st.session_state.selected_date is None and unique_dates:
                            st.session_state.selected_date = unique_dates[0]
                            st.session_state.selected_date_str = unique_dates[0].strftime("%Y-%m-%d")
                
                # 처리 완료 상태로 변경
                st.session_state.processing = False

                # 결과 표시
                display_results(
                    st.session_state.cumulative_approval,
                    st.session_state.daily_approval,
                    st.session_state.cumulative_installation,
                    st.session_state.latest_date,
                    st.session_state.daily_approval_df,
                    st.session_state.daily_installation_df
                )
    
    # 이미 분석된 결과가 있으면 표시
    elif (
        st.session_state.cumulative_approval is not None and 
        st.session_state.daily_approval is not None
    ):
        display_results(
            st.session_state.cumulative_approval,
            st.session_state.daily_approval,
            st.session_state.cumulative_installation,
            st.session_state.latest_date,
            st.session_state.daily_approval_df,
            st.session_state.daily_installation_df
        )
    else:
        # 파일 업로드 전 안내 화면
        st.markdown('<div class="material-card info-card">', unsafe_allow_html=True)
        st.info("승인매출 파일을 업로드하고(여러 파일 선택 가능) 설치매출 파일(선택사항)도 업로드한 후 분석 시작 버튼을 클릭하세요.")
        st.markdown(USAGE_GUIDE_MARKDOWN, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기

def load_targets_from_file(file_path='targets.json'):
    """
    데이터베이스에서 목표 값을 로드하는 함수 (DB 전환)
    현재 월에 해당하는 목표 값을 반환합니다.

    Args:
        file_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        Dict: 목표 값 딕셔너리 {direct_target, affiliate_target}
    """
    # 현재 월 가져오기
    current_month = datetime.now().month

    # 기본 목표 값 (DB에 데이터가 없을 경우)
    default_target = {
        'direct_target': 630029743,
        'affiliate_target': 433543524
    }

    try:
        db = get_db_manager()
        target = db.get_monthly_target(current_month)

        if target:
            return target
        else:
            # DB에 해당 월 데이터가 없으면 기본값 반환
            print(f"경고: {current_month}월 목표 데이터가 DB에 없습니다. 기본값 사용.")
            return default_target

    except Exception as e:
        print(f"목표 값 로드 중 오류: {str(e)}")
        return default_target

def save_targets_to_file(targets, file_path='targets.json'):
    """
    목표 값을 데이터베이스에 저장하는 함수 (DB 전환)

    Args:
        targets: 저장할 목표 값 딕셔너리
        file_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        bool: 저장 성공 여부
    """
    try:
        db = get_db_manager()

        # targets가 monthly_targets 형식인 경우
        if 'monthly_targets' in targets:
            for month_str, target_data in targets['monthly_targets'].items():
                month = int(month_str)
                db.set_monthly_target(
                    month,
                    target_data['direct_target'],
                    target_data['affiliate_target']
                )
        # 단일 월 데이터인 경우 (현재 월로 저장)
        elif 'direct_target' in targets and 'affiliate_target' in targets:
            current_month = datetime.now().month
            db.set_monthly_target(
                current_month,
                targets['direct_target'],
                targets['affiliate_target']
            )

        return True
    except Exception as e:
        print(f"목표 값 저장 중 오류: {str(e)}")
        return False

def display_results(
    cumulative_approval: pd.DataFrame,
    daily_approval: pd.DataFrame,
    cumulative_installation: Optional[pd.DataFrame],
    latest_date: str,
    approval_df: pd.DataFrame,
    installation_df: Optional[pd.DataFrame]
):
    """
    분석 결과를 표시하는 함수 - 세 테이블을 한 줄에 나란히 표시
    
    Args:
        cumulative_approval: 누적 승인 실적 데이터프레임
        daily_approval: 일일 승인 실적 데이터프레임
        cumulative_installation: 누적 설치 실적 데이터프레임
        latest_date: 최신 날짜
        approval_df: 원본 승인 데이터프레임
        installation_df: 원본 설치 데이터프레임
    """
    # 현재 날짜 및 시간 가져오기
    current_time = datetime.now()
    
    # 데이터 정보 표시
    st.markdown(f'<div class="status-container"><div class="status-chip success">분석 완료</div><div class="timestamp">{current_time.strftime("%Y년 %m월 %d일 %H시 %M분")} 기준</div></div>', unsafe_allow_html=True)
    
    # 파일에서 목표 값 로드
    targets = load_targets_from_file()
    
    # 세션 상태에 목표 금액 초기화 (파일에서 로드한 값으로)
    if 'direct_target' not in st.session_state:
        st.session_state.direct_target = targets['direct_target']
    if 'affiliate_target' not in st.session_state:
        st.session_state.affiliate_target = targets['affiliate_target']
    
    # 목표 입력 UI - 숨김 가능한 expander 사용
    with st.expander("📊 목표 설정", expanded=False):
        # 연도/월 선택
        db = get_db_manager()
        available_years = db.get_available_years()
        current_year = datetime.now().year
        current_month_num = datetime.now().month

        # 사용 가능한 연도가 없으면 현재 연도 추가
        if not available_years:
            available_years = [current_year]
        elif current_year not in available_years:
            available_years = [current_year] + available_years

        col_year, col_month = st.columns([1, 1])

        with col_year:
            selected_year = st.selectbox(
                "연도",
                options=available_years,
                index=0,
                key="target_year_select"
            )

        with col_month:
            selected_month = st.selectbox(
                "월",
                options=list(range(1, 13)),
                index=current_month_num - 1,
                key="target_month_select"
            )

        current_month = str(selected_month)

        st.subheader(f"{selected_year}년 {selected_month}월 목표 설정")

        # 선택한 연도/월의 목표 로드
        month_target = db.get_monthly_target(selected_month, selected_year)
        if month_target:
            st.session_state.direct_target = month_target['direct_target']
            st.session_state.affiliate_target = month_target['affiliate_target']
        
        col1, col2 = st.columns(2)
        with col1:
            direct_target = st.number_input(
                "직접 목표 매출(원)", 
                value=int(st.session_state.direct_target),
                step=10000000,
                format="%d",
                key="direct_target_input"
            )
        with col2:
            affiliate_target = st.number_input(
            "연계 목표 매출(원)", 
            value=int(st.session_state.affiliate_target),
            step=10000000,
            format="%d",
            key="affiliate_target_input"
        )
        
        # 저장 버튼
        if st.button("목표 저장", key="save_targets_button"):
            # 세션 상태 업데이트
            st.session_state.direct_target = direct_target
            st.session_state.affiliate_target = affiliate_target

            # DB에 저장
            try:
                db = get_db_manager()
                db.set_monthly_target(
                    int(selected_month),
                    direct_target,
                    affiliate_target,
                    selected_year
                )
                st.success(f"{selected_year}년 {selected_month}월 목표가 저장되었습니다!")
            except Exception as e:
                st.error(f"목표 저장 중 오류가 발생했습니다: {str(e)}")
    
    # 현재 세션 상태의 목표 값 사용
    direct_target = st.session_state.direct_target
    affiliate_target = st.session_state.affiliate_target
    
    # 누적설치 기준 매출액 데이터 계산 - 변수 초기화 추가
    direct_sales = 0
    affiliate_sales = 0

    
    # 누적설치실적 데이터에서 매출액 계산 (누적설치 데이터 있는 경우)
    if cumulative_installation is not None and not cumulative_installation.empty:
        for _, row in cumulative_installation.iterrows():
            # 직접/연계 매출액 집계
            direct_sales += row['본사직접승인_매출액']
            affiliate_sales += row['연계승인_매출액']
    else:
        # 설치 데이터 없으면 승인 데이터 사용
        if cumulative_approval is not None and not cumulative_approval.empty:
            for _, row in cumulative_approval.iterrows():
                # 직접/연계 매출액 집계
                direct_sales += row['본사직접승인_매출액']
                affiliate_sales += row['연계승인_매출액']

    
    # 목표 달성률 계산
    total_target = direct_target + affiliate_target
    direct_achievement = (direct_sales/2 / direct_target * 100) if direct_target > 0 else 0
    affiliate_achievement = (affiliate_sales/2 / affiliate_target * 100) if affiliate_target > 0 else 0
    total_sales = direct_sales/2 + affiliate_sales/2
    total_achievement = (total_sales / total_target * 100) if total_target > 0 else 0

    ## 매출액 포맷팅 함수 - 한글 표기 방식 (백만 단위 반올림 포함)
    def format_amount(amount):
        if amount >= 100000000:  # 1억 이상
            억 = int(amount // 100000000)
            나머지 = amount % 100000000
            천만_반올림 = round(나머지 / 10000000)  # 천만 단위로 반올림
            if 천만_반올림 >= 10:
                억 += 1
                return f"{억}억"
            elif 천만_반올림 > 0:
                return f"{억}억{천만_반올림}천"
            else:
                return f"{억}억"
        elif amount >= 10000000:  # 1천만 이상
            천만_반올림 = round(amount / 10000000)
            return f"{천만_반올림}천"
        elif amount >= 1000000:  # 백만 단위
            백만_반올림 = round(amount / 1000000)
            return f"{백만_반올림}백"
        else:
            return f"{int(amount)}원"


    direct_sales_formatted = format_amount(direct_sales/2)
    affiliate_sales_formatted = format_amount(affiliate_sales/2)
    total_sales_formatted = format_amount(total_sales)
    direct_target_formatted = format_amount(direct_target)
    affiliate_target_formatted = format_amount(affiliate_target)
    total_target_formatted = format_amount(total_target)
    
    # 세 개의 테이블을 한 줄에 나란히 배치
    st.markdown('<div class="results-row">', unsafe_allow_html=True)
    
    # 3개의 열 생성
    col1, col2, col3 = st.columns(3)
    
    # 1. 누적승인실적 표시
    with col1:
        st.markdown('<div class="material-card result-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header"><h3>누적승인실적</h3></div>', unsafe_allow_html=True)
        display_custom_table(cumulative_approval, "누적승인실적")
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 2. 누적설치실적 표시 (있는 경우)
    with col2:
        st.markdown('<div class="material-card result-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header"><h3>누적설치실적</h3></div>', unsafe_allow_html=True)
        
        if cumulative_installation is None:
            st.info("설치매출 파일이 업로드되지 않았습니다. 설치실적을 확인하려면 설치매출 파일을 업로드하세요.")
        elif cumulative_installation.empty:
            st.info("설치매출 데이터에서 유효한 데이터를 찾을 수 없습니다.")
        else:
            display_custom_table(cumulative_installation, "누적설치실적")
        
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 선택된 일일 데이터와 날짜 초기화
    selected_date_daily_approval = None
    selected_date_str = latest_date
    
    # 3. 일일 승인실적 표시 (날짜 선택 기능 추가)
    with col3:
        st.markdown('<div class="material-card result-card">', unsafe_allow_html=True)
        
        # 헤더와 날짜 선택기를 위한 컨테이너
        st.markdown('<div class="card-header"><h3>일일 승인실적</h3></div>', unsafe_allow_html=True)
        
        # 날짜 선택기 추가
        selected_date = None
        
        # 사용 가능한 날짜가 있는 경우
        if 'available_dates' in st.session_state and st.session_state.available_dates:
            # 날짜 선택 UI 표시
            available_dates = st.session_state.available_dates
            # 기본값으로 첫 번째 날짜(최신 날짜) 선택
            default_idx = 0
            # 이전에 선택한 날짜가 있으면 그 날짜를 기본값으로 사용
            if st.session_state.selected_date is not None:
                for i, date_val in enumerate(available_dates):
                    if date_val == st.session_state.selected_date:
                        default_idx = i
                        break
            
            # 달력으로 날짜 선택
            selected_date = st.date_input(
                "날짜 선택", 
                value=available_dates[default_idx],
                min_value=min(available_dates) if available_dates else None,
                max_value=max(available_dates) if available_dates else None,
                key="daily_date_selector"
            )
            
            # 세션 상태 업데이트
            st.session_state.selected_date = selected_date
            st.session_state.selected_date_str = selected_date.strftime("%Y-%m-%d")
            selected_date_str = selected_date.strftime("%Y-%m-%d")
            
            # 해당 날짜의 데이터 표시
            if selected_date and approval_df is not None:
                # 선택한 날짜에 대한 일일 승인실적 분석
                selected_date_daily_approval = analyze_daily_approval_by_date(approval_df, selected_date)
                
                if selected_date_daily_approval.empty:
                    st.info(f"{selected_date.strftime('%Y-%m-%d')}에 해당하는 승인 데이터가 없습니다.")
                    selected_date_daily_approval = None
                else:
                    display_custom_table(selected_date_daily_approval, f"{selected_date.strftime('%Y-%m-%d')} 승인 실적")
            else:
                st.info("날짜를 선택하세요.")
        # 사용 가능한 날짜가 없는 경우
        else:
            # 기존 최신 날짜 기준 일일 승인실적 표시
            if daily_approval.empty:
                st.info(f"{latest_date}에 해당하는 승인 데이터가 없습니다.")
            else:
                display_custom_table(daily_approval, f"일일 승인 실적 ({latest_date})")
                selected_date_daily_approval = daily_approval
        
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    st.markdown('</div>', unsafe_allow_html=True)  # 행 닫기
    
    # 일일 데이터에서 건수 정보 추출 (선택한 날짜 기준)
    daily_df = selected_date_daily_approval if selected_date_daily_approval is not None else daily_approval
    
    # 제품별 합계 및 팀별 데이터 초기화
    total_anma = 0
    total_lacloud = 0 
    total_water = 0
    total_thecare = 0
    total_membership = 0
    
    crm_total = 0
    crm_anma = 0
    crm_lacloud = 0
    crm_water = 0
    crm_thecare = 0
    crm_membership = 0
    
    online_total = 0
    online_anma = 0
    online_lacloud = 0
    online_water = 0
    online_thecare = 0
    online_membership = 0
    
    # 선택한 날짜에 해당하는 원본 데이터 필터링
    daily_source_df = None
    
    if approval_df is not None and '주문 일자' in approval_df.columns:
        try:
            # 날짜 선택이 있는 경우 해당 날짜 데이터 사용
            if selected_date is not None:
                # 객체형 비교로 인한 오류 방지를 위해 string 변환 후 비교
                selected_date_str_for_filter = selected_date.strftime("%Y-%m-%d")
                daily_source_df = approval_df[approval_df['주문 일자'].dt.strftime("%Y-%m-%d") == selected_date_str_for_filter].copy()
            else:
                # 날짜 선택이 없는 경우 최신 날짜 데이터 사용
                latest_date_obj = approval_df['주문 일자'].max()
                if pd.notna(latest_date_obj):
                    latest_date_str_for_filter = latest_date_obj.strftime("%Y-%m-%d")
                    daily_source_df = approval_df[approval_df['주문 일자'].dt.strftime("%Y-%m-%d") == latest_date_str_for_filter].copy()
        except Exception as e:
            st.warning(f"일일 데이터 필터링 중 오류 발생: {str(e)}")
            daily_source_df = None
    
    # 선택한 날짜의 일일 데이터에서 정보 추출
    if daily_df is not None and not daily_df.empty:
        # 일일 데이터에서 제품별 건수 계산
        for _, row in daily_df.iterrows():
            product = row['제품'].lower() if isinstance(row['제품'], str) else ""
            
            # 제품별 총합에 추가
            if '안마의자' in product:
                total_anma += row['총승인(본사/연계)_건수']
            elif '라클라우드' in product:
                total_lacloud += row['총승인(본사/연계)_건수']
            elif '정수기' in product:
                total_water += row['총승인(본사/연계)_건수']
    
    # 원본 일일 데이터에서 팀별 구분 계산
    if daily_source_df is not None:
        # CRM팀 데이터 (판매인입경로에 'CRM' 포함)
        crm_data = daily_source_df[daily_source_df['판매인입경로'].astype(str).str.contains('CRM', case=False)].copy()
        # 온라인팀 데이터 (일반회차 캠페인이 'CB-'로 시작)
        online_data = daily_source_df[daily_source_df['일반회차 캠페인'].astype(str).str.startswith('CB-')].copy()
        
        # 판매 유형 컬럼이 있는지 확인 (공백 있음/없음 둘 다 체크)
        has_sale_type = '판매유형' in daily_source_df.columns or '판매 유형' in daily_source_df.columns
        sale_type_col = '판매유형' if '판매유형' in daily_source_df.columns else '판매 유형'

        # CRM팀 데이터 처리
        for _, row in crm_data.iterrows():
            sale_type = str(row.get(sale_type_col, '')).lower() if has_sale_type else ''
            category = str(row.get('대분류', '')).lower()
            
            # 판매 유형에 따른 분류 (우선순위: 더케어 > 멤버십 > 대분류)
            if '더케어' in sale_type or 'the care' in sale_type or 'thecare' in sale_type:
                crm_thecare += 1
                crm_total += 1
            elif '멤버' in sale_type:  # 멤버십, 멤버쉽, 멤버 모두 포함
                crm_membership += 1
                crm_total += 1
            # 대분류에 따른 분류
            elif '안마의자' in category:
                crm_anma += 1
                crm_total += 1
            elif '라클라우드' in category:
                crm_lacloud += 1
                crm_total += 1
            elif '정수기' in category:
                crm_water += 1
                crm_total += 1
        
        # 온라인팀 데이터 처리
        for _, row in online_data.iterrows():
            sale_type = str(row.get(sale_type_col, '')).lower() if has_sale_type else ''
            category = str(row.get('대분류', '')).lower()
            
            # 판매 유형에 따른 분류 (우선순위: 더케어 > 멤버십 > 대분류)
            if '더케어' in sale_type or 'the care' in sale_type or 'thecare' in sale_type:
                online_thecare += 1
                online_total += 1
            elif '멤버' in sale_type:  # 멤버십, 멤버쉽, 멤버 모두 포함
                online_membership += 1
                online_total += 1
            # 대분류에 따른 분류
            elif '안마의자' in category:
                online_anma += 1
                online_total += 1
            elif '라클라우드' in category:
                online_lacloud += 1
                online_total += 1
            elif '정수기' in category:
                online_water += 1
                online_total += 1
    
    # 요약 텍스트 박스 추가
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']
    date_str = f"{current_time.month}월{current_time.day}일({weekday_names[current_time.weekday()]})"
    time_str = f"{current_time.hour}:{current_time.minute:02d}"
    
    # 총 건수 계산
    grand_total = crm_total + online_total
    
    # CRM팀 상세 정보 생성
    crm_parts = []
    if crm_anma > 0:
        crm_parts.append(f"안마 {crm_anma}건")
    if crm_lacloud > 0:
        crm_parts.append(f"라클 {crm_lacloud}건")
    if crm_water > 0:
        crm_parts.append(f"정수기 {crm_water}건")
    if crm_thecare > 0:
        crm_parts.append(f"더케어 {crm_thecare}건")
    if crm_membership > 0:
        crm_parts.append(f"멤버쉽 {crm_membership}건")
    
    crm_details = f"({', '.join(crm_parts)})" if crm_parts else "(0건)"
    
    # 온라인팀 상세 정보 생성
    online_parts = []
    if online_anma > 0:
        online_parts.append(f"안마 {online_anma}건")
    if online_lacloud > 0:
        online_parts.append(f"라클 {online_lacloud}건")
    if online_water > 0:
        online_parts.append(f"정수기 {online_water}건")
    if online_thecare > 0:
        online_parts.append(f"더케어 {online_thecare}건")
    if online_membership > 0:
        online_parts.append(f"멤버쉽 {online_membership}건")
    
    online_details = f"({', '.join(online_parts)})" if online_parts else "(0건)"
    
    # 요약 텍스트 박스 콘텐츠 준비 - 0건인 항목 생략
    product_items = []
    total_anma_all = crm_anma + online_anma
    total_lacloud_all = crm_lacloud + online_lacloud
    total_water_all = crm_water + online_water
    total_thecare_all = crm_thecare + online_thecare
    total_membership_all = crm_membership + online_membership
    
    if total_anma_all > 0:
        product_items.append(f'<div class="summary-textbox-product">💆 안마의자 {total_anma_all}건</div>')
    if total_lacloud_all > 0:
        product_items.append(f'<div class="summary-textbox-product">🛏️ 라클라우드 {total_lacloud_all}건</div>')
    if total_water_all > 0:
        product_items.append(f'<div class="summary-textbox-product">💧 정수기 {total_water_all}건</div>')
    if total_thecare_all > 0:
        product_items.append(f'<div class="summary-textbox-product">🛠️ 더케어 {total_thecare_all}건</div>')
    if total_membership_all > 0:
        product_items.append(f'<div class="summary-textbox-product">🔖 멤버쉽 {total_membership_all}건</div>')
    
    product_html = '\n'.join(product_items)
    
    # 요약 텍스트 박스 HTML - 선택한 날짜의 일일 데이터 기준으로 건수 표시
    summary_box_html = f'''
    <div class="summary-textbox" style="width: 60%; max-width: 500px;">
        <div class="summary-textbox-title">{date_str} CRM팀 실적_{time_str}</div>
        <br>
        <div class="summary-textbox-goal">목표 매출 : {direct_target_formatted}(직), {affiliate_target_formatted}(연), 총 {total_target_formatted}</div>
        <div class="summary-textbox-achievement">누적 달성: {direct_sales_formatted}(직 {direct_achievement:.1f}%), {affiliate_sales_formatted}(연 {affiliate_achievement:.1f}%), {total_sales_formatted}(총 {total_achievement:.1f}%)</div>
        <br>
        <div class="summary-textbox-team">🔄 CRM팀 : 총 {crm_total}건</div>
        <div>{crm_details}</div>
        <div class="summary-textbox-team">💻 온라인팀: 총 {online_total}건</div>
        <div>{online_details}</div>
        <br>
        {product_html}
        <br>
        <div class="summary-textbox-total">📊 총 건수 {grand_total}건</div>
    </div>
    '''
    
    st.markdown(summary_box_html, unsafe_allow_html=True)
    
    # 엑셀 내보내기
    st.markdown('<div class="material-card download-card">', unsafe_allow_html=True)
    st.subheader("데이터 다운로드")
    st.markdown(DOWNLOAD_BUTTON_STYLE, unsafe_allow_html=True)
    
    try:
        # 현재 날짜와 UUID 생성
        today = datetime.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4())[:4]  # UUID 앞 4자리만 사용
        file_prefix = f"{today}_{unique_id}_"
        
        # 선택한 날짜가 있는 경우
        selected_date_for_excel = st.session_state.selected_date if hasattr(st.session_state, 'selected_date') else None
        selected_date_str_for_excel = st.session_state.selected_date_str if hasattr(st.session_state, 'selected_date_str') else latest_date
        
        # 선택한 날짜에 대한 일일 승인실적 데이터 생성
        if selected_date_for_excel and approval_df is not None:
            selected_daily_approval = analyze_daily_approval_by_date(approval_df, selected_date_for_excel)
        else:
            selected_daily_approval = daily_approval
        
        # 엑셀 파일 생성 - 업데이트된 함수 사용
        excel_data = create_excel_report(
            cumulative_approval,
            selected_daily_approval,
            cumulative_installation,
            selected_date_str_for_excel,
            approval_df,
            installation_df,
            selected_date_for_excel
        )
        
        if excel_data:
            # 시트 구성에 따른 다운로드 버튼 레이블 변경
            sheet_count = 3  # 기본: 매출현황, 승인매출, 설치매출(있는 경우)
            label = f"엑셀 다운로드 ({sheet_count}시트)"
            
            # 다운로드 링크 생성
            b64 = base64.b64encode(excel_data).decode()
            href = f'<div class="download-button-container"><a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{file_prefix}일일_매출_현황.xlsx" class="material-button">{label}</a></div>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.error("엑셀 파일 생성에 실패했습니다.")
    except Exception as e:
        st.error(f"엑셀 파일 다운로드 준비 중 오류가 발생했습니다: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기

def format_value(value):
    """
    값을 포맷팅하는 함수 - 백만 단위로 표시 (소수점 없음)
    
    Args:
        value: 포맷팅할 값
    
    Returns:
        str: 포맷팅된 문자열
    """
    if pd.isna(value) or value == 0:
        return "-"
    
    if isinstance(value, (int, float)):
        # 백만 단위로 변환하여 소수점 없이 반올림
        if value >= 1000000:
            return f"{round(value/1000000)}"
        # 그 외에는 정수로 표시
        return str(int(value))
    
    return str(value)

def display_custom_table(df: pd.DataFrame, title: str):
    """
    Streamlit 네이티브 테이블을 사용하여 데이터 표시
    
    Args:
        df: 표시할 데이터프레임
        title: 테이블 제목
    """
    # 데이터가 없는 경우
    if df is None or df.empty:
        st.info(f"{title}에 해당하는 데이터가 없습니다.")
        return
    
    # 새로운 형태의 데이터프레임 생성
    display_df = pd.DataFrame()
    
    # 제품 열 추가
    display_df['구분'] = df['제품']
    
    # 총승인 열 추가
    display_df['총승인_건수'] = df['총승인(본사/연계)_건수']
    display_df['총승인_매출액'] = df['총승인(본사/연계)_매출액'].apply(
        lambda x: round(x/1000000) if x >= 1000000 else x)
    
    # 본사 열 추가
    display_df['본사_건수'] = df['본사직접승인_건수']
    display_df['본사_매출액'] = df['본사직접승인_매출액'].apply(
        lambda x: round(x/1000000) if x >= 1000000 else x)
    
    # 연계 열 추가
    display_df['연계_건수'] = df['연계승인_건수']
    display_df['연계_매출액'] = df['연계승인_매출액'].apply(
        lambda x: round(x/1000000) if x >= 1000000 else x)
    
    # 온라인 열 추가
    display_df['온라인_건수'] = df['온라인_건수']
    display_df['온라인_매출액'] = df['온라인_매출액'].apply(
        lambda x: round(x/1000000) if x >= 1000000 else x)
    
    # 열 이름 변경 (더 간결하게)
    display_df.columns = [
        '구분',
        '건수', '매출액',  # 총승인
        '건수', '매출액',  # 본사
        '건수', '매출액',  # 연계
        '건수', '매출액'   # 온라인
    ]
    
    # 멀티 인덱스 헤더 생성
    header = pd.MultiIndex.from_arrays([
        ['', '총승인(본사/연계)', '총승인(본사/연계)', '본사직접승인', '본사직접승인', '연계승인', '연계승인', '온라인', '온라인'],
        display_df.columns
    ])
    
    display_df.columns = header
    
    # Streamlit의 네이티브 테이블 컴포넌트 사용
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )