"""
상담사 프로모션 현황 비즈니스 로직

이 모듈은 상담사 프로모션 현황을 처리하고 분석하는 비즈니스 로직을 포함합니다.
UI와 독립적으로 작동하여 단위 테스트가 가능하도록 설계되었습니다.
"""

import pandas as pd
import numpy as np
from io import BytesIO
import re
import xlsxwriter
from typing import Tuple, Dict, List, Optional, Any, Union

def process_promotion_file(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    프로모션 분석용 엑셀 파일을 처리하는 함수
    
    Args:
        file: 업로드된 엑셀 파일 객체
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 처리된 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 파일 포인터 초기화
        file.seek(0)
        
        # 엑셀 파일 읽기 (3행에 헤더 있음)
        df = pd.read_excel(file, header=2)
        
        # 컬럼명이 비어있는 열 제거
        if df is not None:
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 필요한 컬럼 확인
        required_columns = ["상담사", "일반회차 캠페인", "판매 인입경로", "대분류", "판매 유형", "매출 금액", "주문 일자"]
        
        # 컬럼명이 비슷한 경우 매핑
        column_mapping = {}
        for req_col in required_columns:
            if req_col in df.columns:
                continue  # 이미 존재하면 매핑 불필요
                
            # 유사한 컬럼명 목록
            similar_cols = {
                "상담사": ["상담원", "상담원명", "직원명", "사원명", "담당자"],
                "일반회차 캠페인": ["캠페인", "일반회차캠페인", "회차", "회차 캠페인"],
                "판매 인입경로": ["판매인입경로", "인입경로", "영업채널", "영업 채널"],
                "대분류": ["제품", "품목", "상품", "상품명", "제품명", "품목명", "카테고리"],
                "판매 유형": ["판매유형", "상품유형", "제품유형", "서비스유형"],
                "매출 금액": ["매출금액", "매출", "금액", "판매금액"],
                "주문 일자": ["주문일자", "계약일자", "판매일자", "승인일자"]
            }
            
            if req_col in similar_cols:
                # 유사한 컬럼 찾기
                for col in df.columns:
                    col_str = str(col).lower()
                    if any(term.lower() in col_str for term in similar_cols[req_col]):
                        column_mapping[col] = req_col
                        break
        
        # 컬럼명 변경
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # 필요한 컬럼 확인 재검사
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"프로모션 분석 파일에 필요한 열이 없습니다: {', '.join(missing_columns)}"
        
        # 일반회차 캠페인 필터링: 비어있지 않고, 특정 값을 포함하는 것만 유지
        df = df[df["일반회차 캠페인"].notna()]  # 비어있지 않은 값
        
        # "V-", "C-", "캠", "정규", "재분배", "CB-" 중 하나라도 포함하는 값 필터링
        campaign_mask = (
            df["일반회차 캠페인"].astype(str).str.contains("V-|C-|캠|정규|재분배|CB-", case=False)
        )
        df = df[campaign_mask].copy()
        
        # 상담사가 "fmin2"인 행 제외 (공용아이디 제외)
        df = df[df["상담사"] != "fmin2"].copy()
        
        # 매출 금액이 숫자형이 아닌 경우 변환
        if not pd.api.types.is_numeric_dtype(df["매출 금액"]):
            df["매출 금액"] = pd.to_numeric(df["매출 금액"], errors='coerce')
            df = df.dropna(subset=["매출 금액"])
        
        # 주문 일자가 날짜형이 아닌 경우 변환
        if not pd.api.types.is_datetime64_any_dtype(df["주문 일자"]):
            df["주문 일자"] = pd.to_datetime(df["주문 일자"], errors='coerce')
        
        return df, None
        
    except Exception as e:
        return None, f"프로모션 파일 처리 중 오류가 발생했습니다: {str(e)}"

def analyze_promotion_data(
    df: pd.DataFrame, 
    include_products: List[str], 
    include_services: bool,
    direct_only: bool,
    criteria: List[str],
    min_condition: int,
    reward_positions: int
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    커스텀 프로모션 기준에 따라 상담사별 실적을 분석하는 함수
    
    Args:
        df: 데이터프레임
        include_products: 포함할 제품 목록 (안마의자, 라클라우드, 정수기)
        include_services: 서비스 품목 포함 여부 (더케어, 멤버십)
        direct_only: 직접 판매만 포함할지 여부
        criteria: 기준 목록 (건수, 매출액)
        min_condition: 최소 건수 조건
        reward_positions: 포상 순위 수
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 결과 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 데이터 필터링
        filtered_df = df.copy()
        
        # 1. 직접 판매만 필터링 (옵션에 따라)
        if direct_only:
            filtered_df = filtered_df[filtered_df["판매 인입경로"].astype(str).str.contains("CRM", case=False)]
        
        # 2. 제품 카테고리 필터링
        product_mask = pd.Series(False, index=filtered_df.index)
        for product in include_products:
            product_mask |= filtered_df["대분류"].astype(str).str.contains(product, case=False)
        
        # 3. 서비스 품목 처리
        # 서비스 품목을 포함하지 않는 경우
        if not include_services:
            # 더케어 필터링 (대분류가 안마의자이고 판매 유형에 "케어"가 포함된 것 제외)
            care_mask = (
                filtered_df["대분류"].astype(str).str.contains("안마의자", case=False) & 
                filtered_df["판매 유형"].astype(str).str.contains("케어", case=False)
            )
            
            # 멤버십 필터링 (대분류가 정수기이고 판매 유형에 "멤버십"이 포함된 것 제외)
            membership_mask = (
                filtered_df["대분류"].astype(str).str.contains("정수기", case=False) & 
                filtered_df["판매 유형"].astype(str).str.contains("멤버십|멤버쉽", case=False)
            )
            
            # 서비스 품목이 아닌 것만 유지
            filtered_df = filtered_df[~(care_mask | membership_mask) & product_mask]
        else:
            # 서비스 품목 포함 시에는 선택된 제품 카테고리만 필터링
            filtered_df = filtered_df[product_mask]
        
        # 4. 상담사별 실적 집계
        result_data = []
        
        # 상담사 목록 가져오기
        consultants = filtered_df["상담사"].unique().tolist()
        
        for consultant in consultants:
            # 해당 상담사의 데이터 추출
            consultant_df = filtered_df[filtered_df["상담사"] == consultant]
            
            # 제품별 건수
            anma_count = len(consultant_df[consultant_df["대분류"].astype(str).str.contains("안마의자", case=False)])
            lacloud_count = len(consultant_df[consultant_df["대분류"].astype(str).str.contains("라클라우드", case=False)])
            water_count = len(consultant_df[consultant_df["대분류"].astype(str).str.contains("정수기", case=False)])
            
            # 서비스 품목 건수
            care_count = len(
                consultant_df[
                    consultant_df["대분류"].astype(str).str.contains("안마의자", case=False) & 
                    consultant_df["판매 유형"].astype(str).str.contains("케어", case=False)
                ]
            )
            
            membership_count = len(
                consultant_df[
                    consultant_df["대분류"].astype(str).str.contains("정수기", case=False) & 
                    consultant_df["판매 유형"].astype(str).str.contains("멤버십|멤버쉽", case=False)
                ]
            )
            
            # 총 승인 건수
            total_count = len(consultant_df)
            
            # 총 매출액
            total_amount = consultant_df["매출 금액"].sum()
            
            # 최소 조건 확인
            if total_count < min_condition:
                continue
            
            # 결과 딕셔너리 생성
            result_dict = {
                "상담사": consultant,
                "안마의자": anma_count,
                "라클라우드": lacloud_count,
                "정수기": water_count,
                "더케어": care_count,
                "멤버십": membership_count,
                "누적승인(건)": total_count,
                "누적승인(액)": total_amount
            }
            
            result_data.append(result_dict)
        
        # 결과가 없는 경우
        if not result_data:
            return None, "설정한 조건에 해당하는 상담사가 없습니다."
        
        # 결과 데이터프레임 생성
        result_df = pd.DataFrame(result_data)
        
        # 정렬 기준 설정
        sort_columns = []
        ascending_values = []
        
        # 기준에 따라 정렬 컬럼 추가
        for criterion in criteria:
            if criterion == "승인건수":
                sort_columns.append("누적승인(건)")
                ascending_values.append(False)  # 내림차순
            elif criterion == "승인액":
                sort_columns.append("누적승인(액)")
                ascending_values.append(False)  # 내림차순
        
        # 정렬
        if sort_columns:
            result_df = result_df.sort_values(by=sort_columns, ascending=ascending_values)
        
        # 순위 부여
        result_df["순위"] = range(1, len(result_df) + 1)
        
        # 포상 획득 여부 설정
        result_df["포상획득여부"] = result_df["순위"].apply(lambda x: "Y" if x <= reward_positions else "N")
        
        # 컬럼 순서 재정렬
        columns = ["순위", "상담사"]
        
        # 선택된 제품 컬럼 추가
        for product in include_products:
            if product == "안마의자":
                columns.append("안")
                result_df["안"] = result_df["안마의자"]
            elif product == "라클라우드":
                columns.append("라")
                result_df["라"] = result_df["라클라우드"]
            elif product == "정수기":
                columns.append("정")
                result_df["정"] = result_df["정수기"]
        
        # 서비스 품목 추가 (포함된 경우)
        if include_services:
            columns.append("케어")
            result_df["케어"] = result_df["더케어"]
            columns.append("멤버")
            result_df["멤버"] = result_df["멤버십"]
        
        # 기본 컬럼 추가
        columns.extend(["누적승인(건)", "누적승인(액)", "포상획득여부"])
        
        # 필요한 컬럼만 선택 및 재정렬
        result_df = result_df[columns]
        
        return result_df, None
        
    except Exception as e:
        return None, f"프로모션 데이터 분석 중 오류가 발생했습니다: {str(e)}"

def create_excel_report(result_df: pd.DataFrame, original_df: pd.DataFrame) -> Optional[bytes]:
    """
    분석 결과를 엑셀 파일로 변환하는 함수
    
    Args:
        result_df: 분석 결과 데이터프레임
        original_df: 원본 데이터프레임
        
    Returns:
        Optional[bytes]: 엑셀 바이너리 데이터 또는 None (오류 발생 시)
    """
    try:
        # 엑셀 파일 생성
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 워크북과 워크시트 설정
            workbook = writer.book
            
            # 공통 스타일 정의
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center',
                'fg_color': '#305496',
                'font_color': 'white',
                'border': 1,
                'border_color': '#D4D4D4'
            })

            title_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            data_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D4D4D4'
            })

            number_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D4D4D4',
                'num_format': '#,##0'
            })

            currency_format = workbook.add_format({
                'align': 'right',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D4D4D4',
                'num_format': '#,##0'
            })

            # 포상 획득 여부 스타일
            reward_yes_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D4D4D4',
                'bg_color': '#DFF2BF',
                'color': '#4F8A10',
                'bold': True
            })
            
            reward_no_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D4D4D4',
                'bg_color': '#FEEFB3',
                'color': '#9F6000'
            })

            # 1. 프로모션 결과 시트 - 수정된 방식으로 워크시트 생성
            worksheet1 = workbook.add_worksheet('프로모션결과')
            
            # 제목 추가
            merge_end_col = min(len(result_df.columns) - 1, 7)  # 최대 H열까지만 병합
            worksheet1.merge_range(0, 0, 0, merge_end_col, '상담사 프로모션 결과', title_format)
            worksheet1.set_row(0, 25)  # 제목 행 높이 설정
            
            # 헤더 행 작성
            for col_num, column_name in enumerate(result_df.columns):
                worksheet1.write(1, col_num, column_name, header_format)
            
            # 데이터 행 작성
            for row_num, row in result_df.iterrows():
                row_idx = row_num + 2  # 헤더(1행) + 제목(1행) 다음부터 시작
                for col_num, column_name in enumerate(result_df.columns):
                    value = row[column_name]
                    
                    # 컬럼 유형에 따라 다른 형식 적용
                    if column_name == "포상획득여부":
                        if value == "Y":
                            worksheet1.write(row_idx, col_num, value, reward_yes_format)
                        else:
                            worksheet1.write(row_idx, col_num, value, reward_no_format)
                    elif column_name in ["누적승인(액)"]:
                        worksheet1.write_number(row_idx, col_num, value, currency_format)
                    elif column_name in ["순위", "누적승인(건)", "안", "라", "정", "케어", "멤버"]:
                        worksheet1.write_number(row_idx, col_num, value, number_format)
                    else:
                        worksheet1.write(row_idx, col_num, value, data_format)
            
            # 컬럼 너비 설정
            column_widths = {
                0: 6,   # 순위
                1: 15,  # 상담사
                2: 8,   # 안
                3: 8,   # 라
                4: 8,   # 정
                5: 8,   # 케어
                6: 8,   # 멤버
                7: 12,  # 누적승인(건)
                8: 15,  # 누적승인(액)
                9: 12,  # 포상획득여부
            }
            
            # 데이터프레임 컬럼 수에 맞게 설정
            for col_num, width in column_widths.items():
                if col_num < len(result_df.columns):
                    worksheet1.set_column(col_num, col_num, width)
            
            # 원본 데이터 시트 생성
            if original_df is not None and not original_df.empty:
                # 원본 데이터를 엑셀 시트에 저장
                original_df.to_excel(writer, sheet_name='원본데이터', index=False)
                
                # 워크시트 가져오기
                worksheet2 = writer.sheets['원본데이터']
                
                # 헤더 행에 스타일 적용
                for col_num, column_name in enumerate(original_df.columns):
                    worksheet2.write(0, col_num, column_name, header_format)
                
                # 컬럼 너비 자동 조정
                for col_num, column_name in enumerate(original_df.columns):
                    # 컬럼 이름 길이와 데이터 길이 중 최대값으로 열 너비 설정
                    max_len = max(
                        len(str(column_name)),
                        original_df[column_name].astype(str).str.len().max() if not original_df.empty else 0
                    )
                    worksheet2.set_column(col_num, col_num, min(max_len + 2, 30))  # 최대 30
        
        # 버퍼 위치를 처음으로 되돌림
        output.seek(0)
        excel_data = output.getvalue()
        return excel_data
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"엑셀 파일 생성 중 오류: {str(e)}\n{error_details}")
        return None