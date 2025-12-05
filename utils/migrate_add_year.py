"""
monthly_targets 테이블에 year 컬럼 추가 마이그레이션

기존 데이터는 2025년으로 설정
"""

import sqlite3
from pathlib import Path

def migrate_add_year_column():
    """year 컬럼 추가 및 기존 데이터 업데이트"""

    db_path = Path(__file__).parent.parent / "crm_data.db"

    print("=" * 60)
    print("monthly_targets 테이블 마이그레이션 시작")
    print("=" * 60)
    print()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. year 컬럼 추가
        print("📝 year 컬럼 추가 중...")
        try:
            cursor.execute("""
                ALTER TABLE monthly_targets
                ADD COLUMN year INTEGER NOT NULL DEFAULT 2025
            """)
            print("  ✅ year 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("  ℹ️  year 컬럼이 이미 존재합니다.")
            else:
                raise

        # 2. 기존 UNIQUE 제약 조건 확인
        cursor.execute("""
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='monthly_targets'
        """)
        table_sql = cursor.fetchone()[0]
        print(f"\n현재 테이블 구조:\n{table_sql}\n")

        # 3. 새 테이블 생성 (year + month를 UNIQUE로)
        print("📝 새 테이블 구조로 마이그레이션 중...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_targets_new (
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

        # 4. 기존 데이터 복사
        print("📝 기존 데이터 복사 중...")
        cursor.execute("""
            INSERT INTO monthly_targets_new (year, month, direct_target, affiliate_target, created_at, updated_at)
            SELECT
                COALESCE(year, 2025) as year,
                month,
                direct_target,
                affiliate_target,
                created_at,
                updated_at
            FROM monthly_targets
        """)

        row_count = cursor.rowcount
        print(f"  ✅ {row_count}개 데이터 복사 완료")

        # 5. 기존 테이블 삭제 및 이름 변경
        print("📝 테이블 교체 중...")
        cursor.execute("DROP TABLE monthly_targets")
        cursor.execute("ALTER TABLE monthly_targets_new RENAME TO monthly_targets")
        print("  ✅ 테이블 교체 완료")

        # 6. 인덱스 생성
        print("📝 인덱스 생성 중...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monthly_targets_year_month
            ON monthly_targets(year, month)
        """)
        print("  ✅ 인덱스 생성 완료")

        conn.commit()

        # 7. 결과 확인
        print("\n🔍 마이그레이션 결과 확인:")
        cursor.execute("""
            SELECT year, month, direct_target, affiliate_target
            FROM monthly_targets
            ORDER BY year, month
        """)

        rows = cursor.fetchall()
        print(f"  총 {len(rows)}개 데이터")
        print("\n  최근 3개월 데이터:")
        for row in rows[-3:]:
            year, month, direct, affiliate = row
            print(f"    {year}년 {month}월: 직접={direct:,.0f}, 연계={affiliate:,.0f}")

        conn.close()

        print("\n" + "=" * 60)
        print("✅ 마이그레이션 완료!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    migrate_add_year_column()
