import asyncio
import nest_asyncio
import csv
from datetime import datetime
from playwright.async_api import async_playwright

nest_asyncio.apply()
URL = "https://www.cos.com/ko-kr/women/dresses.html"

async def collect_all_products(page):
    products = []
    seen = set()
    prev_category = ""

    await page.wait_for_selector("div.o-product", timeout=10000)

    while True:
        await page.wait_for_timeout(2000)

        try:
            category_el = await page.query_selector("h1.pb-5.uppercase.font_m_semibold")
            current_category = await category_el.inner_text() if category_el else ""
            if current_category:
                prev_category = current_category.strip()
        except:
            pass

        cards = await page.query_selector_all("a.a-link.no-styling")
        print(f"📦 현재 보이는 상품 수: {len(cards)}")

        for card in cards:
            image_urls = []

            img1 = await card.query_selector("img.a-image.product-image")
            src1 = await img1.get_attribute("src") if img1 else None
            if src1:
                image_urls.append(src1)

            img2 = await card.query_selector("img.a-image.default-image")
            src2 = await img2.get_attribute("src") if img2 else None
            if src2:
                image_urls.append(src2)

            tourl = await card.get_attribute("data-tourl")
            url = "https://www.cos.com" + tourl if tourl else None

            if url and url not in seen:
                seen.add(url)
                products.append({
                    "images": image_urls,
                    "url": url,
                    "tourl": tourl or "",
                    "category": prev_category
                })

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

async def get_product_detail_by_dataurl(context, tourl: str):
    try:
        if not tourl:
            return "", "", "", "", "", ""

        url = "https://www.cos.com" + tourl
        detail_page = await context.new_page()
        response = await detail_page.goto(url, timeout=60000)
        if not response or response.status != 200:
            print(f"⚠️ 유효하지 않은 URL (status: {response.status if response else 'N/A'}): {url}")
            await detail_page.close()
            return "", "", "", "", "", ""

        await detail_page.wait_for_selector("h1#product-detail-name", timeout=10000)

        title_el = await detail_page.query_selector("h1#product-detail-name")
        title = await title_el.inner_text() if title_el else ""

        price_el = await detail_page.query_selector("label#priceValue")
        price = await price_el.inner_text() if price_el else ""

        material = color = ""
        try:
            await detail_page.click("a#essentialLink")
            await detail_page.wait_for_timeout(1000)
            rows = await detail_page.query_selector_all("div.information-product table tr")
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

        color_classification_url = ""
        try:
            color_img_el = await detail_page.query_selector("div#pdpSelectedColor img")
            if color_img_el:
                color_classification_url = await color_img_el.get_attribute("src") or ""
        except:
            pass

        details_text = ""
        try:
            desc_p = await detail_page.query_selector("div.description-text p")
            desc_text = await desc_p.inner_text() if desc_p else ""

            fit_li = await detail_page.query_selector("div.description-text ul li")
            fit_text = await fit_li.inner_text() if fit_li else ""

            if desc_text or fit_text:
                details_text = desc_text.strip()
                if fit_text:
                    details_text += f". 핏: {fit_text.strip()}"
        except:
            pass

        await detail_page.close()
        return title.strip(), price.strip(), material, color, color_classification_url, details_text
    except Exception as e:
        print(f"❌ 상세 진입 실패: {e}")
        return "", "", "", "", "", ""

def print_product_info(item: dict, idx: int):
    print(f"\n📥 {idx}번째 상품 정보")
    print(item.get("category", ""))
    print(item.get("product_name", ""))
    print(item.get("current_price", ""))
    print(item.get("color", ""))
    print(item.get("material", ""))
    print(item.get("details", ""))
    print(item.get("front_images_url", ""))
    print(item.get("product_detail_url", ""))
    print(item.get("color_classification_url", ""))
    print("-" * 80)

def save_to_csv(data):
    date_str = datetime.now().strftime("%y%m%d")
    filename = f"cos_woman_{date_str}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow([
            "category",
            "product_name",
            "current_price",
            "color",
            "material",
            "details",
            "front_images_url",
            "product_detail_url",
            "color_classification_url"
        ])
        for item in data:
            writer.writerow([
                item.get("category", ""),
                item.get("product_name", ""),
                item.get("current_price", ""),
                item.get("color", ""),
                item.get("material", ""),
                item.get("details", ""),
                item.get("front_images_url", ""),
                item.get("product_detail_url", ""),
                item.get("color_classification_url", "")
            ])
    print(f"\n💾 저장 완료: {filename}")

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
            title, price, material, color, color_classification_url, details_text = await get_product_detail_by_dataurl(context, item["tourl"])

            result_item = {
                "category": item['category'],
                "product_name": title,
                "current_price": price,
                "color": color,
                "material": material,
                "details": details_text,
                "front_images_url": ', '.join(item['images']) if item['images'] else "",
                "product_detail_url": item['url'],
                "color_classification_url": color_classification_url
            }

            result.append(result_item)
            print_product_info(result_item, idx)

        await browser.close()
        save_to_csv(result)

if __name__ == "__main__":
    asyncio.run(main())