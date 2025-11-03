"""
프로모션 설정 관리 모듈

이 모듈은 프로모션 설정의 저장, 불러오기, 초기화 기능을 제공합니다.
설정은 data/promotion_config.json 파일에 저장됩니다.
"""

import json
import os
from typing import Dict, Tuple, Optional

# 설정 파일 경로
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
    프로모션 설정을 JSON 파일로 저장

    Args:
        config_data: 저장할 설정 데이터

    Returns:
        Tuple[bool, Optional[str]]: (성공 여부, 오류 메시지)
    """
    try:
        # data 폴더가 없으면 생성
        os.makedirs("data", exist_ok=True)

        # 마지막 업데이트 시간 추가
        from datetime import datetime
        config_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # JSON 파일로 저장
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        return True, None

    except Exception as e:
        return False, f"설정 저장 중 오류: {str(e)}"


def load_config() -> Tuple[Optional[Dict], Optional[str]]:
    """
    JSON 파일에서 프로모션 설정을 불러오기
    파일이 없으면 기본 설정 반환

    Returns:
        Tuple[Optional[Dict], Optional[str]]: (설정 데이터, 오류 메시지)
    """
    try:
        # 파일이 없으면 기본 설정 반환
        if not os.path.exists(CONFIG_FILE):
            return DEFAULT_CONFIG.copy(), None

        # JSON 파일 불러오기
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

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
