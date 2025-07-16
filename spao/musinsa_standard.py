import nest_asyncio
import asyncio
from playwright.async_api import async_playwright

nest_asyncio.apply()

LIST_URL = "https://www.musinsa.com/brand/musinsastandard/products?gf=A"

async def collect_product_links(page, max_scrolls=1):
    seen_names = set()
    products = []

    for _ in range(max_scrolls):
        product_cards = await page.query_selector_all('div.sc-widb61-1.dPWHpp')
        print(f"📦 현재 보이는 상품 수: {len(product_cards)}")

        for card in product_cards:
            name_el = await card.query_selector("a span[data-mds='Typography']")
            name = await name_el.inner_text() if name_el else None
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            link_el = await card.query_selector("a")
            link_suffix = await link_el.get_attribute("href") if link_el else None
            link = f"https://www.musinsa.com{link_suffix}" if link_suffix and not link_suffix.startswith("http") else link_suffix

            # 성별
            gender_el = await card.query_selector("div.sc-gnqCJb span")
            gender = await gender_el.inner_text() if gender_el else "?"

            # 할인            discount_el = await card.query_selector("span:has-text('%')")
            discount_el = await card.query_selector("span:has-text('%')")
            discount = await discount_el.inner_text() if discount_el else "0%"

            # 가격
            price_el = await card.query_selector("div.sc-hKDTPf span[data-mds='Typography']:nth-child(2)")
            price = await price_el.inner_text() if price_el else "?"

            # 평점
            rating_el = await card.query_selector("span.text-yellow")
            rating = await rating_el.inner_text() if rating_el else "0"

            # \cc2c 수
            likes_el = await card.query_selector("span.text-etc_11px_reg.text-red")
            likes = await likes_el.inner_text() if likes_el else "-"

            # 이미지
            img_el = await card.query_selector("img")
            img_src = await img_el.get_attribute("src") if img_el else None
            if img_src and img_src.startswith("//"):
                img_src = "https:" + img_src

            products.append({
                "name": name,
                "gender": gender,
                "discount": discount,
                "price": price,
                "rating": rating,
                "likes": likes,
                "link": link,
                "image": img_src,
            })

        # 스크롤
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)

    return products


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # 1. 목록 진입
        await page.goto(LIST_URL)
        await page.wait_for_load_state("networkidle")

        # 2. 전체 상품 링크 수집
        product_list = await collect_product_links(page, max_scrolls=2)
        print(f"📟 총 수집된 상품 수: {len(product_list)}\n")

        results = []

        # 3. 각 상품 상세 페이지 들어가서 카테고리 + 핀/계절감 수집
        for i, product in enumerate(product_list, start=1):
            link = product["link"]
            category = "N/A"
            fit_dict = {}

            try:
                await page.goto(link)
                await page.wait_for_load_state("networkidle")

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)

                category_els = await page.query_selector_all("a[data-section-name='cate_navi'][data-button-name='상품카테고리']")
                categories = [await el.text_content() for el in category_els if el]
                category = categories[-1] if categories else "N/A"

                # 핏/계절감 정보 추출
                fit_keys = ["핏", "촉감", "신축성", "비침", "두께", "계절"]
                fit_dict = {}

                fit_elements = await page.query_selector_all(
                    'table.sc-36xiah-6.jizuRz > tbody > tr:not(:last-child) > td.sc-36xiah-7.eviTcu')
                fit_info = [await el.inner_text() for el in fit_elements]

                while len(fit_info) < 5:
                    fit_info.append("없음")

                for j, key in enumerate(fit_keys[:-1]):
                    fit_dict[key] = fit_info[j]

                season_els = await page.query_selector_all(
                    'table.sc-36xiah-6.jizuRz > tbody > tr:last-child > td.sc-36xiah-7.eviTcu')
                seasons = [await el.inner_text() for el in season_els]
                fit_dict["계절"] = ", ".join(seasons) if seasons else "없음"

                print(f"\n🏭️ {i}. {product['name']}")
                print(f"   ├ 할인: {product['discount']}")
                print(f"   ├ 가격: {product['price']}")
                print(f"   ├ 찜 수: {product['likes']}")
                print(f"   ├ 평점: {product['rating']}")
                print(f"   ├ 성별: {product['gender']}")
                print(f"   ├ 카테고리: {category}")
                print(f"   └ 이미지: {product['image']}")

                for key in fit_keys:
                    print(f"      - {key}: {fit_dict[key]}")

            except Exception as e:
                print(f"⚠️ 상세 페이지 진입 실패: {link} / 오류: {e}")

            results.append({ **product, "category": category, **fit_dict })

            await page.goto(LIST_URL)
            await page.wait_for_load_state("networkidle")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        await browser.close()

asyncio.run(main())