# 필요한 라이브러리 임포트
import streamlit as st

# 탭별 모듈 임포트
import sales_analysis
import consultant_performance
import campaign_analysis

# 페이지 설정
st.set_page_config(
    page_title="CRM팀 데이터 분석기", 
    page_icon="📊",  # 차트 이모지 사용
    layout="wide"
)

# Streamlit 헤더 영역 커스터마이징 및 Material UI 스타일 적용
st.markdown("""
<style>
    /* Streamlit 기본 헤더의 제목 변경 */
    header [data-testid="stHeader"] {
        background-color: #1976d2 !important;
    }
    
    /* Streamlit 상단 Hamburger 메뉴 너머 공백 영역에 텍스트 추가 */
    header [data-testid="stHeader"]::before {
        content: 'CRM팀 데이터 분석기';
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
        margin-left: 50px; /* 햄버거 메뉴 다음에 위치하도록 여백 조정 */
        display: inline-block;
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
    }
    
    /* Material UI 스타일 */
    .main {
        background-color: #fafafa;
        font-family: 'Roboto', sans-serif;
    }
    .stButton button {
        background-color: #1976d2;
        color: white;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .stButton button:hover {
        background-color: #1565c0;
    }
    h1, h2, h3 {
        color: #1976d2;
        font-weight: 400;
    }
    .stTextInput input, .stSelectbox, .stMultiselect, .stNumberInput input {
        border-radius: 4px;
        border: 1px solid #ddd;
        padding: 0.5rem;
    }
    .card {
        background-color: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
    }
    .data-grid {
        margin-top: 1rem;
        border-radius: 8px;
        overflow: hidden;
    }
    .download-button {
        display: inline-block;
        background-color: #1976d2;
        color: white;
        padding: 0.5rem 1rem;
        text-decoration: none;
        border-radius: 4px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .download-button:hover {
        background-color: #1565c0;
    }
    .copy-button {
        background-color: #1976d2;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 10px;
    }
    .copy-button:hover {
        background-color: #1565c0;
    }
    .filter-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .filter-item {
        flex: 1;
        min-width: 200px;
    }
    .success-message {
        color: green;
        font-weight: bold;
    }
    .error-message {
        color: red;
        font-weight: bold;
    }
    .scroll-area {
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #eee;
        border-radius: 4px;
        padding: 10px;
    }
    .checkbox-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
    }
    /* 탭 스타일 */
    .main-tabs {
        margin-bottom: 20px;
    }
    .dark-card {
        background-color: dark;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 최상위 탭 생성
tab1, tab2, tab3 = st.tabs(["📊 매출 데이터 분석 도구", "👥 상담원 실적 현황", "📢 캠페인/정규분배 현황"])

# 탭1: 매출 데이터 분석 도구
with tab1:
    sales_analysis.show()

# 탭2: 상담원 실적 현황
with tab2:
    consultant_performance.show()

# 탭3: 캠페인/정규분배 현황
with tab3:
    campaign_analysis.show()

# 페이지 하단 정보
st.markdown("""
<div style="text-align: center; margin-top: 30px; padding: 10px; color: #666;">
    © 2025 CRM팀 데이터 분석 도구 Made in BM | 버전 3.0.0
</div>
""", unsafe_allow_html=True)