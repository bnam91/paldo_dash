'''
# STEP2.블로거 최근글 크롤링 ver.1.2
- step 1단계에서 추출한 블로거들의 최근 글을 크롤링합니다.

### 방법
- step 1단계에서 추출한 엑셀파일을 그대로 넣고 실행하면 됨
- (a2)는 연결하지 말것. 점령할 키워드는 한번에 하나씩진행할 것 (셀이 안맞아서 C레벨에서 이상하게 나옴)
- 처음 로딩시간이 제법 걸리는 점 참고. 3분 이내로 되긴 함

'''


import tkinter as tk
from tkinter import filedialog
import re
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth import get_credentials

def select_excel_file():
    root = tk.Tk()
    root.withdraw()  # 루트 창 숨기기
    root.update()  # 상태 갱신

def select_excel_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="엑셀 파일 선택", filetypes=[("Excel files", "*.xlsx")])
    return file_path

def setup_webdriver():
    options = Options()
    options.headless = False
    driver = webdriver.Chrome(options=options)
    return driver


def extract_blog_ids(file_path):
    wb = load_workbook(file_path)
    ws = wb.active
    urls, names = [], []
    for row in range(1, ws.max_row + 1):
        url = ws['E' + str(row)].value
        name = ws['A' + str(row)].value
        if url and url.startswith("https://blog.naver.com/"):
            blog_id = url.split('/')[3]
            urls.append(f"https://blog.naver.com/PostList.naver?blogId={blog_id}&skinType=&skinId=&from=menu")
            names.append(name)
        time.sleep(1)
    return urls, names



def set_30_line_view(driver):
    select_box = driver.find_elements(By.CSS_SELECTOR, 'a.btn_select.pcol2._ListCountToggle._returnFalse')
    if select_box:
        select_box[0].click()
        time.sleep(1)
        thirty_lines_option = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-value='30']"))
        )
        thirty_lines_option.click()
        time.sleep(2)
    else:
        open_list_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'btn_openlist.pcol2._toggleTopList._returnFalse'))
        )
        open_list_button.click()
        time.sleep(1)
        
        select_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn_select.pcol2._ListCountToggle._returnFalse'))
        )
        select_button.click()
        time.sleep(1)
        thirty_lines_option = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-value='30']"))
        )
        thirty_lines_option.click()
        time.sleep(2)


def get_search_keyword():
    keyword = input("검색할 키워드를 입력하세요: ").strip()
    return keyword

def convert_to_date(date_str):
    try:
        # '분 전', '시간 전' 체크
        if '분 전' in date_str or '시간 전' in date_str:
            return datetime.now().strftime('%Y. %m. %d.')
            
        # '2025. 5. 19.' 형식 체크
        if re.match(r'\d{4}\. \d{1,2}\. \d{1,2}\.', date_str):
            return date_str
            
        # 그 외의 경우 오늘 날짜 반환
        return datetime.now().strftime('%Y. %m. %d.')
    except:
        return datetime.now().strftime('%Y. %m. %d.')

def update_sheet_with_link_and_date(service, spreadsheet_id, row_index, link, post_date):
    try:
        # 날짜 형식 변환
        formatted_date = convert_to_date(post_date)
        
        # C열 업데이트
        range_name_c = f"'시트1'!C{row_index}"
        body_c = {
            'values': [[link]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name_c,
            valueInputOption='RAW',
            body=body_c
        ).execute()
        
        # I열 업데이트 (변환된 날짜로)
        range_name_i = f"'시트1'!I{row_index}"
        body_i = {
            'values': [[formatted_date]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name_i,
            valueInputOption='RAW',
            body=body_i
        ).execute()
        
    except Exception as e:
        print(f"시트 업데이트 중 오류 발생: {str(e)}")

def scrape_blog_data(driver, url, keyword, name, service, spreadsheet_id, row_index):
    driver.get(url)
    time.sleep(5)
    set_30_line_view(driver)
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'table.blog2_list'))
        )
        posts = driver.find_elements(By.CSS_SELECTOR, 'table.blog2_list tbody tr')[:30]
        data = []
        found_in_blog = False
        
        for post in posts:
            title_elements = post.find_elements(By.CSS_SELECTOR, 'span.ell2.pcol2')
            date_elements = post.find_elements(By.CSS_SELECTOR, 'div.wrap_td span.date.pcol2')
            link_elements = post.find_elements(By.CSS_SELECTOR, 'td.title a')
            if title_elements and date_elements and link_elements:
                title = title_elements[0].text
                date = date_elements[0].text
                link = link_elements[0].get_attribute('href')
                
                if keyword in title:
                    if not found_in_blog:
                        print(f"\n키워드 '{keyword}' 발견")
                        found_in_blog = True
                        # 작성일을 파라미터로 전달
                        update_sheet_with_link_and_date(service, spreadsheet_id, row_index, link, date)
                    print(f"제목: {title}")
                    print(f"작성일: {date}")
                    print(f"링크: {link}")
                    print("-" * 80)
                
                data.append((title, date, link))
                
        if not found_in_blog:
            print(f"{name}의 블로그에서 '{keyword}' 관련 글이 없습니다.")
            
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        data = []
    return data



def apply_excel_styles(ws):
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="FCD5B4", end_color="FCD5B4", fill_type="solid")
    center_alignment = Alignment(horizontal='center', vertical='center')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    grey_fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
    
    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 16
    ws.column_dimensions['C'].width = 70
    ws.column_dimensions['D'].width = 16

    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = center_alignment
        cell.fill = header_fill
        cell.border = thin_border
    
    return grey_fill

def save_data_to_excel(urls, names, data_list, ws, grey_fill):
    for index, (url, name, data) in enumerate(zip(urls, names, data_list)):
        for title, date, link in data:
            row = [name, "", title, date, link]
            ws.append(row)
            if index % 2 == 1:
                for cell in ws[ws.max_row]:
                    cell.fill = grey_fill

def get_user_input():
    urls = []
    names = []
    print("블로그 URL을 입력하세요 (입력 완료시 'done' 입력):")
    while True:
        url = input("URL: ").strip()
        if url.lower() == 'done':
            break
        if url.startswith("https://blog.naver.com/"):
            blog_id = url.split('/')[3]
            name = input("블로거 이름: ").strip()
            urls.append(f"https://blog.naver.com/PostList.naver?blogId={blog_id}&skinType=&skinId=&from=menu")
            names.append(name)
        else:
            print("올바른 네이버 블로그 URL을 입력해주세요 (https://blog.naver.com/로 시작해야 합니다)")
    return urls, names

def print_blog_data(urls, names, data_list, keyword):
    print(f"\n=== '{keyword}' 키워드 검색 결과 ===\n")
    found_any = False
    
    for url, name, data in zip(urls, names, data_list):
        found_in_blog = False
        for title, date, link in data:
            if keyword in title:
                if not found_in_blog:
                    print(f"\n[{name}의 블로그에서 발견]")
                    found_in_blog = True
                    found_any = True
                print(f"제목: {title}")
                print(f"작성일: {date}")
                print(f"링크: {link}")
                print("-" * 80)
    
    if not found_any:
        print(f"'{keyword}' 키워드가 포함된 글이 없습니다.")

def extract_sheet_id(input_str):
    """구글 시트 URL 또는 ID에서 시트 ID를 추출합니다."""
    # URL 패턴 매칭
    url_pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(url_pattern, input_str)
    
    if match:
        # URL에서 ID 추출
        return match.group(1)
    else:
        # URL이 아닌 경우 입력값이 ID라고 가정
        # ID 형식 검증 (알파벳, 숫자, 하이픈, 언더스코어로만 구성)
        if re.match(r'^[a-zA-Z0-9-_]+$', input_str):
            return input_str
        else:
            raise ValueError("유효하지 않은 구글 시트 URL 또는 ID입니다.")

def get_blog_data_from_sheet(service, spreadsheet_id_or_url):
    """구글 시트에서 블로그 데이터를 가져옵니다."""
    try:
        # 시트 ID 추출
        spreadsheet_id = extract_sheet_id(spreadsheet_id_or_url)
        RANGE_NAME = "'시트1'!B:F"  # B열부터 F열까지 가져오도록 수정
        
        # 시트 데이터 가져오기
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=RANGE_NAME
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print('데이터가 없습니다.')
            return [], [], []
            
        urls = []
        names = []
        row_indices = []  # 실제 행 번호를 저장할 리스트
        
        # 데이터 처리 (첫 번째 행은 헤더이므로 건너뛰기)
        for i, row in enumerate(values[1:], start=2):
            print(f"\n행 {i} 처리 중:")
            print(f"행 데이터: {row}")
            
            if len(row) >= 1:  # URL만 있어도 처리 (B열만 있으면 됨)
                print(f"열 개수 조건 통과 (현재 {len(row)}개 열)")
                has_url = bool(row[0])  # B열에 URL이 있는지
                print(f"B열 URL 존재: {has_url} (값: {row[0]})")
                
                # C열이 없거나 비어있는 경우 처리
                is_cell_empty = len(row) <= 1 or not row[1] or row[1].strip() == ""
                print(f"C열 비어있음: {is_cell_empty} (값: {row[1] if len(row) > 1 else '없음'})")
                
                if has_url and is_cell_empty:
                    print("URL 처리 시작")
                    blog_url = row[0]
                    # 모바일 URL을 PC URL로 변환
                    if blog_url.startswith("https://m.blog.naver.com/"):
                        blog_url = blog_url.replace("https://m.blog.naver.com/", "https://blog.naver.com/")
                        # URL에서 ?tab=1 같은 파라미터 제거
                        blog_url = blog_url.split('?')[0]
                    
                    if blog_url.startswith("https://blog.naver.com/"):
                        blog_id = blog_url.split('/')[3]
                        urls.append(f"https://blog.naver.com/PostList.naver?blogId={blog_id}&skinType=&skinId=&from=menu")
                        names.append(row[4] if len(row) > 4 else "")  # F열(인덱스 4)의 블로거 이름
                        row_indices.append(i)
                    else:
                        print("URL 처리 건너뜀 (네이버 블로그 URL이 아님)")
                else:
                    print("URL 처리 건너뜀 (조건 불충족)")
            else:
                print(f"열 개수 부족 (현재 {len(row)}개 열)")
        
        print(f"\n최종 처리된 URL 수: {len(urls)}")
        return urls, names, row_indices
        
    except Exception as e:
        print(f"구글 시트 데이터 읽기 오류: {str(e)}")
        return [], [], []

def main():
    # 키워드 입력 받기
    keyword = get_search_keyword()
    print(f"\n=== '{keyword}' 키워드 검색 시작 ===\n")
    
    # 구글 시트 서비스 초기화
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    # 시트 ID 입력 받기
    sheet_id_or_url = input("구글 시트 URL 또는 ID를 입력하세요: ").strip()
    if not sheet_id_or_url:
        print("시트 URL 또는 ID가 입력되지 않았습니다.")
        return
    
    try:
        # 구글 시트에서 블로그 데이터 가져오기
        urls, names, row_indices = get_blog_data_from_sheet(service, sheet_id_or_url)
        if not urls:
            print("처리할 블로그 데이터가 없습니다.")
            return

        print(f"총 {len(urls)}개의 블로그를 검색합니다.")
        
        driver = setup_webdriver()
        data_list = []
        
        # 각 블로그별로 실시간 처리
        for url, name, row_index in zip(urls, names, row_indices):
            print(f"\n{name}의 블로그 검색 중...")
            data = scrape_blog_data(driver, url, keyword, name, service, extract_sheet_id(sheet_id_or_url), row_index)
            data_list.append(data)
        
        driver.quit()
    except ValueError as e:
        print(f"오류: {str(e)}")
    except Exception as e:
        print(f"처리 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()

    ## 이게 거의 최종일듯
