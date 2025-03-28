"""
상담원 실적 현황 UI 모듈

이 모듈은 상담원 실적 현황 탭의 UI 요소와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import base64
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Optional, Any

# 비즈니스 로직 가져오기
from consultant_logic import (
    process_consultant_file, process_calltime_file, 
    analyze_consultant_performance, create_excel_report
)
# CSS 스타일 가져오기
from consultant_styles import (
    CONSULTANT_TABLE_STYLE, CONSULTANT_SAMPLE_TABLE_STYLE,
    DOWNLOAD_BUTTON_STYLE, DATE_DISPLAY_STYLE,
    CONSULTANT_DESCRIPTION, USAGE_GUIDE_MARKDOWN
)
# 유틸리티 함수 가져오기
from utils import format_time, get_previous_business_day

def generate_compact_html_table(df: pd.DataFrame) -> str:
    """
    컴팩트한 HTML 테이블 생성 함수
    
    Args:
        df: 상담원 실적 데이터프레임
        
    Returns:
        str: HTML 테이블 코드
    """
    html = CONSULTANT_TABLE_STYLE
    
    # 테이블 컨테이너 시작
    html += '<div class="table-container"><table class="compact-table">'
    
    # 헤더 추가
    headers = [
        '순위', 
        '상담사', 
        '<span>안마의자</span>', 
        '<span>라클라우드</span>', 
        '<span>정수기</span>', 
        '<span>더케어</span>', 
        '<span>멤버십</span>', 
        '건수', 
        '콜건수', 
        '콜타임'
    ]
    html += '<thead><tr>'
    for header in headers:
        html += f'<th>{header}</th>'
    html += '</tr></thead>'
    
    # 본문 데이터 추가
    html += '<tbody>'
    
    # CRM 파트 먼저 처리
    crm_df = df[df['조직'] == 'CRM파트'].sort_values(by=['건수', '콜타임_초'], ascending=[False, False])
    row_num = 1
    for i, row in crm_df.iterrows():
        # CRM 요약인지 확인
        is_summary = row['상담사'] == 'CRM팀순위'
        row_class = 'summary-row' if is_summary else ''
        
        html += f'<tr class="{row_class}">'
        # 순위 부여
        rank = "총합/평균" if is_summary else row_num
        html += f'<td>{rank}</td>'
        
        # 상담사 이름
        html += f'<td>{row["상담사"]}</td>'
        
        # 안마의자, 라클라우드, 정수기, 더케어, 멤버십
        for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
            value = row[col]
            # 0 값을 '-'로 변환
            value = '-' if value == 0 else value
            html += f'<td>{value}</td>'
        
        # 콜건수, 콜타임
        html += f'<td>{row["콜건수"]}</td>'
        html += f'<td>{row["콜타임"]}</td>'
        html += '</tr>'
        
        if not is_summary:
            row_num += 1
    
    # CRM 요약 추가
    crm_summary = {
        "순위": "총합/평균",
        "상담사": "CRM팀순위",
        "안마의자": crm_df["안마의자"].sum(),
        "라클라우드": crm_df["라클라우드"].sum(),
        "정수기": crm_df["정수기"].sum(),
        "더케어": crm_df["더케어"].sum(),
        "멤버십": crm_df["멤버십"].sum(),
        "건수": crm_df["건수"].sum(),
        "콜건수": round(crm_df["콜건수"].mean(), 1),
        # 평균 콜타임 초를 계산하고 format_time 함수로 변환
        "콜타임": format_time(crm_df["콜타임_초"].mean())
    }
    
    html += '<tr class="summary-row">'
    html += '<td>총합/평균</td>'
    html += f'<td>{crm_summary["상담사"]}</td>'
    for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
        value = crm_summary[col]
        value = '-' if value == 0 else value
        html += f'<td>{value}</td>'
    html += f'<td>{crm_summary["콜건수"]}</td>'
    html += f'<td>{crm_summary["콜타임"]}</td>'
    html += '</tr>'
    
    # 온라인 파트 처리
    online_df = df[df['조직'] == '온라인파트'].sort_values(by=['건수', '콜타임_초'], ascending=[False, False])
    row_num = 1
    for i, row in online_df.iterrows():
        # 온라인 요약인지 확인
        is_summary = row['상담사'] == '온라인팀순위'
        row_class = 'summary-row' if is_summary else ''
        
        html += f'<tr class="{row_class}">'
        # 순위 부여
        rank = "총합/평균" if is_summary else row_num
        html += f'<td>{rank}</td>'
        
        # 상담사 이름
        html += f'<td>{row["상담사"]}</td>'
        
        # 안마의자, 라클라우드, 정수기, 더케어, 멤버십
        for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
            value = row[col]
            # 0 값을 '-'로 변환
            value = '-' if value == 0 else value
            html += f'<td>{value}</td>'
        
        # 콜건수, 콜타임
        html += f'<td>{row["콜건수"]}</td>'
        html += f'<td>{row["콜타임"]}</td>'
        html += '</tr>'
        
        if not is_summary:
            row_num += 1
    
    # 온라인 요약 추가
    if len(online_df) > 0:
        online_summary = {
            "순위": "총합/평균",
            "상담사": "온라인팀순위",
            "안마의자": online_df["안마의자"].sum(),
            "라클라우드": online_df["라클라우드"].sum(),
            "정수기": online_df["정수기"].sum(),
            "더케어": online_df["더케어"].sum(),
            "멤버십": online_df["멤버십"].sum(),
            "건수": online_df["건수"].sum(),
            "콜건수": round(online_df["콜건수"].mean(), 1),
            # 평균 콜타임 초를 계산하고 format_time 함수로 변환
            "콜타임": format_time(online_df["콜타임_초"].mean())
        }
        
        html += '<tr class="summary-row">'
        html += '<td>총합/평균</td>'
        html += f'<td>{online_summary["상담사"]}</td>'
        for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
            value = online_summary[col]
            value = '-' if value == 0 else value
            html += f'<td>{value}</td>'
        html += f'<td>{online_summary["콜건수"]}</td>'
        html += f'<td>{online_summary["콜타임"]}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    return html

def generate_compact_sample_html_table() -> str:
    """
    샘플 HTML 테이블 생성 함수
    
    Returns:
        str: 샘플 HTML 테이블 코드
    """
    html = CONSULTANT_SAMPLE_TABLE_STYLE
    
    # 테이블 컨테이너 시작
    html += '<div class="table-container"><table class="compact-table">'
    
    # 헤더 추가
    headers = ['순위', '상담사', '<span>안마의자</span>', '<span>라클라우드</span>', '<span>정수기</span>', '<span>더케어</span>', '<span>멤버십</span>', '건수', '콜건수', '콜타임']
    html += '<thead><tr>'
    for header in headers:
        html += f'<th>{header}</th>'
    html += '</tr></thead>'
    
    # CRM 파트 샘플 데이터
    html += '<tbody>'
    crm_data = [
        [1, '이승현', '-', '-', 3, 2, '-', 5, 53, '2:29:48'],
        [2, '유태경', '-', '-', 3, 1, '-', 4, 81, '1:41:45'],
        [3, '임명숙', '-', '-', 2, 1, '-', 3, 216, '2:32:51'],
        [4, '김미정', '-', '-', 2, 1, '-', 3, 247, '2:19:56'],
        [5, '장희경', '-', 1, 1, '-', 1, 3, 131, '1:58:41'],
        ['총합/평균', 'CRM팀순위', 1, 1, 22, 8, 2, 34, 132, '2:15:02']
    ]
    
    for row in crm_data:
        row_class = 'summary-row' if row[0] == '총합/평균' else ''
        html += f'<tr class="{row_class}">'
        for cell in row:
            html += f'<td>{cell}</td>'
        html += '</tr>'
    
    # 온라인 파트 샘플 데이터
    online_data = [
        [1, '김부자', 2, '-', '-', 1, '-', 3, 60, '2:37:15'],
        [2, '최진영', 1, '-', '-', 1, '-', 2, 59, '1:44:40'],
        ['총합/평균', '온라인팀순위', 3, '-', '-', 2, '-', 5, 59, '1:44:40']
    ]
    
    for row in online_data:
        row_class = 'summary-row' if row[0] == '총합/평균' else ''
        html += f'<tr class="{row_class}">'
        for cell in row:
            html += f'<td>{cell}</td>'
        html += '</tr>'
            
    html += '</tbody></table></div>'
    return html

def create_compact_visualization(performance_df: pd.DataFrame):
    """
    팀별 비교 시각화를 위한 컴팩트한 차트 생성
    
    Args:
        performance_df: 상담원 실적 데이터프레임
        
    Returns:
        plotly.Figure: 시각화 차트
    """
    # 팀별 제품 유형 합계 막대 그래프
    team_summary = performance_df.groupby("조직").agg(
        안마의자=("안마의자", "sum"),
        라클라우드=("라클라우드", "sum"),
        정수기=("정수기", "sum"),
        더케어=("더케어", "sum"),
        멤버십=("멤버십", "sum")
    ).reset_index()
    
    # 차트 설정 - 작은 크기와 간소화된 레이아웃
    fig = px.bar(
        team_summary,
        x="조직",
        y=["안마의자", "라클라우드", "정수기", "더케어", "멤버십"],
        title="팀별 제품 유형 합계",
        labels={"value": "건수", "variable": "제품 유형"},
        height=300,  # 높이 축소
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    # 레이아웃 간소화
    fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=40),  # 마진 축소
        legend=dict(
            orientation="h",  # 가로 방향 범례
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=8)  # 작은 폰트
        ),
        font=dict(size=10)  # 전체 폰트 크기 축소
    )
    
    # 축 레이블 간소화
    fig.update_xaxes(title_font=dict(size=10))
    fig.update_yaxes(title_font=dict(size=10))
    
    return fig

def show():
    """상담원 실적 현황 탭 UI를 표시하는 메인 함수"""
    
    # 타이틀 및 설명
    st.title("👥상담원 실적 현황")
    st.markdown(CONSULTANT_DESCRIPTION, unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if 'consultant_df' not in st.session_state:
        st.session_state.consultant_df = None
    if 'calltime_df' not in st.session_state:
        st.session_state.calltime_df = None
    if 'performance_df' not in st.session_state:
        st.session_state.performance_df = None
    
    # 파일 업로드 UI
    st.subheader("데이터 파일 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 상담주문계약내역 첨부")
        consultant_file = st.file_uploader("상담주문계약내역 엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="consultant_file")
    
    with col2:
        st.markdown("### 콜타임 첨부")
        calltime_file = st.file_uploader("콜타임 엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="calltime_file")
    
    # 메인 로직
    if consultant_file is not None and calltime_file is not None:
        # 파일 처리 진행 상태 표시
        with st.spinner('파일 처리 중...'):
            # 파일 위치 저장을 위해 seek(0)
            consultant_file.seek(0)
            calltime_file.seek(0)
            
            # 파일 처리 시도
            consultant_df, consultant_error = process_consultant_file(consultant_file)
            calltime_df, calltime_error = process_calltime_file(calltime_file)
        
        # 오류 체크
        if consultant_error:
            st.error(consultant_error)
        elif calltime_error:
            st.error(calltime_error)
        else:
            # 세션 상태에 데이터프레임 저장
            st.session_state.consultant_df = consultant_df
            st.session_state.calltime_df = calltime_df
            
            # 분석 실행
            performance_df, analysis_error = analyze_consultant_performance(consultant_df, calltime_df)
            
            if analysis_error:
                st.error(analysis_error)
            else:
                # 세션 상태에 결과 저장
                st.session_state.performance_df = performance_df
                
                # 결과 표시 (압축된 버전)
                st.markdown('<h3>상담원 실적 현황</h3>', unsafe_allow_html=True)
                
                # 날짜 및 시간 표시 추가
                current_time = datetime.now()
                # 오전 10시 30분 기준으로 표시 방식 결정
                cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)
                
                # 데이터 정보 표시
                st.write(f"총 {len(performance_df)}명의 상담원 실적이 분석되었습니다.")
                
                if current_time < cutoff_time:
                    # 이전 영업일 구하기 (공휴일 & 주말 제외)
                    prev_date = get_previous_business_day(current_time)
                    date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {prev_date.year}년 {prev_date.month}월 {prev_date.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 전체집계"
                else:
                    date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.year}년 {current_time.month}월 {current_time.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.hour}시{current_time.minute}분 기준"
                
                st.markdown(DATE_DISPLAY_STYLE.format(date_display=date_display), unsafe_allow_html=True)
                
                # 컴팩트 HTML 테이블 생성 및 표시
                html_table = generate_compact_html_table(performance_df)
                st.markdown(html_table, unsafe_allow_html=True)
                
                # 시각화 섹션 - 접을 수 있게 수정
                with st.expander("시각화 보기", expanded=False):
                    st.plotly_chart(create_compact_visualization(performance_df), use_container_width=True)
                
                # 엑셀 내보내기
                st.markdown("### 엑셀 파일 다운로드")
                st.markdown(DOWNLOAD_BUTTON_STYLE, unsafe_allow_html=True)

                # 엑셀 파일 생성
                excel_data = create_excel_report(performance_df)
                
                if excel_data:
                    # 다운로드 링크 생성
                    b64 = base64.b64encode(excel_data).decode()
                    href = f'<div style="text-align: center;"><a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="상담원_실적_현황.xlsx" class="download-button">엑셀 파일 다운로드</a></div>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("엑셀 파일 생성에 실패했습니다.")
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        # 파일 업로드 전 안내 화면
        st.info("상담주문계약내역과 콜타임 파일을 모두 업로드하면 분석이 시작됩니다.")
        
        # 샘플 데이터 표시
        st.markdown("### 표시 형식 샘플")
        
        # 현재 날짜 및 시간 표시 추가 (샘플에도 적용)
        current_time = datetime.now()
        # 오전 10시 30분 기준으로 표시 방식 결정
        cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)
        
        if current_time < cutoff_time:
            # 이전 영업일 구하기 (공휴일 & 주말 제외)
            prev_date = get_previous_business_day(current_time)
            date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {prev_date.year}년 {prev_date.month}월 {prev_date.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 전체집계"
        else:
            date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.year}년 {current_time.month}월 {current_time.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.hour}시{current_time.minute}분 기준"
        
        st.markdown(DATE_DISPLAY_STYLE.format(date_display=date_display), unsafe_allow_html=True)
        
        # 컴팩트 샘플 테이블 표시
        html_table = generate_compact_sample_html_table()
        st.markdown(html_table, unsafe_allow_html=True)
        
        # 간소화된 사용 가이드
        st.markdown(USAGE_GUIDE_MARKDOWN)
        st.markdown('</div>', unsafe_allow_html=True)