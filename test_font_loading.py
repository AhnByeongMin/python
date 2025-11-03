"""
폰트 로딩 테스트 스크립트

WOFF2 폰트가 제대로 로드되고 base64 인코딩되는지 확인합니다.
"""
import base64
from pathlib import Path


def test_font_loading():
    """폰트 로딩 테스트"""
    font_dir = Path(__file__).parent / "font"
    woff2_path = font_dir / "바디프랜드M EU.woff2"

    print("=" * 60)
    print("폰트 로딩 테스트")
    print("=" * 60)

    # 1. WOFF2 파일 존재 확인
    print(f"\n1. WOFF2 파일 확인")
    print(f"   경로: {woff2_path}")
    if woff2_path.exists():
        file_size = woff2_path.stat().st_size
        print(f"   ✓ 파일 존재")
        print(f"   크기: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    else:
        print(f"   ✗ 파일 없음")
        return False

    # 2. 파일 읽기 테스트
    print(f"\n2. 파일 읽기 테스트")
    try:
        with open(woff2_path, "rb") as f:
            font_data = f.read()
        print(f"   ✓ 파일 읽기 성공")
        print(f"   읽은 크기: {len(font_data):,} bytes")
    except Exception as e:
        print(f"   ✗ 파일 읽기 실패: {e}")
        return False

    # 3. Base64 인코딩 테스트
    print(f"\n3. Base64 인코딩 테스트")
    try:
        encoded = base64.b64encode(font_data).decode()
        print(f"   ✓ 인코딩 성공")
        print(f"   인코딩 크기: {len(encoded):,} bytes ({len(encoded) / 1024:.1f} KB)")
        print(f"   인코딩 샘플: {encoded[:60]}...")
    except Exception as e:
        print(f"   ✗ 인코딩 실패: {e}")
        return False

    # 4. CSS 생성 테스트
    print(f"\n4. CSS @font-face 생성 테스트")
    try:
        css = f"""
        @font-face {{
            font-family: 'BodyFriendM EU';
            src: url(data:font/woff2;charset=utf-8;base64,{encoded}) format('woff2');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }}
        """
        print(f"   ✓ CSS 생성 성공")
        print(f"   CSS 크기: {len(css):,} bytes ({len(css) / 1024:.1f} KB)")
    except Exception as e:
        print(f"   ✗ CSS 생성 실패: {e}")
        return False

    # 5. 파일 형식 확인 (WOFF2 매직 넘버)
    print(f"\n5. WOFF2 형식 확인")
    magic = font_data[:4]
    if magic == b'wOF2':
        print(f"   ✓ 올바른 WOFF2 형식")
        print(f"   매직 넘버: {magic.hex()}")
    else:
        print(f"   ⚠ WOFF2 매직 넘버가 아님: {magic.hex()}")

    print("\n" + "=" * 60)
    print("✓ 모든 테스트 통과!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_font_loading()
    exit(0 if success else 1)
