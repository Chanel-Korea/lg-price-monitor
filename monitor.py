import asyncio
from datetime import datetime
import os
import csv
import re
from playwright.async_api import async_playwright

# LG 브라질 공식 홈페이지 정확한 상세 페이지 주소
PRODUCTS = {
    "S3-Q09JA31E (9k)": "https://www.lg.com/br/ar-condicionado-residencial/s3-q09ja31e/",
    "S3-Q12JA31E (12k)": "https://www.lg.com/br/ar-condicionado-residencial/s3-q12ja31e/",
}

CSV_FILE = "price_history.csv"

async def get_prices():
    prices = {}
    async with async_playwright() as p:
        # 브라질 현지 브라우저 환경 모방
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for model_name, url in PRODUCTS.items():
            print(f"조사 시작: {model_name} -> {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # 비동기 가격 데이터 및 쿠키 팝업 로딩 대기 (7초)
                await page.wait_for_timeout(7000)

                # 1. LG 공식몰의 가격 클래스 및 텍스트 영역 탐색
                extracted_price = None

                # LG 전용 가격 셀렉터 우선 탐색
                selectors = [
                    ".c-price__purchase", 
                    ".c-price__total", 
                    ".price-area", 
                    "[data-product-price]",
                    ".cmp-price"
                ]
                
                for sel in selectors:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        text = (await el.inner_text()).strip()
                        if "R$" in text:
                            extracted_price = text
                            break

                # 2. 셀렉터로 못 찾은 경우 전체 텍스트에서 R$ 정밀 추출
                if not extracted_price:
                    body_text = await page.inner_text("body")
                    matches = re.findall(r"R\$\s?[\d\.]+(?:,\d{2})?", body_text)
                    if matches:
                        # 페이지 상단에 노출되는 대표 가격 추출
                        extracted_price = matches[0]

                if extracted_price:
                    # 'R$', 공백, 줄바꿈 제거 후 깔끔한 숫자 포맷(예: 2.461,94)으로 정제
                    clean_price = extracted_price.replace("R$", "").replace("\xa0", " ").strip()
                    clean_price = clean_price.split("\n")[0].strip()
                    prices[model_name] = clean_price
                else:
                    prices[model_name] = "N/A"

            except Exception as e:
                prices[model_name] = f"Error: {str(e)[:30]}"

        await browser.close()
    return prices

def save_to_csv(prices):
    today = datetime.now().strftime("%Y-%m-%d")
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "S3-Q09JA31E (9k)", "S3-Q12JA31E (12k)"])
        writer.writerow([today, prices.get("S3-Q09JA31E (9k)", "N/A"), prices.get("S3-Q12JA31E (12k)", "N/A")])

if __name__ == "__main__":
    current_prices = asyncio.run(get_prices())
    print("수집 완료:", current_prices)
    save_to_csv(current_prices)
