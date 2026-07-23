from playwright.sync_api import sync_playwright

PINCODE = "457001"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()

    page.goto("https://shop.amul.com", wait_until="networkidle")

    # Click the textbox
    page.get_by_role("textbox", name="Enter Your Pincode").click()

    # Type the pincode
    page.get_by_role("textbox", name="Enter Your Pincode").fill(PINCODE)

    page.get_by_text("457001", exact=True).click()
    # Wait a few seconds to see if suggestions appear
    page.wait_for_timeout(5000)

    input("Press Enter to close...")
    browser.close()