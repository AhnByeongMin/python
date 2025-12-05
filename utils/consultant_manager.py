"""
상담사 관리 모듈

이 모듈은 상담사 목록을 SQLite 데이터베이스로 관리하는 기능을 제공합니다.
(이전 JSON 파일 방식에서 DB 방식으로 전환됨)
"""

import os
import json
from typing import Dict, List, Optional
from .db_manager import get_db_manager

# 기본 JSON 파일 경로 (하위 호환성을 위해 유지)
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "consultants.json")

# 팀명 ↔ 파트명 매핑 (로직에서는 파트명 사용)
TEAM_TO_PART_MAP = {
    "CRM팀": "CRM파트",
    "온라인팀": "온라인파트"
}

PART_TO_TEAM_MAP = {
    "CRM파트": "CRM팀",
    "온라인파트": "온라인팀"
}

def get_part_name(team_name: str) -> str:
    """팀명을 파트명으로 변환"""
    return TEAM_TO_PART_MAP.get(team_name, team_name)

def get_team_name(part_name: str) -> str:
    """파트명을 팀명으로 변환"""
    return PART_TO_TEAM_MAP.get(part_name, part_name)

def load_consultants(json_path: str = DEFAULT_JSON_PATH) -> Dict[str, List[str]]:
    """
    데이터베이스에서 상담사 목록을 로드합니다. (DB 전환)

    Args:
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        Dict[str, List[str]]: 팀별 상담사 목록
    """
    try:
        db = get_db_manager()
        return db.get_consultants_by_team()
    except Exception as e:
        print(f"상담사 목록 로드 중 오류: {str(e)}")
        # 오류 시 빈 목록 반환
        return {"CRM팀": [], "온라인팀": []}

def save_consultants(consultants: Dict[str, List[str]], json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    상담사 목록을 데이터베이스에 저장합니다. (DB 전환)

    Args:
        consultants: 팀별 상담사 목록
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        bool: 저장 성공 여부
    """
    try:
        db = get_db_manager()
        db.bulk_add_consultants(consultants)
        return True
    except Exception as e:
        print(f"상담사 목록 저장 중 오류: {str(e)}")
        return False

def add_consultant(team: str, name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    상담사를 추가합니다. (DB 전환)

    Args:
        team: 팀 이름
        name: 상담사 이름
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        bool: 추가 성공 여부
    """
    try:
        db = get_db_manager()
        db.add_consultant(name, team)
        return True
    except Exception as e:
        print(f"상담사 추가 중 오류: {str(e)}")
        return False

def remove_consultant(team: str, name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    상담사를 제거합니다. (DB 전환)

    Args:
        team: 팀 이름
        name: 상담사 이름
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        bool: 제거 성공 여부
    """
    try:
        db = get_db_manager()
        db.remove_consultant(name)
        return True
    except Exception as e:
        print(f"상담사 제거 중 오류: {str(e)}")
        return False

def get_all_consultants(json_path: str = DEFAULT_JSON_PATH) -> List[str]:
    """
    모든 상담사 목록을 가져옵니다. (DB 전환)

    Args:
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        List[str]: 모든 상담사 목록
    """
    consultants = load_consultants()
    all_consultants = []

    for team, members in consultants.items():
        all_consultants.extend(members)

    return sorted(all_consultants)

def get_consultants_by_team(team: str, json_path: str = DEFAULT_JSON_PATH) -> List[str]:
    """
    특정 팀의 상담사 목록을 가져옵니다. (DB 전환)

    Args:
        team: 팀 이름
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        List[str]: 해당 팀의 상담사 목록
    """
    consultants = load_consultants()
    return consultants.get(team, [])

def get_team_by_consultant(name: str, json_path: str = DEFAULT_JSON_PATH) -> Optional[str]:
    """
    상담사가 속한 팀 이름을 가져옵니다. (DB 전환)

    Args:
        name: 상담사 이름
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        Optional[str]: 팀 이름 또는 None (상담사가 없는 경우)
    """
    consultants = load_consultants()

    for team, members in consultants.items():
        if name in members:
            return team

    return None

def add_team(team_name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    새로운 팀을 추가합니다. (DB 전환)

    Args:
        team_name: 추가할 팀 이름
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        bool: 추가 성공 여부
    """
    # DB에서는 상담사 추가 시 자동으로 팀이 생성되므로 별도 처리 불필요
    return True

def remove_team(team_name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    팀을 제거합니다. (DB 전환 - 현재는 지원하지 않음)

    Args:
        team_name: 제거할 팀 이름
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        bool: 제거 성공 여부
    """
    # DB에서는 팀 삭제 기능을 지원하지 않음 (상담사가 없으면 자동으로 표시되지 않음)
    return False

def get_all_teams(json_path: str = DEFAULT_JSON_PATH) -> List[str]:
    """
    모든 팀 목록을 가져옵니다. (DB 전환)

    Args:
        json_path: 하위 호환성을 위한 파라미터 (더 이상 사용되지 않음)

    Returns:
        List[str]: 팀 이름 목록
    """
    consultants = load_consultants()
    return list(consultants.keys())