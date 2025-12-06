"""
SQLite 데이터베이스 관리 모듈

기존 JSON 파일들을 SQLite DB로 전환하여 관리합니다.
- 월별 매출 목표 (targets.json)
- 상담원 정보 (consultants.json)
- 프로모션 설정 (promotion_config.json, promotion_configs/*.json)
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager


class DatabaseManager:
    """SQLite 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "crm_data.db"):
        """
        데이터베이스 관리자 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """
        데이터베이스 연결을 컨텍스트 매니저로 제공

        Yields:
            sqlite3.Connection: 데이터베이스 연결 객체
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리처럼 접근 가능
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_database(self):
        """데이터베이스 테이블 초기화"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. 월별 매출 목표 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monthly_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    direct_target REAL NOT NULL,
                    affiliate_target REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, month)
                )
            """)

            # 2. 상담원 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    team TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. 프로모션 설정 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promotion_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    config_data TEXT NOT NULL,
                    last_updated TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. 프로모션 제품 가중치 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    weight INTEGER NOT NULL,
                    FOREIGN KEY (config_id) REFERENCES promotion_configs(id) ON DELETE CASCADE,
                    UNIQUE(config_id, product_name)
                )
            """)

            # 5. 프로모션 등급 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promotion_tiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER NOT NULL,
                    tier_name TEXT NOT NULL,
                    min_score INTEGER,
                    max_score INTEGER,
                    tier_order INTEGER NOT NULL,
                    FOREIGN KEY (config_id) REFERENCES promotion_configs(id) ON DELETE CASCADE
                )
            """)

            # 6. 공휴일 캐시 테이블 (API 결과 영구 저장)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holidays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    holiday_date TEXT NOT NULL,
                    holiday_name TEXT,
                    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, month, holiday_date)
                )
            """)

            # 7. 공휴일 API 호출 기록 테이블 (주 1회 제한용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holiday_api_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    last_fetched TEXT NOT NULL,
                    success INTEGER DEFAULT 1,
                    UNIQUE(year, month)
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_holidays_year_month
                ON holidays(year, month)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_consultants_team
                ON consultants(team)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_consultants_active
                ON consultants(is_active)
            """)

            conn.commit()

    # ==================== 월별 목표 관련 메서드 ====================

    def get_monthly_target(self, month: int, year: int = None) -> Optional[Dict[str, float]]:
        """
        특정 연월의 목표 조회

        Args:
            month: 조회할 월 (1-12)
            year: 조회할 연도 (None이면 현재 연도)

        Returns:
            Dict: {direct_target, affiliate_target} 또는 None
        """
        if year is None:
            from datetime import datetime
            year = datetime.now().year

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT direct_target, affiliate_target
                FROM monthly_targets
                WHERE year = ? AND month = ?
            """, (year, month))

            row = cursor.fetchone()
            if row:
                return {
                    'direct_target': row['direct_target'],
                    'affiliate_target': row['affiliate_target']
                }
            return None

    def set_monthly_target(self, month: int, direct_target: float, affiliate_target: float, year: int = None):
        """
        월별 목표 설정 (업데이트 또는 삽입)

        Args:
            month: 월 (1-12)
            direct_target: 직접 목표 매출
            affiliate_target: 연계 목표 매출
            year: 연도 (None이면 현재 연도)
        """
        if year is None:
            from datetime import datetime
            year = datetime.now().year

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO monthly_targets (year, month, direct_target, affiliate_target, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(year, month) DO UPDATE SET
                    direct_target = excluded.direct_target,
                    affiliate_target = excluded.affiliate_target,
                    updated_at = CURRENT_TIMESTAMP
            """, (year, month, direct_target, affiliate_target))

    def get_all_monthly_targets(self, year: int = None) -> Dict[str, Dict[str, float]]:
        """
        특정 연도의 모든 월별 목표 조회

        Args:
            year: 조회할 연도 (None이면 현재 연도)

        Returns:
            Dict: {"1": {direct_target, affiliate_target}, "2": {...}, ...}
        """
        if year is None:
            from datetime import datetime
            year = datetime.now().year

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT month, direct_target, affiliate_target
                FROM monthly_targets
                WHERE year = ?
                ORDER BY month
            """, (year,))

            result = {}
            for row in cursor.fetchall():
                result[str(row['month'])] = {
                    'direct_target': row['direct_target'],
                    'affiliate_target': row['affiliate_target']
                }
            return result

    def get_available_years(self) -> List[int]:
        """
        목표 데이터가 있는 연도 목록 조회

        Returns:
            List[int]: 연도 목록 (내림차순)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT year
                FROM monthly_targets
                ORDER BY year DESC
            """)

            return [row['year'] for row in cursor.fetchall()]

    def bulk_set_monthly_targets(self, targets: Dict[int, Dict[str, float]], year: int = None):
        """
        여러 월의 목표를 한 번에 설정

        Args:
            targets: {month: {direct_target, affiliate_target}, ...}
            year: 연도 (None이면 현재 연도)
        """
        if year is None:
            from datetime import datetime
            year = datetime.now().year

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for month, target_data in targets.items():
                cursor.execute("""
                    INSERT INTO monthly_targets (year, month, direct_target, affiliate_target, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(year, month) DO UPDATE SET
                        direct_target = excluded.direct_target,
                        affiliate_target = excluded.affiliate_target,
                        updated_at = CURRENT_TIMESTAMP
                """, (year, month, target_data['direct_target'], target_data['affiliate_target']))

    # ==================== 상담원 관련 메서드 ====================

    def get_consultants_by_team(self, team: str = None) -> Dict[str, List[str]]:
        """
        팀별 상담원 목록 조회

        Args:
            team: 팀 이름 (None이면 전체 조회)

        Returns:
            Dict: {"CRM팀": ["이름1", "이름2"], "온라인팀": [...]}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if team:
                cursor.execute("""
                    SELECT name, team
                    FROM consultants
                    WHERE team = ? AND is_active = 1
                    ORDER BY name
                """, (team,))
            else:
                cursor.execute("""
                    SELECT name, team
                    FROM consultants
                    WHERE is_active = 1
                    ORDER BY team, name
                """)

            result = {}
            for row in cursor.fetchall():
                team_name = row['team']
                if team_name not in result:
                    result[team_name] = []
                result[team_name].append(row['name'])

            return result

    def add_consultant(self, name: str, team: str):
        """
        상담원 추가

        Args:
            name: 상담원 이름
            team: 팀 이름
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO consultants (name, team, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    team = excluded.team,
                    is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (name, team))

    def remove_consultant(self, name: str):
        """
        상담원 비활성화 (삭제하지 않고 is_active를 0으로 설정)

        Args:
            name: 상담원 이름
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE consultants
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (name,))

    def bulk_add_consultants(self, consultants_dict: Dict[str, List[str]]):
        """
        상담원 일괄 추가

        Args:
            consultants_dict: {"팀명": ["이름1", "이름2", ...]}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for team, names in consultants_dict.items():
                for name in names:
                    cursor.execute("""
                        INSERT INTO consultants (name, team, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(name) DO UPDATE SET
                            team = excluded.team,
                            is_active = 1,
                            updated_at = CURRENT_TIMESTAMP
                    """, (name, team))

    # ==================== 프로모션 설정 관련 메서드 ====================

    def save_promotion_config(self, name: str, config_data: Dict[str, Any]):
        """
        프로모션 설정 저장

        Args:
            name: 프로모션 설정 이름
            config_data: 설정 데이터 (딕셔너리)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # JSON 문자열로 변환
            config_json = json.dumps(config_data, ensure_ascii=False, indent=2)
            last_updated = config_data.get('last_updated', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            cursor.execute("""
                INSERT INTO promotion_configs (name, config_data, last_updated, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    config_data = excluded.config_data,
                    last_updated = excluded.last_updated,
                    updated_at = CURRENT_TIMESTAMP
            """, (name, config_json, last_updated))

    def get_promotion_config(self, name: str) -> Optional[Dict[str, Any]]:
        """
        프로모션 설정 조회

        Args:
            name: 프로모션 설정 이름

        Returns:
            Dict: 설정 데이터 또는 None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config_data
                FROM promotion_configs
                WHERE name = ?
            """, (name,))

            row = cursor.fetchone()
            if row:
                return json.loads(row['config_data'])
            return None

    def get_all_promotion_configs(self) -> List[str]:
        """
        모든 프로모션 설정 이름 목록 조회

        Returns:
            List[str]: 프로모션 설정 이름 목록
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name
                FROM promotion_configs
                ORDER BY updated_at DESC
            """)

            return [row['name'] for row in cursor.fetchall()]

    def delete_promotion_config(self, name: str):
        """
        프로모션 설정 삭제

        Args:
            name: 프로모션 설정 이름
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM promotion_configs
                WHERE name = ?
            """, (name,))

    # ==================== 공휴일 캐시 관련 메서드 ====================

    def get_holidays_for_month(self, year: int, month: int) -> Optional[set]:
        """
        특정 연월의 공휴일 목록을 DB에서 조회

        Args:
            year: 연도
            month: 월

        Returns:
            set: 공휴일 날짜 set (datetime.date) 또는 None (캐시 없음)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 먼저 API 호출 기록 확인 (캐시가 있는지)
            cursor.execute("""
                SELECT last_fetched, success
                FROM holiday_api_log
                WHERE year = ? AND month = ?
            """, (year, month))

            log_row = cursor.fetchone()
            if log_row is None:
                return None  # 캐시 없음

            # 공휴일 목록 조회
            cursor.execute("""
                SELECT holiday_date
                FROM holidays
                WHERE year = ? AND month = ?
            """, (year, month))

            holidays = set()
            for row in cursor.fetchall():
                try:
                    holiday_date = datetime.strptime(row['holiday_date'], '%Y-%m-%d').date()
                    holidays.add(holiday_date)
                except ValueError:
                    pass

            return holidays

    def should_refresh_holidays(self, year: int, month: int, days_interval: int = 7) -> bool:
        """
        공휴일 캐시를 갱신해야 하는지 확인 (주 1회)

        Args:
            year: 연도
            month: 월
            days_interval: 갱신 주기 (일)

        Returns:
            bool: 갱신 필요 여부
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_fetched
                FROM holiday_api_log
                WHERE year = ? AND month = ?
            """, (year, month))

            row = cursor.fetchone()
            if row is None:
                return True  # 기록 없음 = 갱신 필요

            try:
                last_fetched = datetime.strptime(row['last_fetched'], '%Y-%m-%d %H:%M:%S')
                days_since = (datetime.now() - last_fetched).days
                return days_since >= days_interval
            except ValueError:
                return True

    def save_holidays(self, year: int, month: int, holidays: List[Tuple[str, str]], success: bool = True):
        """
        공휴일 목록을 DB에 저장

        Args:
            year: 연도
            month: 월
            holidays: [(날짜문자열, 공휴일명), ...] 형태의 리스트
            success: API 호출 성공 여부
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 기존 공휴일 데이터 삭제 (갱신용)
            cursor.execute("""
                DELETE FROM holidays
                WHERE year = ? AND month = ?
            """, (year, month))

            # 공휴일 저장
            for holiday_date, holiday_name in holidays:
                cursor.execute("""
                    INSERT OR REPLACE INTO holidays (year, month, holiday_date, holiday_name, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (year, month, holiday_date, holiday_name, now))

            # API 호출 기록 저장
            cursor.execute("""
                INSERT INTO holiday_api_log (year, month, last_fetched, success)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(year, month) DO UPDATE SET
                    last_fetched = excluded.last_fetched,
                    success = excluded.success
            """, (year, month, now, 1 if success else 0))

    def is_api_failed_recently(self, year: int, month: int, hours: int = 24) -> bool:
        """
        최근 API 호출이 실패했는지 확인 (재시도 방지)

        Args:
            year: 연도
            month: 월
            hours: 재시도 방지 시간 (시간)

        Returns:
            bool: 최근 실패 여부
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_fetched, success
                FROM holiday_api_log
                WHERE year = ? AND month = ? AND success = 0
            """, (year, month))

            row = cursor.fetchone()
            if row is None:
                return False

            try:
                last_fetched = datetime.strptime(row['last_fetched'], '%Y-%m-%d %H:%M:%S')
                hours_since = (datetime.now() - last_fetched).total_seconds() / 3600
                return hours_since < hours
            except ValueError:
                return False


# 전역 데이터베이스 매니저 인스턴스
_db_manager = None


def get_db_manager(db_path: str = "crm_data.db") -> DatabaseManager:
    """
    데이터베이스 매니저 싱글톤 인스턴스 반환

    Args:
        db_path: 데이터베이스 파일 경로

    Returns:
        DatabaseManager: 데이터베이스 매니저 인스턴스
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
