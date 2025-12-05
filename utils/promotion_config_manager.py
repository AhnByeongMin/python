"""
프로모션 설정 관리 모듈

이 모듈은 프로모션 설정의 저장, 불러오기, 초기화 기능을 제공합니다.
설정은 SQLite 데이터베이스에 저장됩니다. (이전 JSON 파일 방식에서 DB로 전환됨)
"""

import json
import os
from typing import Dict, Tuple, Optional
from .db_manager import get_db_manager

# 설정 파일 경로 (하위 호환성을 위해 유지)
CONFIG_FILE = "data/promotion_config.json"

# 기본 설정값
DEFAULT_CONFIG = {
    "last_updated": "",
    "product_weights": {
        "안마의자": 5,
        "라클라우드": 3,
        "정수기": 2,
        "더케어": 1,
        "멤버십": 1
    },
    "include_service_products": False,
    "include_online": False,  # 온라인파트 포함 여부 (기본값: False, CRM파트만)
    "include_indirect": False,  # 연계승인 포함 여부 (기본값: False, 직접승인만)
    "minimum_criteria": {
        "count": 7  # 최소 승인 건수
    },
    "promotion_tiers": [
        {"name": "1등급", "min_score": 10, "max_score": None},
        {"name": "2등급", "min_score": 5, "max_score": 9},
        {"name": "3등급", "min_score": 3, "max_score": 4}
    ],
    "analysis_mode": "건수별",  # "제품별" | "건수별" | "금액별"
    "date_range": {
        "start_date": None,
        "end_date": None
    }
}


def save_config(config_data: Dict) -> Tuple[bool, Optional[str]]:
    """
    프로모션 설정을 데이터베이스에 저장 (DB 전환)

    Args:
        config_data: 저장할 설정 데이터

    Returns:
        Tuple[bool, Optional[str]]: (성공 여부, 오류 메시지)
    """
    try:
        # 마지막 업데이트 시간 추가
        from datetime import datetime
        config_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # DB에 저장
        db = get_db_manager()
        db.save_promotion_config("기본설정", config_data)

        return True, None

    except Exception as e:
        return False, f"설정 저장 중 오류: {str(e)}"


def load_config() -> Tuple[Optional[Dict], Optional[str]]:
    """
    데이터베이스에서 프로모션 설정을 불러오기 (DB 전환)
    설정이 없으면 기본 설정 반환

    Returns:
        Tuple[Optional[Dict], Optional[str]]: (설정 데이터, 오류 메시지)
    """
    try:
        # DB에서 불러오기
        db = get_db_manager()
        config_data = db.get_promotion_config("기본설정")

        # 설정이 없으면 기본 설정 반환
        if config_data is None:
            return DEFAULT_CONFIG.copy(), None

        return config_data, None

    except Exception as e:
        # 오류 발생 시 기본 설정 반환
        return DEFAULT_CONFIG.copy(), f"설정 불러오기 중 오류 (기본값 사용): {str(e)}"


def reset_config() -> Tuple[bool, Optional[str]]:
    """
    설정을 기본값으로 초기화

    Returns:
        Tuple[bool, Optional[str]]: (성공 여부, 오류 메시지)
    """
    try:
        return save_config(DEFAULT_CONFIG.copy())
    except Exception as e:
        return False, f"설정 초기화 중 오류: {str(e)}"


def get_default_config() -> Dict:
    """
    기본 설정값 반환

    Returns:
        Dict: 기본 설정 데이터 복사본
    """
    return DEFAULT_CONFIG.copy()
