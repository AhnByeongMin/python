import pandas as pd
import streamlit as st
import base64
from io import BytesIO
import io
import numpy as np
import plotly.express as px
import re
from datetime import datetime, timedelta
import xlsxwriter

# utils.py에서 함수 import
from utils import format_time, is_holiday, get_previous_business_day, peek_file_content

# 상담주문계약내역 파일 처리 함수
def process_consultant_file(file):
    """상담주문계약내역 엑셀 파일을 처리하는 함수"""
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 먼저 바이너리 데이터 읽기
        file_bytes = file.read()
        file_like = io.BytesIO(file_bytes)
        
        # 다양한 방법으로 파일 읽기 시도
        df = None
        errors = []
        
        # 1. 기본 방법으로 시도
        try:
            file_like.seek(0)
            df = pd.read_excel(file_like, header=2)
            
            # 수동으로 중복 컬럼 처리
            if df is not None:
                # 컬럼 리스트 확인
                cols = df.columns.tolist()
                # 중복된 컬럼 확인
                dupes = set([x for x in cols if cols.count(x) > 1])
                if dupes:
                    # 중복 컬럼 수정 - 수동으로 번호 부여
                    new_cols = []
                    seen = {}
                    for col in cols:
                        if col in dupes:
                            if col not in seen:
                                seen[col] = 0
                            else:
                                seen[col] += 1
                            new_cols.append(f"{col}.{seen[col]}")
                        else:
                            new_cols.append(col)
                    # 새 컬럼 이름 적용
                    df.columns = new_cols
                    
        except Exception as e:
            errors.append(f"기본 방법 실패: {str(e)}")
        
        # 2. xlrd 엔진으로 시도
        if df is None:
            try:
                file_like.seek(0)
                df = pd.read_excel(file_like, header=2, engine='xlrd')
                
                # 수동으로 중복 컬럼 처리
                if df is not None:
                    # 컬럼 리스트 확인
                    cols = df.columns.tolist()
                    # 중복된 컬럼 확인
                    dupes = set([x for x in cols if cols.count(x) > 1])
                    if dupes:
                        # 중복 컬럼 수정 - 수동으로 번호 부여
                        new_cols = []
                        seen = {}
                        for col in cols:
                            if col in dupes:
                                if col not in seen:
                                    seen[col] = 0
                                else:
                                    seen[col] += 1
                                new_cols.append(f"{col}.{seen[col]}")
                            else:
                                new_cols.append(col)
                        # 새 컬럼 이름 적용
                        df.columns = new_cols
                
            except Exception as e:
                errors.append(f"xlrd 엔진 실패: {str(e)}")
        
        # 3. openpyxl 엔진으로 시도
        if df is None:
            try:
                file_like.seek(0)
                df = pd.read_excel(file_like, header=2, engine='openpyxl')
                
                # 수동으로 중복 컬럼 처리
                if df is not None:
                    # 컬럼 리스트 확인
                    cols = df.columns.tolist()
                    # 중복된 컬럼 확인
                    dupes = set([x for x in cols if cols.count(x) > 1])
                    if dupes:
                        # 중복 컬럼 수정 - 수동으로 번호 부여
                        new_cols = []
                        seen = {}
                        for col in cols:
                            if col in dupes:
                                if col not in seen:
                                    seen[col] = 0
                                else:
                                    seen[col] += 1
                                new_cols.append(f"{col}.{seen[col]}")
                            else:
                                new_cols.append(col)
                        # 새 컬럼 이름 적용
                        df.columns = new_cols
                
            except Exception as e:
                errors.append(f"openpyxl 엔진 실패: {str(e)}")
        
        # 모든 방법이 실패한 경우
        if df is None:
            error_details = "\n".join(errors)
            return None, f"계약내역 파일을 읽을 수 없습니다. 다음 형식을 시도했으나 모두 실패했습니다:\n{error_details}"
        
        # 필요한 컬럼 확인
        required_columns = ["상담사", "상담사 조직", "대분류"]
        
        # 컬럼명이 비슷한 경우 매핑
        column_mapping = {}
        for req_col in required_columns:
            if req_col in df.columns:
                continue  # 이미 존재하면 매핑 불필요
                
            # 유사한 컬럼명 목록
            similar_cols = {
                "상담사": ["상담원", "상담원명", "직원명", "사원명", "담당자"],
                "상담사 조직": ["조직", "부서", "팀", "상담팀", "부서명"],
                "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"]
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
            # 대분류 컬럼 특별 처리 - 중복이면 .0 버전 확인 (우리가 수동으로 부여한 인덱스)
            if "대분류" in missing_columns and "대분류.0" in df.columns:
                df["대분류"] = df["대분류.0"]
                missing_columns.remove("대분류")
            # 또는 .1 버전 확인 (pandas가 자동으로 부여한 인덱스)
            elif "대분류" in missing_columns and "대분류.1" in df.columns:
                df["대분류"] = df["대분류.1"]
                missing_columns.remove("대분류")
            
            if missing_columns:  # 여전히 누락된 컬럼이 있으면
                available_columns = ", ".join(df.columns.tolist()[:20]) + "..."  # 처음 20개만 표시
                return None, f"계약내역 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}\n사용 가능한 컬럼 일부: {available_columns}"
        
        # 필수 컬럼만 선택 (판매 유형 컬럼 포함)
        needed_columns = ["상담사", "상담사 조직", "대분류"]
        
        # 캠페인 컬럼이 있다면 추가
        if '캠페인' in df.columns:
            needed_columns.append('캠페인')
            
        # 판매 유형 컬럼이 있다면 추가
        if '판매 유형' in df.columns:
            needed_columns.append('판매 유형')
        
        subset_df = df[needed_columns].copy()
        
        # NaN 값을 가진 행 제거
        subset_df = subset_df.dropna(subset=["상담사"])
        
        return subset_df, None
        
    except Exception as e:
        return None, f"상담주문계약내역 파일 처리 중 오류가 발생했습니다: {str(e)}"

# 콜타임 파일 처리 함수
def process_calltime_file(file):
    """콜타임 엑셀 파일을 처리하는 함수"""
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 먼저 엑셀 파일로 읽기 시도
        try:
            # 일반 엑셀 파일로 시도
            df = pd.read_excel(file)
            
            # 이미지에서 확인된 구조에 따라 필요한 컬럼 매핑
            # 상담원명은 B열(인덱스 1), 총 건수는 AA열, 총 시간은 AB열
            if len(df.columns) >= 28:  # AA와 AB 열이 존재하는지 확인 (A=0, B=1, ... Z=25, AA=26, AB=27)
                # 필요한 데이터 추출
                name_col = df.columns[1]  # 상담원명 (B열)
                count_col = df.columns[26]  # 총 건수 (AA열)
                time_col = df.columns[27]  # 총 시간 (AB열)
                
                # 필요한 데이터 추출
                result_df = pd.DataFrame({
                    '상담원명': df[name_col],
                    '총 건수': df[count_col],
                    '총 시간': df[time_col]
                })
                
                # 숫자가 아닌 행 제거 (헤더, 합계 등)
                result_df = result_df[pd.to_numeric(result_df['총 건수'], errors='coerce').notnull()]
                
                # 누락된 데이터 행 제거
                result_df = result_df.dropna(subset=['상담원명'])
                
                # "상담원ID"나 "합계" 같은 값을 가진 행 제거
                invalid_patterns = ['상담원ID', '상담원 ID', '합계', '합 계', '총계', '총 계']
                for pattern in invalid_patterns:
                    result_df = result_df[~result_df['상담원명'].astype(str).str.contains(pattern)]
                
                # 0:00:00이나 '0' 값을 가진 시간은 제거
                zero_time_patterns = ['0:00:00', '00:00:00', '0']
                result_df = result_df[~result_df['총 시간'].astype(str).isin(zero_time_patterns)].copy()
                
                # 시간을 초로 변환
                def time_to_seconds(time_str):
                    try:
                        if pd.isna(time_str):
                            return 0
                        
                        time_str = str(time_str)
                        time_parts = re.findall(r'\d+', time_str)
                        
                        if not time_parts:
                            return 0
                            
                        # 시간 형식에 따라 변환
                        if len(time_parts) == 3:  # HH:MM:SS
                            h, m, s = map(int, time_parts)
                            return h * 3600 + m * 60 + s
                        elif len(time_parts) == 2:  # MM:SS
                            m, s = map(int, time_parts)
                            return m * 60 + s
                        else:
                            return int(time_parts[0])
                    except:
                        return 0
                
                result_df['총 시간_초'] = result_df['총 시간'].apply(time_to_seconds)
                
                return result_df, None
            else:
                return None, f"필요한 컬럼을 찾을 수 없습니다. 컬럼 수: {len(df.columns)}"
                
        except Exception as excel_err:
            # Excel 파싱 실패, HTML 테이블로 시도
            try:
                file.seek(0)
                file_bytes = file.read()
                content = file_bytes.decode('utf-8', errors='ignore')
                
                if '<table' in content:
                    # HTML에서 행 추출
                    rows = re.findall(r'<tr.*?>(.*?)</tr>', content, re.DOTALL)
                    
                    # 모든 행과 셀 정보 수집
                    all_rows = []
                    for row in rows:
                        cells = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL)
                        if cells:
                            all_rows.append(cells)
                    
                    if not all_rows:
                        return None, "HTML 테이블에서 데이터를 추출할 수 없습니다."
                    
                    # 헤더 정보와 데이터 행 분리
                    header_rows = all_rows[:2]  # 첫 두 행은 헤더
                    data_rows = all_rows[2:]    # 나머지는 데이터
                    
                    # 각 데이터 행의 세번째 열부터는 시간 데이터, 마지막 두 열은 총 건수와 총 시간
                    result_data = []
                    for row in data_rows:
                        if len(row) < 3:
                            continue
                        
                        name = row[1]  # 두 번째 열은 상담원명
                        
                        # "합계" 행이나 공백 행은 건너뛰기
                        if name.strip() in ['합계', '합 계', '총계', '총 계', ''] or '상담원' in name:
                            continue
                        
                        # 마지막 두 열이 총 건수와 총 시간
                        if len(row) >= 28:  # AA열(27)과 AB열(28)
                            count = row[-2]  # AA열
                            time = row[-1]   # AB열
                            
                            # 숫자와 시간 형식 검증
                            try:
                                count = int(re.sub(r'[^\d]', '', count))
                                
                                # 0:00:00 시간은 제외
                                if time not in ['0:00:00', '00:00:00', '0']:
                                    # 시간을 초로 변환
                                    time_parts = re.findall(r'\d+', time)
                                    if len(time_parts) == 3:  # HH:MM:SS
                                        h, m, s = map(int, time_parts)
                                        seconds = h * 3600 + m * 60 + s
                                    elif len(time_parts) == 2:  # MM:SS
                                        m, s = map(int, time_parts)
                                        seconds = m * 60 + s
                                    else:
                                        seconds = 0
                                    
                                    result_data.append({
                                        '상담원명': name,
                                        '총 건수': count,
                                        '총 시간': time,
                                        '총 시간_초': seconds
                                    })
                            except:
                                continue
                    
                    # 결과 데이터프레임 생성
                    if result_data:
                        result_df = pd.DataFrame(result_data)
                        return result_df, None
                    else:
                        return None, "유효한 상담원 데이터를 추출할 수 없습니다."
                else:
                    return None, "HTML 테이블을 찾을 수 없습니다."
                    
            except Exception as html_err:
                return None, f"파일 처리 중 오류가 발생했습니다: Excel - {str(excel_err)}, HTML - {str(html_err)}"
                
    except Exception as e:
        return None, f"콜타임 파일 처리 중 오류가 발생했습니다: {str(e)}"

# 상담원 실적 분석 함수
def analyze_consultant_performance(consultant_df, calltime_df):
    """상담원 실적을 분석하는 함수"""
    try:
        # 데이터 검증
        if consultant_df.empty or calltime_df.empty:
            return None, "데이터가 비어 있습니다."
        
        # 온라인 팀 상담원 목록
        online_consultants = ['김부자', '최진영']
        
        # 상담원 목록 (콜타임 데이터 기준)
        consultants = calltime_df["상담원명"].unique().tolist()
        
        # 결과 데이터프레임을 위한 리스트
        result_data = []
        
        # 각 상담원별 대분류 집계
        for consultant in consultants:
            try:
                # 상담원명이 문자열인지 확인
                if not isinstance(consultant, str):
                    continue
                    
                # 상담원명에 비정상적인 값이 있는지 확인 
                if consultant in ['휴식', '후처리', '대기', '기타', '합계', '00:00:00', '0:00:00']:
                    continue
                
                # 상담사 컬럼 매핑 (이름이 정확히 일치하지 않을 수 있음)
                exact_match = consultant_df[consultant_df["상담사"] == consultant]
                
                # 정확히 일치하는 데이터가 없으면 유사 매칭 시도
                if exact_match.empty:
                    # 상담원명 전처리
                    consultant_clean = consultant.strip()
                    
                    # 포함 관계 확인
                    matches = []
                    for idx, row in consultant_df.iterrows():
                        consultant_name = str(row["상담사"]).strip()
                        # 상담원명이 포함되거나 상담원명에 포함되는 경우
                        if (consultant_clean in consultant_name) or (consultant_name in consultant_clean):
                            matches.append(idx)
                    
                    consultant_data = consultant_df.loc[matches] if matches else pd.DataFrame(columns=consultant_df.columns)
                else:
                    consultant_data = exact_match
                
                # 상담사 조직 정보 결정
                if consultant in online_consultants:
                    organization = "온라인파트"
                elif not consultant_data.empty:
                    organization = consultant_data["상담사 조직"].iloc[0]
                else:
                    organization = "CRM파트"  # 기본값을 CRM파트로 설정
                
                # 캠페인이 비어있지 않은 데이터만 필터링
                if not consultant_data.empty and '캠페인' in consultant_data.columns:
                    consultant_data = consultant_data[~consultant_data['캠페인'].isna()]
                
                # 5가지 분류로 나누어 카운트
                anma_count = 0
                lacloud_count = 0
                water_count = 0
                thecare_count = 0
                membership_count = 0
                
                if not consultant_data.empty:
                    # 판매 유형 컬럼이 있는지 확인
                    has_sale_type = '판매 유형' in consultant_data.columns
                    
                    # 각 행에 대해 판매 유형과 대분류에 따라 분류
                    for idx, row in consultant_data.iterrows():
                        sale_type = str(row.get('판매 유형', '')).lower() if has_sale_type else ''
                        category = str(row.get('대분류', '')).lower()
                        
                        # 판매 유형에 '케어'가 포함되면 더케어로 분류
                        if '케어' in sale_type:
                            thecare_count += 1
                        # 판매 유형에 '멤버십'이 포함되면 멤버십으로 분류
                        elif '멤버십' in sale_type or '멤버쉽' in sale_type:
                            membership_count += 1
                        # 그 외에는 대분류에 따라 분류
                        elif '안마의자' in category:
                            anma_count += 1
                        elif '라클라우드' in category:
                            lacloud_count += 1
                        elif '정수기' in category:
                            water_count += 1
                
                # 총 건수
                total_count = anma_count + lacloud_count + water_count + thecare_count + membership_count
                
                # 콜타임 정보
                call_count = calltime_df.loc[calltime_df["상담원명"] == consultant, "총 건수"].iloc[0]
                call_time = calltime_df.loc[calltime_df["상담원명"] == consultant, "총 시간"].iloc[0]
                call_time_seconds = calltime_df.loc[calltime_df["상담원명"] == consultant, "총 시간_초"].iloc[0]
                
                # 결과 리스트에 추가
                result_data.append({
                    "상담사": consultant,
                    "조직": organization,
                    "안마의자": anma_count,
                    "라클라우드": lacloud_count,
                    "정수기": water_count,
                    "더케어": thecare_count,
                    "멤버십": membership_count,
                    "건수": total_count,
                    "콜건수": call_count,
                    "콜타임": call_time,
                    "콜타임_초": call_time_seconds
                })
                
            except Exception as e:
                # 오류 발생 시 처리 계속 진행
                pass
        
        # 결과 데이터프레임 생성
        if not result_data:
            return None, "유효한 상담원 데이터를 생성할 수 없습니다."
            
        result_df = pd.DataFrame(result_data)
        
        # 조직별 그룹화 및 정렬 (건수 내림차순, 콜타임 내림차순)
        result_df = result_df.sort_values(by=["조직", "건수", "콜타임_초"], ascending=[True, False, False])
        
        return result_df, None
        
    except Exception as e:
        return None, f"상담원 실적 분석 중 오류가 발생했습니다: {str(e)}"

# 컴팩트한 HTML 테이블 생성 함수
def generate_compact_html_table(df):
    """컴팩트한 HTML 테이블 생성 함수"""
    html = '''
    <style>
    .table-container {
        width: 50%;  /* 데스크톱에서는 50% 너비로 제한 */
        margin: 0 auto;  /* 중앙 정렬 */
        overflow-x: auto;  /* 모바일에서 가로 스크롤 가능하게 */
    }
    
    /* 모바일 환경에서는 컨테이너를 100% 너비로 확장 */
    @media (max-width: 768px) {
        .table-container {
            width: 100%;
        }
    }
    
    .compact-table {
        border-collapse: collapse;
        font-size: 0.7em;  /* 더 작은 폰트 크기 */
        width: 100%;  /* 컨테이너 내에서 100% */
        table-layout: fixed;
        margin: 0 auto;
    }
    .compact-table thead tr {
        background-color: #262730;
        color: white;
        text-align: center;
        font-weight: bold;
    }
    .compact-table th, .compact-table td {
        padding: 2px 3px;  /* 패딩 최소화 */
        text-align: center;
        border: 1px solid #444;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .compact-table tbody tr {
        background-color: #1E1E1E;
        color: white;
    }
    .compact-table tbody tr:nth-of-type(even) {
        background-color: #2D2D2D;
    }
    .compact-table tbody tr.summary-row {
        background-color: #2E4053;
        color: white;
        font-weight: bold;
    }
    /* 컬럼 너비 최적화 */
    .compact-table th:nth-child(1), .compact-table td:nth-child(1) { width: 3%; }  /* 순위 */
    .compact-table th:nth-child(2), .compact-table td:nth-child(2) { width: 7%; }  /* 상담사 */
    .compact-table th:nth-child(3), .compact-table td:nth-child(3),
    .compact-table th:nth-child(4), .compact-table td:nth-child(4),
    .compact-table th:nth-child(5), .compact-table td:nth-child(5),
    .compact-table th:nth-child(6), .compact-table td:nth-child(6),
    .compact-table th:nth-child(7), .compact-table td:nth-child(7) { width: 4%; }  /* 제품 카테고리 */
    .compact-table th:nth-child(8), .compact-table td:nth-child(8) { width: 3%; }  /* 건수 */
    .compact-table th:nth-child(9), .compact-table td:nth-child(9) { width: 5%; }  /* 콜건수 */
    .compact-table th:nth-child(10), .compact-table td:nth-child(10) { width: 6%; }  /* 콜타임 */
    
    /* 간소화된 헤더 */
    .compact-table th:nth-child(3)::after { content: "안마"; }
    .compact-table th:nth-child(3) span { display: none;/* 간소화된 헤더 */
    .compact-table th:nth-child(3)::after { content: "안마"; }
    .compact-table th:nth-child(3) span { display: none; }
    .compact-table th:nth-child(4)::after { content: "라클"; }
    .compact-table th:nth-child(4) span { display: none; }
    .compact-table th:nth-child(5)::after { content: "정수기"; }
    .compact-table th:nth-child(5) span { display: none; }
    .compact-table th:nth-child(6)::after { content: "더케어"; }
    .compact-table th:nth-child(6) span { display: none; }
    .compact-table th:nth-child(7)::after { content: "멤버쉽"; }
    .compact-table th:nth-child(7) span { display: none; }
    </style>
    
    <div class="table-container">
    <table class="compact-table">
    '''
    
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

# 시각화를 위한 컴팩트 함수
def create_compact_visualization(performance_df):
    """팀별 비교 시각화를 위한 컴팩트한 차트 생성"""
    
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

# 컴팩트 샘플 테이블 생성 함수
def generate_compact_sample_html_table():
    html = '''
    <style>
    .table-container {
        width: 50%;  /* 데스크톱에서는 50% 너비로 제한 */
        margin: 0 auto;  /* 중앙 정렬 */
        overflow-x: auto;  /* 모바일에서 가로 스크롤 가능하게 */
    }
    
    /* 모바일 환경에서는 컨테이너를 100% 너비로 확장 */
    @media (max-width: 768px) {
        .table-container {
            width: 100%;
        }
    }
    
    /* Streamlit의 테마 변수를 활용한 동적 스타일링 */
    .compact-table {
        border-collapse: collapse;
        font-size: 0.7em;
        width: 100%;
        table-layout: fixed;
        margin: 0 auto;
    }
    
    /* 다크모드/라이트모드 감지 */
    @media (prefers-color-scheme: dark) {
        .compact-table thead tr {
            background-color: #262730;
            color: white;
        }
        .compact-table tbody tr {
            background-color: #1E1E1E;
            color: white;
        }
        .compact-table tbody tr:nth-of-type(even) {
            background-color: #2D2D2D;
        }
        .compact-table tbody tr.summary-row {
            background-color: #2E4053;
            color: white;
        }
        .compact-table th, .compact-table td {
            border: 1px solid #444;
        }
    }
    
    @media (prefers-color-scheme: light) {
        .compact-table thead tr {
            background-color: #f1f1f1;
            color: #333;
        }
        .compact-table tbody tr {
            background-color: #ffffff;
            color: #333;
        }
        .compact-table tbody tr:nth-of-type(even) {
            background-color: #f9f9f9;
        }
        .compact-table tbody tr.summary-row {
            background-color: #e6f0ff;
            color: #333;
        }
        .compact-table th, .compact-table td {
            border: 1px solid #ddd;
        }
    }
    .compact-table th, .compact-table td {
        padding: 2px 3px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .compact-table thead tr {
        text-align: center;
        font-weight: bold;
    }
    
    .compact-table tbody tr.summary-row {
        font-weight: bold;
    }
    /* 컬럼 너비 최적화 */
    .compact-table th:nth-child(1), .compact-table td:nth-child(1) { width: 3%; }
    .compact-table th:nth-child(2), .compact-table td:nth-child(2) { width: 7%; }
    .compact-table th:nth-child(3), .compact-table td:nth-child(3),
    .compact-table th:nth-child(4), .compact-table td:nth-child(4),
    .compact-table th:nth-child(5), .compact-table td:nth-child(5),
    .compact-table th:nth-child(6), .compact-table td:nth-child(6),
    .compact-table th:nth-child(7), .compact-table td:nth-child(7) { width: 4%; }
    .compact-table th:nth-child(8), .compact-table td:nth-child(8) { width: 3%; }
    .compact-table th:nth-child(9), .compact-table td:nth-child(9) { width: 5%; }
    .compact-table th:nth-child(10), .compact-table td:nth-child(10) { width: 6%; }
    
    /* 간소화된 헤더 */
    .compact-table th:nth-child(3)::after { content: "안"; }
    .compact-table th:nth-child(3) span { display: none; }
    .compact-table th:nth-child(4)::after { content: "라"; }
    .compact-table th:nth-child(4) span { display: none; }
    .compact-table th:nth-child(5)::after { content: "정"; }
    .compact-table th:nth-child(5) span { display: none; }
    .compact-table th:nth-child(6)::after { content: "케어"; }
    .compact-table th:nth-child(6) span { display: none; }
    .compact-table th:nth-child(7)::after { content: "멤버"; }
    .compact-table th:nth-child(7) span { display: none; }
    </style>
    <div class="table-container">
    <table class="compact-table">
    '''
    
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

def show():
    # 타이틀 및 설명
    st.title("👥상담원 실적 현황")
    st.markdown('<div class="dark-card"><p>이 도구는 상담원의 실적 현황을 분석하고 시각화합니다. 상담주문계약내역과 콜타임 파일을 업로드하여 상담원별 실적을 확인할 수 있습니다.</p></div>', unsafe_allow_html=True)
    
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
                st.markdown('<div class="dark-card"><h3>상담원 실적 현황</h3>', unsafe_allow_html=True)
                
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
                
                st.markdown(f'<h4 style="text-align: center; margin-bottom: 15px; letter-spacing: 1px; word-spacing: 5px;">{date_display}</h4>', unsafe_allow_html=True)
                
                # 컴팩트 HTML 테이블 생성 및 표시
                html_table = generate_compact_html_table(performance_df)
                st.markdown(html_table, unsafe_allow_html=True)
                
                # 중앙 정렬 컨테이너 종료
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 시각화 섹션 - 접을 수 있게 수정
                with st.expander("시각화 보기", expanded=False):
                    st.plotly_chart(create_compact_visualization(performance_df), use_container_width=True)
                
                # 엑셀 내보내기 부분 유지
                st.markdown("### 엑셀 파일 다운로드")

                # 다운로드용 데이터프레임 준비 (콜타임_초 컬럼 제거)
                download_df = performance_df.drop(columns=["콜타임_초"])

                # 엑셀 파일 생성
                output = BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')

                # 워크북과 워크시트 설정
                workbook = writer.book
                
                # 공통 스타일 정의
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'vcenter',
                    'align': 'center',
                    'fg_color': '#305496',
                    'font_color': 'white',
                    'border': 1,
                    'border_color': '#D4D4D4'
                })

                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'align': 'center',
                    'valign': 'vcenter',
                    'fg_color': '#4472C4',
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

                time_format = workbook.add_format({
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#D4D4D4',
                    'num_format': '[h]:mm:ss'
                })

                summary_format = workbook.add_format({
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'fg_color': '#8EA9DB',
                    'border': 1,
                    'border_color': '#D4D4D4',
                    'font_color': '#363636'
                })

                alternate_row_format = workbook.add_format({
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#D4D4D4',
                    'fg_color': '#E9EDF4'
                })
                
                # 단일 시트 생성
                worksheet = writer.sheets['상담원 실적'] = workbook.add_worksheet('상담원 실적')
                
                # 현재 날짜 시간 정보 가져오기
                current_time = datetime.now()
                cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)
                
                if current_time < cutoff_time:
                    # 이전 영업일 구하기 (공휴일 & 주말 제외)
                    prev_date = get_previous_business_day(current_time)
                    date_str = f"{prev_date.year}년 {prev_date.month}월 {prev_date.day}일 전체집계"
                else:
                    date_str = f"{current_time.year}년 {current_time.month}월 {current_time.day}일 {current_time.hour}시{current_time.minute}분 기준"
                
                # 제목 추가 (합병 셀 사용)
                worksheet.merge_range('A1:J1', f'상담원 실적 현황', title_format)
                worksheet.merge_range('A2:J2', f'★전자계약 제외★     {date_str}', title_format)
                worksheet.set_row(0, 25)  # 제목 행 높이 설정
                
                # 헤더 행 작성
                headers = ['순위', '상담사', '안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수', '콜건수', '콜타임']
                for col_num, header in enumerate(headers):
                    worksheet.write(2, col_num, header, header_format)
                
                # 데이터 정렬 및 준비 (CRM 파트 먼저, 그 다음 온라인 파트)
                row_num = 3  # 헤더 다음부터 시작
                
                # CRM 파트 데이터
                crm_df = download_df[download_df["조직"] == "CRM파트"].sort_values(by=["건수"], ascending=[False]).copy()
                crm_df['순위'] = range(1, len(crm_df) + 1)
                crm_df = crm_df[['순위', '상담사', '안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수', '콜건수', '콜타임']]
                
                # CRM 데이터 작성
                for idx, row_data in enumerate(crm_df.values):
                    row_format = alternate_row_format if idx % 2 == 1 else data_format
                    
                    for col_num, cell_value in enumerate(row_data):
                        # 0을 '-'로 변환 (안마의자, 라클라우드, 정수기, 더케어, 멤버십)
                        if col_num in [2, 3, 4, 5, 6] and cell_value == 0:
                            worksheet.write(row_num, col_num, '-', row_format)
                        # 숫자 형식 (콜건수)
                        elif col_num == 8:
                            worksheet.write(row_num, col_num, cell_value, number_format)
                        # 시간 형식 (콜타임)
                        elif col_num == 9:
                            worksheet.write_string(row_num, col_num, str(cell_value), time_format)
                        # 일반 데이터
                        else:
                            worksheet.write(row_num, col_num, cell_value, row_format)
                    row_num += 1
                
                # CRM 요약행 추가
                crm_summary = {
                    "순위": "총합/평균",
                    "상담사": "CRM팀순위",
                    "안마의자": crm_df["안마의자"].sum(),
                    "라클라우드": crm_df["라클라우드"].sum(),
                    "정수기": crm_df["정수기"].sum(),
                    "더케어": crm_df["더케어"].sum(),
                    "멤버십": crm_df["멤버십"].sum(),
                    "건수": crm_df["건수"].sum(),
                    "콜건수": round(crm_df["콜건수"].mean(), 1)
                }

                # CRM 평균 콜타임 계산
                crm_time_seconds = []
                for time_str in crm_df["콜타임"]:
                    parts = time_str.split(":")
                    if len(parts) == 3:
                        hours, minutes, seconds = map(int, parts)
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        crm_time_seconds.append(total_seconds)

                avg_crm_seconds = sum(crm_time_seconds) / len(crm_time_seconds) if crm_time_seconds else 0
                hours = int(avg_crm_seconds // 3600)
                minutes = int((avg_crm_seconds % 3600) // 60)
                seconds = int(avg_crm_seconds % 60)
                crm_avg_time = f"{hours}:{minutes:02d}:{seconds:02d}"
                
                worksheet.write(row_num, 0, crm_summary["순위"], summary_format)
                worksheet.write(row_num, 1, crm_summary["상담사"], summary_format)
                # 합계 데이터 작성
                for col_num, key in enumerate(['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']):
                    # 0 값은 '-'로 표시
                    value = '-' if crm_summary[key] == 0 else crm_summary[key]
                    worksheet.write(row_num, col_num + 2, value, summary_format)
                worksheet.write(row_num, 8, crm_summary["콜건수"], summary_format)
                worksheet.write_string(row_num, 9, crm_avg_time, summary_format)
                row_num += 1
                
                # 온라인 파트 데이터
                online_df = download_df[download_df["조직"] == "온라인파트"].sort_values(by=["건수"], ascending=[False]).copy()
                online_df['순위'] = range(1, len(online_df) + 1)
                online_df = online_df[['순위', '상담사', '안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수', '콜건수', '콜타임']]
                
                # 온라인 데이터 작성
                for idx, row_data in enumerate(online_df.values):
                    row_format = alternate_row_format if idx % 2 == 1 else data_format
                    
                    for col_num, cell_value in enumerate(row_data):
                        # 0을 '-'로 변환 (안마의자, 라클라우드, 정수기, 더케어, 멤버십)
                        if col_num in [2, 3, 4, 5, 6] and cell_value == 0:
                            worksheet.write(row_num, col_num, '-', row_format)
                        # 숫자 형식 (콜건수)
                        elif col_num == 8:
                            worksheet.write(row_num, col_num, cell_value, number_format)
                        # 시간 형식 (콜타임)
                        elif col_num == 9:
                            worksheet.write_string(row_num, col_num, str(cell_value), time_format)
                        # 일반 데이터
                        else:
                            worksheet.write(row_num, col_num, cell_value, row_format)
                    row_num += 1
                
                # 온라인 요약행 추가
                online_summary = {
                    "순위": "총합/평균",
                    "상담사": "온라인팀순위",
                    "안마의자": online_df["안마의자"].sum(),
                    "라클라우드": online_df["라클라우드"].sum(),
                    "정수기": online_df["정수기"].sum(),
                    "더케어": online_df["더케어"].sum(),
                    "멤버십": online_df["멤버십"].sum(),
                    "건수": online_df["건수"].sum(),
                    "콜건수": round(online_df["콜건수"].mean(), 1)
                }

                # 온라인 평균 콜타임 계산
                online_time_seconds = []
                for time_str in online_df["콜타임"]:
                    parts = time_str.split(":")
                    if len(parts) == 3:
                        hours, minutes, seconds = map(int, parts)
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        online_time_seconds.append(total_seconds)

                avg_online_seconds = sum(online_time_seconds) / len(online_time_seconds) if online_time_seconds else 0
                hours = int(avg_online_seconds // 3600)
                minutes = int((avg_online_seconds % 3600) // 60)
                seconds = int(avg_online_seconds % 60)
                online_avg_time = f"{hours}:{minutes:02d}:{seconds:02d}"

                
                worksheet.write(row_num, 0, online_summary["순위"], summary_format)
                worksheet.write(row_num, 1, online_summary["상담사"], summary_format)
                # 합계 데이터 작성
                for col_num, key in enumerate(['안마의자', '라클라우드', '정수기', '더케어', '멤버십', '건수']):
                    # 0 값은 '-'로 표시
                    value = '-' if online_summary[key] == 0 else online_summary[key]
                    worksheet.write(row_num, col_num + 2, value, summary_format)
                worksheet.write(row_num, 8, online_summary["콜건수"], summary_format)
                worksheet.write_string(row_num, 9, online_avg_time, summary_format)
                
                # 컬럼 너비 조정
                column_widths = {0: 6, 1: 15, 2: 8, 3: 10, 4: 8, 5: 8, 6: 8, 7: 6, 8: 8, 9: 10}
                for col_num, width in column_widths.items():
                    worksheet.set_column(col_num, col_num, width)
                
                # 엑셀 파일 저장
                writer.close()
                excel_data = output.getvalue()
                
                # 다운로드 버튼 스타일 - 더 컴팩트하게
                st.markdown("""
                <style>
                .download-button {
                    display: inline-block;
                    padding: 8px 16px;
                    background-color: #4472C4;
                    color: white;
                    text-align: center;
                    border-radius: 4px;
                    font-weight: bold;
                    text-decoration: none;
                    margin-top: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    transition: all 0.2s ease;
                    font-size: 0.9em;
                }
                .download-button:hover {
                    background-color: #305496;
                    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
                }
                </style>
                """, unsafe_allow_html=True)

                # 다운로드 링크 생성
                b64 = base64.b64encode(excel_data).decode()
                href = f'<div style="text-align: center;"><a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="상담원_실적_현황.xlsx" class="download-button">엑셀 파일 다운로드</a></div>'
                st.markdown(href, unsafe_allow_html=True)
                
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
        
        st.markdown(f'<h4 style="text-align: center; margin-bottom: 15px; letter-spacing: 1px; word-spacing: 5px;">{date_display}</h4>', unsafe_allow_html=True)
        
        # 컴팩트 샘플 테이블 표시
        html_table = generate_compact_sample_html_table()
        st.markdown(html_table, unsafe_allow_html=True)
        
        # 간소화된 사용 가이드
        st.markdown("""
        ### 사용 가이드
        1. 상담주문계약내역 및 콜타임 엑셀 파일을 업로드하세요.
        2. 파일이 업로드되면 자동으로 분석이 진행됩니다.
        3. 조직별로 상담원 실적을 확인하고 엑셀로 다운로드할 수 있습니다.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show()