"""
CRM 데이터 분석기 에러 처리 표준화 예시

이 모듈은 표준화된 에러 처리를 적용한 함수 예시를 제공합니다.
"""

import pandas as pd
import streamlit as st
import logging
from typing import Tuple, Optional, Dict, List, Any, Union

# 표준화된 에러 처리 데코레이터 및 설정 가져오기
from improved_utils import standardized_error_handler
from config import ERROR_MESSAGES, SUCCESS_MESSAGES

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@standardized_error_handler
def process_excel_file(file) -> pd.DataFrame:
    """
    엑셀 파일을 처리하여 데이터프레임으로 변환합니다.
    
    Args:
        file: 업로드된 엑셀 파일 객체
        
    Returns:
        pd.DataFrame: 처리된 데이터프레임
        
    Raises:
        ValueError: 필요한 열이 없는 경우
        Exception: 기타 처리 중 오류가 발생한 경우
    """
    # 엑셀 파일 읽기
    df = pd.read_excel(file, parse_dates=True)
    
    # 빈 열 제거 (Unnamed 열 등)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 필요한 컬럼 확인
    required_columns = ["월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        # 필요한 열이 없는 경우 ValueError 발생
        error_msg = ERROR_MESSAGES["MISSING_COLUMNS_ERROR"].format(columns=', '.join(missing_columns))
        raise ValueError(error_msg)
    
    return df

def display_excel_processing_result(file):
    """
    엑셀 파일 처리 결과를 표시합니다.
    
    Args:
        file: 업로드된 엑셀 파일 객체
    """
    if file is None:
        st.info("엑셀 파일을 업로드하세요.")
        return
    
    # 파일 처리 (표준화된 에러 처리 적용)
    df, error = process_excel_file(file)
    
    if error:
        # 에러 메시지 표시 (표준화된 형식)
        st.error(error)
    else:
        # 성공 메시지 및 결과 표시
        st.success(SUCCESS_MESSAGES["DATA_LOADED"].format(count=len(df)))
        st.dataframe(df.head())

# 복합 에러 처리 예시
@standardized_error_handler
def analyze_campaign_data(files: List) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    다수의 캠페인 관련 엑셀 파일을 처리하고 분석합니다.
    
    Args:
        files: 업로드된 엑셀 파일 목록
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: 분석 결과와 중복 제거된 원본 데이터
        
    Raises:
        ValueError: 필요한 데이터가 없는 경우
        FileNotFoundError: 처리 가능한 파일이 없는 경우
        Exception: 기타 처리 중 오류가 발생한 경우
    """
    if not files:
        raise FileNotFoundError(ERROR_MESSAGES["NO_DATA_ERROR"].format(data_type="파일"))
    
    all_data = []
    
    # 각 파일 처리
    for file in files:
        try:
            # 파일 처리 로직...
            df = pd.read_excel(file, header=2)
            all_data.append(df)
        except Exception as e:
            # 개별 파일 오류는 로깅하되 계속 진행
            logger.warning(ERROR_MESSAGES["CAMPAIGN_PROCESSING_ERROR"].format(
                file_name=file.name, error=str(e)
            ))
    
    # 모든 파일 처리 후 검증
    if not all_data:
        raise ValueError(ERROR_MESSAGES["NO_DATA_ERROR"].format(data_type="처리 가능한 데이터"))
    
    # 데이터 결합
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # 중복 제거된 원본 데이터
    cleaned_data = combined_df.copy()
    
    # 분석 로직...
    # (실제 분석 코드가 여기에 들어갑니다)
    
    # 테스트용 샘플 결과
    result_df = pd.DataFrame({
        '캠페인': ['캠페인A', '캠페인B', '총합계'],
        '총합계': [100, 200, 300],
        '전환율': [10.5, 15.2, 13.1]
    })
    
    return result_df, cleaned_data

def display_campaign_analysis(files):
    """
    캠페인 분석 결과를 표시합니다.
    
    Args:
        files: 업로드된 엑셀 파일 목록
    """
    if not files:
        st.info("캠페인 관련 엑셀 파일을 업로드하세요.")
        return
    
    # 분석 버튼
    if st.button("분석 시작"):
        # 진행 상태 표시
        with st.spinner('파일 분석 중...'):
            # 캠페인 분석 실행 (표준화된 에러 처리 적용)
            result, error = analyze_campaign_data(files)
            
            if error:
                st.error(error)
            else:
                st.success(f"분석 완료! {len(result)}개의 캠페인이 분석되었습니다.")
                st.dataframe(result)

# 메인 UI
def show_error_handling_demo():
    """에러 처리 표준화 데모 UI"""
    st.title("에러 처리 표준화 데모")
    
    tab1, tab2 = st.tabs(["기본 에러 처리", "복합 에러 처리"])
    
    with tab1:
        st.subheader("단일 파일 처리")
        file = st.file_uploader("엑셀 파일을 업로드하세요", type=['xlsx', 'xls'], key="single_file")
        display_excel_processing_result(file)
    
    with tab2:
        st.subheader("다중 파일 분석")
        files = st.file_uploader(
            "캠페인 엑셀 파일을 업로드하세요 (다수 파일 선택 가능)",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            key="multiple_files"
        )
        
        if files:
            st.write(f"총 {len(files)}개의 파일이 업로드되었습니다:")
            st.write(", ".join([file.name for file in files]))
        
        display_campaign_analysis(files)

if __name__ == "__main__":
    show_error_handling_demo()