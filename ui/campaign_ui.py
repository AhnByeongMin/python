"""
캠페인/정규분배 현황 UI 모듈

이 모듈은 캠페인/정규분배 현황 탭의 UI 컴포넌트와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import io
import time
from typing import Dict, List, Optional, Any, Union

# 비즈니스 로직 가져오기
from logic.campaign_logic import (
    process_campaign_files,
    process_consultant_data,
    create_excel_file,
    format_dataframe_for_display
)

# CSS 스타일 가져오기
from styles.campaign_styles import apply_styles

# utils.py에서 필요한 함수 가져오기
from utils.utils import format_time, is_holiday, get_previous_business_day

def display_consultant_results(consultant_df):
    """
    상담사별 분석 결과를 표시하는 함수 (접었다 펼치는 기능 추가)
    
    Args:
        consultant_df: 상담사별 분석 결과 데이터프레임
    """
    if consultant_df is None:
        return
    
    st.markdown('<h3>신규 미처리 건</h3>', unsafe_allow_html=True)
    
    # 데이터 가공
    display_df = consultant_df.copy()
    
    # 행 타입 컬럼 필요 (접었다 펼치는 기능을 위해)
    if "행타입" not in display_df.columns:
        st.error("행타입 컬럼이 없어 계층 구조를 표시할 수 없습니다.")
        return
        
    # 숫자 컬럼 포맷팅
    display_df["신규건수"] = display_df["신규건수"].apply(
        lambda x: "" if pd.isna(x) or x == 0 else f"{int(x)}"
    )
    
    # 캠페인별로 그룹화
    campaign_groups = {}
    current_campaign = None
    
    # 캠페인별 그룹 구성
    for i, row in display_df.iterrows():
        if row["행타입"] == "캠페인":
            current_campaign = row["일반회차 캠페인"]
            campaign_groups[current_campaign] = {
                "건수": row["신규건수"],
                "상담사": []
            }
        elif row["행타입"] == "상담사" and current_campaign is not None:
            campaign_groups[current_campaign]["상담사"].append({
                "이름": row["상담사"],
                "건수": row["신규건수"]
            })
    
    # 각 캠페인에 대한 expander 생성
    for campaign, data in campaign_groups.items():
        # 총합계 행은 항상 표시하고 확장 불가능하게 처리 (맨 아래에 별도로 표시)
        if campaign == "총합계":
            continue
            
        # 캠페인별 확장 가능한 섹션
        with st.expander(f"{campaign} - {data['건수']}건"):
            # 테이블 헤더
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("<b>상담사</b>", unsafe_allow_html=True)
            with col2:
                st.markdown("<b>건수</b>", unsafe_allow_html=True)
            
            # 상담사별 데이터 표시
            for consultant in data["상담사"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(consultant["이름"])
                with col2:
                    st.write(consultant["건수"])
    
    # 총합계 행 별도 표시 (있는 경우)
    if "총합계" in campaign_groups:
        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("<b>총합계</b>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<b>{campaign_groups['총합계']['건수']}</b>", unsafe_allow_html=True)
    

def show():
    """
    캠페인/정규분배 분석 페이지 UI를 표시하는 메인 함수
    """
    # 스타일 적용
    apply_styles()
    
    # 타이틀 및 설명
    st.title("📢캠페인/정규분배 현황")
    st.markdown('<p>이 도구는 다수의 엑셀 파일을 분석하여 캠페인/정규분배 현황을 보여줍니다. 파일을 업로드하고 분석 버튼을 클릭하면 결과를 확인할 수 있습니다.</p>', unsafe_allow_html=True)
    
    # 세션 상태 초기화 (딕셔너리 방식)
    session_defaults = {
        'campaign_files': [],
        'campaign_results': None,
        'cleaned_data': None,
        'consultant_results': None,
        'analysis_complete': False,
        'processing': False
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # 파일 업로드 UI
    st.subheader("엑셀 파일 업로드")
    
    uploaded_files = st.file_uploader(
        "상담주문내역 엑셀 파일을 업로드하세요 (다수 파일 선택 가능)",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        key="campaign_uploader_tab3"
    )
    
    # 업로드된 파일 목록 표시
    if uploaded_files:
        st.session_state.campaign_files = uploaded_files
        st.write(f"총 {len(uploaded_files)}개의 파일이 업로드되었습니다:")
        
        # 파일 목록을 한 줄로 표시하여 UI 공간 절약
        file_names = [file.name for file in uploaded_files]
        st.write(", ".join(file_names))

    # 파일 업로드 전 안내 화면
    st.info("상담주문내역 파일을 모두 업로드한 후 분석 시작을 누르면 분석이 시작됩니다.")
    
    # 분석 버튼
    analyze_button = st.button("분석 시작", key="analyze_campaign_tab3")
    
    # 분석 기능
    if analyze_button and st.session_state.campaign_files:
        if not st.session_state.processing:
            st.session_state.processing = True

            # 진행 상황 표시를 위한 placeholder
            progress_placeholder = st.empty()

            try:
                # 진행 상태 표시
                progress_placeholder.info('🔄 파일 분석 중...')
                start_time = time.time()

                # 캠페인 분석 실행
                results, cleaned_data, before_count, after_count = process_campaign_files(st.session_state.campaign_files)
                st.session_state.campaign_results = results
                st.session_state.cleaned_data = cleaned_data

                # 상담사별 분석 실행 (상담DB상태가 "신규"인 데이터가 있는 경우에만)
                if cleaned_data is not None:
                    progress_placeholder.info('🔄 상담사별 분석 중...')
                    consultant_results, error = process_consultant_data(cleaned_data)
                    if error:
                        if "상담DB상태가 '신규'인 데이터가 없습니다" not in error:
                            st.warning(f"상담사별 분석: {error}")
                    st.session_state.consultant_results = consultant_results

                # 분석 완료 플래그 설정
                st.session_state.analysis_complete = True
                st.session_state.processing = False

                # 분석 소요 시간 및 중복 제거 정보 표시
                end_time = time.time()

                # 중복 제거 메시지 생성
                if before_count > 0 and after_count > 0:
                    removed_count = before_count - after_count
                    if removed_count > 0:
                        progress_placeholder.success(f"✅ 분석 완료! 중복 제거: {removed_count}건 (원본: {before_count}건 → 최종: {after_count}건) | 소요 시간: {end_time - start_time:.2f}초")
                    else:
                        progress_placeholder.success(f"✅ 분석 완료! 중복 없음 (총 {after_count}건) | 소요 시간: {end_time - start_time:.2f}초")
                else:
                    progress_placeholder.info(f"분석 완료 (소요 시간: {end_time - start_time:.2f}초)")

            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생: {str(e)}")
                st.session_state.processing = False
                progress_placeholder.empty()
    
    # 분석 결과 표시 (분석이 완료된 경우에만)
    if st.session_state.analysis_complete:
        display_results(
            st.session_state.campaign_results, 
            st.session_state.cleaned_data, 
            st.session_state.consultant_results
        )

def display_results(results_df, cleaned_data, consultant_df):
    """
    분석 결과를 표시하는 통합 함수 (좌우 레이아웃)
    
    Args:
        results_df: 분석 결과 데이터프레임
        cleaned_data: 중복 제거된 원본 데이터
        consultant_df: 상담사별 분석 결과 데이터프레임
    """
    # 결과가 없는 경우
    if results_df is None:
        return
        
    # 2개의 열 생성 - 컬럼 비율 [4, 1]로 조정 (오른쪽 테이블 폭 크게 줄임)
    col1, col2 = st.columns([4, 1])
    
    # 첫 번째 열: 캠페인 분석 결과
    with col1:
        st.markdown('<h3>캠페인/정규 분배 현황</h3>', unsafe_allow_html=True)
        
        # 데이터 가공
        display_df = format_dataframe_for_display(results_df)
        
        # 표 표시
        st.dataframe(display_df.set_index('일반회차 캠페인'), height=400)
    
    # 두 번째 열: 상담사별 분석 결과 (접었다 펼치는 기능)
    with col2:
        if consultant_df is not None:
            display_consultant_results(consultant_df)
    
    # 엑셀 다운로드 버튼 (전체 화면 너비로 표시)
    if cleaned_data is not None:
        try:
            # 현재 날짜와 UUID 생성
            import datetime
            import uuid
            today = datetime.datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:4]  # UUID 앞 4자리만 사용
            file_prefix = f"{today}_{unique_id}_"
            
            # 엑셀 파일 생성
            excel_buffer = create_excel_file(cleaned_data, results_df, consultant_df)
            
            if excel_buffer is not None:
                # 다운로드 버튼 (시트 수에 따라 레이블 변경)
                sheet_count = 3 if consultant_df is not None else 2
                st.download_button(
                    label=f"엑셀 다운로드 ({sheet_count}시트)",
                    data=excel_buffer,
                    file_name=f"{file_prefix}캠페인_분석결과.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_campaign_excel_tab3"
                )
            else:
                # 대체 다운로드 방법 제공 - BytesIO로 직접 utf-8-sig 인코딩
                csv_buffer = io.BytesIO()
                results_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_buffer.seek(0)
                st.download_button(
                    label="CSV 다운로드 (결과만)",
                    data=csv_buffer.getvalue(),
                    file_name=f"{file_prefix}캠페인_분석결과.csv",
                    mime="text/csv",
                    key="download_campaign_csv_tab3"
                )
                
        except Exception as e:
            st.error(f"다운로드 버튼 생성 중 오류가 발생했습니다: {str(e)}")
            try:
                # 대체 다운로드 방법 제공 - BytesIO로 직접 utf-8-sig 인코딩
                csv_buffer = io.BytesIO()
                results_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_buffer.seek(0)

                # 현재 날짜와 UUID 생성 (예외 처리 내에서도 동일하게 적용)
                import datetime
                import uuid
                today = datetime.datetime.now().strftime('%Y%m%d')
                unique_id = str(uuid.uuid4())[:4]
                file_prefix = f"{today}_{unique_id}_"

                st.download_button(
                    label="CSV 다운로드 (결과만)",
                    data=csv_buffer.getvalue(),
                    file_name=f"{file_prefix}캠페인_분석결과.csv",
                    mime="text/csv",
                    key="download_campaign_csv_tab3"
                )
            except Exception as inner_e:
                st.error(f"CSV 다운로드 버튼 생성 중에도 오류가 발생했습니다: {str(inner_e)}")