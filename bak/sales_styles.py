"""
매출 데이터 분석 탭의 CSS 스타일 정의
"""

# 매출 분석 탭 전체 스타일
SALES_TAB_STYLE = """
<style>
    /* 카드 스타일 */
    .card {
        background-color: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
    }
    
    /* 데이터 그리드 스타일 */
    .data-grid {
        margin-top: 1rem;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* 다운로드 버튼 스타일 */
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
    
    /* 복사 버튼 스타일 */
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
    
    /* 필터 컨테이너 스타일 */
    .filter-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .filter-item {
        flex: 1;
        min-width: 200px;
    }
    
    /* 메시지 스타일 */
    .success-message {
        color: green;
        font-weight: bold;
    }
    .error-message {
        color: red;
        font-weight: bold;
    }
    
    /* 스크롤 영역 스타일 */
    .scroll-area {
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #eee;
        border-radius: 4px;
        padding: 10px;
    }
    
    /* 체크박스 그리드 스타일 */
    .checkbox-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
    }
</style>
"""

# 클립보드 복사 성공 메시지 스타일
COPY_SUCCESS_STYLE = """
<div id="copy-success" style="display:none; color:green; margin-top:5px;">
    클립보드에 복사되었습니다!
</div>
"""

# 클립보드 복사 버튼 HTML
COPY_BUTTON_HTML = """
<button onclick="copyToClipboard()" class="copy-button">
    결과 클립보드에 복사
</button>
"""

# 다운로드 가이드 스타일
DOWNLOAD_GUIDE_MARKDOWN = """
#### 다운로드 파일 내용:
1. **승인건수** 시트: 필터링된 데이터와 매출금액(VAT제외) 컬럼이 포함된 원본 데이터
2. **분석데이터** 시트: 대분류별 승인건수와 매출금액(VAT제외) 요약 데이터
"""

# 사용 가이드 마크다운
USAGE_GUIDE_MARKDOWN = """
### 사용 가이드
1. 엑셀 파일을 업로드합니다.
2. 원본 데이터를 확인합니다.
3. 필요한 경우 '데이터 필터링' 섹션을 펼쳐 필터를 적용합니다.
4. 분석 결과 섹션에서 품목별 집계 결과를 확인합니다.
5. 시각화 탭에서 그래프로 분석 결과를 확인합니다.
6. 다운로드 탭에서 결과를 엑셀 파일로 내려받을 수 있습니다.

### 필수 컬럼
- 월 렌탈 금액
- 약정 기간 값
- 총 패키지 할인 회차
- 판매 금액
- 선납 렌탈 금액
- 대분류 또는 품목명
"""