import asyncio
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from playwright.async_api import async_playwright

# 모니터링할 LG 브라질 에어컨 모델 및 주소
PRODUCTS = {
    "S3-Q09JA31E (9,000 BTU)": "https://www.lg.com/br/ar-condicionado-residencial/dual-inverter-voice-s3-q09ja31e/",
    "S3-Q12JA31E (12,000 BTU)": "https://www.lg.com/br/ar-condicionado-residencial/dual-inverter-voice-s3-q12ja31e/",
}

async def check_prices():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="pt-BR")
        page = await context.new_page()

        for model_name, url in PRODUCTS.items():
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)  # 가격 로딩 대기

                # 화면에서 R$ 가격 텍스트 찾기
                price_locator = page.locator("text=/R\\$\\s?[0-9.,]+/").first
                if await price_locator.count() > 0:
                    price = (await price_locator.inner_text()).strip()
                else:
                    price = "품절 또는 가격 미노출 (사이트 확인 필요)"

                results.append(f"- {model_name}: {price}\n  (링크: {url})")
            except Exception as e:
                results.append(f"- {model_name}: 조회 실패 ({str(e)})")

        await browser.close()
    return "\n\n".join(results)

def send_email(report_body):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    receiver = os.environ.get("EMAIL_RECEIVER", sender)

    if not sender or not password:
        print("이메일 설정이 없어 화면에만 출력합니다:\n", report_body)
        return

    today = datetime.now().strftime("%Y-%m-%d")
    msg = MIMEText(f"[LG 브라질 에어컨 주간 판가 리포트 - {today}]\n\n{report_body}")
    msg["Subject"] = f"[자동 리포트] LG 브라질 에어컨 판가 현황 ({today})"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

if __name__ == "__main__":
    report = asyncio.run(check_prices())
    print(report)
    send_email(report)
