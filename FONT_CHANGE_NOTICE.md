# 폰트 변경 공지

## 📢 변경 사항

커스텀 폰트(바디프랜드M EU)에서 **시스템 기본 폰트**로 변경되었습니다.

### 🔄 변경 이유

1. **데이터프레임 표시 문제**: 커스텀 폰트로 인해 데이터프레임 컬럼 헤더가 깨져 보이는 문제 발생
2. **사용성 저하**: 정렬, 필터 기능 사용 시 텍스트가 겹쳐 보여 사용 불가
3. **안정성**: 시스템 폰트가 모든 환경에서 안정적으로 작동

### ✅ 새로운 폰트 설정

```css
font-family: 'Malgun Gothic',           /* Windows: 맑은 고딕 */
             'Apple SD Gothic Neo',      /* macOS: 애플 산돌고딕 */
             -apple-system,              /* macOS 시스템 폰트 */
             BlinkMacSystemFont,         /* macOS WebKit */
             'Segoe UI',                 /* Windows 최신 */
             Roboto,                     /* Android/Chrome */
             sans-serif;                 /* 기본 sans-serif */
```

### 🎯 특징

- **Windows**: 맑은 고딕 (깔끔하고 가독성 좋음)
- **macOS**: 애플 산돌고딕 (한글 최적화)
- **Linux**: Roboto 또는 시스템 기본 폰트
- **모든 플랫폼**: 해당 OS에 최적화된 폰트 자동 선택

### 📁 관련 파일

기존 커스텀 폰트 파일들은 `font/` 폴더에 보관되어 있습니다:
- `font/바디프랜드M EU.ttf` (원본)
- `font/바디프랜드M EU.woff2` (웹용)
- `font/README.md` (설명서)

필요시 다시 적용할 수 있도록 파일은 삭제하지 않고 유지합니다.

### 🔧 롤백 방법

커스텀 폰트를 다시 사용하고 싶다면:

1. `excel-analyzer-app-complete.py` 파일 열기
2. 20-27번 줄의 `load_custom_font()` 함수를 원래대로 복원
3. CSS 부분의 `'Malgun Gothic'`을 `'BodyFriendM EU'`로 변경

---

**변경일**: 2025-10-27
**버전**: 3.1.1
**상태**: ✅ 적용 완료
