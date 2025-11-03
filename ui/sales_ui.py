"""
매출 데이터 분석 UI

이 모듈은 매출 데이터 분석 탭의 UI를 제공합니다.
"""

import streamlit as st
import pandas as pd
import base64
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# 로직 함수 가져오기
from logic.sales_logic import (
    process_sales_files,
    filter_sales_data,
    filter_by_reservation_date,
    create_aggregation_tables,
    create_excel_output
)


def show():
    """예약 체험 신규 현황 탭 UI를 표시하는 메인 함수"""

    # 타이틀
    st.title("📊 예약 체험 신규 현황")

    st.markdown("""
    복수의 엑셀 파일을 업로드하여 상담사별 예약/체험신청/신규 현황을 분석합니다.

    **주요 기능:**
    - 복수 파일 동시 업로드 및 통합 분석
    - 등록된 상담사만 필터링
    - 예약일자 기준 관리대상 필터링 (과거, 한달 초과, 빈값)
    - 상담DB상태별 집계 (예약, 체험신청, 신규 등)
    - UI에서 테이블 확인 및 엑셀 다운로드
    """)

    st.markdown("---")

    # 파일 업로드
    st.subheader("📁 파일 업로드")
    uploaded_files = st.file_uploader(
        "엑셀 파일을 선택하세요 (복수 선택 가능)",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        key="sales_files"
    )

    # 옵션
    st.subheader("⚙️ 필터 옵션")

    col1, col2 = st.columns(2)

    with col1:
        include_empty = st.checkbox(
            "일반회차 캠페인 빈값 포함",
            value=True,
            help="체크하면 '일반회차 캠페인' 컬럼이 비어있는 행도 포함합니다."
        )

    with col2:
        filter_reservation = st.checkbox(
            "예약일자 관리대상 필터 적용",
            value=False,
            help="예약/체험신청의 관리대상만 집계합니다. (과거 예약, 기준일 초과, 빈값)\n로우데이터는 영향 받지 않습니다."
        )

    # 예약일자 필터 설정
    custom_end_date = None
    custom_start_date = None
    if filter_reservation:
        st.markdown("##### 📅 예약일자 기준일 설정")

        # 기본 기준일 계산
        from dateutil.relativedelta import relativedelta
        today = datetime.now().date()

        # 두 개의 설정 영역
        col_settings1, col_settings2 = st.columns(2)

        with col_settings1:
            st.markdown("**🔴 과거 기준일 (이 날짜까지는 괜찮음, 이전은 과거로 관리대상)**")
            adjust_past = st.checkbox("과거 기준일 조정", value=False, help="금요일에 토/일 포함하려면 체크")

            if adjust_past:
                custom_start_date = st.date_input(
                    "이 날짜까지는 괜찮음",
                    value=today,
                    help="예: 금요일(10/31)에 일요일(11/2)까지 보려면 11/2 선택"
                )
                st.caption(f"📍 {custom_start_date.strftime('%Y-%m-%d')} 이전은 과거로 관리대상")
            else:
                custom_start_date = today
                st.info(f"📌 기본: 오늘({today.strftime('%Y-%m-%d')}) 이전은 과거로 관리대상")

        with col_settings2:
            st.markdown("**🔵 미래 기준일 (이 날짜까지는 괜찮음, 이후는 미래로 관리대상)**")

            # 과거 기준일을 기준으로 +1개월 계산
            base_date = custom_start_date if custom_start_date else today
            default_end_date = base_date + relativedelta(months=1)

            adjust_future = st.checkbox("미래 기준일 수정", value=False, help="종료일을 수동으로 설정")

            if adjust_future:
                custom_end_date = st.date_input(
                    "기준일 선택",
                    value=default_end_date,
                    help="이 날짜 이후의 예약은 관리대상"
                )
                st.caption(f"📍 {custom_end_date.strftime('%Y-%m-%d')} 이후는 관리대상")
            else:
                custom_end_date = default_end_date
                st.info(f"📌 기본: {default_end_date.strftime('%Y-%m-%d')} 이후는 관리대상")

        # 인정 기간 요약
        st.markdown("---")
        col_summary = st.columns(1)[0]
        with col_summary:
            start_str = custom_start_date.strftime('%Y년 %m월 %d일') if custom_start_date else today.strftime('%Y년 %m월 %d일')
            end_str = custom_end_date.strftime('%Y년 %m월 %d일') if custom_end_date else default_end_date.strftime('%Y년 %m월 %d일')
            st.success(f"✅ **허용 범위 (카운트 제외)**: {start_str} ~ {end_str}")

            # 실제 기간 계산
            if custom_start_date and custom_end_date:
                days_diff = (custom_end_date - custom_start_date).days
                st.caption(f"이 범위의 예약은 정상으로 간주하여 관리대상에서 제외합니다. (과거, 미래초과, 빈값만 카운트)")

    st.markdown("---")

    # 분석 시작
    if uploaded_files:
        st.info(f"📂 {len(uploaded_files)}개 파일이 선택되었습니다.")

        if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
            with st.spinner("데이터 처리 중..."):
                # 1. 파일 처리
                combined_df, error = process_sales_files(uploaded_files, include_empty)

                if error:
                    st.error(f"❌ {error}")
                    return

                st.success(f"✅ 파일 통합 완료: 총 {len(combined_df):,}건")

                # 2. 데이터 필터링
                original_count = len(combined_df)
                filtered_df, error = filter_sales_data(combined_df, include_empty)

                if error:
                    st.error(f"❌ {error}")
                    return

                # 중복 제거 및 필터링 정보 표시
                final_count = len(filtered_df)
                removed_count = original_count - final_count

                if removed_count > 0:
                    st.success(f"✅ 필터링 완료: {final_count:,}건 (등록된 상담사만, 중복 제거 {removed_count:,}건)")
                else:
                    st.success(f"✅ 필터링 완료: {final_count:,}건 (등록된 상담사만, 중복 없음)")

                # 3. 예약일자 필터링 (테이블용만)
                table_df = filtered_df
                if filter_reservation:
                    table_df, error, stats = filter_by_reservation_date(
                        filtered_df,
                        apply_filter=True,
                        custom_start_date=custom_start_date,
                        custom_end_date=custom_end_date
                    )
                    if error:
                        st.error(f"❌ {error}")
                        return
                    if stats:
                        st.success(f"✅ 예약일자 필터 적용 (허용범위: {stats['과거기준일']} ~ {stats['미래기준일']}): {stats['관리대상']}건 (빈값:{stats['빈값']}, 과거:{stats['과거']}, 미래초과:{stats['기준일초과']})")
                    else:
                        st.success(f"✅ 예약일자 필터 적용: {len(table_df)}건 (관리대상만)")

                # 4. 집계 테이블 생성 (예약일자 필터 적용된 데이터로)
                tables, error = create_aggregation_tables(table_df)

                if error:
                    st.error(f"❌ {error}")
                    return

                # 세션 상태에 저장
                st.session_state['sales_tables'] = tables
                st.session_state['sales_raw_data'] = filtered_df

                st.success("✅ 집계 테이블 생성 완료!")
                st.rerun()

    # 결과 표시
    if 'sales_tables' in st.session_state and 'sales_raw_data' in st.session_state:
        st.markdown("---")
        st.subheader("📊 분석 결과")

        tables = st.session_state['sales_tables']
        raw_data = st.session_state['sales_raw_data']

        # 통계 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 데이터", f"{len(raw_data):,}건")
        with col2:
            st.metric("상담사 수", f"{raw_data['상담사'].nunique()}명")
        with col3:
            st.metric("상담DB상태 종류", f"{raw_data['상담DB상태'].nunique()}개")

        st.markdown("---")

        # 테이블 표시
        st.subheader("📋 집계 테이블")

        # 탭으로 테이블 구분
        tab_names = list(tables.keys())
        tabs = st.tabs(tab_names)

        for tab, (table_name, table_df) in zip(tabs, tables.items()):
            with tab:
                st.dataframe(
                    table_df,
                    use_container_width=True,
                    hide_index=True
                )

                # CSV 다운로드 버튼
                csv = table_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label=f"📥 {table_name} CSV 다운로드",
                    data=csv,
                    file_name=f"{table_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

        st.markdown("---")

        # 로우데이터 표시 (접기)
        with st.expander("📄 로우데이터 보기 및 필터", expanded=False):
            # _파일명 컬럼 제외
            if '_파일명' in raw_data.columns:
                base_display_data = raw_data.drop(columns=['_파일명'])
            else:
                base_display_data = raw_data

            # 필터 옵션
            st.markdown("##### 🔍 데이터 필터")

            filter_cols = st.columns([2, 2, 2, 1])

            # 상담사 필터
            with filter_cols[0]:
                available_consultants = ['전체'] + sorted(base_display_data['상담사'].unique().tolist())
                selected_consultant = st.selectbox(
                    "상담사",
                    options=available_consultants,
                    key="raw_data_consultant_filter"
                )

            # 상담DB상태 필터
            with filter_cols[1]:
                available_statuses = ['전체'] + sorted(base_display_data['상담DB상태'].unique().tolist())
                selected_status = st.selectbox(
                    "상담DB상태",
                    options=available_statuses,
                    key="raw_data_status_filter"
                )

            # 일반회차 캠페인 필터
            with filter_cols[2]:
                if '일반회차 캠페인' in base_display_data.columns:
                    campaign_values = base_display_data['일반회차 캠페인'].fillna('(빈값)').unique().tolist()
                    available_campaigns = ['전체'] + sorted(campaign_values)
                    selected_campaign = st.selectbox(
                        "일반회차 캠페인",
                        options=available_campaigns,
                        key="raw_data_campaign_filter"
                    )
                else:
                    selected_campaign = '전체'

            # 필터 초기화 버튼
            with filter_cols[3]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 초기화", key="reset_raw_filters"):
                    st.rerun()

            # 텍스트 검색
            search_text = st.text_input(
                "🔎 전체 검색 (모든 컬럼에서 검색)",
                placeholder="검색어를 입력하세요...",
                key="raw_data_search"
            )

            # 필터 적용
            filtered_data = base_display_data.copy()

            if selected_consultant != '전체':
                filtered_data = filtered_data[filtered_data['상담사'] == selected_consultant]

            if selected_status != '전체':
                filtered_data = filtered_data[filtered_data['상담DB상태'] == selected_status]

            if selected_campaign != '전체' and '일반회차 캠페인' in filtered_data.columns:
                if selected_campaign == '(빈값)':
                    filtered_data = filtered_data[filtered_data['일반회차 캠페인'].isna()]
                else:
                    filtered_data = filtered_data[filtered_data['일반회차 캠페인'] == selected_campaign]

            if search_text:
                # 모든 컬럼에서 텍스트 검색 (대소문자 구분 없이)
                mask = filtered_data.astype(str).apply(
                    lambda x: x.str.contains(search_text, case=False, na=False)
                ).any(axis=1)
                filtered_data = filtered_data[mask]

            # NaT와 NaN을 빈 문자열로 변환 (표시용)
            display_filtered_data = filtered_data.copy()

            # 모든 NaT, NaN, None을 빈 문자열로 완전히 치환
            for col in display_filtered_data.columns:
                display_filtered_data[col] = display_filtered_data[col].astype(str).replace('NaT', '').replace('nan', '').replace('None', '').replace('<NA>', '')

            # 컬럼 순서 재정렬 (핀 고정 컬럼을 맨 앞으로)
            pin_columns = ['번호', '상담주문번호', '상담사', '상담DB상태', '예약 일자', '일반회차 캠페인']
            existing_pin_cols = [col for col in pin_columns if col in display_filtered_data.columns]
            other_cols = [col for col in display_filtered_data.columns if col not in pin_columns]
            new_column_order = existing_pin_cols + other_cols
            display_filtered_data = display_filtered_data[new_column_order]

            # 필터링 결과 표시
            st.info(f"📊 전체 {len(base_display_data):,}건 중 {len(display_filtered_data):,}건 표시")

            st.markdown("---")

            # 데이터가 있을 때만 테이블 표시
            if len(display_filtered_data) > 0:
                # 데이터 테이블 (AgGrid - Excel처럼 컬럼별 필터, 정렬 가능)
                gb = GridOptionsBuilder.from_dataframe(display_filtered_data)

                # 기본 컬럼 설정 (성능 최적화)
                gb.configure_default_column(
                    resizable=True,
                    filterable=True,
                    sortable=True,
                    editable=False,
                    wrapText=False,
                    autoHeight=False,
                    width=150,
                    minWidth=100,
                    suppressSizeToFit=False
                )

                # 주요 컬럼 핀 고정 (이미 순서 정렬됨)
                pin_column_widths = {
                    '번호': 100,
                    '상담주문번호': 200,
                    '상담사': 140,
                    '상담DB상태': 150,
                    '예약 일자': 160,
                    '일반회차 캠페인': 220
                }

                for idx, col in enumerate(existing_pin_cols):
                    width = pin_column_widths.get(col, 180)
                    gb.configure_column(
                        col,
                        pinned='left',
                        width=width,
                        minWidth=width,
                        maxWidth=width * 2,
                        lockPosition=True,
                        resizable=True,
                        suppressSizeToFit=False
                    )

                # 페이지네이션 비활성화 (스크롤로 모든 데이터 보기)
                gb.configure_pagination(enabled=False)

                # 그리드 옵션 (성능 최적화)
                gb.configure_grid_options(
                    domLayout='normal',
                    suppressColumnVirtualisation=False,
                    suppressRowVirtualisation=False,
                    rowBuffer=10,
                    animateRows=False,
                    enableCellTextSelection=True
                )

                # 사이드바
                gb.configure_side_bar(
                    filters_panel=True,
                    columns_panel=True
                )

                # 행 선택 (간단하게)
                gb.configure_selection(
                    selection_mode='multiple',
                    use_checkbox=False
                )

                grid_options = gb.build()

                AgGrid(
                    display_filtered_data,
                    gridOptions=grid_options,
                    height=600,
                    theme='streamlit',
                    update_mode=GridUpdateMode.NO_UPDATE,
                    data_return_mode=DataReturnMode.AS_INPUT,
                    fit_columns_on_grid_load=False,
                    allow_unsafe_jscode=False,
                    enable_enterprise_modules=False,
                    reload_data=False
                )
            else:
                st.warning("⚠️ 필터 조건에 맞는 데이터가 없습니다.")

            # CSV 다운로드 (필터링된 데이터)
            csv = filtered_data.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label=f"📥 필터링된 데이터 CSV 다운로드 ({len(filtered_data)}건)",
                data=csv,
                file_name=f"로우데이터_필터_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_filtered_raw"
            )

        st.markdown("---")

        # 엑셀 다운로드
        st.subheader("📥 엑셀 파일 다운로드")

        with st.spinner("엑셀 파일 생성 중..."):
            excel_data = create_excel_output(tables, raw_data)

            if excel_data:
                b64 = base64.b64encode(excel_data).decode()
                filename = f"매출분석_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" class="download-button">📥 엑셀 다운로드 (2시트)</a>'

                st.markdown("""
                <style>
                .download-button {
                    display: inline-block;
                    padding: 0.5rem 1rem;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 0.25rem;
                    font-weight: bold;
                    text-align: center;
                }
                .download-button:hover {
                    background-color: #45a049;
                    color: white;
                }
                </style>
                """, unsafe_allow_html=True)

                st.markdown(href, unsafe_allow_html=True)

                st.info("""
                **엑셀 파일 구성:**
                - 시트1: 집계 테이블 (메인테이블 + 개별 테이블)
                - 시트2: 로우데이터 (등록된 상담사 필터링된 원본 데이터)

                **참고:** 집계 테이블은 예약일자 필터가 적용되지만, 로우데이터는 상담사 필터만 적용됩니다.
                """)
            else:
                st.error("엑셀 파일 생성에 실패했습니다.")

        # 초기화 버튼
        if st.button("🔄 초기화", use_container_width=True):
            if 'sales_tables' in st.session_state:
                del st.session_state['sales_tables']
            if 'sales_raw_data' in st.session_state:
                del st.session_state['sales_raw_data']
            st.rerun()

    else:
        # 파일 미업로드 시 안내
        if not uploaded_files:
            st.info("📂 분석할 엑셀 파일을 업로드해주세요.")
        else:
            st.info("🚀 '분석 시작' 버튼을 클릭하여 분석을 시작하세요.")
