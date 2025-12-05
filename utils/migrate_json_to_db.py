"""
JSON 파일 데이터를 SQLite DB로 마이그레이션하는 스크립트

기존 JSON 파일들의 데이터를 읽어서 SQLite 데이터베이스로 이전합니다.
"""

import json
import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import get_db_manager


def migrate_targets():
    """targets.json 데이터를 DB로 마이그레이션"""
    print("📊 월별 목표 데이터 마이그레이션 시작...")

    targets_path = project_root / "targets.json"

    if not targets_path.exists():
        print(f"❌ {targets_path} 파일을 찾을 수 없습니다.")
        return False

    try:
        with open(targets_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        db = get_db_manager()

        # monthly_targets 딕셔너리 처리
        if 'monthly_targets' in data:
            monthly_targets = data['monthly_targets']
            for month_str, targets in monthly_targets.items():
                month = int(month_str)
                direct_target = targets['direct_target']
                affiliate_target = targets['affiliate_target']

                db.set_monthly_target(month, direct_target, affiliate_target)
                print(f"  ✅ {month}월 목표 저장: 직접={direct_target:,.0f}, 연계={affiliate_target:,.0f}")

        print("✅ 월별 목표 데이터 마이그레이션 완료!\n")
        return True

    except Exception as e:
        print(f"❌ 월별 목표 마이그레이션 오류: {str(e)}")
        return False


def migrate_consultants():
    """consultants.json 데이터를 DB로 마이그레이션"""
    print("👥 상담원 데이터 마이그레이션 시작...")

    consultants_path = project_root / "data" / "consultants.json"

    if not consultants_path.exists():
        print(f"❌ {consultants_path} 파일을 찾을 수 없습니다.")
        return False

    try:
        with open(consultants_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        db = get_db_manager()

        # 팀별 상담원 데이터 일괄 추가
        db.bulk_add_consultants(data)

        # 결과 출력
        for team, consultants in data.items():
            print(f"  ✅ {team}: {len(consultants)}명 저장")
            for consultant in consultants[:3]:  # 처음 3명만 출력
                print(f"     - {consultant}")
            if len(consultants) > 3:
                print(f"     ... 외 {len(consultants) - 3}명")

        print("✅ 상담원 데이터 마이그레이션 완료!\n")
        return True

    except Exception as e:
        print(f"❌ 상담원 마이그레이션 오류: {str(e)}")
        return False


def migrate_promotion_configs():
    """프로모션 설정 파일들을 DB로 마이그레이션"""
    print("🎁 프로모션 설정 데이터 마이그레이션 시작...")

    # 1. 메인 프로모션 설정 (data/promotion_config.json)
    main_config_path = project_root / "data" / "promotion_config.json"
    migrated_count = 0

    if main_config_path.exists():
        try:
            with open(main_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            db = get_db_manager()
            db.save_promotion_config("기본설정", data)
            print(f"  ✅ 기본설정 저장 완료")
            migrated_count += 1

        except Exception as e:
            print(f"  ❌ 기본설정 마이그레이션 오류: {str(e)}")

    # 2. 개별 프로모션 설정 파일들 (promotion_configs/*.json)
    configs_dir = project_root / "promotion_configs"

    if configs_dir.exists() and configs_dir.is_dir():
        json_files = list(configs_dir.glob("*.json"))

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 파일명에서 .json 제거하여 설정 이름으로 사용
                config_name = json_file.stem

                db = get_db_manager()
                db.save_promotion_config(config_name, data)
                print(f"  ✅ '{config_name}' 저장 완료")
                migrated_count += 1

            except Exception as e:
                print(f"  ❌ '{json_file.name}' 마이그레이션 오류: {str(e)}")

    if migrated_count > 0:
        print(f"✅ 프로모션 설정 데이터 마이그레이션 완료! (총 {migrated_count}개)\n")
        return True
    else:
        print("❌ 마이그레이션된 프로모션 설정이 없습니다.\n")
        return False


def verify_migration():
    """마이그레이션 결과 검증"""
    print("🔍 마이그레이션 결과 검증 중...\n")

    db = get_db_manager()

    # 1. 월별 목표 검증
    print("📊 월별 목표:")
    targets = db.get_all_monthly_targets()
    print(f"  총 {len(targets)}개월 데이터")
    if targets:
        # 1월 데이터 예시 출력
        jan_target = targets.get("1")
        if jan_target:
            print(f"  예) 1월: 직접={jan_target['direct_target']:,.0f}, 연계={jan_target['affiliate_target']:,.0f}")

    # 2. 상담원 검증
    print("\n👥 상담원:")
    consultants = db.get_consultants_by_team()
    total_consultants = sum(len(names) for names in consultants.values())
    print(f"  총 {total_consultants}명")
    for team, names in consultants.items():
        print(f"  {team}: {len(names)}명")

    # 3. 프로모션 설정 검증
    print("\n🎁 프로모션 설정:")
    configs = db.get_all_promotion_configs()
    print(f"  총 {len(configs)}개 설정")
    for config_name in configs[:5]:  # 처음 5개만 출력
        print(f"  - {config_name}")
    if len(configs) > 5:
        print(f"  ... 외 {len(configs) - 5}개")

    print("\n✅ 검증 완료!\n")


def create_backup():
    """JSON 파일들을 백업"""
    print("💾 JSON 파일 백업 중...")

    backup_dir = project_root / "json_backup"
    backup_dir.mkdir(exist_ok=True)

    files_to_backup = [
        project_root / "targets.json",
        project_root / "data" / "consultants.json",
        project_root / "data" / "promotion_config.json",
    ]

    # promotion_configs 디렉토리의 모든 JSON 파일도 백업
    configs_dir = project_root / "promotion_configs"
    if configs_dir.exists():
        files_to_backup.extend(configs_dir.glob("*.json"))

    backup_count = 0
    for file_path in files_to_backup:
        if file_path.exists():
            # 상대 경로 구조 유지
            relative_path = file_path.relative_to(project_root)
            backup_path = backup_dir / relative_path

            # 백업 디렉토리 생성
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 복사
            import shutil
            shutil.copy2(file_path, backup_path)
            print(f"  ✅ {relative_path} 백업 완료")
            backup_count += 1

    print(f"✅ 총 {backup_count}개 파일 백업 완료!\n")


def main():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("JSON → SQLite 데이터 마이그레이션 시작")
    print("=" * 60)
    print()

    # 1. 백업 생성
    create_backup()

    # 2. 마이그레이션 실행
    results = {
        "월별 목표": migrate_targets(),
        "상담원": migrate_consultants(),
        "프로모션 설정": migrate_promotion_configs(),
    }

    # 3. 결과 검증
    verify_migration()

    # 4. 최종 결과 출력
    print("=" * 60)
    print("마이그레이션 결과")
    print("=" * 60)
    for name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{name}: {status}")

    all_success = all(results.values())
    print()
    if all_success:
        print("🎉 모든 데이터 마이그레이션이 성공적으로 완료되었습니다!")
        print()
        print("ℹ️  다음 단계:")
        print("   1. 애플리케이션 코드를 DB 사용 방식으로 업데이트")
        print("   2. 테스트 후 json_backup 폴더 확인")
        print("   3. 문제 없으면 기존 JSON 파일 삭제 가능")
    else:
        print("⚠️  일부 마이그레이션이 실패했습니다. 로그를 확인해주세요.")

    print("=" * 60)


if __name__ == "__main__":
    main()
