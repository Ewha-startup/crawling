from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import csv
import re

# 셀레니움 브라우저 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 시작 URL
base_url = "https://www.ssfshop.com/8seconds/WOMEN/list?dspCtgryNo=SFMA41&brandShopNo=BDMA07A01&brndShopId=8SBSS&sortColumn=NEW_GOD_SEQ&serviceType=DSP&ctgrySectCd=GNRL_CTGRY&fitPsbYn=N"
driver.get(base_url)
time.sleep(3)

page_count = 1
max_pages = 2

result_data = []

# 1차 리스트 수집
while page_count <= max_pages:

    print(f"{page_count} 페이지 수집 중...")

    products = driver.find_elements(By.CSS_SELECTOR, "li.god-item")

    for p in products:
        try:
            img = p.find_element(By.CSS_SELECTOR, '.god-img img').get_attribute('src')
            name = p.find_element(By.CSS_SELECTOR, '.god-info .name').text
            price = p.find_element(By.CSS_SELECTOR, '.god-info .price').text

            onclick = p.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
            match = re.search(r"goToProductDetail\('.*?','(.*?)'", onclick)
            if match:
                product_code = match.group(1)
                detail_url = f"https://www.ssfshop.com/8-seconds/{product_code}/good"
            else:
                detail_url = '상세링크 추출 실패'

            result_data.append({
                '상품명': name,
                '가격': price,
                '썸네일이미지': img,
                '상세페이지링크': detail_url
            })

        except Exception as e:
            print("리스트 수집 에러:", e)
            continue

    try:
        next_button = driver.find_element(By.CSS_SELECTOR, '#page_next')
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

print("1차 리스트 수집 완료!")

# 2차 상세페이지 진입해서 소재정보 및 스펙 수집
final_data = []

for item in result_data:
    try:
        driver.get(item['상세페이지링크'])
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 소재 파싱 (팝업 클릭 안 하고 숨겨진 html 바로 파싱)
        material_dd = soup.select_one('#materialAdit .material-group dl dd:nth-of-type(2)')
        material = material_dd.text.strip() if material_dd else '소재 없음'

        spec_data = {}
        table_rows = soup.select('#materialAdit table tbody tr')
        for row in table_rows:
            th_elem = row.select_one('th')
            if not th_elem:
                continue
            category = th_elem.text.strip()
            selected_td = row.select_one('td.on')
            value = selected_td.text.strip() if selected_td else ''
            spec_data[category] = value

        print(f"[상세] {item['상품명']} | 소재: {material} | {spec_data}")

        # 데이터 저장
        final_data.append({
            '상품명': item['상품명'],
            '가격': item['가격'],
            '썸네일이미지': item['썸네일이미지'],
            '상세페이지링크': item['상세페이지링크'],
            '소재': material,
            '착용시기': spec_data.get('착용시기', ''),
            '신축성': spec_data.get('신축성', ''),
            '비침': spec_data.get('비침', ''),
            '안감': spec_data.get('안감', '')
        })

    except Exception as e:
        print("상세페이지 수집 에러:", e)
        continue

driver.quit()
print("모든 페이지 크롤링 완료!")

# CSV 저장
keys = ['상품명', '가격', '썸네일이미지', '상세페이지링크', '소재', '착용시기', '신축성', '비침', '안감']
with open('8seconds_product_full.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for data in final_data:
        writer.writerow(data)

print("CSV 저장 완료!")
