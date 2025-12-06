"""
캠페인/정규분배 현황 비즈니스 로직 [최적화 버전]

이 모듈은 캠페인/정규분배 현황 탭의 데이터 처리 및 분석 로직을 포함합니다.
UI와 독립적으로 작동하여 단위 테스트가 가능하도록 설계되었습니다.

최적화 적용 사항:
- apply(lambda) → 벡터화 연산 (np.select)
- iterrows() → itertuples() 변환
"""

import pandas as pd
import numpy as np
import streamlit as st
import io
from io import BytesIO  # BytesIO를 명시적으로 import
import time
import re
import xlsxwriter
from typing import Tuple, Dict, List, Optional, Any, Union

# 설정 가져오기 (config.py에서 상수 가져오기)
from utils.config import CAMPAIGN_SETTINGS


# ============================================
# 최적화 함수 - 벡터화 연산
# ============================================

def get_campaign_type_vectorized(campaign_series: pd.Series) -> pd.Series:
    """
    캠페인 타입 분류 함수 - 벡터화 버전

    Args:
        campaign_series: 캠페인명 시리즈

    Returns:
        pd.Series: 정렬 순서 시리즈
    """
    campaign_lower = campaign_series.fillna('').astype(str).str.lower()

    # 조건 정의
    cond_campaign = campaign_lower.str.contains('캠', na=False)
    cond_regular = campaign_lower.str.contains('정규', na=False)
    cond_redistribution = campaign_lower.str.contains('재분배', na=False)

    # 선택지
    choices = [
        CAMPAIGN_SETTINGS["CAMPAIGN_TYPE_ORDER"]["CAMPAIGN"],      # 캠페인
        CAMPAIGN_SETTINGS["CAMPAIGN_TYPE_ORDER"]["REGULAR"],       # 정규
        CAMPAIGN_SETTINGS["CAMPAIGN_TYPE_ORDER"]["REDISTRIBUTION"] # 재분배
    ]
    conditions = [cond_campaign, cond_regular, cond_redistribution]

    return pd.Series(
        np.select(conditions, choices, default=CAMPAIGN_SETTINGS["CAMPAIGN_TYPE_ORDER"]["OTHER"]),
        index=campaign_series.index
    )

def process_campaign_files(files) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], int, int]:
    """
    다수의 엑셀 파일을 처리하는 함수

    Args:
        files: 업로드된 엑셀 파일 목록

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], int, int]:
            처리 결과 데이터프레임, 중복 제거된 원본 데이터, 중복 제거 전 개수, 중복 제거 후 개수
    """
    all_data = []
    total_before_dedup = 0
    total_after_dedup = 0

    # 각 파일 처리
    for file in files:
        try:
            # 파일 포인터 초기화
            file.seek(0)
            
            # 엑셀 파일 읽기 (3행부터 데이터 시작)
            df = pd.read_excel(file, header=2)
            
            # 빈 열 제거
            df = df.dropna(axis=1, how='all')
            
            # 필요한 컬럼이 있는지 확인
            required_cols = ["일반회차 캠페인", "상담DB상태", "상담주문번호"]
            found_cols = {}
            
            for req_col in required_cols:
                # 정확한 이름 매칭
                if req_col in df.columns:
                    found_cols[req_col] = req_col
                    continue
                    
                # 유사한 이름 찾기
                for col in df.columns:
                    if req_col in col:
                        found_cols[req_col] = col
                        break
            
            # 필요한 컬럼을 모두 찾았는지 확인
            if len(found_cols) < 2:  # 최소 캠페인과 상담DB상태 컬럼은 필요
                st.warning(f"{file.name}: 필요한 컬럼을 찾을 수 없습니다.")
                continue
            
            # 컬럼 이름 변경 (발견된 열만)
            df = df.rename(columns={v: k for k, v in found_cols.items()})

            # 상담주문번호 컬럼이 있으면 중복 제거
            if "상담주문번호" in df.columns:
                before_count = len(df)
                df.drop_duplicates(subset=["상담주문번호"], inplace=True)
                after_count = len(df)
                total_before_dedup += before_count
                total_after_dedup += after_count
            
            # 일반회차 캠페인 컬럼이 있는 경우에만 처리
            if "일반회차 캠페인" in df.columns:
                # NaN 값이나 None 값 제외
                df = df.dropna(subset=["일반회차 캠페인"])
                
                # 캠페인 값이 "캠", "정규", "재분배" 중 하나 이상 포함된 행만 유지
                df = df[df["일반회차 캠페인"].astype(str).str.contains("캠|정규|재분배|V-|C-|C_|AS-", case=False)]
            
            # 전체 데이터에 추가
            all_data.append(df)
            
        except Exception as e:
            st.error(f"{file.name} 처리 중 오류가 발생했습니다: {str(e)}")
    
    # 데이터가 없는 경우
    if not all_data:
        st.error("처리 가능한 데이터가 없습니다.")
        return None, None, 0, 0
    
    # 모든 데이터 합치기
    try:
        combined_df = pd.concat(all_data, ignore_index=True)
    except Exception as e:
        st.error(f"데이터 결합 중 오류가 발생했습니다: {str(e)}")
        return None, None, 0, 0

    # 데이터가 비어 있는 경우
    if combined_df.empty:
        st.error("결합된 데이터가 비어 있습니다.")
        return None, None, 0, 0
    
    # 중복 제거된 원본 데이터 저장
    cleaned_data = combined_df.copy()
    
    # 그룹화 및 집계
    try:
        # 필요한 컬럼이 있는지 확인
        if "일반회차 캠페인" not in combined_df.columns or "상담DB상태" not in combined_df.columns:
            st.error("일반회차 캠페인 또는 상담DB상태 컬럼이 없습니다.")
            return None, None, 0, 0
        
        # 피벗 테이블 생성 - 일반회차 캠페인 × 상담DB상태의 레코드 수
        pivot_df = pd.pivot_table(
            combined_df,
            index='일반회차 캠페인',
            columns='상담DB상태',
            aggfunc='size',  # 각 조합의 레코드 수를 계산
            fill_value=0     # 없는 조합은 0으로 채움
        )
        
        # 총합계 열 추가
        pivot_df['총합계'] = pivot_df.sum(axis=1)
        
        # 전환율 계산 (주문승인/총합계)
        if '주문승인' in pivot_df.columns:
            pivot_df['전환율'] = pivot_df['주문승인'] / pivot_df['총합계'] * 100

        # 인덱스 리셋 및 정렬 카테고리 추가
        pivot_df = pivot_df.reset_index()
        # [최적화] apply() → 벡터화 함수 사용
        pivot_df['정렬순서'] = get_campaign_type_vectorized(pivot_df['일반회차 캠페인'])
        
        # 정렬순서로 먼저 정렬하고, 그 다음 캠페인 이름으로 오름차순 정렬
        pivot_df = pivot_df.sort_values(by=['정렬순서', '일반회차 캠페인'], ascending=[True, True])
        
        # 정렬순서 컬럼 제거
        pivot_df = pivot_df.drop(columns=['정렬순서'])
        
        # 인덱스 리셋
        pivot_df = pivot_df.reset_index(drop=True)
        
        # 총합계 행 계산
        total_row = pd.DataFrame(pivot_df.drop(columns=['일반회차 캠페인']).sum(axis=0)).T
        total_row['일반회차 캠페인'] = '총합계'
        
        # 총합계 행의 전환율 계산
        if '주문승인' in total_row.columns and '총합계' in total_row.columns:
            total_row['전환율'] = total_row['주문승인'] / total_row['총합계'] * 100
        
        # 일반회차 캠페인 열을 행 레이블로 변경
        pivot_df = pivot_df.rename(columns={'일반회차 캠페인': '행 레이블'})
        total_row = total_row.rename(columns={'일반회차 캠페인': '행 레이블'})
        
        # 총합계 행을 맨 아래에 추가
        result_df = pd.concat([pivot_df, total_row], ignore_index=True)
        
        # 컬럼 순서 정의
        column_order = CAMPAIGN_SETTINGS["COLUMN_ORDER"]
        
        # 존재하는 컬럼만 선택
        final_columns = ['행 레이블']
        for col in column_order:
            if col in result_df.columns and col != '행 레이블':
                final_columns.append(col)
        
        # 기타 컬럼 추가
        for col in result_df.columns:
            if col not in final_columns:
                final_columns.append(col)
        
        # 컬럼 순서 적용
        result_df = result_df[final_columns]

        return result_df, cleaned_data, total_before_dedup, total_after_dedup

    except Exception as e:
        st.error(f"데이터 그룹화 및 집계 중 오류가 발생했습니다: {str(e)}")
        st.error(f"상세 오류: {str(e.__class__.__name__)}: {str(e)}")
        return None, None, 0, 0

def process_consultant_data(cleaned_data) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    상담사별 신규 DB 분석 함수
    
    Args:
        cleaned_data: 중복 제거된 원본 데이터
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 상담사별 신규 DB 개수 데이터프레임과 오류 메시지
    """
    try:
        # 필요한 컬럼이 있는지 확인
        # 상담사 컬럼 찾기 (상담사, 담당자, 담당 상담사 등 다양한 컬럼명이 있을 수 있음)
        consultant_col = None
        for col in cleaned_data.columns:
            if "상담사" in col or "담당자" in col:
                consultant_col = col
                break
                
        if consultant_col is None:
            return None, "상담사 또는 담당자 컬럼을 찾을 수 없습니다."
        
        if "일반회차 캠페인" not in cleaned_data.columns or "상담DB상태" not in cleaned_data.columns:
            return None, "일반회차 캠페인 또는 상담DB상태 컬럼이 없습니다."
            
        # 상담DB상태가 '신규'인 데이터만 필터링
        new_status_df = cleaned_data[cleaned_data["상담DB상태"] == "신규"].copy()
        
        if new_status_df.empty:
            return None, "상담DB상태가 '신규'인 데이터가 없습니다."
            
        # 캠페인 × 상담사 그룹별 개수 계산
        result_df = pd.DataFrame(new_status_df.groupby(["일반회차 캠페인", consultant_col]).size()).reset_index()
        result_df.columns = ["일반회차 캠페인", "상담사", "신규건수"]

        # [최적화] 정렬 순서 적용 - 벡터화 함수 사용
        result_df["정렬순서"] = get_campaign_type_vectorized(result_df["일반회차 캠페인"])
        result_df = result_df.sort_values(by=["정렬순서", "일반회차 캠페인", "신규건수"],
                                         ascending=[True, True, False])

        # 정렬순서 컬럼 제거
        result_df = result_df.drop(columns=["정렬순서"])

        # 총합계 계산
        campaign_totals = result_df.groupby("일반회차 캠페인")["신규건수"].sum().reset_index()
        campaign_totals.columns = ["일반회차 캠페인", "소계"]

        # 캠페인별 소계를 딕셔너리로 변환 (빠른 조회)
        campaign_total_dict = dict(zip(campaign_totals["일반회차 캠페인"], campaign_totals["소계"]))

        # 캠페인별 소계 추가
        final_result = []

        # 각 캠페인별로 상담사 정보 추가
        for campaign in result_df["일반회차 캠페인"].unique():
            # 캠페인 소계 행 추가
            final_result.append({
                "일반회차 캠페인": campaign,
                "상담사": "",  # 빈 값
                "신규건수": campaign_total_dict[campaign],
                "행타입": "캠페인"
            })

            # [최적화] 해당 캠페인의 상담사별 행 추가 - itertuples() 사용
            consultants = result_df[result_df["일반회차 캠페인"] == campaign]
            for row in consultants.itertuples(index=False):
                final_result.append({
                    "일반회차 캠페인": "",  # 빈 값
                    "상담사": row.상담사,
                    "신규건수": row.신규건수,
                    "행타입": "상담사"
                })
        
        # 결과 DataFrame 생성 (지금까지 모은 결과)
        final_df = pd.DataFrame(final_result)
        
        # 총합계 행 계산
        total_count = result_df["신규건수"].sum()
        total_row = pd.DataFrame([{
            "일반회차 캠페인": "총합계",
            "상담사": "",
            "신규건수": total_count,
            "행타입": "총합계"
        }])
        
        # 총합계 행을 맨 마지막에 추가
        final_df = pd.concat([final_df, total_row], ignore_index=True)
        
        return final_df, None
        
    except Exception as e:
        return None, f"상담사별 분석 중 오류가 발생했습니다: {str(e)}"

def create_excel_file(cleaned_data, results_df, consultant_results=None) -> BytesIO:
    """
    결과를 엑셀 파일로 생성하는 함수
    
    Args:
        cleaned_data: 중복 제거된 원본 데이터
        results_df: 분석 결과 데이터프레임
        consultant_results: 상담사별 분석 결과 데이터프레임
        
    Returns:
        BytesIO: 엑셀 파일이 담긴 BytesIO 객체
    """
    try:
        # 메모리에 엑셀 파일 생성
        excel_buffer = io.BytesIO()
        
        # ExcelWriter 사용해 여러 시트 작성
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            # 시트1: 중복 제거된 원본 데이터
            cleaned_data.to_excel(writer, sheet_name='최종 데이터', index=False)
            
            # 시트2: 분석 결과
            results_df.to_excel(writer, sheet_name='분석 결과', index=False)
            
            # 시트3: 상담사별 분석 결과 (있는 경우)
            if consultant_results is not None:
                consultant_results.to_excel(writer, sheet_name='상담사별 분석', index=False)
            
            # 엑셀 워크북과 워크시트 객체 가져오기
            workbook = writer.book
            
            # 결과 시트 스타일링
            result_sheet = writer.sheets['분석 결과']
            
            # 숫자 형식 설정
            number_format = workbook.add_format({'num_format': '#,##0'})
            percent_format = workbook.add_format({'num_format': '0.0%'})
            
            # 전환율 컬럼 인덱스 찾기
            if '전환율' in results_df.columns:
                percent_col = list(results_df.columns).index('전환율') + 1  # Excel은 1부터 시작
                for row in range(1, len(results_df) + 1):  # 헤더 제외
                    result_sheet.write_number(row, percent_col, results_df['전환율'].iloc[row-1] / 100, percent_format)
        
        # 버퍼 위치를 처음으로 되돌림
        excel_buffer.seek(0)
        return excel_buffer
        
    except Exception as e:
        st.error(f"엑셀 파일 생성 중 오류가 발생했습니다: {str(e)}")
        return None

def format_dataframe_for_display(df) -> pd.DataFrame:
    """
    표시용 데이터프레임을 포맷팅하는 함수
    
    Args:
        df: 원본 데이터프레임
        
    Returns:
        pd.DataFrame: 표시용으로 포맷팅된 데이터프레임
    """
    display_df = df.copy()
    
    # 행 레이블 컬럼명 변경
    if "행 레이블" in display_df.columns:
        display_df = display_df.rename(columns={"행 레이블": "일반회차 캠페인"})

    # [최적화] 전환율 포맷팅 - 벡터화 사용
    if '전환율' in display_df.columns:
        rate = display_df['전환율']
        formatted = pd.Series(['-'] * len(rate), index=rate.index)
        valid_mask = rate.notna()
        formatted[valid_mask] = rate[valid_mask].apply(lambda x: f"{x:.1f}%")
        display_df['전환율'] = formatted

    # [최적화] 숫자 컬럼 포맷팅 - 벡터화 사용
    numeric_columns = display_df.columns.difference(['일반회차 캠페인', '전환율'])
    for col in numeric_columns:
        values = display_df[col]
        # 마스크: NaN이거나 0인 경우 빈 문자열
        is_empty = values.isna() | (values == 0)
        formatted = values.fillna(0).astype(int).astype(str)
        formatted = formatted.where(~is_empty, '')
        display_df[col] = formatted

    return display_df