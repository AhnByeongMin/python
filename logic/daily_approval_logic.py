"""
일일 승인 현황 비즈니스 로직

이 모듈은 일일 승인 현황 탭의 데이터 처리 및 분석 로직을 포함합니다.
UI와 독립적으로 작동하여 단위 테스트가 가능하도록 설계되었습니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
import re
import xlsxwriter
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional, Any, Union

# utils.py에서 필요한 함수 가져오기
from utils.utils import format_time, peek_file_content
from utils.consultant_manager import load_consultants, get_team_by_consultant, get_all_consultants

def process_approval_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    상담주문내역 엑셀 파일을 처리하는 함수
    
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
            df = pd.read_excel(file_like)
            
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
                df = pd.read_excel(file_like, engine='xlrd')
                
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
                df = pd.read_excel(file_like, engine='openpyxl')
                
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
            return None, f"승인 파일을 읽을 수 없습니다. 다음 형식을 시도했으나 모두 실패했습니다:\n{error_details}"
        
        # 필요한 컬럼 확인
        required_columns = ["대분류", "매출 금액", "주문 일자", "상담사"]
        
        # 컬럼명이 비슷한 경우 매핑
        column_mapping = {}
        for req_col in required_columns:
            if req_col in df.columns:
                continue  # 이미 존재하면 매핑 불필요
                
            # 유사한 컬럼명 목록
            similar_cols = {
                "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"],
                "매출 금액": ["매출금액", "판매금액", "매출액", "순매출액", "매출금액(VAT제외)"],
                "주문 일자": ["주문일자", "주문날짜", "계약일자", "승인일자", "계약날짜", "승인날짜"],
                "상담사": ["상담원", "상담원명", "담당자", "담당상담사", "담당 상담사", "판매자"]
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
            
            if "매출 금액" in missing_columns and "매출금액" in df.columns:
                df["매출 금액"] = df["매출금액"]
                missing_columns.remove("매출 금액")
                
            if "매출 금액" in missing_columns and "매출금액(VAT제외)" in df.columns:
                df["매출 금액"] = df["매출금액(VAT제외)"]
                missing_columns.remove("매출 금액")
                
            if "상담사" in missing_columns and "상담원" in df.columns:
                df["상담사"] = df["상담원"]
                missing_columns.remove("상담사")
                
            if "상담사" in missing_columns and "담당자" in df.columns:
                df["상담사"] = df["담당자"]
                missing_columns.remove("상담사")
            
            if missing_columns:  # 여전히 누락된 컬럼이 있으면
                available_columns = ", ".join(df.columns.tolist()[:20]) + "..."  # 처음 20개만 표시
                return None, f"승인 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}\n사용 가능한 컬럼 일부: {available_columns}"
        
        # 날짜 컬럼이 있는 경우 날짜 타입으로 변환
        if "주문 일자" in df.columns:
            try:
                df["주문 일자"] = pd.to_datetime(df["주문 일자"], errors='coerce')
            except:
                pass  # 날짜 변환 실패 시 무시
        
        # 매출 금액을 숫자 타입으로 변환
        if "매출 금액" in df.columns:
            df["매출 금액"] = pd.to_numeric(df["매출 금액"], errors='coerce').fillna(0)
        
        # 빈 열(모든 값이 NaN) 제거
        df = df.dropna(axis=1, how='all')
        
        # 대분류 컬럼의 값이 NaN인 행 제거
        df = df.dropna(subset=["대분류"])
        
        return df, None
        
    except Exception as e:
        return None, f"승인 파일 처리 중 오류가 발생했습니다: {str(e)}"

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

def analyze_daily_approval(approval_df: pd.DataFrame) -> Tuple[Optional[Dict], Optional[str]]:
    """
    일일 승인 현황을 분석하는 함수
    
    Args:
        approval_df: 승인 데이터프레임
        
    Returns:
        Tuple[Optional[Dict], Optional[str]]: 분석 결과 딕셔너리와 오류 메시지(있는 경우)
    """
    try:
        # 데이터 검증
        if approval_df is None or approval_df.empty:
            return None, "승인 데이터가 비어 있습니다."
        
        if "주문 일자" not in approval_df.columns:
            return None, "주문 일자 컬럼이 필요합니다."
            
        if "대분류" not in approval_df.columns:
            return None, "대분류 컬럼이 필요합니다."
            
        if "매출 금액" not in approval_df.columns:
            return None, "매출 금액 컬럼이 필요합니다."
        
        # 주문 일자를 날짜로 변환 (이미 변환되어 있을 수 있음)
        if not pd.api.types.is_datetime64_any_dtype(approval_df["주문 일자"]):
            approval_df["주문 일자"] = pd.to_datetime(approval_df["주문 일자"], errors='coerce')
        
        # 가장 최근 날짜 찾기
        latest_date = approval_df["주문 일자"].dropna().max()
        if pd.isna(latest_date):
            latest_date = datetime.now()
            
        # 모든 상담사 목록 로드 (JSON 파일에서)
        all_consultants = get_all_consultants()
        
        # 결과 저장을 위한 데이터 구조
        results = {
            'consultant_data': [],
            'total_data': {
                'anma_count': 0,
                'anma_sales': 0,
                'lacloud_count': 0,
                'lacloud_sales': 0,
                'water_count': 0,
                'water_sales': 0,
                'total_count': 0,
                'total_sales': 0
            },
            'daily_data': {
                'anma_count': 0,
                'anma_sales': 0,
                'lacloud_count': 0,
                'lacloud_sales': 0,
                'water_count': 0,
                'water_sales': 0,
                'total_count': 0,
                'total_sales': 0
            },
            'latest_date': latest_date
        }
        
        # 일일 데이터 (최신 날짜) 필터링
        if latest_date is not None:
            daily_df = approval_df[approval_df["주문 일자"].dt.date == latest_date.date()].copy()
            
            # 일일 안마의자 건수 및 매출
            daily_anma_df = daily_df[daily_df["대분류"].str.contains("안마", case=False, na=False)]
            results['daily_data']['anma_count'] = len(daily_anma_df)
            results['daily_data']['anma_sales'] = daily_anma_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
            
            # 일일 라클라우드 건수 및 매출
            daily_lacloud_df = daily_df[daily_df["대분류"].str.contains("라클", case=False, na=False)]
            results['daily_data']['lacloud_count'] = len(daily_lacloud_df)
            results['daily_data']['lacloud_sales'] = daily_lacloud_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
            
            # 일일 정수기 건수 및 매출
            daily_water_df = daily_df[daily_df["대분류"].str.contains("정수기", case=False, na=False)]
            results['daily_data']['water_count'] = len(daily_water_df)
            results['daily_data']['water_sales'] = daily_water_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
            
            # 일일 총합
            results['daily_data']['total_count'] = (
                results['daily_data']['anma_count'] + 
                results['daily_data']['lacloud_count'] + 
                results['daily_data']['water_count']
            )
            results['daily_data']['total_sales'] = (
                results['daily_data']['anma_sales'] + 
                results['daily_data']['lacloud_sales'] + 
                results['daily_data']['water_sales']
            )
        
        # 전체 누적 분석
        # 안마의자 건수 및 매출
        anma_df = approval_df[approval_df["대분류"].str.contains("안마", case=False, na=False)]
        results['total_data']['anma_count'] = len(anma_df)
        results['total_data']['anma_sales'] = anma_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
        
        # 라클라우드 건수 및 매출
        lacloud_df = approval_df[approval_df["대분류"].str.contains("라클", case=False, na=False)]
        results['total_data']['lacloud_count'] = len(lacloud_df)
        results['total_data']['lacloud_sales'] = lacloud_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
        
        # 정수기 건수 및 매출
        water_df = approval_df[approval_df["대분류"].str.contains("정수기", case=False, na=False)]
        results['total_data']['water_count'] = len(water_df)
        results['total_data']['water_sales'] = water_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
        
        # 총합
        results['total_data']['total_count'] = (
            results['total_data']['anma_count'] + 
            results['total_data']['lacloud_count'] + 
            results['total_data']['water_count']
        )
        results['total_data']['total_sales'] = (
            results['total_data']['anma_sales'] + 
            results['total_data']['lacloud_sales'] + 
            results['total_data']['water_sales']
        )
        
        # 상담원별 분석 (JSON에 등록된 모든 상담원 포함)
        for consultant_name in all_consultants:
            # 상담사별 데이터 필터링
            consultant_df = approval_df[approval_df["상담사"] == consultant_name]
            
            # 상담사 데이터가 없는 경우 빈 데이터 생성
            if consultant_df.empty:
                team = get_team_by_consultant(consultant_name) or "기타"
                results['consultant_data'].append({
                    "상담사": consultant_name,
                    "조직": team,
                    "안마의자": 0,
                    "안마의자_매출액": 0,
                    "라클라우드": 0,
                    "라클라우드_매출액": 0,
                    "정수기": 0,
                    "정수기_매출액": 0,
                    "누적건수": 0,
                    "누적매출액": 0,
                    "일일건수": 0,
                    "일일매출액": 0,
                    "콜건수": 0,
                    "콜타임": "0:00:00",
                    "콜타임_초": 0
                })
                continue
            
            # 소속 팀 확인
            team = get_team_by_consultant(consultant_name) or "기타"
            
            # 안마의자 건수 및 매출
            anma_count = len(consultant_df[consultant_df["대분류"].str.contains("안마", case=False, na=False)])
            anma_sales = consultant_df[consultant_df["대분류"].str.contains("안마", case=False, na=False)]["매출 금액"].sum() / 1000000
            
            # 라클라우드 건수 및 매출
            lacloud_count = len(consultant_df[consultant_df["대분류"].str.contains("라클", case=False, na=False)])
            lacloud_sales = consultant_df[consultant_df["대분류"].str.contains("라클", case=False, na=False)]["매출 금액"].sum() / 1000000
            
            # 정수기 건수 및 매출
            water_count = len(consultant_df[consultant_df["대분류"].str.contains("정수기", case=False, na=False)])
            water_sales = consultant_df[consultant_df["대분류"].str.contains("정수기", case=False, na=False)]["매출 금액"].sum() / 1000000
            
            # 누적 총합
            total_count = anma_count + lacloud_count + water_count
            total_sales = anma_sales + lacloud_sales + water_sales
            
            # 일일 데이터 계산 (최신 날짜)
            daily_count = 0
            daily_sales = 0
            
            if latest_date is not None:
                daily_consultant_df = consultant_df[consultant_df["주문 일자"].dt.date == latest_date.date()]
                
                if not daily_consultant_df.empty:
                    daily_count = len(daily_consultant_df)
                    daily_sales = daily_consultant_df["매출 금액"].sum() / 1000000  # 백만 단위로 변환
            
            # 상담원 데이터 추가
            results['consultant_data'].append({
                "상담사": consultant_name,
                "조직": team,
                "안마의자": anma_count,
                "안마의자_매출액": anma_sales,
                "라클라우드": lacloud_count,
                "라클라우드_매출액": lacloud_sales,
                "정수기": water_count,
                "정수기_매출액": water_sales,
                "누적건수": total_count,
                "누적매출액": total_sales,
                "일일건수": daily_count,
                "일일매출액": daily_sales,
                "콜건수": 0,  # 콜타임 데이터와 매칭 시 업데이트
                "콜타임": "0:00:00",  # 콜타임 데이터와 매칭 시 업데이트
                "콜타임_초": 0  # 콜타임 데이터와 매칭 시 업데이트
            })
        
        # 누적매출액 기준으로 내림차순 정렬
        results['consultant_data'] = sorted(
            results['consultant_data'], 
            key=lambda x: (x["누적매출액"], x["누적건수"]), 
            reverse=True
        )
        
        return results, None
    
    except Exception as e:
        import traceback
        return None, f"일일 승인 현황 분석 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"

def match_consultant_calltime(
    approval_results: Dict, 
    calltime_df: pd.DataFrame
) -> Dict:
    """
    승인 분석 결과와 콜타임 데이터를 매칭하는 함수
    
    Args:
        approval_results: 승인 분석 결과 딕셔너리
        calltime_df: 콜타임 데이터프레임
        
    Returns:
        Dict: 콜타임이 매칭된 승인 분석 결과 딕셔너리
    """
    if calltime_df is None or calltime_df.empty:
        return approval_results
    
    # 상담원 데이터 업데이트
    for i, consultant_data in enumerate(approval_results['consultant_data']):
        consultant_name = consultant_data["상담사"]
        
        # 정확히 일치하는 이름 검색
        calltime_match = calltime_df[calltime_df["상담원명"] == consultant_name]
        
        # 일치하는 데이터가 없으면 유사 매칭 시도
        if calltime_match.empty:
            # 상담원명 전처리
            consultant_clean = consultant_name.strip()
            
            # 포함 관계 확인
            for _, row in calltime_df.iterrows():
                calltime_name = str(row["상담원명"]).strip()
                # 상담원명이 포함되거나 상담원명에 포함되는 경우
                if (consultant_clean in calltime_name) or (calltime_name in consultant_clean):
                    # 콜타임 정보 업데이트
                    approval_results['consultant_data'][i]["콜건수"] = row["총 건수"]
                    approval_results['consultant_data'][i]["콜타임"] = row["총 시간"]
                    approval_results['consultant_data'][i]["콜타임_초"] = row.get("총 시간_초", 0)
                    break
        else:
            # 첫 번째 일치하는 행의 콜타임 정보 사용
            row = calltime_match.iloc[0]
            approval_results['consultant_data'][i]["콜건수"] = row["총 건수"]
            approval_results['consultant_data'][i]["콜타임"] = row["총 시간"]
            approval_results['consultant_data'][i]["콜타임_초"] = row.get("총 시간_초", 0)
    
    return approval_results

def create_excel_report(
    approval_results: Dict,
    approval_df: pd.DataFrame
) -> Optional[bytes]:
    """
    분석 결과를 엑셀 파일로 변환하는 함수
    
    Args:
        approval_results: 승인 분석 결과 딕셔너리
        approval_df: 원본 승인 데이터프레임
        
    Returns:
        Optional[bytes]: 엑셀 바이너리 데이터 또는 None (오류 발생 시)
    """
    try:
        # 엑셀 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # 스타일 정의
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center',
                'fg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })
            
            subheader_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center',
                'fg_color': '#8EA9DB',
                'border': 1
            })
            
            date_format = workbook.add_format({
                'num_format': 'yyyy-mm-dd',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            decimal_format = workbook.add_format({
                'num_format': '#,##0.0',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            team_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#D9E1F2',
                'border': 1
            })
            
            # 결과 시트 작성
            results_sheet = workbook.add_worksheet('일일/누적 승인현황')
            
            # 행과 열 크기 설정
            results_sheet.set_column(0, 0, 15)  # 상담사 열
            results_sheet.set_column(1, 1, 10)  # 조직 열
            results_sheet.set_column(2, 13, 12)  # 데이터 열
            
            # 헤더 작성
            current_date = approval_results['latest_date'].strftime('%Y-%m-%d')
            results_sheet.merge_range('A1:N1', f'일일/누적 승인현황 ({current_date} 기준)', header_format)
            
            # 서브헤더 작성
            headers = [
                '상담사', '조직',
                '안마의자(건)', '안마의자(백만)', 
                '라클라우드(건)', '라클라우드(백만)', 
                '정수기(건)', '정수기(백만)', 
                '누적건수', '누적매출액(백만)', 
                '일일건수', '일일매출액(백만)', 
                '콜건수', '콜타임'
            ]
            
            for col, header in enumerate(headers):
                results_sheet.write(1, col, header, subheader_format)
            
            # 데이터 작성
            current_row = 2
            prev_team = None
            
            for idx, data in enumerate(approval_results['consultant_data']):
                team = data['조직']
                
                # 팀이 바뀌면 구분선 추가
                if team != prev_team and idx > 0:
                    for col in range(len(headers)):
                        results_sheet.write(current_row, col, "", team_format)
                    current_row += 1
                
                prev_team = team
                
                # 데이터 작성
                results_sheet.write(current_row, 0, data['상담사'], cell_format)
                results_sheet.write(current_row, 1, data['조직'], cell_format)
                
                # 안마의자
                results_sheet.write(current_row, 2, data['안마의자'], number_format)
                results_sheet.write(current_row, 3, data['안마의자_매출액'], decimal_format)
                
                # 라클라우드
                results_sheet.write(current_row, 4, data['라클라우드'], number_format)
                results_sheet.write(current_row, 5, data['라클라우드_매출액'], decimal_format)
                
                # 정수기
                results_sheet.write(current_row, 6, data['정수기'], number_format)
                results_sheet.write(current_row, 7, data['정수기_매출액'], decimal_format)
                
                # 누적 데이터
                results_sheet.write(current_row, 8, data['누적건수'], number_format)
                results_sheet.write(current_row, 9, data['누적매출액'], decimal_format)
                
                # 일일 데이터
                results_sheet.write(current_row, 10, data['일일건수'], number_format)
                results_sheet.write(current_row, 11, data['일일매출액'], decimal_format)
                
                # 콜타임 데이터
                results_sheet.write(current_row, 12, data['콜건수'], number_format)
                results_sheet.write(current_row, 13, data['콜타임'], cell_format)
                
                current_row += 1
            
            # 총합계 행 추가
            results_sheet.write(current_row, 0, "총합계", header_format)
            results_sheet.write(current_row, 1, "", header_format)
            
            # 안마의자 합계
            results_sheet.write(current_row, 2, approval_results['total_data']['anma_count'], header_format)
            results_sheet.write(current_row, 3, approval_results['total_data']['anma_sales'], header_format)
            
            # 라클라우드 합계
            results_sheet.write(current_row, 4, approval_results['total_data']['lacloud_count'], header_format)
            results_sheet.write(current_row, 5, approval_results['total_data']['lacloud_sales'], header_format)
            
            # 정수기 합계
            results_sheet.write(current_row, 6, approval_results['total_data']['water_count'], header_format)
            results_sheet.write(current_row, 7, approval_results['total_data']['water_sales'], header_format)
            
            # 누적 합계
            results_sheet.write(current_row, 8, approval_results['total_data']['total_count'], header_format)
            results_sheet.write(current_row, 9, approval_results['total_data']['total_sales'], header_format)
            
            # 일일 합계
            results_sheet.write(current_row, 10, approval_results['daily_data']['total_count'], header_format)
            results_sheet.write(current_row, 11, approval_results['daily_data']['total_sales'], header_format)
            
            # 콜타임 합계 (평균이 아니므로 공백)
            results_sheet.write(current_row, 12, "", header_format)
            results_sheet.write(current_row, 13, "", header_format)
            
            # 2. 로우데이터 시트 작성 (빈 열 제거)
            raw_data = approval_df.copy()
            
            # 빈 열 제거 (모든 값이 NaN인 열)
            raw_data = raw_data.dropna(axis=1, how='all')
            
            # 로우데이터 시트 작성
            raw_data.to_excel(writer, sheet_name='원본 데이터', index=False)
            
            # 로우데이터 시트 스타일링
            raw_sheet = writer.sheets['원본 데이터']
            
            # 헤더 포맷 적용
            for col_num, value in enumerate(raw_data.columns.values):
                raw_sheet.write(0, col_num, value, header_format)
            
            # 컬럼 너비 자동 조정
            for i, col in enumerate(raw_data.columns):
                max_len = max(
                    len(str(col)),
                    raw_data[col].astype(str).str.len().max() if not raw_data[col].empty else 0
                )
                # 최대 50, 최소 8
                column_width = min(max(max_len + 2, 8), 50)
                raw_sheet.set_column(i, i, column_width)
        
        # 파일 포인터 위치 초기화
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"엑셀 파일 생성 중 오류: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None