#streamlit run .\new-dash.py

import streamlit as st
import pandas as pd
import json
import time
import numpy as np
import os
from datetime import datetime

# JSON 파일 로드
@st.cache_data(ttl=None)  # 수동으로 캐시 초기화할 때만 갱신
def load_data():
    try:
        with open('현황.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        df = pd.DataFrame(data)
        
        # 날짜 컬럼을 datetime 타입으로 변환
        date_columns = ['착수일', '중간보고', '내부마감', '보고예정일', '요청일', '보고완료일']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except FileNotFoundError:
        # 파일이 없을 경우 빈 DataFrame 생성
        st.warning('현황.json 파일이 없습니다. 새 파일을 생성합니다.')
        with open('현황.json', 'w', encoding='utf-8') as file:
            json.dump([], file, ensure_ascii=False, indent=2)
        return pd.DataFrame()
    except json.JSONDecodeError:
        st.error('JSON 파일 형식이 올바르지 않습니다. 파일을 확인하세요.')
        return pd.DataFrame()
    except Exception as e:
        st.error(f'파일 로드 중 오류 발생: {e}')
        return pd.DataFrame()

# 페이지 설정 - 와이드 모드 적용
st.set_page_config(layout="wide")

# 페이지 제목 설정
st.title('🚩팔도 현황 대시보드')

# 새로고침 버튼 (페이지 상단에 배치)
if st.button('데이터 새로고침', key='refresh_data'):
    load_data.clear()  # 캐시 초기화
    st.success('데이터를 새로고침했습니다!')
    time.sleep(0.5)
    st.rerun()  # 페이지 새로고침

# 수정된 데이터를 JSON 파일로 저장하는 함수
def save_data(dataframe):
    try:
        # DataFrame의 복사본 생성
        save_df = dataframe.copy()
        
        # 모든 NaT 값을 None으로 변환 (사전 처리)
        for col in save_df.columns:
            if pd.api.types.is_datetime64_any_dtype(save_df[col]):
                save_df[col] = save_df[col].astype(object).where(~pd.isna(save_df[col]), None)
        
        # 데이터프레임을 리스트로 변환
        data_list = []
        for _, row in save_df.iterrows():
            row_dict = {}
            for col, val in row.items():
                # 날짜 타입 처리
                if isinstance(val, (pd.Timestamp, pd.DatetimeIndex)):
                    row_dict[col] = val.strftime('%Y-%m-%d')
                # None, NaN 처리
                elif val is None or (isinstance(val, float) and np.isnan(val)):
                    row_dict[col] = None
                # 기타 값은 그대로 사용
                else:
                    row_dict[col] = val
            data_list.append(row_dict)
        
        # 향상된 JSON 인코더
        class EnhancedJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                # NaT 체크 - 다양한 방법 사용
                if str(obj) == 'NaT' or (hasattr(obj, '__class__') and obj.__class__.__name__ == 'NaTType'):
                    return None
                
                # 날짜/시간 타입 처리
                if isinstance(obj, (pd.Timestamp, pd.DatetimeIndex)):
                    return obj.strftime('%Y-%m-%d')
                # NumPy 타입 처리
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (np.int64, np.int32)):
                    return int(obj)
                elif isinstance(obj, (np.float64, np.float32)):
                    return float(obj)
                # 그 외 모든 경우
                try:
                    return super().default(obj)
                except TypeError:
                    # 최후의 방어: 문자열로 변환 시도
                    return str(obj)
        
        # JSON 파일로 저장
        with open('현황.json', 'w', encoding='utf-8') as file:
            json.dump(data_list, file, ensure_ascii=False, indent=2, cls=EnhancedJSONEncoder)
        
        # 백업 폴더 생성 (없는 경우)
        backup_dir = 'back_up'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # 새 백업 파일 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{backup_dir}/현황_{timestamp}.json"
        
        # 백업 파일 저장
        with open(backup_filename, 'w', encoding='utf-8') as backup_file:
            json.dump(data_list, backup_file, ensure_ascii=False, indent=2, cls=EnhancedJSONEncoder)
        
        # 백업 파일 수 제한 (최대 20개)
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('현황_') and f.endswith('.json')]
        backup_files.sort()  # 시간순 정렬 (오래된 것부터)
        
        # 최대 백업 파일 수를 초과하면 오래된 것부터 삭제
        max_backups = 20
        if len(backup_files) > max_backups:
            files_to_delete = backup_files[:(len(backup_files) - max_backups)]
            for file_to_delete in files_to_delete:
                os.remove(os.path.join(backup_dir, file_to_delete))
        
        # 캐시 초기화
        load_data.clear()
        
        st.success(f'데이터가 성공적으로 저장되었습니다!')
        return True
    except Exception as e:
        st.error(f'파일 저장 중 오류 발생: {e}')
        # 오류 메시지 표시
        import traceback
        st.write("오류 상세:", str(e))
        st.write("스택 트레이스:", traceback.format_exc())
        return False

# 데이터 로드
df = load_data()

# 새 데이터 추가 함수
def add_new_data(new_data):
    try:
        # 필수 필드 검증
        required_fields = ['입력자', '진행상품', '유형']
        missing_fields = [field for field in required_fields if field in new_data and (new_data[field] is None or new_data[field] == '')]
        
        if missing_fields:
            st.error(f'다음 필드는 필수입니다: {", ".join(missing_fields)}')
            return False
            
        # 기존 데이터 로드
        current_df = load_data()
        
        # 품목상세 데이터 유효성 확인 및 처리
        if '품목상세' in new_data:
            # 디버깅 정보 출력
            st.write("저장 전 품목상세 데이터 타입:", type(new_data['품목상세']))
            st.write("저장 전 품목상세 데이터 내용:", new_data['품목상세'])
            
            # 품목상세가 빈 문자열이거나 None인 경우 해당 유형에 맞는 기본값 설정
            if new_data['품목상세'] == "" or new_data['품목상세'] is None:
                if new_data['유형'] == '체험단' and 'items_list' in st.session_state:
                    new_data['품목상세'] = st.session_state.items_list
                elif new_data['유형'] == '⚡패키지충전(체험단)':
                    price_key = f"{new_data['유형']}_price_info"
                    if price_key in st.session_state:
                        new_data['품목상세'] = st.session_state[price_key]
                elif new_data['유형'] in ['가구매', '핫딜&침투', '⚡패키지충전']:
                    price_key = f"{new_data['유형']}_price_info"
                    if price_key in st.session_state:
                        new_data['품목상세'] = st.session_state[price_key]
        
        # 날짜 필드를 문자열로 변환 (JSON 직렬화를 위해)
        date_fields = ['요청일', '착수일', '중간보고', '내부마감', '보고예정일', '보고완료일']
        for field in date_fields:
            if field in new_data and new_data[field] is not None:
                if isinstance(new_data[field], pd.Timestamp) or hasattr(new_data[field], 'strftime'):
                    new_data[field] = new_data[field].strftime('%Y-%m-%d')
        
        # 새 데이터를 DataFrame으로 변환하고 기존 데이터에 추가
        new_row = pd.DataFrame([new_data])
        updated_df = pd.concat([current_df, new_row], ignore_index=True)
        
        # 저장
        if save_data(updated_df):
            st.success('새 데이터가 성공적으로 추가되었습니다!')
            time.sleep(1)
            st.rerun()
            return True
    except Exception as e:
        st.error(f'데이터 추가 중 오류 발생: {e}')
        st.write("오류 상세:", str(e))
        import traceback
        st.write("스택 트레이스:", traceback.format_exc())
        return False

# 데이터가 있는지 확인
if not df.empty:
    # 품목상세 컬럼이 있으면 JSON 객체를 문자열로 변환
    display_df = df.copy()
    if '품목상세' in display_df.columns:
        display_df['품목상세'] = display_df['품목상세'].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x)
    
    # 상태 컬럼에 대한 콤보박스 옵션 설정
    column_config = {}
    
    if '상태' in df.columns:
        # 기존 데이터에서 고유한 상태 값 추출
        status_options = df['상태'].dropna().unique().tolist()
        # 추가 옵션이 필요하면 여기에 추가
        additional_options = ['🟡시작전', '🟠진행중', '완료']
        # 중복 제거하고 모든 옵션 합치기
        all_status_options = sorted(list(set(status_options + additional_options)))
        
        # 상태 컬럼 설정 추가
        column_config['상태'] = st.column_config.SelectboxColumn(
            '상태',
            help='현재 상태를 선택하세요',
            width='medium',
            options=all_status_options,
            required=True
        )
    
    # 품목상세 컬럼에 대한 JSON 뷰 설정 추가
    if '품목상세' in df.columns:
        # JsonColumn이 없으므로 TextColumn으로 대체
        column_config['품목상세'] = st.column_config.TextColumn(
            '품목상세',
            help='품목 세부 정보',
            width='medium'
        )
        
        # 품목상세 컬럼 데이터를 포맷팅하여 보기 좋게 변환
        def format_json_display(json_data):
            if pd.isna(json_data) or json_data is None or json_data == '':
                return ''
            try:
                if isinstance(json_data, str):
                    data = json.loads(json_data)
                else:
                    data = json_data
                # 포맷팅된 JSON 문자열 반환
                return json.dumps(data, ensure_ascii=False, indent=2)
            except:
                return json_data
                
        display_df['품목상세'] = display_df['품목상세'].apply(format_json_display)
    
    # 날짜 컬럼에 대한 달력 선택기 추가
    date_columns = ['착수일', '중간보고', '내부마감', '보고예정일', '요청일']
    for col in date_columns:
        if col in display_df.columns:
            column_config[col] = st.column_config.DateColumn(
                col,
                help=f'{col}을 선택하세요',
                min_value=None,  # 최소 날짜 제한 없음
                max_value=None,  # 최대 날짜 제한 없음
                format="YYYY-MM-DD",  # 날짜 형식
                step=1  # 일 단위로 선택
            )
    
    # 탭 생성
    tab_main, tab_dashboard, tab_team1, tab_team2, tab_team3, tab_team_separate = st.tabs(["메인","대시보드", "1팀", "2팀", "3팀", "별도"])
    

        
    # 메인 탭 - 전체 데이터 표시
    with tab_main:
        st.subheader('전체 데이터')
        
        # 필터링 기능 추가 - 3개 컬럼으로 구성
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        # 유형별 필터
        with filter_col1:
            if '유형' in df.columns:
                all_types = ['전체'] + sorted(df['유형'].dropna().unique().tolist())
                selected_type = st.selectbox('유형별 필터', all_types, key='filter_type')
        
        # 팀별 필터
        with filter_col2:
            if '팀' in df.columns:
                all_teams = ['전체'] + sorted(df['팀'].dropna().unique().tolist())
                selected_team = st.selectbox('팀별 필터', all_teams, key='filter_team')
        
        # 상태별 필터
        with filter_col3:
            if '상태' in df.columns:
                all_status = ['전체'] + sorted(df['상태'].dropna().unique().tolist())
                selected_status = st.selectbox('상태별 필터', all_status, key='filter_status')
        
        # 필터링 적용
        filtered_df = display_df.copy()
        
        # 유형 필터 적용
        if '유형' in df.columns and selected_type != '전체':
            filtered_df = filtered_df[filtered_df['유형'] == selected_type]
            
        # 팀 필터 적용
        if '팀' in df.columns and selected_team != '전체':
            filtered_df = filtered_df[filtered_df['팀'] == selected_team]
            
        # 상태 필터 적용
        if '상태' in df.columns and selected_status != '전체':
            filtered_df = filtered_df[filtered_df['상태'] == selected_status]
        
        # 필터링된 데이터 표시
        edited_df = st.data_editor(
            filtered_df, 
            use_container_width=True, 
            key='data_editor_main',
            column_config=column_config,
            height=800  # 높이를 800px로 설정 (기본값보다 크게)
        )
        
        # 저장 버튼 왼쪽 배치
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:  # col2에서 col1으로 변경
            if st.button('변경사항 저장', key='save_main'):
                if save_data(edited_df):
                    time.sleep(1)  # 성공 메시지를 잠시 표시
                    st.rerun()  # 페이지 새로고침하여 업데이트된 데이터 표시
        
        # 토글 상태를 세션 상태에 저장
        if 'add_data_expanded' not in st.session_state:
            st.session_state.add_data_expanded = False

        # 토글 상태 변경 함수
        def toggle_expander():
            st.session_state.add_data_expanded = not st.session_state.add_data_expanded

        # 토글 상태를 유지하는 expander
        # with st.expander("새 데이터 추가", expanded=st.session_state.add_data_expanded): #접은상태
        with st.expander("새 데이터 추가", expanded=True): #열린상태
            # 필수 필드 및 기본 필드 정의
            new_data = {}
            
            # 4개의 컬럼 생성
            col1, col2, col3, col4 = st.columns(4)
            
            # 1컬럼: 입력자, 진행상품, 건수, 유형
            with col1:
                st.markdown("### 기본 정보")
                if '입력자' in df.columns:
                    new_data['입력자'] = st.text_input('입력자', value="신현빈", key='new_입력자')
                if '프로젝트명' in df.columns:
                    new_data['프로젝트명'] = st.text_input('프로젝트명', key='new_project_name')
                if '진행상품' in df.columns:
                    new_data['진행상품'] = st.text_input('진행상품', key='new_진행상품')
                if '유형' in df.columns:
                    type_options = ['', '체험단', '가구매', '핫딜&침투', '⚡패키지충전', '⚡패키지충전(체험단)']
                    selected_type = st.selectbox('유형', type_options, key='new_유형')
                    new_data['유형'] = selected_type
                    
                    # 초기 품목상세 값을 빈 리스트로 설정
                    if '품목상세' in df.columns and '품목상세' not in new_data:
                        new_data['품목상세'] = []
                    
                    # 선택된 유형에 따라 추가 정보 섹션 표시
                    if selected_type == '체험단':
                        st.markdown("### 추가 정보 (체험단)")
                        
                        # 세션 상태에 품목 목록 초기화
                        if 'items_list' not in st.session_state:
                            st.session_state.items_list = []
                        
                        # 품목 추가 함수 정의
                        def add_item():
                            st.session_state.items_list.append({
                                "개별품목": "",
                                "개별건수": 0,
                                "개별단가": 15000
                            })
                        
                        # 품목 추가 버튼 - on_click 이벤트 사용
                        st.button("품목 추가", key="add_item_btn", on_click=add_item)
                        
                        # 품목이 없으면 기본 항목 추가
                        if not st.session_state.items_list:
                            st.session_state.items_list.append({
                                "개별품목": "",
                                "개별건수": 0,
                                "개별단가": 15000
                            })
                        
                        # 품목 삭제 함수 정의
                        def remove_item(idx):
                            if len(st.session_state.items_list) > 1:  # 최소 1개 항목은 유지
                                st.session_state.items_list.pop(idx)
                        
                        # 각 품목 항목 표시
                        for i, item in enumerate(st.session_state.items_list):
                            st.markdown(f"**품목 #{i+1}**")
                            col_item, col_remove = st.columns([5, 1])
                            
                            # 삭제 버튼 - on_click 이벤트 사용
                            if col_remove.button("삭제", key=f"remove_item_{i}", on_click=remove_item, args=(i,)):
                                pass  # 실제 삭제는 on_click 함수에서 처리
                            
                            # 품목 정보 입력 - 셀렉박스로 변경
                            platform_options = ["블로그", "인스타그램", "인스타그램-릴스", "유튜브 쇼츠", "직접입력"]
                            selected_platform = col_item.selectbox(
                                "개별품목", 
                                platform_options, 
                                key=f"item_platform_{i}",
                                index=platform_options.index(item["개별품목"]) if item["개별품목"] in platform_options else 0
                            )
                            
                            # 직접입력인 경우 텍스트 입력 필드 표시
                            if selected_platform == "직접입력":
                                custom_item = col_item.text_input(
                                    "직접 입력", 
                                    value="" if item["개별품목"] in platform_options else item["개별품목"],
                                    key=f"custom_item_{i}"
                                )
                                # 직접 입력된 값을 품목 정보에 저장
                                item["개별품목"] = custom_item
                            else:
                                # 선택된 옵션을 품목 정보에 저장
                                item["개별품목"] = selected_platform
                            
                            item["개별건수"] = col_item.number_input("개별건수", min_value=0, value=item["개별건수"], key=f"item_count_{i}")
                            item["개별단가"] = col_item.number_input("개별단가", min_value=0, value=item["개별단가"], key=f"item_price_{i}")
                            
                            st.markdown("---")
                        
                        # 품목상세 필드에 품목 정보 저장
                        if '품목상세' in df.columns:
                            if selected_type == '체험단' and len(st.session_state.items_list) > 0:
                                new_data['품목상세'] = st.session_state.items_list.copy()
                                st.write("체험단 품목상세 설정됨:", new_data['품목상세'])
                            elif selected_type in ['가구매', '핫딜&침투', '⚡패키지충전', '⚡패키지충전(체험단)']:
                                price_key = f"{selected_type}_price_info"
                                if price_key in st.session_state and len(st.session_state[price_key]) > 0:
                                    new_data['품목상세'] = st.session_state[price_key].copy()
                                    st.write(f"{selected_type} 품목상세 설정됨:", new_data['품목상세'])
                    
                    # 가구매, 핫딜&침투, 패키지충전 또는 패키지충전(체험단)이 선택된 경우 추가 정보 섹션 표시
                    elif selected_type in ['가구매', '핫딜&침투', '⚡패키지충전', '⚡패키지충전(체험단)']:
                        section_title = f"추가 정보 ({selected_type})"
                        st.markdown(f"### {section_title}")
                        
                        # 세션 상태에 가격 정보 초기화
                        price_key = f"{selected_type}_price_info"
                        if price_key not in st.session_state:
                            if selected_type == '가구매':
                                st.session_state[price_key] = [{"상품가": 0, "배송비": 0, "체험단": 8000, "수량": 1}]
                            elif selected_type == '⚡패키지충전':
                                st.session_state[price_key] = [{"패키지충전": 10000000}]
                            elif selected_type == '⚡패키지충전(체험단)':
                                st.session_state[price_key] = [{"개별품목": "패키지1000", "개별건수": 1, "개별단가": 1000000}]
                            else:  # 핫딜&침투인 경우
                                st.session_state[price_key] = [{"커뮤니티": "", "체험단": 100000, "수량": 1}]
                        
                        # 정보 추가 함수 정의
                        def add_price_info():
                            if selected_type == '가구매':
                                st.session_state[price_key].append({"상품가": 0, "배송비": 0, "체험단": 8000, "수량": 1})
                            elif selected_type == '⚡패키지충전':
                                st.session_state[price_key].append({"패키지충전": 10000000})
                            elif selected_type == '⚡패키지충전(체험단)':
                                st.session_state[price_key].append({"개별품목": "패키지1000", "개별건수": 1, "개별단가": 1000000})
                            else:  # 핫딜&침투인 경우
                                st.session_state[price_key].append({"커뮤니티": "", "체험단": 100000, "수량": 1})
                        
                        # 패키지충전 유형이 아닌 경우만 정보 추가 버튼 표시
                        if selected_type != '⚡패키지충전':
                            st.button("정보 추가", key=f"add_{selected_type}_info", on_click=add_price_info)
                        
                        # 정보 삭제 함수 정의
                        def remove_price_info(idx):
                            if len(st.session_state[price_key]) > 1:  # 최소 1개 항목은 유지
                                st.session_state[price_key].pop(idx)
                        
                        # 각 가격 정보 항목 표시
                        for i, price_info in enumerate(st.session_state[price_key]):
                            # 패키지충전인 경우 항목 번호 표시하지 않음
                            if selected_type != '⚡패키지충전':
                                st.markdown(f"**{selected_type} 정보 #{i+1}**")
                                col_price, col_remove = st.columns([5, 1])
                                
                                # 삭제 버튼 (패키지충전 제외)
                                if col_remove.button("삭제", key=f"remove_{selected_type}_info_{i}", on_click=remove_price_info, args=(i,)):
                                    pass  # 실제 삭제는 on_click 함수에서 처리
                            else:
                                col_price = st
                            
                            # 가격 정보 입력 - 유형에 따라 다른 필드 표시
                            if selected_type == '가구매':
                                price_info["상품가"] = col_price.number_input(
                                    "상품가", min_value=0, value=price_info["상품가"], key=f"{selected_type}_product_price_{i}"
                                )
                                price_info["배송비"] = col_price.number_input(
                                    "배송비", min_value=0, value=price_info["배송비"], key=f"{selected_type}_shipping_price_{i}"
                                )
                                price_info["체험단"] = col_price.number_input(
                                    "체험단비용", min_value=0, value=price_info["체험단"], key=f"{selected_type}_trial_price_{i}"
                                )
                                price_info["수량"] = col_price.number_input(
                                    "수량", min_value=1, value=price_info.get("수량", 1), key=f"{selected_type}_quantity_{i}"
                                )
                            elif selected_type == '⚡패키지충전':
                                price_info["⚡패키지충전"] = col_price.number_input(
                                    "⚡패키지충전", min_value=0, value=price_info.get("⚡패키지충전", 10000000), 
                                    key=f"{selected_type}_amount_{i}", format="%d"
                                )
                            elif selected_type == '⚡패키지충전(체험단)':
                                # 패키지 이름 셀렉트박스로 설정 (미리 정의된 옵션 포함)
                                package_options = ["패키지1000", "패키지500", "직접입력"]
                                selected_package = col_price.selectbox(
                                    "패키지", 
                                    package_options, 
                                    key=f"{selected_type}_package_name_{i}",
                                    index=package_options.index(price_info["개별품목"]) if price_info["개별품목"] in package_options else 0
                                )
                                
                                # 직접입력인 경우 텍스트 입력 필드 표시
                                if selected_package == "직접입력":
                                    custom_package = col_price.text_input(
                                        "패키지명 직접 입력", 
                                        value="" if price_info["개별품목"] in package_options else price_info["개별품목"],
                                        key=f"{selected_type}_custom_package_{i}"
                                    )
                                    # 직접 입력된 값을 저장
                                    price_info["개별품목"] = custom_package
                                else:
                                    # 선택된 옵션을 저장
                                    price_info["개별품목"] = selected_package
                                
                                price_info["개별건수"] = col_price.number_input(
                                    "수량", min_value=1, value=price_info["개별건수"], key=f"{selected_type}_count_{i}"
                                )
                                price_info["개별단가"] = col_price.number_input(
                                    "단가", min_value=0, value=price_info["개별단가"], key=f"{selected_type}_price_{i}", format="%d"
                                )
                            else:  # 핫딜&침투인 경우
                                price_info["커뮤니티"] = col_price.text_input(
                                    "커뮤니티", value=price_info.get("커뮤니티", ""), key=f"{selected_type}_community_{i}"
                                )
                                price_info["체험단"] = col_price.number_input(
                                    "단가", min_value=0, value=price_info.get("체험단", 100000), key=f"{selected_type}_trial_price_{i}"
                                )
                                price_info["수량"] = col_price.number_input(
                                    "수량", min_value=1, value=price_info.get("수량", 1), key=f"{selected_type}_quantity_{i}"
                                )
                            
                            # 패키지충전이 아닌 경우에만 구분선 표시
                            if selected_type != '⚡패키지충전':
                                st.markdown("---")
            
            # 2컬럼: 요청일, 착수일, 중간보고, 내부마감, 보고예정일
            with col2:
                st.markdown("### 일정 정보")
                date_fields = ['요청일', '착수일', '중간보고', '내부마감', '보고예정일']
                for field in date_fields:
                    if field in df.columns:
                        new_data[field] = st.date_input(field, key=f'new_{field}')
            
            # 3컬럼: 팀, 담당자, 비고
            with col3:
                st.markdown("### 담당 정보")
                if '팀' in df.columns:
                    new_data['팀'] = st.selectbox('팀', ['1팀', '2팀', '3팀', '별도'], key='new_team')
                
                if '담당자' in df.columns:
                    # 담당자 옵션 리스트
                    manager_options = [
                        "1팀 조민우 선임님", 
                        "2팀 임용혁 책임님", 
                        "2팀 김성희 책임님", 
                        "3팀 김동락 책임님", 
                        "3팀 배세웅 책임님", 
                        "3팀 유호경 선임님", 
                        "직접입력"
                    ]
                    
                    # 선택된 옵션 저장 변수
                    selected_manager = st.selectbox('담당자', manager_options, key='new_담당자_select')
                    
                    # 직접입력인 경우 텍스트 입력 필드 표시
                    if selected_manager == "직접입력":
                        custom_manager = st.text_input(
                            "담당자 직접 입력", 
                            value="",
                            key='custom_manager'
                        )
                        # 직접 입력된 값을 담당자 정보에 저장
                        new_data['담당자'] = custom_manager
                    else:
                        # 선택된 옵션을 담당자 정보에 저장
                        new_data['담당자'] = selected_manager
                
                if '비고' in df.columns:
                    new_data['비고'] = st.text_area('비고', key='new_비고', height=100)
            
            # 4컬럼: 상태, 보고완료일, 피드백
            with col4:
                st.markdown("### 상태 정보")
                if '상태' in df.columns:
                    status_options = sorted(list(set(df['상태'].dropna().unique().tolist() + ['🟡시작전', '🟠진행중', '완료'])))
                    new_data['상태'] = st.selectbox('상태', status_options, key='new_status')
                if '보고완료일' in df.columns:
                    new_data['보고완료일'] = st.date_input('보고완료일', key='new_보고완료일')
                if '피드백' in df.columns:
                    new_data['피드백'] = st.text_area('피드백', key='new_피드백', height=100)
            
            # 추가 필드 처리 (숨김 처리)
            processed_fields = ['입력자', '프로젝트명', '진행상품', '건수', '유형', 
                              '요청일', '착수일', '중간보고', '내부마감', '보고예정일',
                              '팀', '담당자', '비고', '상태', '보고완료일', '피드백']
            additional_fields = [col for col in df.columns if col not in processed_fields]
            
            # 추가 필드는 기본값으로 설정 (UI에 표시하지 않음)
            for field in additional_fields:
                if pd.api.types.is_numeric_dtype(df[field]):
                    new_data[field] = 0
                else:
                    new_data[field] = ""
            
            # 추가 버튼
            if st.button('데이터 추가', key='add_data_main'):
                add_new_data(new_data)
    
    # 1팀 탭
    with tab_team1:
        st.subheader('1팀 체험단 현황판')
        # 1팀 및 체험단/패키지충전 데이터 필터링
        if '팀' in df.columns and '유형' in df.columns:
            team1_exp_df = df[
                (df['팀'] == '1팀') & 
                (
                    (df['유형'] == '체험단') | 
                    (df['유형'] == '⚡패키지충전(체험단)')
                )
            ]
            
            if not team1_exp_df.empty:
                exp_view_data = []
                cumulative_remaining = 0  # 잔여 누적값 초기화
                
                for idx, row in team1_exp_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    if not 품목상세 or not isinstance(품목상세, list):
                        품목상세 = [{"개별품목": "", "개별건수": 0, "개별단가": 0}]
                    
                    for item in 품목상세:
                        개별건수 = item.get('개별건수', 0)
                        개별단가 = item.get('개별단가', 0)
                        공급가액 = 개별건수 * 개별단가
                        
                        # 소진 계산: 유형에 따라 +1 또는 -1 곱하기
                        소진 = 공급가액 * (1 if row['유형'] == '⚡패키지충전(체험단)' else -1)
                        
                        # 잔여 계산: 이전 잔여값 + 현재 소진값
                        cumulative_remaining += 소진
                        
                        exp_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': item.get('개별품목', ''),
                            '수량': 개별건수,
                            '단가': 개별단가,
                            '공급가액': 공급가액,
                            '소진': 소진,  # 계산된 소진값
                            '잔여': cumulative_remaining,  # 누적된 잔여값
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')                            
                        }
                        exp_view_data.append(exp_row)
                
                if exp_view_data:
                    exp_view_df = pd.DataFrame(exp_view_data)
                    
                    if '날짜' in exp_view_df.columns and not exp_view_df['날짜'].isna().all():
                        exp_view_df['날짜'] = pd.to_datetime(exp_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    exp_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                        
                    }
                    
                    edited_exp_df = st.data_editor(
                        exp_view_df,
                        use_container_width=True,
                        key='data_editor_team1_exp',
                        column_config=exp_column_config,
                        height=600  # 높이 감소
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('1팀 체험단/패키지충전 데이터가 없습니다.')
            else:
                st.info('1팀 체험단/패키지충전 데이터가 없습니다.')
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
        
        # 1팀 가구매/핫딜&침투/패키지충전 현황판 추가
        st.subheader('1팀 가구매/핫딜&침투/패키지충전 현황판')
        if '팀' in df.columns and '유형' in df.columns:
            team1_purchase_df = df[
                (df['팀'] == '1팀') & 
                (df['유형'].isin(['가구매', '⚡패키지충전', '핫딜&침투']))
            ]
            
            if not team1_purchase_df.empty:
                purchase_view_data = []
                purchase_cumulative_remaining = 0  # 가구매용 잔여 누적값 초기화
                
                for idx, row in team1_purchase_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    # 문자열인 경우 JSON으로 파싱
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    # 유형에 따라 다르게 처리
                    if row['유형'] == '⚡패키지충전':
                        # 패키지충전인 경우 한 줄로만 표시
                        충전금액 = 0
                        if isinstance(품목상세, list) and len(품목상세) > 0:
                            for item in 품목상세:
                                if isinstance(item, dict) and '패키지충전' in item:
                                    충전금액 = item.get('패키지충전', 0)
                                    break
                        
                        # 소진 계산 (패키지충전은 +1)
                        소진 = 충전금액
                        purchase_cumulative_remaining += 소진
                        
                        # 한 줄만 추가
                        purchase_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': '패키지충전',
                            '수량': 1,
                            '단가': 충전금액,
                            '공급가액': 충전금액,
                            '소진': 소진,
                            '잔여': purchase_cumulative_remaining,
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')
                        }
                        purchase_view_data.append(purchase_row)
                        
                    else:  # 가구매, 핫딜&침투인 경우
                        # 품목상세가 비어있거나 리스트가 아닌 경우 기본값 설정
                        if not 품목상세 or not isinstance(품목상세, list):
                            if row['유형'] == '가구매':
                                품목상세 = [{"상품가": 0, "배송비": 0, "체험단": 0, "수량": 1}]
                            else:  # 핫딜&침투인 경우
                                품목상세 = [{"커뮤니티": "", "체험단": 100000, "수량": 1}]
                        
                        if row['유형'] == '가구매':
                            for item in 품목상세:
                                수량 = item.get('수량', 1)
                                
                                # 상품가 행 추가
                                상품가 = item.get('상품가', 0)
                                공급가액_상품가 = 상품가 * 수량
                                소진_상품가 = 공급가액_상품가 * -1  # 가구매는 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진_상품가
                                
                                purchase_row_상품가 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '상품가',
                                    '수량': 수량,
                                    '단가': 상품가,
                                    '공급가액': 공급가액_상품가,
                                    '소진': 소진_상품가,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_상품가)
                                
                                # 배송비 행 추가
                                배송비 = item.get('배송비', 0)
                                공급가액_배송비 = 배송비 * 수량
                                소진_배송비 = 공급가액_배송비 * -1
                                purchase_cumulative_remaining += 소진_배송비
                                
                                purchase_row_배송비 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '배송비',
                                    '수량': 수량,
                                    '단가': 배송비,
                                    '공급가액': 공급가액_배송비,
                                    '소진': 소진_배송비,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_배송비)
                                
                                # 체험단비용 행 추가
                                체험단비용 = item.get('체험단', 0)
                                공급가액_체험단 = 체험단비용 * 수량
                                소진_체험단 = 공급가액_체험단 * -1
                                purchase_cumulative_remaining += 소진_체험단
                                
                                purchase_row_체험단 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '체험단비용',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액_체험단,
                                    '소진': 소진_체험단,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_체험단)
                        else:  # 핫딜&침투인 경우
                            # 각 커뮤니티 항목을 개별적으로 처리하여 별도의 행으로 추가
                            for item in 품목상세:
                                커뮤니티 = item.get('커뮤니티', '')
                                체험단비용 = item.get('체험단', 100000)
                                수량 = item.get('수량', 1)
                                공급가액 = 체험단비용 * 수량
                                소진 = 공급가액 * -1  # 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진
                                
                                purchase_row = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': 커뮤니티 or '커뮤니티',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액,
                                    '소진': 소진,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row)
                
                if purchase_view_data:
                    purchase_view_df = pd.DataFrame(purchase_view_data)
                    
                    if '날짜' in purchase_view_df.columns and not purchase_view_df['날짜'].isna().all():
                        purchase_view_df['날짜'] = pd.to_datetime(purchase_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    purchase_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                    }
                    
                    edited_purchase_df = st.data_editor(
                        purchase_view_df,
                        use_container_width=True,
                        key='data_editor_team1_purchase',
                        column_config=purchase_column_config,
                        height=600
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('1팀 가구매/핫딜&침투/패키지충전 데이터가 없습니다.')
            else:
                st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
    
    # 2팀 탭
    with tab_team2:
        st.subheader('2팀 체험단 현황판')
        # 2팀 및 체험단/패키지충전 데이터 필터링
        if '팀' in df.columns and '유형' in df.columns:
            team2_exp_df = df[
                (df['팀'] == '2팀') & 
                (
                    (df['유형'] == '체험단') | 
                    (df['유형'] == '⚡패키지충전(체험단)')
                )
            ]
            
            if not team2_exp_df.empty:
                exp_view_data = []
                cumulative_remaining = 0  # 잔여 누적값 초기화
                
                for idx, row in team2_exp_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    if not 품목상세 or not isinstance(품목상세, list):
                        품목상세 = [{"개별품목": "", "개별건수": 0, "개별단가": 0}]
                    
                    for item in 품목상세:
                        개별건수 = item.get('개별건수', 0)
                        개별단가 = item.get('개별단가', 0)
                        공급가액 = 개별건수 * 개별단가
                        
                        # 소진 계산: 유형에 따라 +1 또는 -1 곱하기
                        소진 = 공급가액 * (1 if row['유형'] == '⚡패키지충전(체험단)' else -1)
                        
                        # 잔여 계산: 이전 잔여값 + 현재 소진값
                        cumulative_remaining += 소진
                        
                        exp_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': item.get('개별품목', ''),
                            '수량': 개별건수,
                            '단가': 개별단가,
                            '공급가액': 공급가액,
                            '소진': 소진,  # 계산된 소진값
                            '잔여': cumulative_remaining,  # 누적된 잔여값
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')                            
                        }
                        exp_view_data.append(exp_row)
                
                if exp_view_data:
                    exp_view_df = pd.DataFrame(exp_view_data)
                    
                    if '날짜' in exp_view_df.columns and not exp_view_df['날짜'].isna().all():
                        exp_view_df['날짜'] = pd.to_datetime(exp_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    exp_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                        
                    }
                    
                    edited_exp_df = st.data_editor(
                        exp_view_df,
                        use_container_width=True,
                        key='data_editor_team2_exp',
                        column_config=exp_column_config,
                        height=600  # 높이 감소
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('2팀 체험단/패키지충전 데이터가 없습니다.')
            else:
                st.info('2팀 체험단/패키지충전 데이터가 없습니다.')
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
        
        # 2팀 가구매/핫딜&침투/패키지충전 현황판 추가
        st.subheader('2팀 가구매/핫딜&침투/패키지충전 현황판')
        if '팀' in df.columns and '유형' in df.columns:
            team2_purchase_df = df[
                (df['팀'] == '2팀') & 
                (df['유형'].isin(['가구매', '⚡패키지충전', '핫딜&침투']))
            ]
            
            if not team2_purchase_df.empty:
                purchase_view_data = []
                purchase_cumulative_remaining = 0  # 가구매용 잔여 누적값 초기화
                
                for idx, row in team2_purchase_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    # 문자열인 경우 JSON으로 파싱
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    # 유형에 따라 다르게 처리
                    if row['유형'] == '⚡패키지충전':
                        # 패키지충전인 경우 한 줄로만 표시
                        충전금액 = 0
                        if isinstance(품목상세, list) and len(품목상세) > 0:
                            for item in 품목상세:
                                if isinstance(item, dict) and '패키지충전' in item:
                                    충전금액 = item.get('패키지충전', 0)
                                    break
                        
                        # 소진 계산 (패키지충전은 +1)
                        소진 = 충전금액
                        purchase_cumulative_remaining += 소진
                        
                        # 한 줄만 추가
                        purchase_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': '⚡패키지충전',
                            '수량': 1,
                            '단가': 충전금액,
                            '공급가액': 충전금액,
                            '소진': 소진,
                            '잔여': purchase_cumulative_remaining,
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')
                        }
                        purchase_view_data.append(purchase_row)
                        
                    else:  # 가구매, 핫딜&침투인 경우
                        # 품목상세가 비어있거나 리스트가 아닌 경우 기본값 설정
                        if not 품목상세 or not isinstance(품목상세, list):
                            if row['유형'] == '가구매':
                                품목상세 = [{"상품가": 0, "배송비": 0, "체험단": 0, "수량": 1}]
                            else:  # 핫딜&침투인 경우
                                품목상세 = [{"커뮤니티": "", "체험단": 100000, "수량": 1}]
                        
                        if row['유형'] == '가구매':
                            for item in 품목상세:
                                수량 = item.get('수량', 1)
                                
                                # 상품가 행 추가
                                상품가 = item.get('상품가', 0)
                                공급가액_상품가 = 상품가 * 수량
                                소진_상품가 = 공급가액_상품가 * -1  # 가구매는 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진_상품가
                                
                                purchase_row_상품가 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '상품가',
                                    '수량': 수량,
                                    '단가': 상품가,
                                    '공급가액': 공급가액_상품가,
                                    '소진': 소진_상품가,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_상품가)
                                
                                # 배송비 행 추가
                                배송비 = item.get('배송비', 0)
                                공급가액_배송비 = 배송비 * 수량
                                소진_배송비 = 공급가액_배송비 * -1
                                purchase_cumulative_remaining += 소진_배송비
                                
                                purchase_row_배송비 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '배송비',
                                    '수량': 수량,
                                    '단가': 배송비,
                                    '공급가액': 공급가액_배송비,
                                    '소진': 소진_배송비,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_배송비)
                                
                                # 체험단비용 행 추가
                                체험단비용 = item.get('체험단', 0)
                                공급가액_체험단 = 체험단비용 * 수량
                                소진_체험단 = 공급가액_체험단 * -1
                                purchase_cumulative_remaining += 소진_체험단
                                
                                purchase_row_체험단 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '체험단비용',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액_체험단,
                                    '소진': 소진_체험단,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_체험단)
                        else:  # 핫딜&침투인 경우
                            # 각 커뮤니티 항목을 개별적으로 처리하여 별도의 행으로 추가
                            for item in 품목상세:
                                커뮤니티 = item.get('커뮤니티', '')
                                체험단비용 = item.get('체험단', 100000)
                                수량 = item.get('수량', 1)
                                공급가액 = 체험단비용 * 수량
                                소진 = 공급가액 * -1  # 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진
                                
                                purchase_row = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': 커뮤니티 or '커뮤니티',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액,
                                    '소진': 소진,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row)
                
                if purchase_view_data:
                    purchase_view_df = pd.DataFrame(purchase_view_data)
                    
                    if '날짜' in purchase_view_df.columns and not purchase_view_df['날짜'].isna().all():
                        purchase_view_df['날짜'] = pd.to_datetime(purchase_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    purchase_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                    }
                    
                    edited_purchase_df = st.data_editor(
                        purchase_view_df,
                        use_container_width=True,
                        key='data_editor_team2_purchase',
                        column_config=purchase_column_config,
                        height=600
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('2팀 가구매/핫딜&침투/패키지충전 데이터가 없습니다.')
            else:
                st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
    
    # 3팀 탭
    with tab_team3:
        st.subheader('3팀 체험단 현황판')
        # 3팀 및 체험단/패키지충전 데이터 필터링
        if '팀' in df.columns and '유형' in df.columns:
            team3_exp_df = df[
                (df['팀'] == '3팀') & 
                (
                    (df['유형'] == '체험단') | 
                    (df['유형'] == '⚡패키지충전(체험단)')
                )
            ]
            
            if not team3_exp_df.empty:
                exp_view_data = []
                cumulative_remaining = 0  # 잔여 누적값 초기화
                
                for idx, row in team3_exp_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    if not 품목상세 or not isinstance(품목상세, list):
                        품목상세 = [{"개별품목": "", "개별건수": 0, "개별단가": 0}]
                    
                    for item in 품목상세:
                        개별건수 = item.get('개별건수', 0)
                        개별단가 = item.get('개별단가', 0)
                        공급가액 = 개별건수 * 개별단가
                        
                        # 소진 계산: 유형에 따라 +1 또는 -1 곱하기
                        소진 = 공급가액 * (1 if row['유형'] == '⚡패키지충전(체험단)' else -1)
                        
                        # 잔여 계산: 이전 잔여값 + 현재 소진값
                        cumulative_remaining += 소진
                        
                        exp_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': item.get('개별품목', ''),
                            '수량': 개별건수,
                            '단가': 개별단가,
                            '공급가액': 공급가액,
                            '소진': 소진,  # 계산된 소진값
                            '잔여': cumulative_remaining,  # 누적된 잔여값
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')                            
                        }
                        exp_view_data.append(exp_row)
                
                if exp_view_data:
                    exp_view_df = pd.DataFrame(exp_view_data)
                    
                    if '날짜' in exp_view_df.columns and not exp_view_df['날짜'].isna().all():
                        exp_view_df['날짜'] = pd.to_datetime(exp_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    exp_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                        
                    }
                    
                    edited_exp_df = st.data_editor(
                        exp_view_df,
                        use_container_width=True,
                        key='data_editor_team3_exp',
                        column_config=exp_column_config,
                        height=600  # 높이 감소
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('3팀 체험단/패키지충전 데이터가 없습니다.')
            else:
                st.info('3팀 체험단/패키지충전 데이터가 없습니다.')
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
        
        # 3팀 가구매/핫딜&침투/패키지충전 현황판 추가
        st.subheader('3팀 가구매/핫딜&침투/패키지충전 현황판')
        if '팀' in df.columns and '유형' in df.columns:
            team3_purchase_df = df[
                (df['팀'] == '3팀') & 
                (df['유형'].isin(['가구매', '⚡패키지충전', '핫딜&침투']))
            ]
            
            if not team3_purchase_df.empty:
                purchase_view_data = []
                purchase_cumulative_remaining = 0  # 가구매용 잔여 누적값 초기화
                
                for idx, row in team3_purchase_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    # 문자열인 경우 JSON으로 파싱
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    # 유형에 따라 다르게 처리
                    if row['유형'] == '⚡패키지충전':
                        # 패키지충전인 경우 한 줄로만 표시
                        충전금액 = 0
                        if isinstance(품목상세, list) and len(품목상세) > 0:
                            for item in 품목상세:
                                if isinstance(item, dict) and '패키지충전' in item:
                                    충전금액 = item.get('패키지충전', 0)
                                    break
                        
                        # 소진 계산 (패키지충전은 +1)
                        소진 = 충전금액
                        purchase_cumulative_remaining += 소진
                        
                        # 한 줄만 추가
                        purchase_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': '⚡패키지충전',
                            '수량': 1,
                            '단가': 충전금액,
                            '공급가액': 충전금액,
                            '소진': 소진,
                            '잔여': purchase_cumulative_remaining,
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')
                        }
                        purchase_view_data.append(purchase_row)
                        
                    else:  # 가구매, 핫딜&침투인 경우
                        # 품목상세가 비어있거나 리스트가 아닌 경우 기본값 설정
                        if not 품목상세 or not isinstance(품목상세, list):
                            if row['유형'] == '가구매':
                                품목상세 = [{"상품가": 0, "배송비": 0, "체험단": 0, "수량": 1}]
                            else:  # 핫딜&침투인 경우
                                품목상세 = [{"커뮤니티": "", "체험단": 100000, "수량": 1}]
                        
                        if row['유형'] == '가구매':
                            for item in 품목상세:
                                수량 = item.get('수량', 1)
                                
                                # 상품가 행 추가
                                상품가 = item.get('상품가', 0)
                                공급가액_상품가 = 상품가 * 수량
                                소진_상품가 = 공급가액_상품가 * -1  # 가구매는 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진_상품가
                                
                                purchase_row_상품가 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '상품가',
                                    '수량': 수량,
                                    '단가': 상품가,
                                    '공급가액': 공급가액_상품가,
                                    '소진': 소진_상품가,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_상품가)
                                
                                # 배송비 행 추가
                                배송비 = item.get('배송비', 0)
                                공급가액_배송비 = 배송비 * 수량
                                소진_배송비 = 공급가액_배송비 * -1
                                purchase_cumulative_remaining += 소진_배송비
                                
                                purchase_row_배송비 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '배송비',
                                    '수량': 수량,
                                    '단가': 배송비,
                                    '공급가액': 공급가액_배송비,
                                    '소진': 소진_배송비,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_배송비)
                                
                                # 체험단비용 행 추가
                                체험단비용 = item.get('체험단', 0)
                                공급가액_체험단 = 체험단비용 * 수량
                                소진_체험단 = 공급가액_체험단 * -1
                                purchase_cumulative_remaining += 소진_체험단
                                
                                purchase_row_체험단 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '체험단비용',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액_체험단,
                                    '소진': 소진_체험단,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_체험단)
                        else:  # 핫딜&침투인 경우
                            # 각 커뮤니티 항목을 개별적으로 처리하여 별도의 행으로 추가
                            for item in 품목상세:
                                커뮤니티 = item.get('커뮤니티', '')
                                체험단비용 = item.get('체험단', 100000)
                                수량 = item.get('수량', 1)
                                공급가액 = 체험단비용 * 수량
                                소진 = 공급가액 * -1  # 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진
                                
                                purchase_row = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': 커뮤니티 or '커뮤니티',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액,
                                    '소진': 소진,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row)
                
                if purchase_view_data:
                    purchase_view_df = pd.DataFrame(purchase_view_data)
                    
                    if '날짜' in purchase_view_df.columns and not purchase_view_df['날짜'].isna().all():
                        purchase_view_df['날짜'] = pd.to_datetime(purchase_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    purchase_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                    }
                    
                    edited_purchase_df = st.data_editor(
                        purchase_view_df,
                        use_container_width=True,
                        key='data_editor_team3_purchase',
                        column_config=purchase_column_config,
                        height=600
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('3팀 가구매/핫딜&침투/패키지충전 데이터가 없습니다.')
            else:
                st.info('3팀 가구매/핫딜&침투/패키지충전 데이터가 없습니다.')
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
    
    # '별도' 탭
    with tab_team_separate:
        st.subheader('별도 체험단 현황판')
        # '별도' 및 체험단/패키지충전 데이터 필터링
        if '팀' in df.columns and '유형' in df.columns:
            team_separate_exp_df = df[
                (df['팀'] == '별도') & 
                (
                    (df['유형'] == '체험단') | 
                    (df['유형'] == '⚡패키지충전(체험단)')
                )
            ]
            
            if not team_separate_exp_df.empty:
                exp_view_data = []
                cumulative_remaining = 0  # 잔여 누적값 초기화
                
                for idx, row in team_separate_exp_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    if not 품목상세 or not isinstance(품목상세, list):
                        품목상세 = [{"개별품목": "", "개별건수": 0, "개별단가": 0}]
                    
                    for item in 품목상세:
                        개별건수 = item.get('개별건수', 0)
                        개별단가 = item.get('개별단가', 0)
                        공급가액 = 개별건수 * 개별단가
                        
                        # 소진 계산: 유형에 따라 +1 또는 -1 곱하기
                        소진 = 공급가액 * (1 if row['유형'] == '⚡패키지충전(체험단)' else -1)
                        
                        # 잔여 계산: 이전 잔여값 + 현재 소진값
                        cumulative_remaining += 소진
                        
                        exp_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': item.get('개별품목', ''),
                            '수량': 개별건수,
                            '단가': 개별단가,
                            '공급가액': 공급가액,
                            '소진': 소진,  # 계산된 소진값
                            '잔여': cumulative_remaining,  # 누적된 잔여값
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')                            
                        }
                        exp_view_data.append(exp_row)
                
                if exp_view_data:
                    exp_view_df = pd.DataFrame(exp_view_data)
                    
                    if '날짜' in exp_view_df.columns and not exp_view_df['날짜'].isna().all():
                        exp_view_df['날짜'] = pd.to_datetime(exp_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    exp_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                        
                    }
                    
                    edited_exp_df = st.data_editor(
                        exp_view_df,
                        use_container_width=True,
                        key='data_editor_team_separate_exp',
                        column_config=exp_column_config,
                        height=600  # 높이 감소
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('별도 체험단/패키지충전 데이터가 없습니다.')
            else:
                st.info('별도 체험단/패키지충전 데이터가 없습니다.')
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
        
        # 별도 가구매/핫딜&침투/패키지충전 현황판 추가
        st.subheader('별도 가구매/핫딜&침투/패키지충전 현황판')
        if '팀' in df.columns and '유형' in df.columns:
            team_separate_purchase_df = df[
                (df['팀'] == '별도') & 
                (df['유형'].isin(['가구매', '⚡패키지충전', '핫딜&침투']))
            ]
            
            if not team_separate_purchase_df.empty:
                purchase_view_data = []
                purchase_cumulative_remaining = 0  # 가구매용 잔여 누적값 초기화
                
                for idx, row in team_separate_purchase_df.iterrows():
                    품목상세 = row.get('품목상세', [])
                    
                    # 문자열인 경우 JSON으로 파싱
                    if isinstance(품목상세, str):
                        try:
                            품목상세 = json.loads(품목상세)
                        except:
                            품목상세 = []
                    
                    # 유형에 따라 다르게 처리
                    if row['유형'] == '⚡패키지충전':
                        # 패키지충전인 경우 한 줄로만 표시
                        충전금액 = 0
                        if isinstance(품목상세, list) and len(품목상세) > 0:
                            for item in 품목상세:
                                if isinstance(item, dict) and '패키지충전' in item:
                                    충전금액 = item.get('패키지충전', 0)
                                    break
                        
                        # 소진 계산 (패키지충전은 +1)
                        소진 = 충전금액
                        purchase_cumulative_remaining += 소진
                        
                        # 한 줄만 추가
                        purchase_row = {
                            '날짜': row.get('요청일', None),
                            '유형': row.get('유형', ''),
                            '진행상품': row.get('진행상품', ''),
                            '담당자': row.get('담당자', ''),
                            '품목': '⚡패키지충전',
                            '수량': 1,
                            '단가': 충전금액,
                            '공급가액': 충전금액,
                            '소진': 소진,
                            '잔여': purchase_cumulative_remaining,
                            '상태': row.get('상태', ''),
                            '비고': row.get('비고', '')
                        }
                        purchase_view_data.append(purchase_row)
                        
                    else:  # 가구매, 핫딜&침투인 경우
                        # 품목상세가 비어있거나 리스트가 아닌 경우 기본값 설정
                        if not 품목상세 or not isinstance(품목상세, list):
                            if row['유형'] == '가구매':
                                품목상세 = [{"상품가": 0, "배송비": 0, "체험단": 0, "수량": 1}]
                            else:  # 핫딜&침투인 경우
                                품목상세 = [{"커뮤니티": "", "체험단": 100000, "수량": 1}]
                        
                        if row['유형'] == '가구매':
                            for item in 품목상세:
                                수량 = item.get('수량', 1)
                                
                                # 상품가 행 추가
                                상품가 = item.get('상품가', 0)
                                공급가액_상품가 = 상품가 * 수량
                                소진_상품가 = 공급가액_상품가 * -1  # 가구매는 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진_상품가
                                
                                purchase_row_상품가 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '상품가',
                                    '수량': 수량,
                                    '단가': 상품가,
                                    '공급가액': 공급가액_상품가,
                                    '소진': 소진_상품가,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_상품가)
                                
                                # 배송비 행 추가
                                배송비 = item.get('배송비', 0)
                                공급가액_배송비 = 배송비 * 수량
                                소진_배송비 = 공급가액_배송비 * -1
                                purchase_cumulative_remaining += 소진_배송비
                                
                                purchase_row_배송비 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '배송비',
                                    '수량': 수량,
                                    '단가': 배송비,
                                    '공급가액': 공급가액_배송비,
                                    '소진': 소진_배송비,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_배송비)
                                
                                # 체험단비용 행 추가
                                체험단비용 = item.get('체험단', 0)
                                공급가액_체험단 = 체험단비용 * 수량
                                소진_체험단 = 공급가액_체험단 * -1
                                purchase_cumulative_remaining += 소진_체험단
                                
                                purchase_row_체험단 = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': '체험단비용',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액_체험단,
                                    '소진': 소진_체험단,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row_체험단)
                        else:  # 핫딜&침투인 경우
                            # 각 커뮤니티 항목을 개별적으로 처리하여 별도의 행으로 추가
                            for item in 품목상세:
                                커뮤니티 = item.get('커뮤니티', '')
                                체험단비용 = item.get('체험단', 100000)
                                수량 = item.get('수량', 1)
                                공급가액 = 체험단비용 * 수량
                                소진 = 공급가액 * -1  # 소진에 -1 곱하기
                                purchase_cumulative_remaining += 소진
                                
                                purchase_row = {
                                    '날짜': row.get('요청일', None),
                                    '유형': row.get('유형', ''),
                                    '진행상품': row.get('진행상품', ''),
                                    '담당자': row.get('담당자', ''),
                                    '품목': 커뮤니티 or '커뮤니티',
                                    '수량': 수량,
                                    '단가': 체험단비용,
                                    '공급가액': 공급가액,
                                    '소진': 소진,
                                    '잔여': purchase_cumulative_remaining,
                                    '상태': row.get('상태', ''),
                                    '비고': row.get('비고', '')
                                }
                                purchase_view_data.append(purchase_row)
                
                if purchase_view_data:
                    purchase_view_df = pd.DataFrame(purchase_view_data)
                    
                    if '날짜' in purchase_view_df.columns and not purchase_view_df['날짜'].isna().all():
                        purchase_view_df['날짜'] = pd.to_datetime(purchase_view_df['날짜']).dt.strftime('%Y-%m-%d')
                    
                    purchase_column_config = {
                        '날짜': st.column_config.TextColumn('날짜', width='small'),
                        '유형': st.column_config.TextColumn('유형', width='small'),
                        '진행상품': st.column_config.TextColumn('진행상품', width='medium'),
                        '담당자': st.column_config.TextColumn('담당자', width='medium'),
                        '품목': st.column_config.TextColumn('품목', width='medium'),
                        '수량': st.column_config.NumberColumn('수량', width='small'),
                        '단가': st.column_config.NumberColumn('단가', format="₩%d", width='medium'),
                        '공급가액': st.column_config.NumberColumn('공급가액', format="₩%d", width='medium'),
                        '소진': st.column_config.NumberColumn('소진', format="₩%d", width='medium'),
                        '잔여': st.column_config.NumberColumn('잔여', format="₩%d", width='medium'),
                        '상태': st.column_config.SelectboxColumn(
                            '상태',
                            width='medium',
                            options=['🟡시작전', '🟠진행중', '완료']
                        ),
                        '비고': st.column_config.TextColumn('비고', width='large')
                    }
                    
                    edited_purchase_df = st.data_editor(
                        purchase_view_df,
                        use_container_width=True,
                        key='data_editor_team_separate_purchase',
                        column_config=purchase_column_config,
                        height=600
                    )
                    
                    st.info("이 뷰에서의 변경 사항은 원본 데이터에 반영되지 않습니다. 수정 기능은 나중에 추가될 예정입니다.")
                else:
                    st.info('별도 가구매/핫딜&침투/패키지충전 데이터가 없습니다.')
            else:
                st.info('별도 가구매/핫딜&침투/패키지충전 데이터가 없습니다.')
        else:
            st.info("데이터에 '팀' 또는 '유형' 컬럼이 없습니다.")
else:
    st.warning('데이터를 로드할 수 없습니다. 파일이 존재하고 올바른 JSON 형식인지 확인하세요.')
