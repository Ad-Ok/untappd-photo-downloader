#!/usr/bin/env python3
"""
Untappd Photo Scraper
Скрипт для скачивания фотографий пользователя с Untappd.com

ВНИМАНИЕ: Используйте только для личных целей и соблюдайте ToS Untappd.
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
    """Класс для скрейпинга фотографий с Untappd"""
    
    BASE_URL = "https://untappd.com"
    LOGIN_URL = f"{BASE_URL}/login"
    
    def __init__(self, username: str, password: str, delay: float = 2.0):
        """
        Инициализация скрейпера
        
        Args:
            username: Email для авторизации
            password: Пароль
            delay: Задержка между запросами в секундах (для вежливости)
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
        Получение списка фотографий пользователя с использованием Selenium
        
        Args:
            target_username: Имя пользователя Untappd
            max_photos: Максимальное количество фото (None = все)
            
        Returns:
            Список словарей с информацией о фотографиях
        """
        print(f"📸 Получение фотографий пользователя '{target_username}'...")
        
        # Инициализация Selenium WebDriver
        self._init_driver()
        
        try:
            # Переходим на страницу логина
            print("🔐 Откроется браузер - авторизуйтесь вручную и пройдите капчу")
            self.driver.get(self.LOGIN_URL)
            
            # Ждём, пока пользователь авторизуется вручную
            print("⏳ Ожидание авторизации... (после входа нажмите Enter в терминале)")
            input("Нажмите Enter после успешной авторизации: ")
            
            # Переходим на страницу фотографий
            url = f"{self.BASE_URL}/user/{target_username}/photos"
            self.driver.get(url)
            time.sleep(3)
            
            # Собираем все фото, кликая "Show More"
            photos = self._load_all_photos(target_username, max_photos)
            
            print(f"✅ Всего найдено фотографий: {len(photos)}")
            return photos
            
        finally:
            # Закрываем браузер
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _init_driver(self):
        """Инициализация Selenium WebDriver"""
        print("🌐 Запуск браузера...")
        options = webdriver.ChromeOptions()
        # Браузер будет видимым для ручной авторизации
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # Используем webdriver-manager для автоматической установки ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def _load_all_photos(self, username: str, max_photos: Optional[int] = None) -> List[Dict]:
        """Загрузка всех фотографий, кликая кнопку Show More"""
        all_photos = []
        seen_photo_ids: Set[str] = set()
        load_more_attempts = 0
        max_attempts = 100  # Защита от бесконечного цикла
        
        while load_more_attempts < max_attempts:
            # Парсим текущую страницу
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            photo_items = soup.find_all('a', class_='photo-item')
            
            # Извлекаем новые фото
            new_photos = 0
            for item in photo_items:
                photo_id = item.get('data-photo-id')
                
                if photo_id and photo_id not in seen_photo_ids:
                    seen_photo_ids.add(photo_id)
                    
                    # Ищем div с photoJSON
                    photo_json_div = item.find('div', id=re.compile(r'^photoJSON_'))
                    if photo_json_div and photo_json_div.string:
                        try:
                            photo_data = json.loads(photo_json_div.string)
                            photo_img_og = photo_data.get('photo', {}).get('photo_img_og')
                            
                            if photo_img_og:
                                img_url = photo_img_og.replace(r'\/', '/')
                                
                                # Пропускаем логотипы
                                if 'beer_logos' in img_url or 'brewery_logos' in img_url:
                                    continue
                                
                                all_photos.append({
                                    'url': img_url,
                                    'photo_id': photo_id
                                })
                                new_photos += 1
                        except (json.JSONDecodeError, AttributeError):
                            continue
            
            print(f"  Загружено фотографий: {len(all_photos)} (+{new_photos} новых)")
            
            # Проверяем лимит
            if max_photos and len(all_photos) >= max_photos:
                return all_photos[:max_photos]
            
            # Ищем кнопку "Show More" с разными селекторами
            show_more_found = False
            try:
                # Прокручиваем вниз страницы
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Пробуем разные селекторы для кнопки
                selectors = [
                    "a.more_photos",
                    "a.yellow.button.more_photos",
                    "a[data-href=':photos/showmore']",
                    ".more_photos"
                ]
                
                for selector in selectors:
                    try:
                        show_more_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        # Проверяем, видна ли кнопка
                        if show_more_button.is_displayed() and show_more_button.is_enabled():
                            print(f"  Кликаем 'Show More' (селектор: {selector})...")
                            # Используем JavaScript для клика, чтобы избежать проблем с перекрытием
                            self.driver.execute_script("arguments[0].click();", show_more_button)
                            show_more_found = True
                            
                            # Ждём загрузки новых фото (5 секунд)
                            time.sleep(5)
                            load_more_attempts += 1
                            break
                    except NoSuchElementException:
                        continue
                
                if not show_more_found:
                    print("  Кнопка 'Show More' не найдена или не видна - все фото загружены")
                    break
                    
            except Exception as e:
                print(f"  Ошибка при поиске кнопки: {e}")
                break
        
        return all_photos
    
    def download_photos(self, photos: List[Dict], output_dir: str = "photos") -> None:
        """
        Скачивание фотографий
        
        Args:
            photos: Список фотографий из get_user_photos()
            output_dir: Директория для сохранения
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"\n💾 Скачивание {len(photos)} фотографий в '{output_dir}'...")
        
        for idx, photo in enumerate(photos, 1):
            try:
                # Формируем имя файла
                filename = f"photo_{idx:04d}.jpg"
                filepath = output_path / filename
                
                # Проверяем, не скачан ли уже файл
                if filepath.exists():
                    print(f"  [{idx}/{len(photos)}] Пропуск (уже существует): {filename}")
                    continue
                
                # Скачиваем
                print(f"  [{idx}/{len(photos)}] Скачивание: {filename}")
                response = self.session.get(photo['url'], stream=True)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"  ❌ Ошибка скачивания фото {idx}: {e}")
                continue
        
        print(f"\n✅ Готово! Фотографии сохранены в '{output_dir}'")


def load_credentials(creds_file: str = "creds.txt") -> tuple:
    """Загрузка учетных данных из файла"""
    if not os.path.exists(creds_file):
        raise FileNotFoundError(f"Файл '{creds_file}' не найден. Создайте файл с email и паролем.")
    
    with open(creds_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if len(lines) < 2:
        raise ValueError("Файл creds.txt должен содержать 2 строки: email и пароль")
    
    email = lines[0]
    password = lines[1]
    
    return email, password


def main():
    """Основная функция"""
    print("=" * 60)
    print("Untappd Photo Scraper")
    print("=" * 60)
    
    try:
        # Загружаем учетные данные
        email, password = load_credentials()
        
        # Создаем скрейпер
        scraper = UntappdPhotoScraper(email, password, delay=2.0)
        
        # Целевой пользователь (можно изменить здесь или в creds.txt)
        target_user = "goosinsky"
        
        # Получаем список фотографий (с ручной авторизацией в браузере)
        photos = scraper.get_user_photos(target_user)
        
        if not photos:
            print("❌ Фотографии не найдены")
            return
        
        # Скачиваем фотографии
        scraper.download_photos(photos, output_dir=f"photos_{target_user}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
