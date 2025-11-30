#!/usr/bin/env python3
"""
Untappd Photo Downloader
Script for downloading user photos from Untappd.com

WARNING: Use only for personal purposes and respect Untappd's ToS.
"""

import os
import re
import time
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class UntappdPhotoScraper:
    """Class for scraping photos from Untappd"""
    
    BASE_URL = "https://untappd.com"
    LOGIN_URL = f"{BASE_URL}/login"
    
    def __init__(self, username: str, password: str, delay: float = 2.0):
        """
        Initialize scraper
        
        Args:
            username: Email for authentication
            password: Password
            delay: Delay between requests in seconds (for politeness)
        """
        self.username = username
        self.password = password
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.driver = None
    
    def get_user_photos(self, target_username: str, max_photos: Optional[int] = None) -> List[Dict]:
        """
        Get list of user photos using Selenium
        
        Args:
            target_username: Untappd username
            max_photos: Maximum number of photos (None = all)
            
        Returns:
            List of dictionaries with photo information
        """
        print(f"📸 Getting photos for user '{target_username}'...")
        
        # Initialize Selenium WebDriver
        self._init_driver()
        
        try:
            # Go to login page
            print("🔐 Browser will open - log in manually and pass CAPTCHA")
            self.driver.get(self.LOGIN_URL)
            
            # Wait for user to log in manually
            print("⏳ Waiting for login... (press Enter in terminal after logging in)")
            input("Press Enter after successful login: ")
            
            # Go to photos page
            url = f"{self.BASE_URL}/user/{target_username}/photos"
            self.driver.get(url)
            time.sleep(3)
            
            # Collect all photos by clicking "Show More"
            photos = self._load_all_photos(target_username, max_photos)
            
            print(f"✅ Total photos found: {len(photos)}")
            return photos
            
        finally:
            # Close browser
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        print("🌐 Starting browser...")
        options = webdriver.ChromeOptions()
        # Browser will be visible for manual login
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # Use webdriver-manager for automatic ChromeDriver installation
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def _load_all_photos(self, username: str, max_photos: Optional[int] = None) -> List[Dict]:
        """Load all photos by clicking Show More button"""
        all_photos = []
        seen_photo_ids: Set[str] = set()
        load_more_attempts = 0
        max_attempts = 100  # Protection against infinite loop
        
        while load_more_attempts < max_attempts:
            # Parse current page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            photo_items = soup.find_all('a', class_='photo-item')
            
            # Extract new photos
            new_photos = 0
            for item in photo_items:
                photo_id = item.get('data-photo-id')
                
                if photo_id and photo_id not in seen_photo_ids:
                    seen_photo_ids.add(photo_id)
                    
                    # Find div with photoJSON
                    photo_json_div = item.find('div', id=re.compile(r'^photoJSON_'))
                    if photo_json_div and photo_json_div.string:
                        try:
                            photo_data = json.loads(photo_json_div.string)
                            photo_img_og = photo_data.get('photo', {}).get('photo_img_og')
                            
                            if photo_img_og:
                                img_url = photo_img_og.replace(r'\/', '/')
                                
                                # Skip logos
                                if 'beer_logos' in img_url or 'brewery_logos' in img_url:
                                    continue
                                
                                all_photos.append({
                                    'url': img_url,
                                    'photo_id': photo_id
                                })
                                new_photos += 1
                        except (json.JSONDecodeError, AttributeError):
                            continue
            
            print(f"  Loaded photos: {len(all_photos)} (+{new_photos} new)")
            
            # Check limit
            if max_photos and len(all_photos) >= max_photos:
                return all_photos[:max_photos]
            
            # Look for "Show More" button with different selectors
            show_more_found = False
            try:
                # Scroll to bottom of page
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Try different selectors for the button
                selectors = [
                    "a.more_photos",
                    "a.yellow.button.more_photos",
                    "a[data-href=':photos/showmore']",
                    ".more_photos"
                ]
                
                for selector in selectors:
                    try:
                        show_more_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        # Check if button is visible
                        if show_more_button.is_displayed() and show_more_button.is_enabled():
                            print(f"  Clicking 'Show More' (selector: {selector})...")
                            # Use JavaScript to click to avoid overlay issues
                            self.driver.execute_script("arguments[0].click();", show_more_button)
                            show_more_found = True
                            
                            # Wait for new photos to load (5 seconds)
                            time.sleep(5)
                            load_more_attempts += 1
                            break
                    except NoSuchElementException:
                        continue
                
                if not show_more_found:
                    print("  'Show More' button not found or not visible - all photos loaded")
                    break
                    
            except Exception as e:
                print(f"  Error searching for button: {e}")
                break
        
        return all_photos
    
    def download_photos(self, photos: List[Dict], output_dir: str = "photos") -> None:
        """
        Download photos
        
        Args:
            photos: List of photos from get_user_photos()
            output_dir: Directory for saving photos
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"\n💾 Downloading {len(photos)} photos to '{output_dir}'...")
        
        for idx, photo in enumerate(photos, 1):
            try:
                # Format filename
                filename = f"photo_{idx:04d}.jpg"
                filepath = output_path / filename
                
                # Check if file already exists
                if filepath.exists():
                    print(f"  [{idx}/{len(photos)}] Skipping (already exists): {filename}")
                    continue
                
                # Download
                print(f"  [{idx}/{len(photos)}] Downloading: {filename}")
                response = self.session.get(photo['url'], stream=True)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"  ❌ Download error for photo {idx}: {e}")
                continue
        
        print(f"\n✅ Done! Photos saved to '{output_dir}'")


def load_credentials(creds_file: str = "creds.txt") -> tuple:
    """Load credentials from file"""
    if not os.path.exists(creds_file):
        raise FileNotFoundError(f"File '{creds_file}' not found. Create file with email and password.")
    
    with open(creds_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if len(lines) < 2:
        raise ValueError("File creds.txt must contain 2 lines: email and password")
    
    email = lines[0]
    password = lines[1]
    
    return email, password


def main():
    """Main function"""
    print("=" * 60)
    print("Untappd Photo Scraper")
    print("=" * 60)
    
    try:
        # Load credentials
        email, password = load_credentials()
        
        # Create scraper
        scraper = UntappdPhotoScraper(email, password, delay=2.0)
        
        # Target user (can be changed here or in creds.txt)
        target_user = "goosinsky"
        
        # Get list of photos (with manual browser login)
        photos = scraper.get_user_photos(target_user)
        
        if not photos:
            print("❌ No photos found")
            return
        
        # Download photos
        scraper.download_photos(photos, output_dir=f"photos_{target_user}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
