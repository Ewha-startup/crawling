from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from bs4 import BeautifulSoup

# 셀레니움 셋업
options = webdriver.ChromeOptions()
options.add_argument('--window-size=1920,1080')
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--log-level=3')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

base_url = "https://www.uniqlo.com/kr/ko/women/shirts-and-blouses"

driver.get(base_url)
time.sleep(3)

# 무한스크롤
SCROLL_PAUSE_TIME = 1.5
prev_height = driver.execute_script("return document.body.scrollHeight")

while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE_TIME)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == prev_height:
        break
    prev_height = new_height

print("스크롤 완료. 상품링크 수집 시작.")

# 상품 링크 수집
product_elements = driver.find_elements(By.CSS_SELECTOR, "div.fr-ec-product-tile-resize-wrapper a.fr-ec-tile")
product_links = [elem.get_attribute("href") for elem in product_elements]

print(f"총 {len(product_links)}개 상품 발견.\n")

result_data = []

# 상세페이지 진입
for idx, link in enumerate(product_links):
    print(f"\n[{idx+1}/{len(product_links)}] 상세페이지 수집 중: {link}")
    try:
        driver.get(link)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 상품명
        try:
            name = soup.select_one("main h1").text.strip()
        except:
            name = ''

                
        # 가격
        # 가격 추출
        try:
            price_tag = soup.select_one("p.fr-ec-price-text--large.fr-ec-price-text--color-promotional")
            if not price_tag:
                price_tag = soup.select_one("p.fr-ec-price-text--large.fr-ec-price-text--color-primary-dark")
            price = price_tag.text.strip() if price_tag else ''
        except:
            price = ''



        # 기능 세부 정보
        feature_dl = soup.select_one('#productLongDescription-content dl')
        features = {'비침':'', '핏':'', '포켓':''}

        if feature_dl:
            feature_text = feature_dl.get_text(separator='\n')
            for line in feature_text.split('\n'):
                line = line.strip()
                if '비침:' in line:
                    features['비침'] = line.split(':', 1)[1].strip()
                elif '핏:' in line:
                    features['핏'] = line.split(':', 1)[1].strip()
                elif '포켓' in line:
                    features['포켓'] = line.split(':', 1)[1].strip()
        else:
            print("※ 기능 세부정보 없음")

        # 소재
        material_dl = soup.select_one('#productMaterialDescription-content dl')
        material = ''
        if material_dl:
            for dt in material_dl.select('dt'):
                if dt.text.strip() == '소재':
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        material = dd.text.strip()

        # 상세 이미지 (마지막 이미지)
        image_divs = soup.select("div.media-gallery--grid img")
        detail_img = ''
        if image_divs:
            detail_img = image_divs[-1].get("src")

        # 디버깅 로그
        print(f"상품명: {name}")
        print(f"가격: {price}")
        print(f"비침: {features['비침']} / 핏: {features['핏']} / 포켓: {features['포켓']}")
        print(f"소재: {material}")
        print(f"상세이미지: {detail_img}")

        result_data.append({
            '상품명': name,
            '가격': price,
            '상세링크': link,
            '비침': features['비침'],
            '핏': features['핏'],
            '포켓': features['포켓'],
            '소재': material,
            '상세이미지': detail_img
        })

    except Exception as e:
        print("상세페이지 수집 에러:", e)
        continue

driver.quit()

# CSV 저장
keys = ['상품명', '가격', '상세링크', '비침', '핏', '포켓', '소재', '상세이미지']
with open('uniqlo_product_detail_full.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for data in result_data:
        writer.writerow(data)

print("\nCSV 저장 완료!")
