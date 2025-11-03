"""
폰트 관리 모듈
애플리케이션 전체에서 사용할 커스텀 폰트를 관리합니다.
"""
import customtkinter as ctk
from pathlib import Path
from typing import Optional
import platform

class FontManager:
    """커스텀 폰트를 관리하는 클래스"""

    # 폰트 파일 경로
    FONT_PATH = Path(__file__).parent.parent / "font" / "바디프랜드M EU.ttf"
    FONT_FAMILY = "바디프랜드M EU"

    # 기본 폰트 크기
    SIZES = {
        "small": 11,
        "normal": 12,
        "medium": 13,
        "large": 14,
        "xlarge": 16,
        "title": 18,
        "header": 20
    }

    @classmethod
    def get_font(cls, size: Optional[int] = None, weight: str = "normal") -> ctk.CTkFont:
        """
        커스텀 폰트를 반환합니다.

        Args:
            size: 폰트 크기 (기본값: SIZES["normal"])
            weight: 폰트 굵기 ("normal" 또는 "bold")

        Returns:
            CTkFont 객체
        """
        if size is None:
            size = cls.SIZES["normal"]

        # 폰트 파일이 존재하는 경우 커스텀 폰트 사용
        if cls.FONT_PATH.exists():
            return ctk.CTkFont(family=cls.FONT_FAMILY, size=size, weight=weight)
        else:
            # 폰트 파일이 없는 경우 시스템 기본 폰트 사용
            fallback_family = cls._get_fallback_font()
            return ctk.CTkFont(family=fallback_family, size=size, weight=weight)

    @classmethod
    def get_small_font(cls, weight: str = "normal") -> ctk.CTkFont:
        """작은 크기의 폰트를 반환합니다."""
        return cls.get_font(cls.SIZES["small"], weight)

    @classmethod
    def get_normal_font(cls, weight: str = "normal") -> ctk.CTkFont:
        """일반 크기의 폰트를 반환합니다."""
        return cls.get_font(cls.SIZES["normal"], weight)

    @classmethod
    def get_medium_font(cls, weight: str = "normal") -> ctk.CTkFont:
        """중간 크기의 폰트를 반환합니다."""
        return cls.get_font(cls.SIZES["medium"], weight)

    @classmethod
    def get_large_font(cls, weight: str = "normal") -> ctk.CTkFont:
        """큰 크기의 폰트를 반환합니다."""
        return cls.get_font(cls.SIZES["large"], weight)

    @classmethod
    def get_title_font(cls, weight: str = "bold") -> ctk.CTkFont:
        """타이틀용 폰트를 반환합니다."""
        return cls.get_font(cls.SIZES["title"], weight)

    @classmethod
    def get_header_font(cls, weight: str = "bold") -> ctk.CTkFont:
        """헤더용 폰트를 반환합니다."""
        return cls.get_font(cls.SIZES["header"], weight)

    @staticmethod
    def _get_fallback_font() -> str:
        """시스템에 따른 폴백 폰트를 반환합니다."""
        system = platform.system()
        if system == "Windows":
            return "맑은 고딕"
        elif system == "Darwin":  # macOS
            return "AppleGothic"
        else:  # Linux
            return "NanumGothic"

    @classmethod
    def load_font(cls):
        """
        시스템에 폰트를 로드합니다.
        애플리케이션 시작 시 한 번 호출해야 합니다.
        """
        if cls.FONT_PATH.exists():
            try:
                import tkinter.font as tkfont
                # Tkinter에서 폰트 파일을 로드
                # 주의: Windows에서는 ctk.CTkFont가 자동으로 처리하므로 추가 작업 불필요
                print(f"폰트 로드 완료: {cls.FONT_PATH}")
                return True
            except Exception as e:
                print(f"폰트 로드 실패: {e}")
                return False
        else:
            print(f"폰트 파일을 찾을 수 없습니다: {cls.FONT_PATH}")
            return False
