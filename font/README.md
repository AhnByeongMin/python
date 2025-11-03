# 커스텀 폰트 가이드

이 폴더에는 애플리케이션에서 사용하는 "바디프랜드M EU" 폰트가 포함되어 있습니다.

## 폰트 정보
- **원본 파일**: 바디프랜드M EU.ttf (907 KB)
- **웹 포맷**: 바디프랜드M EU.woff2 (213 KB) - 자동 변환됨
- **폰트명**: BodyFriendM EU (또는 바디프랜드 M EU)
- **스타일**: Regular

## 작동 방식

애플리케이션은 다음과 같이 폰트를 로드합니다:

1. **WOFF2 파일 우선 사용** (추천)
   - `바디프랜드M EU.woff2` 파일이 있으면 자동으로 base64 인코딩하여 CSS에 임베드
   - 별도의 시스템 설치 불필요
   - 브라우저에서 바로 사용 가능
   - 파일 크기가 작아 빠른 로딩

2. **시스템 폰트 폴백**
   - WOFF2 파일이 없거나 로드 실패 시 시스템에 설치된 폰트 사용
   - 폰트가 설치되지 않은 경우 맑은 고딕, Roboto 등 기본 폰트 사용

## WOFF2 파일 생성 (선택사항)

WOFF2 파일은 이미 포함되어 있습니다. 재생성이 필요한 경우:

```bash
# fonttools 설치
pip install fonttools brotli

# TTF를 WOFF2로 변환
python utils/font_converter.py
```

## 수동 설치 방법 (선택사항)

### Windows
1. `바디프랜드M EU.ttf` 파일을 더블클릭합니다
2. 열리는 창에서 "설치" 버튼을 클릭합니다
3. 또는 파일을 `C:\Windows\Fonts` 폴더에 복사합니다

### Linux
```bash
# 사용자 폰트 디렉토리에 폰트 복사
mkdir -p ~/.fonts
cp "바디프랜드M EU.ttf" ~/.fonts/

# 폰트 캐시 업데이트
fc-cache -f -v

# 설치 확인
fc-list | grep -i "바디프랜드"
```

### macOS
1. `바디프랜드M EU.ttf` 파일을 더블클릭합니다
2. 폰트 북(Font Book)이 열리면 "폰트 설치" 버튼을 클릭합니다
3. 또는 파일을 `/Library/Fonts` 또는 `~/Library/Fonts` 폴더에 복사합니다

## 설치 확인

폰트가 제대로 설치되었는지 확인하려면:

### Windows
- 제어판 → 글꼴에서 "BodyFriendM EU" 또는 "바디프랜드" 검색

### Linux
```bash
fc-list | grep -i "bodyfriend"
```

### macOS
- 폰트 북(Font Book) 앱을 열고 검색

## 애플리케이션에서 사용

Streamlit 애플리케이션을 실행하면 자동으로 폰트가 적용됩니다:

```bash
streamlit run excel-analyzer-app-complete.py
```

**WOFF2 파일이 있는 경우**: 자동으로 임베드되어 즉시 사용됩니다 (추가 설정 불필요).

**WOFF2 파일이 없는 경우**: 시스템에 설치된 폰트를 사용하거나 기본 폴백 폰트를 사용합니다.

## 문제 해결

### 브라우저에서 폰트가 표시되지 않는 경우
1. WOFF2 파일이 `font/` 폴더에 있는지 확인
2. 브라우저 캐시를 지우고 페이지 새로고침 (Ctrl+F5 또는 Cmd+Shift+R)
3. 브라우저 개발자 도구(F12)의 Console 탭에서 에러 확인
4. Streamlit 서버를 재시작

### WOFF2 파일이 없는 경우
```bash
# 폰트 변환 스크립트 실행
python utils/font_converter.py
```

### 폰트 파일 크기가 큰 경우
- WOFF2 포맷은 TTF 대비 약 76% 압축됩니다
- 213KB 정도면 웹에서 사용하기에 적합한 크기입니다
- 초기 로딩 시 한 번만 다운로드되며 브라우저에 캐시됩니다

## 라이선스

이 폰트의 사용은 해당 폰트의 라이선스 조건에 따릅니다.
