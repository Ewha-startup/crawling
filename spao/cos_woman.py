import asyncio
import nest_asyncio
import csv
from playwright.async_api import async_playwright

nest_asyncio.apply()

URL = "https://www.cos.com/ko-kr/women/jeans.html"

# ✅ 목록 수집
async def collect_all_products(page):
    products = []
    seen = set()

    await page.wait_for_selector("div.o-product", timeout=10000)

    # 카테고리 추출
    category_el = await page.query_selector("h1.pb-5.uppercase.font_m_semibold")
    category = await category_el.inner_text() if category_el else "❌"
    print(f"📌 현재 카테고리: {category}")

    while True:
        await page.wait_for_timeout(2000)

        cards = await page.query_selector_all("div.o-product")
        print(f"📦 현재 보이는 상품 수: {len(cards)}")

        for card in cards:
            image_urls = []

            # 대표 이미지
            img1 = await card.query_selector("img.a-image.product-image")
            src1 = await img1.get_attribute("src") if img1 else None
            if src1:
                image_urls.append(src1)

            # 백업 이미지
            img2 = await card.query_selector("img.a-image.default-image")
            src2 = await img2.get_attribute("src") if img2 else None
            if src2:
                image_urls.append(src2)

            # <a> 태그에서 data-tourl 추출
            link_el = await card.query_selector("a")
            tourl = await link_el.get_attribute("data-tourl") if link_el else None
            url = "https://www.cos.com" + tourl if tourl else None

            if url and url not in seen:
                seen.add(url)
                products.append({
                    "images": image_urls,
                    "url": url,
                    "category": category,
                    "element_handle": link_el
                })

        # 다음 페이지 버튼 처리
        try:
            buttons = await page.query_selector_all("button#load-more-product-list, button#next-category-product-list")
            clickable_btn = None
            for btn in buttons:
                if await btn.is_visible() and await btn.is_enabled():
                    clickable_btn = btn
                    break
            if clickable_btn:
                text = await clickable_btn.inner_text()
                if "NEXT CATEGORY: 모두 보기" in text:
                    print("✅ 마지막 버튼 — 종료")
                    break
                await clickable_btn.click()
                await page.wait_for_timeout(2000)
            else:
                print("🚫 클릭 가능한 버튼 없음 — 종료")
                break
        except Exception as e:
            print(f"⚠️ 버튼 클릭 실패: {e}")
            break

    return products

# ✅ 상세페이지 진입 (data-tourl 기반 이동)
async def get_product_detail_by_dataurl(page, element_handle):
    try:
        tourl = await element_handle.get_attribute("data-tourl")
        if not tourl:
            return "❌", "❌", "❌", "❌"

        url = "https://www.cos.com" + tourl
        print(f"🌐 이동 중: {url}")
        response = await page.goto(url, timeout=60000)
        if response.status != 200:
            print(f"⚠️ 유효하지 않은 URL (status: {response.status}): {url}")
            return "❌", "❌", "❌", "❌"

        await page.wait_for_selector("h1#product-detail-name", timeout=10000)

        title_el = await page.query_selector("h1#product-detail-name")
        title = await title_el.inner_text() if title_el else "❌"

        price_el = await page.query_selector("label#priceValue")
        price = await price_el.inner_text() if price_el else "❌"

        material = color = "❌"
        try:
            await page.click("a#essentialLink")
            await page.wait_for_timeout(1000)
            rows = await page.query_selector_all("div.information-product table tr")
            for row in rows:
                th = await row.query_selector("th")
                td = await row.query_selector("td")
                if th and td:
                    k = await th.inner_text()
                    v = await td.inner_text()
                    if "제품소재" in k:
                        material = v.strip()
                    if "색상" in k:
                        color = v.strip()
        except:
            pass

        return title.strip(), price.strip(), material, color
    except Exception as e:
        print(f"❌ 상세 진입 실패: {e}")
        return "❌", "❌", "❌", "❌"

# ✅ CSV 저장
def save_to_csv(data, filename="cos_woman_crawled_results.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(["category", "title", "price", "color", "material", "images"])

        for item in data:
            writer.writerow([
                item.get("category", ""),
                item.get("title", ""),
                item.get("price", ""),
                item.get("color", ""),
                item.get("material", ""),
                item.get("images", "")
            ])
    print(f"\n💾 저장 완료: {filename}")

# ✅ 메인 실행
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            bypass_csp=True,
        )
        page = await context.new_page()
        await page.goto(URL)
        await page.wait_for_load_state("domcontentloaded")

        products = await collect_all_products(page)

        result = []
        for idx, item in enumerate(products, 1):
            print(f"\n📥 {idx}번째 상품 수집 중: {item['url']}")
            title, price, material, color = await get_product_detail_by_dataurl(page, item["element_handle"])
            result.append({
                "title": title,
                "price": price,
                "material": material,
                "color": color,
                "images": ", ".join(item["images"]),
                "url": item["url"],
                "category": item["category"]
            })

        await browser.close()
        save_to_csv(result)

if __name__ == "__main__":
    asyncio.run(main())