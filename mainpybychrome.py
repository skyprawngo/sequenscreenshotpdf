import os
import io
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
import time
import socket
import atexit
import subprocess
from subprocess import Popen
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# URL 저장 파일 경로
URL_SAVE_FILE = "./env.json"

def save_env(key, url):
  #JSON 파일에 URL 저장 (기존 데이터 유지 및 수정)
  # 기존 데이터 불러오기
  data = {}
  if os.path.exists(URL_SAVE_FILE):
    with open(URL_SAVE_FILE, "r") as file:
      try:
        data = json.load(file)
      except json.JSONDecodeError:
        print("JSON 파일이 비어 있거나 손상되었습니다. 새로 생성합니다.")

  # 새로운 데이터 추가 또는 수정
  data[key] = url

  # JSON 파일에 저장
  with open(URL_SAVE_FILE, "w") as file:
    json.dump(data, file, indent=4)
  print(f"'{key}'에 대한 URL 저장 완료: {url}")

def register_exit_handler(driver):
  #프로그램 종료 시 URL을 자동으로 저장
  def save_url_on_exit():
    if driver and driver.current_url:  # driver와 current_url이 유효한 경우만 저장
      save_env("last_url", driver.current_url)
    print("프로그램 종료 시 URL 자동 저장 완료.")
  
  # atexit에 종료 핸들러 등록
  atexit.register(save_url_on_exit)

def load_env(key):
  # JSON 파일에서 특정 키의 URL 불러오기
  if os.path.exists(URL_SAVE_FILE):
    with open(URL_SAVE_FILE, "r") as file:
      try:
        data = json.load(file)
        return data.get(key)  # 해당 키의 URL 반환
      except json.JSONDecodeError:
        print("JSON 파일이 비어 있거나 손상되었습니다.")
        return None
  return None

def is_chrome_open(port):
  # 포트가 열려 있는지 확인 (Chrome이 실행 중인지 체크)
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    result = sock.connect_ex(('127.0.0.1', port))
  return result == 0

def start_chrome_with_debugger(port, user_data_dir, chrome_path):
  # Chrome 디버깅 모드로 실행. 디버깅 포트가 열려 있지 않으면 Chrome을 시작.
  if not is_chrome_open(port):
    print(f"Chrome 디버깅 포트 {port}이 열려있지 않습니다. Chrome을 새로 시작합니다.")
    Popen([
      chrome_path,
      f"--remote-debugging-port={port}",
      f"--user-data-dir={user_data_dir}"
    ])
    time.sleep(5)  # Chrome이 완전히 열리도록 대기
  else:
    print(f"Chrome 디버깅 포트 {port}이 이미 열려 있습니다.")

def compare_and_get_reset_url(set_url, loaded_url):
  # set_url과 loaded_url의 id와 pg 값을 비교하여 reset_url을 반환
  if not loaded_url:  # loaded_url이 None인 경우 기본 set_url 반환
    return set_url

  # URL 파싱
  set_url_parsed = urlparse(set_url)
  loaded_url_parsed = urlparse(loaded_url)

  # 쿼리 파라미터 추출
  set_params = parse_qs(set_url_parsed.query)
  loaded_params = parse_qs(loaded_url_parsed.query)

  # id 값 비교
  if set_params.get("id") == loaded_params.get("id"):
    # pg 값 비교
    set_pg = set_params.get("pg", [""])[0]
    loaded_pg = loaded_params.get("pg", [""])[0]

    # pg 값 순서 비교 함수
    def pg_to_order(pg):
      if not pg.startswith("GBS."):
        return float('inf')  # 예외적으로 잘못된 형식은 가장 큰 값으로 처리
      pg = pg[4:]  # "GBS." 제거
      prefix_order = {"PP": 1, "PA": 2, "RA": 3}  # 우선순위 정의 (RA 유지)
      prefix = pg[:2]  # "PP", "PA", "RA" 추출
      number = int(pg[2:]) if pg[2:].isdigit() else float('inf')  # 숫자 추출
      
      # "RA"를 "RA1-PA"로 변경
      if prefix == "RA":
        prefix = "RA1-PA"
      
      return (prefix_order.get(prefix, float('inf')), number)

    # pg 순서 비교
    set_order = pg_to_order(set_pg)
    loaded_order = pg_to_order(loaded_pg)

    # 더 큰 pg 값을 reset_url로 선택
    if loaded_order > set_order:
      reset_params = loaded_params
    else:
      reset_params = set_params
  else:
    # id 값이 다르면 기본 set_url 사용
    reset_params = set_params

  # 새로운 URL 생성
  reset_url = urlunparse((
    set_url_parsed.scheme,
    set_url_parsed.netloc,
    set_url_parsed.path,
    set_url_parsed.params,
    urlencode(reset_params, doseq=True),
    set_url_parsed.fragment
  ))
  return reset_url

def capture_screen_as_png(output_path):
  """전체 화면 스크린샷을 저장"""
  try:
    # 브라우저의 전체 화면을 스크린샷으로 저장
    screenshot = driver.get_screenshot_as_png()
    with open(output_path, "wb") as file:
      file.write(screenshot)
    print(f"전체 화면 스크린샷 저장 완료: {output_path}")
  except Exception as e:
    print(f"전체 화면 스크린샷 저장 중 오류 발생: {e}")
    
def main_func():
  reset_url = compare_and_get_reset_url(set_url, loaded_url)
  print(f"선택된 reset_url: {reset_url}")

  # 새로고침 방지
  if driver.current_url != reset_url:
    driver.get(reset_url)
    time.sleep(4)
  else:
    time.sleep(1)

  try:
    # iframe으로 전환
    iframe = WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)  # 첫 번째 iframe으로 전환
    print("iframe으로 전환 성공")

    # 전체 화면 스크린샷
    capture_screen_as_png("full_screen_screenshot.png")

  except Exception as e:
    print(f"iframe 내에서 오류 발생: {e}")
  finally:
    # iframe에서 기본 컨텍스트로 돌아오기
    driver.switch_to.default_content()

  # 현재 URL 저장
  save_env("last_url", driver.current_url)

  # 브라우저 종료하지 않음
  print("브라우저는 종료되지 않고 유지됩니다. 저장된 URL로 다음 실행에 재사용 가능합니다.")
  
# 전역 변수
# ChromeDriver와 연결된 포트 정보 설정
CHROME_DEBUGGER_PORT = 9222
USER_DATA_DIR = "/tmp/chrome_debug"  # 세션 유지 디렉토리
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
set_url = "https://play.google.com/books/reader?id=FB-rEAAAQBAJ&pg=GBS.PP1"
loaded_url = load_env("last_url")

def initialize_driver():
  # ChromeDriver 초기화 및 설정
  global driver  # 전역으로 설정하여 다른 함수에서 접근 가능
  start_chrome_with_debugger(CHROME_DEBUGGER_PORT, USER_DATA_DIR, CHROME_PATH)
  chrome_options = Options()
  chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUGGER_PORT}")
  chrome_options.add_argument(f"user-data-dir={USER_DATA_DIR}")
  chrome_options.add_argument("--disable-dev-shm-usage")
  chrome_options.add_argument("--disable-devtools")
  chrome_options.add_argument("--lang=ko")

  driver = webdriver.Chrome(options=chrome_options)
  driver.set_window_size(1920, 1080)
  time.sleep(2)
  
  # 종료 핸들러 등록
  register_exit_handler(driver)

def main():
  # 프로그램 실행
  try:
    initialize_driver()
    main_func()
  except Exception as e:
    print(f"예외 발생: {e}")
  finally:
    # 프로그램이 비정상 종료되더라도 URL 자동 저장 보장
    if driver and driver.current_url:
      save_env("last_url", driver.current_url)
      print("예외 처리 중 URL 자동 저장 완료.")

# 프로그램 실행
if __name__ == "__main__":
  main()