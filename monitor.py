import asyncio
from datetime import datetime
import os
import csv
from playwright.async_api import async_playwright

# 모니터링할 LG 브라질 에어컨 모델 및 주소
PRODUCTS = {
    "S3-Q09JA31E": "https://www.lg.com/br/ar-condicionado-residencial/dual-inverter-voice-s3-q09ja31e/",
    "S3-Q12JA31E": "https://www.lg.com/br/ar-condicionado-residencial/dual-inverter-voice-s3-q12ja31e/",
}

CSV_FILE = "price_history.csv"

async def get_prices():
    prices = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for model_name, url in PRODUCTS.items():
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(5000)

                # 브라질 가격 포맷(R$ 1.234,56 등) 찾기
                price_locator = page.locator("text=/R\\$\\s?[0-9.,]+/")
                if await price_locator.count() > 0:
                    raw_price = await price_locator.first.inner_text()
                    # R$ 기호 빼고 숫자만 깔끔하게 저장 (예: 1.999,00)
                    price = raw_price.replace("R$", "").replace("\xa0", "").strip()
                else:
                    price = "N/A"
                prices[model_name] = price
            except Exception as e:
                prices[model_name] = f"Error ({str(e)})"

        await browser.close()
    return prices

def save_to_csv(prices):
    today = datetime.now().strftime("%Y-%m-%d")
    file_exists = os.path.isfile(CSV_FILE)
    
    # 파일이 없으면 제목 첫 줄(헤더)과 함께 새로 만들고, 있으면 맨 아래에 한 줄 누적
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "S3-Q09JA31E (9k)", "S3-Q12JA31E (12k)"])
        writer.writerow([today, prices.get("S3-Q09JA31E", "N/A"), prices.get("S3-Q12JA31E", "N/A")])

if __name__ == "__main__":
    print("Starting price check...")
    current_prices = asyncio.run(get_prices())
    save_to_csv(current_prices)
    print("Saved to CSV successfully:", current_prices)
