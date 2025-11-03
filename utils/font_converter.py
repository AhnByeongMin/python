"""
폰트 변환 유틸리티

TTF 파일을 웹 호환 WOFF2 형식으로 변환합니다.
"""
from fontTools import ttLib
from pathlib import Path
import sys


def convert_ttf_to_woff2(ttf_path: Path, output_path: Path = None) -> Path:
    """
    TTF 파일을 WOFF2 포맷으로 변환합니다.

    Args:
        ttf_path: 입력 TTF 파일 경로
        output_path: 출력 WOFF2 파일 경로 (지정하지 않으면 자동 생성)

    Returns:
        변환된 WOFF2 파일 경로
    """
    if not ttf_path.exists():
        raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {ttf_path}")

    # 출력 경로가 지정되지 않으면 같은 디렉토리에 생성
    if output_path is None:
        output_path = ttf_path.with_suffix('.woff2')

    print(f"폰트 변환 중: {ttf_path.name} → {output_path.name}")

    try:
        # TTF 파일 로드
        font = ttLib.TTFont(ttf_path)

        # WOFF2로 저장 (flavor 설정)
        font.flavor = 'woff2'
        font.save(output_path)

        print(f"✓ 변환 완료: {output_path}")
        print(f"  원본 크기: {ttf_path.stat().st_size / 1024:.1f} KB")
        print(f"  변환 크기: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"  압축률: {(1 - output_path.stat().st_size / ttf_path.stat().st_size) * 100:.1f}%")

        return output_path

    except Exception as e:
        print(f"✗ 변환 실패: {e}", file=sys.stderr)
        raise


def main():
    """메인 함수 - 커맨드라인에서 실행 가능"""
    script_dir = Path(__file__).parent.parent
    font_dir = script_dir / "font"
    ttf_file = font_dir / "바디프랜드M EU.ttf"

    if not ttf_file.exists():
        print(f"폰트 파일을 찾을 수 없습니다: {ttf_file}")
        sys.exit(1)

    try:
        woff2_file = convert_ttf_to_woff2(ttf_file)
        print(f"\n✓ 폰트 변환 성공!")
        print(f"  변환된 파일: {woff2_file}")
    except Exception as e:
        print(f"\n✗ 폰트 변환 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
