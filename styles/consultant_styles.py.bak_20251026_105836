"""
상담원 실적 현황 탭의 CSS 스타일 정의
다크/라이트 모드 자동 감지 및 적용 기능 포함
나눔고딕 폰트 적용 및 볼드체 강화
"""

# 상담원 실적 현황 테이블 스타일
CONSULTANT_TABLE_STYLE = """
<style>
    /* 구글 폰트에서 나눔고딕 가져오기 */
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
    
    .table-container {
        width: 50%;  /* 데스크톱에서는 50% 너비로 제한 */
        margin: 0 auto;  /* 중앙 정렬 */
        overflow-x: auto;  /* 모바일에서 가로 스크롤 가능하게 */
        font-family: 'Nanum Gothic', sans-serif;  /* 나눔고딕 적용 */
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
        font-family: 'Nanum Gothic', sans-serif;  /* 나눔고딕 적용 */
        font-weight: 700;  /* 기본 폰트 굵기를 Bold로 설정 */
    }
    
    /* 라이트 모드 스타일 (기본값) */
    .compact-table thead tr {
        background-color: #0e50a1;  /* 더 진한 배경색 */
        color: white;  /* 흰색 텍스트로 강조 */
        text-align: center;
        font-weight: 800;  /* ExtraBold로 강화 */
        letter-spacing: 0.5px;  /* 글자 간격 넓히기 */
    }
    .compact-table th, .compact-table td {
        padding: 4px 3px;  /* 패딩 살짝 증가 */
        text-align: center;
        border: 1px solid #ddd;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .compact-table th {
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.2);  /* 텍스트에 약간의 그림자 */
        font-size: 0.9em;  /* 헤더 폰트 더 크게 */
        font-weight: 800;  /* ExtraBold로 강화 */
    }
    .compact-table tbody tr {
        background-color: #ffffff;
        color: #333;
    }
    .compact-table tbody tr:nth-of-type(even) {
        background-color: #f9f9f9;
    }
    .compact-table tbody tr.summary-row {
        background-color: #0e50a1;  /* 헤더와 동일한 배경색 */
        color: white;  /* 흰색 텍스트 */
        font-weight: 800;  /* ExtraBold로 강화 */
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.2);  /* 텍스트에 약간의 그림자 */
    }
    
    /* 명시적 다크 테마 클래스 */
    .compact-table.dark-theme thead tr {
        background-color: #1565C0;  /* 다크 모드에서도 눈에 잘 띄는 파란색 */
        color: white;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.4);  /* 더 강한 그림자 */
    }
    .compact-table.dark-theme th, 
    .compact-table.dark-theme td {
        border: 1px solid #444;
    }
    .compact-table.dark-theme tbody tr {
        background-color: #1E1E1E;
        color: white;
    }
    .compact-table.dark-theme tbody tr:nth-of-type(even) {
        background-color: #2D2D2D;
    }
    .compact-table.dark-theme tbody tr.summary-row {
        background-color: #1565C0;  /* 다크 모드 헤더와 동일한 배경색 */
        color: white;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.4);  /* 더 강한 그림자 */
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
    .compact-table th:nth-child(9), .compact-table td:nth-child(9) { width: 5%; }  /* 콜수 */
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
    
    /* 프로그레스 바 스타일 */
    .calltime-cell {
        position: relative;
        overflow: visible;
        z-index: 1;
    }

    .progress-bar-bg {
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        background-color: #4CAF50;  /* 녹색 배경 */
        z-index: -1;
        opacity: 0.7;
        border-radius: 0 2px 2px 0;
    }

    /* 다크 테마에서의 프로그레스 바 */
    .compact-table.dark-theme .progress-bar-bg {
        background-color: #2E7D32;  /* 다크 테마에서 더 어두운 녹색 */
        opacity: 0.8;
    }

    /* 요약 텍스트 박스 스타일 */
    .summary-textbox {
        margin-top: 20px;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        background-color: #f8f9fa;
        width: 90%;
        margin-left: auto;
        margin-right: auto;
        font-family: 'Nanum Gothic', sans-serif;
        font-size: 0.8em;
        line-height: 1.5;
    }

    /* 요약 텍스트 박스 스타일 */
    .summary-textbox {
        margin-top: 20px;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        background-color: #f8f9fa;
        width: 90%;
        margin-left: auto;
        margin-right: auto;
        font-family: 'Nanum Gothic', sans-serif;
        font-size: 0.8em;
        line-height: 1.5;
        color: #333;  /* 라이트 모드에서 텍스트 색상 명시적 지정 */
    }

    .summary-textbox-title {
        font-weight: 800;
        font-size: 1.1em;
        margin-bottom: 10px;
        color: #0e50a1;  /* 진한 파란색으로 유지 */
    }

    .summary-textbox-team {
        margin-bottom: 5px;
        font-weight: 700;
        color: #333;  /* 라이트 모드에서 텍스트 색상 명시적 지정 */
    }

    .summary-textbox-product {
        margin-top: 10px;
        font-weight: 700;
        color: #333;  /* 라이트 모드에서 텍스트 색상 명시적 지정 */
    }

    .summary-textbox-total {
        margin-top: 15px;
        font-weight: 800;
        color: #0e50a1;  /* 진한 파란색으로 유지 */
        font-size: 1.1em;
    }

    /* 다크 테마 요약 텍스트 박스 */
    .dark-theme .summary-textbox {
        background-color: #1E1E1E;
        border-color: #444;
        color: #E0E0E0;
    }

    .dark-theme .summary-textbox-title {
        color: #1565C0;
    }

    .dark-theme .summary-textbox-total {
        color: #1565C0;
    }
</style>

<script>
// Streamlit 테마 감지 및 테이블 스타일 적용 스크립트
document.addEventListener('DOMContentLoaded', function() {
    // 테마 감지 및 적용 함수
    function detectAndApplyTheme() {
        try {
            // 테마 감지를 위한 방법들 
            let isDarkTheme = false;
            
            // 1. Streamlit 앱 컨테이너에서 테마 확인
            const stApp = document.querySelector('[data-testid="stAppViewContainer"]');
            if (stApp && stApp.getAttribute('data-theme') === 'dark') {
                isDarkTheme = true;
            }
            
            // 2. 시스템 다크 모드 설정 확인
            else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                isDarkTheme = true;
            }
            
            // 3. body 클래스에서 테마 확인
            else if (document.body.classList.contains('dark')) {
                isDarkTheme = true;
            }
            
            // 4. 배경 색상으로 추정
            else {
                const bodyBgColor = window.getComputedStyle(document.body).backgroundColor;
                if (bodyBgColor) {
                    // RGB 값 파싱 (rgb(r, g, b) 형식)
                    const rgb = bodyBgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
                    if (rgb) {
                        const [_, r, g, b] = rgb.map(Number);
                        // 어두운 배경이면 다크 모드로 간주 (밝기가 낮으면)
                        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
                        if (brightness < 128) {
                            isDarkTheme = true;
                        }
                    }
                }
            }
            
            // 테마 적용
            const tables = document.querySelectorAll('.compact-table');
            tables.forEach(table => {
                if (isDarkTheme) {
                    table.classList.add('dark-theme');
                } else {
                    table.classList.remove('dark-theme');
                }
            });
            
            // 요약 텍스트 박스에도 테마 적용
            const textboxes = document.querySelectorAll('.summary-textbox');
            textboxes.forEach(box => {
                if (isDarkTheme) {
                    box.classList.add('dark-theme');
                } else {
                    box.classList.remove('dark-theme');
                }
            });
            
            // 다운로드 버튼 컨테이너에도 테마 적용
            const buttonContainers = document.querySelectorAll('.download-button-container');
            buttonContainers.forEach(container => {
                if (isDarkTheme) {
                    container.classList.add('dark-theme');
                } else {
                    container.classList.remove('dark-theme');
                }
            });
        } catch (e) {
            console.error('Theme detection error:', e);
        }
    }
    
    // 초기 테마 적용
    detectAndApplyTheme();
    
    // 변경 감지를 위한 MutationObserver 설정
    const observer = new MutationObserver(function(mutationsList) {
        for (const mutation of mutationsList) {
            if (mutation.type === 'attributes' && 
                (mutation.attributeName === 'data-theme' || 
                 mutation.attributeName === 'class')) {
                detectAndApplyTheme();
                break;
            }
        }
    });
    
    observer.observe(document.body, { 
        attributes: true,
        childList: true,
        subtree: true
    });
    
    // 시스템 테마 변경 감지
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', detectAndApplyTheme);
    }
    
    // 지연 처리 (DOM이 완전히 로드된 후 다시 확인)
    setTimeout(detectAndApplyTheme, 500);
});
</script>
"""

# 상담원 실적 현황 샘플 테이블 스타일
CONSULTANT_SAMPLE_TABLE_STYLE = """
<style>
    /* 구글 폰트에서 나눔고딕 가져오기 */
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
    
    .table-container {
        width: 50%;  /* 데스크톱에서는 50% 너비로 제한 */
        margin: 0 auto;  /* 중앙 정렬 */
        overflow-x: auto;  /* 모바일에서 가로 스크롤 가능하게 */
        font-family: 'Nanum Gothic', sans-serif;  /* 나눔고딕 적용 */
    }
    
    /* 모바일 환경에서는 컨테이너를 100% 너비로 확장 */
    @media (max-width: 768px) {
        .table-container {
            width: 100%;
        }
    }
    
    .compact-table {
        border-collapse: collapse;
        font-size: 0.7em;
        width: 100%;
        table-layout: fixed;
        margin: 0 auto;
        font-family: 'Nanum Gothic', sans-serif;  /* 나눔고딕 적용 */
        font-weight: 700;  /* 기본 폰트 굵기를 Bold로 설정 */
    }
    
    /* 라이트 모드 스타일 (기본값) */
    .compact-table thead tr {
        background-color: #0e50a1;  /* 더 진한 배경색 */
        color: white;  /* 흰색 텍스트로 강조 */
        text-align: center;
        font-weight: 800;  /* ExtraBold로 강화 */
        letter-spacing: 0.5px;  /* 글자 간격 넓히기 */
    }
    .compact-table th, .compact-table td {
        padding: 4px 3px;  /* 패딩 살짝 증가 */
        text-align: center;
        border: 1px solid #ddd;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .compact-table th {
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.2);  /* 텍스트에 약간의 그림자 */
        font-size: 0.9em;  /* 헤더 폰트 더 크게 */
        font-weight: 800;  /* ExtraBold로 강화 */
    }
    .compact-table tbody tr {
        background-color: #ffffff;
        color: #333;
    }
    .compact-table tbody tr:nth-of-type(even) {
        background-color: #f9f9f9;
    }
    .compact-table tbody tr.summary-row {
        background-color: #0e50a1;  /* 헤더와 동일한 배경색 */
        color: white;  /* 흰색 텍스트 */
        font-weight: 800;  /* ExtraBold로 강화 */
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.2);  /* 텍스트에 약간의 그림자 */
    }
    
    /* 명시적 다크 테마 클래스 */
    .compact-table.dark-theme thead tr {
        background-color: #1565C0;  /* 다크 모드에서도 눈에 잘 띄는 파란색 */
        color: white;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.4);  /* 더 강한 그림자 */
    }
    .compact-table.dark-theme th, 
    .compact-table.dark-theme td {
        border: 1px solid #444;
    }
    .compact-table.dark-theme tbody tr {
        background-color: #1E1E1E;
        color: white;
    }
    .compact-table.dark-theme tbody tr:nth-of-type(even) {
        background-color: #2D2D2D;
    }
    .compact-table.dark-theme tbody tr.summary-row {
        background-color: #1565C0;  /* 다크 모드 헤더와 동일한 배경색 */
        color: white;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.4);  /* 더 강한 그림자 */
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
    
    /* 프로그레스 바 스타일 */
    .calltime-cell {
        position: relative;
        overflow: visible;
        z-index: 1;
    }

    .progress-bar-bg {
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        background-color: #4CAF50;  /* 녹색 배경 */
        z-index: -1;
        opacity: 0.7;
        border-radius: 0 2px 2px 0;
    }

    /* 다크 테마에서의 프로그레스 바 */
    .compact-table.dark-theme .progress-bar-bg {
        background-color: #2E7D32;  /* 다크 테마에서 더 어두운 녹색 */
        opacity: 0.8;
    }
    
    /* 요약 텍스트 박스 스타일 */
    .summary-textbox {
        margin-top: 20px;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        background-color: #f8f9fa;
        width: 90%;
        margin-left: auto;
        margin-right: auto;
        font-family: 'Nanum Gothic', sans-serif;
        font-size: 0.8em;
        line-height: 1.5;
    }

    .summary-textbox-title {
        font-weight: 800;
        font-size: 1.1em;
        margin-bottom: 10px;
        color: #0e50a1;
    }

    .summary-textbox-team {
        margin-bottom: 5px;
        font-weight: 700;
    }

    .summary-textbox-product {
        margin-top: 10px;
        font-weight: 700;
    }

    .summary-textbox-total {
        margin-top: 15px;
        font-weight: 800;
        color: #0e50a1;
        font-size: 1.1em;
    }

    /* 다크 테마 요약 텍스트 박스 */
    .dark-theme .summary-textbox {
        background-color: #1E1E1E;
        border-color: #444;
        color: #E0E0E0;
    }

    .dark-theme .summary-textbox-title {
        color: #1565C0;
    }

    .dark-theme .summary-textbox-total {
        color: #1565C0;
    }
</style>

<script>
// Streamlit 테마 감지 및 테이블 스타일 적용 스크립트
document.addEventListener('DOMContentLoaded', function() {
    // 테마 감지 및 적용 함수
    function detectAndApplyTheme() {
        try {
            // 테마 감지를 위한 방법들 
            let isDarkTheme = false;
            
            // 1. Streamlit 앱 컨테이너에서 테마 확인
            const stApp = document.querySelector('[data-testid="stAppViewContainer"]');
            if (stApp && stApp.getAttribute('data-theme') === 'dark') {
                isDarkTheme = true;
            }
            
            // 2. 시스템 다크 모드 설정 확인
            else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                isDarkTheme = true;
            }
            
            // 3. body 클래스에서 테마 확인
            else if (document.body.classList.contains('dark')) {
                isDarkTheme = true;
            }
            
            // 4. 배경 색상으로 추정
            else {
                const bodyBgColor = window.getComputedStyle(document.body).backgroundColor;
                if (bodyBgColor) {
                    // RGB 값 파싱 (rgb(r, g, b) 형식)
                    const rgb = bodyBgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
                    if (rgb) {
                        const [_, r, g, b] = rgb.map(Number);
                        // 어두운 배경이면 다크 모드로 간주 (밝기가 낮으면)
                        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
                        if (brightness < 128) {
                            isDarkTheme = true;
                        }
                    }
                }
            }
            
            // 테마 적용
            const tables = document.querySelectorAll('.compact-table');
            tables.forEach(table => {
                if (isDarkTheme) {
                    table.classList.add('dark-theme');
                } else {
                    table.classList.remove('dark-theme');
                }
            });
            
            // 요약 텍스트 박스에도 테마 적용
            const textboxes = document.querySelectorAll('.summary-textbox');
            textboxes.forEach(box => {
                if (isDarkTheme) {
                    box.classList.add('dark-theme');
                } else {
                    box.classList.remove('dark-theme');
                }
            });
        } catch (e) {
            console.error('Theme detection error:', e);
        }
    }
    
    // 초기 테마 적용
    detectAndApplyTheme();
    
    // 변경 감지를 위한 MutationObserver 설정
    const observer = new MutationObserver(function(mutationsList) {
        for (const mutation of mutationsList) {
            if (mutation.type === 'attributes' && 
                (mutation.attributeName === 'data-theme' || 
                 mutation.attributeName === 'class')) {
                detectAndApplyTheme();
                break;
            }
        }
    });
    
    observer.observe(document.body, { 
        attributes: true,
        childList: true,
        subtree: true
    });
    
    // 시스템 테마 변경 감지
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', detectAndApplyTheme);
    }
    
    // 지연 처리 (DOM이 완전히 로드된 후 다시 확인)
    setTimeout(detectAndApplyTheme, 500);
});
</script>
"""

# 다운로드 버튼 스타일
DOWNLOAD_BUTTON_STYLE = """
<style>
/* 구글 폰트에서 나눔고딕 가져오기 */
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');

.download-button {
    display: inline-block;
    width: auto;
    padding: 8px 20px;
    text-align: center;
    border-radius: 25px;
    font-weight: 800;  /* ExtraBold로 강화 */
    text-decoration: none;
    margin-top: 20px;
    transition: all 0.2s ease;
    margin: 0 auto;
    font-family: 'Nanum Gothic', sans-serif;  /* 나눔고딕 적용 */
    
    /* 라이트 모드 기본 스타일 */
    background-color: transparent;
    color: #555;
    border: 1px solid #999;
}

.download-button:hover {
    color: #3a85ff;
    border-color: #3a85ff;
}

/* 다크 테마 적용 */
.dark-theme .download-button {
    color: #E0E0E0;
    border: 1px solid #555;
}

.dark-theme .download-button:hover {
    color: #3a85ff;
    border-color: #3a85ff;
}

.download-button-container {
    text-align: center;
    width: 100%;
    margin-top: 20px;
    font-family: 'Nanum Gothic', sans-serif;  /* 나눔고딕 적용 */
}
</style>
"""

# 날짜 표시 스타일
DATE_DISPLAY_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
</style>
<h4 style="text-align: center; margin-bottom: 15px; letter-spacing: 1px; word-spacing: 5px; font-family: 'Nanum Gothic', sans-serif; font-weight: 800;">{date_display}</h4>
"""

# 상담원 실적 현황 설명 스타일
CONSULTANT_DESCRIPTION = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
</style>
<p style="font-family: 'Nanum Gothic', sans-serif; font-weight: 700;">이 도구는 상담원의 실적 현황을 분석하고 시각화합니다. 상담주문계약내역과 콜타임 파일을 업로드하여 상담원별 실적을 확인할 수 있습니다.</p>
"""

# 사용 가이드 마크다운
USAGE_GUIDE_MARKDOWN = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
.nanumgothic-guide {
    font-family: 'Nanum Gothic', sans-serif;
    font-weight: 700;
}
.nanumgothic-guide h3 {
    font-weight: 800;
}
</style>
<div class="nanumgothic-guide">
<h3>사용 가이드</h3>
<ol>
<li>상담주문계약내역 및 콜타임 엑셀 파일을 업로드하세요.</li>
<li>파일이 업로드되면 자동으로 분석이 진행됩니다.</li>
<li>조직별로 상담원 실적을 확인하고 엑셀로 다운로드할 수 있습니다.</li>
</ol>
</div>
"""