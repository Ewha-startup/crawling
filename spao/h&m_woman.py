import nest_asyncio
import asyncio
import csv
import re
from datetime import datetime
from playwright.async_api import async_playwright

from libs.spao.hm_woman_category import hm_woman_category


nest_asyncio.apply()

async def get_product_detail(context, url):
    try:
        detail_page = await context.new_page()
        await detail_page.goto(url, timeout=60000)
        await detail_page.wait_for_load_state("domcontentloaded")
        await detail_page.wait_for_timeout(1000)

        title_el = await detail_page.query_selector("h1")
        title = await title_el.inner_text() if title_el else "❌ 상품명 없음"

        price_el = await detail_page.query_selector("span[class*='e31b97']")
        price = await price_el.inner_text() if price_el else ""

        color = ""
        try:
            color_section = await detail_page.query_selector('section[aria-label="컬러"]')
            if color_section:
                color_p = await color_section.query_selector("p")
                if color_p:
                    color = await color_p.inner_text()
        except:
            pass

        color_img_url = ""
        try:
            color_image_a = await detail_page.query_selector('a[role="radio"][aria-checked="true"] img')
            if color_image_a:
                raw_url = await color_image_a.get_attribute("src")
                if raw_url:
                    color_img_url = "https:" + raw_url if raw_url.startswith("//") else raw_url
        except:
            pass

        discount_rate = ""
        regular_price = ""
        try:
            discount_el = await detail_page.query_selector("span[class*='f37698']")
            discount_rate = await discount_el.inner_text() if discount_el else ""

            regular_el = await detail_page.query_selector("span[class*='b130b3']")
            regular_price = await regular_el.inner_text() if regular_el else ""
        except:
            pass

        reviews = ""
        rating = ""
        try:
            review_btn = await detail_page.query_selector('button[aria-label*="리뷰"]')
            if review_btn:
                review_text = await review_btn.inner_text()
                match = re.search(r"\[(\d+)\]", review_text)
                if match:
                    reviews = match.group(1)
        except:
            pass

        try:
            rating_wrapper = await detail_page.query_selector('span[data-testid="stars"]')
            if rating_wrapper:
                sibling = await rating_wrapper.evaluate_handle('el => el.nextElementSibling')
                if sibling:
                    rating = await sibling.inner_text()
        except:
            pass

        details = {}
        dl_section = await detail_page.query_selector("dl.d418f1")
        if dl_section:
            rows = await dl_section.query_selector_all("div.ecc0f3")
            for row in rows:
                key_el = await row.query_selector("dt")
                val_el = await row.query_selector("dd")
                if key_el and val_el:
                    key = (await key_el.inner_text()).strip().replace(":", "")
                    val = (await val_el.inner_text()).strip()
                    details[key] = val

        material_combined = ""
        material_button = await detail_page.query_selector("button:has-text('소재')")
        if material_button:
            await material_button.click()
            await detail_page.wait_for_timeout(1000)

            section = await detail_page.query_selector("#section-materialsAndSuppliersAccordion")
            if section:
                h3_blocks = await section.query_selector_all("h3")
                for h3 in h3_blocks:
                    h3_title = (await h3.inner_text()).strip()
                    if h3_title in ["구성", "소재"]:
                        parent = await h3.evaluate_handle("el => el.parentElement.parentElement")
                        ul = await parent.query_selector("ul.f94b22")
                        if ul:
                            li_items = await ul.query_selector_all("li")
                            for li in li_items:
                                spans = await li.query_selector_all("span")
                                if len(spans) >= 2:
                                    key = (await spans[0].inner_text()).strip().replace(":", "")
                                    val = (await spans[1].inner_text()).strip()
                                    material_combined += f"{key}: {val} / "

                        dl = await parent.query_selector("dl")
                        if dl:
                            divs = await dl.query_selector_all("div.ecc0f3")
                            for div in divs:
                                dt = await div.query_selector("dt")
                                dd = await div.query_selector("dd")
                                if dt and dd:
                                    key = (await dt.inner_text()).strip().replace(":", "")
                                    val = (await dd.inner_text()).strip()
                                    if key == "소재":
                                        material_combined += f"{val} / "
                                    else:
                                        material_combined += f"{key}: {val} / "

        await detail_page.close()
        return title.strip(), price.strip(), color.strip(), material_combined.strip(" / "), details, color_img_url, discount_rate, regular_price, url, reviews, rating
    except Exception as e:
        print(f"⚠️ 에러 발생: {url} / {e}")
        return "", "", "", "", {}, "", "", "", url, "", ""

def extract_color_chip(style_str):
    match = re.search(r"rgb\([^)]+\)", style_str)
    return match.group(0) if match else ""

async def collect_product_links_and_thumbnails(page):
    await page.wait_for_timeout(1500)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)

    url_set = set()
    products = []
    anchors = await page.query_selector_all("a[href*='/ko_kr/productpage.']")
    for anchor in anchors:
        href = await anchor.get_attribute("href")
        url = href if href.startswith("http") else "https://www2.hm.com" + href
        if url in url_set:
            continue
        url_set.add(url)

        img_el = await anchor.query_selector("img")
        img_src = await img_el.get_attribute("src") if img_el else None
        if img_src and img_src.startswith("//"):
            img_src = "https:" + img_src

        color_chip = ""
        try:
            rgb_span = await anchor.query_selector("span[style*='background-color']")
            if rgb_span:
                style = await rgb_span.get_attribute("style")
                color_chip = extract_color_chip(style)
        except:
            pass

        if img_src:
            products.append({"url": url, "image": img_src, "color_chip": color_chip})

    return products

def save_to_csv(data):
    date_str = datetime.now().strftime("%y%m%d")
    filename = f"hm_woman_{date_str}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow([
            "category",
            "product_name",
            "current_price",
            "regular_price",
            "discount_rate",
            "color",
            "color_chip",
            "material",
            "details",
            "reviews",
            "rating",
            "front_images_url",
            "color_classification_url",
            "product_detail_url"
        ])

        for item in data:
            detail_str = "; ".join([f"{k}: {v}" for k, v in item["details"].items()])
            writer.writerow([
                item["category"],
                item["product_name"],
                item["current_price"],
                item["regular_price"],
                item["discount_rate"],
                item["color"],
                item["color_chip"],
                item["material"],
                detail_str,
                item["reviews"],
                item["rating"],
                item["front_images_url"],
                item["color_classification_url"],
                item["product_detail_url"]
            ])
    return filename

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        final_results = []

        for category_info in hm_woman_category:
            category = category_info["category"]
            url = category_info["url"]

            page = await context.new_page()
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

            print(f"📂 카테고리: {category}")
            products = await collect_product_links_and_thumbnails(page)
            print(f"🔗 수집된 상품 수: {len(products)}")

            for i, item in enumerate(products, 1):
                print(f"\n📥 {i}번째 상품 크롤링 중...")
                title, price, color, material, details, color_img_url, discount_rate, regular_price, detail_url, reviews, rating = await get_product_detail(context, item["url"])
                result_item = {
                    "category": category,
                    "product_name": title,
                    "current_price": price,
                    "regular_price": regular_price,
                    "discount_rate": discount_rate,
                    "color": color,
                    "color_chip": item["color_chip"],
                    "material": material,
                    "details": details,
                    "reviews": reviews,
                    "rating": rating,
                    "front_images_url": item["image"],
                    "color_classification_url": color_img_url,
                    "product_detail_url": detail_url
                }

                print(f"📂 category: {result_item['category']}")
                print(f"🧾 product_name: {result_item['product_name']}")
                print(f"💰 current_price: {result_item['current_price']}")
                print(f"🏷 regular_price: {result_item['regular_price']}")
                print(f"📉 discount_rate: {result_item['discount_rate']}")
                print(f"🎨 color: {result_item['color']}")
                print(f"🎨 color_chip: {result_item['color_chip']}")
                print(f"🧵 material: {result_item['material']}")
                print(f"📐 details: {'; '.join([f'{k}: {v}' for k, v in result_item['details'].items()])}")
                print(f"⭐ reviews: {result_item['reviews']}")
                print(f"✨ rating: {result_item['rating']}")
                print(f"🖼 front_images_url: {result_item['front_images_url']}")
                print(f"🎯 color_classification_url: {result_item['color_classification_url']}")
                print(f"🔗 product_detail_url: {result_item['product_detail_url']}")

                final_results.append(result_item)

        await browser.close()
        filename = save_to_csv(final_results)
        print(f"\n✅ CSV 저장 완료: {filename}")
if __name__ == "__main__":
    asyncio.run(main())