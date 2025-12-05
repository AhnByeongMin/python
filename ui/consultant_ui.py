"""
상담원 실적 현황 UI 모듈

이 모듈은 상담원 실적 현황 탭의 UI 요소와 사용자 상호작용을 처리합니다.
비즈니스 로직과 UI를 분리하여 유지보수성을 향상시킵니다.
"""

import streamlit as st
import pandas as pd
import base64
import plotly.express as px
from datetime import datetime, time
import uuid
from typing import Dict, List, Optional, Any

# 비즈니스 로직 가져오기
from logic.consultant_logic import (
    process_consultant_file, process_calltime_file, 
    analyze_consultant_performance, create_excel_report
)
# CSS 스타일 가져오기
from styles.consultant_styles import (
    CONSULTANT_TABLE_STYLE, CONSULTANT_SAMPLE_TABLE_STYLE,
    DOWNLOAD_BUTTON_STYLE, DATE_DISPLAY_STYLE,
    CONSULTANT_DESCRIPTION, USAGE_GUIDE_MARKDOWN
)
# 유틸리티 함수 가져오기
from utils.utils import format_time, get_previous_business_day, is_holiday
from utils.consultant_manager import (
    load_consultants, save_consultants, add_consultant, remove_consultant,
    add_team, remove_team, get_all_teams, get_part_name, get_team_name
)
from utils.trainee_group_manager import (
    load_trainee_groups, add_trainee_group, remove_trainee_group,
    get_trainee_group_target, update_trainee_group
)

# 근무 설정 상수
WORK_CONFIG = {
    "평일근무": {
        "target_hours": 3,
        "target_minutes": 30,
        "work_start": "09:30",
        "lunch_start": "11:50",
        "lunch_end": "13:00",
        "work_end": "18:30"
    },
    "휴일근무": {
        "target_hours": 2,
        "target_minutes": 0,
        "work_start": "10:00",
        "lunch_start": "12:30",
        "lunch_end": "13:00",
        "work_end": "15:30"
    }
}

def get_work_config(target_date=None, manual_config=None):
    """
    근무 설정을 반환합니다.

    Args:
        target_date: 목표 날짜 (None이면 오늘)
        manual_config: 수동 설정 딕셔너리 (None이면 자동)

    Returns:
        dict: 근무 설정
    """
    # 1. 수동 설정 최우선
    if manual_config is not None:
        return manual_config

    # 2. 자동 감지
    if target_date is None:
        target_date = datetime.now()

    # 3. 휴일 여부 확인 (기존 is_holiday 함수 활용)
    if is_holiday(target_date):
        return WORK_CONFIG["휴일근무"]
    else:
        return WORK_CONFIG["평일근무"]

def calculate_target_calltime_seconds(current_time=None, work_config=None):
    """
    현재 시간 기준으로 목표 콜타임을 계산합니다.

    Args:
        current_time: 현재 시간 (None일 경우 실제 현재 시간 사용)
        work_config: 근무 설정 딕셔너리 (None이면 기본 평일 설정)

    Returns:
        int: 현재 시간까지 목표 콜타임 (초 단위)
    """
    if current_time is None:
        current_time = datetime.now().time()

    # 기본 설정 (평일)
    if work_config is None:
        work_config = WORK_CONFIG["평일근무"]

    # 목표 시간 (초)
    total_target_seconds = (
        work_config["target_hours"] * 3600 +
        work_config["target_minutes"] * 60
    )

    # 근무 시간 파싱
    work_start = time(*map(int, work_config["work_start"].split(":")))
    lunch_start = time(*map(int, work_config["lunch_start"].split(":")))
    lunch_end = time(*map(int, work_config["lunch_end"].split(":")))
    work_end = time(*map(int, work_config["work_end"].split(":")))

    # 전체 근무 시간 (점심 시간 제외, 분 단위)
    total_work_minutes = (
        (work_end.hour * 60 + work_end.minute) -
        (work_start.hour * 60 + work_start.minute)
    ) - (
        (lunch_end.hour * 60 + lunch_end.minute) -
        (lunch_start.hour * 60 + lunch_start.minute)
    )
    
    # 분 단위로 현재 경과 근무 시간 계산
    elapsed_minutes = 0
    
    # 현재 시간이 업무 시작 시간 이전인 경우
    if current_time < work_start:
        return 0
    
    # 현재 시간이 업무 종료 시간 이후인 경우
    if current_time > work_end:
        return total_target_seconds
    
    # 현재 시간이 오전 업무 시간인 경우
    if work_start <= current_time < lunch_start:
        elapsed_minutes = (current_time.hour * 60 + current_time.minute) - (work_start.hour * 60 + work_start.minute)

    # 현재 시간이 점심 시간인 경우
    elif lunch_start <= current_time < lunch_end:
        elapsed_minutes = (lunch_start.hour * 60 + lunch_start.minute) - (work_start.hour * 60 + work_start.minute)

    # 현재 시간이 오후 업무 시간인 경우
    elif lunch_end <= current_time <= work_end:
        morning_minutes = (lunch_start.hour * 60 + lunch_start.minute) - (work_start.hour * 60 + work_start.minute)
        afternoon_minutes = (current_time.hour * 60 + current_time.minute) - (lunch_end.hour * 60 + lunch_end.minute)
        elapsed_minutes = morning_minutes + afternoon_minutes
    
    # 현재 경과 근무 시간 비율에 따라 목표 콜타임 계산
    target_seconds = int((elapsed_minutes / total_work_minutes) * total_target_seconds)
    
    return target_seconds

def get_consultant_status_emoji(calltime_seconds, target_seconds):
    """
    콜타임 달성 상태에 따라 적절한 이모지를 반환합니다.
    
    Args:
        calltime_seconds: 상담원의 현재 콜타임 (초 단위)
        target_seconds: 현재 시간까지 목표 콜타임 (초 단위)
        
    Returns:
        str: 상태 이모지
    """
    # 달성률 계산 (%)
    if target_seconds == 0:
        achievement_rate = 100  # 목표가 0인 경우 (업무 시작 전)
    else:
        achievement_rate = (calltime_seconds / target_seconds) * 100
    
    # 달성률에 따른 이모지 반환
    if achievement_rate >= 100:  # 3시간반 초과 달성
        return "🚩"  # 달성 깃발발
    elif achievement_rate <= 71.4:  # 2시간반이하 페이스
        return "⏰"  # 알람시계 (관심 필요)
    else :
        return ""

    
def generate_compact_html_table(df: pd.DataFrame, is_previous_day: bool = False):
    """
    컴팩트한 HTML 테이블 생성 함수 - 콜타임 프로그레스 바 추가 버전
    
    Args:
        df: 상담원 실적 데이터프레임
        is_previous_day: 전날 데이터 조회 여부
        
    Returns:
        str: HTML 테이블 코드
    """
    html = CONSULTANT_TABLE_STYLE
    
    # 현재 날짜 및 시간 가져오기
    current_time = datetime.now()
    date_str = f"{current_time.month}월{current_time.day}일({['월','화','수','목','금','토','일'][current_time.weekday()]})"
    time_str = f"{current_time.hour}:{current_time.minute:02d}"
    
    # 목표 콜타임 계산 - 휴일/평일 구분 및 수동 설정 반영
    if is_previous_day:
        # 전날 데이터를 조회하는 경우
        prev_date = get_previous_business_day(current_time)
        work_config = get_work_config(
            target_date=prev_date,
            manual_config=st.session_state.get('manual_work_config')
        )
        current_target_seconds = (
            work_config["target_hours"] * 3600 +
            work_config["target_minutes"] * 60
        )
    else:
        # 당일 데이터를 조회하는 경우
        work_config = get_work_config(
            target_date=current_time,
            manual_config=st.session_state.get('manual_work_config')
        )
        current_target_seconds = calculate_target_calltime_seconds(
            current_time.time(),
            work_config
        )

    # 전체 목표 시간 (프로그레스 바 계산용)
    total_target_seconds = (
        work_config["target_hours"] * 3600 +
        work_config["target_minutes"] * 60
    )
       # 테이블 컨테이너 시작
    html += '<div class="table-container">'
    html += '<table class="compact-table">'
    
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
        '콜수', 
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
        is_summary = row['상담사'] == '총합/평균'
        row_class = 'summary-row' if is_summary else ''

        html += f'<tr class="{row_class}">'
        # 순위 부여
        rank = "총합/평균" if is_summary else row_num
        html += f'<td>{rank}</td>'

        # 상담사 이름 (신입에게 병아리 이모지 추가)
        consultant_name = row["상담사"]
        new_consultants = ['강하나', '김서윤', '구준모', '이은경', '이보람']
        if consultant_name in new_consultants:
            consultant_name = f'🐥 {consultant_name}'
        html += f'<td>{consultant_name}</td>'
        
        # 안마의자, 라클라우드, 정수기, 더케어, 멤버십
        for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
            value = row[col]
            # 0 값을 '-'로 변환
            value = '-' if value == 0 else value
            html += f'<td>{value}</td>'
        
        # 콜수
        html += f'<td>{row["콜건수"]}</td>'
        
        # 콜타임 (프로그레스 바 포함) - 이제 이모지도 포함
        if not is_summary:
            # 콜타임 초 데이터를 퍼센트로 변환 (최대 100%)
            percentage = min(100, (row["콜타임_초"] / total_target_seconds) * 100)
            
            # 상태 이모지 계산
            status_emoji = get_consultant_status_emoji(row["콜타임_초"], current_target_seconds)
            
            # 콜타임과 이모지를 함께 표시
            html += f'<td class="calltime-cell">{row["콜타임"]} {status_emoji}<div class="progress-bar-bg" style="width: {percentage}%;"></div></td>'
        else:
            # 요약행은 프로그레스 바 없이 표시
            html += f'<td>{row["콜타임"]}</td>'
        
        html += '</tr>'
        
        if not is_summary:
            row_num += 1
    
    # CRM 요약 추가
    crm_summary = {
        "순위": "CRM팀",
        "상담사": "총합/평균",
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
    html += f'<td>{crm_summary["순위"]}</td>'
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
        is_summary = row['상담사'] == '총합/평균'
        row_class = 'summary-row' if is_summary else ''

        html += f'<tr class="{row_class}">'
        # 순위 부여
        rank = "총합/평균" if is_summary else row_num
        html += f'<td>{rank}</td>'

        # 상담사 이름 (신입에게 병아리 이모지 추가)
        consultant_name = row["상담사"]
        new_consultants = ['강하나', '김서윤', '구준모', '이은경', '이보람']
        if consultant_name in new_consultants:
            consultant_name = f'🐥 {consultant_name}'
        html += f'<td>{consultant_name}</td>'
        
        # 안마의자, 라클라우드, 정수기, 더케어, 멤버십
        for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
            value = row[col]
            # 0 값을 '-'로 변환
            value = '-' if value == 0 else value
            html += f'<td>{value}</td>'
        
        # 콜수
        html += f'<td>{row["콜건수"]}</td>'
        
        # 콜타임 (프로그레스 바 포함) - 이제 이모지도 포함
        if not is_summary:
            # 콜타임 초 데이터를 퍼센트로 변환 (최대 100%)
            percentage = min(100, (row["콜타임_초"] / total_target_seconds) * 100)
            
            # 상태 이모지 계산
            status_emoji = get_consultant_status_emoji(row["콜타임_초"], current_target_seconds)
            
            # 콜타임과 이모지를 함께 표시
            html += f'<td class="calltime-cell">{row["콜타임"]} {status_emoji}<div class="progress-bar-bg" style="width: {percentage}%;"></div></td>'
        else:
            # 요약행은 프로그레스 바 없이 표시
            html += f'<td>{row["콜타임"]}</td>'
        
        html += '</tr>'
        
        if not is_summary:
            row_num += 1
    
    # 온라인 요약 추가
    if len(online_df) > 0:
        online_summary = {
            "순위": "온라인팀",
            "상담사": "총합/평균",
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
        html += f'<td>{online_summary["순위"]}</td>'
        html += f'<td>{online_summary["상담사"]}</td>'
        for col in ['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']:
            value = online_summary[col]
            value = '-' if value == 0 else value
            html += f'<td>{value}</td>'
        html += f'<td>{online_summary["콜건수"]}</td>'
        html += f'<td>{online_summary["콜타임"]}</td>'
        html += '</tr>'
    
    html += '</tbody></table>'
    
    # 요약 텍스트 박스 추가
    # 팀별 합계 계산
    crm_df = df[df['조직'] == 'CRM파트']
    online_df = df[df['조직'] == '온라인파트']
    
    crm_total = crm_df['건수'].sum()
    online_total = online_df['건수'].sum() if not online_df.empty else 0
    
    # 제품별 합계
    total_anma = df['안마의자'].sum()
    total_lacloud = df['라클라우드'].sum()
    total_water = df['정수기'].sum()
    total_thecare = df['더케어'].sum()
    total_membership = df['멤버십'].sum()
    
    # 총 건수
    grand_total = crm_total + online_total
    
    # 팀별 제품 내역
    crm_anma = crm_df['안마의자'].sum()
    crm_lacloud = crm_df['라클라우드'].sum()
    crm_water = crm_df['정수기'].sum()
    crm_thecare = crm_df['더케어'].sum()
    crm_membership = crm_df['멤버십'].sum()
    
    # CRM 팀 상세 정보 생성
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
    
    # 온라인 팀 상세 정보 생성
    online_details = "(0건)"
    if not online_df.empty:
        online_anma = online_df['안마의자'].sum()
        online_lacloud = online_df['라클라우드'].sum()
        online_water = online_df['정수기'].sum()
        online_thecare = online_df['더케어'].sum()
        online_membership = online_df['멤버십'].sum()
        
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
    if total_anma > 0:
        product_items.append(f'<div class="summary-textbox-product">💆 안마의자 {total_anma}건</div>')
    if total_lacloud > 0:
        product_items.append(f'<div class="summary-textbox-product">🛏️ 라클라우드 {total_lacloud}건</div>')
    if total_water > 0:
        product_items.append(f'<div class="summary-textbox-product">💧 정수기 {total_water}건</div>')
    if total_thecare > 0:
        product_items.append(f'<div class="summary-textbox-product">🛠️ 더케어 {total_thecare}건</div>')
    if total_membership > 0:
        product_items.append(f'<div class="summary-textbox-product">🔖 멤버쉽 {total_membership}건</div>')
    
    product_html = '\n'.join(product_items)
    
    # 현재 목표 시간을 시간:분:초 형식으로 변환
    current_target_time = format_time(current_target_seconds)
    
    # 요약 텍스트 박스 HTML 직접 작성 (JavaScript 없이 단순하게)
    html += f'''
    <div class="summary-textbox">
        <div class="summary-textbox-title">{date_str} CRM팀 실적_{time_str}</div>
        <br>
        <div class="summary-textbox-team">🔄 CRM팀 : 총 {crm_total}건</div>
        <div>{crm_details}</div>
        <div class="summary-textbox-team">💻 온라인팀: 총 {online_total}건</div>
        <div>{online_details}</div>
        <br>
        {product_html}
        <br>
        <div class="summary-textbox-total">📊 총 건수 {grand_total}건</div>
        <div class="summary-textbox-info">⏱️ 현재 목표 시간: {current_target_time}</div>
        <div class="summary-textbox-legend">
            <span class="legend-item">🚩: 목표 달성</span>
            <span class="legend-item">⏰: 분발발 필요</span>
        </div>
    </div>
    '''
    
    html += '</div>'  # 테이블 컨테이너 닫기
    return html

def generate_compact_sample_html_table() -> str:
    """
    샘플 HTML 테이블 생성 함수 - 콜타임 프로그레스 바 추가 버전
    
    Returns:
        str: 샘플 HTML 테이블 코드
    """
    html = CONSULTANT_TABLE_STYLE
    
    # 현재 날짜 및 시간 가져오기
    current_time = datetime.now()
    date_str = f"{current_time.month}월{current_time.day}일({['월','화','수','목','금','토','일'][current_time.weekday()]})"
    time_str = f"{current_time.hour}:{current_time.minute:02d}"
    
    # 10시 30분 기준으로 표시 방식 결정
    cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)
    is_previous_day = current_time < cutoff_time

    # 목표 콜타임 계산 - 휴일/평일 구분 및 수동 설정 반영
    if is_previous_day:
        # 전날 데이터를 조회하는 경우
        prev_date = get_previous_business_day(current_time)
        work_config = get_work_config(
            target_date=prev_date,
            manual_config=st.session_state.get('manual_work_config')
        )
        current_target_seconds = (
            work_config["target_hours"] * 3600 +
            work_config["target_minutes"] * 60
        )
        current_target_time = format_time(current_target_seconds)
    else:
        # 당일 데이터를 조회하는 경우
        work_config = get_work_config(
            target_date=current_time,
            manual_config=st.session_state.get('manual_work_config')
        )
        current_target_seconds = calculate_target_calltime_seconds(
            current_time.time(),
            work_config
        )
        current_target_time = format_time(current_target_seconds)

    # 전체 목표 시간 (프로그레스 바 계산용)
    total_target_seconds = (
        work_config["target_hours"] * 3600 +
        work_config["target_minutes"] * 60
    )
    
    # 테이블 컨테이너 시작
    html += '<div class="table-container">'
    html += '<table class="compact-table">'
    
    # 헤더 추가
    headers = ['순위', '상담사', '<span>안마의자</span>', '<span>라클라우드</span>', '<span>정수기</span>', '<span>더케어</span>', '<span>멤버십</span>', '건수', '콜수', '콜타임']
    html += '<thead><tr>'
    for header in headers:
        html += f'<th>{header}</th>'
    html += '</tr></thead>'
    
    # 목표 시간을 초 단위로 변환 (이미 위에서 계산된 total_target_seconds 사용)
    target_seconds = total_target_seconds
    
    # 각 시간 문자열을 초로 변환하는 함수
    def time_to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        return 0
    
    # CRM 파트 샘플 데이터
    html += '<tbody>'
    crm_data = [
        [1, '이승현', '-', '-', 5, 5, '-', 5, 55, '2:34:18'],
        [2, '유태경', '-', '-', 4, 4, '-', 4, 91, '1:50:16'],
        [3, '임명숙', '-', '-', 3, 3, '-', 3, 91, '2:49:10'],
        [4, '임명숙', '-', '-', 3, 3, '-', 3, 217, '2:33:39'],
        [5, '김미정', '-', '-', 3, 3, '-', 3, 247, '2:19:56'],
        ['CRM팀', '총합/평균', 1, 1, 32, 34, 1, 34, 134, '2:18:39']
    ]
    
    for row in crm_data:
        is_summary = row[0] == 'CRM팀'
        row_class = 'summary-row' if is_summary else ''
        html += f'<tr class="{row_class}">'
        
        # 처음 열: 순위
        if is_summary:
            html += f'<td>{row[0]}</td>'
        else:
            html += f'<td>{row[0]}</td>'
        
        # 두 번째 열: 상담사 이름 (이모지 제거)
        html += f'<td>{row[1]}</td>'
            
        # 나머지 필드는 그대로 표시
        for i in range(2, 9):
            html += f'<td>{row[i]}</td>'
        
        # 콜타임은 프로그레스 바와 함께 표시 (이모지도 함께 표시)
        if not is_summary:
            call_time = row[9]
            seconds = time_to_seconds(call_time)
            percentage = min(100, (seconds / target_seconds) * 100)
            
            # 상태 이모지 계산
            status_emoji = get_consultant_status_emoji(seconds, current_target_seconds)
            
            html += f'<td class="calltime-cell">{call_time} {status_emoji}<div class="progress-bar-bg" style="width: {percentage}%;"></div></td>'
        else:
            html += f'<td>{row[9]}</td>'
        
        html += '</tr>'
    
    # 온라인 파트 샘플 데이터
    online_data = [
        [1, '김부자', 2, '-', '-', 1, '-', 3, 60, '2:37:15'],
        [2, '최진영', 1, '-', '-', 1, '-', 2, 59, '1:44:40'],
        ['온라인팀', '총합/평균', 3, '-', '-', 2, '-', 5, 59, '2:10:58']
    ]
    
    for row in online_data:
        is_summary = row[0] == '온라인팀'
        row_class = 'summary-row' if is_summary else ''
        html += f'<tr class="{row_class}">'
        
        # 첫 번째 열: 순위
        if is_summary:
            html += f'<td>{row[0]}</td>'
        else:
            html += f'<td>{row[0]}</td>'
        
        # 두 번째 열: 상담사 이름 (이모지 제거)
        html += f'<td>{row[1]}</td>'
            
        # 나머지 필드는 그대로 표시
        for i in range(2, 9):
            html += f'<td>{row[i]}</td>'
        
        # 콜타임은 프로그레스 바와 함께 표시 (이모지도 함께 표시)
        if not is_summary:
            call_time = row[9]
            seconds = time_to_seconds(call_time)
            percentage = min(100, (seconds / target_seconds) * 100)
            
            # 상태 이모지 계산
            status_emoji = get_consultant_status_emoji(seconds, current_target_seconds)
            
            html += f'<td class="calltime-cell">{call_time} {status_emoji}<div class="progress-bar-bg" style="width: {percentage}%;"></div></td>'
        else:
            html += f'<td>{row[9]}</td>'
        
        html += '</tr>'
            
    html += '</tbody></table>'
    
    # 요약 텍스트 박스 추가 (샘플 데이터 직접 하드코딩)
    html += f'''
    <div class="summary-textbox">
        <div class="summary-textbox-title">{date_str} CRM팀 실적_{time_str}</div>
        <br>
        <div class="summary-textbox-team">🔄 CRM팀 : 총 30건</div>
        <div>(안마 1건, 라클 3건, 정수기 24건, 더케어 1건, 멤버쉽 1건)</div>
        <div class="summary-textbox-team">💻 온라인팀: 총 9건</div>
        <div>(안마 5건, 라클 3건, 정수기 1건)</div>
        <br>
        <div class="summary-textbox-product">💆 안마의자 6건</div>
        <div class="summary-textbox-product">🛏️ 라클라우드 6건</div>
        <div class="summary-textbox-product">💧 정수기 25건</div>
        <div class="summary-textbox-product">🛠️ 더케어 1건</div>
        <div class="summary-textbox-product">🔖 멤버쉽 1건</div>
        <br>
        <div class="summary-textbox-total">📊 총 건수 39건</div>
        <div class="summary-textbox-info">⏱️ 현재 목표 시간: {current_target_time}</div>
        <div class="summary-textbox-legend">
            <span class="legend-item">🚩: 목표 달성</span>
            <span class="legend-item">⏰: 목표 미달</span>
        </div>
    </div>
    '''
    
    html += '</div>'  # 테이블 컨테이너 닫기
    return html
        

def create_compact_visualization(performance_df: pd.DataFrame):
    """
    팀별 비교 시각화를 위한 컴팩트한 차트 생성
    빈 공간 없이 막대가 연속적으로 표시되는 방식
    배경 및 그리드 스타일 개선
    
    Args:
        performance_df: 상담원 실적 데이터프레임
        
    Returns:
        plotly.Figure: 시각화 차트
    """
    import plotly.graph_objects as go
    import pandas as pd
    import plotly.express as px
    
    # 데이터 준비 - 팀별 요약
    team_summary = performance_df.groupby("조직").agg(
        안마의자=("안마의자", "sum"),
        라클라우드=("라클라우드", "sum"),
        정수기=("정수기", "sum"),
        더케어=("더케어", "sum"),
        멤버십=("멤버십", "sum"),
        총건수=("건수", "sum")
    ).reset_index()
    
    # 색상 설정 - 더 선명한 색상으로 변경
    colors = {
        "안마의자": "#66c2a5",
        "라클라우드": "#fcfc99",
        "정수기": "#8da0cb",
        "더케어": "#fc8d62",
        "멤버십": "#80b1d3",
        "총건수": "#4472C4"  # 더 진한 파란색으로 총건수 강조
    }
    
    # 팀별 데이터 정리
    team_data = {}
    for team in team_summary["조직"].unique():
        team_rows = team_summary[team_summary["조직"] == team].iloc[0]
        
        # 0건이 아닌 제품만 필터링
        non_zero_products = {}
        for product in ["안마의자", "라클라우드", "정수기", "더케어", "멤버십"]:
            if team_rows[product] > 0:
                non_zero_products[product] = team_rows[product]
        
        # 총건수 항상 포함
        non_zero_products["총건수"] = team_rows["총건수"]
        
        team_data[team] = non_zero_products
    
    # 기본 그래프 생성 - Plotly Express 사용
    # 0건이 아닌 제품만 포함하는 데이터프레임 생성
    plot_data = []
    
    for team, products in team_data.items():
        for product, value in products.items():
            plot_data.append({
                "팀": team,
                "제품": product,
                "건수": value
            })
    
    # 데이터프레임 생성
    plot_df = pd.DataFrame(plot_data)
    
    # 제품 유형 순서 지정 (총건수가 맨 마지막에 오도록)
    category_order = ["안마의자", "라클라우드", "정수기", "더케어", "멤버십", "총건수"]
    
    # Plotly Express로 그래프 생성
    fig = px.bar(
        plot_df,
        x="팀",
        y="건수",
        color="제품",
        barmode="group",
        color_discrete_map=colors,
        category_orders={"제품": category_order},
        text="건수",
        title="팀별 제품 유형 및 총건수 비교"
    )
    
    # 총건수 막대 강조
    for trace in fig.data:
        if trace.name == "총건수":
            trace.marker.line.width = 1.5
            trace.marker.line.color = "black"
    
    # 레이아웃 설정 - 그리드 및 배경 개선
    fig.update_layout(
        # 높이 및 여백 설정
        height=350,
        margin=dict(l=40, r=40, t=60, b=40),
        
        # 범례 설정
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        ),
        
        # 폰트 설정
        font=dict(size=10),
        
        # 배경 설정
        plot_bgcolor="rgba(240, 240, 240, 0.2)",  # 연한 회색 배경
        paper_bgcolor="rgba(0, 0, 0, 0)",  # 투명 배경
        
        # 그리드 설정
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(211, 211, 211, 0.3)"  # 연한 회색 그리드
        ),
        xaxis=dict(
            showgrid=False  # x축 그리드 미표시
        )
    )
    
    # 스타일 개선
    fig.update_traces(
        textposition='outside',  # 텍스트 위치
        textfont_size=9,         # 텍스트 크기
        width=0.7                # 막대 너비 조정
    )
    
    # 빈 공간 최소화
    fig.update_layout(
        bargap=0.2,        # 팀 사이 간격
        bargroupgap=0.02   # 막대 간 간격
    )
    
    return fig

def show():
    """상담원 실적 현황 탭 UI를 표시하는 메인 함수"""
    
    # 타이틀 및 설명
    st.title("👥상담원 실적 현황")
    st.markdown(CONSULTANT_DESCRIPTION, unsafe_allow_html=True)

    # ========== 근무 설정 UI ==========
    with st.expander("⚙️ 근무 설정", expanded=False):
        # 세션 상태 초기화
        if 'work_mode' not in st.session_state:
            st.session_state.work_mode = "자동 감지"
        if 'manual_work_config' not in st.session_state:
            st.session_state.manual_work_config = None

        # 모드 선택
        work_mode = st.radio(
            "설정 모드",
            ["자동 감지", "수동 설정"],
            horizontal=True,
            key="work_mode"
        )

        st.markdown("---")

        # 현재 상태 표시
        current_date = datetime.now()
        is_today_holiday = is_holiday(current_date)
        work_type_text = "🏖️ 휴일근무" if is_today_holiday else "🏢 평일근무"
        default_target = "2시간" if is_today_holiday else "3시간 30분"

        st.info(f"""
**📅 현재 상태**
- 오늘: {current_date.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][current_date.weekday()]})
- 근무 유형: {work_type_text}
- 기본 목표: {default_target}
        """)

        if work_mode == "수동 설정":
            st.markdown("---")

            # 전일자 조회 옵션
            if 'force_previous_day' not in st.session_state:
                st.session_state.force_previous_day = False

            force_previous_day = st.checkbox(
                "🔙 전일자 조회 모드 (10시 30분 이후에도 전날 데이터 조회)",
                value=st.session_state.force_previous_day,
                key="force_previous_day_checkbox"
            )
            st.session_state.force_previous_day = force_previous_day

            if force_previous_day:
                prev_date = get_previous_business_day(datetime.now())
                st.info(f"📅 전일자 조회: {prev_date.year}년 {prev_date.month}월 {prev_date.day}일 ({['월','화','수','목','금','토','일'][prev_date.weekday()]})")

            st.markdown("---")
            st.markdown("### 🎯 전체 목표 시간 설정")

            # 프리셋 선택을 위한 임시 값 초기화
            if 'preset_hours' not in st.session_state:
                st.session_state.preset_hours = 3
            if 'preset_minutes' not in st.session_state:
                st.session_state.preset_minutes = 30

            # 빠른 프리셋 (위젯보다 먼저 배치)
            st.markdown("💡 **빠른 설정:**")
            preset_cols = st.columns(4)

            with preset_cols[0]:
                if st.button("평일 3.5h"):
                    st.session_state.preset_hours = 3
                    st.session_state.preset_minutes = 30
                    # 바로 적용
                    config = WORK_CONFIG["평일근무"].copy()
                    config["target_hours"] = 3
                    config["target_minutes"] = 30
                    st.session_state.manual_work_config = config
                    st.rerun()

            with preset_cols[1]:
                if st.button("휴일 2h"):
                    st.session_state.preset_hours = 2
                    st.session_state.preset_minutes = 0
                    # 바로 적용
                    config = WORK_CONFIG["휴일근무"].copy()
                    config["target_hours"] = 2
                    config["target_minutes"] = 0
                    st.session_state.manual_work_config = config
                    st.rerun()

            with preset_cols[2]:
                if st.button("교육 3h"):
                    st.session_state.preset_hours = 3
                    st.session_state.preset_minutes = 0
                    # 바로 적용
                    config = WORK_CONFIG["평일근무"].copy()
                    config["target_hours"] = 3
                    config["target_minutes"] = 0
                    st.session_state.manual_work_config = config
                    st.rerun()

            with preset_cols[3]:
                if st.button("교육 2.5h"):
                    st.session_state.preset_hours = 2
                    st.session_state.preset_minutes = 30
                    # 바로 적용
                    config = WORK_CONFIG["평일근무"].copy()
                    config["target_hours"] = 2
                    config["target_minutes"] = 30
                    st.session_state.manual_work_config = config
                    st.rerun()

            st.markdown("---")

            # 현재 설정 표시
            if st.session_state.get('manual_work_config'):
                current_config = st.session_state.manual_work_config
                st.success(f"✅ 현재 설정: {current_config['target_hours']}시간 {current_config['target_minutes']}분")

            # 수동 입력 (프리셋 후에 배치)
            col1, col2 = st.columns(2)
            with col1:
                manual_hours = st.number_input(
                    "시간",
                    min_value=0,
                    max_value=12,
                    value=st.session_state.preset_hours,
                    key="manual_hours"
                )
            with col2:
                manual_minutes = st.number_input(
                    "분",
                    min_value=0,
                    max_value=59,
                    value=st.session_state.preset_minutes,
                    key="manual_minutes"
                )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ 적용하기", use_container_width=True):
                    # 수동 설정을 평일 기준으로 복사 후 목표시간만 변경
                    config = WORK_CONFIG["평일근무"].copy()
                    config["target_hours"] = manual_hours
                    config["target_minutes"] = manual_minutes
                    st.session_state.manual_work_config = config
                    st.session_state.preset_hours = manual_hours
                    st.session_state.preset_minutes = manual_minutes
                    st.rerun()

            with col_btn2:
                if st.button("🔄 초기화", use_container_width=True):
                    st.session_state.manual_work_config = None
                    st.session_state.preset_hours = 3
                    st.session_state.preset_minutes = 30
                    st.session_state.force_previous_day = False
                    st.rerun()
        else:
            # 자동 감지 모드일 때는 수동 설정 초기화
            st.session_state.manual_work_config = None
            st.session_state.force_previous_day = False

    # ========== 상담사 관리 UI ==========
    with st.expander("👥 상담사 및 팀 관리", expanded=False):
        tab1, tab2, tab3 = st.tabs(["📋 상담사 관리", "🏢 팀 관리", "🐣 신입 그룹 관리"])

        # === 탭 1: 상담사 관리 ===
        with tab1:
            consultants = load_consultants()
            teams = get_all_teams()

            st.markdown("### 📝 상담사 추가")
            col_add1, col_add2, col_add3 = st.columns([2, 2, 1])
            with col_add1:
                selected_team_add = st.selectbox("팀 선택", teams, key="add_consultant_team")
            with col_add2:
                new_consultant_name = st.text_input("상담사 이름", key="add_consultant_name")
            with col_add3:
                st.write("")
                st.write("")
                if st.button("➕ 추가", use_container_width=True):
                    if new_consultant_name.strip():
                        if add_consultant(selected_team_add, new_consultant_name.strip()):
                            st.success(f"✅ {new_consultant_name}님이 {selected_team_add}에 추가되었습니다!")
                            st.rerun()
                        else:
                            st.error(f"❌ 이미 존재하는 상담사입니다.")
                    else:
                        st.warning("⚠️ 이름을 입력해주세요.")

            st.markdown("---")
            st.markdown("### 👤 상담사 삭제")
            for team in teams:
                members = consultants.get(team, [])
                if members:
                    st.markdown(f"**{team}** ({len(members)}명)")
                    cols = st.columns(4)
                    for idx, member in enumerate(members):
                        with cols[idx % 4]:
                            if st.button(f"🗑️ {member}", key=f"remove_{team}_{member}"):
                                if remove_consultant(team, member):
                                    st.success(f"✅ {member}님이 삭제되었습니다!")
                                    st.rerun()
                                else:
                                    st.error("❌ 삭제 실패")

        # === 탭 2: 팀 관리 ===
        with tab2:
            st.markdown("### ➕ 팀 추가")
            col_team1, col_team2 = st.columns([3, 1])
            with col_team1:
                new_team_name = st.text_input("팀 이름", key="add_team_name")
            with col_team2:
                st.write("")
                st.write("")
                if st.button("➕ 팀 추가", use_container_width=True):
                    if new_team_name.strip():
                        if add_team(new_team_name.strip()):
                            st.success(f"✅ {new_team_name} 팀이 추가되었습니다!")
                            st.rerun()
                        else:
                            st.error("❌ 이미 존재하는 팀입니다.")
                    else:
                        st.warning("⚠️ 팀 이름을 입력해주세요.")

            st.markdown("---")
            st.markdown("### 🏢 팀 목록 및 삭제")
            consultants = load_consultants()
            for team in get_all_teams():
                member_count = len(consultants.get(team, []))
                col_team_info1, col_team_info2 = st.columns([4, 1])
                with col_team_info1:
                    st.info(f"**{team}**: {member_count}명")
                with col_team_info2:
                    # CRM팀과 온라인팀은 삭제 불가
                    if team not in ["CRM팀", "온라인팀"]:
                        if member_count == 0:
                            if st.button(f"🗑️ 삭제", key=f"remove_team_{team}"):
                                if remove_team(team):
                                    st.success(f"✅ {team}이 삭제되었습니다!")
                                    st.rerun()
                        else:
                            st.button(f"🔒 ({member_count}명)", key=f"locked_team_{team}", disabled=True)

        # === 탭 3: 신입 그룹 관리 ===
        with tab3:
            trainee_groups = load_trainee_groups()

            st.markdown("### ➕ 신입 그룹 추가")
            col_trainee1, col_trainee2, col_trainee3, col_trainee4 = st.columns([2, 1, 1, 1])
            with col_trainee1:
                new_group_name = st.text_input("그룹명 (예: 신입그룹1기)", key="add_trainee_group_name")
            with col_trainee2:
                trainee_hours = st.number_input("목표(시)", min_value=0, max_value=12, value=2, key="trainee_hours")
            with col_trainee3:
                trainee_minutes = st.number_input("목표(분)", min_value=0, max_value=59, value=0, key="trainee_minutes")
            with col_trainee4:
                st.write("")
                st.write("")
                if st.button("➕ 추가", key="add_trainee_group_btn", use_container_width=True):
                    if new_group_name.strip():
                        # 먼저 팀으로 추가
                        if add_team(new_group_name.strip()):
                            # 그 다음 신입 그룹 설정 추가
                            if add_trainee_group(new_group_name.strip(), trainee_hours, trainee_minutes):
                                st.success(f"✅ {new_group_name} 그룹이 추가되었습니다! (목표: {trainee_hours}시간 {trainee_minutes}분)")
                                st.rerun()
                            else:
                                st.error("❌ 신입 그룹 설정 추가 실패")
                        else:
                            st.error("❌ 이미 존재하는 그룹입니다.")
                    else:
                        st.warning("⚠️ 그룹명을 입력해주세요.")

            st.markdown("---")
            st.markdown("### 🐣 신입 그룹 목록")
            if trainee_groups:
                for group_name, config in trainee_groups.items():
                    col_g1, col_g2, col_g3 = st.columns([2, 2, 1])
                    with col_g1:
                        st.info(f"**{group_name}**")
                    with col_g2:
                        st.write(f"목표: {config['target_hours']}시간 {config['target_minutes']}분")
                    with col_g3:
                        if st.button(f"🗑️ 삭제", key=f"remove_trainee_{group_name}"):
                            # 팀에 소속된 상담사가 있는지 확인
                            consultants = load_consultants()
                            if group_name in consultants and len(consultants[group_name]) > 0:
                                st.error(f"❌ 그룹에 소속된 상담사가 있습니다. 먼저 상담사를 다른 팀으로 이동하거나 삭제해주세요.")
                            else:
                                # 신입 그룹 설정 삭제
                                if remove_trainee_group(group_name):
                                    # 팀도 삭제
                                    remove_team(group_name)
                                    st.success(f"✅ {group_name}이 삭제되었습니다!")
                                    st.rerun()
            else:
                st.info("📋 등록된 신입 그룹이 없습니다.")

    # 추가 스타일 적용 - 범례 스타일 (라이트모드/다크모드 모두 시인성 개선 및 간격 조정)
    st.markdown("""
    <style>
    .summary-textbox-info {
        margin-top: 10px;
        font-weight: 700;
        color: #1976d2;
    }
    .summary-textbox-legend {
        margin-top: 5px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 0.75em;
    }
    .legend-item {
        background-color: #2c5aa0;
        color: white;
        padding: 3px 6px;
        border-radius: 4px;
        white-space: nowrap;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    /* 다크 모드에서의 범례 스타일 개선 */
    .dark-theme .summary-textbox-info {
        color: #4f96e6;
    }
    .dark-theme .legend-item {
        background-color: #3a3a3a;
        color: #ffffff;
    }
    
    /* 날짜 아래의 간단한 범례 스타일 (라이트모드/다크모드 모두 개선) */
    .simple-legend {
        text-align: center;
        margin-top: 2px;
        margin-bottom: 5px;
        font-size: 0.9em;
        font-weight: 500;
        background-color: #2c5aa0;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        width: fit-content;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 세션 상태 초기화 (딕셔너리 방식)
    session_defaults = {
        'consultant_df': None,
        'calltime_df': None,
        'performance_df': None,
        'filtered_data': None,
        'processing': False
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
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
        if not st.session_state.processing:
            st.session_state.processing = True

            # 진행 상황 표시를 위한 placeholder
            progress_placeholder = st.empty()

            try:
                # 파일 처리 진행 상태 표시
                progress_placeholder.info('🔄 파일 처리 중...')

                # 파일 위치 저장을 위해 seek(0)
                consultant_file.seek(0)
                calltime_file.seek(0)

                # 파일 처리 시도
                consultant_df, consultant_error = process_consultant_file(consultant_file)
                calltime_df, calltime_error = process_calltime_file(calltime_file)

                # 오류 체크
                if consultant_error:
                    st.error(consultant_error)
                    st.session_state.processing = False
                    progress_placeholder.empty()
                elif calltime_error:
                    st.error(calltime_error)
                    st.session_state.processing = False
                    progress_placeholder.empty()
                else:
                    # 세션 상태에 데이터프레임 저장
                    st.session_state.consultant_df = consultant_df
                    st.session_state.calltime_df = calltime_df

                    progress_placeholder.info('🔄 데이터 분석 중...')

                    # 분석 실행
                    performance_df, filtered_data, analysis_error = analyze_consultant_performance(consultant_df, calltime_df)

                    if analysis_error:
                        st.error(analysis_error)
                        st.session_state.processing = False
                        progress_placeholder.empty()
                    else:
                        # 세션 상태에 결과 저장
                        st.session_state.performance_df = performance_df
                        st.session_state.filtered_data = filtered_data
                        st.session_state.processing = False

                        progress_placeholder.success('✅ 분석 완료!')

                        # 결과 표시 (압축된 버전)
                        st.markdown('<h3>상담원 실적 현황</h3>', unsafe_allow_html=True)

                        # 필터링된 데이터 정보 표시 (추가됨)
                        if filtered_data is not None:
                            st.write(f"필터링된 원본 데이터: {len(filtered_data)}개의 행, 판매채널이 '본사' 또는 '온라인'인 데이터만 포함")

            except Exception as e:
                st.error(f"❌ 처리 중 오류 발생: {str(e)}")
                st.session_state.processing = False
                progress_placeholder.empty()

    # 결과가 이미 있는 경우 표시
    if st.session_state.performance_df is not None and not st.session_state.processing:
        # 결과 표시
        st.markdown('<h3>상담원 실적 현황</h3>', unsafe_allow_html=True)

        # 필터링된 데이터 정보 표시
        if st.session_state.filtered_data is not None:
            st.write(f"필터링된 원본 데이터: {len(st.session_state.filtered_data)}개의 행, 판매채널이 '본사' 또는 '온라인'인 데이터만 포함")

        # 현재 시간 가져오기
        current_time = datetime.now()
        # 오전 10시 30분 기준으로 표시 방식 결정
        cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)

        # 전일자 강제 조회 옵션 확인
        force_previous = st.session_state.get('force_previous_day', False)

        # 목표 시간 및 이모지 기준 설정
        if current_time < cutoff_time or force_previous:
            # 10시 30분 이전 - 전날 데이터 조회
            is_previous_day = True

            # 이전 영업일 구하기 (공휴일 & 주말 제외)
            prev_date = get_previous_business_day(current_time)

            # 전날 근무 설정 가져오기
            work_config = get_work_config(
                target_date=prev_date,
                manual_config=st.session_state.get('manual_work_config')
            )
            current_target_seconds = (
                work_config["target_hours"] * 3600 +
                work_config["target_minutes"] * 60
            )
            current_target_time = format_time(current_target_seconds)

            date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {prev_date.year}년 {prev_date.month}월 {prev_date.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 전체집계"
        else:
            # 10시 30분 이후 - 당일 데이터 조회
            is_previous_day = False

            # 당일 근무 설정 가져오기
            work_config = get_work_config(
                target_date=current_time,
                manual_config=st.session_state.get('manual_work_config')
            )
            current_target_seconds = calculate_target_calltime_seconds(
                current_time.time(),
                work_config
            )
            current_target_time = format_time(current_target_seconds)

            date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.year}년 {current_time.month}월 {current_time.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.hour}시{current_time.minute}분 기준"

        # 상태 표시
        st.markdown(f'<div class="status-container"><div class="status-chip success">분석 완료</div><div class="timestamp">{current_time.strftime("%Y년 %m월 %d일 %H시 %M분")} 기준 | 현재 목표 콜타임: {current_target_time}</div></div>', unsafe_allow_html=True)

        # 데이터 정보 표시
        st.write(f"총 {len(st.session_state.performance_df)}명의 상담원 실적이 분석되었습니다.")

        # 날짜 표시
        st.markdown(DATE_DISPLAY_STYLE.format(date_display=date_display), unsafe_allow_html=True)

        # 범례를 날짜 바로 아래에 간단하게 추가 - 간격 축소 및 양쪽 모드 시인성 개선
        st.markdown(f'<div class="simple-legend">⏱️ 목표시간: {current_target_time} | 🚩:달성 | ⏰:분발필요</div>', unsafe_allow_html=True)

        # 컴팩트 HTML 테이블 생성 및 표시 - is_previous_day 파라미터 전달
        html_table = generate_compact_html_table(st.session_state.performance_df, is_previous_day)
        st.markdown(html_table, unsafe_allow_html=True)

        # 시각화 섹션 - 접을 수 있게 수정
        with st.expander("시각화 보기", expanded=False):
            st.plotly_chart(create_compact_visualization(st.session_state.performance_df), use_container_width=True)

        # 엑셀 내보내기
        st.markdown("### 엑셀 파일 다운로드")
        st.markdown(DOWNLOAD_BUTTON_STYLE, unsafe_allow_html=True)

        try:
            # 현재 날짜와 UUID 생성
            today = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:4]  # UUID 앞 4자리만 사용
            file_prefix = f"{today}_{unique_id}_"

            # 엑셀 파일 생성 (필터링된 데이터 포함)
            excel_data = create_excel_report(st.session_state.performance_df, st.session_state.filtered_data)

            if excel_data:
                # 다운로드 링크 생성 - 필터링된 데이터가 있으면 2시트, 없으면 1시트
                sheet_count = "2시트" if st.session_state.filtered_data is not None else "1시트"
                b64 = base64.b64encode(excel_data).decode()
                href = f'<div class="download-button-container"><a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{file_prefix}상담원_실적_현황.xlsx" class="download-button">엑셀 다운로드 ({sheet_count})</a></div>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.error("엑셀 파일 생성에 실패했습니다.")
        except Exception as e:
            st.error(f"엑셀 파일 다운로드 준비 중 오류가 발생했습니다: {str(e)}")
    else:
        # 파일 업로드 전 안내 화면
        st.info("상담주문계약내역과 콜타임 파일을 모두 업로드하면 분석이 시작됩니다.")
        
        # 샘플 데이터 표시
        st.markdown("### 표시 형식 샘플")
        
        # 현재 날짜 및 시간 표시 추가 (샘플에도 적용)
        current_time = datetime.now()
        # 10시 30분 기준으로 표시 방식 결정
        cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)

        if current_time < cutoff_time:
            # 10시 30분 이전 - 전날 데이터 조회
            # 이전 영업일 구하기 (공휴일 & 주말 제외)
            prev_date = get_previous_business_day(current_time)

            # 전날 근무 설정 가져오기
            work_config = get_work_config(
                target_date=prev_date,
                manual_config=st.session_state.get('manual_work_config')
            )
            current_target_seconds = (
                work_config["target_hours"] * 3600 +
                work_config["target_minutes"] * 60
            )
            current_target_time = format_time(current_target_seconds)

            date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {prev_date.year}년 {prev_date.month}월 {prev_date.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 전체집계"
        else:
            # 10시 30분 이후 - 당일 데이터 조회
            # 당일 근무 설정 가져오기
            work_config = get_work_config(
                target_date=current_time,
                manual_config=st.session_state.get('manual_work_config')
            )
            current_target_seconds = calculate_target_calltime_seconds(
                current_time.time(),
                work_config
            )
            current_target_time = format_time(current_target_seconds)

            date_display = f"★전자계약 제외★ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.year}년 {current_time.month}월 {current_time.day}일 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {current_time.hour}시{current_time.minute}분 기준"
        
        st.markdown(DATE_DISPLAY_STYLE.format(date_display=date_display), unsafe_allow_html=True)
        
        # 범례를 날짜 바로 아래에 간단하게 추가 - 간격 축소 및 양쪽 모드 시인성 개선
        st.markdown(f'<div class="simple-legend">⏱️ 목표시간: {current_target_time} |  🚩:달성 | ⏰:분발발필요</div>', unsafe_allow_html=True)
        
        # 컴팩트 샘플 테이블 표시
        html_table = generate_compact_sample_html_table()
        st.markdown(html_table, unsafe_allow_html=True)
        
        # 간소화된 사용 가이드
        st.markdown(USAGE_GUIDE_MARKDOWN, unsafe_allow_html=True)