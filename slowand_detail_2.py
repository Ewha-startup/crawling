from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import csv

# 셀레니움 브라우저 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

base_url = "https://slowand.com"
start_url = base_url + "/product/list.html?cate_no=66"
driver.get(start_url)
time.sleep(2)

page_count = 1
max_pages = 2
result_data = []

while page_count <= max_pages:
    print(f"{page_count} 페이지 수집 중...")

    products = driver.find_elements(By.CSS_SELECTOR, "ul.prdList li[id^='anchorBoxId_']")
    product_links = []

    for p in products:
        try:
            inner_html = p.get_attribute('innerHTML')
            soup = BeautifulSoup(inner_html, 'html.parser')

            name_tag = soup.select_one('.description .name a')
            name = name_tag.text.strip() if name_tag else '상품명 없음'

            img_tag = soup.select_one('.prdImg img')
            img = img_tag['src'] if img_tag else '이미지 없음'
            img = "https:" + img if img.startswith("//") else img

            link_tag = soup.select_one('.prdImg a')
            relative_link = link_tag['href'] if link_tag else ''
            link = base_url + relative_link

            product_links.append((name, img, link))
        except Exception as e:
            print("리스트 링크 수집 에러:", e)

    for name, img, link in product_links:
        try:
            driver.get(link)
            print(f"\n상세페이지 이동: {name}")

            # 스크롤 살짝 내려서 iframe 유도
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            # 첫번째 iframe 잡기 (작은 floating iframe)
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[id^='crema-fit-product-floating']"))
            )
            driver.switch_to.frame(iframe)
            print("[iframe 진입 성공]")

            # 버튼 대기 및 클릭
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".js-link-combined-detail"))
            )
            time.sleep(1)  # 살짝 여유
            button.click()
            print("[버튼 클릭 완료]")

            # 버튼 클릭 후 바깥으로 빠져나와서 새 iframe 로딩 대기
            driver.switch_to.default_content()
            new_iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[id^='crema-fullscreen-popup']"))
            )
            driver.switch_to.frame(new_iframe)
            print("[새로 로드된 iframe 재진입 성공]")

            # 상세 테이블 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.fit_product_combined_fit_product__property_table"))
            )

            # BeautifulSoup로 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            rows = soup.select('table.fit_product_combined_fit_product__property_table tr')

            details = {}
            for row in rows:
                key_tag = row.select_one('.fit_product_combined_fit_product__property_key')
                value_tag = row.select_one('.fit_product_combined_fit_product__property_table_content_col--selected .fit_product_combined_fit_product__property_value')
                if key_tag and value_tag:
                    key = key_tag.text.strip()
                    value = value_tag.text.strip()
                    details[key] = value

            print("[상세정보 수집 완료]", details)

            result_data.append({
                '상품명': name,
                '이미지': img,
                '상세링크': link,
                '안감': details.get('안감', ''),
                '두께감': details.get('두께감', ''),
                '계절감': details.get('계절감', ''),
                '비침': details.get('비침', ''),
                '신축성': details.get('신축성', '')
            })

            driver.switch_to.default_content()

        except Exception as e:
            print("상세페이지 수집 에러:", e)
            result_data.append({
                '상품명': name,
                '이미지': img,
                '상세링크': link,
                '안감': '',
                '두께감': '',
                '계절감': '',
                '비침': '',
                '신축성': ''
            })

    # 다음 페이지 이동
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, 'a.next')
        if next_button.is_enabled():
            next_button.click()
            time.sleep(3)
            page_count += 1
        else:
            print("다음 페이지 없음. 종료")
            break
    except:
        print("다음 페이지 없음. 종료")
        break

driver.quit()
print("\n모든 페이지 크롤링 완료!")

# CSV 저장
keys = ['상품명', '이미지', '상세링크', '안감', '두께감', '계절감', '비침', '신축성']
with open('slowand_product_detail.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for data in result_data:
        writer.writerow(data)

print("CSV 저장 완료!")
