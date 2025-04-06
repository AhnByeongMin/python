"""
CRM 데이터 분석기 유틸리티 함수 모듈

이 모듈은 애플리케이션 전체에서 사용되는 유틸리티 함수들을 포함합니다.
각 함수는 특정 기능을 수행하며, 여러 모듈에서 재사용 가능합니다.
"""

import pandas as pd
import base64
from io import BytesIO
import io
import html
import re
from datetime import datetime, timedelta
import requests
import xml.etree.ElementTree as ET
import logging
from typing import Union, Optional, Dict, List, Tuple, Any

# 설정 파일 가져오기
from .config import (
    API_SETTINGS, FIXED_HOLIDAYS, LUNAR_HOLIDAYS, ALTERNATIVE_HOLIDAYS,
    FILE_SETTINGS, ERROR_MESSAGES
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    데이터프레임의 날짜 컬럼들을 yyyy-mm-dd 형식으로 변환합니다.
    
    Args:
        df (pd.DataFrame): 변환할 데이터프레임
        
    Returns:
        pd.DataFrame: 날짜 컬럼이 포맷팅된 데이터프레임
        
    Example:
        >>> df = pd.DataFrame({'date': pd.date_range('2023-01-01', periods=3)})
        >>> formatted_df = format_date_columns(df)
        >>> formatted_df.columns
        Index(['date', 'date_formatted'], dtype='object')
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

def process_datetime(dt: pd.Timestamp) -> Union[datetime, pd.Timestamp]:
    """
    날짜/시간 데이터를 처리하여 적절한 형식으로 변환합니다.
    
    Args:
        dt (pd.Timestamp): 변환할 날짜/시간 객체
        
    Returns:
        Union[datetime, pd.Timestamp]: 변환된 날짜, 시간 또는 원본 값
        
    Notes:
        - NaT(Not a Time) 값은 그대로 반환
        - 시간이 00:00:00인 경우 날짜만 반환
        - 날짜가 1970-01-01이고 시간이 00:00:00이 아닌 경우 시간만 반환
        - 그 외의 경우 원래 datetime 값 반환
        
    Example:
        >>> dt = pd.Timestamp('2023-01-01 00:00:00')
        >>> process_datetime(dt)
        datetime.date(2023, 1, 1)
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
        
    Example:
        >>> format_time(3665)
        '1:01:05'
        >>> format_time(0)
        '0:00:00'
    """
    if pd.isna(seconds) or seconds == 0:
        return "0:00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"

def copy_to_clipboard(text: Any) -> str:
    """
    텍스트를 클립보드에 복사하는 JavaScript 함수를 생성합니다.
    
    Args:
        text (Any): 복사할 텍스트 (문자열로 변환됨)
        
    Returns:
        str: JavaScript 코드를 포함한 HTML 문자열
        
    Notes:
        - XSS 방지를 위해 HTML 특수 문자를 이스케이프 처리
        - 복사 성공 시 사용자에게 알림을 표시하는 UI 요소 포함
        
    Example:
        >>> js_code = copy_to_clipboard("Example text")
        >>> "<script>" in js_code and "copyToClipboard" in js_code
        True
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

def peek_file_content(file: Any, n_bytes: int = FILE_SETTINGS["PREVIEW_BYTES"]) -> str:
    """
    파일의 처음 n_bytes만큼을 읽어 내용을 미리보기 합니다.
    
    Args:
        file: 파일 객체
        n_bytes (int, optional): 읽을 바이트 수. 기본값은 설정 파일에서 가져옴.
        
    Returns:
        str: 파일 내용 미리보기 문자열
        
    Notes:
        - 바이너리 파일의 경우 여러 인코딩으로 디코딩 시도
        - 모든 인코딩 시도가 실패하면 기본 UTF-8 인코딩으로 강제 변환 (오류 무시)
        
    Example:
        >>> with open('example.txt', 'w') as f:
        ...     f.write('Hello World')
        >>> with open('example.txt', 'rb') as f:
        ...     preview = peek_file_content(f, 5)
        >>> preview
        'Hello'
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

def is_holiday(date: datetime) -> bool:
    """
    주어진 날짜가 공휴일 또는 주말인지 확인합니다.
    
    Args:
        date (datetime): 확인할 날짜
        
    Returns:
        bool: 공휴일 또는 주말이면 True, 아니면 False
        
    Notes:
        - 주말(토요일, 일요일) 자동 확인
        - 양력 기반 법정 공휴일 확인
        - 음력 기반 공휴일(설날, 추석) 확인
        - 대체 공휴일 확인
        - 공공데이터포털 API를 통한 공휴일 정보 추가 확인
        
    Example:
        >>> from datetime import datetime
        >>> is_holiday(datetime(2023, 1, 1))  # 신정
        True
        >>> is_holiday(datetime(2023, 1, 2))  # 평일
        False
    """
    year = date.year
    month = date.month
    day = date.day
    date_tuple = (year, month, day)
    
    # 주말 체크 (토요일: 5, 일요일: 6)
    if date.weekday() >= 5:
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
                if date.date() == holiday_date:
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
        
    Notes:
        - 공휴일과 주말은 영업일에서 제외됨
        - 영업일을 찾을 때까지 하루씩 이전 날짜로 이동
        
    Example:
        >>> from datetime import datetime
        >>> # 월요일이라고 가정할 때, 이전 영업일은 금요일
        >>> prev_day = get_previous_business_day(datetime(2023, 1, 2))
        >>> prev_day.strftime('%Y-%m-%d')  # 2022-12-30 (금요일)
    """
    # 하루 전부터 시작
    previous_day = current_date - timedelta(days=1)
    
    # 영업일(평일 & 공휴일 아님)을 찾을 때까지 하루씩 이동
    while is_holiday(previous_day):
        previous_day = previous_day - timedelta(days=1)
    
    return previous_day

def standardized_error_handler(func):
    """
    함수 실행 중 발생하는 예외를 표준화된 방식으로 처리하는 데코레이터.
    
    Args:
        func: 래핑할 함수
        
    Returns:
        래핑된 함수
        
    Notes:
        - 함수 실행 중 발생하는 모든 예외를 잡아서 로깅
        - 오류 메시지를 표준화된 형식으로 반환
        - 디버깅 정보 포함
        
    Example:
        >>> @standardized_error_handler
        ... def divide(a, b):
        ...     return a / b
        >>> divide(10, 0)
        (None, '연산 중 오류가 발생했습니다: division by zero')
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs), None
        except Exception as e:
            error_type = func.__name__ + "_error"
            error_message = f"{func.__name__} 중 오류가 발생했습니다: {str(e)}"
            
            # 로깅
            logger.error(error_message, exc_info=True)
            
            # 표준 에러 메시지 반환
            return None, error_message
    return wrapper

# 추가 유틸리티 함수들

def generate_excel_document(dataframes: Dict[str, pd.DataFrame], filename: str = "export.xlsx") -> BytesIO:
    """
    여러 데이터프레임을 포함하는 엑셀 문서를 생성합니다.
    
    Args:
        dataframes (Dict[str, pd.DataFrame]): 시트명을, 데이터프레임을 키로 하는 딕셔너리
        filename (str, optional): 생성할 파일명
        
    Returns:
        BytesIO: 엑셀 바이너리 데이터를 포함하는 BytesIO 객체
        
    Example:
        >>> df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        >>> df2 = pd.DataFrame({'C': [5, 6], 'D': [7, 8]})
        >>> excel_data = generate_excel_document({'Sheet1': df1, 'Sheet2': df2})
        >>> isinstance(excel_data, BytesIO)
        True
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
            
            # 각 데이터프레임을 별도 시트로 저장
            for sheet_name, df in dataframes.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 스타일 적용
                worksheet = writer.sheets[sheet_name]
                
                # 헤더 행에 스타일 적용
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # 컬럼 폭 자동 조정
                for i, col in enumerate(df.columns):
                    column_width = max(len(str(col)), df[col].astype(str).str.len().max())
                    worksheet.set_column(i, i, column_width + 2)  # 여유 공간 추가
        
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
        
    Example:
        >>> data = b'example data'
        >>> link = get_download_link(data, 'example.txt', 'Download Text', 'text/plain')
        >>> '<a href=' in link and 'example.txt' in link
        True
    """
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}" class="download-button">{label}</a>'
    return href

def normalize_column_names(df: pd.DataFrame, name_map: Dict[str, List[str]], required_columns: Optional[List[str]] = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    데이터프레임의 컬럼명을 정규화하고 필수 컬럼을 확인합니다.
    
    Args:
        df (pd.DataFrame): 원본 데이터프레임
        name_map (Dict[str, List[str]]): 정규화할 컬럼명 매핑 (표준이름: [유사한 이름들])
        required_columns (Optional[List[str]]): 필수 컬럼 목록
        
    Returns:
        Tuple[pd.DataFrame, List[str]]: 정규화된 데이터프레임과 누락된 필수 컬럼 목록
        
    Example:
        >>> df = pd.DataFrame({'이름': [1, 2], '나이정보': [30, 40]})
        >>> name_map = {'이름': ['name', '성명'], '나이': ['나이정보', 'age']}
        >>> new_df, missing = normalize_column_names(df, name_map, ['이름', '나이'])
        >>> '이름' in new_df.columns and '나이' in new_df.columns
        True
        >>> missing
        []
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