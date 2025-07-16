import nest_asyncio
import asyncio
import csv
import re
from datetime import datetime
from playwright.async_api import async_playwright
from libs.spao.zara_woman_category import zara_woman_category

nest_asyncio.apply()

def extract_rgb(style_str):
    match = re.search(r"rgb\([^)]+\)", style_str)
    return match.group(0) if match else ""

# ✅ 상세페이지 크롤링
async def get_product_detail(context, url, thumbnail_url):
    try:
        page = await context.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)

        async def safe_text(element):
            return "" if not element else (await element.inner_text()).strip()

        name = await safe_text(await page.query_selector("h1"))
        price = await safe_text(await page.query_selector('span.price-current__amount'))
        regular_price = await safe_text(await page.query_selector('span[data-qa-qualifier="price-amount-old"] span.money-amount__main'))
        discount_rate = await safe_text(await page.query_selector('span[data-qa-qualifier="price-discount-percentage"]'))

        # ✅ 색상 텍스트
        color = ""
        color_el = await page.query_selector('p[data-qa-qualifier="product-detail-info-color"]')
        if color_el:
            full_text = await color_el.inner_text()
            btn_el = await color_el.query_selector('button')
            btn_text = await btn_el.inner_text() if btn_el else ""
            if btn_text and btn_text in full_text:
                full_text = full_text.replace(btn_text, "")
            color = full_text.strip().strip('|').strip()

        color_chip = ""
        try:
            selected_chip = await page.query_selector(
                'li[aria-current="true"] div.product-detail-color-selector__color-area'
            )
            if selected_chip:
                color_chip = await selected_chip.evaluate("el => getComputedStyle(el).backgroundColor")
        except:
            pass

        # ✅ 소재 정보
        material = ""
        try:
            detail_btn = await page.query_selector('button[data-qa-action="show-extra-detail"]')
            if detail_btn:
                await detail_btn.click()
                await page.wait_for_timeout(1000)

            materials_section = await page.query_selector('div[data-observer-key="materials"]')
            if materials_section:
                material_set = set()
                material_combined = []

                subtitles = await materials_section.query_selector_all('div.structured-component-text-block-subtitle span')
                paragraphs = await materials_section.query_selector_all('div.structured-component-text-block-paragraph span')

                for subtitle, paragraph in zip(subtitles, paragraphs):
                    raw_key = (await subtitle.inner_text()).strip()
                    for word in ["혼용률", "소재", "주요소재"]:
                        raw_key = raw_key.replace(word, "")
                    key = raw_key.strip(":").strip()
                    value = (await paragraph.inner_text()).strip()
                    if key and value:
                        pair = f"{key}: {value}"
                        if pair not in material_set:
                            material_set.add(pair)
                            material_combined.append(pair)

                material = " / ".join(material_combined)
        except:
            pass

        # ✅ 상세 설명
        details = ""
        try:
            p_el = await page.query_selector("div.expandable-text__inner-content p")
            if p_el:
                details = (await p_el.inner_text()).strip()
        except:
            pass

        # ✅ 대표 이미지
        front_image_url = ""
        try:
            img_el = await page.query_selector('div.product-detail-view__main-image-wrapper img.media-image__image')
            if img_el:
                front_image_url = await img_el.get_attribute("src")
        except:
            pass

        await page.close()
        return {
            "product_name": name,
            "current_price": price,
            "regular_price": regular_price,
            "discount_rate": discount_rate,
            "color": color,
            "color_chip": color_chip,
            "material": material,
            "details": details,
            "color_classification_url": thumbnail_url,
            "front_images_url": front_image_url,
            "product_detail_url": url
        }

    except Exception as e:
        print(f"⚠️ 상세페이지 크롤링 실패: {url} / {e}")
        return {
            "product_name": "", "current_price": "", "regular_price": "",
            "discount_rate": "", "color": "", "color_chip": "", "material": "",
            "details": "", "color_classification_url": thumbnail_url,
            "front_images_url": "", "product_detail_url": url
        }

# ✅ 목록에서 썸네일과 링크 수집
async def collect_product_links(page):
    await page.wait_for_timeout(1500)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)

    seen = set()
    products = []
    items = await page.query_selector_all('a[href*="/kr/ko/"] img[data-qa-qualifier="media-image"]')

    for img in items:
        parent_link = await img.evaluate_handle('img => img.closest("a")')
        href = await parent_link.get_attribute("href")
        full_link = f"https://www.zara.com{href}" if href and href.startswith("/kr") else href
        src = await img.get_attribute("src")
        if full_link not in seen:
            seen.add(full_link)
            products.append({"url": full_link, "thumbnail": src})

    return products

# ✅ CSV 저장
def save_to_csv(data):
    date_str = datetime.now().strftime("%y%m%d")
    filename = f"zara_woman_{date_str}.csv"
    with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "category", "product_name", "current_price", "regular_price", "discount_rate",
            "color", "color_chip", "material", "details",
            "color_classification_url", "front_images_url", "product_detail_url"
        ])
        for item in data:
            writer.writerow([
                f'category: {item["category"]}',
                f'product_name: {item["product_name"]}',
                f'current_price: {item["current_price"]}',
                f'regular_price: {item["regular_price"]}',
                f'discount_rate: {item["discount_rate"]}',
                f'color: {item["color"]}',
                f'color_chip: {item["color_chip"]}',
                f'material: {item["material"]}',
                f'details: {item["details"]}',
                f'color_classification_url: {item["color_classification_url"]}',
                f'front_images_url: {item["front_images_url"]}',
                f'product_detail_url: {item["product_detail_url"]}',
            ])
    return filename

# ✅ 메인 실행
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        results = []

        for category_item in zara_woman_category:
            category = category_item["category"]
            url = category_item["url"]
            page = await context.new_page()
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

            print(f"\n📂 카테고리: {category}")
            product_links = await collect_product_links(page)
            print(f"🔗 수집된 상품 수: {len(product_links)}")

            for i, item in enumerate(product_links, start=1):
                print(f"\n📥 {i}번째 상품 크롤링 중...")
                detail = await get_product_detail(context, item["url"], item["thumbnail"])
                detail["category"] = category

                print(f"📂 category: {detail['category']}")
                print(f"🧾 product_name: {detail['product_name']}")
                print(f"💰 current_price: {detail['current_price']}")
                print(f"🏷 regular_price: {detail['regular_price']}")
                print(f"📉 discount_rate: {detail['discount_rate']}")
                print(f"🎨 color: {detail['color']}")
                print(f"🎨 color_chip: {detail['color_chip']}")
                print(f"🧵 material: {detail['material']}")
                print(f"📐 details: {detail['details']}")
                print(f"🖼 front_images_url: {detail['front_images_url']}")
                print(f"🎯 color_classification_url: {detail['color_classification_url']}")
                print(f"🔗 product_detail_url: {detail['product_detail_url']}")

                results.append(detail)
            await page.close()

        await browser.close()
        filename = save_to_csv(results)
        print(f"\n✅ CSV 저장 완료: {filename}")

if __name__ == "__main__":
    asyncio.run(main())