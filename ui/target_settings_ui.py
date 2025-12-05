"""
CRM 목표 설정 UI 모듈

월별 매출 목표를 관리하는 UI를 제공합니다.
- 연도별 목표 조회 및 수정
- 12개월 목표 일괄 입력
- CSV/Excel 가져오기/내보내기
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict
import io

from utils.db_manager import get_db_manager


def show():
    """CRM 목표 설정 탭 UI를 표시하는 메인 함수"""

    st.title("🎯 CRM 목표 설정")
    st.markdown("월별 매출 목표를 조회하고 설정할 수 있습니다.")

    # CSS 스타일
    st.markdown("""
        <style>
        .target-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .month-header {
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 10px;
        }
        .target-summary {
            background: #f0f8ff;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)

    db = get_db_manager()

    # 연도 선택
    available_years = db.get_available_years()
    current_year = datetime.now().year

    # 사용 가능한 연도가 없으면 현재 연도 추가
    if not available_years:
        available_years = [current_year]
    elif current_year not in available_years:
        available_years = [current_year] + available_years

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📊 목표 조회/수정", "📝 일괄 입력", "📤 가져오기/내보내기"])

    # ========== 탭 1: 목표 조회/수정 ==========
    with tab1:
        st.markdown('<div class="target-card">', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 3])
        with col1:
            selected_year = st.selectbox(
                "연도 선택",
                options=available_years,
                index=0,
                key="view_year_select"
            )

        st.markdown(f"### {selected_year}년 월별 목표")

        # 현재 연도의 목표 조회
        targets = db.get_all_monthly_targets(selected_year)

        # 목표가 없으면 기본값 설정
        if not targets:
            st.info(f"{selected_year}년 목표 데이터가 없습니다. 아래에서 입력하세요.")
            targets = {str(i): {'direct_target': 0, 'affiliate_target': 0} for i in range(1, 13)}

        # 월별 목표 표시 및 수정
        modified = False
        new_targets = {}

        # 3개월씩 나눠서 표시
        for quarter in range(4):
            start_month = quarter * 3 + 1
            end_month = start_month + 3

            st.markdown(f"#### {start_month}월 ~ {end_month-1}월")

            cols = st.columns(3)
            for i, month in enumerate(range(start_month, end_month)):
                with cols[i]:
                    st.markdown(f'<div class="month-header">{month}월</div>', unsafe_allow_html=True)

                    month_str = str(month)
                    current_target = targets.get(month_str, {'direct_target': 0, 'affiliate_target': 0})

                    direct = st.number_input(
                        "직접 목표 (원)",
                        min_value=0,
                        value=int(current_target['direct_target']),
                        step=1000000,
                        key=f"direct_{selected_year}_{month}",
                        format="%d"
                    )

                    affiliate = st.number_input(
                        "연계 목표 (원)",
                        min_value=0,
                        value=int(current_target['affiliate_target']),
                        step=1000000,
                        key=f"affiliate_{selected_year}_{month}",
                        format="%d"
                    )

                    new_targets[month] = {
                        'direct_target': direct,
                        'affiliate_target': affiliate
                    }

                    # 변경 여부 체크
                    if (direct != current_target['direct_target'] or
                        affiliate != current_target['affiliate_target']):
                        modified = True

            st.markdown("---")

        # 요약 정보
        total_direct = sum(t['direct_target'] for t in new_targets.values())
        total_affiliate = sum(t['affiliate_target'] for t in new_targets.values())

        st.markdown(f"""
            <div class="target-summary">
                <h4>📈 {selected_year}년 연간 목표 합계</h4>
                <p>직접 목표: <strong>{total_direct:,.0f}</strong> 원</p>
                <p>연계 목표: <strong>{total_affiliate:,.0f}</strong> 원</p>
                <p>총 목표: <strong>{total_direct + total_affiliate:,.0f}</strong> 원</p>
            </div>
        """, unsafe_allow_html=True)

        # 저장 버튼
        if st.button("💾 목표 저장", key="save_all_targets", type="primary"):
            try:
                db.bulk_set_monthly_targets(new_targets, selected_year)
                st.success(f"✅ {selected_year}년 목표가 저장되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 저장 실패: {str(e)}")

        st.markdown('</div>', unsafe_allow_html=True)

    # ========== 탭 2: 일괄 입력 ==========
    with tab2:
        st.markdown('<div class="target-card">', unsafe_allow_html=True)
        st.subheader("📝 월별 목표 일괄 입력")

        bulk_year = st.selectbox(
            "연도 선택",
            options=available_years,
            index=0,
            key="bulk_year_select"
        )

        st.markdown("**직접 목표 (백만 원 단위)**")
        direct_input = st.text_area(
            "1월부터 12월까지 쉼표(,)로 구분하여 입력",
            placeholder="예: 630, 624, 648, 630, 757, 609, 576, 603, 681, 671, 612, 599",
            key="bulk_direct_input",
            height=100
        )

        st.markdown("**연계 목표 (백만 원 단위)**")
        affiliate_input = st.text_area(
            "1월부터 12월까지 쉼표(,)로 구분하여 입력",
            placeholder="예: 483, 458, 463, 434, 585, 409, 366, 421, 527, 526, 451, 435",
            key="bulk_affiliate_input",
            height=100
        )

        if st.button("📊 미리보기", key="preview_bulk"):
            try:
                direct_values = [float(x.strip()) * 1000000 for x in direct_input.split(',')]
                affiliate_values = [float(x.strip()) * 1000000 for x in affiliate_input.split(',')]

                if len(direct_values) != 12 or len(affiliate_values) != 12:
                    st.error("각각 12개월 데이터를 입력해야 합니다.")
                else:
                    # 미리보기 테이블
                    preview_data = {
                        '월': [f"{i}월" for i in range(1, 13)],
                        '직접 목표': [f"{v:,.0f}" for v in direct_values],
                        '연계 목표': [f"{v:,.0f}" for v in affiliate_values],
                        '합계': [f"{d + a:,.0f}" for d, a in zip(direct_values, affiliate_values)]
                    }
                    preview_df = pd.DataFrame(preview_data)
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

                    # 저장 버튼
                    if st.button("💾 일괄 저장", key="save_bulk_targets", type="primary"):
                        bulk_targets = {}
                        for month in range(1, 13):
                            bulk_targets[month] = {
                                'direct_target': direct_values[month-1],
                                'affiliate_target': affiliate_values[month-1]
                            }

                        db.bulk_set_monthly_targets(bulk_targets, bulk_year)
                        st.success(f"✅ {bulk_year}년 목표가 일괄 저장되었습니다!")
                        st.rerun()

            except Exception as e:
                st.error(f"❌ 입력 형식 오류: {str(e)}")

        st.markdown('</div>', unsafe_allow_html=True)

    # ========== 탭 3: 가져오기/내보내기 ==========
    with tab3:
        st.markdown('<div class="target-card">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        # 내보내기
        with col1:
            st.subheader("📤 목표 내보내기 (Excel)")

            export_year = st.selectbox(
                "연도 선택",
                options=available_years,
                index=0,
                key="export_year_select"
            )

            if st.button("📥 Excel 다운로드", key="export_excel"):
                targets = db.get_all_monthly_targets(export_year)

                if targets:
                    # DataFrame 생성
                    export_data = []
                    for month in range(1, 13):
                        month_str = str(month)
                        target = targets.get(month_str, {'direct_target': 0, 'affiliate_target': 0})
                        export_data.append({
                            '연도': export_year,
                            '월': month,
                            '직접목표': target['direct_target'],
                            '연계목표': target['affiliate_target'],
                            '합계': target['direct_target'] + target['affiliate_target']
                        })

                    df = pd.DataFrame(export_data)

                    # Excel 파일 생성
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='월별목표')

                    excel_data = output.getvalue()

                    st.download_button(
                        label="💾 다운로드",
                        data=excel_data,
                        file_name=f"CRM목표_{export_year}년.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning(f"{export_year}년 목표 데이터가 없습니다.")

        # 가져오기
        with col2:
            st.subheader("📥 목표 가져오기 (Excel)")

            uploaded_file = st.file_uploader(
                "Excel 파일 선택",
                type=['xlsx', 'xls'],
                key="import_excel_file"
            )

            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)

                    # 필수 컬럼 확인
                    required_cols = ['연도', '월', '직접목표', '연계목표']
                    if all(col in df.columns for col in required_cols):
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        if st.button("📥 가져오기", key="import_confirm"):
                            # 연도별로 그룹화
                            for year in df['연도'].unique():
                                year_data = df[df['연도'] == year]
                                import_targets = {}

                                for _, row in year_data.iterrows():
                                    month = int(row['월'])
                                    import_targets[month] = {
                                        'direct_target': float(row['직접목표']),
                                        'affiliate_target': float(row['연계목표'])
                                    }

                                db.bulk_set_monthly_targets(import_targets, int(year))

                            st.success("✅ 목표 데이터를 가져왔습니다!")
                            st.rerun()
                    else:
                        st.error(f"필수 컬럼이 없습니다: {required_cols}")

                except Exception as e:
                    st.error(f"❌ 파일 읽기 오류: {str(e)}")

        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    show()
