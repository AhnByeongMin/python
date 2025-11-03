"""
상담사 프로모션 현황 UI 모듈 (리뉴얼)

이 모듈은 리뉴얼된 상담사 프로모션 현황 탭의 UI를 제공합니다.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Dict, List

# 로직 및 설정 관리 가져오기
from logic.promotion_logic import process_promotion_file, analyze_promotion_data_new, create_promotion_excel
from utils.promotion_config_manager import save_config, load_config, reset_config, get_default_config
import base64


def style_promotion_table(df: pd.DataFrame, analysis_mode: str) -> pd.DataFrame:
    """
    프로모션 결과 테이블에 스타일링 적용

    Args:
        df: 분석 결과 데이터프레임
        analysis_mode: 분석 모드 ("제품별", "건수별", "금액별")

    Returns:
        스타일이 적용된 Styler 객체
    """
    def rank_gradient_color(val, max_rank):
        """순위에 따른 그라데이션 색상 (초록→노랑→빨강)"""
        if pd.isna(val):
            return ''
        try:
            rank = int(val)
            # 전체 순위 수에 따라 비율 계산 (1등=0.0, 꼴등=1.0)
            if max_rank <= 1:
                ratio = 0
            else:
                ratio = (rank - 1) / (max_rank - 1)

            # 초록(0) → 노랑(0.5) → 빨강(1.0) 그라데이션
            if ratio <= 0.5:
                # 초록 → 노랑
                r = int(144 + (255 - 144) * (ratio * 2))
                g = int(238 - (238 - 235) * (ratio * 2))
                b = int(144 - 144 * (ratio * 2))
            else:
                # 노랑 → 빨강
                r = 255
                g = int(235 - 235 * ((ratio - 0.5) * 2))
                b = 0

            bg_color = f'#{r:02x}{g:02x}{b:02x}'

            # 상위권은 진한 글자, 하위권은 흰 글자
            font_color = '#000000' if ratio < 0.7 else '#FFFFFF'
            font_weight = 'bold' if rank <= 3 else 'normal'

            return f'background-color: {bg_color}; font-weight: {font_weight}; color: {font_color}'
        except:
            return ''

    def tier_color(val):
        """등급에 따른 색상 (제품별 분석용)"""
        if pd.isna(val):
            return ''
        val_str = str(val)
        if '1등급' in val_str:
            return 'background-color: #764ba2; font-weight: bold; color: white'  # 진한 보라
        elif '2등급' in val_str:
            return 'background-color: #f5576c; font-weight: bold; color: white'  # 핑크
        elif '3등급' in val_str:
            return 'background-color: #00f2fe; font-weight: bold; color: white'  # 시안
        else:
            return 'background-color: #f8f9fa; color: #6c757d'  # 연한 회색

    def yn_color(val):
        """Y/N에 따른 색상"""
        if pd.isna(val):
            return ''
        val_str = str(val).upper()
        if val_str == 'Y':
            return 'background-color: #38ef7d; font-weight: bold; color: white'  # 밝은 초록
        elif val_str == 'N':
            return 'background-color: #ff6a00; font-weight: bold; color: white'  # 오렌지
        else:
            return ''

    # 스타일 적용 함수 정의
    def apply_styles(row):
        styles = [''] * len(row)

        # 순위 그라데이션 (모든 모드 공통)
        if '순위' in df.columns:
            rank_idx = df.columns.get_loc('순위')
            max_rank = df['순위'].max()
            styles[rank_idx] = rank_gradient_color(row.iloc[rank_idx], max_rank)

        # 프로모션등급 색상 (제품별)
        if analysis_mode == '제품별' and '프로모션등급' in df.columns:
            tier_idx = df.columns.get_loc('프로모션등급')
            styles[tier_idx] = tier_color(row.iloc[tier_idx])

        # 프로모션대상 Y/N 색상 (건수별/금액별)
        if analysis_mode != '제품별' and '프로모션대상' in df.columns:
            yn_idx = df.columns.get_loc('프로모션대상')
            styles[yn_idx] = yn_color(row.iloc[yn_idx])

        return styles

    # 스타일 적용
    styler = df.style.apply(apply_styles, axis=1)

    # 숫자 컬럼 포맷팅
    number_cols = ['누적승인(건)', '누적승인(액)', '제품점수', '추첨권', '포상금']
    for col in number_cols:
        if col in df.columns:
            if '(액)' in col or '포상금' in col:
                styler = styler.format({col: '₩{:,.0f}'})
            else:
                styler = styler.format({col: '{:,.0f}'})

    # 전체 테이블 스타일 추가 (테두리, 간격)
    styler = styler.set_table_styles([
        # 모든 셀에 테두리
        {'selector': 'td, th',
         'props': [('border', '1px solid #ddd'),
                   ('padding', '8px'),
                   ('text-align', 'center')]},
        # 헤더 스타일
        {'selector': 'th',
         'props': [('background-color', '#4472C4'),
                   ('color', 'white'),
                   ('font-weight', 'bold'),
                   ('border', '1px solid #2d5a9e')]},
        # 테이블 전체
        {'selector': 'table',
         'props': [('border-collapse', 'collapse'),
                   ('width', '100%'),
                   ('font-size', '14px')]},
        # 행 hover 효과
        {'selector': 'tbody tr:hover',
         'props': [('background-color', '#f5f5f5')]}
    ])

    return styler


def show():
    """상담사 프로모션 진행현황 탭 메인 함수"""

    st.title("🏆 상담사 프로모션 진행현황")
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <p style='margin: 0; color: #333;'>
        📊 상담사별 프로모션 현황을 분석합니다.<br>
        💡 <b>제품별</b>: 가중치 기반 점수 → 등급별 색상 구분 |
        <b>건수별/금액별</b>: 순위 기반 → 그라데이션 색상 표시
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 세션 상태 초기화
    if "promo_config" not in st.session_state:
        config, error = load_config()
        if error:
            st.warning(error)
        st.session_state.promo_config = config

    if "promo_df" not in st.session_state:
        st.session_state.promo_df = None

    if "promo_results" not in st.session_state:
        st.session_state.promo_results = None

    if "promo_filtered_df" not in st.session_state:
        st.session_state.promo_filtered_df = None

    # 설정 가져오기
    config = st.session_state.promo_config

    # === 파일 업로드 ===
    st.markdown("### 📁 1단계: 데이터 업로드")

    uploaded_file = st.file_uploader(
        "상담주문내역 엑셀 파일을 업로드하세요",
        type=['xlsx', 'xls'],
        key="promo_file_upload",
        help="엑셀 파일의 3행에 헤더가 있어야 합니다."
    )

    if uploaded_file:
        with st.spinner("🔄 파일 처리 중..."):
            df, error = process_promotion_file(uploaded_file)
            if error:
                st.error(f"❌ {error}")
            else:
                st.session_state.promo_df = df
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 레코드", f"{len(df):,}개")
                with col2:
                    if "주문 일자" in df.columns:
                        min_date = df["주문 일자"].min()
                        st.metric("시작일", min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else "N/A")
                with col3:
                    if "주문 일자" in df.columns:
                        max_date = df["주문 일자"].max()
                        st.metric("종료일", max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else "N/A")

                # 날짜 범위 자동 설정
                if "주문 일자" in df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(df["주문 일자"]):
                        df["주문 일자"] = pd.to_datetime(df["주문 일자"], errors='coerce')
                    valid_dates = df["주문 일자"].dropna()
                    if not valid_dates.empty:
                        min_date = valid_dates.min().date()
                        max_date = valid_dates.max().date()
                        if "date_range" not in config or not config["date_range"].get("start_date"):
                            config["date_range"]["start_date"] = str(min_date)
                            config["date_range"]["end_date"] = str(max_date)

    st.divider()

    # === 분석 설정 ===
    st.markdown("### ⚙️ 2단계: 분석 조건 설정")

    # 날짜 범위와 분석 기준을 한 행에
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**📅 분석 기간**")
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            start_date_str = config["date_range"].get("start_date")
            start_date = date.fromisoformat(start_date_str) if start_date_str else date.today()
            start_date = st.date_input("시작일", value=start_date, key="start_date_input", label_visibility="collapsed")
        with subcol2:
            end_date_str = config["date_range"].get("end_date")
            end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()
            end_date = st.date_input("종료일", value=end_date, key="end_date_input", label_visibility="collapsed")

        # 설정 업데이트
        config["date_range"]["start_date"] = str(start_date)
        config["date_range"]["end_date"] = str(end_date)

    with col2:
        st.markdown("**📊 분석 기준**")
        # 이전 분석 모드 저장
        prev_mode = st.session_state.get("prev_analysis_mode", config.get("analysis_mode", "건수별"))

        analysis_mode = st.radio(
            "분석 기준",
            options=["건수별", "제품별", "금액별"],
            index=["건수별", "제품별", "금액별"].index(config.get("analysis_mode", "건수별")),
            horizontal=True,
            key="analysis_mode_radio",
            label_visibility="collapsed"
        )

        # 분석 모드가 바뀌면 이전 결과 초기화
        if analysis_mode != prev_mode:
            st.session_state.promo_results = None
            st.session_state.prev_analysis_mode = analysis_mode
            st.info(f"💡 분석 모드가 '{analysis_mode}'(으)로 변경되었습니다. '분석 시작하기' 버튼을 눌러주세요.")

        config["analysis_mode"] = analysis_mode

    st.markdown("**🔍 필터 옵션**")
    col1, col2, col3 = st.columns(3)

    with col1:
        include_services = st.checkbox(
            "🛠️ 서비스성 제품 포함",
            value=config.get("include_service_products", False),
            key="include_services_check",
            help="더케어, 멤버십 제품을 포함합니다"
        )
        config["include_service_products"] = include_services

    with col2:
        include_online = st.checkbox(
            "🌐 온라인파트 포함",
            value=config.get("include_online", False),
            key="include_online_check",
            help="기본값: CRM파트만 분석"
        )
        config["include_online"] = include_online

    with col3:
        include_indirect = st.checkbox(
            "🔗 연계승인 포함",
            value=config.get("include_indirect", False),
            key="include_indirect_check",
            help="기본값: 직접승인만 분석"
        )
        config["include_indirect"] = include_indirect

    st.divider()

    # === 상세 설정 (expander) ===
    with st.expander("🔧 상세 설정", expanded=False):

        # 제품별 가중치 설정
        st.markdown("#### 제품별 가중치")
        st.markdown("제품별 기준 분석 시 사용되는 가중치입니다.")

        weights = config["product_weights"]
        col1, col2, col3 = st.columns(3)

        with col1:
            weights["안마의자"] = st.number_input(
                "안마의자", min_value=0, value=weights.get("안마의자", 5),
                step=1, key="weight_chair"
            )
            weights["라클라우드"] = st.number_input(
                "라클라우드", min_value=0, value=weights.get("라클라우드", 3),
                step=1, key="weight_lacloud"
            )

        with col2:
            weights["정수기"] = st.number_input(
                "정수기", min_value=0, value=weights.get("정수기", 2),
                step=1, key="weight_water"
            )
            weights["더케어"] = st.number_input(
                "더케어", min_value=0, value=weights.get("더케어", 1),
                step=1, key="weight_care"
            )

        with col3:
            weights["멤버십"] = st.number_input(
                "멤버십", min_value=0, value=weights.get("멤버십", 1),
                step=1, key="weight_member"
            )

        config["product_weights"] = weights

        st.divider()

        # 최소 기준치 설정
        st.markdown("#### 최소 승인 건수 기준")
        min_criteria = st.number_input(
            "프로모션 대상 최소 승인 건수",
            min_value=0,
            value=config["minimum_criteria"].get("count", 7),
            step=1,
            key="min_criteria_input"
        )
        config["minimum_criteria"]["count"] = min_criteria

        st.divider()

        # 프로모션 구간 설정 (제품별 기준인 경우만 표시)
        if analysis_mode == "제품별":
            st.markdown("#### 프로모션 점수 구간")
            st.markdown("점수에 따른 프로모션 등급을 설정합니다.")

            tiers = config.get("promotion_tiers", [])

            # 기존 구간 표시 및 수정
            for i, tier in enumerate(tiers):
                cols = st.columns([2, 2, 2, 1])
                with cols[0]:
                    tier["name"] = st.text_input(
                        "등급명", value=tier.get("name", f"{i+1}등급"),
                        key=f"tier_name_{i}"
                    )
                with cols[1]:
                    tier["min_score"] = st.number_input(
                        "최소 점수", min_value=0, value=tier.get("min_score", 0),
                        step=1, key=f"tier_min_{i}"
                    )
                with cols[2]:
                    max_score = tier.get("max_score")
                    use_max = st.checkbox("최대값 설정", value=(max_score is not None), key=f"tier_use_max_{i}")
                    if use_max:
                        tier["max_score"] = st.number_input(
                            "최대 점수", min_value=0, value=max_score if max_score else 100,
                            step=1, key=f"tier_max_{i}"
                        )
                    else:
                        tier["max_score"] = None
                with cols[3]:
                    if st.button("🗑️", key=f"delete_tier_{i}"):
                        tiers.pop(i)
                        st.rerun()

            # 새 구간 추가
            if st.button("➕ 구간 추가", key="add_tier_btn"):
                tiers.append({"name": f"{len(tiers)+1}등급", "min_score": 0, "max_score": None})
                st.rerun()

            config["promotion_tiers"] = tiers

    st.divider()

    # === 설정 관리 버튼 ===
    st.markdown("#### 💾 설정 관리")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("설정 저장", key="save_config_btn", use_container_width=True):
            success, error = save_config(config)
            if success:
                st.success("✅ 설정이 저장되었습니다!")
            else:
                st.error(f"❌ {error}")

    with col2:
        if st.button("초기화", key="reset_config_btn", use_container_width=True):
            success, error = reset_config()
            if success:
                st.session_state.promo_config = get_default_config()
                st.success("✅ 설정이 초기화되었습니다!")
                st.rerun()
            else:
                st.error(f"❌ {error}")

    with col3:
        if st.button("새 프로모션", key="new_promo_btn", use_container_width=True):
            st.session_state.promo_config = get_default_config()
            st.session_state.promo_results = None
            st.success("✅ 새 프로모션 설정으로 초기화되었습니다!")
            st.rerun()

    st.divider()

    # === 분석 실행 ===
    st.markdown("### 🚀 3단계: 분석 실행")

    if st.button("📊 분석 시작하기", key="analyze_btn", type="primary", use_container_width=True):
        if st.session_state.promo_df is None:
            st.error("❌ 먼저 데이터 파일을 업로드해주세요!")
        else:
            with st.spinner("🔄 데이터 분석 중... 잠시만 기다려주세요."):
                # 날짜를 datetime으로 변환
                start_dt = pd.Timestamp(start_date)
                end_dt = pd.Timestamp(end_date).replace(hour=23, minute=59, second=59)

                # 분석 실행
                result_df, error, filtered_df = analyze_promotion_data_new(
                    df=st.session_state.promo_df,
                    analysis_mode=analysis_mode,
                    product_weights=config["product_weights"],
                    include_services=include_services,
                    min_criteria=min_criteria,
                    promotion_tiers=config.get("promotion_tiers", []),
                    start_date=start_dt,
                    end_date=end_dt,
                    include_online=include_online,
                    include_indirect=include_indirect
                )

                if error:
                    st.error(f"❌ {error}")
                else:
                    st.session_state.promo_results = result_df
                    st.session_state.promo_filtered_df = filtered_df
                    st.session_state.promo_analysis_mode = analysis_mode  # 분석 모드 저장
                    st.session_state.prev_analysis_mode = analysis_mode  # 이전 모드 업데이트
                    st.success("✅ 분석이 완료되었습니다!")

    # === 결과 표시 ===
    if st.session_state.promo_results is not None:
        st.divider()
        st.markdown("### 📊 분석 결과")

        result_df = st.session_state.promo_results
        # 저장된 분석 모드 사용 (결과 생성 당시의 모드)
        result_analysis_mode = st.session_state.get("promo_analysis_mode", analysis_mode)

        # 요약 정보 (카드 형태)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 인원", f"{len(result_df)}명")
        with col2:
            st.metric("분석 기준", result_analysis_mode)
        with col3:
            st.metric("분석 기간", f"{(end_date - start_date).days + 1}일")
        with col4:
            if result_analysis_mode == "제품별" and "프로모션등급" in result_df.columns:
                tier_counts = result_df["프로모션등급"].value_counts()
                tier_1_count = tier_counts.get("1등급", 0)
                st.metric("1등급", f"{tier_1_count}명")
            elif "프로모션대상" in result_df.columns:
                target_count = (result_df["프로모션대상"] == "Y").sum()
                st.metric("대상자", f"{target_count}명")
            else:
                st.metric("분석 완료", "✓")

        # 색상 범례 표시
        if result_analysis_mode == "제품별" and "프로모션등급" in result_df.columns:
            st.info("🎨 **색상 안내**: 순위=그라데이션(초록→노랑→빨강), 프로모션등급=색상구분(1등급=보라, 2등급=핑크, 3등급=시안)")
        elif "순위" in result_df.columns:
            st.info("🎨 **색상 안내**: 순위별로 그라데이션 색상이 적용됩니다 (상위=초록, 중간=노랑, 하위=빨강)")

        # 컬럼 설정
        column_config = {}

        # 순위: 중앙 정렬, 고정 너비
        if "순위" in result_df.columns:
            column_config["순위"] = st.column_config.NumberColumn(
                "순위",
                width="small",
                help="순위"
            )

        # 상담사: 좌측 정렬, 적당한 너비
        if "상담사" in result_df.columns:
            column_config["상담사"] = st.column_config.TextColumn(
                "상담사",
                width="medium",
                help="상담사명"
            )

        # 제품 컬럼들: 중앙 정렬, 작은 너비
        for col in ["안마의자", "라클라우드", "정수기", "더케어", "멤버십"]:
            if col in result_df.columns:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    width="small",
                    help=f"{col} 승인건수"
                )

        # 승인건수, 승인액: 우측 정렬
        if "승인건수" in result_df.columns:
            column_config["승인건수"] = st.column_config.NumberColumn(
                "승인건수",
                width="small",
                help="총 승인건수"
            )

        if "승인액" in result_df.columns:
            column_config["승인액"] = st.column_config.NumberColumn(
                "승인액",
                width="medium",
                help="총 승인금액"
            )

        # 점수 (제품별)
        if "점수" in result_df.columns:
            column_config["점수"] = st.column_config.NumberColumn(
                "점수",
                width="small",
                help="가중치 적용 점수"
            )

        # 프로모션등급 (제품별) - 텍스트 컬럼이 아닌 일반 컬럼으로
        if "프로모션등급" in result_df.columns:
            column_config["프로모션등급"] = st.column_config.Column(
                "프로모션등급",
                width="medium",
                help="등급"
            )

        # 프로모션대상 (건수별/금액별) - 텍스트 컬럼이 아닌 일반 컬럼으로
        if "프로모션대상" in result_df.columns:
            column_config["프로모션대상"] = st.column_config.Column(
                "프로모션대상",
                width="small",
                help="대상 여부 (Y/N)"
            )

        # 스타일링 적용된 결과 테이블 표시 (저장된 분석 모드 사용)
        styled_df = style_promotion_table(result_df.copy(), result_analysis_mode)

        st.dataframe(
            styled_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=500
        )

        st.markdown("---")

        # 다운로드 버튼
        st.markdown("**📥 결과 다운로드**")
        col1, col2 = st.columns(2)

        with col1:
            # CSV 다운로드
            csv = result_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"프로모션결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv_btn",
                use_container_width=True
            )

        with col2:
            # 엑셀 다운로드 (2개 시트: 결과 + 원본 데이터) - 저장된 분석 모드 사용
            try:
                excel_data = create_promotion_excel(
                    result_df=result_df,
                    original_df=st.session_state.promo_df,
                    analysis_mode=result_analysis_mode
                )

                if excel_data:
                    st.download_button(
                        label="📊 엑셀 다운로드 (2시트)",
                        data=excel_data,
                        file_name=f"프로모션결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel_btn",
                        use_container_width=True
                    )
                else:
                    st.error("엑셀 파일 생성 실패")
            except Exception as e:
                st.error(f"엑셀 다운로드 오류: {str(e)}")
