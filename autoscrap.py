import time
import sqlite3
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- Setup SQLite Database ---
conn = sqlite3.connect('11888_data.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    location TEXT,
    phones TEXT,
    page_url TEXT,
    page INTEGER
)
''')
conn.commit()

# --- List of Proxies ---
proxies = [
    "http://proxy1:port",  # Replace with your actual proxy addresses
    "http://proxy2:port",
    "http://proxy3:port"
]

def create_driver(proxy):
    """Creates a patched Chrome WebDriver to bypass bot detection."""
    options = uc.ChromeOptions()
    
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    
    # Note: We do NOT set a custom user-agent. 
    # uc automatically patches in a clean, legitimate one.
    
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
        
    # Initialize the undetected driver
    driver = uc.Chrome(
        options=options,
        headless=True,       # uc handles headless mode specially
        use_subprocess=True  # Recommended to prevent hanging zombie processes
    )
    
    return driver

# --- Scraping Logic ---
scrape_page = 1
max_pages = 50000000
requests_with_current_ip = 0
MAX_REQUESTS_PER_IP = 100  # Rotate IP after 100 successful requests

driver = None

while scrape_page < max_pages:
    try:
        # Initialize driver or rotate proxy if we hit the request limit
        if driver is None or requests_with_current_ip >= MAX_REQUESTS_PER_IP:
            if driver:
                driver.quit()
            
            # Select a random proxy (in production, you'd want logic to ensure it's not the same as the last one)
            proxy = random.choice(proxies) if proxies else None
            print(f"[*] Booting session. Proxy: {proxy or 'Direct IP'}")
            
            driver = create_driver(proxy)
            requests_with_current_ip = 0

        url = f"https://www.11888.gr/search/white_pages/{scrape_page}/"
        driver.get(url)
        requests_with_current_ip += 1
        
        # Explicit Wait: Wait up to 5 seconds for the data container to load
        wait = WebDriverWait(driver, 5)
        
        # Check for redirects (if page has no data, they might redirect)
        if "search/white_pages" not in driver.current_url:
            print(f"Redirected away on page {scrape_page}. Skipping.")
            scrape_page += 1
            continue

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.details")))
            details_containers = driver.find_elements(By.CSS_SELECTOR, "div.details")
        except TimeoutException:
            print(f"No details found or timeout on page {scrape_page}.")
            scrape_page += 1
            continue

        print(f"Data found on page {scrape_page}.")
        for container in details_containers:
            try:
                name = container.find_element(By.CSS_SELECTOR, "div.share_header div.name h1").text.strip()
            except Exception:
                name = "N/A"
            
            try:
                location = container.find_element(By.CSS_SELECTOR, "div.location div.address").text.strip()
            except Exception:
                location = "N/A"
            
            try:
                phone_elems = container.find_elements(By.CSS_SELECTOR, "div.phones a.tel-link")
                phones = ", ".join([elem.get_attribute("href").split("tel:")[-1].strip() for elem in phone_elems if "tel:" in elem.get_attribute("href")])
            except Exception:
                phones = "N/A"
            
            cursor.execute(
                "INSERT INTO contacts (name, location, phones, page_url, page) VALUES (?, ?, ?, ?, ?)",
                (name, location, phones or "N/A", driver.current_url, scrape_page)
            )
            print(f"Inserted: {name} | {location} | {phones}")
        
        conn.commit()
        scrape_page += 1

    except WebDriverException as e:
        # Catches network errors, target machine actively refusing connection, or driver crashes
        print(f"[!] WebDriver error: {e}. Rotating IP and retrying page {scrape_page}...")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        driver = None 
        # Do not increment scrape_page here so the loop retries the same page

print("Scraping complete!")
if driver:
    driver.quit()
conn.close()