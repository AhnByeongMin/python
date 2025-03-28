import pandas as pd
import streamlit as st
import base64
from io import BytesIO
import io
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
import plotly.express as px
import plotly.graph_objects as go
import xlsxwriter
import re

# utils.py에서 함수 import
from utils import format_date_columns, copy_to_clipboard, process_datetime

# 데이터 처리 함수
def process_excel(file):
   """
   엑셀 파일을 읽고 데이터를 전처리하는 함수
   
   매개변수:
       file: 업로드된 엑셀 파일 객체
       
   반환값:
       처리된 데이터프레임 또는 오류 메시지
   """
   try:
       # 엑셀 파일 읽기
       df = pd.read_excel(file, parse_dates=True)
       
       # 날짜/시간 컬럼에 대해 process_datetime 적용
       date_time_columns = df.select_dtypes(include=['datetime64']).columns
       
       for col in date_time_columns:
           df[col] = df[col].apply(process_datetime)
       
       # Total 행 체크 및 제거 (A열에 'Total'이 있는 행부터 모두 제거)
       if 'Total' in df.iloc[:, 0].values:
           total_idx = df.iloc[:, 0].eq('Total').idxmax()
           df = df.iloc[:total_idx]
       
       # 빈 열 제거 (Unnamed 열 등)
       df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
       
       # VAT 세율 설정 - 1.1%
       vat_rate = 0.011
       
       # 필요한 컬럼 확인 - 대분류 대신 품목명 사용
       required_columns = ["월 렌탈 금액", "약정 기간 값", "총 패키지 할인 회차", 
                          "판매 금액", "선납 렌탈 금액", "품목명"]
                          
       # 대분류 컬럼이 없고 품목명이 있으면 품목명 사용
       has_product_name = "품목명" in df.columns
       has_category = "대분류" in df.columns
       
       if has_product_name:
           category_column = "품목명"
       elif has_category:
           category_column = "대분류"
           # 대분류 컬럼을 품목명으로 복제
           df["품목명"] = df["대분류"]
       else:
           return None, "품목명 또는 대분류 열이 필요합니다."
       
       # 필수 컬럼 확인 (품목명 제외)
       missing_columns = [col for col in required_columns[:-1] if col not in df.columns]
       if missing_columns:
           return None, f"필요한 열이 없습니다: {', '.join(missing_columns)}"
       
       # 숫자형 변환 (품목명 제외한 모든 필수 컬럼)
       for col in required_columns[:-1]:
           df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
       
       # 매출금액 계산 전 패키지 할인 회차 데이터 정제
       # 39, 59, 60 값은 0으로 대체 (특정 비즈니스 규칙)
       df['총 패키지 할인 회차'] = df['총 패키지 할인 회차'].replace([39, 59, 60], 0)
       
       # 매출금액 계산 공식
       df['매출금액'] = (df['월 렌탈 금액'] * (df['약정 기간 값'] - df['총 패키지 할인 회차']) + 
                      df['판매 금액'] + df['선납 렌탈 금액'])
       
       # VAT 제외 매출금액 계산
       df['매출금액(VAT제외)'] = df['매출금액'] / (1 + vat_rate)
       
       # 날짜 컬럼 포맷팅
       df = format_date_columns(df)
       
       return df, None
   except Exception as e:
       return None, f"파일 처리 중 오류가 발생했습니다: {str(e)}"

# 데이터 분석 함수
def analyze_data(df, filters=None):
    """
    데이터프레임을 분석하여 품목별 집계 결과를 생성하는 함수
    
    매개변수:
        df: 분석할 데이터프레임
        filters: 적용할 필터 딕셔너리 (선택적)
        
    반환값:
        분석 결과 데이터프레임 또는 오류 메시지
    """
    try:
        # 필터가 제공된 경우 데이터프레임 필터링
        if filters:
            for field, filter_value in filters.items():
                if pd.api.types.is_datetime64_any_dtype(df[field]):
                    # 날짜 필드인 경우
                    start_date, end_date = filter_value
                    df = df[(df[field].dt.date >= start_date) & 
                            (df[field].dt.date <= end_date)]
                
                elif pd.api.types.is_numeric_dtype(df[field]):
                    # 숫자 필드인 경우
                    min_val, max_val = filter_value
                    df = df[(df[field] >= min_val) & 
                            (df[field] <= max_val)]
                
                else:
                    # 카테고리/문자열 필드인 경우
                    df = df[df[field].isin(filter_value)]
        
        if '품목명' not in df.columns:
            return None, "품목명 열이 없습니다."
            
        # 품목별 승인건수와 매출금액 집계
        analysis = df.groupby('품목명').agg(
            승인건수=('품목명', 'count'),
            매출금액_VAT제외=('매출금액(VAT제외)', 'sum')
        ).reset_index()
        
        # 지정된 순서로 정렬 (안마의자, 라클라우드, 정수기)
        order = ['안마의자', '라클라우드', '정수기']
        
        # 카테고리형 변환 후 정렬
        analysis['품목명'] = pd.Categorical(
            analysis['품목명'], 
            categories=order, 
            ordered=True
        )
        analysis = analysis.sort_values('품목명')
        
        # 숫자 포맷팅 (천 단위 구분 기호 추가)
        analysis['매출금액_VAT제외_포맷'] = analysis['매출금액_VAT제외'].apply(lambda x: f"{x:,.0f}")
        
        return analysis, None
    except Exception as e:
        return None, f"데이터 분석 중 오류가 발생했습니다: {str(e)}"

# 엑셀 다운로드 함수
def to_excel(df, analysis_df):
    """
    데이터프레임을 엑셀 파일로 변환하는 함수
    
    매개변수:
        df: 원본 데이터프레임
        analysis_df: 분석 결과 데이터프레임
        
    반환값:
        엑셀 바이너리 데이터
    """
    try:
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        
        # 첫 번째 시트 - 승인건수 (필터링된 원본 데이터)
        df.to_excel(writer, sheet_name='승인건수', index=False)
        
        # 두 번째 시트 - 분석데이터 (집계 결과)
        analysis_for_excel = analysis_df.copy()
        
        # 포맷팅된 매출금액 컬럼 사용 (숫자 포맷팅 컬럼으로 대체)
        if '매출금액_VAT제외_포맷' in analysis_for_excel.columns:
            analysis_for_excel.rename(columns={'매출금액_VAT제외_포맷': '매출금액(VAT제외)'}, inplace=True)
            analysis_for_excel.drop('매출금액_VAT제외', axis=1, inplace=True)
        
        # 임시 분석용 숫자 컬럼 제거
        if '매출금액_숫자' in analysis_for_excel.columns:
            analysis_for_excel.drop('매출금액_숫자', axis=1, inplace=True)
        
        # 분석 데이터 저장
        analysis_for_excel.to_excel(writer, sheet_name='분석데이터', index=False)
        
        # 스타일 적용
        workbook = writer.book
        worksheet = writer.sheets['분석데이터']
        
        # 헤더 셀 스타일 정의
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # 헤더 행에 스타일 적용
        for col_num, value in enumerate(analysis_for_excel.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # 컬럼 폭 자동 조정
        for i, col in enumerate(analysis_for_excel.columns):
            column_width = max(len(str(col)), analysis_for_excel[col].astype(str).str.len().max())
            worksheet.set_column(i, i, column_width + 2)  # 여유 공간 추가
        
        writer.close()
        processed_data = output.getvalue()
        return processed_data
    except Exception as e:
        st.error(f"엑셀 파일 생성 중 오류가 발생했습니다: {str(e)}")
        return None

def get_table_download_link(df, analysis_df, filename="분석_결과.xlsx"):
    """
    DataFrame을 엑셀 파일로 다운로드할 수 있는 링크 생성
    
    매개변수:
        df: 원본 데이터프레임
        analysis_df: 분석 결과 데이터프레임
        filename: 다운로드될 파일명
        
    반환값:
        HTML 다운로드 링크
    """
    val = to_excel(df, analysis_df)
    if val is None:
        return '<p class="error-message">엑셀 파일 생성에 실패했습니다.</p>'
    
    # 바이너리 데이터를 base64로 인코딩
    b64 = base64.b64encode(val).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" class="download-button">엑셀 파일 다운로드</a>'
    return href

def show():
    # 타이틀 및 설명
    st.title("📊 매출 데이터 분석 도구")
    st.markdown('<p>이 도구는 엑셀 파일을 분석하여 매출 데이터를 계산하고 필터링할 수 있습니다. 업로드된 데이터에서 매출금액(VAT제외)을 계산하고 대분류별 집계를 수행합니다.</p>', unsafe_allow_html=True)

    # 세션 상태 초기화
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'filtered_df' not in st.session_state:
        st.session_state.filtered_df = None
    if 'analysis_df' not in st.session_state:
        st.session_state.analysis_df = None
    if 'copy_success' not in st.session_state:
        st.session_state.copy_success = False

    # 파일 업로드
    uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=['xlsx', 'xls'])

    # 메인 로직
    if uploaded_file is not None:
        # 파일 처리 및 데이터프레임 생성
        df, error = process_excel(uploaded_file)
        st.session_state.df = df
        
        if error:
            st.error(error)
        else:
            # 원본 데이터 표시
            st.subheader("원본 데이터")
            st.write(f"총 {len(df)}개의 레코드가 로드되었습니다.")
            
            # AgGrid로 인터랙티브 테이블 표시
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            gb.configure_selection('multiple', use_checkbox=True)

            # 날짜 컬럼 포맷 처리
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    gb.configure_column(
                        col,
                        type=["dateColumnFilter", "customDateTimeFormat"],
                        custom_format="%Y-%m-%d",  # 날짜만 표시
                        valueFormatter='value ? value.substr(0, 10) : ""',  # JavaScript 포맷터로 날짜만 추출
                        pivot=True
                    )

            # 시간 컬럼의 경우 별도로 처리
            time_columns = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col]) and 'time' in col.lower()]
            for col in time_columns:
                gb.configure_column(
                    col,
                    type=["dateColumnFilter", "customDateTimeFormat"],
                    custom_format="%H:%M:%S",  # 시간만 표시
                    valueFormatter='value ? value.substr(11, 8) : ""',  # JavaScript 포맷터로 시간만 추출
                    pivot=True
                )
            
            # 그룹화, 집계 기능 설정
            gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)
            gridOptions = gb.build()
            
            # 데이터 그리드 표시
            grid_response = AgGrid(
                df,
                gridOptions=gridOptions,
                update_mode=GridUpdateMode.MODEL_CHANGED,
                height=400,
                enable_enterprise_modules=True,
                allow_unsafe_jscode=True
            )
            
            # 데이터 필터링 UI (접을 수 있는 섹션)
            with st.expander("데이터 필터링", expanded=False):
                # 필터링할 컬럼 선택
                st.markdown("#### 필터링할 컬럼을 선택하세요")
                cols = df.columns.tolist()
                filter_cols = st.multiselect(
                    "필터링할 컬럼 선택",
                    options=cols,
                    default=[]
                )
                
                filtered_df = df.copy()
                
                if filter_cols:
                    # 선택된 각 컬럼에 대한 필터 생성
                    for col in filter_cols:
                        st.markdown(f'### {col}')
                        unique_values = df[col].unique().tolist()
                        
                        # 검색 기능 개선 - 검색 버튼 추가
                        search_col1, search_col2 = st.columns([3, 1])
                        with search_col1:
                            search_term = st.text_input(f"{col} 검색", placeholder="검색어 입력...", key=f"search_{col}")
                        with search_col2:
                            st.markdown("<br>", unsafe_allow_html=True)  # 간격 조정
                            search_button = st.button("검색", key=f"search_btn_{col}")

                        # 검색어를 포함하는 값만 필터링
                        if search_term:
                            filtered_values = [val for val in unique_values if str(search_term).lower() in str(val).lower()]
                            st.write(f"'{search_term}'을(를) 포함한 {len(filtered_values)}개의 항목이 표시됨")
                        else:
                            filtered_values = unique_values
                        
                        # 전체 선택/해제 옵션
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            select_all = st.checkbox(
                                f"전체 선택", 
                                value=True,
                                key=f"all_{col}"
                            )
                        
                        with col2:
                            # 선택된 개수 표시
                            selected_count = len(filtered_values) if select_all else 0
                            st.write(f"선택됨: {selected_count}/{len(filtered_values)}")
                        
                        selected_values = []

                        # 화면 크기에 따라 컬럼 수 결정
                        num_columns = 4  # 기본값으로 4열 사용

                        # 그리드 형태로 체크박스 배치
                        grid_cols = st.columns(num_columns)
                        for i, val in enumerate(filtered_values):
                            val_str = str(val) if not pd.isna(val) else "빈 값"
                            
                            # 각 열에 체크박스 배치
                            with grid_cols[i % num_columns]:
                                is_checked = st.checkbox(
                                    val_str, 
                                    value=select_all,
                                    key=f"cb_{col}_{val}"
                                )
                                
                                if is_checked:
                                    selected_values.append(val)
                        
                        # 선택된 값으로 필터링 (버튼 없이 즉시 적용)
                        filtered_df = filtered_df[filtered_df[col].isin(selected_values)]
                    
                    # 필터가 적용된 데이터프레임 저장
                    st.session_state.filtered_df = filtered_df
                    
                    # 필터링된 데이터 정보 표시
                    st.write(f"현재 {len(filtered_df)}개의 레코드가 필터링되었습니다.")
                else:
                    # 필터가 적용되지 않은 경우 원본 데이터 사용
                    filtered_df = df
                    st.session_state.filtered_df = df
            
            # 분석 결과 표시
            st.subheader("분석 결과")
            
            # 현재 필터링된 데이터 기준으로 분석
            current_df = st.session_state.filtered_df if 'filtered_df' in st.session_state else df
            
            # 분석 데이터 생성
            analysis_df, analysis_error = analyze_data(current_df)
            st.session_state.analysis_df = analysis_df
            
            if analysis_error:
                st.error(analysis_error)
            else:
                # 데이터 요약 정보 표시
                st.write(f"{len(current_df)}개의 레코드로 분석되었습니다.")
                
                # 분석 결과 테이블 표시
                analysis_display = analysis_df.copy()
                
                # 데이터 포맷팅 - 가독성 개선
                if '매출금액_VAT제외_포맷' in analysis_display.columns:
                    analysis_display.rename(columns={'매출금액_VAT제외_포맷': '매출금액(VAT제외)'}, inplace=True)
                    analysis_display.drop('매출금액_VAT제외', axis=1, inplace=True)
                
                # 임시 분석용 컬럼 제거
                if '매출금액_숫자' in analysis_display.columns:
                    analysis_display.drop('매출금액_숫자', axis=1, inplace=True)
                
                # 분석 결과 데이터프레임 표시
                st.dataframe(analysis_display)
                
                # 클립보드 복사 기능 개선
                st.markdown("### 분석 결과 복사")
                st.markdown("아래 버튼을 클릭하여 분석 결과를 클립보드에 복사할 수 있습니다.")

                # 복사할 텍스트 생성 (포맷 개선)
                copy_text = "품목명\t승인건수\t매출금액(VAT제외)\n"  # 헤더 추가
                for _, row in analysis_display.iterrows():
                    copy_text += f"{row['품목명']}\t{row['승인건수']}\t{row['매출금액(VAT제외)']}\n"

                # 복사 버튼 UI
                st.markdown(copy_to_clipboard(copy_text), unsafe_allow_html=True)
                copy_button_html = """
                <button onclick="copyToClipboard()" class="copy-button">
                    결과 클립보드에 복사
                </button>
                <div id="copy-success" style="display:none; color:green; margin-top:5px;">
                    클립보드에 복사되었습니다!
                </div>
                """
                st.markdown(copy_button_html, unsafe_allow_html=True)
                
                # 시각화와 다운로드 탭
                visualization_tab, custom_analysis_tab, download_tab = st.tabs(["시각화", "커스텀 분석", "다운로드"])
                
                with visualization_tab:
                    col1, col2 = st.columns(2)
                    
                    # 매출금액 숫자 컬럼 추가 (시각화 용도)
                    if '매출금액_숫자' not in analysis_df.columns:
                        analysis_df['매출금액_숫자'] = analysis_df['매출금액_VAT제외']
                    
                    with col1:
                        # 승인건수 막대 그래프
                        fig = px.bar(
                            analysis_df, 
                            x='품목명', 
                            y='승인건수',
                            text='승인건수',
                            title='품목별 승인건수',
                            color='품목명',
                            color_discrete_sequence=px.colors.qualitative.G10
                        )
                        fig.update_layout(
                            height=400,
                            xaxis_title="품목명",
                            yaxis_title="승인건수",
                            font=dict(size=12)
                        )
                        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # 매출액 파이 차트
                        fig2 = px.pie(
                            analysis_df, 
                            values='매출금액_숫자', 
                            names='품목명',
                            title='품목별 매출금액(VAT제외) 비율',
                            color_discrete_sequence=px.colors.qualitative.G10
                        )
                        fig2.update_layout(
                            height=400,
                            font=dict(size=12)
                        )
                        fig2.update_traces(texttemplate='%{percent:.1%}', textinfo='label+percent')
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # 종합 대시보드
                    st.subheader("종합 대시보드")
                    
                    fig3 = go.Figure()
                    
                    fig3.add_trace(go.Bar(
                        x=analysis_df['품목명'],
                        y=analysis_df['승인건수'],
                        name='승인건수',
                        marker_color='indianred',
                        text=analysis_df['승인건수'],
                        texttemplate='%{text:,}',
                        textposition='outside'
                    ))
                    
                    fig3.add_trace(go.Scatter(
                        x=analysis_df['품목명'],
                        y=analysis_df['매출금액_숫자'],
                        mode='lines+markers',
                        name='매출금액(VAT제외)',
                        marker_color='royalblue',
                        yaxis='y2',
                        text=analysis_df['매출금액_숫자'].apply(lambda x: f"{x:,.0f}"),
                        textposition='top center'
                    ))
                    
                    fig3.update_layout(
                        title='품목별 승인건수 및 매출금액',
                        xaxis=dict(title='품목명', tickfont=dict(size=12)),
                        yaxis=dict(title='승인건수', side='left', tickformat=','),
                        yaxis2=dict(title='매출금액(VAT제외)', side='right', overlaying='y', tickformat=','),
                        legend=dict(x=0.1, y=1.1, orientation='h'),
                        height=500,
                        font=dict(size=12)
                    )
                    
                    st.plotly_chart(fig3, use_container_width=True)
                
                with custom_analysis_tab:
                    st.subheader("피벗 테이블 분석")
                    
                    # 좌우 레이아웃으로 구성
                    config_col, result_col = st.columns([1, 2])
                    
                    with config_col:
                        st.markdown("### 피벗 테이블 필드")
                        
                        # 사용 가능한 필드 분류
                        all_fields = current_df.columns.tolist()
                        dimension_fields = [col for col in all_fields 
                                    if not pd.api.types.is_numeric_dtype(current_df[col])]
                        measure_fields = [col for col in all_fields 
                                    if pd.api.types.is_numeric_dtype(current_df[col])]
                        
                        # 필터 영역 추가
                        st.markdown("#### 필터 필드")
                        filter_fields = st.multiselect(
                            "필터로 사용할 필드",
                            options=all_fields,
                            default=[]
                        )
                        
                        # 필터 설정 UI
                        filtered_data = current_df.copy()
                        
                        if filter_fields:
                            st.markdown("##### 필터 설정:")
                            
                            for field in filter_fields:
                                st.markdown(f"**{field}** 필터:")
                                
                                # 필드 타입에 따라 다른 필터 UI 제공
                                if pd.api.types.is_datetime64_any_dtype(filtered_data[field]):
                                    # 날짜 필드인 경우 날짜 범위 선택
                                    min_date = filtered_data[field].min().date()
                                    max_date = filtered_data[field].max().date()
                                    
                                    date_col1, date_col2 = st.columns(2)
                                    with date_col1:
                                        start_date = st.date_input(
                                            "시작일",
                                            value=min_date,
                                            min_value=min_date,
                                            max_value=max_date,
                                            key=f"pivot_start_date_{field}"
                                        )
                                    with date_col2:
                                        end_date = st.date_input(
                                            "종료일",
                                            value=max_date,
                                            min_value=min_date,
                                            max_value=max_date,
                                            key=f"pivot_end_date_{field}"
                                        )
                                    
                                    # 필터 적용
                                    filtered_data = filtered_data[(filtered_data[field].dt.date >= start_date) & 
                                                                (filtered_data[field].dt.date <= end_date)]
                                    
                                elif pd.api.types.is_numeric_dtype(filtered_data[field]):
                                    # 숫자 필드인 경우 슬라이더
                                    min_val = float(filtered_data[field].min())
                                    max_val = float(filtered_data[field].max())
                                    
                                    value_range = st.slider(
                                        "값 범위",
                                        min_value=min_val,
                                        max_value=max_val,
                                        value=(min_val, max_val),
                                        key=f"pivot_range_{field}"
                                    )
                                    
                                    # 필터 적용
                                    filtered_data = filtered_data[(filtered_data[field] >= value_range[0]) & 
                                                                (filtered_data[field] <= value_range[1])]
                                    
                                else:
                                    # 카테고리/문자열 필드인 경우 다중 선택
                                    unique_values = filtered_data[field].dropna().unique()
                                    
                                    # 전체 선택/해제 옵션
                                    select_all = st.checkbox(
                                        "전체 선택",
                                        value=True,
                                        key=f"pivot_all_{field}"
                                    )
                                    
                                    if select_all:
                                        selected_values = list(unique_values)
                                    else:
                                        selected_values = st.multiselect(
                                            "값 선택",
                                            options=unique_values,
                                            default=list(unique_values),
                                            key=f"pivot_values_{field}"
                                        )
                                    
                                    # 필터 적용
                                    filtered_data = filtered_data[filtered_data[field].isin(selected_values)]
                            
                            # 필터 적용 후 레코드 수 표시
                            st.write(f"필터 적용 후 {len(filtered_data)}개의 레코드가 선택되었습니다.")
                        
                        # 행 영역 (계층적 구조 지원)
                        st.markdown("#### 행 필드")
                        row_fields = st.multiselect(
                            "행으로 사용할 필드 (순서대로 계층 구조가 적용됩니다)",
                            options=dimension_fields,
                            default=[]
                        )
                        
                        # 열 영역
                        st.markdown("#### 열 필드")
                        column_fields = st.multiselect(
                            "열로 사용할 필드",
                            options=dimension_fields,
                            default=[]
                        )
                        
                        # 값 영역 (여러 값 지원)
                        st.markdown("#### 값 필드")
                        
                        # 세션 상태로 값 필드 관리
                        if 'value_fields' not in st.session_state:
                            st.session_state.value_fields = []
                            st.session_state.agg_functions = []
                        
                        # 필드와 집계 함수 선택 UI
                        new_value_col1, new_value_col2, new_value_col3 = st.columns([2, 2, 1])
                        
                        with new_value_col1:
                            new_value_field = st.selectbox(
                                "값 필드",
                                options=measure_fields,
                                index=measure_fields.index('매출금액(VAT제외)') if '매출금액(VAT제외)' in measure_fields else 0
                            )
                        
                        with new_value_col2:
                            new_agg_function = st.selectbox(
                                "집계 함수",
                                options=["합계", "평균", "최댓값", "최솟값", "개수"],
                                index=0
                            )
                        
                        with new_value_col3:
                            st.write(" ")
                            st.write(" ")
                            if st.button("추가", key="add_value"):
                                # 중복 검사
                                field_agg_pair = (new_value_field, new_agg_function)
                                if field_agg_pair not in zip(st.session_state.value_fields, st.session_state.agg_functions):
                                    st.session_state.value_fields.append(new_value_field)
                                    st.session_state.agg_functions.append(new_agg_function)
                                    st.rerun()
                        
                        # 추가된 값 필드 목록
                        if st.session_state.value_fields:
                            st.markdown("##### 추가된 값 필드:")
                            for i, (field, agg) in enumerate(zip(st.session_state.value_fields, st.session_state.agg_functions)):
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.markdown(f"**{i+1}.** {agg}: {field}")
                                with col2:
                                    if st.button("삭제", key=f"remove_{i}"):
                                        st.session_state.value_fields.pop(i)
                                        st.session_state.agg_functions.pop(i)
                                        st.rerun()
                        else:
                            st.info("값 필드를 추가해주세요.")
                        
                        # 추가 옵션
                        st.markdown("#### 추가 옵션")
                        show_totals = st.checkbox("합계 표시", value=True)
                        
                    with result_col:
                        # 피벗 테이블 결과 영역
                        st.markdown("### 피벗 테이블 결과")
                        
                        # 필드가 선택되었는지 확인
                        if not row_fields and not column_fields:
                            st.info("분석을 시작하려면 행 또는 열 필드를 선택하세요.")
                        elif not st.session_state.value_fields:
                            st.info("분석을 시작하려면 값 필드를 추가하세요.")
                        else:
                            try:
                                # 집계 함수 매핑
                                agg_map = {
                                    "합계": "sum",
                                    "평균": "mean", 
                                    "최댓값": "max",
                                    "최솟값": "min",
                                    "개수": "count"
                                }
                                
                                # 집계 함수 딕셔너리 생성
                                agg_dict = {}
                                for field, agg in zip(st.session_state.value_fields, st.session_state.agg_functions):
                                    agg_dict[field] = agg_map[agg]
                                
                                # 기존 pivot_table 사용
                                pivot = pd.pivot_table(
                                    filtered_data,  # 필터링된 데이터 사용
                                    values=st.session_state.value_fields,
                                    index=row_fields,
                                    columns=column_fields,
                                    aggfunc=agg_dict,
                                    margins=show_totals,
                                    margins_name="총합계"
                                )
                                
                                # 결과 표시 (포맷팅 적용)
                                st.dataframe(pivot.style.format("{:,.0f}"), height=600)
                                
                                # 다운로드 버튼
                                csv = pivot.to_csv()
                                st.download_button(
                                    label="CSV 다운로드",
                                    data=csv,
                                    file_name="pivot_table.csv",
                                    mime="text/csv",
                                )
                                
                            except Exception as e:
                                st.error(f"피벗 테이블 생성 중 오류가 발생했습니다: {str(e)}")
                                st.info("행과 열 필드 구성을 확인해보세요. 데이터에 따라 일부 조합이 작동하지 않을 수 있습니다.")
                
                with download_tab:
                    # 엑셀 다운로드 기능
                    st.markdown("### 엑셀 파일 다운로드")
                    st.markdown("아래 버튼을 클릭하여 데이터와 분석 결과를 엑셀 파일로 다운로드하세요.")
                    st.markdown(get_table_download_link(current_df, analysis_df), unsafe_allow_html=True)
                    
                    # 다운로드 가이드
                    st.markdown("""
                    #### 다운로드 파일 내용:
                    1. **승인건수** 시트: 필터링된 데이터와 매출금액(VAT제외) 컬럼이 포함된 원본 데이터
                    2. **분석데이터** 시트: 대분류별 승인건수와 매출금액(VAT제외) 요약 데이터
                    """)
    else:
        # 파일 업로드 전 안내 화면
        st.info("엑셀 파일을 업로드하면 데이터 분석이 시작됩니다.")
        
        # 사용 가이드
        st.markdown("""
        ### 사용 가이드
        1. 엑셀 파일을 업로드합니다.
        2. 원본 데이터를 확인합니다.
        3. 필요한 경우 '데이터 필터링' 섹션을 펼쳐 필터를 적용합니다.
        4. 분석 결과 섹션에서 품목별 집계 결과를 확인합니다.
        5. 시각화 탭에서 그래프로 분석 결과를 확인합니다.
        6. 다운로드 탭에서 결과를 엑셀 파일로 내려받을 수 있습니다.
        
        ### 필수 컬럼
        - 월 렌탈 금액
        - 약정 기간 값
        - 총 패키지 할인 회차
        - 판매 금액
        - 선납 렌탈 금액
        - 대분류 또는 품목명
        """)