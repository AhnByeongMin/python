"""
상담원 실적 현황 비즈니스 로직

이 모듈은 상담원 실적을 처리하고 분석하는 순수 비즈니스 로직을 포함합니다.
UI와 독립적으로 작동하여 단위 테스트가 가능하도록 설계되었습니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
import re
import xlsxwriter
from datetime import datetime
from typing import Tuple, Dict, List, Optional, Any, Union

# utils.py에서 필요한 함수 가져오기
from utils.utils import format_time, peek_file_content

def process_consultant_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    상담주문계약내역 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 먼저 바이너리 데이터 읽기
        file_bytes = file.read()
        file_like = BytesIO(file_bytes)
        
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
            
        # 일반회차 캠페인 컬럼이 있다면 추가
        if '일반회차 캠페인' in df.columns:
            needed_columns.append('일반회차 캠페인')
            
        # 판매 유형 컬럼이 있다면 추가
        if '판매 유형' in df.columns:
            needed_columns.append('판매 유형')
            
        # 판매채널 컬럼이 있다면 추가 (필터링용)
        if '판매채널' in df.columns:
            needed_columns.append('판매채널')
        
        subset_df = df[needed_columns].copy()
        
        # NaN 값을 가진 행 제거
        subset_df = subset_df.dropna(subset=["상담사"])
        
        # 일반회차 캠페인 컬럼이 비어있는 값을 삭제하는 로직 추가
        if '일반회차 캠페인' in subset_df.columns:
            # NaN 또는 빈 문자열인 경우 필터링
            valid_rows = subset_df['일반회차 캠페인'].notna() & (subset_df['일반회차 캠페인'] != '')
            subset_df = subset_df[valid_rows]
        
        return subset_df, None
        
    except Exception as e:
        return None, f"상담주문계약내역 파일 처리 중 오류가 발생했습니다: {str(e)}"

def process_calltime_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    콜타임 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 콜타임 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
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

def analyze_consultant_performance(consultant_df: pd.DataFrame, calltime_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[str]]:
    """
    상담원 실적을 분석하는 함수
    
    Args:
        consultant_df: 상담주문계약내역 데이터프레임
        calltime_df: 콜타임 데이터프레임
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[str]]: 
            - 분석 결과 데이터프레임 
            - 필터링된 원본 데이터프레임
            - 오류 메시지(있는 경우)
    """
    try:
        # 데이터 검증
        if consultant_df.empty or calltime_df.empty:
            return None, None, "데이터가 비어 있습니다."
            
        # 판매채널이 "본사" 또는 "온라인"인 데이터만 필터링
        filtered_original_data = None
        if '판매채널' in consultant_df.columns:
            valid_channels = ['본사', '온라인']
            filtered_original_data = consultant_df[consultant_df['판매채널'].isin(valid_channels)].copy()
            
            # 일반회차 캠페인 값이 있는 행만 유지 (있는 경우)
            if '일반회차 캠페인' in filtered_original_data.columns:
                filtered_original_data = filtered_original_data[
                    filtered_original_data['일반회차 캠페인'].notna() & 
                    (filtered_original_data['일반회차 캠페인'] != '')
                ]
        
        # 관리자 목록 (분석에서 제외)
        excluded_consultants = ['김은아', '김지원', '민건희', '홍민지', '안병민']
        
        # 온라인 팀 상담원 목록
        online_consultants = ['김부자', '최진영']
        
        # 상담원 목록 (콜타임 데이터 기준)
        # 관리자 목록을 필터링하여 제외
        consultants = [consultant for consultant in calltime_df["상담원명"].unique().tolist() 
                      if consultant not in excluded_consultants]
        
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
                
                # 판매채널이 "본사" 또는 "온라인"인 데이터만 필터링
                if not consultant_data.empty and '판매채널' in consultant_data.columns:
                    # "본사" 또는 "온라인"인 행만 유지
                    valid_channels = ['본사', '온라인']
                    consultant_data = consultant_data[consultant_data['판매채널'].isin(valid_channels)]
                    
                    if consultant_data.empty:
                        consultant_data = pd.DataFrame(columns=consultant_data.columns)
                
                # 일반회차 캠페인 컬럼이 있는 경우 필터링
                if not consultant_data.empty and '일반회차 캠페인' in consultant_data.columns:
                    # 값이 없거나 빈 문자열인 행 제거
                    valid_rows = consultant_data['일반회차 캠페인'].notna() & (consultant_data['일반회차 캠페인'] != '')
                    consultant_data = consultant_data[valid_rows]
                    
                    if consultant_data.empty:
                        consultant_data = pd.DataFrame(columns=consultant_data.columns)

                # 캠페인 컬럼에 유효한 값이 있는 데이터만 필터링
                if not consultant_data.empty and '캠페인' in consultant_data.columns:
                    # 캠페인 컬럼이 유효한 값을 가진 행만 필터링
                    valid_rows = []
                    for idx, row in consultant_data.iterrows():
                        campaign_value = str(row.get('캠페인', '')).strip()
                        
                        # 캠페인 값이 유효한지 확인
                        # 1. "캠"을 포함하거나
                        # 2. "분배"를 포함하거나
                        # 3. "C"로 시작하거나
                        # 4. "V"로 시작하는 경우
                        if campaign_value and (
                            '캠' in campaign_value or 
                            '분배' in campaign_value or 
                            campaign_value.startswith('C') or 
                            campaign_value.startswith('V')
                        ):
                            valid_rows.append(idx)
                    
                    if valid_rows:
                        consultant_data = consultant_data.loc[valid_rows]
                    else:
                        consultant_data = pd.DataFrame(columns=consultant_data.columns)
                
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
            return None, filtered_original_data, "유효한 상담원 데이터를 생성할 수 없습니다."
            
        result_df = pd.DataFrame(result_data)
        
        # 조직별 그룹화 및 정렬 (건수 내림차순, 콜타임 내림차순)
        result_df = result_df.sort_values(by=["조직", "건수", "콜타임_초"], ascending=[True, False, False])
        
        return result_df, filtered_original_data, None
        
    except Exception as e:
        return None, None, f"상담원 실적 분석 중 오류가 발생했습니다: {str(e)}"

def create_excel_report(performance_df: pd.DataFrame, filtered_data: pd.DataFrame = None) -> Optional[bytes]:
    """
    상담원 실적 현황을 엑셀 파일로 변환하는 함수
    
    Args:
        performance_df: 상담원 실적 데이터프레임
        filtered_data: 필터링된 원본 데이터 (선택 사항)
        
    Returns:
        Optional[bytes]: 엑셀 바이너리 데이터 또는 None (오류 발생 시)
    """
    try:
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
        
        # 상담원 실적 시트 생성
        worksheet = writer.sheets['상담원 실적'] = workbook.add_worksheet('상담원 실적')
        
        # 현재 날짜 시간 정보 가져오기
        current_time = datetime.now()
        cutoff_time = current_time.replace(hour=10, minute=30, second=0, microsecond=0)
        
        # 날짜 문자열 생성 (오전 10시 30분 기준)
        if current_time < cutoff_time:
            # 이전 영업일 기준 (이 함수는 utils.py에서 가져와야 함)
            # 여기서는 간단히 하루 전으로 처리
            prev_date = current_time - pd.Timedelta(days=1)
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
        
        # 온라인 요약행 추가 (온라인 파트가 있는 경우만)
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
        
        # 필터링된 원본 데이터 시트 추가 (있는 경우)
        if filtered_data is not None and not filtered_data.empty:
            # 필터링된 데이터 시트 생성
            filtered_worksheet = writer.sheets['필터링된 원본 데이터'] = workbook.add_worksheet('필터링된 원본 데이터')
            
            # 필터링된 데이터의 헤더 쓰기
            for col_num, column_name in enumerate(filtered_data.columns):
                filtered_worksheet.write(0, col_num, column_name, header_format)
            
            # 필터링된 데이터 내용 쓰기
            for row_num, row_data in enumerate(filtered_data.values, 1):
                row_format = alternate_row_format if row_num % 2 == 0 else data_format
                for col_num, cell_value in enumerate(row_data):
                    # 셀 값이 None이나 NaN이면 빈 문자열로 처리
                    if pd.isna(cell_value):
                        cell_value = ""
                    filtered_worksheet.write(row_num, col_num, cell_value, row_format)
            
            # 컬럼 너비 자동 조정 (최대 30)
            for col_num, column_name in enumerate(filtered_data.columns):
                max_len = max(
                    len(str(column_name)),
                    filtered_data[column_name].astype(str).str.len().max() if not filtered_data.empty else 0
                )
                filtered_worksheet.set_column(col_num, col_num, min(max_len + 2, 30))
        
        # 엑셀 파일 저장
        writer.close()
        excel_data = output.getvalue()
        return excel_data
    except Exception as e:
        return None