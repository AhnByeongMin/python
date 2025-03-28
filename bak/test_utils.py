"""
CRM 데이터 분석기 유틸리티 함수 단위 테스트

이 모듈은 utils.py 모듈의 함수들에 대한 단위 테스트를 포함합니다.
pytest 프레임워크를 사용하여 테스트를 실행합니다.

실행 방법:
    pytest test_utils.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, time
from io import BytesIO, StringIO
import html
import re

# 테스트할 모듈 임포트
from improved_utils import (
    format_date_columns, process_datetime, format_time,
    copy_to_clipboard, normalize_column_names, 
    get_previous_business_day, is_holiday
)

class TestDateFunctions:
    """날짜 처리 관련 함수 테스트"""
    
    def test_format_date_columns(self):
        """format_date_columns 함수 테스트"""
        # 테스트용 데이터프레임 생성
        df = pd.DataFrame({
            'date_col': pd.date_range('2023-01-01', periods=3),
            'text_col': ['A', 'B', 'C']
        })
        
        # 함수 실행
        result = format_date_columns(df)
        
        # 검증
        assert 'date_col_formatted' in result.columns
        assert result['date_col_formatted'].iloc[0] == '2023-01-01'
        assert 'text_col_formatted' not in result.columns
    
    def test_process_datetime_nat(self):
        """process_datetime 함수의 NaT 처리 테스트"""
        # NaT 값 테스트
        nat_value = pd.NaT
        result = process_datetime(nat_value)
        assert pd.isna(result)
    
    def test_process_datetime_date_only(self):
        """process_datetime 함수의 날짜만 반환 테스트"""
        # 시간이 00:00:00인 경우
        dt = pd.Timestamp('2023-01-01 00:00:00')
        result = process_datetime(dt)
        assert isinstance(result, date)
        assert result == date(2023, 1, 1)
    
    def test_process_datetime_time_only(self):
        """process_datetime 함수의 시간만 반환 테스트"""
        # 날짜가 1970-01-01이고 시간이 00:00:00이 아닌 경우
        dt = pd.Timestamp('1970-01-01 12:34:56')
        result = process_datetime(dt)
        assert isinstance(result, time)
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
    
    def test_process_datetime_full_datetime(self):
        """process_datetime 함수의 원본 datetime 반환 테스트"""
        # 일반적인 날짜+시간 값
        dt = pd.Timestamp('2023-01-01 12:34:56')
        result = process_datetime(dt)
        assert isinstance(result, pd.Timestamp)
        assert result == dt
    
    def test_format_time(self):
        """format_time 함수 테스트"""
        # 0 초
        assert format_time(0) == "0:00:00"
        
        # 일반 케이스
        assert format_time(3661) == "1:01:01"  # 1시간 1분 1초
        
        # NaN 값
        assert format_time(np.nan) == "0:00:00"
        
        # 큰 값
        assert format_time(90061) == "25:01:01"  # 25시간 1분 1초
    
    def test_is_holiday_weekend(self):
        """is_holiday 함수의 주말 체크 테스트"""
        # 토요일
        assert is_holiday(datetime(2023, 1, 7)) == True
        
        # 일요일
        assert is_holiday(datetime(2023, 1, 8)) == True
    
    def test_is_holiday_fixed_holiday(self):
        """is_holiday 함수의 법정 공휴일 체크 테스트"""
        # 신정
        assert is_holiday(datetime(2023, 1, 1)) == True
        
        # 삼일절
        assert is_holiday(datetime(2023, 3, 1)) == True
    
    def test_is_holiday_lunar_holiday(self):
        """is_holiday 함수의 음력 공휴일 체크 테스트"""
        # 설날 (2023년)
        assert is_holiday(datetime(2023, 1, 22)) == True
    
    def test_is_holiday_weekday(self):
        """is_holiday 함수의 평일 체크 테스트"""
        # 평일 (공휴일 아님)
        assert is_holiday(datetime(2023, 1, 2)) == False
    
    def test_get_previous_business_day(self):
        """get_previous_business_day 함수 테스트"""
        # 월요일 기준 (이전 영업일은 금요일)
        monday = datetime(2023, 1, 9)  # 월요일
        prev_day = get_previous_business_day(monday)
        assert prev_day.weekday() == 4  # 금요일 (1/6)
        
        # 화요일 기준 (이전 영업일은 월요일)
        tuesday = datetime(2023, 1, 10)  # 화요일
        prev_day = get_previous_business_day(tuesday)
        assert prev_day.weekday() == 0  # 월요일 (1/9)
        
        # 공휴일 다음날 기준
        day_after_holiday = datetime(2023, 1, 2)  # 신정 다음날
        prev_day = get_previous_business_day(day_after_holiday)
        # 이전 영업일은 12/30 (금) - 12/31,1/1은 주말과 공휴일
        assert prev_day.day == 30
        assert prev_day.month == 12
        assert prev_day.year == 2022


class TestUtilityFunctions:
    """기타 유틸리티 함수 테스트"""
    
    def test_copy_to_clipboard(self):
        """copy_to_clipboard 함수 테스트"""
        # 일반 문자열
        text = "Hello, World!"
        result = copy_to_clipboard(text)
        
        # 검증
        assert "<script>" in result
        assert "copyToClipboard" in result
        assert "Hello, World!" in result
        
        # HTML 이스케이프 테스트
        html_text = "<script>alert('XSS');</script>"
        result = copy_to_clipboard(html_text)
        
        # 검증
        assert "&lt;script&gt;" in result  # < 가 &lt;로 이스케이프됨
        assert "alert('XSS')" in result
        assert "&lt;/script&gt;" in result  # </ 가 &lt;/로 이스케이프됨
        
        # 비 문자열 입력 테스트
        num = 12345
        result = copy_to_clipboard(num)
        assert "12345" in result
    
    def test_normalize_column_names(self):
        """normalize_column_names 함수 테스트"""
        # 테스트용 데이터프레임
        df = pd.DataFrame({
            '고객명': ['홍길동', '김철수'],
            '연락처정보': ['010-1234-5678', '010-8765-4321'],
            '구매상품': ['노트북', '모니터']
        })
        
        # 컬럼명 매핑
        name_map = {
            '이름': ['고객명', '성명', '이름'],
            '연락처': ['연락처정보', '전화번호', '연락정보'],
            '상품': ['구매상품', '제품명', '상품명']
        }
        
        # 필수 컬럼
        required_cols = ['이름', '연락처']
        
        # 함수 실행
        new_df, missing = normalize_column_names(df, name_map, required_cols)
        
        # 검증
        assert '이름' in new_df.columns
        assert '연락처' in new_df.columns
        assert '상품' in new_df.columns
        assert len(missing) == 0
        
        # 누락된 필수 컬럼 테스트
        required_cols2 = ['이름', '연락처', '주소']
        new_df2, missing2 = normalize_column_names(df, name_map, required_cols2)
        
        # 검증
        assert '주소' in missing2
        assert len(missing2) == 1