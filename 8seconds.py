from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# 셀레니움 브라우저 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # 브라우저 창 안 띄움
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 시작 URL (처음 1페이지)
base_url = "https://www.ssfshop.com/8seconds/WOMEN/list?dspCtgryNo=SFMA41&brandShopNo=BDMA07A01&brndShopId=8SBSS&sortColumn=NEW_GOD_SEQ&serviceType=DSP&ctgrySectCd=GNRL_CTGRY&fitPsbYn=N"

driver.get(base_url)
time.sleep(3)

page_count = 1
max_pages = 2  # 수집할 최대 페이지 수

# 반복해서 페이지 넘기기
while page_count <= max_pages:

    print(f"{page_count} 페이지 수집 중...")

    products = driver.find_elements(By.CSS_SELECTOR, "li.god-item")
    for p in products:
        try:
            img = p.find_element(By.CSS_SELECTOR, '.god-img img').get_attribute('src')
            name = p.find_element(By.CSS_SELECTOR, '.god-info .name').text
            price = p.find_element(By.CSS_SELECTOR, '.god-info .price').text
            
            # color 추출
            color_spans = p.find_elements(By.CSS_SELECTOR, '.god-info .color span')
            colors = [c.text for c in color_spans]
            color_str = ', '.join(colors)

            print(f"상품명: {name} | 가격: {price} | 색상: {color_str} | 이미지: {img}")
        except Exception as e:
            print("에러 발생:", e)
            continue

    # 다음 페이지 버튼 확인
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, '#page_next')
        next_button.click()
        time.sleep(3)
        page_count += 1
    except:
        print("다음 페이지 없음. 종료")
        break

driver.quit()
print("모든 페이지 크롤링 완료!")




