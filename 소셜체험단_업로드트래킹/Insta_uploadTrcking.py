#https://docs.google.com/spreadsheets/d/1RdnS9IsC1TbTi356J5W-Pb66oaJ7xUhVZr-pTlJTwxQ/edit?gid=0#gid=0



# 전역 변수로 SHEET_NAME과 SPREADSHEET_ID 선언
SHEET_NAME = None
SPREADSHEET_ID = None
PROCESSED_USERNAMES = set()  # 처리된 username을 추적하는 전역 변수

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os
import shutil
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime, timezone, timedelta
import json
import random
from googleapiclient.discovery import build
import sys
from urllib.parse import urlparse, urlunsplit

# auth.py 파일 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth import get_credentials

def get_sheet_list(service, spreadsheet_id):
    """스프레드시트의 모든 시트 목록을 가져오는 함수"""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        return [(i+1, sheet['properties']['title']) for i, sheet in enumerate(sheets)]
    except Exception as e:
        print(f"시트 목록을 가져오는 중 오류 발생: {str(e)}")
        return []

def extract_spreadsheet_id(url):
    """스프레드시트 URL에서 ID를 추출하는 함수"""
    try:
        # URL에서 ID 부분 추출
        if '/d/' in url:
            # /d/ 다음에 오는 ID 추출
            id_part = url.split('/d/')[1]
            # ID는 보통 44자리이며, 그 이후의 부분은 제거
            spreadsheet_id = id_part.split('/')[0]
            return spreadsheet_id
        else:
            # URL이 아닌 경우 입력값을 그대로 반환
            return url.strip()
    except Exception as e:
        print(f"URL에서 ID 추출 중 오류 발생: {str(e)}")
        return url.strip()

def select_sheet():
    """사용자가 시트를 선택하는 함수"""
    global SHEET_NAME, SPREADSHEET_ID  # 전역 변수 사용 선언
    
    # 스프레드시트 ID 입력 받기
    while True:
        spreadsheet_input = input("\n스프레드시트 URL 또는 ID를 입력하세요: ").strip()
        if spreadsheet_input:
            SPREADSHEET_ID = extract_spreadsheet_id(spreadsheet_input)
            break
        print("스프레드시트 URL 또는 ID를 입력해주세요.")
    
    # Google Sheets API 인증 및 서비스 객체 생성
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    # 시트 목록 가져오기
    sheets = get_sheet_list(service, SPREADSHEET_ID)
    
    if not sheets:
        print("시트 목록을 가져올 수 없습니다.")
        return None
    
    # 시트 목록 출력
    print("\n=== 사용 가능한 시트 목록 ===")
    for num, title in sheets:
        print(f"{num}. {title}")
    
    # 사용자 입력 받기
    while True:
        try:
            choice = int(input("\n사용할 시트 번호를 입력하세요: "))
            if 1 <= choice <= len(sheets):
                SHEET_NAME = sheets[choice-1][1]  # 전역 변수 업데이트
                print(f"\n선택된 시트: {SHEET_NAME}")
                return SHEET_NAME
            else:
                print(f"1부터 {len(sheets)} 사이의 숫자를 입력해주세요.")
        except ValueError:
            print("올바른 숫자를 입력해주세요.")

def clean_url(url):
    """URL에서 쿼리 파라미터를 제거하는 함수"""
    print(f"\n[URL 정규화 시작] 원본 URL: {url}")
    parsed = urlparse(url)
    print(f"URL 파싱 결과:")
    print(f"- scheme: {parsed.scheme}")
    print(f"- netloc: {parsed.netloc}")
    print(f"- path: {parsed.path}")
    print(f"- query: {parsed.query}")
    print(f"- fragment: {parsed.fragment}")
    
    clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
    print(f"[URL 정규화 완료] 정규화된 URL: {clean}")
    return clean

def clear_chrome_data(user_data_dir, keep_login=True):
    default_dir = os.path.join(user_data_dir, 'Default')
    if not os.path.exists(default_dir):
        print("Default 디렉토리가 존재하지 않습니다.")
        return

    dirs_to_clear = ['Cache', 'Code Cache', 'GPUCache']
    files_to_clear = ['History', 'Visited Links', 'Web Data']
    
    for dir_name in dirs_to_clear:
        dir_path = os.path.join(default_dir, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"{dir_name} 디렉토리를 삭제했습니다.")

    if not keep_login:
        files_to_clear.extend(['Cookies', 'Login Data'])

    for file_name in files_to_clear:
        file_path = os.path.join(default_dir, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"{file_name} 파일을 삭제했습니다.")

def is_within_period(date_str, weeks):
    try:
        post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        period_ago = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        return post_date >= period_ago
    except Exception as e:
        print(f"날짜 변환 중 오류 발생: {str(e)}")
        return False

def crawl_instagram_posts(driver, post_url, weeks, username, keyword):
    try:
        # 게시물 카운터 초기화 (기간 내 모든 게시물 카운트)
        total_posts_in_period = 0
        keyword_posts = []  # 키워드가 포함된 게시물 저장
        
        # 여러 키워드 처리 (쉼표로 분리)
        raw_keywords = [k.strip() for k in keyword.split(',') if k.strip()]
        # 각 키워드별로 띄어쓰기 제거 버전도 포함
        keyword_variations = []
        for k in raw_keywords:
            keyword_variations.append(k.lower())
            keyword_variations.append(k.lower().replace(' ', ''))
        print(f"\n검색 키워드 변형: {keyword_variations}")
        
        # 첫 번째 피드 게시물이 로드될 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._aagv"))
        )
        
        # 잠시 대기
        time.sleep(3)
        
        # 첫 번째 게시물 찾기
        first_post = driver.find_element(By.CSS_SELECTOR, "div._aagv")
        
        # 부모 요소로 이동하여 링크 찾기
        parent = first_post.find_element(By.XPATH, "./ancestor::a")
        post_link = parent.get_attribute("href")
        
        # JavaScript로 첫 번째 게시물 클릭
        print(f"\n첫 번째 게시물({post_link})을 클릭합니다...")
        driver.execute_script("arguments[0].click();", parent)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        try:
            # 게시물 정보 추출
            post_data = {}
            
            # 작성자 ID 추출 (여러 선택자 시도)
            try:
                print("\n[작성자 정보 추출 시도]")
                # 여러 가능한 선택자 시도
                selectors = [
                    "a[role='link'][tabindex='0']",  # 기존 선택자
                    "header a[role='link']",         # 헤더 내 링크
                    "div._a9zr a[role='link']",      # 게시물 헤더 내 링크
                    "div._a9zr h2._a9zc"            # 게시물 헤더 내 텍스트
                ]
                
                author_found = False
                for selector in selectors:
                    try:
                        print(f"선택자 시도: {selector}")
                        author_element = driver.find_element(By.CSS_SELECTOR, selector)
                        if author_element.text.strip():
                            post_data['author'] = author_element.text.strip()
                            print(f"작성자 정보 추출 성공: {post_data['author']}")
                            author_found = True
                            break
                    except Exception as e:
                        print(f"선택자 {selector} 실패: {str(e)}")
                        continue
                
                if not author_found:
                    print("경고: 작성자 정보를 찾을 수 없습니다. username을 사용합니다.")
                    post_data['author'] = username  # username을 author로 사용
                
            except Exception as e:
                print(f"작성자 정보 추출 중 오류 발생: {str(e)}")
                print("username을 author로 사용합니다.")
                post_data['author'] = username  # username을 author로 사용
            
            # 본문 내용 추출
            try:
                content_element = driver.find_element(By.CSS_SELECTOR, "h1._ap3a._aaco._aacu._aacx._aad7._aade")
                post_data['content'] = content_element.text  # 전체 내용 저장
                
                # 게시 날짜 추출
                time_element = driver.find_element(By.CSS_SELECTOR, "time._a9ze._a9zf")
                post_date = time_element.get_attribute('datetime')
                
                # 키워드 검색 (모든 키워드 변형이 본문에 포함되어야 함)
                content_lower = post_data['content'].lower().replace(' ', '')
                if all(k.replace(' ', '') in content_lower for k in raw_keywords):
                    keyword_posts.append({
                        'url': driver.current_url,
                        'content': post_data['content'],
                        'date': post_date
                    })
                    print(f"\n✅ 모든 키워드가 포함된 게시물을 찾았습니다!")
                    print(f"게시물 내용: {post_data['content'][:100]}...")  # 내용 일부 출력
                
            except Exception as e:
                print(f"\n본문 내용을 찾을 수 없습니다. 빈 내용으로 처리합니다.")
                post_data['content'] = ""  # 빈 내용으로 설정
            
            # 게시 날짜 추출
            time_element = driver.find_element(By.CSS_SELECTOR, "time._a9ze._a9zf")
            post_date = time_element.get_attribute('datetime')
            
            # 처음 3개의 게시물은 핀고정 가능성 때문에 무조건 확인
            if total_posts_in_period < 3:
                total_posts_in_period += 1
                print(f"핀고정 가능성 있는 게시물 {total_posts_in_period}/3 확인 중...")
            else:
                # 4번째 게시물부터 기간 체크
                if not is_within_period(post_date, weeks):
                    print(f"\n{weeks}주 이전 게시물을 발견했습니다. 크롤링을 종료합니다.")
                    return total_posts_in_period, keyword_posts
                total_posts_in_period += 1  # 기간 내 게시물 카운트 증가
            
            print(f"기간 내 총 게시물 수: {total_posts_in_period}")
            
            # 다음 피드로 이동 (1주일 이내의 모든 피드)
            i = 1
            while True:  # 무한 루프로 변경
                # 게시물 120개 제한 체크
                if total_posts_in_period >= 120:
                    print("\n120개의 게시물을 확인했습니다. 다음 계정으로 넘어갑니다.")
                    return total_posts_in_period, keyword_posts
                    
                try:
                    # 현재 URL 저장
                    current_url = driver.current_url
                    
                    # 다음 버튼 찾기
                    next_button = None
                    selector = "//span[contains(@style, 'rotate(90deg)')]/.."  # 90도 회전된 화살표(다음 버튼)의 부모 요소
                    
                    print("\n다음 버튼 찾는 중...")
                    try:
                        next_button = driver.find_element(By.XPATH, selector)
                        if next_button.is_displayed():
                            print("다음 버튼을 찾았습니다.")
                    except Exception as e:
                        print(f"다음 버튼을 찾을 수 없습니다: {str(e)}")
                        break
                    
                    if next_button is None:
                        print(f"{i+1}번째 피드로 이동할 수 없습니다. 다음 버튼을 찾을 수 없습니다.")
                        break
                    
                    print(f"\n{i+1}번째 피드로 이동합니다...")
                    driver.execute_script("arguments[0].click();", next_button)
                    
                    # 실제 사람처럼 랜덤한 시간 대기 (정규 분포 사용)
                    wait_time = abs(random.gauss(2.5, 2))  # 평균 6초, 표준편차 4초
                    # 최소 0.5초, 최대 50초로 제한
                    wait_time = max(0.5, min(wait_time, 20.0))
                    print(f"다음 피드 로딩 대기 중... ({wait_time:.1f}초)")
                    time.sleep(wait_time)
                    
                    # URL이 변경되었는지 확인
                    if driver.current_url == current_url:
                        print(f"{i+1}번째 피드로 이동하지 못했습니다. URL이 변경되지 않았습니다.")
                        print("현재 URL:", driver.current_url)
                        print("이전 URL:", current_url)
                        break
                    
                    # 다음 피드 정보 추출
                    next_post_data = {}
                    
                    # 작성자 ID 추출
                    author_element = driver.find_element(By.CSS_SELECTOR, "a[role='link'][tabindex='0']")
                    next_post_data['author'] = author_element.text.strip() or username  # author가 비어있으면 username 사용
                    
                    # 본문 내용 추출
                    try:
                        content_element = driver.find_element(By.CSS_SELECTOR, "h1._ap3a._aaco._aacu._aacx._aad7._aade")
                        next_post_data['content'] = content_element.text  # 전체 내용 저장
                        
                        # 게시 날짜 추출
                        time_element = driver.find_element(By.CSS_SELECTOR, "time._a9ze._a9zf")
                        post_date = time_element.get_attribute('datetime')
                        
                        # 키워드 검색 (모든 키워드 변형이 본문에 포함되어야 함)
                        content_lower = next_post_data['content'].lower().replace(' ', '')
                        if all(k.replace(' ', '') in content_lower for k in raw_keywords):
                            keyword_posts.append({
                                'url': driver.current_url,
                                'content': next_post_data['content'],
                                'date': post_date
                            })
                            print(f"\n✅ 모든 키워드가 포함된 게시물을 찾았습니다!")
                            print(f"게시물 내용: {next_post_data['content'][:100]}...")  # 내용 일부 출력
                        
                    except Exception as e:
                        print(f"\n본문 내용을 찾을 수 없습니다. 빈 내용으로 처리합니다.")
                        next_post_data['content'] = ""  # 빈 내용으로 설정
                    
                    # 게시 날짜 추출
                    time_element = driver.find_element(By.CSS_SELECTOR, "time._a9ze._a9zf")
                    post_date = time_element.get_attribute('datetime')
                    
                    # 처음 3개의 게시물은 핀고정 가능성 때문에 무조건 다음으로 넘어감
                    if total_posts_in_period < 3:
                        total_posts_in_period += 1
                        print(f"핀고정 가능성 있는 게시물 {total_posts_in_period}/3 확인 중...")
                    else:
                        # 4번째 게시물부터 기간 체크
                        if not is_within_period(post_date, weeks):
                            print(f"\n{weeks}주 이전 게시물을 발견했습니다. 크롤링을 종료합니다.")
                            return total_posts_in_period, keyword_posts
                        total_posts_in_period += 1  # 기간 내 게시물 카운트 증가
                    
                    print(f"기간 내 총 게시물 수: {total_posts_in_period}")
                    
                    i += 1  # 카운터 증가
                    
                except Exception as e:
                    print(f"{i+1}번째 피드로 이동하는 중 오류 발생: {str(e)}")
                    break
            
        except Exception as e:
            print(f"게시물 정보를 추출하는 중 오류 발생: {str(e)}")
            print("현재 페이지 소스:")
            print(driver.page_source[:500])  # 페이지 소스의 일부를 출력하여 디버깅

    except Exception as e:
        print(f"게시물을 클릭하는 중 오류 발생: {str(e)}")
        print("현재 페이지 소스:")
        print(driver.page_source[:500])  # 페이지 소스의 일부를 출력하여 디버깅

    return total_posts_in_period, keyword_posts

def take_break(username_count):
    """
    크롤링 중 휴식 시간을 관리하는 함수
    
    Args:
        username_count (int): 현재까지 처리한 username의 수
    """
    def show_countdown(seconds, break_type):
        """카운트다운을 보여주는 내부 함수"""
        start_time = time.time()
        while True:
            elapsed_time = int(time.time() - start_time)
            remaining = seconds - elapsed_time
            if remaining <= 0:
                break
            
            if break_type == "중간":
                mins, secs = divmod(remaining, 60)
                countdown = f"\r{break_type} 휴식 중: {mins}분 {secs}초 남음...     "
            else:  # "대규모"
                hours, remainder = divmod(remaining, 3600)
                mins, secs = divmod(remainder, 60)
                countdown = f"\r{break_type} 휴식 중: {hours}시간 {mins}분 {secs}초 남음...     "
            
            print(countdown, end='', flush=True)
            time.sleep(1)
        print("\r휴식 완료!            ")  # 카운트다운 종료 후 줄 정리

    # 중간 휴식 (15-25개 username마다)
    if username_count % random.randint(15, 25) == 0:
        break_time = random.randint(60, 720)  # 1-12분
        print(f"\n중간 휴식 시작 (총 {break_time//60}분 {break_time%60}초)...")
        show_countdown(break_time, "중간")

def load_sheet_data(service, spreadsheet_id):
    """스프레드시트 전체 데이터를 한 번에 로드"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{SHEET_NAME}!A:M'  # 시트명 변수 사용
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f"\n❌ 스프레드시트 로드 중 오류 발생: {str(e)}")
        return None

def batch_update_sheet(service, spreadsheet_id, updates):
    """여러 셀을 한 번에 업데이트"""
    max_retries = 3  # 최대 재시도 횟수
    retry_delay = 2  # 재시도 간 대기 시간(초)
    
    for attempt in range(max_retries):
        try:
            body = {
                'valueInputOption': 'RAW',
                'data': updates
            }
            result = service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            return result
        except Exception as e:
            if attempt < max_retries - 1:  # 마지막 시도가 아니면 재시도
                print(f"\n⚠️ 일괄 업데이트 실패 (시도 {attempt + 1}/{max_retries}). {retry_delay}초 후 재시도합니다...")
                print(f"오류 내용: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # 지수 백오프: 대기 시간을 2배로 증가
            else:  # 마지막 시도에서도 실패
                print(f"\n❌ 일괄 업데이트 중 오류 발생 (최대 재시도 횟수 초과): {str(e)}")
                return None

def process_next_username(service, spreadsheet_id, usernames):
    """다음 크롤링할 계정을 찾고 상태를 업데이트"""
    global PROCESSED_USERNAMES  # 전역 변수 사용
    max_retries = 3  # 최대 재시도 횟수
    retry_delay = 2  # 재시도 간 대기 시간(초)
    
    for attempt in range(max_retries):
        try:
            # 스프레드시트 데이터를 한 번에 로드
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f'{SHEET_NAME}!A:M'  # 시트명 변수 사용
            ).execute()
            sheet_data = result.get('values', [])
            
            if not sheet_data:
                print("스프레드시트에서 데이터를 찾을 수 없습니다.")
                return None, None, None  # URL도 None으로 반환
            
            # username과 행 번호, URL 매핑
            username_to_row = {}
            username_to_url = {}

            # 헤더 제외하고 데이터 처리
            for i, row in enumerate(sheet_data[1:], start=2):  # 2부터 시작 (1-based, 헤더 제외)
                if not row or len(row) < 2:  # 빈 행이나 URL이 없는 행 건너뛰기
                    continue
                    
                # B열의 URL 확인
                url = row[1]
                if not url or 'instagram.com' not in url.lower():
                    continue
                
                # URL에서 username 추출
                username = url.split('instagram.com/')[-1].split('?')[0].split('/')[0]
                
                if username not in usernames:  # 크롤링 대상 목록에 없는 경우 건너뛰기
                    continue
                
                # 이미 처리한 username인 경우 건너뛰기
                if username in PROCESSED_USERNAMES:
                    print(f"\n⏭️ {username} 계정은 이미 처리되었습니다.")
                    continue
                
                # C열이 비어있는지 확인
                content = row[2] if len(row) > 2 else ""
                if content.strip():
                    print(f"\n⏭️ {username} 계정은 이미 C열에 내용이 있어 건너뜁니다.")
                    PROCESSED_USERNAMES.add(username)  # 처리된 username으로 표시
                    continue
                    
                username_to_row[username] = i
                username_to_url[username] = url
                PROCESSED_USERNAMES.add(username)  # 처리된 username으로 표시
                
                print(f"\n🔄 {username} 계정 크롤링을 시작합니다.")
                return username_to_row, username, username_to_url[username]

            print("\n더 이상 크롤링할 계정이 없습니다.")
            return username_to_row, None, None

        except Exception as e:
            if attempt < max_retries - 1:  # 마지막 시도가 아니면 재시도
                print(f"\n⚠️ 스프레드시트 처리 실패 (시도 {attempt + 1}/{max_retries}). {retry_delay}초 후 재시도합니다...")
                print(f"오류 내용: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # 지수 백오프: 대기 시간을 2배로 증가
            else:  # 마지막 시도에서도 실패
                print(f"\n❌ 스프레드시트 처리 중 오류 발생 (최대 재시도 횟수 초과): {str(e)}")
                return None, None, None

def update_crawl_date(service, spreadsheet_id, username, post_count, error_log=None):
    """Google Sheets의 M열에 게시물 수와 에러 로그 업데이트"""
    try:
        # 전체 데이터 가져오기
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{SHEET_NAME}!A:M'  # 시트명 변수 사용
        ).execute()
        values = result.get('values', [])

        # username이 있는 행 찾기
        row_number = None
        for i, row in enumerate(values):
            if row and row[0] == username:
                row_number = i + 1  # 1-based index
                break

        if row_number:
            # M열 업데이트
            range_name = f'{SHEET_NAME}!M{row_number}'  # 시트명 변수 사용
            
            # 에러가 있는 경우와 없는 경우 구분
            if error_log:
                body = {
                    'values': [[f"게시물 수: {post_count}개, 에러: {error_log}"]]
                }
                print(f"\n❌ {username}의 크롤링 중 에러 발생. 에러 로그가 기록되었습니다.")
            else:
                body = {
                    'values': [[f"게시물 수: {post_count}개"]]
                }
                print(f"\n✅ {username}의 크롤링이 완료되었습니다. ({post_count}개 게시물)")

            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()

        else:
            print(f"\n❌ {username}을 스프레드시트에서 찾을 수 없습니다.")

    except Exception as e:
        print(f"\n❌ 크롤링 결과 업데이트 중 오류 발생: {str(e)}")

def update_crawl_result(service, spreadsheet_id, username, username_to_row, post_count, keyword_posts, error_log=None):
    """크롤링 결과 업데이트"""
    if username not in username_to_row:
        print(f"\n❌ {username}을 행 매핑에서 찾을 수 없습니다.")
        return

    row_number = username_to_row[username]

    # 키워드가 포함된 게시물 정보 생성
    keyword_info = ""
    if keyword_posts:
        # C열에 첫 번째 키워드 게시물 URL 저장
        c_update = {
            'range': f'{SHEET_NAME}!C{row_number}',
            'values': [[keyword_posts[0]['url']]]
        }
        batch_update_sheet(service, spreadsheet_id, [c_update])
        
        # M열에 첫 번째 키워드 게시물의 날짜만 표시 (YYMMDD 형식)
        first_post_date = datetime.fromisoformat(keyword_posts[0]['date'].replace('Z', '+00:00'))
        formatted_date = first_post_date.strftime('%y%m%d')
        keyword_info = formatted_date

    # M열 업데이트
    m_update = {
        'range': f'{SHEET_NAME}!M{row_number}',
        'values': [[keyword_info]]
    }

    result = batch_update_sheet(service, spreadsheet_id, [m_update])
    if result:
        if error_log:
            print(f"\n❌ {username}의 크롤링 중 에러 발생. 에러 로그가 기록되었습니다.")
        else:
            print(f"\n✅ {username}의 크롤링이 완료되었습니다.")
            if keyword_posts:
                print(f"✅ 첫 번째 키워드 게시물 URL이 C열에 저장되었습니다.")
                print(f"✅ 첫 번째 키워드 게시물의 작성일이 M열에 저장되었습니다.")
            else:
                print(f"ℹ️ 키워드가 포함된 게시물을 찾지 못했습니다.")

# 메인 실행 코드
def main():
    global SHEET_NAME, SPREADSHEET_ID, PROCESSED_USERNAMES  # 전역 변수 사용 선언
    
    # 처리된 username 초기화
    PROCESSED_USERNAMES.clear()
    
    # 시트 선택
    selected_sheet = select_sheet()
    if not selected_sheet:
        print("시트를 선택할 수 없어 프로그램을 종료합니다.")
        return

    # Google Sheets API 설정
    RANGE_NAME = f'{SHEET_NAME}!A:B'  # A열과 B열 모두 가져오기

    # Google Sheets API 인증 및 서비스 객체 생성
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    # 스프레드시트에서 데이터 가져오기
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('스프레드시트에서 데이터를 찾을 수 없습니다.')
        return

    # 헤더 제거 (첫 번째 행 건너뛰기)
    usernames = []
    for row in values[1:]:  # 빈 행 제외
        if len(row) > 1 and row[1]:  # B열에 URL이 있는 경우
            url = row[1]
            if 'instagram.com' in url.lower():
                # URL에서 username 추출
                username = url.split('instagram.com/')[-1].split('?')[0].split('/')[0]
                usernames.append(username)
                print(f"추가된 username: {username}")

    if not usernames:
        print('크롤링할 계정이 없습니다.')
        return

    print(f"\n총 {len(usernames)}개의 계정이 크롤링 대상입니다.")

    # 크롤링 기간 입력 받기
    while True:
        try:
            weeks = int(input("\n크롤링할 기간을 주 단위로 입력하세요 (예: 9주(63일) = 9): "))
            if weeks > 0:
                break
            print("1 이상의 숫자를 입력해주세요.")
        except ValueError:
            print("올바른 숫자를 입력해주세요.")

    # 검색할 키워드 입력 받기
    keyword = input("\n검색할 키워드를 입력하세요: ").strip()
    if not keyword:
        print("키워드를 입력해주세요.")
        return

    # 키워드 변형 생성 (원본, 띄어쓰기 제거)
    keyword_variations = [
        keyword.lower(),  # 원본 키워드
        keyword.lower().replace(" ", "")  # 띄어쓰기 제거
    ]
    print(f"\n검색 키워드 변형: {keyword_variations}")

    # 로그인 정보 파일 경로 설정 (상대 경로 사용)
    login_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "0_insta_login.txt")
    with open(login_file_path, 'r', encoding='utf-8') as f:
        profile_name = f.read().strip()

    # 사용자 데이터 디렉토리 설정 (상대 경로 사용)
    user_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data", profile_name)

    try:
        while True:
            # 다음 크롤링할 계정 찾기
            username_to_row, next_username, next_url = process_next_username(service, SPREADSHEET_ID, usernames)
            
            if not username_to_row or not next_username or not next_url:
                print("\n크롤링을 종료합니다.")
                break

            try:
                # Chrome 옵션 설정
                options = Options()
                options.add_argument("--start-maximized")
                options.add_experimental_option("detach", True)
                options.add_argument("disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-logging"])
                options.add_argument(f"user-data-dir={user_data_dir}")
                options.add_argument("--disable-application-cache")
                options.add_argument("--disable-cache")

                # 캐시와 임시 파일 정리 (로그인 정보 유지)
                clear_chrome_data(user_data_dir)

                # 새로운 Chrome 드라이버 시작
                driver = webdriver.Chrome(options=options)

                print(f"\n{next_username} 계정 크롤링을 시작합니다...")
                print(f"\n프로필 URL({next_url})로 이동합니다...")
                driver.get(next_url)
                
                # 프로필 페이지의 주요 요소가 로드될 때까지 대기
                try:
                    # 프로필 이미지나 게시물 그리드가 로드될 때까지 대기
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div._aagv"))
                    )
                    print("프로필 페이지가 성공적으로 로드되었습니다.")
                except Exception as e:
                    print(f"프로필 페이지 로딩 중 오류 발생: {str(e)}")
                    raise

                # 크롤링 실행 및 게시물 수 받기
                post_count, keyword_posts = crawl_instagram_posts(driver, next_url, weeks, next_username, keyword)
                
                # 크롤링 결과 업데이트
                update_crawl_result(service, SPREADSHEET_ID, next_username, username_to_row, post_count, keyword_posts)
                
                # 브라우저 종료
                print(f"\n{next_username} 계정 크롤링 완료. 브라우저를 종료합니다.")
                driver.quit()
                
                # 휴식 시간 관리
                take_break(usernames.index(next_username) + 1)

            except Exception as e:
                error_message = f"{datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')} - {str(e)}"
                update_crawl_result(service, SPREADSHEET_ID, next_username, username_to_row, 0, [], error_message)
                if 'driver' in locals():
                    driver.quit()
                continue

    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
    finally:
        print("\n모든 계정의 크롤링이 완료되었습니다.")
        input("프로그램을 종료하려면 엔터를 누르세요...")

if __name__ == "__main__":
    main()
