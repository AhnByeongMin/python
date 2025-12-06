"""
CRM 데이터 분석기 메인 애플리케이션 [최적화 버전]

이 파일은 Streamlit 애플리케이션의 진입점으로,
다양한 데이터 분석 도구를 탭으로 구성하여 표시합니다.

최적화 적용 사항:
- 벡터화 연산으로 iterrows() 제거
- apply(lambda) → np.select() 변환
- 중복 컬럼 검사 O(n²) → O(n) 최적화
- pandas crosstab/pivot_table 활용
"""

# 필요한 라이브러리 임포트
import streamlit as st
import time

# Streamlit 성능 최적화 설정
# 파일 업로드 시 전체 리렌더링 방지
if 'initialized' not in st.session_state:
    st.session_state.initialized = True

# 탭별 모듈 임포트 - UI 모듈을 직접 호출하도록 변경
from ui import sales_ui
from ui import consultant_ui
from ui import campaign_ui
from ui import daily_sales_ui
from ui import promotion_ui  # 새로운 상담사 프로모션 UI 모듈 추가
from ui import target_settings_ui  # CRM 목표 설정 UI 모듈 추가
from ui import affiliate_check_ui  # 연계실적 체크 UI 모듈 추가

# 페이지 설정
st.set_page_config(
    page_title="CRM팀 데이터 분석기 [최적화]",
    page_icon="🚀",  # 로켓 이모지로 최적화 버전 표시
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
        content: '🚀 CRM팀 데이터 분석기 [최적화 버전]';
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
    
    /* 다크 카드 기본 스타일 */
    .dark-card {
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
    }
    
    /* 라이트 모드(기본) 스타일 */
    .dark-card {
        background-color: #f8f9fa;
        color: #000;
    }
    
    /* 다크 모드 스타일 */
    .stApp[data-theme="dark"] .dark-card,
    html[data-theme="dark"] .dark-card {
        background-color: #343a40;
        color: #fff;
    }
</style>
""", unsafe_allow_html=True)

# 최상위 탭 생성 (연계실적체크 탭 추가)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 예약 체험 신규 현황",
    "👥 상담원 실적 현황",
    "📢 캠페인/정규분배 현황",
    "📈 일일 매출 현황",
    "🔍 연계실적체크",  # 일일 매출 뒤에 추가
    "🏆 상담사 프로모션 진행현황",
    "🎯 CRM 목표 설정"
])

# 탭1: 매출 데이터 분석 도구
with tab1:
    sales_ui.show()

# 탭2: 상담원 실적 현황
with tab2:
    consultant_ui.show()

# 탭3: 캠페인/정규분배 현황
with tab3:
    campaign_ui.show()

# 탭4: 일일 매출 현황
with tab4:
    daily_sales_ui.show()

# 탭5: 연계실적체크 (새로 추가)
with tab5:
    affiliate_check_ui.show()

# 탭6: 상담사 프로모션 진행현황
with tab6:
    promotion_ui.show()

# 탭7: CRM 목표 설정
with tab7:
    target_settings_ui.show()

# 페이지 하단 정보
st.markdown("""
<div style="text-align: center; margin-top: 30px; padding: 10px; color: #666;">
    © 2025 CRM팀 데이터 분석 도구 Made in BM | 버전 3.2.0-optimized 🚀
</div>
""", unsafe_allow_html=True)