"""
매출 데이터 분석 비즈니스 로직

이 모듈은 매출 데이터를 처리하고 분석하는 순수 비즈니스 로직을 포함합니다.
UI와 독립적으로 작동하여 유닛 테스트가 용이하도록 설계되었습니다.
"""

import pandas as pd
from io import BytesIO
import xlsxwriter
import re
from typing import Tuple, Dict, List, Optional, Any, Union

# utils.py에서 함수 import
from utils.utils import format_date_columns, process_datetime

def process_excel(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    엑셀 파일을 읽고 데이터를 전처리하는 함수
    
    매개변수:
        file: 업로드된 엑셀 파일 객체
        
    반환값:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(file, parse_dates=True)
        
        # 날짜/시간 컬럼에 대해 process_datetime 적용
        date_time_columns = df.select_dtypes(include=['datetime64']).columns
        
        for col in date_time_columns:
            df[col] = df[col].apply(process_datetime)
        
        # Total 행 체크 및 제거 (A열에 'Total'이 있는 행부터 모두 제거)
        if 'Total' in df.iloc[:, 0].values:
            total_idx = df.iloc[:, 0].eq('Total').idxmax()
            df = df.iloc[:total_idx]
        
        # 빈 열 제거 (Unnamed 열 등)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # VAT 세율 설정 - 1.1%
        vat_rate = 0.011
        
        # 필요한 컬럼 확인 - 대분류 대신 품목명 사용
        required_columns = ["월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
                          "판매 금액", "선납 렌탈 금액", "품목명"]
                          
        # 대분류 컬럼이 없고 품목명이 있으면 품목명 사용
        has_product_name = "품목명" in df.columns
        has_category = "대분류" in df.columns
        
        if has_product_name:
            category_column = "품목명"
        elif has_category:
            category_column = "대분류"
            # 대분류 컬럼을 품목명으로 복제
            df["품목명"] = df["대분류"]
        else:
            return None, "품목명 또는 대분류 열이 필요합니다."
        
        # 필수 컬럼 확인 (품목명 제외)
        missing_columns = [col for col in required_columns[:-1] if col not in df.columns]
        if missing_columns:
            return None, f"필요한 열이 없습니다: {', '.join(missing_columns)}"
        
        # 숫자형 변환 (품목명 제외한 모든 필수 컬럼)
        for col in required_columns[:-1]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 매출금액 계산 전 패키지 할인 회차 데이터 정제
        # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
        df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace([39, 59, 60], 0)
        
        # 매출금액 계산 공식
        df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                      df['판매 금액'] + df['선납 렌탈 금액'])
        
        # VAT 제외 매출금액 계산
        df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
        
        # 날짜 컬럼 포맷팅
        df = format_date_columns(df)
        
        return df, None
    except Exception as e:
        return None, f"파일 처리 중 오류가 발생했습니다: {str(e)}"

def analyze_data(df: pd.DataFrame, filters: Optional[Dict] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    데이터프레임을 분석하여 품목별 집계 결과를 생성하는 함수
    
    매개변수:
        df: 분석할 데이터프레임
        filters: 적용할 필터 딕셔너리 (선택적)
        
    반환값:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 분석 결과 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 필터가 제공된 경우 데이터프레임 필터링
        if filters:
            for field, filter_value in filters.items():
                if pd.api.types.is_datetime64_any_dtype(df[field]):
                    # 날짜 필드인 경우
                    start_date, end_date = filter_value
                    df = df[(df[field].dt.date >= start_date) & 
                            (df[field].dt.date <= end_date)]
                
                elif pd.api.types.is_numeric_dtype(df[field]):
                    # 숫자 필드인 경우
                    min_val, max_val = filter_value
                    df = df[(df[field] >= min_val) & 
                            (df[field] <= max_val)]
                
                else:
                    # 카테고리/문자열 필드인 경우
                    df = df[df[field].isin(filter_value)]
        
        if '품목명' not in df.columns:
            return None, "품목명 열이 없습니다."
            
        # 품목별 승인건수와 매출금액 집계
        analysis = df.groupby('품목명').agg(
            승인건수=('품목명', 'count'),
            매출금액_VAT제외=('매출금액(VAT제외)', 'sum')
        ).reset_index()
        
        # 지정된 순서로 정렬 (안마의자, 라클라우드, 정수기)
        order = ['안마의자', '라클라우드', '정수기']
        
        # 카테고리형 변환 후 정렬
        analysis['품목명'] = pd.Categorical(
            analysis['품목명'], 
            categories=order, 
            ordered=True
        )
        analysis = analysis.sort_values('품목명')
        
        # 숫자 포맷팅 (천 단위 구분 기호 추가)
        analysis['매출금액_VAT제외_포맷'] = analysis['매출금액_VAT제외'].apply(lambda x: f"{x:,.0f}")
        
        return analysis, None
    except Exception as e:
        return None, f"데이터 분석 중 오류가 발생했습니다: {str(e)}"

def to_excel(df: pd.DataFrame, analysis_df: pd.DataFrame) -> Optional[bytes]:
    """
    데이터프레임을 엑셀 파일로 변환하는 함수
    
    매개변수:
        df: 원본 데이터프레임
        analysis_df: 분석 결과 데이터프레임
        
    반환값:
        Optional[bytes]: 엑셀 바이너리 데이터 또는 None (오류 발생 시)
    """
    try:
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        
        # 첫 번째 시트 - 승인건수 (필터링된 원본 데이터)
        df.to_excel(writer, sheet_name='승인건수', index=False)
        
        # 두 번째 시트 - 분석데이터 (집계 결과)
        analysis_for_excel = analysis_df.copy()
        
        # 포맷팅된 매출금액 컬럼 사용 (숫자 포맷팅 컬럼으로 대체)
        if '매출금액_VAT제외_포맷' in analysis_for_excel.columns:
            analysis_for_excel.rename(columns={'매출금액_VAT제외_포맷': '매출금액(VAT제외)'}, inplace=True)
            analysis_for_excel.drop('매출금액_VAT제외', axis=1, inplace=True)
        
        # 임시 분석용 숫자 컬럼 제거
        if '매출금액_숫자' in analysis_for_excel.columns:
            analysis_for_excel.drop('매출금액_숫자', axis=1, inplace=True)
        
        # 분석 데이터 저장
        analysis_for_excel.to_excel(writer, sheet_name='분석데이터', index=False)
        
        # 스타일 적용
        workbook = writer.book
        worksheet = writer.sheets['분석데이터']
        
        # 헤더 셀 스타일 정의
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # 헤더 행에 스타일 적용
        for col_num, value in enumerate(analysis_for_excel.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # 컬럼 폭 자동 조정
        for i, col in enumerate(analysis_for_excel.columns):
            column_width = max(len(str(col)), analysis_for_excel[col].astype(str).str.len().max())
            worksheet.set_column(i, i, column_width + 2)  # 여유 공간 추가
        
        writer.close()
        processed_data = output.getvalue()
        return processed_data
    except Exception as e:
        return None