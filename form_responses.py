import os
import sys
import csv
import datetime
from googleapiclient.discovery import build
from auth import get_credentials
import re

def extract_form_id_from_url(url):
    """URL에서 폼 ID를 추출합니다."""
    # URL 형식: https://docs.google.com/forms/d/{FORM_ID}/edit
    parts = url.split('/')
    for i, part in enumerate(parts):
        if part == 'd' and i + 1 < len(parts):
            return parts[i + 1]
    return None

def get_form_responses_direct(form_id):
    """Forms API를 사용하여 응답 데이터를 직접 가져옵니다."""
    try:
        # 인증 정보 가져오기
        creds = get_credentials()
        
        # Forms API 서비스 객체 생성
        forms_service = build('forms', 'v1', credentials=creds)
        
        # 폼 정보 가져오기
        form_info = forms_service.forms().get(formId=form_id).execute()
        form_title = form_info.get('info', {}).get('title', '제목 없음')
        print(f"폼 제목: {form_title}")
        
        # 응답 데이터 직접 가져오기
        responses_data = forms_service.forms().responses().list(formId=form_id).execute()
        responses = responses_data.get('responses', [])
        
        return len(responses), responses, form_title
    
    except Exception as e:
        print(f"오류 발생: {e}")
        return None, [], ''

def get_spreadsheet_id_manually():
    """사용자에게 스프레드시트 ID를 직접 입력받습니다."""
    print("\n폼에 연결된 스프레드시트를 찾을 수 없습니다.")
    print("구글 폼의 '응답' 탭에서 '스프레드시트에서 보기' 버튼을 클릭하면 열리는 스프레드시트의 URL을 입력해주세요.")
    print("예: https://docs.google.com/spreadsheets/d/1abc123def456/edit")
    print("URL이 없으면 그냥 Enter 키를 눌러주세요.")
    
    spreadsheet_url = input("스프레드시트 URL: ")
    
    if not spreadsheet_url:
        return None
        
    # URL에서 스프레드시트 ID 추출
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
    if match:
        return match.group(1)
    
    return None

def get_form_responses_from_spreadsheet(spreadsheet_id):
    """스프레드시트에서 응답 수를 가져옵니다."""
    try:
        # 인증 정보 가져오기
        creds = get_credentials()
        
        # 스프레드시트 API 서비스 객체 생성
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # 스프레드시트 정보 가져오기
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        spreadsheet_title = sheet_metadata.get('properties', {}).get('title', '제목 없음')
        
        # 첫 번째 시트의 제목 가져오기
        sheet_title = sheets[0]['properties']['title']
        
        # 데이터 범위 가져오기
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_title
        ).execute()
        
        # 데이터 가져오기
        rows = result.get('values', [])
        
        # 행 수 계산 (헤더 행 제외)
        if len(rows) > 1:  # 헤더 행이 있다고 가정
            return len(rows) - 1, rows, spreadsheet_title
        return 0, rows, spreadsheet_title
    
    except Exception as e:
        print(f"스프레드시트 접근 중 오류 발생: {e}")
        return None, [], ''

def save_to_csv(data, form_title):
    """응답 데이터를 CSV 파일로 저장합니다."""
    if not data or len(data) <= 1:
        print("저장할 데이터가 없습니다.")
        return False
    
    # 현재 날짜와 시간을 파일명에 포함
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 파일명에 사용할 수 없는 문자 제거
    safe_title = re.sub(r'[\\/*?:"<>|]', "", form_title).strip()
    if not safe_title:
        safe_title = "form_responses"
    
    # 저장 디렉토리 지정 (바탕화면 또는 현재 디렉토리)
    try:
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop_path):
            save_dir = desktop_path
            print(f"CSV 파일을 바탕화면에 저장합니다.")
        else:
            save_dir = os.getcwd()
            print(f"CSV 파일을 현재 디렉토리에 저장합니다.")
    except:
        save_dir = os.getcwd()
        print(f"CSV 파일을 현재 디렉토리에 저장합니다.")
    
    # 파일명 및 전체 경로 생성
    filename = f"{safe_title}_{now}.csv"
    filepath = os.path.join(save_dir, filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 데이터의 모든 행 작성
            print(f"데이터 {len(data)}행을 저장 중...")
            for row in data:
                writer.writerow(row)
        
        print(f"응답 데이터가 '{filepath}' 파일로 저장되었습니다.")
        
        # 파일이 실제로 존재하는지 확인
        if os.path.exists(filepath):
            print(f"파일 크기: {os.path.getsize(filepath)} 바이트")
        else:
            print("경고: 파일이 저장되었지만 확인할 수 없습니다.")
            
        return True
    
    except Exception as e:
        print(f"CSV 파일 저장 중 오류 발생: {e}")
        print(f"저장 시도한 경로: {filepath}")
        
        # 디렉토리 쓰기 권한 확인
        try:
            test_file = os.path.join(save_dir, "test_write_permission.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("저장 디렉토리에 쓰기 권한이 있습니다.")
        except:
            print("경고: 저장 디렉토리에 쓰기 권한이 없습니다.")
        
        return False

def main():
    # 사용자로부터 URL 직접 입력받기
    url = input("구글 폼 URL을 입력하세요: ")
    
    form_id = extract_form_id_from_url(url)
    if not form_id:
        print("URL에서 폼 ID를 추출할 수 없습니다.")
        return
    
    # 방법 1: 폼 API를 통해 직접 응답 데이터 조회
    print("Forms API를 통해 응답 데이터를 직접 조회합니다...")
    direct_count, direct_responses, form_title = get_form_responses_direct(form_id)
    
    if direct_count is not None:
        print(f"폼 API에서 직접 가져온 응답 수: {direct_count}개")
    
    # 방법 2: 사용자에게 스프레드시트 ID를 직접 입력받기
    spreadsheet_id = get_spreadsheet_id_manually()
    
    if spreadsheet_id:
        print("입력한 스프레드시트에서 응답 수를 조회합니다...")
        spreadsheet_count, spreadsheet_data, spreadsheet_title = get_form_responses_from_spreadsheet(spreadsheet_id)
        
        if spreadsheet_count is not None:
            print(f"스프레드시트에서 가져온 응답 수: {spreadsheet_count}개")
            
            # CSV로 저장할지 물어보기
            if spreadsheet_data:
                save_option = input("\n응답 데이터를 CSV 파일로 저장하시겠습니까? (y/n): ")
                if save_option.lower() == 'y':
                    save_to_csv(spreadsheet_data, spreadsheet_title)
    
    print("\n참고: 구글 폼에서 정확한 응답 수를 확인하려면 다음 방법을 사용하세요:")
    print("1. 구글 폼에 접속하여 '응답' 탭 선택")
    print("2. 상단에 표시되는 응답 수 확인")
    print("3. 또는 '스프레드시트에서 보기' 버튼을 클릭하여 연결된 스프레드시트에서 응답 수 확인")

if __name__ == "__main__":
    main() 