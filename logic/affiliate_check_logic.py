"""
연계실적 체크 비즈니스 로직

외부 연계 매출(CRM팀 내부가 아닌)을 확인하기 위한 로직입니다.
필터링 순서가 중요하며, 순서대로 적용됩니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from typing import Tuple, Optional, List
import xlsxwriter


def process_affiliate_check_file(file, file_type: str = "approval") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    승인매출/설치매출 엑셀 파일을 처리하는 함수

    Args:
        file: 업로드된 엑셀 파일 객체 또는 리스트
        file_type: "approval" (승인) 또는 "installation" (설치)

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지
    """
    try:
        # 다중 파일인 경우
        if isinstance(file, list):
            all_dfs = []
            for single_file in file:
                df, error = process_single_file(single_file)
                if error:
                    return None, error
                if df is not None:
                    all_dfs.append(df)

            if not all_dfs:
                return None, "처리 가능한 파일이 없습니다."

            combined_df = pd.concat(all_dfs, ignore_index=True)
            return combined_df, None
        else:
            return process_single_file(file)

    except Exception as e:
        return None, f"파일 처리 중 오류: {str(e)}"


def process_single_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    단일 엑셀 파일 처리
    상담주문계약내역 파일은 3행부터 데이터가 시작되므로 skiprows=2 우선 적용
    """
    try:
        file.seek(0)

        # skiprows=2 우선 시도 (3행부터 읽기 - 상담주문계약내역 파일 형식)
        df = None
        for skip_rows in [2, 0, 1, 3, 4, 5]:
            try:
                file.seek(0)
                temp_df = pd.read_excel(file, skiprows=skip_rows)

                # 유효한 데이터인지 확인 - 컬럼명이 실제 데이터 컬럼명인지 체크
                if len(temp_df) >= 3 and len(temp_df.columns) >= 3:
                    # Unnamed 컬럼이 많으면 잘못 읽은 것
                    unnamed_count = sum(1 for col in temp_df.columns if str(col).startswith('Unnamed'))
                    if unnamed_count < len(temp_df.columns) / 2:  # Unnamed가 절반 미만이면 유효
                        print(f"skiprows={skip_rows}에서 유효한 데이터 발견: {len(temp_df)}행, {len(temp_df.columns)}컬럼")
                        df = temp_df
                        break
            except:
                continue

        if df is None:
            return None, "유효한 데이터를 찾을 수 없습니다."

        return df, None

    except Exception as e:
        return None, f"파일 읽기 오류: {str(e)}"


def filter_affiliate_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    연계실적 필터링 로직 (순서 중요!)

    필터링 순서:
    1. "일반회차 캠페인" 값이 있는 행 제거
    2. "상담사 조직"이 "안마" 또는 "라정" 포함 시 제거
    3. "대분류"가 안마의자, 라클라우드, 정수기만 유지
    4. "품목 명"에 필터, 베개, 탄산 포함 시 제거
    5. "모바일 번호" 중복 제거

    Args:
        df: 원본 데이터프레임

    Returns:
        Tuple[pd.DataFrame, dict]: 필터링된 데이터프레임과 통계 정보
    """
    stats = {
        "original_count": len(df),
        "after_campaign_filter": 0,
        "after_org_filter": 0,
        "after_category_filter": 0,
        "after_product_filter": 0,
        "after_duplicate_filter": 0,
        "removed_by_campaign": 0,
        "removed_by_org": 0,
        "removed_by_category": 0,
        "removed_by_product": 0,
        "removed_by_duplicate": 0
    }

    result_df = df.copy()

    # 1. 캠페인 데이터 제거 - "일반회차 캠페인" 값이 있는 행
    if "일반회차 캠페인" in result_df.columns:
        before_count = len(result_df)
        # 빈 값, NaN, 공백만 있는 경우만 유지
        campaign_col = result_df["일반회차 캠페인"].fillna("").astype(str).str.strip()
        result_df = result_df[campaign_col == ""]
        stats["removed_by_campaign"] = before_count - len(result_df)
        stats["after_campaign_filter"] = len(result_df)
    else:
        stats["after_campaign_filter"] = len(result_df)

    # 2. 홈쇼핑 상담사 실적 반영건 사전제거 - "안마" 또는 "라정" 포함
    if "상담사 조직" in result_df.columns:
        before_count = len(result_df)
        org_col = result_df["상담사 조직"].fillna("").astype(str)
        # 안마, 라정 등 홈쇼핑 상담사 조직 제거
        homeshopping_org_mask = org_col.str.contains("안마|라정", case=False, na=False)
        result_df = result_df[~homeshopping_org_mask]
        stats["removed_by_org"] = before_count - len(result_df)
        stats["after_org_filter"] = len(result_df)
    else:
        stats["after_org_filter"] = len(result_df)

    # 3. 주요 제품만 유지 - 안마의자, 라클라우드, 정수기
    if "대분류" in result_df.columns:
        before_count = len(result_df)
        category_col = result_df["대분류"].fillna("").astype(str)
        main_product_mask = category_col.str.contains("안마의자|라클라우드|정수기", case=False, na=False)
        result_df = result_df[main_product_mask]
        stats["removed_by_category"] = before_count - len(result_df)
        stats["after_category_filter"] = len(result_df)
    else:
        stats["after_category_filter"] = len(result_df)

    # 4. 소모품 제거 - 필터, 베개, 탄산
    if "품목 명" in result_df.columns:
        before_count = len(result_df)
        product_col = result_df["품목 명"].fillna("").astype(str)
        consumable_mask = product_col.str.contains("필터|베개|탄산", case=False, na=False)
        result_df = result_df[~consumable_mask]
        stats["removed_by_product"] = before_count - len(result_df)
        stats["after_product_filter"] = len(result_df)
    else:
        stats["after_product_filter"] = len(result_df)

    # 5. 모바일 번호 중복 제거 (첫 번째 항목 유지)
    if "모바일 번호" in result_df.columns:
        before_count = len(result_df)
        result_df = result_df.drop_duplicates(subset=["모바일 번호"], keep="first")
        stats["removed_by_duplicate"] = before_count - len(result_df)
        stats["after_duplicate_filter"] = len(result_df)
    else:
        stats["after_duplicate_filter"] = len(result_df)

    return result_df, stats


def select_and_sort_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    필요한 컬럼만 선택하고 주문일자 순으로 정렬

    Args:
        df: 필터링된 데이터프레임

    Returns:
        pd.DataFrame: 정렬된 데이터프레임
    """
    # 필요한 컬럼 목록 (정확한 순서 유지)
    required_columns = [
        "주문 일자", "계약 번호", "상담주문번호", "고객 번호", "고객 명",
        "모바일 번호", "전화 번호", "판매 채널", "판매인입경로",
        "대분류", "품목 명", "상담사", "상담사 조직"
    ]

    # 컬럼명 변형 매핑 (공백 포함 등 다양한 변형 처리)
    column_variations = {
        "판매인입경로": ["판매인입경로", "판매 인입경로", "판매인입 경로", "판매 인입 경로", "인입경로"],
        "주문 일자": ["주문 일자", "주문일자"],
        "계약 번호": ["계약 번호", "계약번호"],
        "상담주문번호": ["상담주문번호", "상담 주문번호", "상담주문 번호"],
        "고객 번호": ["고객 번호", "고객번호"],
        "고객 명": ["고객 명", "고객명"],
        "모바일 번호": ["모바일 번호", "모바일번호", "휴대폰 번호", "휴대폰번호"],
        "전화 번호": ["전화 번호", "전화번호"],
        "판매 채널": ["판매 채널", "판매채널"],
        "대분류": ["대분류"],
        "품목 명": ["품목 명", "품목명"],
        "상담사": ["상담사"],
        "상담사 조직": ["상담사 조직", "상담사조직"]
    }

    # 실제 컬럼명 찾기 함수
    def find_actual_column(target_col, df_columns):
        if target_col in df_columns:
            return target_col
        # 변형 목록에서 찾기
        if target_col in column_variations:
            for variation in column_variations[target_col]:
                if variation in df_columns:
                    return variation
        return None

    # 존재하는 컬럼만 선택 (변형 이름도 포함)
    existing_columns = []
    column_mapping = {}  # 원래 이름 -> 실제 이름 매핑

    for col in required_columns:
        actual_col = find_actual_column(col, df.columns.tolist())
        if actual_col:
            existing_columns.append(actual_col)
            if actual_col != col:
                column_mapping[actual_col] = col

    if not existing_columns:
        return df

    result_df = df[existing_columns].copy()

    # 컬럼명을 표준 이름으로 변경
    if column_mapping:
        result_df = result_df.rename(columns=column_mapping)

    # 주문일자 순으로 정렬 (이미 표준화된 이름 사용)
    if "주문 일자" in result_df.columns:
        result_df["주문 일자"] = pd.to_datetime(result_df["주문 일자"], errors="coerce")
        result_df = result_df.sort_values("주문 일자", ascending=True)

    return result_df


def create_affiliate_check_excel(
    approval_df: Optional[pd.DataFrame],
    installation_df: Optional[pd.DataFrame],
    approval_stats: Optional[dict],
    installation_stats: Optional[dict]
) -> Optional[bytes]:
    """
    연계실적 체크 결과를 엑셀 파일로 생성

    Args:
        approval_df: 승인연계 데이터프레임
        installation_df: 설치연계 데이터프레임
        approval_stats: 승인매출 필터링 통계
        installation_stats: 설치매출 필터링 통계

    Returns:
        Optional[bytes]: 엑셀 바이너리 데이터
    """
    try:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # 스타일 정의
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#00498c',
            'font_color': 'white',
            'border': 1
        })

        data_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0'
        })

        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': 'yyyy-mm-dd'
        })

        mobile_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '@'  # 텍스트 형식
        })

        # 1. 승인연계 시트
        if approval_df is not None and not approval_df.empty:
            ws_approval = workbook.add_worksheet('승인연계')
            write_data_to_worksheet(ws_approval, approval_df, header_format, data_format, number_format, date_format, mobile_format)

        # 2. 설치연계 시트
        if installation_df is not None and not installation_df.empty:
            ws_installation = workbook.add_worksheet('설치연계')
            write_data_to_worksheet(ws_installation, installation_df, header_format, data_format, number_format, date_format, mobile_format)

        # 시트가 하나도 없으면 빈 시트라도 생성
        has_data = False
        if approval_df is not None and not approval_df.empty:
            has_data = True
        if installation_df is not None and not installation_df.empty:
            has_data = True

        if not has_data:
            # 빈 데이터 시트 생성
            ws_empty = workbook.add_worksheet('데이터없음')
            ws_empty.write(0, 0, "필터링 결과 데이터가 없습니다.", data_format)

        # 3. 필터링 통계 시트
        ws_stats = workbook.add_worksheet('필터링통계')
        write_stats_to_worksheet(ws_stats, approval_stats, installation_stats, header_format, data_format, number_format)

        workbook.close()
        return output.getvalue()

    except Exception as e:
        import traceback
        error_msg = f"엑셀 생성 오류: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return None


def write_data_to_worksheet(worksheet, df, header_format, data_format, number_format, date_format, mobile_format):
    """
    워크시트에 데이터 작성 (자동 필터 및 열 너비 자동 조정 포함)
    최적화: iterrows() 대신 numpy 배열 기반 처리
    """
    if df.empty:
        return

    # 컬럼 정보 미리 분석
    columns = df.columns.tolist()
    n_cols = len(columns)
    n_rows = len(df)

    # 컬럼 타입 미리 분류 (벡터화)
    is_phone_col = np.array(["모바일" in col or "전화" in col for col in columns])
    is_date_col = np.array(["일자" in col or "날짜" in col for col in columns])

    # 각 컬럼별 최대 너비 계산용 (헤더 길이로 초기화)
    col_widths = {i: len(str(col)) for i, col in enumerate(columns)}

    # 헤더 작성
    for col_idx, col_name in enumerate(columns):
        worksheet.write(0, col_idx, col_name, header_format)

    # 데이터를 numpy 배열로 변환하여 빠른 접근
    data_values = df.values

    # 데이터 작성 (행 기반 루프는 유지하되 내부 연산 최적화)
    for row_idx in range(n_rows):
        row_data = data_values[row_idx]
        excel_row = row_idx + 1  # 헤더가 0행

        for col_idx in range(n_cols):
            value = row_data[col_idx]

            # NaN 처리
            if pd.isna(value):
                worksheet.write(excel_row, col_idx, "", data_format)
                continue

            # 모바일/전화 번호 처리
            if is_phone_col[col_idx]:
                if isinstance(value, (int, float, np.integer, np.floating)):
                    phone_str = str(int(value))
                    # 한국 전화번호 보정
                    if len(phone_str) == 10 and phone_str.startswith('10'):
                        phone_str = '0' + phone_str
                    worksheet.write(excel_row, col_idx, phone_str, mobile_format)
                    col_widths[col_idx] = max(col_widths[col_idx], len(phone_str))
                else:
                    str_value = str(value)
                    worksheet.write(excel_row, col_idx, str_value, mobile_format)
                    col_widths[col_idx] = max(col_widths[col_idx], len(str_value))
            # 날짜 처리
            elif is_date_col[col_idx]:
                if isinstance(value, (datetime, pd.Timestamp)):
                    worksheet.write_datetime(excel_row, col_idx, value, date_format)
                    col_widths[col_idx] = max(col_widths[col_idx], 12)
                else:
                    worksheet.write(excel_row, col_idx, value, data_format)
                    col_widths[col_idx] = max(col_widths[col_idx], len(str(value)))
            # 숫자 처리
            elif isinstance(value, (int, float, np.integer, np.floating)):
                worksheet.write(excel_row, col_idx, value, number_format)
                formatted_len = len(f"{value:,.0f}")
                col_widths[col_idx] = max(col_widths[col_idx], formatted_len)
            else:
                str_value = str(value)
                worksheet.write(excel_row, col_idx, str_value, data_format)
                col_widths[col_idx] = max(col_widths[col_idx], len(str_value))

    # 열 너비 자동 조정 적용 (최소 8, 최대 50)
    for col_idx, width in col_widths.items():
        adjusted_width = min(max(width + 2, 8), 50)
        worksheet.set_column(col_idx, col_idx, adjusted_width)

    # 자동 필터 적용 (데이터가 있는 범위)
    if n_rows > 0:
        worksheet.autofilter(0, 0, n_rows, n_cols - 1)

    # 틀 고정 (헤더 행 고정)
    worksheet.freeze_panes(1, 0)


def write_stats_to_worksheet(worksheet, approval_stats, installation_stats, header_format, data_format, number_format):
    """
    필터링 통계를 워크시트에 작성
    """
    # 헤더
    worksheet.write(0, 0, "필터링 단계", header_format)
    worksheet.write(0, 1, "승인매출", header_format)
    worksheet.write(0, 2, "설치매출", header_format)

    worksheet.set_column(0, 0, 25)
    worksheet.set_column(1, 2, 15)

    # 통계 항목
    stats_items = [
        ("원본 데이터", "original_count"),
        ("1. 캠페인 제거 후", "after_campaign_filter"),
        ("   - 제거된 건수", "removed_by_campaign"),
        ("2. 홈쇼핑 상담사 제거 후", "after_org_filter"),
        ("   - 제거된 건수", "removed_by_org"),
        ("3. 제품필터 후", "after_category_filter"),
        ("   - 제거된 건수", "removed_by_category"),
        ("4. 소모품 제거 후", "after_product_filter"),
        ("   - 제거된 건수", "removed_by_product"),
        ("5. 중복 제거 후 (최종)", "after_duplicate_filter"),
        ("   - 제거된 건수", "removed_by_duplicate"),
    ]

    for row_idx, (label, key) in enumerate(stats_items, 1):
        worksheet.write(row_idx, 0, label, data_format)

        if approval_stats:
            worksheet.write(row_idx, 1, approval_stats.get(key, 0), number_format)
        else:
            worksheet.write(row_idx, 1, "-", data_format)

        if installation_stats:
            worksheet.write(row_idx, 2, installation_stats.get(key, 0), number_format)
        else:
            worksheet.write(row_idx, 2, "-", data_format)
