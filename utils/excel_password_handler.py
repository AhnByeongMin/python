"""
비밀번호로 보호된 엑셀 파일 처리 기능

이 모듈은 비밀번호로 보호된 엑셀 파일을 감지하고 처리하는 기능을 제공합니다.
daily_sales_logic.py 및 daily_sales_ui.py에 통합하여 사용합니다.
"""

import pandas as pd
from io import BytesIO
import streamlit as st
import msoffcrypto
import tempfile
from typing import Tuple, Optional

def is_excel_encrypted(file_content: bytes) -> bool:
    """
    엑셀 파일이 비밀번호로 보호되어 있는지 확인하는 함수
    
    Args:
        file_content: 엑셀 파일의 바이너리 내용
        
    Returns:
        bool: 파일이 암호화되어 있으면 True, 아니면 False
    """
    try:
        # 파일 내용을 BytesIO 객체로 변환
        file_input = BytesIO(file_content)
        
        # msoffcrypto 라이브러리로 파일 열기 시도
        excel_file = msoffcrypto.OfficeFile(file_input)
        
        # 암호화 여부 확인
        return excel_file.is_encrypted()
    except Exception as e:
        # 오류 발생 시 False 반환 (안전한 처리를 위해)
        print(f"암호화 확인 중 오류: {str(e)}")
        return False

def decrypt_excel_file(file_content: bytes, password: str) -> Tuple[Optional[BytesIO], Optional[str]]:
    """
    비밀번호로 보호된 엑셀 파일을 복호화하는 함수
    
    Args:
        file_content: 엑셀 파일의 바이너리 내용
        password: 엑셀 파일 비밀번호
        
    Returns:
        Tuple[Optional[BytesIO], Optional[str]]: 복호화된 파일 내용과 오류 메시지(있는 경우)
    """
    try:
        # 파일 내용을 BytesIO 객체로 변환
        file_input = BytesIO(file_content)
        
        # msoffcrypto 라이브러리로 파일 열기
        excel_file = msoffcrypto.OfficeFile(file_input)
        
        # 암호화 여부 확인
        if not excel_file.is_encrypted():
            return BytesIO(file_content), None
        
        # 비밀번호 적용
        try:
            excel_file.load_key(password=password)
        except Exception:
            return None, "잘못된 비밀번호입니다. 다시 시도해주세요."
        
        # 복호화된 내용을 새 BytesIO 객체에 저장
        decrypted_file = BytesIO()
        excel_file.decrypt(decrypted_file)
        
        # 파일 포인터를 처음으로 되돌림
        decrypted_file.seek(0)
        
        return decrypted_file, None
    except Exception as e:
        return None, f"파일 복호화 중 오류가 발생했습니다: {str(e)}"

def handle_excel_with_password(uploaded_file) -> Tuple[Optional[BytesIO], Optional[str]]:
    """
    업로드된 엑셀 파일을 처리하고, 필요한 경우 비밀번호를 입력받는 함수
    
    Args:
        uploaded_file: Streamlit에서 업로드된 파일 객체
        
    Returns:
        Tuple[Optional[BytesIO], Optional[str]]: 처리된 파일 객체와 오류 메시지(있는 경우)
    """
    try:
        # 파일이 없는 경우
        if uploaded_file is None:
            return None, "파일이 업로드되지 않았습니다."
        
        # 파일 내용 읽기
        file_content = uploaded_file.getvalue()
        
        # 암호화 여부 확인
        if is_excel_encrypted(file_content):
            # 비밀번호 입력 UI 표시
            st.info("이 엑셀 파일은 비밀번호로 보호되어 있습니다.")
            password = st.text_input("파일 비밀번호를 입력하세요:", type="password", key=f"password_{uploaded_file.name}")
            
            # 비밀번호가 입력된 경우
            if password:
                with st.spinner('파일 복호화 중...'):
                    # 파일 복호화 시도
                    decrypted_file, error = decrypt_excel_file(file_content, password)
                    
                    if error:
                        return None, error
                    
                    return decrypted_file, None
            else:
                return None, "비밀번호를 입력해주세요."
        else:
            # 암호화되지 않은 파일은 그대로 반환
            return BytesIO(file_content), None
    except Exception as e:
        return None, f"파일 처리 중 오류가 발생했습니다: {str(e)}"