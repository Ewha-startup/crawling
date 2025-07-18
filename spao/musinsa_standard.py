import nest_asyncio
import asyncio
import csv
import re
from playwright.async_api import async_playwright
from datetime import datetime

from libs.spao.musinsa_woman_category import musinsa_woman_category

nest_asyncio.apply()

async def scroll_and_collect(page, url):
    await page.goto(url)
    seen_links = set()
    products = []
    same_count = 0

    while same_count < 5:
        product_cards = await page.query_selector_all("div.sc-widb61-1.dPWHpp")
        newly_added = 0

        for card in product_cards:
            link_el = await card.query_selector("a")
            link_suffix = await link_el.get_attribute("href") if link_el else None
            link = f"https://www.musinsa.com{link_suffix}" if link_suffix and not link_suffix.startswith("http") else link_suffix
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            newly_added += 1

            name_el = await card.query_selector("a span[data-mds='Typography']")
            name = await name_el.inner_text() if name_el else None
            if not name:
                continue

            color_match = re.search(r"\[(.*?)\]", name)
            color = color_match.group(1) if color_match else ""
            cleaned_name = re.sub(r"\[.*?\]", "", name).strip()

            gender_el = await card.query_selector("div.sc-gnqCJb span")
            gender = await gender_el.inner_text() if gender_el else ""

            discount_el = await card.query_selector("span:has-text('%')")
            discount = await discount_el.inner_text() if discount_el else ""

            price_el = await card.query_selector("span.text-title_18px_semi.text-black")
            price = await price_el.inner_text() if price_el else ""
            price = re.sub(r"[^\d,]", "", price)

            rating_el = await card.query_selector("span.text-yellow")
            rating = await rating_el.inner_text() if rating_el else ""

            img_el = await card.query_selector("img")
            img_src = await img_el.get_attribute("src") if img_el else ""
            if img_src and img_src.startswith("//"):
                img_src = "https:" + img_src

            products.append({
                "product_name": cleaned_name,
                "color": color,
                "gender": gender,
                "discount_rate": discount,
                "current_price": price,
                "rating": rating,
                "product_detail_url": link,
                "front_images_url": img_src,
            })

        print(f"📦 누적 수집된 상품 수: {len(products)}")

        if newly_added == 0:
            same_count += 1
        else:
            same_count = 0

        await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        await page.wait_for_timeout(1500)

    return products

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        results = []

        for url in musinsa_woman_category:
            product_list = await scroll_and_collect(page, url)

            for i, product in enumerate(product_list, start=1):
                link = product["product_detail_url"]
                category = ""
                regular_price = ""
                reviews = ""
                details = ""

                try:
                    await page.goto(link)
                    await page.wait_for_load_state("networkidle")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(3000)

                    price_el = await page.query_selector("span.text-title_18px_semi.text-black")
                    price = await price_el.inner_text() if price_el else ""
                    price = re.sub(r"[^\d,]", "", price)
                    product["current_price"] = price

                    category_els = await page.query_selector_all("a[data-section-name='cate_navi'][data-button-name='상품카테고리']")
                    categories = [await el.text_content() for el in category_els if el]
                    category = categories[-1] if categories else ""

                    regular_el = await page.query_selector("span.line-through")
                    if regular_el:
                        regular_price = await regular_el.inner_text()
                        regular_price = regular_price.replace("원", "").strip()

                    review_el = await page.query_selector("span:has-text('후기')")
                    if review_el:
                        review_text = await review_el.inner_text()
                        match = re.search(r'\d+', review_text)
                        if match:
                            reviews = match.group(0)

                    fit_keys = ["핏", "촉감", "신축성", "비침", "두께", "계절"]
                    fit_elements = await page.query_selector_all('table.sc-36xiah-6.jizuRz > tbody > tr:not(:last-child) > td.sc-36xiah-7.eviTcu')
                    fit_info = [await el.inner_text() for el in fit_elements]
                    while len(fit_info) < 5:
                        fit_info.append("")

                    season_els = await page.query_selector_all('table.sc-36xiah-6.jizuRz > tbody > tr:last-child > td.sc-36xiah-7.eviTcu')
                    seasons = [await el.inner_text() for el in season_els]
                    fit_info.append(", ".join(seasons) if seasons else "")

                    details = ", ".join([f"{k}: {v}" for k, v in zip(fit_keys, fit_info)])

                    print(f"\n🛍️ {i}. category: {category}")
                    print(f"   ├ product_name: {product['product_name']}")
                    print(f"   ├ color: {product['color']}")
                    print(f"   ├ current_price: {product['current_price']}")
                    print(f"   ├ regular_price: {regular_price}")
                    print(f"   ├ discount_rate: {product['discount_rate']}")
                    print(f"   ├ gender: {product['gender']}")
                    print(f"   ├ rating: {product['rating']}")
                    print(f"   ├ reviews: {reviews}")
                    print(f"   ├ details: {details}")
                    print(f"   ├ product_detail_url: {product['product_detail_url']}")
                    print(f"   └ front_images_url: {product['front_images_url']}")

                except Exception as e:
                    print(f"⚠️ 상세 페이지 진입 실패: {link} / 오류: {e}")

                results.append({
                    "category": category,
                    **product,
                    "regular_price": regular_price,
                    "reviews": reviews,
                    "details": details
                })

        fieldnames = [
            "category", "product_name", "color", "current_price", "regular_price",
            "discount_rate", "gender", "rating", "reviews", "details",
            "product_detail_url", "front_images_url"
        ]
        date_str = datetime.now().strftime("%y%m%d")
        filename = f"musinsa_woman_{date_str}.csv"

        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in results:
                writer.writerow(row)

        await browser.close()

asyncio.run(main())