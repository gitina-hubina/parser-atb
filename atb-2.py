#!/usr/bin/env python3

import cloudscraper
from bs4 import BeautifulSoup
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": "keep-alive",
}

cookies = {
    "birthday": "true"
}

scraper = cloudscraper.create_scraper(
    browser={
        'custom': headers["User-Agent"]
    }
)

def get_last_page(pagination):
    page_numbers = []
    for li in pagination.select("li.product-pagination__item"):
        a = li.select_one("a.product-pagination__link")
        if a and a.text.isdigit():
            page_numbers.append(int(a.text))
    return max(page_numbers) if page_numbers else 1

def parse_page(url):
    response = scraper.get(url, headers=headers, cookies=cookies)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("article.catalog-item.js-product-container")

    promos = []
    for item in items:
        counter = item.select_one(".b-addToCart")
        product_id = counter["data-itemid"] if counter and counter.has_attr("data-itemid") else None
        category = counter["data-category"] if counter and counter.has_attr("data-category") else None

        title_tag = item.select_one(".catalog-item__title a")
        name = title_tag.get_text(strip=True) if title_tag else None

        image_tag = item.select_one(".catalog-item__photo img")
        image_url = image_tag["src"] if image_tag and image_tag.has_attr("src") else None

        price_block = item.select_one(".catalog-item__product-price")
        price_new_tag = price_block.select_one("data.product-price__top") if price_block else None
        price_old_tag = price_block.select_one("data.product-price__bottom") if price_block else None

        atb_card_block = item.select_one(".atbcard-sale")
        price_atb_tag = atb_card_block.select_one("data.atbcard-sale__price-top") if atb_card_block else None

        if not price_new_tag or not price_new_tag.has_attr("value"):
            raise ValueError(f"Не найдена новая цена для товара: {name}")

        price_new = price_new_tag["value"]
        price_old = price_old_tag["value"] if price_old_tag and price_old_tag.has_attr("value") else "--.--"
        price_atb = price_atb_tag["value"] if price_atb_tag and price_atb_tag.has_attr("value") else "--.--"

        promos.append({
            "id": product_id,
            "name": name,
            "category": category,
            "imageUrl": image_url,
            "oldPrice": price_old,
            "newPrice": price_new,
            "cardPrice": price_atb,
            "quantity": 0
        })

    return promos, soup

def save_to_file(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Сохранено в файл: {filename}")

def process_promo(name, base_url):
    print(f"\n➤ Обрабатываем акцию: {name}")
    all_promos = []

    response = scraper.get(base_url, headers=headers, cookies=cookies)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    pagination = soup.select_one(".product-pagination__list")

    if pagination:
        last_page = get_last_page(pagination)
        print(f"Пагинация: всего страниц {last_page}")

        all_promos.extend(parse_page(base_url)[0])

        for page_num in range(2, last_page + 1):
            print(f"➤ Обрабатываем страницу {page_num}")
            page_url = f"{base_url}&page={page_num}"
            all_promos.extend(parse_page(page_url)[0])
    else:
        print("Пагинации нет — всего 1 страница")
        all_promos.extend(parse_page(base_url)[0])

    save_to_file(all_promos, f"{name}.json")

    return all_promos

def main():
    with open("atb_actions.json", "r", encoding="utf-8") as f:
        promo_urls = json.load(f)

    all_data = {}

    for name, url in promo_urls.items():
        promos = process_promo(name, url)
        all_data[name] = promos

if __name__ == "__main__":
    main()
