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
import traceback
import logging
from datetime import datetime
import json
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def classify_product(row: pd.Series) -> str:
    """
    대분류와 판매유형을 기반으로 제품을 5개 카테고리로 분류

    분류 규칙:
    1. 라클라우드: 대분류 = "라클라우드"
    2. 안마의자: 대분류 = "안마의자" AND 판매유형에 "더케어" 미포함
    3. 더케어: 대분류 = "안마의자" AND 판매유형에 "더케어" 포함
    4. 정수기: 대분류 = "정수기" AND 판매유형에 "멤버십" 미포함
    5. 멤버십: 대분류 = "정수기" AND 판매유형에 "멤버십" 포함

    Args:
        row: 데이터프레임의 행 (대분류, 판매 유형 컬럼 필요)

    Returns:
        str: 분류된 제품명 (안마의자, 라클라우드, 정수기, 더케어, 멤버십)
    """
    category = str(row["대분류"]).lower()
    sales_type = str(row["판매 유형"]).lower()

    # 라클라우드
    if "라클" in category:
        return "라클라우드"

    # 안마의자 vs 더케어
    if "안마" in category:
        if "케어" in sales_type or "더케어" in sales_type:
            return "더케어"
        else:
            return "안마의자"

    # 정수기 vs 멤버십
    if "정수기" in category:
        if "멤버" in sales_type:
            return "멤버십"
        else:
            return "정수기"

    # 분류되지 않은 경우 대분류 그대로 반환
    return row["대분류"]

def clean_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    의미없는 컬럼 제거 함수
    - Unnamed 컬럼 제거
    - 컬럼명이 없거나, 0, "0"인 컬럼 제거

    Args:
        df: 원본 데이터프레임

    Returns:
        pd.DataFrame: 정리된 데이터프레임
    """
    # Unnamed 컬럼 제거
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]

    # 컬럼명이 없거나, 0, "0"인 컬럼 제거
    valid_columns = []
    for col in df.columns:
        col_str = str(col).strip()
        # 빈 문자열, None, 0, "0" 제외
        if col_str and col_str not in ['0', 'nan', 'None', '']:
            valid_columns.append(col)

    df = df[valid_columns]

    # 모든 값이 NaN인 컬럼 제거
    df = df.dropna(axis=1, how='all')

    return df


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

        # 의미없는 컬럼 제거
        df = clean_dataframe_columns(df)
        
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
            df["일반회차 캠페인"].astype(str).str.contains("V-|C-|AS-|캠|정규|재분배|CB-", case=False)
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

def analyze_promotion_data_new(
    df: pd.DataFrame,
    analysis_mode: str,  # "제품별" | "건수별" | "금액별"
    product_weights: Dict[str, int],  # 제품별 가중치
    include_services: bool,  # 서비스성 제품 포함 여부
    min_criteria: int,  # 최소 기준치 (건수)
    promotion_tiers: List[Dict],  # 프로모션 구간 설정
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_online: bool = False,  # 온라인파트 포함 여부
    include_indirect: bool = False  # 연계승인 포함 여부 (기본값: False, 직접승인만)
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    새로운 프로모션 분석 함수

    Args:
        df: 데이터프레임
        analysis_mode: 분석 기준 ("제품별" | "건수별" | "금액별")
        product_weights: 제품별 가중치 {"안마의자": 5, "라클라우드": 3, ...}
        include_services: 서비스성 제품 포함 여부
        min_criteria: 최소 기준치 (승인 건수)
        promotion_tiers: 프로모션 구간 설정
        start_date: 시작 날짜
        end_date: 종료 날짜
        include_online: 온라인파트 포함 여부 (기본값: False, CRM파트만)
        include_indirect: 연계승인 포함 여부 (기본값: False, 직접승인만)

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str], Optional[pd.DataFrame]]:
            결과 데이터프레임, 오류 메시지, 필터링된 원본 데이터
    """
    try:
        # 데이터 복사
        filtered_df = df.copy()
        original_filtered_df = None  # 필터링된 원본 데이터 저장용

        # 날짜 범위 필터링
        if start_date and end_date:
            if "주문 일자" in filtered_df.columns:
                if not pd.api.types.is_datetime64_any_dtype(filtered_df["주문 일자"]):
                    filtered_df["주문 일자"] = pd.to_datetime(filtered_df["주문 일자"], errors='coerce')
                filtered_df = filtered_df[(filtered_df["주문 일자"] >= start_date) &
                                         (filtered_df["주문 일자"] <= end_date)]

        # 판매 인입경로 필터링 (직접승인/연계승인)
        if "판매 인입경로" in filtered_df.columns:
            if not include_indirect:
                # 직접승인만 포함 (판매 인입경로가 CRM인 경우만)
                filtered_df = filtered_df[
                    filtered_df["판매 인입경로"].astype(str).str.contains("CRM|crm", case=False, na=False)
                ]
            # include_indirect=True이면 필터링 없이 전체 포함

        # 상담사 조직 필터링
        if "상담사 조직" in filtered_df.columns:
            if not include_online:
                # CRM파트만 포함 (온라인파트 제외)
                # "CRM팀", "CRM파트" 등 다양한 명칭 포함
                filtered_df = filtered_df[
                    filtered_df["상담사 조직"].astype(str).str.contains("CRM|crm", case=False, na=False)
                ]

        # 제품 분류 컬럼 추가
        filtered_df["제품분류"] = filtered_df.apply(classify_product, axis=1)

        # 필터링된 원본 데이터 저장 (엑셀 다운로드용)
        original_filtered_df = filtered_df.copy()

        # 상담사별 집계
        result_data = []
        consultants = filtered_df["상담사"].unique()

        for consultant in consultants:
            consultant_df = filtered_df[filtered_df["상담사"] == consultant]

            # 제품별 건수 집계
            product_counts = {}
            for product in ["안마의자", "라클라우드", "정수기", "더케어", "멤버십"]:
                count = len(consultant_df[consultant_df["제품분류"] == product])
                product_counts[product] = count

            # 총 승인 건수 및 승인액
            if include_services:
                # 서비스 포함 시 모든 제품 카운트
                total_count = sum(product_counts.values())
            else:
                # 서비스 제외 시 안마의자, 라클라우드, 정수기만
                total_count = (product_counts["안마의자"] +
                             product_counts["라클라우드"] +
                             product_counts["정수기"])

            total_amount = consultant_df["매출 금액"].sum()

            # 제품별 점수 계산 (제품별 기준인 경우)
            product_score = 0
            if analysis_mode == "제품별":
                for product, count in product_counts.items():
                    weight = product_weights.get(product, 0)
                    product_score += count * weight

            # 결과 딕셔너리
            result_dict = {
                "상담사": consultant,
                "안마의자": product_counts["안마의자"],
                "라클라우드": product_counts["라클라우드"],
                "정수기": product_counts["정수기"],
                "더케어": product_counts["더케어"],
                "멤버십": product_counts["멤버십"],
                "승인건수": total_count,
                "승인액": total_amount
            }

            # 제품별 모드인 경우 점수 추가
            if analysis_mode == "제품별":
                result_dict["점수"] = product_score

            result_data.append(result_dict)

        # 결과 없음
        if not result_data:
            return None, "조건에 맞는 상담사가 없습니다.", original_filtered_df

        # 데이터프레임 생성
        result_df = pd.DataFrame(result_data)

        # 정렬 기준 설정
        if analysis_mode == "제품별":
            # 1차: 점수, 2차: 승인액
            result_df = result_df.sort_values(by=["점수", "승인액"], ascending=[False, False])
        elif analysis_mode == "금액별":
            # 1차: 승인액, 2차: 승인건수
            result_df = result_df.sort_values(by=["승인액", "승인건수"], ascending=[False, False])
        else:  # 건수별
            # 1차: 승인건수, 2차: 승인액
            result_df = result_df.sort_values(by=["승인건수", "승인액"], ascending=[False, False])

        # 순위 부여
        result_df["순위"] = range(1, len(result_df) + 1)

        # 프로모션 대상 판정
        if analysis_mode == "제품별":
            # 점수 구간에 따른 등급 판정
            def get_tier(score):
                for tier in sorted(promotion_tiers, key=lambda x: x["min_score"], reverse=True):
                    min_score = tier["min_score"]
                    max_score = tier.get("max_score")

                    if max_score is None:
                        # 최대값이 없으면 min_score 이상인 경우
                        if score >= min_score:
                            return tier["name"]
                    else:
                        # 범위 확인
                        if min_score <= score <= max_score:
                            return tier["name"]
                return "대상 제외"

            result_df["프로모션등급"] = result_df["점수"].apply(get_tier)
        else:
            # 건수별/금액별은 최소 기준치 충족 여부만 표시
            result_df["프로모션대상"] = result_df["승인건수"].apply(
                lambda x: "Y" if x >= min_criteria else "N"
            )

        # 컬럼 순서 재정렬
        if analysis_mode == "제품별":
            columns = ["순위", "상담사", "안마의자", "라클라우드", "정수기"]
            if include_services:
                columns.extend(["더케어", "멤버십"])
            columns.extend(["승인건수", "승인액", "점수", "프로모션등급"])
        else:
            columns = ["순위", "상담사", "안마의자", "라클라우드", "정수기"]
            if include_services:
                columns.extend(["더케어", "멤버십"])
            columns.extend(["승인건수", "승인액", "프로모션대상"])

        result_df = result_df[columns]

        return result_df, None, original_filtered_df

    except Exception as e:
        return None, f"분석 중 오류: {str(e)}", None


def analyze_promotion_data(
    df: pd.DataFrame,
    include_products: List[str],
    include_services: bool,
    direct_only: bool,
    criteria: List[str],
    min_condition: int,
    reward_positions: int,
    start_date: Optional[datetime] = None,  # 날짜 범위 시작
    end_date: Optional[datetime] = None,    # 날짜 범위 끝
    promotion_type: str = "포상금",         # 프로모션 유형: "포상금" 또는 "추첨권"
    reward_config: List[Dict[str, int]] = None,  # 포상금 설정 리스트 [{"amount": 금액, "count": 인원수}, ...]
    lottery_weights: Dict[str, int] = None  # 제품별 추첨권 가중치
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    커스텀 프로모션 기준에 따라 상담사별 실적을 분석하는 함수
    
    Args:
        df: 데이터프레임
        include_products: 포함할 제품 목록 (안마의자, 라클라우드, 정수기)
        include_services: 서비스 품목 포함 여부 (더케어, 멤버십)
        direct_only: 직접 판매만 포함할지 여부
        criteria: 기준 목록 (건수, 매출액, 추첨권)
        min_condition: 최소 건수 조건
        reward_positions: 포상 순위 수
        start_date: 시작 날짜 (선택사항)
        end_date: 종료 날짜 (선택사항)
        promotion_type: 프로모션 유형 ("포상금" 또는 "추첨권")
        reward_config: 포상금 설정 리스트 [{"amount": 금액, "count": 인원수}, ...]
        lottery_weights: 제품별 추첨권 가중치 (예: {"안마의자": 3, "라클라우드": 2, "정수기": 1})
        
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: 결과 데이터프레임과 오류 메시지(있는 경우)
    """
    try:
        # 데이터 필터링
        filtered_df = df.copy()
        
        # 날짜 기준 필터링 (주문 일자)
        if start_date is not None and end_date is not None:
            if "주문 일자" in filtered_df.columns:
                # datetime 형식 확인
                if not pd.api.types.is_datetime64_any_dtype(filtered_df["주문 일자"]):
                    filtered_df["주문 일자"] = pd.to_datetime(filtered_df["주문 일자"], errors='coerce')
                
                # 시작일과 종료일 포함하여 필터링
                filtered_df = filtered_df[(filtered_df["주문 일자"] >= start_date) & 
                                         (filtered_df["주문 일자"] <= end_date)]
        
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
            
            # 서비스 품목 마스크 먼저 생성
            care_mask = (
                consultant_df["대분류"].astype(str).str.contains("안마의자", case=False) & 
                consultant_df["판매 유형"].astype(str).str.contains("케어", case=False)
            )
            
            membership_mask = (
                consultant_df["대분류"].astype(str).str.contains("정수기", case=False) & 
                consultant_df["판매 유형"].astype(str).str.contains("멤버십|멤버쉽", case=False)
            )
            
            # 서비스 품목 건수
            care_count = len(consultant_df[care_mask])
            membership_count = len(consultant_df[membership_mask])
            
            # 제품별 건수 - 서비스 제외하고 계산
            anma_count = len(consultant_df[
                consultant_df["대분류"].astype(str).str.contains("안마의자", case=False) & 
                ~care_mask  # 케어 서비스가 아닌 안마의자만 카운트
            ])
            
            lacloud_count = len(consultant_df[
                consultant_df["대분류"].astype(str).str.contains("라클라우드", case=False)
            ])
            
            water_count = len(consultant_df[
                consultant_df["대분류"].astype(str).str.contains("정수기", case=False) & 
                ~membership_mask  # 멤버십이 아닌 정수기만 카운트
            ])
            
            # 총 승인 건수
            total_count = len(consultant_df)
            
            # 총 매출액
            total_amount = consultant_df["매출 금액"].sum()
            
            # 최소 조건 확인
            if total_count < min_condition:
                continue
                
            # 추첨권 계산 (추첨권 프로모션인 경우)
            lottery_tickets = 0
            if promotion_type == "추첨권" and lottery_weights:
                lottery_tickets = (
                    anma_count * lottery_weights.get("안마의자", 0) +
                    lacloud_count * lottery_weights.get("라클라우드", 0) +
                    water_count * lottery_weights.get("정수기", 0) +
                    care_count * lottery_weights.get("더케어", 0) +
                    membership_count * lottery_weights.get("멤버십", 0)
                )
            
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
            
            # 추첨권 프로모션인 경우 추첨권 수 추가
            if promotion_type == "추첨권":
                result_dict["추첨권"] = lottery_tickets
            
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
            # 추첨권 기준 추가
            elif criterion == "추첨권" and promotion_type == "추첨권":
                sort_columns.append("추첨권")
                ascending_values.append(False)  # 내림차순
        
        # 추첨권 모드일 때 기본 정렬 기준 설정 (명시적으로 지정되지 않은 경우)
        if promotion_type == "추첨권" and not sort_columns:
            sort_columns.append("추첨권")
            ascending_values.append(False)  # 내림차순
        
        # 정렬
        if sort_columns:
            result_df = result_df.sort_values(by=sort_columns, ascending=ascending_values)
        
        # 순위 부여
        result_df["순위"] = range(1, len(result_df) + 1)
        
        # 포상금 결정 (포상금 프로모션인 경우)
        if promotion_type == "포상금" and reward_config:
            # 등수 범위별 포상금액 적용
            def get_reward_amount(rank):
                current_pos = 1
                for config in reward_config:
                    amount = config["amount"]
                    count = config["count"]
                    if current_pos <= rank <= current_pos + count - 1:
                        return f"{amount:,d}원"
                    current_pos += count
                return "N"
            
            result_df["포상금"] = result_df["순위"].apply(get_reward_amount)
        else:
            # 추첨권 프로모션 또는 포상금 설정이 없는 경우 포상 획득 여부만 표시
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
        columns.extend(["누적승인(건)", "누적승인(액)"])
        
        # 프로모션 유형에 따른 추가 컬럼
        if promotion_type == "추첨권":
            columns.append("추첨권")
            columns.append("포상획득여부")
        else:  # 포상금 프로모션
            columns.append("포상금" if "포상금" in result_df.columns else "포상획득여부")
        
        # 필요한 컬럼만 선택 및 재정렬
        result_df = result_df[columns]
        
        return result_df, None
        
    except Exception as e:
        return None, f"프로모션 데이터 분석 중 오류가 발생했습니다: {str(e)}"

def create_promotion_excel(result_df: pd.DataFrame, original_df: pd.DataFrame, analysis_mode: str = "건수별") -> Optional[bytes]:
    """
    프로모션 결과와 원본 데이터를 포함한 엑셀 파일 생성 (스타일링 포함)

    Args:
        result_df: 프로모션 분석 결과 데이터프레임
        original_df: 전체 원본 데이터 (의미없는 컬럼만 제거됨, 필터링 안됨)
        analysis_mode: 분석 모드 ("제품별", "건수별", "금액별")

    Returns:
        Optional[bytes]: 엑셀 파일 바이트 데이터
    """
    try:
        output = BytesIO()

        # 결과 데이터를 순위별로 정렬 (순위 컬럼이 있는 경우)
        if '순위' in result_df.columns:
            result_df = result_df.sort_values('순위').reset_index(drop=True)

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 워크북 객체 먼저 가져오기
            workbook = writer.book

            # 시트 1: 프로모션 분석 결과 (수동으로 작성)
            worksheet1 = workbook.add_worksheet('프로모션결과')

            # 시트 2: 원본 데이터
            if original_df is not None and not original_df.empty:
                original_df.to_excel(writer, sheet_name='원본데이터', index=False)

            # === 서식 정의 ===

            # 헤더 서식
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            })

            # 등급별 서식 (제품별 분석용) - 더 선명한 색상
            tier1_format = workbook.add_format({
                'bg_color': '#764ba2',  # 진한 보라
                'font_color': '#FFFFFF',
                'bold': True,
                'border': 1,
                'align': 'center'
            })
            tier2_format = workbook.add_format({
                'bg_color': '#f5576c',  # 핑크
                'font_color': '#FFFFFF',
                'bold': True,
                'border': 1,
                'align': 'center'
            })
            tier3_format = workbook.add_format({
                'bg_color': '#00f2fe',  # 시안
                'font_color': '#FFFFFF',
                'bold': True,
                'border': 1,
                'align': 'center'
            })

            # Y/N 서식 - 더 선명한 색상
            y_format = workbook.add_format({
                'bg_color': '#38ef7d',  # 밝은 초록
                'font_color': '#FFFFFF',
                'bold': True,
                'border': 1,
                'align': 'center'
            })
            n_format = workbook.add_format({
                'bg_color': '#ff6a00',  # 오렌지-빨강
                'font_color': '#FFFFFF',
                'bold': True,
                'border': 1,
                'align': 'center'
            })

            # 숫자 서식
            number_format = workbook.add_format({
                'num_format': '#,##0',
                'border': 1,
                'align': 'right'
            })
            money_format = workbook.add_format({
                'num_format': '₩#,##0',
                'border': 1,
                'align': 'right'
            })
            text_format = workbook.add_format({
                'border': 1,
                'align': 'left'
            })
            center_format = workbook.add_format({
                'border': 1,
                'align': 'center'
            })

            # 순위별 그라데이션 서식 생성 함수 (건수별/금액별 분석용)
            def get_rank_format(rank, max_rank):
                """순위에 따른 그라데이션 색상 계산"""
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

                bg_color = f'#{r:02X}{g:02X}{b:02X}'
                font_color = '#000000' if ratio < 0.7 else '#FFFFFF'
                is_bold = rank <= 3

                fmt = workbook.add_format({
                    'bg_color': bg_color,
                    'font_color': font_color,
                    'bold': is_bold,
                    'border': 1,
                    'align': 'center'
                })
                return fmt

            # === 헤더 행 스타일링 ===
            for col_num, value in enumerate(result_df.columns.values):
                worksheet1.write(0, col_num, value, header_format)

            # === 데이터 행 스타일링 ===
            rank_col_idx = None
            tier_col_idx = None
            yn_col_idx = None

            # 컬럼 인덱스 찾기
            for idx, col in enumerate(result_df.columns):
                if col == '순위':
                    rank_col_idx = idx
                elif col == '프로모션등급':
                    tier_col_idx = idx
                elif col == '프로모션대상':
                    yn_col_idx = idx

            # 순위 최대값 계산 (그라데이션용)
            max_rank = result_df['순위'].max() if '순위' in result_df.columns else 0

            # 데이터 행별 스타일 적용
            for row_idx, row in result_df.iterrows():
                excel_row = row_idx + 1  # 헤더가 0번 행, 데이터는 1번 행부터

                for col_idx, col_name in enumerate(result_df.columns):
                    value = row[col_name]

                    # 제품별 분석: 등급 컬럼만 색상 적용
                    if analysis_mode == '제품별':
                        if col_idx == tier_col_idx and pd.notna(value):
                            val_str = str(value)
                            if '1등급' in val_str:
                                worksheet1.write(excel_row, col_idx, value, tier1_format)
                            elif '2등급' in val_str:
                                worksheet1.write(excel_row, col_idx, value, tier2_format)
                            elif '3등급' in val_str:
                                worksheet1.write(excel_row, col_idx, value, tier3_format)
                            else:
                                worksheet1.write(excel_row, col_idx, value, center_format)

                        # 순위는 색상 없이 중앙 정렬만
                        elif col_idx == rank_col_idx:
                            worksheet1.write(excel_row, col_idx, value if pd.notna(value) else '', center_format)

                        # 숫자 컬럼 포맷팅
                        elif col_name in ['누적승인(액)', '포상금']:
                            if pd.notna(value):
                                worksheet1.write(excel_row, col_idx, value, money_format)
                            else:
                                worksheet1.write(excel_row, col_idx, '', money_format)
                        elif col_name in ['누적승인(건)', '제품점수', '추첨권', '안마의자', '라클라우드', '정수기', '더케어', '멤버십', '안', '라', '정', '케어', '멤버']:
                            if pd.notna(value):
                                worksheet1.write(excel_row, col_idx, value, number_format)
                            else:
                                worksheet1.write(excel_row, col_idx, '', number_format)

                        # 텍스트 컬럼
                        else:
                            worksheet1.write(excel_row, col_idx, value if pd.notna(value) else '', text_format)

                    # 건수별/금액별 분석: 순위에 그라데이션 적용
                    else:
                        # 순위 컬럼 그라데이션 스타일링
                        if col_idx == rank_col_idx and pd.notna(value):
                            try:
                                rank = int(value)
                                rank_fmt = get_rank_format(rank, max_rank)
                                worksheet1.write(excel_row, col_idx, value, rank_fmt)
                            except:
                                worksheet1.write(excel_row, col_idx, value, center_format)

                        # Y/N 컬럼 스타일링 (건수별만)
                        elif col_idx == yn_col_idx and pd.notna(value):
                            val_str = str(value).upper()
                            if val_str == 'Y':
                                worksheet1.write(excel_row, col_idx, value, y_format)
                            elif val_str == 'N':
                                worksheet1.write(excel_row, col_idx, value, n_format)
                            else:
                                worksheet1.write(excel_row, col_idx, value, center_format)

                        # 숫자 컬럼 포맷팅
                        elif col_name in ['누적승인(액)', '포상금']:
                            if pd.notna(value):
                                worksheet1.write(excel_row, col_idx, value, money_format)
                            else:
                                worksheet1.write(excel_row, col_idx, '', money_format)
                        elif col_name in ['누적승인(건)', '제품점수', '추첨권', '안마의자', '라클라우드', '정수기', '더케어', '멤버십', '안', '라', '정', '케어', '멤버']:
                            if pd.notna(value):
                                worksheet1.write(excel_row, col_idx, value, number_format)
                            else:
                                worksheet1.write(excel_row, col_idx, '', number_format)

                        # 텍스트 컬럼
                        else:
                            worksheet1.write(excel_row, col_idx, value if pd.notna(value) else '', text_format)

            # === 열 너비 자동 조정 ===
            for i, col in enumerate(result_df.columns):
                max_len = max(
                    result_df[col].astype(str).map(len).max() if not result_df[col].empty else 0,
                    len(str(col))
                ) + 2
                worksheet1.set_column(i, i, min(max_len, 30))

            # === 원본데이터 시트 헤더 스타일링 ===
            if original_df is not None and not original_df.empty and '원본데이터' in writer.sheets:
                worksheet2 = writer.sheets['원본데이터']
                for col_num, value in enumerate(original_df.columns.values):
                    worksheet2.write(0, col_num, value, header_format)

                # 열 너비 조정
                for i, col in enumerate(original_df.columns):
                    max_len = max(
                        original_df[col].astype(str).map(len).max() if not original_df[col].empty else 0,
                        len(str(col))
                    ) + 2
                    worksheet2.set_column(i, i, min(max_len, 30))

        output.seek(0)
        return output.getvalue()

    except Exception as e:
        print(f"엑셀 파일 생성 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def create_excel_report(result_df: pd.DataFrame, original_df: pd.DataFrame) -> Optional[bytes]:
    """
    기존 호환성을 위한 래퍼 함수
    """
    return create_promotion_excel(result_df, original_df)

def save_promotion_config(config_name: str, config_data: Dict) -> Tuple[bool, Optional[str]]:
    """
    프로모션 설정을 JSON 파일로 저장하는 함수
    
    Args:
        config_name: 설정 이름
        config_data: 설정 데이터 (딕셔너리)
    
    Returns:
        Tuple[bool, Optional[str]]: 성공 여부와 오류 메시지(있는 경우)
    """
    try:
        # 설정 파일 경로
        config_dir = "promotion_configs"
        os.makedirs(config_dir, exist_ok=True)
        
        filename = os.path.join(config_dir, f"{config_name}.json")
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        return True, None
    except Exception as e:
        return False, f"설정 저장 중 오류가 발생했습니다: {str(e)}"

def load_promotion_config(config_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    JSON 파일에서 프로모션 설정을 불러오는 함수
    
    Args:
        config_name: 설정 이름
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: 설정 데이터와 오류 메시지(있는 경우)
    """
    try:
        # 설정 파일 경로
        config_dir = "promotion_configs"
        filename = os.path.join(config_dir, f"{config_name}.json")
        
        # 파일이 존재하지 않는 경우
        if not os.path.exists(filename):
            return None, f"설정 파일이 존재하지 않습니다: {config_name}"
        
        # JSON 파일 불러오기
        with open(filename, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return config_data, None
    except Exception as e:
        return None, f"설정 불러오기 중 오류가 발생했습니다: {str(e)}"

def list_promotion_configs() -> List[str]:
    """
    저장된 프로모션 설정 목록을 반환하는 함수
    
    Returns:
        List[str]: 설정 이름 목록
    """
    config_dir = "promotion_configs"
    os.makedirs(config_dir, exist_ok=True)
    
    # JSON 파일만 필터링
    config_files = [f.replace('.json', '') for f in os.listdir(config_dir) 
                    if f.endswith('.json')]
    
    return config_files