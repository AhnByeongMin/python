"""
연계실적 체크 UI 모듈

외부 연계 매출(CRM팀 내부가 아닌)을 확인하기 위한 UI입니다.
승인매출/설치매출 파일을 업로드하여 연계실적을 필터링합니다.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import uuid

# 비즈니스 로직 가져오기
from logic.affiliate_check_logic import (
    process_affiliate_check_file,
    filter_affiliate_data,
    select_and_sort_columns,
    create_affiliate_check_excel
)


def show():
    """
    연계실적 체크 페이지 UI를 표시하는 메인 함수
    """
    # 타이틀
    st.title("🔍 연계실적 체크")
    st.markdown("""
    <p>외부 연계 매출을 확인하기 위한 도구입니다. 승인매출/설치매출 파일을 업로드하면 다음 조건으로 필터링합니다:</p>
    <ul>
        <li>캠페인 데이터 제거 (일반회차 캠페인 값이 있는 건)</li>
        <li>홈쇼핑 상담사 실적 반영건 사전제거 (안마, 라정 조직)</li>
        <li>주요 제품만 유지 (안마의자, 라클라우드, 정수기)</li>
        <li>소모품 제거 (필터, 베개, 탄산)</li>
        <li>모바일 번호 중복 제거</li>
    </ul>
    """, unsafe_allow_html=True)

    # 세션 상태 초기화
    session_defaults = {
        'aff_approval_files': [],
        'aff_installation_files': [],
        'aff_approval_result': None,
        'aff_installation_result': None,
        'aff_approval_stats': None,
        'aff_installation_stats': None,
        'aff_analysis_complete': False,
        'aff_processing': False
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    # 파일 업로드 섹션
    st.subheader("📁 파일 업로드")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**승인매출 파일**")
        approval_files = st.file_uploader(
            "승인매출 엑셀 파일을 업로드하세요",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            key="aff_approval_uploader"
        )
        # 파일 변경 감지 및 이전 결과 초기화
        if approval_files:
            # 파일이 변경되었는지 확인 (파일 수나 이름 비교)
            prev_files = st.session_state.get('aff_approval_files', [])
            prev_names = set(f.name for f in prev_files) if prev_files else set()
            curr_names = set(f.name for f in approval_files)

            if prev_names != curr_names:
                # 파일이 변경되면 이전 결과 초기화
                st.session_state.aff_approval_result = None
                st.session_state.aff_approval_stats = None
                st.session_state.aff_analysis_complete = False

            st.session_state.aff_approval_files = approval_files
            st.info(f"승인매출: {len(approval_files)}개 파일 업로드됨")
        else:
            # 파일이 제거되면 초기화
            if st.session_state.get('aff_approval_files'):
                st.session_state.aff_approval_files = []
                st.session_state.aff_approval_result = None
                st.session_state.aff_approval_stats = None

    with col2:
        st.markdown("**설치매출 파일**")
        installation_files = st.file_uploader(
            "설치매출 엑셀 파일을 업로드하세요",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            key="aff_installation_uploader"
        )
        # 파일 변경 감지 및 이전 결과 초기화
        if installation_files:
            prev_files = st.session_state.get('aff_installation_files', [])
            prev_names = set(f.name for f in prev_files) if prev_files else set()
            curr_names = set(f.name for f in installation_files)

            if prev_names != curr_names:
                st.session_state.aff_installation_result = None
                st.session_state.aff_installation_stats = None
                st.session_state.aff_analysis_complete = False

            st.session_state.aff_installation_files = installation_files
            st.info(f"설치매출: {len(installation_files)}개 파일 업로드됨")
        else:
            if st.session_state.get('aff_installation_files'):
                st.session_state.aff_installation_files = []
                st.session_state.aff_installation_result = None
                st.session_state.aff_installation_stats = None

    # 분석 버튼
    st.markdown("---")
    analyze_button = st.button("🔍 연계실적 분석 시작", key="aff_analyze_btn", use_container_width=True)

    if analyze_button:
        if not st.session_state.aff_approval_files and not st.session_state.aff_installation_files:
            st.warning("승인매출 또는 설치매출 파일을 업로드해주세요.")
        else:
            run_analysis()

    # 결과 표시
    if st.session_state.aff_analysis_complete:
        display_results()


def run_analysis():
    """
    분석 실행
    """
    st.session_state.aff_processing = True
    progress_placeholder = st.empty()
    start_time = time.time()

    try:
        # 1. 승인매출 처리
        approval_result = None
        approval_stats = None

        if st.session_state.aff_approval_files:
            progress_placeholder.info("🔄 승인매출 파일 처리 중...")

            # 파일 읽기
            approval_df, error = process_affiliate_check_file(
                st.session_state.aff_approval_files,
                file_type="approval"
            )

            if error:
                st.error(f"승인매출 파일 오류: {error}")
            elif approval_df is not None:
                # 필터링 적용
                filtered_df, stats = filter_affiliate_data(approval_df)
                # 컬럼 선택 및 정렬
                approval_result = select_and_sort_columns(filtered_df)
                approval_stats = stats

        # 2. 설치매출 처리
        installation_result = None
        installation_stats = None

        if st.session_state.aff_installation_files:
            progress_placeholder.info("🔄 설치매출 파일 처리 중...")

            # 파일 읽기
            installation_df, error = process_affiliate_check_file(
                st.session_state.aff_installation_files,
                file_type="installation"
            )

            if error:
                st.error(f"설치매출 파일 오류: {error}")
            elif installation_df is not None:
                # 필터링 적용
                filtered_df, stats = filter_affiliate_data(installation_df)
                # 컬럼 선택 및 정렬
                installation_result = select_and_sort_columns(filtered_df)
                installation_stats = stats

        # 결과 저장
        st.session_state.aff_approval_result = approval_result
        st.session_state.aff_installation_result = installation_result
        st.session_state.aff_approval_stats = approval_stats
        st.session_state.aff_installation_stats = installation_stats
        st.session_state.aff_analysis_complete = True
        st.session_state.aff_processing = False

        # 완료 메시지
        end_time = time.time()
        elapsed = end_time - start_time

        approval_count = len(approval_result) if approval_result is not None else 0
        installation_count = len(installation_result) if installation_result is not None else 0

        progress_placeholder.success(
            f"✅ 분석 완료! 승인연계: {approval_count}건, 설치연계: {installation_count}건 "
            f"(소요시간: {elapsed:.2f}초)"
        )

    except Exception as e:
        st.error(f"❌ 분석 중 오류 발생: {str(e)}")
        st.session_state.aff_processing = False
        progress_placeholder.empty()


def display_results():
    """
    분석 결과 표시
    """
    st.markdown("---")
    st.subheader("📊 분석 결과")

    approval_result = st.session_state.aff_approval_result
    installation_result = st.session_state.aff_installation_result
    approval_stats = st.session_state.aff_approval_stats
    installation_stats = st.session_state.aff_installation_stats

    # 탭으로 결과 표시
    tabs = st.tabs(["승인연계", "설치연계", "필터링 통계"])

    # 승인연계 탭
    with tabs[0]:
        if approval_result is not None and not approval_result.empty:
            st.markdown(f"**총 {len(approval_result)}건**")
            st.dataframe(approval_result, height=400, use_container_width=True)
        else:
            st.info("승인연계 데이터가 없습니다.")

    # 설치연계 탭
    with tabs[1]:
        if installation_result is not None and not installation_result.empty:
            st.markdown(f"**총 {len(installation_result)}건**")
            st.dataframe(installation_result, height=400, use_container_width=True)
        else:
            st.info("설치연계 데이터가 없습니다.")

    # 필터링 통계 탭
    with tabs[2]:
        display_filter_stats(approval_stats, installation_stats)

    # 다운로드 버튼
    st.markdown("---")
    st.subheader("📥 결과 다운로드")

    if (approval_result is not None and not approval_result.empty) or \
       (installation_result is not None and not installation_result.empty):

        # 엑셀 파일 생성
        excel_data = create_affiliate_check_excel(
            approval_result,
            installation_result,
            approval_stats,
            installation_stats
        )

        if excel_data:
            today = datetime.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:4]

            st.download_button(
                label="📥 엑셀 다운로드 (승인연계 + 설치연계)",
                data=excel_data,
                file_name=f"{today}_{unique_id}_연계실적체크.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="aff_download_excel",
                use_container_width=True
            )
        else:
            st.error("엑셀 파일 생성 중 오류가 발생했습니다.")


def display_filter_stats(approval_stats, installation_stats):
    """
    필터링 통계 표시
    """
    st.markdown("**필터링 단계별 데이터 현황**")

    # 통계 데이터프레임 생성
    stats_data = []

    stats_items = [
        ("원본 데이터", "original_count"),
        ("1. 캠페인 제거 후", "after_campaign_filter"),
        ("   └ 제거된 건수", "removed_by_campaign"),
        ("2. 홈쇼핑 상담사 제거 후", "after_org_filter"),
        ("   └ 제거된 건수", "removed_by_org"),
        ("3. 제품필터 후", "after_category_filter"),
        ("   └ 제거된 건수", "removed_by_category"),
        ("4. 소모품 제거 후", "after_product_filter"),
        ("   └ 제거된 건수", "removed_by_product"),
        ("5. 중복 제거 후 (최종)", "after_duplicate_filter"),
        ("   └ 제거된 건수", "removed_by_duplicate"),
    ]

    for label, key in stats_items:
        row = {"필터링 단계": label}
        row["승인매출"] = approval_stats.get(key, "-") if approval_stats else "-"
        row["설치매출"] = installation_stats.get(key, "-") if installation_stats else "-"
        stats_data.append(row)

    stats_df = pd.DataFrame(stats_data)
    st.dataframe(stats_df, hide_index=True, use_container_width=True)

    # 요약 메트릭
    col1, col2 = st.columns(2)

    with col1:
        if approval_stats:
            original = approval_stats.get("original_count", 0)
            final = approval_stats.get("after_duplicate_filter", 0)
            removed = original - final
            st.metric(
                label="승인매출 필터링 결과",
                value=f"{final:,}건",
                delta=f"-{removed:,}건 제거",
                delta_color="off"
            )

    with col2:
        if installation_stats:
            original = installation_stats.get("original_count", 0)
            final = installation_stats.get("after_duplicate_filter", 0)
            removed = original - final
            st.metric(
                label="설치매출 필터링 결과",
                value=f"{final:,}건",
                delta=f"-{removed:,}건 제거",
                delta_color="off"
            )
