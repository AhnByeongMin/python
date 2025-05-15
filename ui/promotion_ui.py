"""
상담사 프로모션 현황 UI 모듈

이 모듈은 상담사 프로모션 현황 탭의 UI 요소와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Optional, Any

# 비즈니스 로직 가져오기
from logic.promotion_logic import (
    process_promotion_file, analyze_promotion_data, create_excel_report
)

# CSS 스타일 가져오기
from styles.promotion_styles import (
    PROMOTION_TAB_STYLE, FORMAT_REWARD_SCRIPT,
    DOWNLOAD_BUTTON_STYLE, USAGE_GUIDE_MARKDOWN
)

def show():
    """상담사 프로모션 현황 탭 UI를 표시하는 메인 함수"""
    
    # 스타일 적용
    st.markdown(PROMOTION_TAB_STYLE, unsafe_allow_html=True)
    st.markdown(FORMAT_REWARD_SCRIPT, unsafe_allow_html=True)
    
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
        st.session_state.min_condition = 1
    if 'reward_positions' not in st.session_state:
        st.session_state.reward_positions = 3
    
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
                st.success(f"파일 로드 완료! 총 {len(df)}개의 레코드가 처리되었습니다.")
    
    st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 프로모션 설정 UI
    st.markdown('<div class="settings-card">', unsafe_allow_html=True)
    st.subheader("프로모션 설정")
    
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
        st.markdown("#### 판매 경로 설정")
        
        # 직접/연계 포함 여부
        direct_only = st.checkbox(
            "직접 판매만 포함 (CRM 판매인입경로)",
            value=st.session_state.direct_only,
            key="direct_checkbox"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="settings-section">', unsafe_allow_html=True)
        st.markdown("#### 기준 설정")
        
        # 기준 선택 (다중 선택)
        criteria = st.multiselect(
            "순위 기준",
            options=["승인건수", "승인액"],
            default=st.session_state.criteria,
            key="criteria_select"
        )
        
        # 최소 조건
        min_condition = st.number_input(
            "최소 건수 조건",
            min_value=1,
            value=st.session_state.min_condition,
            step=1,
            key="min_condition_input"
        )
        
        # 포상 순위
        reward_positions = st.number_input(
            "포상 순위 수",
            min_value=1,
            value=st.session_state.reward_positions,
            step=1,
            key="reward_positions_input"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
    if apply_button and st.session_state.promotion_df is not None:
        # 세션 상태 업데이트
        st.session_state.include_products = include_products
        st.session_state.include_services = include_services
        st.session_state.direct_only = direct_only
        st.session_state.criteria = criteria
        st.session_state.min_condition = min_condition
        st.session_state.reward_positions = reward_positions
        
        # 대상 품목이 최소 하나는 선택되어야 함
        if not include_products:
            st.error("최소한 하나 이상의 제품을 선택해야 합니다.")
        # 순위 기준이 최소 하나는 선택되어야 함
        elif not criteria:
            st.error("최소한 하나 이상의 순위 기준을 선택해야 합니다.")
        else:
            with st.spinner("프로모션 분석 중..."):
                # 프로모션 분석 실행
                results_df, error = analyze_promotion_data(
                    st.session_state.promotion_df,
                    include_products,
                    include_services,
                    direct_only,
                    criteria,
                    min_condition,
                    reward_positions
                )
                
                if error:
                    st.error(error)
                else:
                    # 세션 상태에 결과 저장
                    st.session_state.promotion_results = results_df
                    st.success("프로모션 분석이 완료되었습니다!")
    
    # 결과 표시
    if st.session_state.promotion_results is not None:
        st.markdown('<div class="results-card">', unsafe_allow_html=True)
        st.subheader("프로모션 결과")
        
        # 현재 설정 요약 표시
        current_settings = []
        current_settings.append(f"대상 품목: {', '.join(st.session_state.include_products)}")
        current_settings.append(f"서비스 품목 포함: {'예' if st.session_state.include_services else '아니오'}")
        current_settings.append(f"직접 판매만: {'예' if st.session_state.direct_only else '아니오'}")
        current_settings.append(f"순위 기준: {', '.join(st.session_state.criteria)}")
        current_settings.append(f"최소 건수 조건: {st.session_state.min_condition}")
        current_settings.append(f"포상 순위 수: {st.session_state.reward_positions}")
        
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
        except Exception as e:
            st.error(f"엑셀 파일 다운로드 준비 중 오류가 발생했습니다: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)  # 카드 닫기
    
    # 파일이 업로드되지 않았을 때 안내 정보
    elif st.session_state.promotion_df is None:
        st.info("상담주문내역 엑셀 파일을 업로드하고 프로모션 설정을 적용하세요.")
        st.markdown(USAGE_GUIDE_MARKDOWN)