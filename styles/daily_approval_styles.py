"""
일일 승인 현황 탭의 CSS 스타일 정의
"""

# 일일 승인 현황 탭 전체 스타일
DAILY_APPROVAL_TAB_STYLE = """
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
        width: auto;
        padding: 8px 20px;
        background-color: #1976d2;
        color: white !important;
        text-align: center;
        border-radius: 4px;
        font-weight: 500;
        text-decoration: none;
        margin-top: 20px;
        transition: all 0.2s ease;
        margin: 0 auto;
    }
    .download-button:hover {
        background-color: #1565c0;
        color: white !important;
        text-decoration: none;
    }
    .download-button-container {
        text-align: center;
        width: 100%;
        margin-top: 20px;
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
    
    /* 상태 표시 컨테이너 */
    .status-container {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    
    /* 상태 칩 스타일 */
    .status-chip {
        padding: 5px 10px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
        margin-right: 12px;
        display: inline-block;
    }
    
    .status-chip.success {
        background-color: #4caf50;
        color: white;
    }
    
    .timestamp {
        color: #666;
        font-size: 14px;
    }
</style>
"""

# 상담사 카드 스타일
DAILY_APPROVAL_CARD_STYLE = """
<style>
    /* 카드 컨테이너 */
    .card-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 15px;
        margin-top: 20px;
    }
    
    /* 카드 스타일 */
    .consultant-card {
        width: 250px;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        background: #fff;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .consultant-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* 카드 헤더 */
    .card-header {
        margin-bottom: 15px;
        position: relative;
    }
    
    .consultant-name {
        font-size: 16px;
        font-weight: bold;
        color: #333;
        margin: 0;
    }
    
    .team-badge {
        position: absolute;
        top: 0;
        right: 0;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .team-badge.crm {
        background: #e3f2fd;
        color: #1976d2;
    }
    
    .team-badge.online {
        background: #fff8e1;
        color: #ff8f00;
    }
    
    /* 카드 내용 */
    .card-content {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    
    .data-row {
        border-bottom: 1px dashed #eee;
        padding-bottom: 5px;
    }
    
    .data-label {
        font-size: 12px;
        color: #666;
    }
    
    .data-value {
        font-size: 14px;
        font-weight: 500;
        color: #333;
        text-align: right;
    }
    
    /* 프로그레스 바 */
    .progress-bar {
        width: 100%;
        height: 8px;
        background: #f5f5f5;
        border-radius: 4px;
        margin-top: 15px;
        overflow: hidden;
    }
    
    .progress-item {
        height: 100%;
        float: left;
    }
    
    .progress-anma {
        background: #1976d2;
    }
    
    .progress-lacloud {
        background: #ff8f00;
    }
    
    .progress-water {
        background: #43a047;
    }
    
    /* 푸터 */
    .card-footer {
        margin-top: 10px;
        text-align: center;
        font-size: 12px;
        color: #999;
    }
</style>
"""

# Material 디자인 다운로드 버튼 스타일
DOWNLOAD_BUTTON_STYLE = """
<style>
.download-button-container {
    text-align: center;
    margin: 30px 0;
}

.download-button {
    background-color: #1976d2;
    color: white !important;
    padding: 10px 20px;
    border-radius: 4px;
    text-decoration: none;
    font-weight: 500;
    font-size: 14px;
    display: inline-block;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
}

.download-button:hover {
    background-color: #1565c0;
    box-shadow: 0 3px 8px rgba(0,0,0,0.3);
    transform: translateY(-2px);
}

.download-button:active {
    transform: translateY(0);
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
</style>
"""

# 날짜 표시 스타일
DATE_DISPLAY_STYLE = """
<div style="text-align: center; margin: 20px 0; padding: 10px; background-color: #f5f5f5; border-radius: 4px; font-weight: 500; color: #333;">
    {date_display}
</div>
"""

# 일일 승인 현황 설명 스타일
DAILY_APPROVAL_DESCRIPTION = """
<p style="margin-bottom: 20px;">
    이 탭에서는 상담원별 일일 및 누적 승인 현황을 분석합니다. 안마의자, 라클라우드, 정수기 별로 건수와 매출액을 확인할 수 있으며, 상담원 콜타임 정보도 함께 표시됩니다.
</p>
"""

# 사용 가이드 마크다운
USAGE_GUIDE_MARKDOWN = """
<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
    <h3 style="color: #1976d2; margin-top: 0;">사용 가이드</h3>
    <ol>
        <li><strong>파일 업로드:</strong> 승인 파일과 콜타임 파일(선택사항)을 업로드합니다.</li>
        <li><strong>분석 시작:</strong> 분석 시작 버튼을 클릭하여 데이터를 분석합니다.</li>
        <li><strong>결과 확인:</strong> 일일/누적 승인 현황 테이블과 상담사별 카드를 확인합니다.</li>
        <li><strong>시각화:</strong> 데이터 시각화 섹션에서 그래프로 결과를 확인합니다.</li>
        <li><strong>엑셀 다운로드:</strong> 분석 결과를 엑셀 파일로 다운로드할 수 있습니다.</li>
    </ol>
    <h4 style="color: #1976d2;">참고사항</h4>
    <ul>
        <li>상담사 관리 섹션에서 상담사 목록을 추가/삭제할 수 있습니다.</li>
        <li>상담사 카드 보기/숨기기 버튼을 통해 카드 UI를 표시하거나 숨길 수 있습니다.</li>
        <li>원본 데이터는 엑셀 파일의 두 번째 시트에 포함됩니다.</li>
    </ul>
</div>
"""