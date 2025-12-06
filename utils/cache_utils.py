"""
Streamlit 캐싱 유틸리티 모듈

데이터 처리 함수들에 대한 캐싱 래퍼를 제공합니다.
캐싱을 통해 동일한 데이터에 대한 반복 처리를 최적화합니다.
"""

import streamlit as st
import pandas as pd
import hashlib
from typing import Optional, Tuple, Dict, Any
from datetime import date


def get_dataframe_hash(df: pd.DataFrame) -> str:
    """
    DataFrame의 해시값을 생성합니다.
    캐싱 키 생성에 사용됩니다.

    Args:
        df: 해시할 DataFrame

    Returns:
        str: DataFrame의 해시값
    """
    if df is None or df.empty:
        return "empty"

    # DataFrame을 bytes로 변환하여 해시
    try:
        df_bytes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
        return hashlib.md5(df_bytes).hexdigest()
    except Exception:
        # 해시 실패 시 shape 기반 간단한 해시
        return f"{len(df)}_{len(df.columns)}"


@st.cache_data(ttl=300, show_spinner=False)
def cached_analyze_approval_data(_df_hash: str, df_json: str) -> pd.DataFrame:
    """
    승인매출 데이터 분석 결과를 캐싱합니다.

    Args:
        _df_hash: DataFrame 해시 (캐시 키용, 언더스코어로 해싱 제외)
        df_json: DataFrame JSON 문자열

    Returns:
        pd.DataFrame: 분석 결과
    """
    from logic.daily_sales_logic import analyze_approval_data_by_product

    df = pd.read_json(df_json, orient='split')
    return analyze_approval_data_by_product(df)


@st.cache_data(ttl=300, show_spinner=False)
def cached_analyze_installation(_df_hash: str, df_json: str) -> pd.DataFrame:
    """
    설치매출 안마의자 분석 결과를 캐싱합니다.

    Args:
        _df_hash: DataFrame 해시 (캐시 키용)
        df_json: DataFrame JSON 문자열

    Returns:
        pd.DataFrame: 분석 결과
    """
    from logic.daily_sales_logic import analyze_installation_by_product_model

    df = pd.read_json(df_json, orient='split')
    return analyze_installation_by_product_model(df)


def analyze_with_cache(df: pd.DataFrame, analysis_type: str = "approval") -> pd.DataFrame:
    """
    캐싱을 적용한 분석 함수 래퍼

    Args:
        df: 분석할 DataFrame
        analysis_type: "approval" 또는 "installation"

    Returns:
        pd.DataFrame: 분석 결과
    """
    if df is None or df.empty:
        return pd.DataFrame()

    try:
        df_hash = get_dataframe_hash(df)
        df_json = df.to_json(orient='split', date_format='iso')

        if analysis_type == "approval":
            return cached_analyze_approval_data(df_hash, df_json)
        elif analysis_type == "installation":
            return cached_analyze_installation(df_hash, df_json)
        else:
            return pd.DataFrame()
    except Exception as e:
        # 캐싱 실패 시 직접 호출
        from logic.daily_sales_logic import (
            analyze_approval_data_by_product,
            analyze_installation_by_product_model
        )

        if analysis_type == "approval":
            return analyze_approval_data_by_product(df)
        elif analysis_type == "installation":
            return analyze_installation_by_product_model(df)
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def cached_promotion_analysis(
    _df_hash: str,
    df_json: str,
    analysis_mode: str,
    include_services: bool,
    include_online: bool,
    product_weights_json: str
) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[pd.DataFrame]]:
    """
    프로모션 분석 결과를 캐싱합니다.

    Returns:
        Tuple: (분석결과 DataFrame, 오류메시지, 원본필터링 DataFrame)
    """
    from logic.promotion_logic import analyze_promotion_data_new
    import json

    df = pd.read_json(df_json, orient='split')
    product_weights = json.loads(product_weights_json)

    return analyze_promotion_data_new(
        df=df,
        analysis_mode=analysis_mode,
        include_services=include_services,
        include_online=include_online,
        product_weights=product_weights
    )


@st.cache_data(ttl=600, show_spinner=False)
def cached_consultant_analysis(
    _consultant_hash: str,
    _calltime_hash: str,
    consultant_json: str,
    calltime_json: str
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[str]]:
    """
    상담원 실적 분석 결과를 캐싱합니다.

    Returns:
        Tuple: (분석결과 DataFrame, 콜타임결과 DataFrame, 오류메시지)
    """
    from logic.consultant_logic import analyze_consultant_performance

    consultant_df = pd.read_json(consultant_json, orient='split')
    calltime_df = pd.read_json(calltime_json, orient='split') if calltime_json else None

    return analyze_consultant_performance(consultant_df, calltime_df)


def clear_all_cache():
    """모든 캐시를 클리어합니다."""
    st.cache_data.clear()


def clear_analysis_cache():
    """분석 관련 캐시만 클리어합니다."""
    # 특정 함수의 캐시만 클리어
    cached_analyze_approval_data.clear()
    cached_analyze_installation.clear()
    cached_promotion_analysis.clear()
    cached_consultant_analysis.clear()
