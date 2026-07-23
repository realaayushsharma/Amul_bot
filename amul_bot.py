import os
import threading
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


def send_telegram(message, chat_id=None):
    try:
        if chat_id is None:
            chat_id = CHAT_ID

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
            },
            timeout=20,
        )

        log(f"Telegram: {response.status_code}")

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

LAST_UPDATE_ID = None
page_lock = threading.Lock()
def telegram_listener(page):
    global LAST_UPDATE_ID

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

            params = {"timeout": 2}

            if LAST_UPDATE_ID is not None:
                params["offset"] = LAST_UPDATE_ID + 1

            response = requests.get(url, params=params, timeout=10).json()

            if response["ok"]:

                for update in response["result"]:

                    LAST_UPDATE_ID = update["update_id"]

                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")

                    if text == "/start":

                        status = (
                            "👋 Welcome to the Amul Stock Monitor Bot!\n\n"
                            "📊 Current Stock Status\n\n"
                        )

                        for name, product_url in PRODUCTS.items():
                            with page_lock:
                                available = safe_check(page, product_url)

                            if available:
                                status += f"✅ {name}: In Stock\n"
                            else:
                                status += f"❌ {name}: Out of Stock\n"

                        status += (
                            "\n🔔 I'll automatically notify you whenever "
                            "an out-of-stock product becomes available."
                        )

                        send_telegram(status, chat_id)

        except Exception as e:
            log(f"Telegram Listener Error: {e}")

        time.sleep(3)

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

    
    
    threading.Thread(
    target=telegram_listener,
    args=(page,),
    daemon=True
).start()
    
    previous = {}

    log("Monitoring Started...")

    while True:

        

        for name, url in PRODUCTS.items():
            with page_lock:
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