"""
상담원 실적 현황 탭의 CSS 스타일 정의
"""

# 상담원 실적 현황 테이블 스타일
CONSULTANT_TABLE_STYLE = """
<style>
    .table-container {
        width: 50%;  /* 데스크톱에서는 50% 너비로 제한 */
        margin: 0 auto;  /* 중앙 정렬 */
        overflow-x: auto;  /* 모바일에서 가로 스크롤 가능하게 */
    }
    
    /* 모바일 환경에서는 컨테이너를 100% 너비로 확장 */
    @media (max-width: 768px) {
        .table-container {
            width: 100%;
        }
    }
    
    .compact-table {
        border-collapse: collapse;
        font-size: 0.7em;  /* 더 작은 폰트 크기 */
        width: 100%;  /* 컨테이너 내에서 100% */
        table-layout: fixed;
        margin: 0 auto;
    }
    .compact-table thead tr {
        background-color: #262730;
        color: white;
        text-align: center;
        font-weight: bold;
    }
    .compact-table th, .compact-table td {
        padding: 2px 3px;  /* 패딩 최소화 */
        text-align: center;
        border: 1px solid #444;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .compact-table tbody tr {
        background-color: #1E1E1E;
        color: white;
    }
    .compact-table tbody tr:nth-of-type(even) {
        background-color: #2D2D2D;
    }
    .compact-table tbody tr.summary-row {
        background-color: #2E4053;
        color: white;
        font-weight: bold;
    }
    /* 컬럼 너비 최적화 */
    .compact-table th:nth-child(1), .compact-table td:nth-child(1) { width: 3%; }  /* 순위 */
    .compact-table th:nth-child(2), .compact-table td:nth-child(2) { width: 7%; }  /* 상담사 */
    .compact-table th:nth-child(3), .compact-table td:nth-child(3),
    .compact-table th:nth-child(4), .compact-table td:nth-child(4),
    .compact-table th:nth-child(5), .compact-table td:nth-child(5),
    .compact-table th:nth-child(6), .compact-table td:nth-child(6),
    .compact-table th:nth-child(7), .compact-table td:nth-child(7) { width: 4%; }  /* 제품 카테고리 */
    .compact-table th:nth-child(8), .compact-table td:nth-child(8) { width: 3%; }  /* 건수 */
    .compact-table th:nth-child(9), .compact-table td:nth-child(9) { width: 5%; }  /* 콜건수 */
    .compact-table th:nth-child(10), .compact-table td:nth-child(10) { width: 6%; }  /* 콜타임 */
    
    /* 간소화된 헤더 */
    .compact-table th:nth-child(3)::after { content: "안마"; }
    .compact-table th:nth-child(3) span { display: none; }
    .compact-table th:nth-child(4)::after { content: "라클"; }
    .compact-table th:nth-child(4) span { display: none; }
    .compact-table th:nth-child(5)::after { content: "정수기"; }
    .compact-table th:nth-child(5) span { display: none; }
    .compact-table th:nth-child(6)::after { content: "더케어"; }
    .compact-table th:nth-child(6) span { display: none; }
    .compact-table th:nth-child(7)::after { content: "멤버쉽"; }
    .compact-table th:nth-child(7) span { display: none; }
</style>
"""

# 상담원 실적 현황 샘플 테이블 스타일
CONSULTANT_SAMPLE_TABLE_STYLE = """
<style>
    .table-container {
        width: 50%;  /* 데스크톱에서는 50% 너비로 제한 */
        margin: 0 auto;  /* 중앙 정렬 */
        overflow-x: auto;  /* 모바일에서 가로 스크롤 가능하게 */
    }
    
    /* 모바일 환경에서는 컨테이너를 100% 너비로 확장 */
    @media (max-width: 768px) {
        .table-container {
            width: 100%;
        }
    }
    
    /* Streamlit의 테마 변수를 활용한 동적 스타일링 */
    .compact-table {
        border-collapse: collapse;
        font-size: 0.7em;
        width: 100%;
        table-layout: fixed;
        margin: 0 auto;
    }
    
    /* 다크모드/라이트모드 감지 */
    @media (prefers-color-scheme: dark) {
        .compact-table thead tr {
            background-color: #262730;
            color: white;
        }
        .compact-table tbody tr {
            background-color: #1E1E1E;
            color: white;
        }
        .compact-table tbody tr:nth-of-type(even) {
            background-color: #2D2D2D;
        }
        .compact-table tbody tr.summary-row {
            background-color: #2E4053;
            color: white;
        }
        .compact-table th, .compact-table td {
            border: 1px solid #444;
        }
    }
    
    @media (prefers-color-scheme: light) {
        .compact-table thead tr {
            background-color: #f1f1f1;
            color: #333;
        }
        .compact-table tbody tr {
            background-color: #ffffff;
            color: #333;
        }
        .compact-table tbody tr:nth-of-type(even) {
            background-color: #f9f9f9;
        }
        .compact-table tbody tr.summary-row {
            background-color: #e6f0ff;
            color: #333;
        }
        .compact-table th, .compact-table td {
            border: 1px solid #ddd;
        }
    }
    .compact-table th, .compact-table td {
        padding: 2px 3px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .compact-table thead tr {
        text-align: center;
        font-weight: bold;
    }
    
    .compact-table tbody tr.summary-row {
        font-weight: bold;
    }
    /* 컬럼 너비 최적화 */
    .compact-table th:nth-child(1), .compact-table td:nth-child(1) { width: 3%; }
    .compact-table th:nth-child(2), .compact-table td:nth-child(2) { width: 7%; }
    .compact-table th:nth-child(3), .compact-table td:nth-child(3),
    .compact-table th:nth-child(4), .compact-table td:nth-child(4),
    .compact-table th:nth-child(5), .compact-table td:nth-child(5),
    .compact-table th:nth-child(6), .compact-table td:nth-child(6),
    .compact-table th:nth-child(7), .compact-table td:nth-child(7) { width: 4%; }
    .compact-table th:nth-child(8), .compact-table td:nth-child(8) { width: 3%; }
    .compact-table th:nth-child(9), .compact-table td:nth-child(9) { width: 5%; }
    .compact-table th:nth-child(10), .compact-table td:nth-child(10) { width: 6%; }
    
    /* 간소화된 헤더 */
    .compact-table th:nth-child(3)::after { content: "안"; }
    .compact-table th:nth-child(3) span { display: none; }
    .compact-table th:nth-child(4)::after { content: "라"; }
    .compact-table th:nth-child(4) span { display: none; }
    .compact-table th:nth-child(5)::after { content: "정"; }
    .compact-table th:nth-child(5) span { display: none; }
    .compact-table th:nth-child(6)::after { content: "케어"; }
    .compact-table th:nth-child(6) span { display: none; }
    .compact-table th:nth-child(7)::after { content: "멤버"; }
    .compact-table th:nth-child(7) span { display: none; }
</style>
"""

# 다운로드 버튼 스타일
DOWNLOAD_BUTTON_STYLE = """
<style>
.download-button {
    display: inline-block;
    padding: 8px 16px;
    background-color: #4472C4;
    color: white;
    text-align: center;
    border-radius: 4px;
    font-weight: bold;
    text-decoration: none;
    margin-top: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    transition: all 0.2s ease;
    font-size: 0.9em;
}
.download-button:hover {
    background-color: #305496;
    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
}
</style>
"""

# 날짜 표시 스타일
DATE_DISPLAY_STYLE = """
<h4 style="text-align: center; margin-bottom: 15px; letter-spacing: 1px; word-spacing: 5px;">{date_display}</h4>
"""

# 상담원 실적 현황 설명 스타일
CONSULTANT_DESCRIPTION = """
<p>이 도구는 상담원의 실적 현황을 분석하고 시각화합니다. 상담주문계약내역과 콜타임 파일을 업로드하여 상담원별 실적을 확인할 수 있습니다.</p>
"""

# 사용 가이드 마크다운
USAGE_GUIDE_MARKDOWN = """
### 사용 가이드
1. 상담주문계약내역 및 콜타임 엑셀 파일을 업로드하세요.
2. 파일이 업로드되면 자동으로 분석이 진행됩니다.
3. 조직별로 상담원 실적을 확인하고 엑셀로 다운로드할 수 있습니다.
"""