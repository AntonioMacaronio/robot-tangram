#!/usr/bin/env python3
"""
Webscraper to download tangram solution images using Selenium
This version uses a real browser to bypass anti-bot protections
"""

import os
import time
import requests
from urllib.parse import urljoin, urlparse

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not installed. Install with: pip install selenium")

# Configuration
BASE_URL = "https://www.tangram-channel.com/tangram-solutions/"
OUTPUT_DIR = "tangram-imgs"

def create_output_directory():
    """Create the output directory if it doesn't exist"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")
    else:
        print(f"Directory already exists: {OUTPUT_DIR}")

def download_image(img_url, filename):
    """Download an image from a URL and save it to the output directory"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': BASE_URL
        }
        response = requests.get(img_url, headers=headers, timeout=15)
        response.raise_for_status()

        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return False

def scrape_with_selenium():
    """Scrape using Selenium WebDriver"""
    if not SELENIUM_AVAILABLE:
        print("Please install selenium: pip install selenium")
        print("Also install Chrome/Chromium and chromedriver")
        return

    create_output_directory()

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        print("Starting browser...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)

        print(f"Fetching {BASE_URL}...")
        driver.get(BASE_URL)

        # Wait for page to load
        time.sleep(3)

        # Find all images
        img_elements = driver.find_elements(By.TAG_NAME, "img")
        print(f"Found {len(img_elements)} img elements")

        # Collect image URLs
        image_urls = []
        for img in img_elements:
            try:
                src = img.get_attribute('src') or img.get_attribute('data-src')
                if src and src.startswith('http'):
                    # Filter for actual content images
                    alt = img.get_attribute('alt') or ''
                    width = img.get_attribute('width')

                    # Skip very small images (icons, etc.)
                    try:
                        if width and int(width) < 50:
                            continue
                    except:
                        pass

                    if any(keyword in src.lower() for keyword in ['tangram', 'solution', 'puzzle']) or \
                       any(keyword in alt.lower() for keyword in ['tangram', 'solution', 'puzzle']) or \
                       (not width):
                        image_urls.append(src)
            except Exception as e:
                continue

        # Also check for linked images
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            try:
                href = link.get_attribute('href')
                if href and any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    image_urls.append(href)
            except:
                continue

        # Remove duplicates
        image_urls = list(set(image_urls))
        print(f"Found {len(image_urls)} unique images")

        if not image_urls:
            print("\nNo images found. Debugging info:")
            print(f"Page title: {driver.title}")
            print(f"Page source length: {len(driver.page_source)}")

            # Save page source for inspection
            with open('page_debug.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Saved page source to page_debug.html for inspection")

        driver.quit()

        # Download images
        downloaded = 0
        for i, img_url in enumerate(image_urls, 1):
            filename = os.path.basename(urlparse(img_url).path)
            if not filename or '.' not in filename:
                ext = img_url.split('.')[-1].split('?')[0][:4]
                filename = f"tangram_{i}.{ext}"

            # Be respectful to the server
            if i > 1:
                time.sleep(1)

            if download_image(img_url, filename):
                downloaded += 1

        print(f"\nDownload complete! {downloaded}/{len(image_urls)} images saved to {OUTPUT_DIR}/")

    except Exception as e:
        print(f"Error: {e}")
        if 'driver' in locals():
            driver.quit()
        raise

if __name__ == "__main__":
    scrape_with_selenium()
