"""
매출 데이터 분석 로직

이 모듈은 복수 엑셀 파일을 처리하고 상담사별 집계를 생성합니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
import xlsxwriter
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 상담사 관리 모듈
from utils.consultant_manager import load_consultants, get_all_consultants


def process_sales_files(
    files: List[Any],
    include_empty_campaign: bool = True
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    복수의 엑셀 파일을 처리하여 하나의 데이터프레임으로 통합합니다.

    Args:
        files: 업로드된 파일 리스트
        include_empty_campaign: 일반회차 캠페인 빈값 포함 여부

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 통합 데이터프레임, 오류 메시지
    """
    try:
        all_dataframes = []

        for file in files:
            file.seek(0)

            # 엑셀 파일 읽기 (3행부터 데이터 시작 - header=2)
            df = None
            engines = ['openpyxl', 'xlrd']

            for engine in engines:
                try:
                    df = pd.read_excel(file, header=2, engine=engine)
                    break
                except Exception:
                    continue

            if df is None:
                return None, f"파일 읽기 실패: {file.name}"

            # 빈 열(컬럼명 없는 열) 제거
            df = df.dropna(axis=1, how='all')

            # 컬럼명이 Unnamed인 열 제거
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

            # 필수 컬럼 확인 및 매핑
            required_cols = ["상담사", "상담DB상태"]
            found_cols = {}

            for req_col in required_cols:
                # 정확한 이름 매칭
                if req_col in df.columns:
                    found_cols[req_col] = req_col
                    continue

                # 유사한 이름 찾기 (부분 매칭)
                for col in df.columns:
                    if req_col in str(col):
                        found_cols[req_col] = col
                        break

            # 필수 컬럼이 없으면 에러
            if len(found_cols) < len(required_cols):
                missing = [col for col in required_cols if col not in found_cols]
                return None, f"필수 컬럼 누락 ({file.name}): {', '.join(missing)}"

            # 컬럼 이름 정규화
            df = df.rename(columns={v: k for k, v in found_cols.items()})

            # 파일명 추가 (추적용)
            df['_파일명'] = file.name

            all_dataframes.append(df)

        # 모든 데이터프레임 통합
        if not all_dataframes:
            return None, "처리할 파일이 없습니다."

        combined_df = pd.concat(all_dataframes, ignore_index=True)

        # 데이터가 비어있는지 확인
        if combined_df.empty:
            return None, "결합된 데이터가 비어 있습니다."

        return combined_df, None

    except Exception as e:
        return None, f"파일 처리 중 오류: {str(e)}"


def filter_sales_data(
    df: pd.DataFrame,
    include_empty_campaign: bool = True
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    데이터를 필터링합니다.

    Args:
        df: 원본 데이터프레임
        include_empty_campaign: 일반회차 캠페인 빈값 포함 여부

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 필터링된 데이터프레임, 오류 메시지
    """
    try:
        # 등록된 상담사 목록 가져오기
        registered_consultants = get_all_consultants()

        # 상담사 필터링 (로우데이터용 - 예약일자 필터 X)
        filtered_df = df[df['상담사'].isin(registered_consultants)].copy()

        # 일반회차 캠페인 빈값 처리
        if not include_empty_campaign and '일반회차 캠페인' in df.columns:
            filtered_df = filtered_df[filtered_df['일반회차 캠페인'].notna()]
            filtered_df = filtered_df[filtered_df['일반회차 캠페인'] != '']

        # 상담주문번호 기준 중복 제거 (첫 번째 행만 유지)
        if '상담주문번호' in filtered_df.columns:
            original_count = len(filtered_df)
            filtered_df = filtered_df.drop_duplicates(subset=['상담주문번호'], keep='first')
            duplicates_removed = original_count - len(filtered_df)
            if duplicates_removed > 0:
                print(f"중복 제거: {duplicates_removed}건 (상담주문번호 기준)")

        # 번호 컬럼을 1부터 순차적으로 채번
        if '번호' in filtered_df.columns:
            filtered_df['번호'] = range(1, len(filtered_df) + 1)
        else:
            # 번호 컬럼이 없으면 새로 생성 (맨 앞에 추가)
            filtered_df.insert(0, '번호', range(1, len(filtered_df) + 1))

        return filtered_df, None

    except Exception as e:
        return None, f"데이터 필터링 중 오류: {str(e)}"


def filter_by_reservation_date(
    df: pd.DataFrame,
    apply_filter: bool = False,
    custom_start_date: Optional[datetime] = None,
    custom_end_date: Optional[datetime] = None
) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[Dict[str, int]]]:
    """
    예약일자 기준으로 관리대상을 필터링합니다.

    관리대상 조건 (카운트 대상):
    1. 과거 예약: 예약일자 ≤ 과거 기준일 (사용자 지정 또는 오늘, 기준일까지가 과거)
    2. 미래 초과 예약: 예약일자 > 미래 기준일 (사용자 지정 또는 오늘+1개월)
    3. 예약일자 비어있음: NaN/빈값

    허용 범위 (카운트 제외): 과거 기준일+1일 ≤ 예약일자 ≤ 미래 기준일

    Args:
        df: 필터링할 데이터프레임
        apply_filter: 필터 적용 여부
        custom_start_date: 과거 기준일 (이 날짜까지는 괜찮음)
        custom_end_date: 미래 기준일 (이 날짜까지는 괜찮음)

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str], Optional[Dict]]:
            필터링된 데이터프레임, 오류 메시지, 통계 정보
    """
    try:
        # 필터 미적용 시 원본 반환
        if not apply_filter:
            return df, None, None

        # 예약일자 컬럼 찾기 (유연한 매칭)
        reservation_date_col = None

        # 정확한 매칭 시도
        if '예약 일자' in df.columns:
            reservation_date_col = '예약 일자'
        elif '예약일자' in df.columns:
            reservation_date_col = '예약일자'
        else:
            # 부분 매칭 시도 (공백 제거해서 비교)
            for col in df.columns:
                col_normalized = str(col).replace(' ', '').replace('\u3000', '')  # 공백, 전각공백 제거
                if '예약일자' in col_normalized:
                    reservation_date_col = col
                    break

        # 예약일자 컬럼이 없으면 원본 반환 (경고 메시지 포함)
        if reservation_date_col is None:
            # 사용 가능한 컬럼 목록 출력 (디버깅용)
            available_cols = ', '.join(df.columns[:10].tolist())
            if len(df.columns) > 10:
                available_cols += f" ... (총 {len(df.columns)}개 컬럼)"
            return df, f"⚠️ '예약일자' 또는 '예약 일자' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {available_cols}", None

        # 오늘 날짜
        today = datetime.now().date()

        # 과거 기준일 설정 (사용자 지정 또는 오늘)
        if custom_start_date is not None:
            if isinstance(custom_start_date, datetime):
                start_date = custom_start_date.date()
            else:
                start_date = custom_start_date
        else:
            start_date = today

        # 미래 기준일 설정 (사용자 지정 또는 오늘+1개월)
        if custom_end_date is not None:
            if isinstance(custom_end_date, datetime):
                end_date = custom_end_date.date()
            else:
                end_date = custom_end_date
        else:
            end_date = start_date + relativedelta(months=1)

        # 예약일자를 datetime으로 변환
        df_copy = df.copy()
        df_copy['예약일자_dt'] = pd.to_datetime(df_copy[reservation_date_col], errors='coerce')

        # 관리대상 필터링
        # 1. 예약일자가 비어있음 (NaT)
        mask_empty = df_copy['예약일자_dt'].isna()

        # 2. 과거 예약: 예약일자 ≤ 과거 기준일 (기준일까지가 과거)
        mask_past = (~mask_empty) & (df_copy['예약일자_dt'].dt.date <= start_date)

        # 3. 미래 초과 예약: 예약일자 > 미래 기준일
        mask_far_future = (~mask_empty) & (df_copy['예약일자_dt'].dt.date > end_date)

        # 관리대상: 빈값 OR 과거 OR 미래 초과
        management_target = mask_empty | mask_past | mask_far_future

        # 통계 정보
        stats = {
            "빈값": int(mask_empty.sum()),
            "과거": int(mask_past.sum()),
            "기준일초과": int(mask_far_future.sum()),
            "관리대상": int(management_target.sum()),
            "총건수": len(df_copy),
            "과거기준일": start_date.strftime('%Y-%m-%d'),
            "미래기준일": end_date.strftime('%Y-%m-%d')
        }

        # 관리대상만 필터링
        filtered_df = df_copy[management_target].copy()

        # 임시 컬럼 제거
        if '예약일자_dt' in filtered_df.columns:
            filtered_df = filtered_df.drop(columns=['예약일자_dt'])

        return filtered_df, None, stats

    except Exception as e:
        return None, f"예약일자 필터링 중 오류: {str(e)}", None


def create_aggregation_tables(df: pd.DataFrame) -> Tuple[Optional[Dict[str, pd.DataFrame]], Optional[str]]:
    """
    상담사별 집계 테이블을 생성합니다.

    Args:
        df: 필터링된 데이터프레임

    Returns:
        Tuple[Optional[Dict[str, pd.DataFrame]], Optional[str]]: 테이블 딕셔너리, 오류 메시지
    """
    try:
        tables = {}

        # 상담DB상태의 모든 값 가져오기
        db_statuses = df['상담DB상태'].unique()

        # 우선순위: 예약 → 체험신청 → 신규 → 나머지 (정렬)
        priority_statuses = ['예약', '체험신청', '신규']
        other_statuses = sorted([s for s in db_statuses if s not in priority_statuses])
        ordered_statuses = [s for s in priority_statuses if s in db_statuses] + other_statuses

        # 1. 메인 테이블 생성 (전체)
        main_table = df.groupby(['상담사', '상담DB상태']).size().unstack(fill_value=0)

        # 컬럼 순서 정렬
        existing_cols = [col for col in ordered_statuses if col in main_table.columns]
        main_table = main_table[existing_cols]

        # 총건 컬럼 추가
        main_table['총건'] = main_table.sum(axis=1)

        # 총 합계 행 추가
        total_row = main_table.sum()
        total_row.name = '총 합계'
        main_table = pd.concat([main_table, pd.DataFrame([total_row])])

        # 인덱스 이름 설정
        main_table.index.name = '상담사명'
        main_table = main_table.reset_index()

        tables['메인테이블'] = main_table

        # 2. 개별 테이블 생성 (예약, 체험신청, 신규)
        for status in ['예약', '체험신청', '신규']:
            if status in db_statuses:
                status_df = df[df['상담DB상태'] == status]

                # 신규 테이블은 캠페인별로 그룹화
                if status == '신규' and '일반회차 캠페인' in status_df.columns:
                    # 일반회차 캠페인별, 상담사별 집계
                    campaign_consultant = status_df.groupby(['일반회차 캠페인', '상담사']).size().reset_index(name='건수')

                    # 캠페인 빈값 처리
                    campaign_consultant['일반회차 캠페인'] = campaign_consultant['일반회차 캠페인'].fillna('(빈값)')

                    # 캠페인별로 정렬
                    campaign_consultant = campaign_consultant.sort_values(['일반회차 캠페인', '건수'], ascending=[True, False])

                    # 캠페인별로 구분선과 소계 추가
                    result_rows = []
                    unique_campaigns = campaign_consultant['일반회차 캠페인'].unique()

                    for campaign in unique_campaigns:
                        campaign_data = campaign_consultant[campaign_consultant['일반회차 캠페인'] == campaign]

                        # 캠페인명 헤더 행 추가
                        result_rows.append({
                            '일반회차 캠페인': f'▼ {campaign}',
                            '상담사': '',
                            '건수': ''
                        })

                        # 해당 캠페인의 상담사별 데이터 추가
                        for _, row in campaign_data.iterrows():
                            result_rows.append({
                                '일반회차 캠페인': '',
                                '상담사': row['상담사'],
                                '건수': row['건수']
                            })

                    # 총건 행 추가
                    result_rows.append({
                        '일반회차 캠페인': '',
                        '상담사': '총건',
                        '건수': campaign_consultant['건수'].sum()
                    })

                    status_table = pd.DataFrame(result_rows)
                    tables[f'{status}테이블'] = status_table

                else:
                    # 예약, 체험신청은 기존 방식
                    status_count = status_df.groupby('상담사').size()

                    if len(status_count) > 0:
                        status_table = pd.DataFrame({
                            '상담사명': status_count.index,
                            status: status_count.values
                        })

                        # 총건 행 추가
                        total_row = pd.DataFrame({
                            '상담사명': ['총건'],
                            status: [status_count.sum()]
                        })
                        status_table = pd.concat([status_table, total_row], ignore_index=True)

                        tables[f'{status}테이블'] = status_table

        return tables, None

    except Exception as e:
        return None, f"집계 테이블 생성 중 오류: {str(e)}"


def create_excel_output(
    tables: Dict[str, pd.DataFrame],
    raw_data: pd.DataFrame
) -> Optional[bytes]:
    """
    엑셀 파일을 생성합니다.

    Args:
        tables: 집계 테이블 딕셔너리
        raw_data: 로우데이터

    Returns:
        Optional[bytes]: 엑셀 바이너리 데이터
    """
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book

            # 헤더 포맷
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BD',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })

            # 총합계/총건 포맷
            total_format = workbook.add_format({
                'bold': True,
                'bg_color': '#FFF2CC',
                'border': 1
            })

            # 시트1: 집계 테이블
            worksheet = workbook.add_worksheet('집계 테이블')
            current_row = 0

            for table_name, table_df in tables.items():
                # 테이블 제목
                worksheet.write(current_row, 0, table_name, header_format)
                current_row += 1

                # 테이블 데이터
                for col_idx, col_name in enumerate(table_df.columns):
                    worksheet.write(current_row, col_idx, col_name, header_format)

                current_row += 1

                for row_idx, row in table_df.iterrows():
                    for col_idx, value in enumerate(row):
                        # 총 합계, 총건 행은 강조
                        if row_idx == len(table_df) - 1:
                            worksheet.write(current_row, col_idx, value, total_format)
                        else:
                            worksheet.write(current_row, col_idx, value)
                    current_row += 1

                # 테이블 간 간격
                current_row += 2

            # 시트2: 로우데이터
            # _파일명 컬럼 제외
            if '_파일명' in raw_data.columns:
                raw_data_output = raw_data.drop(columns=['_파일명'])
            else:
                raw_data_output = raw_data

            raw_data_output.to_excel(writer, sheet_name='로우데이터', index=False)

            # 로우데이터 시트 포맷팅
            raw_worksheet = writer.sheets['로우데이터']
            for col_idx, col_name in enumerate(raw_data_output.columns):
                raw_worksheet.write(0, col_idx, col_name, header_format)
                # 컬럼 너비 자동 조정
                max_length = max(
                    raw_data_output[col_name].astype(str).str.len().max(),
                    len(str(col_name))
                )
                raw_worksheet.set_column(col_idx, col_idx, min(max_length + 2, 50))

        output.seek(0)
        return output.getvalue()

    except Exception as e:
        print(f"엑셀 생성 중 오류: {str(e)}")
        return None
