import time
import requests
from playwright.sync_api import sync_playwright

PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30"

BOT_TOKEN = "8847440514:AAFubM_CGuInXwMGBGJeEKRMZ-fmC6mzxmc"
CHAT_ID = "1303604314"

CHECK_INTERVAL = 300  # 5 minutes


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=20,
    )


def check_stock(page):
    page.goto(PRODUCT_URL, wait_until="networkidle")

    buttons = page.locator("button").all_inner_texts()

    print(buttons)

    return False


with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    notified = False

    print("Monitoring started...")

    while True:

        try:
            available = check_stock(page)

            print(f"Available: {available}")

            if available and not notified:

                send_telegram(
                    f"""🚨 AMUL ALERT

High Protein Buttermilk is now IN STOCK!

{PRODUCT_URL}"""
                )

                print("Telegram notification sent!")

                notified = True

            elif not available:

                notified = False

        except Exception as e:
            print("Error:", e)

        time.sleep(CHECK_INTERVAL)