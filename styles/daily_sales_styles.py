"""
일일 매출 현황 탭의 CSS 스타일 정의 - 다크모드 및 가로 레이아웃
"""

# 일일 매출 현황 탭 전체 스타일 - 다크모드 적용
DAILY_SALES_TAB_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    /* 전체 페이지 스타일 - 다크모드 */
    .main .block-container {
        font-family: 'Roboto', sans-serif;
        max-width: 1400px;
        padding: 2rem 1rem;
        color: #e0e0e0;
    }
    
    /* 머티리얼 카드 - 다크모드 */
    .material-card {
        background-color: #1e1e1e;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin-bottom: 24px;
        transition: box-shadow 0.3s ease;
        border: 1px solid #333333;
    }
    
    .material-card:hover {
        box-shadow: 0 6px 10px rgba(0, 0, 0, 0.4);
    }
    
    /* 카드 헤더 - 다크모드 */
    .card-header {
        border-bottom: 1px solid #333333;
        padding: 12px 16px;
        background-color: #252525;
    }
    
    .card-header h3 {
        margin: 0;
        color: #e0e0e0;
        font-size: 16px;
        font-weight: 500;
    }
    
    /* 특정 카드 유형에 대한 스타일 */
    .upload-card {
        border-left: 4px solid #444444;
    }
    
    .result-card {
        border-left: 4px solid #444444;
    }
    
    .info-card {
        border-left: 4px solid #444444;
    }
    
    .download-card {
        border-left: 4px solid #444444;
    }
    
    /* 상태 표시 컨테이너 */
    .status-container {
        display: flex;
        align-items: center;
        margin-bottom: 24px;
        font-family: 'Roboto', sans-serif;
    }
    
    /* 상태 칩 스타일 */
    .status-chip {
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
        margin-right: 12px;
        display: inline-block;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-chip.success {
        background-color: #454545;
        color: #e0e0e0;
    }
    
    .timestamp {
        color: #9e9e9e;
        font-size: 14px;
    }
    
    /* 결과 행 스타일 */
    .results-row {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 24px;
    }
    
    /* 버튼 컨테이너 */
    .button-container {
        margin: 24px 0;
        display: flex;
        justify-content: center;
    }
    
    /* 머티리얼 버튼 스타일 */
    .material-button {
        background-color: #454545;
        color: white !important;
        padding: 10px 24px;
        font-family: 'Roboto', sans-serif;
        font-size: 14px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-radius: 4px;
        border: none;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        transition: background-color 0.3s, box-shadow 0.3s;
    }
    
    .material-button:hover {
        background-color: #555555;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
        text-decoration: none;
    }
    
    /* 커스텀 폰트 설정 */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        color: #e0e0e0;
    }
    
    p {
        font-family: 'Roboto', sans-serif;
        color: #b0b0b0;
        line-height: 1.6;
    }
    
    /* 탭 스타일 - 스트림릿 기본 오버라이드 */
    .stTabs [data-baseweb="tab-list"] {
        margin-bottom: 16px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Roboto', sans-serif;
        font-size: 14px;
        font-weight: 500;
    }
    
    /* 리스트 스타일 */
    ol {
        padding-left: 1.5em;
    }
    
    ol li {
        margin-bottom: 8px;
        padding-left: 8px;
        line-height: 1.6;
    }
    
    /* Streamlit의 인포 메시지 스타일 조정 */
    .stAlert {
        background-color: #1e1e1e !important;
        color: #b0b0b0 !important;
        border-color: #333333 !important;
    }

    
</style>
"""

# 다크 테이블 스타일 - 컴팩트 버전 (수정됨 - 파란색 제거 및 테이블 구조 간소화)
DARK_TABLE_STYLE = """
<style>
    /* 테이블 반응형 컨테이너 */
    .table-responsive {
        overflow-x: auto;
        margin: 8px;
        background-color: #1e1e1e;
        border-radius: 4px;
        padding-bottom: 8px;
    }

    /* 다크 테이블 - 컴팩트 버전 */
    .dark-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Roboto', sans-serif;
        font-size: 12px;
        color: #e0e0e0;
        border: none;
        box-shadow: none;
        text-align: center;
    }

    /* 구분 열 스타일 */
    .dark-table th:first-child,
    .dark-table td:first-child {
        background-color: #252525;
        font-weight: 500;
        text-align: left;
        padding-left: 12px;
        position: sticky;
        left: 0;
        z-index: 1;
        min-width: 90px;
        max-width: 120px;
    }

    /* 헤더 기본 스타일 */
    .dark-table th {
        background-color: #333333;
        color: #ffffff;
        font-weight: 500;
        text-align: center;
        padding: 6px 4px;
        border: 1px solid #444444;
        font-size: 11px;
    }

    /* 데이터 셀 스타일 */
    .dark-table td {
        border: 1px solid #333333;
        padding: 6px 8px;
        text-align: center;
        font-size: 11px;
        color: #e0e0e0;
    }

    /* 매출액 셀 */
    .dark-table td.amount {
        text-align: right;
        padding-right: 12px;
    }

    /* 합계 행 스타일 */
    .dark-table tbody tr:last-child td {
        background-color: #444444;
        color: white;
        font-weight: 500;
    }

    /* 짝수 행 배경 */
    .dark-table tbody tr:nth-child(even):not(:last-child) {
        background-color: #252525;
    }

    /* 홀수 행 배경 */
    .dark-table tbody tr:nth-child(odd):not(:last-child) {
        background-color: #1e1e1e;
    }

    /* 행 호버시 하이라이트 */
    .dark-table tbody tr:hover:not(:last-child) {
        background-color: #2a2a2a;
    }
    
    /* 컬럼 너비 조정 */
    .dark-table th, .dark-table td {
        min-width: 60px;
    }
</style>
"""

# Material 디자인 다운로드 버튼 스타일 - 다크모드 (파란색 제거)
DOWNLOAD_BUTTON_STYLE = """
<style>
.download-button-container {
    display: flex;
    justify-content: center;
    margin: 24px 0;
}

.material-button {
    background-color: #454545;
    color: white !important;
    padding: 10px 24px;
    font-family: 'Roboto', sans-serif;
    font-size: 14px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-radius: 4px;
    border: none;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    transition: background-color 0.3s, box-shadow 0.3s;
}

.material-button:hover {
    background-color: #555555;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
    text-decoration: none;
}

.material-button:visited {
    color: white !important;
    text-decoration: none;
}
</style>
"""

# 사용 가이드 마크다운 - 다크모드에 맞게 스타일링
USAGE_GUIDE_MARKDOWN = """
<div style="font-family: 'Roboto', sans-serif; color: #b0b0b0; line-height: 1.6;">
<h3 style="color: #e0e0e0; font-weight: 500; margin-top: 24px;">사용 가이드</h3>
<ol style="padding-left: 1.5em;">
<li>승인매출 엑셀 파일을 업로드합니다.</li>
<li>선택적으로 설치매출 엑셀 파일도 업로드할 수 있습니다.</li>
<li>'분석 시작' 버튼을 클릭하여 분석을 시작합니다.</li>
<li>분석 결과는 세 부분으로 나란히 표시됩니다:
  <ul style="margin-top: 8px;">
    <li>누적승인실적: 전체 기간의 승인 데이터 분석</li>
    <li>누적설치실적: 전체 기간의 설치 데이터 분석 (설치매출 파일이 업로드된 경우)</li>
    <li>일자별 승인실적: 가장 최근 날짜의 승인 데이터 분석</li>
  </ul>
</li>
<li>각 분석 결과는 다음과 같이 분류됩니다:
  <ul style="margin-top: 8px;">
    <li>총승인: 모든 판매 인입 경로 데이터 (온라인 제외)</li>
    <li>본사: CRM 포함된 판매 인입 경로 데이터</li>
    <li>연계: CRM 제외된 판매 인입 경로 데이터</li>
    <li>온라인: CB- 시작하는 캠페인 데이터</li>
  </ul>
</li>
<li>엑셀 다운로드 버튼을 통해 분석 결과를 엑셀 파일로 저장할 수 있습니다.</li>
</ol>

<h3 style="color: #e0e0e0; font-weight: 500; margin-top: 24px;">필수 컬럼</h3>
<ul style="padding-left: 1.5em; margin-top: 8px;">
<li>주문 일자</li>
<li>판매인입경로</li>
<li>일반회차 캠페인</li>
<li>대분류</li>
<li>월 렌탈 금액</li>
<li>약정 기간 값</li>
<li>총 패키지 할인 회차</li>
<li>판매 금액</li>
<li>선납 렌탈 금액</li>
</ul>
</div>
"""

# 요약 텍스트 박스 스타일
SUMMARY_BOX_STYLE = """
<style>
    /* 요약 텍스트 박스 스타일 */
    .summary-textbox {
        margin-top: 20px;
        border: 1px solid #333333;
        border-radius: 5px;
        padding: 15px;
        background-color: #1e1e1e;
        width: 60%;  /* 90%에서 60%로 변경 */
        max-width: 500px; /* 최대 너비 추가 */
        margin-left: auto;
        margin-right: auto;
        font-family: 'Roboto', sans-serif;
        font-size: 0.8em;
        line-height: 1.5;
        color: #e0e0e0;
    }

    .summary-textbox-title {
        font-weight: 700;
        font-size: 1.1em;
        margin-bottom: 10px;
        color: #e0e0e0;
    }

    .summary-textbox-goal {
        margin-bottom: 5px;
        font-weight: 600;
        color: #e0e0e0;
    }

    .summary-textbox-achievement {
        margin-bottom: 15px;
        font-weight: 600;
        color: #e0e0e0;
    }

    .summary-textbox-team {
        margin-bottom: 5px;
        font-weight: 600;
        color: #e0e0e0;
    }

    .summary-textbox-product {
        margin-top: 10px;
        font-weight: 600;
        color: #e0e0e0;
    }

    .summary-textbox-total {
        margin-top: 15px;
        font-weight: 700;
        color: #e0e0e0;
        font-size: 1.1em;
    }
이렇게 구현하면:

"목표 설정" expander를 통해 직접 목표와 연계 목표를 쉽게 입력할 수 있습니다.
입력된 목표 금액은 세션 상태로 저장되어 페이지를 새로고침해도 유지됩니다.
누적 승인 실적 데이터에서 직접/연계 매출액을 집계합니다.
목표 달성률을 계산하여 표시합니다.
매출액은 억 단위로 소수점 첫째자리까지 표시됩니다.
이렇게 하면 요청하신 형식대로 "목표 매출"과 "누적 달성" 정보가 요약 텍스트 박스에 표시됩니다.


</style>
"""

# 이전 스타일들 (호환성을 위해 유지)
CUSTOM_TABLE_STYLE = DARK_TABLE_STYLE
REFINED_TABLE_STYLE = DARK_TABLE_STYLE
MATERIAL_TABLE_STYLE = DARK_TABLE_STYLE