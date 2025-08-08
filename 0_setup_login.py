"""
인스타그램 로그인 정보 설정 스크립트

이 스크립트는 인스타그램 크롤링을 위한 로그인 정보를 설정합니다.
1. user_data 폴더 생성
2. 로그인 정보 입력 및 저장
3. 0_insta_login.txt 파일 생성

사용 방법:
1. 이 스크립트를 실행합니다.
2. 프롬프트에 따라 로그인 정보를 입력합니다.
3. 입력된 정보는 user_data 폴더에 저장됩니다.
"""

import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def create_user_data_folder(profile_name):
    """user_data 폴더와 프로필 폴더를 생성합니다."""
    # 현재 스크립트의 상위 디렉토리 경로
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # user_data 폴더 경로
    user_data_dir = os.path.join(base_dir, "user_data")
    
    # 프로필 폴더 경로
    profile_dir = os.path.join(user_data_dir, profile_name)
    
    # user_data 폴더가 없으면 생성
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
        print(f"user_data 폴더가 생성되었습니다: {user_data_dir}")
    
    # 프로필 폴더가 없으면 생성
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
        print(f"프로필 폴더가 생성되었습니다: {profile_dir}")
    
    return profile_dir

def save_login_info(profile_name):
    """로그인 정보를 0_insta_login.txt 파일에 저장합니다."""
    # 현재 스크립트의 상위 디렉토리 경로
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # 0_insta_login.txt 파일 경로
    login_file_path = os.path.join(base_dir, "0_insta_login.txt")
    
    # 파일에 프로필 이름 저장
    with open(login_file_path, 'w', encoding='utf-8') as f:
        f.write(profile_name)
    
    print(f"로그인 정보가 저장되었습니다: {login_file_path}")

def setup_chrome_profile(profile_dir):
    """Chrome 프로필을 설정하고 로그인을 수행합니다."""
    options = Options()
    options.add_argument(f"user-data-dir={profile_dir}")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)
    options.add_argument("disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # 인스타그램 로그인 페이지로 이동
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)
        
        print("\n인스타그램 로그인 페이지가 열렸습니다.")
        print("브라우저에서 로그인을 완료해주세요.")
        print("로그인이 완료되면 이 창에서 Enter 키를 눌러주세요...")
        input()
        
        # 로그인 확인
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='홈']"))
            )
            print("로그인이 성공적으로 완료되었습니다!")
        except:
            print("로그인 확인에 실패했습니다. 다시 시도해주세요.")
            return False
        
        return True
    
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return False
    
    finally:
        driver.quit()

def main():
    print("=== 인스타그램 로그인 정보 설정 ===")
    
    # 프로필 이름 입력
    while True:
        profile_name = input("\n사용할 프로필 이름을 입력하세요 (예: mini_goyamedia_feed): ").strip()
        if profile_name:
            break
        print("프로필 이름을 입력해주세요.")
    
    # user_data 폴더 생성
    profile_dir = create_user_data_folder(profile_name)
    
    # Chrome 프로필 설정 및 로그인
    if setup_chrome_profile(profile_dir):
        # 로그인 정보 저장
        save_login_info(profile_name)
        print("\n설정이 완료되었습니다!")
        print(f"프로필 이름: {profile_name}")
        print(f"프로필 폴더: {profile_dir}")
    else:
        print("\n설정에 실패했습니다. 다시 시도해주세요.")

if __name__ == "__main__":
    main() 