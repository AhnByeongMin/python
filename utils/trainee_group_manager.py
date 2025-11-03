"""
신입 그룹 설정 관리 모듈

이 모듈은 신입 그룹별 목표 시간 설정을 JSON 파일로 관리합니다.
"""

import os
import json
from typing import Dict, Optional

# 기본 JSON 파일 경로
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "trainee_groups.json")

def load_trainee_groups(json_path: str = DEFAULT_JSON_PATH) -> Dict[str, Dict]:
    """
    신입 그룹 설정을 로드합니다.

    Args:
        json_path: JSON 파일 경로

    Returns:
        Dict[str, Dict]: 그룹명을 키로 하는 설정 딕셔너리
        예: {
            "신입그룹1기": {
                "target_hours": 2,
                "target_minutes": 0
            }
        }
    """
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"신입 그룹 설정 로드 중 오류: {str(e)}")
        return {}

def save_trainee_groups(groups: Dict[str, Dict], json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    신입 그룹 설정을 저장합니다.

    Args:
        groups: 신입 그룹 설정
        json_path: 저장할 JSON 파일 경로

    Returns:
        bool: 저장 성공 여부
    """
    try:
        # 디렉터리가 없으면 생성
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(groups, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"신입 그룹 설정 저장 중 오류: {str(e)}")
        return False

def add_trainee_group(group_name: str, target_hours: int, target_minutes: int,
                     json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    신입 그룹을 추가합니다.

    Args:
        group_name: 그룹명
        target_hours: 목표 시간
        target_minutes: 목표 분
        json_path: JSON 파일 경로

    Returns:
        bool: 추가 성공 여부
    """
    groups = load_trainee_groups(json_path)

    # 이미 존재하는 그룹인지 확인
    if group_name in groups:
        return False

    groups[group_name] = {
        "target_hours": target_hours,
        "target_minutes": target_minutes
    }

    return save_trainee_groups(groups, json_path)

def remove_trainee_group(group_name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    신입 그룹을 제거합니다.

    Args:
        group_name: 그룹명
        json_path: JSON 파일 경로

    Returns:
        bool: 제거 성공 여부
    """
    groups = load_trainee_groups(json_path)

    if group_name not in groups:
        return False

    del groups[group_name]
    return save_trainee_groups(groups, json_path)

def get_trainee_group_target(group_name: str, json_path: str = DEFAULT_JSON_PATH) -> Optional[Dict]:
    """
    신입 그룹의 목표 시간을 가져옵니다.

    Args:
        group_name: 그룹명
        json_path: JSON 파일 경로

    Returns:
        Optional[Dict]: 목표 시간 설정 또는 None
    """
    groups = load_trainee_groups(json_path)
    return groups.get(group_name)

def update_trainee_group(group_name: str, target_hours: int, target_minutes: int,
                        json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    신입 그룹의 목표 시간을 수정합니다.

    Args:
        group_name: 그룹명
        target_hours: 목표 시간
        target_minutes: 목표 분
        json_path: JSON 파일 경로

    Returns:
        bool: 수정 성공 여부
    """
    groups = load_trainee_groups(json_path)

    if group_name not in groups:
        return False

    groups[group_name]["target_hours"] = target_hours
    groups[group_name]["target_minutes"] = target_minutes

    return save_trainee_groups(groups, json_path)
