#!/usr/bin/env python3
"""
Webscraper to download tangram solution images using cloudscraper
This version can bypass Cloudflare and similar protections
"""

import os
import time
from urllib.parse import urljoin, urlparse

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    print("cloudscraper not installed. Installing...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'cloudscraper'])
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True

from bs4 import BeautifulSoup

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

def download_image(scraper, img_url, filename):
    """Download an image from a URL and save it to the output directory"""
    try:
        response = scraper.get(img_url, timeout=15)
        response.raise_for_status()

        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return False

def scrape_tangram_solutions():
    """Main scraping function"""
    create_output_directory()

    # Create a cloudscraper session
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    try:
        print(f"Fetching {BASE_URL}...")
        response = scraper.get(BASE_URL, timeout=15)
        response.raise_for_status()
        print(f"Successfully fetched page (status: {response.status_code})")

        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        print(f"Page title: {soup.title.string if soup.title else 'N/A'}")

        # Find all images
        image_urls = set()

        # Method 1: Find all img tags
        img_tags = soup.find_all('img')
        print(f"Found {len(img_tags)} img tags")

        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                # Make absolute URL
                full_url = urljoin(BASE_URL, src)

                # Skip very small images and common non-content images
                if any(skip in full_url.lower() for skip in ['logo', 'icon', 'avatar', 'button']):
                    continue

                # Add image if it looks like content
                if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    image_urls.add(full_url)

        # Method 2: Find images in links
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                full_url = urljoin(BASE_URL, href)
                image_urls.add(full_url)

        # Method 3: Look for WordPress gallery images (common pattern)
        for div in soup.find_all(['div', 'figure'], class_=lambda x: x and ('gallery' in x.lower() or 'image' in x.lower() or 'wp-block' in x.lower())):
            for img in div.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    full_url = urljoin(BASE_URL, src)
                    if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        image_urls.add(full_url)

        image_urls = list(image_urls)
        print(f"\nFound {len(image_urls)} unique images to download")

        if not image_urls:
            print("\nNo images found. Saving page HTML for manual inspection...")
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("Saved to page_source.html")

            print("\nFirst 10 img tags found:")
            for i, img in enumerate(img_tags[:10], 1):
                print(f"{i}. src={img.get('src')}, class={img.get('class')}, alt={img.get('alt')}")

        # Download images
        downloaded = 0
        failed = 0

        for i, img_url in enumerate(image_urls, 1):
            # Generate filename
            filename = os.path.basename(urlparse(img_url).path)
            if not filename or '.' not in filename:
                ext = 'jpg'
                if '.png' in img_url.lower():
                    ext = 'png'
                elif '.webp' in img_url.lower():
                    ext = 'webp'
                elif '.gif' in img_url.lower():
                    ext = 'gif'
                filename = f"tangram_{i:03d}.{ext}"

            # Clean filename
            filename = filename.split('?')[0]  # Remove query parameters

            # Be respectful to the server
            if i > 1:
                time.sleep(0.5)

            if download_image(scraper, img_url, filename):
                downloaded += 1
            else:
                failed += 1

        print(f"\n{'='*50}")
        print(f"Download complete!")
        print(f"Successfully downloaded: {downloaded}")
        print(f"Failed: {failed}")
        print(f"Total: {len(image_urls)}")
        print(f"Images saved to: {OUTPUT_DIR}/")
        print(f"{'='*50}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scrape_tangram_solutions()
