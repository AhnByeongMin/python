# 커스텀 폰트 설정 완료

"바디프랜드M EU" 폰트가 애플리케이션에 성공적으로 적용되었습니다.

## 📋 요약

- ✅ TTF 파일의 vhea 테이블 버전 수정 (0x10001 → 0x10000)
- ✅ 수정된 TTF를 WOFF2 포맷으로 변환 (907KB → 213KB, 76.5% 압축)
- ✅ WOFF2 파일을 base64로 인코딩하여 CSS에 임베드
- ✅ 시스템 폰트 설치 불필요 (자동으로 임베드됨)
- ✅ 브라우저 호환성 문제 완전 해결 (OTS parsing error 수정)
- ✅ 폴백 폰트 체인 구성 (폰트 미적용 시 대체 폰트 사용)

## 🎯 작동 방식

### 1. 폰트 로딩 우선순위
```
WOFF2 파일 (임베드)
  → 시스템 폰트 (BodyFriendM EU)
    → 시스템 폰트 (바디프랜드 M EU)
      → 맑은 고딕 (Malgun Gothic)
        → Roboto
          → sans-serif (시스템 기본)
```

### 2. 파일 구조
```
font/
├── 바디프랜드M EU.ttf      # 원본 폰트 (907 KB)
├── 바디프랜드M EU.woff2    # 웹 호환 폰트 (213 KB) ⭐
└── README.md               # 폰트 가이드

utils/
└── font_converter.py       # TTF → WOFF2 변환 도구

excel-analyzer-app-complete.py  # 메인 앱 (폰트 자동 로드)
test_font_loading.py            # 폰트 로딩 테스트
```

### 3. 코드 구현

**폰트 로드 함수** ([excel-analyzer-app-complete.py:20-52](excel-analyzer-app-complete.py#L20-L52)):
```python
def load_custom_font():
    """WOFF2 폰트를 base64로 인코딩하여 CSS에 임베드"""
    woff2_path = Path(__file__).parent / "font" / "바디프랜드M EU.woff2"

    if woff2_path.exists():
        with open(woff2_path, "rb") as f:
            font_data = base64.b64encode(f.read()).decode()

        return f"""
        @font-face {{
            font-family: 'BodyFriendM EU';
            src: url(data:font/woff2;base64,{font_data}) format('woff2');
            font-display: swap;
        }}
        """
    return ""
```

**CSS 적용**:
```css
html, body, [class*="css"], .main {
    font-family: 'BodyFriendM EU', '바디프랜드 M EU',
                 'Malgun Gothic', 'Roboto', sans-serif !important;
}
```

## 🚀 사용 방법

### 기본 사용 (추가 설정 불필요)
```bash
streamlit run excel-analyzer-app-complete.py
```

WOFF2 파일이 있으면 자동으로 폰트가 적용됩니다.

### 폰트 재생성 (필요시)
```bash
# fonttools 설치
pip install fonttools brotli

# vhea 테이블 수정 + WOFF2 변환 (권장)
python utils/fix_font.py

# 또는 단순 변환만 (vhea 문제 있을 수 있음)
python utils/font_converter.py
```

### 폰트 로딩 테스트
```bash
python test_font_loading.py
```

## 🔍 확인 방법

### 1. 브라우저에서 확인
1. 애플리케이션 실행 후 브라우저 열기
2. F12 (개발자 도구) → Console 탭
3. 에러 메시지 없이 로드되면 성공

### 2. 폰트 적용 확인
1. F12 (개발자 도구) → Elements 탭
2. 아무 텍스트 요소 선택
3. Computed 탭에서 `font-family` 확인
4. "BodyFriendM EU"가 표시되면 성공

### 3. 네트워크 확인
- F12 → Network 탭
- 별도의 폰트 다운로드 요청 없음 (CSS에 임베드되어 있음)
- HTML과 함께 한 번에 로드됨

## ⚙️ 기술 스펙

| 항목 | 값 |
|------|-----|
| 원본 포맷 | TrueType Font (.ttf) |
| 웹 포맷 | Web Open Font Format 2 (.woff2) |
| 원본 크기 | 907 KB |
| 압축 크기 | 213 KB |
| 압축률 | 76.6% |
| Base64 크기 | 283 KB |
| 인코딩 | UTF-8 |
| MIME 타입 | font/woff2 |
| 브라우저 지원 | Chrome, Firefox, Safari, Edge (모던 브라우저) |

## 🐛 문제 해결

### 폰트가 표시되지 않을 때
1. WOFF2 파일 확인: `ls -lh font/*.woff2`
2. 브라우저 캐시 삭제: Ctrl+Shift+Delete
3. 하드 리프레시: Ctrl+F5 (Windows) / Cmd+Shift+R (Mac)
4. Streamlit 서버 재시작
5. HTML 테스트 페이지로 확인: `test_font.html` 파일을 브라우저에서 열기

### OTS parsing error 발생 시
- ✅ **해결됨**: vhea 테이블 버전을 0x10000으로 수정하여 완전히 해결
- 원인: 원본 폰트의 vhea 테이블 버전이 0x10001 (비표준)
- 해결: `python utils/fix_font.py` 실행하여 표준 버전(0x10000)으로 수정

### 파일 크기 문제
- WOFF2는 이미 최적화된 포맷 (76.6% 압축)
- 213KB는 웹 폰트로 적합한 크기
- 초기 로딩 후 브라우저에 캐시됨

## 📚 참고 자료

- **WOFF2 스펙**: https://www.w3.org/TR/WOFF2/
- **fonttools 문서**: https://fonttools.readthedocs.io/
- **CSS @font-face**: https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face

## ✅ 완료 체크리스트

- [x] fonttools 설치
- [x] vhea 테이블 버전 수정 (0x10001 → 0x10000)
- [x] TTF → WOFF2 변환
- [x] base64 인코딩 구현
- [x] CSS 임베드 적용
- [x] 폴백 폰트 설정
- [x] 테스트 스크립트 작성
- [x] HTML 테스트 페이지 작성
- [x] 문서화 완료
- [x] OTS parsing error 완전 해결

## 📁 생성된 파일

- `font/바디프랜드M EU.woff2` - 수정되고 최적화된 웹 폰트 (213KB)
- `utils/fix_font.py` - vhea 테이블 수정 + WOFF2 변환 도구
- `utils/font_converter.py` - 단순 TTF → WOFF2 변환 도구
- `test_font_loading.py` - Python 폰트 로딩 테스트
- `test_font.html` - 브라우저 폰트 테스트 페이지
- `FONT_SETUP.md` - 이 문서

---

**상태**: ✅ 완료 및 검증됨
**테스트**: ✅ 모든 테스트 통과
**브라우저 호환성**: ✅ OTS parsing error 해결
**버전**: 2.0.0 (vhea 테이블 수정 버전)
**마지막 업데이트**: 2025-10-27
