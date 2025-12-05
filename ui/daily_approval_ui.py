"""
일일 승인 현황 UI 모듈

이 모듈은 일일 승인 현황 탭의 UI 요소와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import base64
import plotly.express as px
from datetime import datetime, time
import uuid
import json
import os
from typing import Dict, List, Optional, Any

# 비즈니스 로직 가져오기
from logic.daily_approval_logic import (
    process_approval_file, process_calltime_file, 
    analyze_daily_approval, match_consultant_calltime, create_excel_report
)

# CSS 스타일 가져오기
from styles.daily_approval_styles import (
    DAILY_APPROVAL_TAB_STYLE, DAILY_APPROVAL_CARD_STYLE,
    DOWNLOAD_BUTTON_STYLE, DATE_DISPLAY_STYLE,
    DAILY_APPROVAL_DESCRIPTION, USAGE_GUIDE_MARKDOWN
)

# 상담사 관리 유틸리티 가져오기
from utils.consultant_manager import (
    load_consultants, save_consultants, add_consultant, remove_consultant,
    get_all_consultants, get_consultants_by_team, get_team_by_consultant
)

# 유틸리티 함수 가져오기
from utils.utils import format_time

def generate_daily_approval_table(results: Dict) -> str:
    """
    일일 승인 현황 테이블 HTML 생성 함수
    
    Args:
        results: 분석 결과 딕셔너리
        
    Returns:
        str: HTML 테이블
    """
    if not results:
        return "<p>분석 결과가 없습니다.</p>"
    
    html = """
    <style>
    .approval-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .approval-table th, .approval-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center;
    }
    .approval-table th {
        background-color: #4472c4;
        color: white;
        font-weight: bold;
    }
    .approval-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    .approval-table tr:hover {
        background-color: #e6e6e6;
    }
    .approval-table td.numeric {
        text-align: right;
        padding-right: 10px;
    }
    .approval-team-header {
        background-color: #8eaadb !important;
        color: #333;
        font-weight: bold;
    }
    .approval-total-row {
        background-color: #4472c4 !important;
        color: white;
        font-weight: bold;
    }
    </style>
    """
    
    # 현재 날짜/시간 정보
    latest_date = results['latest_date']
    date_str = latest_date.strftime("%Y-%m-%d")
    
    # 테이블 시작
    html += f"""
    <h3 style="text-align:center; margin-bottom:10px;">일일/누적 승인현황 ({date_str} 기준)</h3>
    <table class="approval-table">
        <thead>
            <tr>
                <th>상담사</th>
                <th>팀</th>
                <th>안마의자(건)</th>
                <th>안마의자(백만)</th>
                <th>라클라우드(건)</th>
                <th>라클라우드(백만)</th>
                <th>정수기(건)</th>
                <th>정수기(백만)</th>
                <th>누적건수</th>
                <th>누적매출액</th>
                <th>일일건수</th>
                <th>일일매출액</th>
                <th>콜건수</th>
                <th>콜타임</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # 데이터 행 추가
    current_team = None
    for consultant_data in results['consultant_data']:
        # 팀이 바뀌면 팀 구분 행 추가
        if consultant_data['조직'] != current_team:
            current_team = consultant_data['조직']
            html += f"""
            <tr>
                <td colspan="14" class="approval-team-header">{current_team}</td>
            </tr>
            """
        
        # 상담원 데이터 행 추가
        html += f"""
        <tr>
            <td>{consultant_data['상담사']}</td>
            <td>{consultant_data['조직']}</td>
            <td>{consultant_data['안마의자']}</td>
            <td class="numeric">{consultant_data['안마의자_매출액']:.1f}</td>
            <td>{consultant_data['라클라우드']}</td>
            <td class="numeric">{consultant_data['라클라우드_매출액']:.1f}</td>
            <td>{consultant_data['정수기']}</td>
            <td class="numeric">{consultant_data['정수기_매출액']:.1f}</td>
            <td>{consultant_data['누적건수']}</td>
            <td class="numeric">{consultant_data['누적매출액']:.1f}</td>
            <td>{consultant_data['일일건수']}</td>
            <td class="numeric">{consultant_data['일일매출액']:.1f}</td>
            <td>{consultant_data['콜건수']}</td>
            <td>{consultant_data['콜타임']}</td>
        </tr>
        """
    
    # 총합계 행 추가
    html += f"""
        <tr class="approval-total-row">
            <td>총합계</td>
            <td></td>
            <td>{results['total_data']['anma_count']}</td>
            <td class="numeric">{results['total_data']['anma_sales']:.1f}</td>
            <td>{results['total_data']['lacloud_count']}</td>
            <td class="numeric">{results['total_data']['lacloud_sales']:.1f}</td>
            <td>{results['total_data']['water_count']}</td>
            <td class="numeric">{results['total_data']['water_sales']:.1f}</td>
            <td>{results['total_data']['total_count']}</td>
            <td class="numeric">{results['total_data']['total_sales']:.1f}</td>
            <td>{results['daily_data']['total_count']}</td>
            <td class="numeric">{results['daily_data']['total_sales']:.1f}</td>
            <td></td>
            <td></td>
        </tr>
    """
    
    # 테이블 닫기
    html += """
        </tbody>
    </table>
    """
    
    return html

def generate_consultant_cards(results: Dict) -> str:
    """
    상담사별 카드 UI HTML 생성 함수
    
    Args:
        results: 분석 결과 딕셔너리
        
    Returns:
        str: HTML 카드 UI
    """
    if not results:
        return "<p>분석 결과가 없습니다.</p>"
    
    html = """
    <style>
    .card-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-start;
        gap: 15px;
        margin-top: 20px;
    }
    .consultant-card {
        width: 300px;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        background-color: white;
        position: relative;
    }
    .consultant-card.crm {
        border-left: 5px solid #4472c4;
    }
    .consultant-card.online {
        border-left: 5px solid #ed7d31;
    }
    .consultant-card.other {
        border-left: 5px solid #a5a5a5;
    }
    .consultant-name {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #333;
    }
    .consultant-team {
        position: absolute;
        top: 10px;
        right: 10px;
        font-size: 12px;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: bold;
    }
    .consultant-team.crm {
        background-color: #e6f0ff;
        color: #4472c4;
    }
    .consultant-team.online {
        background-color: #ffeee5;
        color: #ed7d31;
    }
    .consultant-team.other {
        background-color: #f0f0f0;
        color: #666;
    }
    .data-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 5px;
        margin-top: 10px;
    }
    .data-item {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px dashed #eee;
    }
    .data-label {
        font-size: 13px;
        color: #666;
    }
    .data-value {
        font-size: 13px;
        font-weight: bold;
        color: #333;
    }
    .data-value.highlight {
        color: #4472c4;
    }
    .summary-bar {
        height: 8px;
        background-color: #f0f0f0;
        border-radius: 4px;
        margin-top: 15px;
        overflow: hidden;
    }
    .bar-segment {
        height: 100%;
        float: left;
    }
    .bar-anma {
        background-color: #4472c4;
    }
    .bar-lacloud {
        background-color: #ed7d31;
    }
    .bar-water {
        background-color: #70ad47;
    }
    .legend {
        display: flex;
        justify-content: center;
        margin-top: 5px;
        flex-wrap: wrap;
        gap: 10px;
    }
    .legend-item {
        display: flex;
        align-items: center;
        font-size: 11px;
        color: #666;
    }
    .legend-color {
        width: 10px;
        height: 10px;
        margin-right: 5px;
        border-radius: 2px;
    }
    .collapsible-control {
        display: block;
        width: 100%;
        text-align: center;
        margin-top: 20px;
        border: none;
        background: #f0f0f0;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
        font-weight: bold;
        color: #333;
    }
    .collapsible-control:hover {
        background: #e0e0e0;
    }
    </style>
    
    <!-- Collapsible control -->
    <button class="collapsible-control" id="toggleCards">카드 보기 / 숨기기</button>
    
    <!-- Card container - initially hidden -->
    <div class="card-container" id="cardContainer" style="display: none;">
    """
    
    # 각 상담사별 카드 생성
    for consultant_data in results['consultant_data']:
        team = consultant_data['조직']
        team_class = "crm" if team == "CRM팀" else "online" if team == "온라인팀" else "other"
        
        # 누적 비율 계산 (안마의자, 라클라우드, 정수기)
        total_count = consultant_data['누적건수']
        if total_count > 0:
            anma_percent = (consultant_data['안마의자'] / total_count) * 100
            lacloud_percent = (consultant_data['라클라우드'] / total_count) * 100
            water_percent = (consultant_data['정수기'] / total_count) * 100
        else:
            anma_percent = lacloud_percent = water_percent = 0
        
        html += f"""
        <div class="consultant-card {team_class}">
            <div class="consultant-name">{consultant_data['상담사']}</div>
            <div class="consultant-team {team_class}">{team}</div>
            
            <div class="data-grid">
                <div class="data-item">
                    <span class="data-label">누적건수:</span>
                    <span class="data-value highlight">{consultant_data['누적건수']}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">누적매출액:</span>
                    <span class="data-value highlight">{consultant_data['누적매출액']:.1f}백만</span>
                </div>
                <div class="data-item">
                    <span class="data-label">안마의자:</span>
                    <span class="data-value">{consultant_data['안마의자']}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">라클라우드:</span>
                    <span class="data-value">{consultant_data['라클라우드']}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">정수기:</span>
                    <span class="data-value">{consultant_data['정수기']}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">일일건수:</span>
                    <span class="data-value">{consultant_data['일일건수']}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">콜건수:</span>
                    <span class="data-value">{consultant_data['콜건수']}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">콜타임:</span>
                    <span class="data-value">{consultant_data['콜타임']}</span>
                </div>
            </div>
            
            <div class="summary-bar">
                <div class="bar-segment bar-anma" style="width: {anma_percent}%;"></div>
                <div class="bar-segment bar-lacloud" style="width: {lacloud_percent}%;"></div>
                <div class="bar-segment bar-water" style="width: {water_percent}%;"></div>
            </div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #4472c4;"></div>
                    <span>안마의자</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #ed7d31;"></div>
                    <span>라클라우드</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #70ad47;"></div>
                    <span>정수기</span>
                </div>
            </div>
        </div>
        """
    
    # 컨테이너 닫기 및 JavaScript 추가
    html += """
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        var toggleButton = document.getElementById('toggleCards');
        var cardContainer = document.getElementById('cardContainer');
        
        // 토글 버튼 클릭 이벤트
        toggleButton.addEventListener('click', function() {
            if (cardContainer.style.display === 'none') {
                cardContainer.style.display = 'flex';
                toggleButton.textContent = '카드 숨기기';
            } else {
                cardContainer.style.display = 'none';
                toggleButton.textContent = '카드 보기';
            }
        });
    });
    </script>
    """
    
    return html

def show_consultant_management():
    """상담사 관리 UI를 표시하는 함수"""
    st.subheader("상담사 관리")
    
    # 상담사 목록 로드
    consultants = load_consultants()
    
    # 변경사항 감지를 위한 플래그
    changes_made = False
    
    # 탭으로 팀별 구분
    tab1, tab2 = st.tabs(["CRM팀", "온라인팀"])
    
    with tab1:
        st.write("CRM팀 상담사 목록")
        
        # CRM팀 상담사 목록 표시
        crm_consultants = consultants.get("CRM팀", [])
        
        # 상담사 추가
        new_crm_consultant = st.text_input("새 CRM팀 상담사 이름", key="new_crm_consultant")
        if st.button("추가", key="add_crm"):
            if new_crm_consultant and new_crm_consultant not in crm_consultants:
                add_consultant("CRM팀", new_crm_consultant)
                changes_made = True
                st.success(f"'{new_crm_consultant}' 상담사가 CRM팀에 추가되었습니다.")
            elif new_crm_consultant in crm_consultants:
                st.warning(f"'{new_crm_consultant}' 상담사는 이미 CRM팀에 있습니다.")
            else:
                st.warning("상담사 이름을 입력하세요.")
        
        # 상담사 목록 (삭제 버튼 포함)
        for i, consultant in enumerate(crm_consultants):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"{i+1}. {consultant}")
            with col2:
                if st.button("삭제", key=f"del_crm_{i}"):
                    remove_consultant("CRM팀", consultant)
                    changes_made = True
                    st.warning(f"'{consultant}' 상담사가 CRM팀에서 제거되었습니다.")
    
    with tab2:
        st.write("온라인팀 상담사 목록")
        
        # 온라인팀 상담사 목록 표시
        online_consultants = consultants.get("온라인팀", [])
        
        # 상담사 추가
        new_online_consultant = st.text_input("새 온라인팀 상담사 이름", key="new_online_consultant")
        if st.button("추가", key="add_online"):
            if new_online_consultant and new_online_consultant not in online_consultants:
                add_consultant("온라인팀", new_online_consultant)
                changes_made = True
                st.success(f"'{new_online_consultant}' 상담사가 온라인팀에 추가되었습니다.")
            elif new_online_consultant in online_consultants:
                st.warning(f"'{new_online_consultant}' 상담사는 이미 온라인팀에 있습니다.")
            else:
                st.warning("상담사 이름을 입력하세요.")
        
        # 상담사 목록 (삭제 버튼 포함)
        for i, consultant in enumerate(online_consultants):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"{i+1}. {consultant}")
            with col2:
                if st.button("삭제", key=f"del_online_{i}"):
                    remove_consultant("온라인팀", consultant)
                    changes_made = True
                    st.warning(f"'{consultant}' 상담사가 온라인팀에서 제거되었습니다.")
    
    # 변경사항이 있으면 페이지 새로고침
    if changes_made:
        st.experimental_rerun()

def show():
    """일일 승인 현황 탭 UI를 표시하는 메인 함수"""
    
    # CSS 스타일 적용
    st.markdown(DAILY_APPROVAL_TAB_STYLE, unsafe_allow_html=True)
    st.markdown(DAILY_APPROVAL_CARD_STYLE, unsafe_allow_html=True)
    
    # 타이틀 및 설명
    st.title("📊 일일/누적 승인 현황")
    st.markdown(DAILY_APPROVAL_DESCRIPTION, unsafe_allow_html=True)
    
    # 세션 상태 초기화 (딕셔너리 방식)
    session_defaults = {
        'daily_approval_df': None,
        'daily_calltime_df': None,
        'daily_approval_results': None,
        'processing': False
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # 상담사 관리 섹션 (Expander로 숨김)
    with st.expander("👥 상담사 관리", expanded=False):
        show_consultant_management()
    
    # 파일 업로드 UI
    st.subheader("📄 데이터 파일 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 승인 파일 첨부")
        approval_file = st.file_uploader("승인 엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="daily_approval_data_file")
    
    with col2:
        st.markdown("### 콜타임 파일 첨부")
        calltime_file = st.file_uploader("콜타임 엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="daily_approval_calltime_file")
    
    # 분석 버튼
    analyze_button = st.button("분석 시작", key="analyze_daily_approval")
    
    # 메인 로직
    if analyze_button and approval_file is not None:
        if not st.session_state.processing:
            st.session_state.processing = True

            # 진행 상황 표시를 위한 placeholder
            progress_placeholder = st.empty()

            try:
                # 파일 처리 진행 상태 표시
                progress_placeholder.info('🔄 파일 분석 중...')

                # 파일 위치 저장을 위해 seek(0)
                approval_file.seek(0)
                if calltime_file is not None:
                    calltime_file.seek(0)

                # 파일 처리 시도
                approval_df, approval_error = process_approval_file(approval_file)

                calltime_df = None
                calltime_error = None
                if calltime_file is not None:
                    calltime_df, calltime_error = process_calltime_file(calltime_file)

                # 오류 체크
                if approval_error:
                    st.error(approval_error)
                    st.session_state.processing = False
                    progress_placeholder.empty()
                elif calltime_file is not None and calltime_error:
                    st.error(calltime_error)
                    st.session_state.processing = False
                    progress_placeholder.empty()
                else:
                    # 세션 상태에 데이터프레임 저장
                    st.session_state.daily_approval_df = approval_df
                    st.session_state.daily_calltime_df = calltime_df

                    progress_placeholder.info('🔄 데이터 분석 중...')

                    # 분석 실행
                    results, analysis_error = analyze_daily_approval(approval_df)

                    if analysis_error:
                        st.error(analysis_error)
                        st.session_state.processing = False
                        progress_placeholder.empty()
                    else:
                        # 콜타임 데이터 매칭 (있는 경우)
                        if calltime_df is not None:
                            results = match_consultant_calltime(results, calltime_df)

                        # 세션 상태에 결과 저장
                        st.session_state.daily_approval_results = results
                        st.session_state.processing = False

                        progress_placeholder.success('✅ 분석 완료!')

                        # 결과 표시
                        display_results(
                            st.session_state.daily_approval_results,
                            st.session_state.daily_approval_df
                        )

            except Exception as e:
                st.error(f"❌ 처리 중 오류 발생: {str(e)}")
                st.session_state.processing = False
                progress_placeholder.empty()
    
    # 이미 분석된 결과가 있으면 표시
    elif st.session_state.daily_approval_results is not None:
        display_results(
            st.session_state.daily_approval_results,
            st.session_state.daily_approval_df
        )
    else:
        # 파일 업로드 전 안내 화면
        st.info("승인 파일을 업로드하고 콜타임 파일(선택사항)도 업로드한 후 분석 시작 버튼을 클릭하세요.")
        st.markdown(USAGE_GUIDE_MARKDOWN, unsafe_allow_html=True)

def display_results(results: Dict, approval_df: pd.DataFrame):
    """
    분석 결과를 표시하는 함수
    
    Args:
        results: 분석 결과 딕셔너리
        approval_df: 원본 승인 데이터프레임
    """
    # 현재 날짜 및 시간 가져오기
    current_time = datetime.now()
    
    # 데이터 정보 표시
    st.markdown(f'<div class="status-container"><div class="status-chip success">분석 완료</div><div class="timestamp">{current_time.strftime("%Y년 %m월 %d일 %H시 %M분")} 기준</div></div>', unsafe_allow_html=True)
    
    # 전체 상담사 수와 테이블 스타일 정보
    consultant_count = len(results['consultant_data'])
    st.write(f"총 {consultant_count}명의 상담원 실적이 분석되었습니다.")
    
    # 결과 테이블 표시
    st.markdown("<h3>일일/누적 승인 현황 표</h3>", unsafe_allow_html=True)
    table_html = generate_daily_approval_table(results)
    st.markdown(table_html, unsafe_allow_html=True)
    
    # 상담사별 카드 UI
    cards_html = generate_consultant_cards(results)
    st.markdown(cards_html, unsafe_allow_html=True)
    
    # 시각화 섹션 - 접을 수 있게 수정
    with st.expander("📈 데이터 시각화", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # 누적 제품별 건수 막대 그래프
            fig1 = px.bar(
                x=["안마의자", "라클라우드", "정수기"],
                y=[results['total_data']['anma_count'], 
                   results['total_data']['lacloud_count'],
                   results['total_data']['water_count']],
                labels={"x": "제품", "y": "누적 건수"},
                title="제품별 누적 건수",
                color_discrete_sequence=['#4472c4', '#ed7d31', '#70ad47']
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # 누적 제품별 매출액 파이 차트
            fig2 = px.pie(
                names=["안마의자", "라클라우드", "정수기"],
                values=[results['total_data']['anma_sales'], 
                        results['total_data']['lacloud_sales'],
                        results['total_data']['water_sales']],
                title="제품별 누적 매출액 비율",
                color_discrete_sequence=['#4472c4', '#ed7d31', '#70ad47']
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            # 일일 제품별 건수 막대 그래프
            fig3 = px.bar(
                x=["안마의자", "라클라우드", "정수기"],
                y=[results['daily_data']['anma_count'], 
                   results['daily_data']['lacloud_count'],
                   results['daily_data']['water_count']],
                labels={"x": "제품", "y": "일일 건수"},
                title=f"일일 제품별 건수 ({results['latest_date'].strftime('%Y-%m-%d')})",
                color_discrete_sequence=['#4472c4', '#ed7d31', '#70ad47']
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        with col4:
            # 일일 제품별 매출액 파이 차트
            fig4 = px.pie(
                names=["안마의자", "라클라우드", "정수기"],
                values=[results['daily_data']['anma_sales'], 
                        results['daily_data']['lacloud_sales'],
                        results['daily_data']['water_sales']],
                title=f"일일 제품별 매출액 비율 ({results['latest_date'].strftime('%Y-%m-%d')})",
                color_discrete_sequence=['#4472c4', '#ed7d31', '#70ad47']
            )
            st.plotly_chart(fig4, use_container_width=True)
    
    # 엑셀 내보내기
    st.subheader("📥 엑셀 파일 다운로드")
    st.markdown(DOWNLOAD_BUTTON_STYLE, unsafe_allow_html=True)
    
    try:
        # 현재 날짜와 UUID 생성
        today = datetime.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4())[:4]  # UUID 앞 4자리만 사용
        file_prefix = f"{today}_{unique_id}_"
        
        # 엑셀 파일 생성
        excel_data = create_excel_report(results, approval_df)
        
        if excel_data:
            # 다운로드 링크 생성
            b64 = base64.b64encode(excel_data).decode()
            href = f'<div class="download-button-container"><a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{file_prefix}일일_누적_승인현황.xlsx" class="download-button">엑셀 다운로드 (2시트)</a></div>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.error("엑셀 파일 생성에 실패했습니다.")
    except Exception as e:
        st.error(f"엑셀 파일 다운로드 준비 중 오류가 발생했습니다: {str(e)}")