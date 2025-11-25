from playwright.sync_api import sync_playwright
import time

def inspect_structure():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to Nike.sk...")
        page.goto("https://www.nike.sk/tipovanie/futbal")
        
        try:
            # Accept cookies if needed
            try:
                page.get_by_text("Povoliť všetko").click(timeout=5000)
                print("Accepted cookies")
            except:
                print("No cookie banner found or already accepted")

            print("Waiting for odds container...")
            page.wait_for_selector("div.native-scroll", timeout=10000)
            
            # Get the container
            container = page.locator("div.native-scroll")

            # Get the inner container and innermost view
            inner_container = container.locator("div.mx-3")
            innermost = inner_container.locator("div.boxes-inner-view")
            
            # Get children
            children = innermost.locator("> *").all()
            print(f"Found {len(children)} children in innermost container (div.boxes-inner-view)")
            
            # Inspect first few children
            for i, child in enumerate(children[:20]):
                tag = child.evaluate("el => el.tagName")
                class_name = child.evaluate("el => el.className")
                text = child.inner_text().replace("\n", " ")[:50]
                print(f"Item {i}: <{tag} class='{class_name}'> - Text: {text}...")
                
                # Check if this child contains odds
                odds = child.locator("a.bet-box").all()
                if odds:
                    print(f"  -> Contains {len(odds)} bet boxes")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="debug_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    inspect_structure()
