"""
상담사 관리 모듈

이 모듈은 상담사 목록을 JSON 파일로 관리하는 기능을 제공합니다.
"""

import os
import json
from typing import Dict, List, Optional

# 기본 JSON 파일 경로
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "consultants.json")

def load_consultants(json_path: str = DEFAULT_JSON_PATH) -> Dict[str, List[str]]:
    """
    JSON 파일에서 상담사 목록을 로드합니다.
    
    Args:
        json_path: 상담사 JSON 파일 경로
        
    Returns:
        Dict[str, List[str]]: 팀별 상담사 목록
    """
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 기본 상담사 목록 반환
            return {
                "CRM팀": [
                    "임명숙", "김미정", "양희정", "장희경", "김태희", 
                    "전향봉", "조경애", "유태경", "이연석", "황선애", 
                    "신순옥", "경도형", "주성덕", "왕은경", "정진경", 
                    "이지영", "정문희", "천대영", "유선희", "이승현", 
                    "안주연", "김보경", "김원영"
                ],
                "온라인팀": ["김부자", "최진영"]
            }
    except Exception as e:
        print(f"상담사 목록 로드 중 오류: {str(e)}")
        # 오류 시 빈 목록 반환
        return {"CRM팀": [], "온라인팀": []}

def save_consultants(consultants: Dict[str, List[str]], json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    상담사 목록을 JSON 파일로 저장합니다.
    
    Args:
        consultants: 팀별 상담사 목록
        json_path: 저장할 JSON 파일 경로
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        # 디렉터리가 없으면 생성
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(consultants, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"상담사 목록 저장 중 오류: {str(e)}")
        return False

def add_consultant(team: str, name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    상담사를 추가합니다.
    
    Args:
        team: 팀 이름
        name: 상담사 이름
        json_path: JSON 파일 경로
        
    Returns:
        bool: 추가 성공 여부
    """
    consultants = load_consultants(json_path)
    
    # 팀이 없으면 생성
    if team not in consultants:
        consultants[team] = []
    
    # 이미 존재하는지 확인
    if name in consultants[team]:
        return False
    
    consultants[team].append(name)
    return save_consultants(consultants, json_path)

def remove_consultant(team: str, name: str, json_path: str = DEFAULT_JSON_PATH) -> bool:
    """
    상담사를 제거합니다.
    
    Args:
        team: 팀 이름
        name: 상담사 이름
        json_path: JSON 파일 경로
        
    Returns:
        bool: 제거 성공 여부
    """
    consultants = load_consultants(json_path)
    
    # 팀이 없으면 실패
    if team not in consultants:
        return False
    
    # 상담사가 없으면 실패
    if name not in consultants[team]:
        return False
    
    consultants[team].remove(name)
    return save_consultants(consultants, json_path)

def get_all_consultants(json_path: str = DEFAULT_JSON_PATH) -> List[str]:
    """
    모든 상담사 목록을 가져옵니다.
    
    Args:
        json_path: JSON 파일 경로
        
    Returns:
        List[str]: 모든 상담사 목록
    """
    consultants = load_consultants(json_path)
    all_consultants = []
    
    for team, members in consultants.items():
        all_consultants.extend(members)
    
    return sorted(all_consultants)

def get_consultants_by_team(team: str, json_path: str = DEFAULT_JSON_PATH) -> List[str]:
    """
    특정 팀의 상담사 목록을 가져옵니다.
    
    Args:
        team: 팀 이름
        json_path: JSON 파일 경로
        
    Returns:
        List[str]: 해당 팀의 상담사 목록
    """
    consultants = load_consultants(json_path)
    return consultants.get(team, [])

def get_team_by_consultant(name: str, json_path: str = DEFAULT_JSON_PATH) -> Optional[str]:
    """
    상담사가 속한 팀 이름을 가져옵니다.
    
    Args:
        name: 상담사 이름
        json_path: JSON 파일 경로
        
    Returns:
        Optional[str]: 팀 이름 또는 None (상담사가 없는 경우)
    """
    consultants = load_consultants(json_path)
    
    for team, members in consultants.items():
        if name in members:
            return team
    
    return None