"""
CRM 데이터 분석기 공통 유틸리티 함수 모듈 (리팩토링 버전)

이 모듈은 애플리케이션 전체에서 사용되는 공통 유틸리티 함수들을 포함합니다.
코드 중복을 제거하고 재사용성을 높이기 위해 리팩토링되었습니다.
"""

import pandas as pd
import base64
from io import BytesIO, StringIO
import io
import html
import re
import os
import time
import logging
import xlsxwriter
from datetime import datetime, timedelta, date
import requests
import xml.etree.ElementTree as ET
from typing import Union, Optional, Dict, List, Tuple, Any, Callable, TypeVar, cast

# 설정 파일 가져오기
from config import (
    API_SETTINGS, FIXED_HOLIDAYS, LUNAR_HOLIDAYS, ALTERNATIVE_HOLIDAYS,
    FILE_SETTINGS, ERROR_MESSAGES, SUCCESS_MESSAGES
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 타입 변수 정의
T = TypeVar('T')
R = TypeVar('R')


# ---------- 날짜 관련 유틸리티 함수 ----------

def format_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    데이터프레임의 날짜 컬럼들을 yyyy-mm-dd 형식으로 변환합니다.
    
    Args:
        df (pd.DataFrame): 변환할 데이터프레임
        
    Returns:
        pd.DataFrame: 날짜 컬럼이 포맷팅된 데이터프레임
    """
    try:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                # 화면 표시용 및 필터링용 문자열 날짜 컬럼 추가
                formatted_col_name = f"{col}_formatted"
                df[formatted_col_name] = df[col].dt.strftime('%Y-%m-%d')
        return df
    except Exception as e:
        logger.error(f"날짜 컬럼 포맷팅 중 오류 발생: {str(e)}")
        # 원본 데이터프레임 반환
        return df


def process_datetime(dt: pd.Timestamp) -> Union[datetime, pd.Timestamp, date, Any]:
    """
    날짜/시간 데이터를 처리하여 적절한 형식으로 변환합니다.
    
    Args:
        dt (pd.Timestamp): 변환할 날짜/시간 객체
        
    Returns:
        Union[datetime, pd.Timestamp, date]: 변환된 날짜, 시간 또는 원본 값
    """
    # NaT 값 체크 먼저
    if pd.isnull(dt):
        return dt
    
    # 시간이 완전히 00:00:00이면 날짜만 반환
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt.date()
    
    # 날짜가 1970-01-01이고 시간이 00:00:00이 아니면 시간만 반환
    if dt.date() == pd.Timestamp('1970-01-01').date() and (dt.hour != 0 or dt.minute != 0 or dt.second != 0):
        return dt.time()
    
    # 그 외의 경우 원래 datetime 반환
    return dt


def format_time(seconds: Union[int, float]) -> str:
    """
    초 단위 시간을 HH:MM:SS 형식으로 변환합니다.
    
    Args:
        seconds (Union[int, float]): 변환할 초 단위 시간
        
    Returns:
        str: HH:MM:SS 형식의 시간 문자열
    """
    if pd.isna(seconds) or seconds == 0:
        return "0:00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def is_holiday(date_obj: datetime) -> bool:
    """
    주어진 날짜가 공휴일 또는 주말인지 확인합니다.
    
    Args:
        date_obj (datetime): 확인할 날짜
        
    Returns:
        bool: 공휴일 또는 주말이면 True, 아니면 False
    """
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    date_tuple = (year, month, day)
    
    # 주말 체크 (토요일: 5, 일요일: 6)
    if date_obj.weekday() >= 5:
        return True
    
    # 법정 공휴일 체크 (백업 데이터)
    if (month, day) in FIXED_HOLIDAYS:
        return True
    
    # 설날/추석 체크 (백업 데이터)
    if date_tuple in LUNAR_HOLIDAYS:
        return True
    
    # 대체 공휴일 체크 (백업 데이터)
    if date_tuple in ALTERNATIVE_HOLIDAYS:
        return True
    
    # API 호출을 통한 공휴일 체크
    try:
        # API 요청 파라미터 설정
        params = {
            'serviceKey': API_SETTINGS["HOLIDAY_API_KEY"],
            'solYear': year,
            'solMonth': f"{month:02d}"
        }
        
        # API 요청
        response = requests.get(API_SETTINGS["HOLIDAY_API_URL"], params=params)
        
        # 응답이 비어있는지 확인
        if not response.content:
            return False
        
        # XML 응답 파싱
        root = ET.fromstring(response.content)
        
        # 응답 구조 확인 및 공휴일 검사
        items = root.find('.//items')
        if items is None:
            # items 요소가 없으면 공휴일 정보가 없는 것으로 간주
            return False
            
        # 공휴일 목록 순회
        for item in items.findall('./item'):
            # 공휴일 날짜 가져오기 (yyyyMMdd 형식)
            locdate_elem = item.find('locdate')
            if locdate_elem is not None and locdate_elem.text:
                locdate = locdate_elem.text
                holiday_date = datetime.strptime(locdate, '%Y%m%d').date()
                
                # 주어진 날짜와 일치하는지 확인
                if date_obj.date() == holiday_date:
                    return True
            
        return False
        
    except Exception as e:
        logger.error(f"공휴일 API 호출 중 오류 발생: {str(e)}")
        # 오류 발생 시 백업 공휴일 데이터만 사용 (주말은 이미 위에서 처리)
        return False


def get_previous_business_day(current_date: datetime) -> datetime:
    """
    현재 날짜 기준 이전 영업일(평일 & 공휴일 아님)을 찾습니다.
    
    Args:
        current_date (datetime): 기준 날짜
        
    Returns:
        datetime: 이전 영업일 날짜
    """
    # 하루 전부터 시작
    previous_day = current_date - timedelta(days=1)
    
    # 영업일(평일 & 공휴일 아님)을 찾을 때까지 하루씩 이동
    while is_holiday(previous_day):
        previous_day = previous_day - timedelta(days=1)
    
    return previous_day


# ---------- 파일 처리 관련 유틸리티 함수 ----------

def read_excel_file(file: Any, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    엑셀 파일을 읽어 데이터프레임으로 변환하는 통합 함수
    
    Args:
        file: 업로드된 파일 객체
        **kwargs: pandas read_excel에 전달할 추가 파라미터
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 데이터프레임과 오류 메시지(있는 경우)
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
        
        # 기본 엔진으로 시도
        try:
            file_like.seek(0)
            df = pd.read_excel(file_like, **kwargs)
            
            # 수동으로 중복 컬럼 처리
            if df is not None:
                df = fix_duplicate_columns(df)
                
        except Exception as e:
            errors.append(f"기본 엔진으로 읽기 실패: {str(e)}")
        
        # xlrd 엔진으로 시도
        if df is None:
            try:
                file_like.seek(0)
                df = pd.read_excel(file_like, engine='xlrd', **kwargs)
                
                if df is not None:
                    df = fix_duplicate_columns(df)
                
            except Exception as e:
                errors.append(f"xlrd 엔진으로 읽기 실패: {str(e)}")
        
        # openpyxl 엔진으로 시도
        if df is None:
            try:
                file_like.seek(0)
                df = pd.read_excel(file_like, engine='openpyxl', **kwargs)
                
                if df is not None:
                    df = fix_duplicate_columns(df)
                
            except Exception as e:
                errors.append(f"openpyxl 엔진으로 읽기 실패: {str(e)}")
        
        # 모든 방법이 실패한 경우
        if df is None:
            error_details = "\n".join(errors)
            return None, f"파일을 읽을 수 없습니다. 다음 형식을 시도했으나 모두 실패했습니다:\n{error_details}"
        
        # 빈 열 제거
        df = df.dropna(axis=1, how='all')
        
        return df, None
        
    except Exception as e:
        return None, f"엑셀 파일 처리 중 오류가 발생했습니다: {str(e)}"


def fix_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    중복된 컬럼명을 가진 데이터프레임을 수정하는 함수
    
    Args:
        df: 원본 데이터프레임
        
    Returns:
        pd.DataFrame: 중복 컬럼이 수정된 데이터프레임
    """
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
    
    return df


def peek_file_content(file: Any, n_bytes: int = FILE_SETTINGS["PREVIEW_BYTES"]) -> str:
    """
    파일의 처음 n_bytes만큼을 읽어 내용을 미리보기 합니다.
    
    Args:
        file: 파일 객체
        n_bytes (int, optional): 읽을 바이트 수. 기본값은 설정 파일에서 가져옴.
        
    Returns:
        str: 파일 내용 미리보기 문자열
    """
    try:
        file.seek(0)
        content = file.read(n_bytes)
        if isinstance(content, bytes):
            # 여러 인코딩 시도
            for encoding in FILE_SETTINGS["SUPPORTED_ENCODINGS"]:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            # 모든 인코딩 실패 시 무시하고 디코딩
            return content.decode(FILE_SETTINGS["DEFAULT_ENCODING"], errors='ignore')
        return str(content)
    except Exception as e:
        error_msg = ERROR_MESSAGES["FILE_CONTENT_ERROR"].format(error=str(e))
        logger.error(error_msg)
        return error_msg


# ---------- 데이터 처리 유틸리티 함수 ----------

def normalize_column_names(df: pd.DataFrame, name_map: Dict[str, List[str]], required_columns: Optional[List[str]] = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    데이터프레임의 컬럼명을 정규화하고 필수 컬럼을 확인합니다.
    
    Args:
        df (pd.DataFrame): 원본 데이터프레임
        name_map (Dict[str, List[str]]): 정규화할 컬럼명 매핑 (표준이름: [유사한 이름들])
        required_columns (Optional[List[str]]): 필수 컬럼 목록
        
    Returns:
        Tuple[pd.DataFrame, List[str]]: 정규화된 데이터프레임과 누락된 필수 컬럼 목록
    """
    # 컬럼명 매핑 사전 생성
    column_mapping = {}
    
    # 유사한 컬럼명 찾아서 매핑
    for standard_name, similar_names in name_map.items():
        # 이미 표준 이름이 있으면 넘어감
        if standard_name in df.columns:
            continue
            
        # 유사한 이름 찾기
        for col in df.columns:
            col_str = str(col).lower()
            if any(similar.lower() in col_str for similar in similar_names):
                column_mapping[col] = standard_name
                break
    
    # 컬럼명 변경
    if column_mapping:
        df = df.rename(columns=column_mapping)
    
    # 필수 컬럼 확인
    missing_columns = []
    if required_columns:
        missing_columns = [col for col in required_columns if col not in df.columns]
    
    return df, missing_columns


def time_to_seconds(time_str: str) -> int:
    """
    시간 문자열(HH:MM:SS)을 초 단위로 변환합니다.
    
    Args:
        time_str (str): 변환할 시간 문자열
        
    Returns:
        int: 초 단위 시간
    """
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


def copy_to_clipboard(text: Any) -> str:
    """
    텍스트를 클립보드에 복사하는 JavaScript 함수를 생성합니다.
    
    Args:
        text (Any): 복사할 텍스트 (문자열로 변환됨)
        
    Returns:
        str: JavaScript 코드를 포함한 HTML 문자열
    """
    if not isinstance(text, str):
        text = str(text)  # 문자열로 변환

    # HTML 특수 문자 처리 (XSS 방지)
    safe_text = html.escape(text)
    
    # 클립보드 복사 JavaScript 코드
    copy_js = f"""
    <script>
    function copyToClipboard() {{
        const el = document.createElement('textarea');
        el.value = `{safe_text}`;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        
        // 성공 메시지 표시
        document.getElementById('copy-success').style.display = 'block';
        setTimeout(() => {{
            document.getElementById('copy-success').style.display = 'none';
        }}, 3000);
    }}
    </script>
    """
    return copy_js


# ---------- 엑셀 관련 유틸리티 함수 ----------

def create_excel_file(sheets_data: Dict[str, Union[pd.DataFrame, Dict[str, Any]]], filename: str = "export.xlsx") -> BytesIO:
    """
    여러 시트를 포함하는 엑셀 파일을 생성하는 통합 함수
    
    Args:
        sheets_data (Dict[str, Union[pd.DataFrame, Dict]]): 
            시트명을 키로 하고 데이터프레임이나 포맷 정보를 포함한 딕셔너리를 값으로 갖는 딕셔너리
            예: {'시트1': df1, '시트2': {'data': df2, 'formats': {'A1': header_format}}}
        filename (str, optional): 생성할 파일명
        
    Returns:
        BytesIO: 엑셀 바이너리 데이터를 포함하는 BytesIO 객체
    """
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # 공통 스타일 정의
            header_format = workbook.add_format({
                'bold': True, 
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0'
            })
            
            percent_format = workbook.add_format({
                'num_format': '0.0%'
            })
            
            date_format = workbook.add_format({
                'num_format': 'yyyy-mm-dd'
            })
            
            # 각 시트 데이터 처리
            for sheet_name, sheet_data in sheets_data.items():
                if isinstance(sheet_data, pd.DataFrame):
                    # 데이터프레임인 경우 기본 스타일로 저장
                    df = sheet_data
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # 헤더 스타일 적용
                    worksheet = writer.sheets[sheet_name]
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                    
                    # 컬럼 너비 자동 조정
                    for i, col in enumerate(df.columns):
                        column_width = max(len(str(col)), df[col].astype(str).str.len().max())
                        worksheet.set_column(i, i, column_width + 2)  # 여유 공간 추가
                else:
                    # 딕셔너리 형태로 추가 설정을 제공하는 경우
                    df = sheet_data.get('data')
                    if df is not None and isinstance(df, pd.DataFrame):
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # 커스텀 포맷 적용
                        formats = sheet_data.get('formats', {})
                        column_formats = sheet_data.get('column_formats', {})
                        worksheet = writer.sheets[sheet_name]
                        
                        # 특정 셀 포맷 적용
                        for cell, fmt in formats.items():
                            worksheet.write(cell, None, fmt)
                        
                        # 특정 컬럼 포맷 적용
                        for col, fmt in column_formats.items():
                            col_idx = df.columns.get_loc(col) if col in df.columns else -1
                            if col_idx >= 0:
                                for row_idx in range(1, len(df) + 1):  # 헤더 제외
                                    value = df[col].iloc[row_idx-1]
                                    if fmt == 'number':
                                        worksheet.write_number(row_idx, col_idx, value, number_format)
                                    elif fmt == 'percent':
                                        worksheet.write_number(row_idx, col_idx, value / 100, percent_format)
                                    elif fmt == 'date':
                                        worksheet.write_datetime(row_idx, col_idx, value, date_format)
        
        # 버퍼 위치를 처음으로 되돌림
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"엑셀 파일 생성 중 오류 발생: {str(e)}")
        raise


def get_download_link(data: bytes, filename: str, label: str = "다운로드", mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") -> str:
    """
    바이너리 데이터에 대한 다운로드 링크를 생성합니다.
    
    Args:
        data (bytes): 다운로드할 바이너리 데이터
        filename (str): 다운로드될 파일 이름
        label (str, optional): 다운로드 버튼에 표시될 텍스트. 기본값은 "다운로드".
        mime (str, optional): MIME 타입. 기본값은 Excel MIME 타입.
        
    Returns:
        str: HTML 다운로드 링크
    """
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}" class="download-button">{label}</a>'
    return href


# ---------- 에러 처리 관련 유틸리티 함수 ----------

def standardized_error_handler(func: Callable[..., T]) -> Callable[..., Tuple[Optional[T], Optional[str]]]:
    """
    함수 실행 중 발생하는 예외를 표준화된 방식으로 처리하는 데코레이터.
    
    Args:
        func: 래핑할 함수
        
    Returns:
        래핑된 함수
    """
    def wrapper(*args, **kwargs) -> Tuple[Optional[T], Optional[str]]:
        try:
            result = func(*args, **kwargs)
            return result, None
        except Exception as e:
            error_type = func.__name__ + "_error"
            error_message = f"{func.__name__} 중 오류가 발생했습니다: {str(e)}"
            
            # 로깅
            logger.error(error_message, exc_info=True)
            
            # 표준 에러 메시지 반환
            return None, error_message
    return wrapper


# ---------- 성능 측정 유틸리티 함수 ----------

def measure_performance(func: Callable[..., R]) -> Callable[..., R]:
    """
    함수의 실행 시간을 측정하는 데코레이터
    
    Args:
        func: 래핑할 함수
        
    Returns:
        래핑된 함수
    """
    def wrapper(*args, **kwargs) -> R:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # 실행 시간 로깅
        logger.info(f"{func.__name__} 함수 실행 시간: {end_time - start_time:.4f}초")
        
        return result
    return wrapper


# ---------- 편의 함수 ----------

def create_timestamp_id() -> str:
    """
    현재 시간 기반으로 고유 ID를 생성합니다.
    
    Returns:
        str: 시간 기반 고유 ID
    """
    import uuid
    now = datetime.now()
    date_part = now.strftime('%Y%m%d')
    uuid_part = str(uuid.uuid4())[:8]
    return f"{date_part}_{uuid_part}"
