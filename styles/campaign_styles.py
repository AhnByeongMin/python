"""
캠페인/정규분배 현황 탭의 CSS 스타일 정의

이 모듈은 캠페인/정규분배 현황 탭에서 사용되는 CSS 스타일과 스타일 관련 함수를 포함합니다.
"""

import streamlit as st

# 캠페인 테이블 스타일
CAMPAIGN_TABLE_STYLE = """
<style>
    .dark-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    
    .stDataFrame {
        width: 100%;
    }
    
    .stDownloadButton {
        width: 100%;
        margin-top: 20px;
    }

    /* 상담사별 현황 스타일 */
    .consultant-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .consultant-header h3 {
        margin: 0;
    }
    
    .consultant-header .badge {
        background-color: #4472C4;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
    }
</style>
"""

def apply_styles():
    """
    캠페인/정규분배 현황 탭에 필요한 스타일을 적용하는 함수
    """
    st.markdown(CAMPAIGN_TABLE_STYLE, unsafe_allow_html=True)