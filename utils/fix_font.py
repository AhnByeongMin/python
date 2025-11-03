"""
폰트 파일의 vhea 테이블 수정
브라우저 호환성 문제를 해결합니다.
"""
from fontTools import ttLib
from pathlib import Path
import sys


def fix_vhea_table(font_path: Path, output_path: Path = None) -> Path:
    """
    폰트의 vhea 테이블을 브라우저 호환 버전으로 수정합니다.

    Args:
        font_path: 입력 폰트 파일 경로
        output_path: 출력 파일 경로 (지정하지 않으면 -fixed 추가)

    Returns:
        수정된 폰트 파일 경로
    """
    if not font_path.exists():
        raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")

    if output_path is None:
        output_path = font_path.with_stem(font_path.stem + "-fixed")

    print(f"폰트 수정 중: {font_path.name}")

    try:
        # 폰트 로드
        font = ttLib.TTFont(font_path)

        # vhea 테이블이 있는지 확인
        if 'vhea' in font:
            print("  - vhea 테이블 발견")
            vhea = font['vhea']
            print(f"    현재 버전: {vhea.tableVersion:#x}")

            # 버전을 1.0으로 변경 (0x00010000)
            if vhea.tableVersion != 0x00010000:
                vhea.tableVersion = 0x00010000
                print(f"    수정된 버전: {vhea.tableVersion:#x}")
            else:
                print("    이미 올바른 버전입니다")
        else:
            print("  - vhea 테이블 없음 (수평 전용 폰트)")
            # vhea 테이블이 없으면 제거 시도
            if 'vhea' in font.tables:
                del font['vhea']
                print("    vhea 테이블 제거됨")

        # WOFF2로 저장
        font.flavor = 'woff2'
        font.save(output_path)

        print(f"✓ 수정 완료: {output_path}")
        print(f"  파일 크기: {output_path.stat().st_size / 1024:.1f} KB")

        return output_path

    except Exception as e:
        print(f"✗ 수정 실패: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent.parent
    font_dir = script_dir / "font"

    # TTF 파일 수정
    ttf_file = font_dir / "바디프랜드M EU.ttf"

    if not ttf_file.exists():
        print(f"폰트 파일을 찾을 수 없습니다: {ttf_file}")
        sys.exit(1)

    try:
        # TTF를 수정하여 WOFF2로 변환
        output_file = font_dir / "바디프랜드M EU.woff2"
        fixed_file = fix_vhea_table(ttf_file, output_file)

        print(f"\n✓ 폰트 수정 성공!")
        print(f"  수정된 파일: {fixed_file}")
        print(f"\n다음 명령으로 테스트하세요:")
        print(f"  python test_font_loading.py")

    except Exception as e:
        print(f"\n✗ 폰트 수정 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
