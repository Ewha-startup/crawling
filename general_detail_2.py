from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import csv

# 셀레니움 브라우저 설정
options = webdriver.ChromeOptions()
options.add_argument('--window-size=1920,1080')
options.add_argument('--headless')  
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 스크롤 함수: 1/3 확 내리고 → 천천히 끝까지
def hybrid_scroll(driver, step_size=300, pause_time=0.3):
    total_height = driver.execute_script("return document.body.scrollHeight")
    initial_target = int(total_height * 0.33)
    
    # 먼저 1/3 확 내리기
    driver.execute_script(f"window.scrollTo(0, {initial_target});")
    time.sleep(1)
    
    # 그 다음 slow scroll
    last_height = driver.execute_script("return document.body.scrollHeight")
    current_position = initial_target
    while current_position < last_height:
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(pause_time)
        current_position += step_size
        last_height = driver.execute_script("return document.body.scrollHeight")
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

# 시작 URL
base_url = "https://www.generalidea.co.kr"
start_url = base_url + "/product/list.html?cate_no=353&sort_method=5#Product_ListMenu"
driver.get(start_url)
time.sleep(3)

page_count = 1
max_pages = 2
result_data = []
product_links = []

# 1단계: 전체 상품 리스트에서 링크 수집
while page_count <= max_pages:
    print(f"{page_count} 페이지 수집 중...")

    products = driver.find_elements(By.CSS_SELECTOR, "ul.prdList li[id^='anchorBoxId_']")
    for p in products:
        try:
            inner_html = p.get_attribute('innerHTML')
            soup = BeautifulSoup(inner_html, 'html.parser')

            img_tag = soup.select_one('.thumbnail .prdImg img.thumber_2') or soup.select_one('.thumbnail .prdImg img.thumber_1')
            img = img_tag['src'] if img_tag else '이미지 없음'
            if img.startswith("//"):
                img = "https:" + img

            name_tag = soup.select_one('.description .name a')
            name = name_tag.text.split(':')[-1].strip() if name_tag else '상품명 없음'

            price_li = soup.select_one('li.product_price')
            if price_li:
                full_text = price_li.get_text(separator=' ', strip=True)
                price_candidates = [part for part in full_text.split() if '₩' in part]
                price = price_candidates[0] if price_candidates else '가격 없음'
            else:
                price = '가격 없음'

            link_tag = soup.select_one('div.prdImg a')
            relative_link = link_tag['href'] if link_tag else ''
            link = base_url + relative_link

            product_links.append({
                '상품명': name,
                '가격': price,
                '썸네일이미지': img,
                '상세페이지링크': link
            })

        except Exception as e:
            print("리스트 수집 에러:", e)

    # 다음 페이지 이동
    try:
        next_buttons = driver.find_elements(By.CSS_SELECTOR, 'a.first_nt')
        if len(next_buttons) >= 2:
            next_buttons[1].click()
            time.sleep(3)
            page_count += 1
        else:
            print("다음 페이지 없음. 종료")
            break
    except Exception as e:
        print("페이지 이동 중 에러:", e)
        break

# 2단계: 상세페이지 수집
for item in product_links:
    try:
        driver.get(item['상세페이지링크'])
        time.sleep(2)

        hybrid_scroll(driver)  # <-- 여기에 핵심 스크롤 적용

        detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
        prd_detail = detail_soup.select_one('#prdDetailContentLazy')

        if prd_detail:
            img_tags = prd_detail.select('img')
            if len(img_tags) >= 2:
                detail_img = img_tags[-2].get('src')
                if detail_img.startswith("//"):
                    detail_img = "https:" + detail_img
            else:
                detail_img = '상세 이미지 부족'
        else:
            detail_img = '상세정보 없음'

        print(f"상품명: {item['상품명']} | 가격: {item['가격']} | 썸네일: {item['썸네일이미지']} | 상세이미지: {detail_img}\n")
        item['상세이미지'] = detail_img
        result_data.append(item)

    except Exception as e:
        print("상세페이지 진입 에러:", e)

driver.quit()
print("모든 페이지 크롤링 완료!")

# CSV 저장
keys = ['상품명', '가격', '썸네일이미지', '상세이미지', '상세페이지링크']
with open('generalidea_product_detail.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for data in result_data:
        writer.writerow(data)

print("CSV 저장 완료!")
