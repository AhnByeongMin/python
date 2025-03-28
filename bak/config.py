"""
CRM 데이터 분석기 설정 파일

이 파일은 애플리케이션 전체에서 사용되는 상수 및 설정값들을 포함합니다.
하드코딩된 값들을 중앙화하여 유지보수를 용이하게 합니다.
"""

# 필요한 라이브러리 임포트
import plotly.express as px  # 차트 색상 등을 위해 필요

# API 설정
API_SETTINGS = {
    # 공공데이터포털 API 키 (공휴일 정보 조회용)
    "HOLIDAY_API_KEY": "98ZmBNqJKopiWlxH4hak1rclm30Dx1Ht3aGvPhs%2B90%2FW0Xf4zmisn2y7ebqbUiwfjLOMtgo4n48N9smQyhL7zQ%3D%3D",
    "HOLIDAY_API_URL": "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getHoliDeInfo"
}

# 법정 공휴일 (양력 기준, 월/일)
FIXED_HOLIDAYS = {
    (1, 1): "신정",
    (3, 1): "삼일절",
    (5, 5): "어린이날",
    (6, 6): "현충일",
    (8, 15): "광복절",
    (10, 3): "개천절",
    (10, 9): "한글날",
    (12, 25): "크리스마스"
}

# 음력 기반 공휴일 (설날, 추석) - 매년 변동됨
LUNAR_HOLIDAYS = {
    # (년, 월, 일): 명칭
    (2024, 2, 9): "설날 전날",
    (2024, 2, 10): "설날",
    (2024, 2, 11): "설날 다음날",
    (2024, 9, 16): "추석 전날",
    (2024, 9, 17): "추석",
    (2024, 9, 18): "추석 다음날",
    (2025, 1, 28): "설날 전날",
    (2025, 1, 29): "설날",
    (2025, 1, 30): "설날 다음날",
    (2025, 10, 5): "추석 전날",
    (2025, 10, 6): "추석",
    (2025, 10, 7): "추석 다음날"
}

# 대체 공휴일 (확정된 날짜만 포함)
ALTERNATIVE_HOLIDAYS = [
    (2024, 5, 6),  # 어린이날 대체
    (2025, 3, 3),  # 삼일절 대체
    # 더 많은 대체 공휴일은 확정되는 대로 추가
]

# 파일 처리 설정
FILE_SETTINGS = {
    # 엑셀 파일 읽기 관련 설정
    "SUPPORTED_ENCODINGS": ['utf-8', 'cp949', 'euc-kr', 'latin1'],
    "DEFAULT_ENCODING": "utf-8",
    
    # 지원하는 파일 형식
    "SUPPORTED_EXTENSIONS": ['xlsx', 'xls'],
    
    # 파일 미리보기 최대 바이트 수
    "PREVIEW_BYTES": 1000
}

# 매출 분석 관련 설정
SALES_ANALYSIS = {
    # VAT 세율 설정
    "VAT_RATE": 0.011,
    
    # 분석 결과 정렬 기준 (안마의자, 라클라우드, 정수기)
    "PRODUCT_ORDER": ['안마의자', '라클라우드', '정수기'],
    
    # 패키지 할인 회차에서 0으로 대체할 값들
    "ZERO_PACKAGE_DISCOUNT_VALUES": [39, 59, 60]
}

# 상담원 설정
CONSULTANT_SETTINGS = {
    # 온라인 팀 소속 상담원 목록
    "ONLINE_TEAM_MEMBERS": ['김부자', '최진영'],
    
    # 유효하지 않은 상담원명 패턴
    "INVALID_CONSULTANT_PATTERNS": ['휴식', '후처리', '대기', '기타', '합계', '00:00:00', '0:00:00'],
    
    # 유효하지 않은 패턴들 (파일 처리 시 제외할 항목)
    "INVALID_PATTERNS": ['상담원ID', '상담원 ID', '합계', '합 계', '총계', '총 계'],
    
    # 0 시간 관련 패턴
    "ZERO_TIME_PATTERNS": ['0:00:00', '00:00:00', '0']
}

# 캠페인 분석 설정
CAMPAIGN_SETTINGS = {
    # 캠페인 타입 분류 키워드
    "CAMPAIGN_KEYWORDS": ["캠", "정규", "재분배"],
    
    # 캠페인 타입별 정렬 순서 값
    "CAMPAIGN_TYPE_ORDER": {
        "CAMPAIGN": 1,    # 캠페인
        "REGULAR": 2,     # 정규
        "REDISTRIBUTION": 3,  # 재분배
        "OTHER": 4        # 기타
    },
    
    # 컬럼 순서 정의
    "COLUMN_ORDER": ['행 레이블', '총합계', '전환율', '주문승인', '승인취소', '체험신청', '예약', '진행중', 
                    '상담취소', '자격미달', '재접수', '중복', '결번', '해피콜거부', '신규']
}

# 에러 메시지 포맷
ERROR_MESSAGES = {
    "FILE_READ_ERROR": "파일 읽기 중 오류: {error}",
    "FILE_CONTENT_ERROR": "파일 내용 확인 중 오류 발생: {error}",
    "EXCEL_PROCESSING_ERROR": "엑셀 파일 처리 중 오류: {error}",
    "HTML_PROCESSING_ERROR": "HTML 처리 중 오류: {error}",
    "CAMPAIGN_PROCESSING_ERROR": "{file_name} 처리 중 오류가 발생했습니다: {error}",
    "DATA_COMBINATION_ERROR": "데이터 결합 중 오류가 발생했습니다: {error}",
    "EMPTY_DATA_ERROR": "결합된 데이터가 비어 있습니다.",
    "MISSING_COLUMN_ERROR": "{column_name} 컬럼이 없습니다.",
    "MISSING_COLUMNS_ERROR": "필요한 열이 없습니다: {columns}",
    "CONSULTANT_ANALYSIS_ERROR": "상담사별 분석 중 오류가 발생했습니다: {error}",
    "EXCEL_CREATION_ERROR": "엑셀 파일 생성 중 오류가 발생했습니다: {error}",
    "LAYOUT_ERROR": "{component} 컬럼이 없어 {feature}를 표시할 수 없습니다.",
    "PIVOT_TABLE_ERROR": "피벗 테이블 생성 중 오류가 발생했습니다: {error}",
    "NO_DATA_ERROR": "{data_type}이(가) 비어 있습니다.",
    "API_ERROR": "API 호출 중 오류가 발생했습니다: {error}"
}

# 성공 메시지 포맷
SUCCESS_MESSAGES = {
    "ANALYSIS_COMPLETE": "분석 완료 (소요 시간: {time:.2f}초)",
    "DATA_LOADED": "총 {count}개의 레코드가 로드되었습니다.",
    "FILTERED_DATA": "현재 {count}개의 레코드가 필터링되었습니다.",
    "ANALYSIS_RESULT": "{count}개의 레코드로 분석되었습니다.",
    "CONSULTANT_ANALYSIS": "총 {count}명의 상담원 실적이 분석되었습니다.",
    "FILES_UPLOADED": "총 {count}개의 파일이 업로드되었습니다:"
}

# UI 관련 설정
UI_SETTINGS = {
    # 차트 관련 설정
    "CHART_COLORS": px.colors.qualitative.G10,
    "CHART_HEIGHT": 400,
    "DASHBOARD_HEIGHT": 500,
    "COMPACT_CHART_HEIGHT": 300,
    
    # 표 관련 설정
    "TABLE_HEIGHT": 400,
    "PIVOT_TABLE_HEIGHT": 600,
    
    # 폰트 설정
    "FONT_SIZE": 12,
    "COMPACT_FONT_SIZE": 10,
    
    # 컬럼 너비 설정 (엑셀 출력용)
    "COLUMN_WIDTHS": {0: 6, 1: 15, 2: 8, 3: 10, 4: 8, 5: 8, 6: 8, 7: 6, 8: 8, 9: 10}
}