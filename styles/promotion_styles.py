"""
상담사 프로모션 현황 탭의 CSS 스타일 정의
"""

# 메인 스타일
PROMOTION_TAB_STYLE = """
<style>
    /* 카드 스타일 */
    .promotion-card {
        background-color: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
        border-left: 4px solid #4CAF50;
    }
    
    /* 설정 카드 스타일 */
    .settings-card {
        background-color: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
        border-left: 4px solid #2196F3;
    }
    
    /* 결과 카드 스타일 */
    .results-card {
        background-color: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
        border-left: 4px solid #FF9800;
    }
    
    /* 테이블 스타일 */
    .promotion-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 14px;
        margin-top: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    }
    
    .promotion-table th {
        background-color: #4472C4;
        color: white;
        text-align: center;
        padding: 8px;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .promotion-table td {
        padding: 8px;
        text-align: center;
        border-bottom: 1px solid #ddd;
    }
    
    .promotion-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    
    .promotion-table tr:hover {
        background-color: #ddd;
    }
    
    /* 포상 Y 스타일 */
    .reward-yes {
        background-color: #DFF2BF;
        color: #4F8A10;
        font-weight: bold;
    }
    
    /* 포상 N 스타일 */
    .reward-no {
        background-color: #FEEFB3;
        color: #9F6000;
    }
    
    /* 설정 섹션 스타일 */
    .settings-section {
        margin-bottom: 20px;
        border-bottom: 1px solid #eee;
        padding-bottom: 15px;
    }
    
    .settings-section h4 {
        font-size: 16px;
        color: #305496;
        margin-bottom: 10px;
    }
    
    /* 버튼 스타일 */
    .apply-button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 8px 16px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
    }
    
    .download-button {
        background-color: #2196F3;
        color: white;
        border: none;
        padding: 8px 16px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
    }
    
    /* 프로그레스 바 스타일 */
    .progress-container {
        width: 100%;
        background-color: #f1f1f1;
        border-radius: 4px;
        margin-top: 10px;
        margin-bottom: 20px;
        position: relative;
    }
    
    .progress-bar {
        height: 20px;
        border-radius: 4px;
        background-color: #4CAF50;
        text-align: center;
        line-height: 20px;
        color: white;
        transition: width 0.3s ease;
    }
    
    .progress-label {
        position: absolute;
        width: 100%;
        text-align: center;
        line-height: 20px;
        color: white;
        font-weight: bold;
        text-shadow: 1px 1px 1px rgba(0,0,0,0.3);
    }
</style>
"""

# 테이블 포맷 스타일
FORMAT_REWARD_SCRIPT = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    // 포상 획득 여부 Y/N에 따라 스타일 적용
    var table = document.querySelector('.promotion-table');
    if (table) {
        var rows = table.querySelectorAll('tbody tr');
        rows.forEach(function(row) {
            var rewardCell = row.querySelector('td:last-child');
            if (rewardCell) {
                if (rewardCell.textContent.trim() === 'Y') {
                    rewardCell.classList.add('reward-yes');
                } else if (rewardCell.textContent.trim() === 'N') {
                    rewardCell.classList.add('reward-no');
                }
            }
        });
    }
});
</script>
"""

# 다운로드 버튼 스타일
DOWNLOAD_BUTTON_STYLE = """
<style>
    .download-button-container {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }

    .download-button {
        display: inline-block;
        background-color: #2196F3;
        color: white !important;
        text-align: center;
        padding: 8px 16px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.3s;
        border: none;
        cursor: pointer;
    }

    .download-button:hover {
        background-color: #0b7dda;
        text-decoration: none;
    }
</style>
"""

# 사용 가이드 마크다운
USAGE_GUIDE_MARKDOWN = """
### 사용 가이드
1. 상담주문내역 엑셀 파일을 업로드합니다.
2. 프로모션 설정에서 다음 옵션을 선택합니다:
   - 대상 품목: 안마의자, 라클라우드, 정수기 중 포함할 품목
   - 서비스 품목 포함 여부: 더케어, 멤버십 포함 여부
   - 직접/연계 옵션: CRM 직접 판매만 포함할지 여부
   - 기준 설정: 승인건수, 승인액 중 순위 기준
   - 최소 조건: 프로모션 참여에 필요한 최소 건수
   - 포상 순위: 포상을 받는 순위 수
3. '설정 적용' 버튼을 클릭하여 프로모션 결과를 확인합니다.
4. 결과를 엑셀 파일로 다운로드할 수 있습니다.

### 필수 컬럼
- 상담사
- 일반회차 캠페인
- 판매 인입경로
- 대분류
- 판매 유형
- 매출 금액
- 주문 일자
"""