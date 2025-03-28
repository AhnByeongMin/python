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

def show():
    """일일 매출 현황 탭 UI를 표시하는 메인 함수"""
    
    # CSS 스타일 적용
    st.markdown(DAILY_SALES_TAB_STYLE, unsafe_allow_html=True)
    st.markdown(DARK_TABLE_STYLE, unsafe_allow_html=True)
    
    # 타이틀 및 설명
    st.title("📈 일일 매출 현황")
    st.markdown('<p>이 도구는 승인매출과 설치매출 데이터를 분석하여 일일 매출 현황을 보여줍니다. 판매인입경로와 캠페인 유형에 따라 매출을 분류합니다.</p>', unsafe_allow_html=True)

    # 세션 상태 초기화
    if 'daily_approval_df' not in st.session_state:
        st.session_state.daily_approval_df = None
    if 'daily_installation_df' not in st.session_state:
        st.session_state.daily_installation_df = None
    if 'cumulative_approval' not in st.session_state:
        st.session_state.cumulative_approval = None
    if 'daily_approval' not in st.session_state:
        st.session_state.daily_approval = None
    if 'cumulative_installation' not in st.session_state:
        st.session_state.cumulative_installation = None
    if 'latest_date' not in st.session_state:
        st.session_state.latest_date = None
    if 'available_dates' not in st.session_state:
        st.session_state.available_dates = []
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None
    if 'selected_date_str' not in st.session_state:
        st.session_state.selected_date_str = None

    # 파일 업로드 UI
    st.markdown('<div class="material-card upload-card">', unsafe_allow_html=True)
    st.subheader("데이터 파일 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 승인매출 파일 첨부")
        # 키 이름 변경: approval_file -> daily_approval_file
        approval_file = st.file_uploader("승인매출 엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="daily_approval_file")
    
    with col2:
        st.markdown("### 설치매출 파일 첨부")
        # 키 이름 변경: installation_file -> daily_installation_file
        installation_file = st.file_uploader("설치매출 엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="daily_installation_file")
    
    # 분석 버튼
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    # 키 이름 변경: analyze_daily_sales -> analyze_daily_button
    analyze_button = st.button("분석 시작", key="analyze_daily_button")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 메인 로직
    if analyze_button and approval_file is not None:
        # 파일 처리 진행 상태 표시
        with st.spinner('파일 분석 중...'):
            # 파일 위치 저장을 위해 seek(0)
            approval_file.seek(0)
            if installation_file is not None:
                installation_file.seek(0)
            
            # 파일 처리 시도
            approval_df, approval_error = process_approval_file(approval_file)
            
            installation_df = None
            installation_error = None
            if installation_file is not None:
                installation_df, installation_error = process_installation_file(installation_file)
        
        # 오류 체크
        if approval_error:
            st.error(approval_error)
        elif installation_file is not None and installation_error:
            st.error(installation_error)
        else:
            # 세션 상태에 데이터프레임 저장
            st.session_state.daily_approval_df = approval_df
            st.session_state.daily_installation_df = installation_df
            
            # 분석 실행
            results = analyze_sales_data(approval_df, installation_df)
            
            if 'error' in results:
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
        st.info("승인매출 파일을 업로드하고 설치매출 파일(선택사항)도 업로드한 후 분석 시작 버튼을 클릭하세요.")
        st.markdown(USAGE_GUIDE_MARKDOWN, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기

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
            
            # 해당 날짜의 데이터 표시
            if selected_date and approval_df is not None:
                # 선택한 날짜에 대한 일일 승인실적 분석
                selected_date_daily_approval = analyze_daily_approval_by_date(approval_df, selected_date)
                
                if selected_date_daily_approval.empty:
                    st.info(f"{selected_date.strftime('%Y-%m-%d')}에 해당하는 승인 데이터가 없습니다.")
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
        
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    st.markdown('</div>', unsafe_allow_html=True)  # 행 닫기
    
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