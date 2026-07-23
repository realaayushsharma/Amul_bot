import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PINCODE = os.getenv("PINCODE")

CHECK_INTERVAL = 300  # seconds

PRODUCTS = {
    "High Protein Buttermilk":
        "https://shop.amul.com/en/product/amul-high-protein-buttermilk-200-ml-or-pack-of-30",

    "High Protein Rose Lassi":
        "https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30",
}


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")


def send_telegram(message):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
            },
            timeout=20,
        )

        log(f"Telegram: {response.status_code}")
        log(response.text)

    except Exception as e:
        log(f"Telegram Error: {e}")


def set_pincode(page):
    try:
        # Wait until the textbox is visible
        page.get_by_role(
            "textbox",
            name="Enter Your Pincode"
        ).wait_for(timeout=10000)

        # Click and fill
        page.get_by_role(
            "textbox",
            name="Enter Your Pincode"
        ).click()

        page.get_by_role(
            "textbox",
            name="Enter Your Pincode"
        ).fill(PINCODE)

        # Wait for dropdown
        page.get_by_text(PINCODE, exact=True).wait_for(timeout=5000)

        # Select pincode
        page.get_by_text(PINCODE, exact=True).click()

        page.wait_for_timeout(3000)

        log(f"✅ Pincode set to {PINCODE}")

    except Exception:
        log("ℹ️ Pincode popup not found. Assuming it's already selected.")


def check_stock(page, url):
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(3000)

    add_to_cart = page.locator("a.add-to-cart").first

    if add_to_cart.count() == 0:
        return False

    disabled = add_to_cart.get_attribute("disabled")

    print(f"{url}")
    print("Text:", add_to_cart.inner_text())
    print("Disabled:", disabled)

    return disabled == "0"


def safe_check(page, url):

    for _ in range(3):
        try:
            return check_stock(page, url)
        except Exception as e:
            log(f"Retry because: {e}")
            time.sleep(5)

    return False


with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="amul_profile",
        headless=True,
    )

    page = browser.new_page()

    page.goto("https://shop.amul.com")

    set_pincode(page)

    previous = {}

    log("Monitoring Started...")

    while True:

        for name, url in PRODUCTS.items():

            available = safe_check(page, url)

            log(f"{name}: {available}")

            previous_state = previous.get(url)

            # Notify only when Out of Stock -> In Stock
            if available and (previous_state is None or previous_state is False):

                send_telegram(
                    f"""🚨 AMUL STOCK ALERT

{name} is now AVAILABLE!

🛒 Product: {name}

✅ Status: IN STOCK

{url}

⏰ {datetime.now():%d-%m-%Y %H:%M:%S}
"""
                )

                log(f"Notification sent for {name}")

            previous[url] = available

        time.sleep(CHECK_INTERVAL)