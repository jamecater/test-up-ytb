"""
Module scraping TikTok với các tính năng chống detect
"""
import time
import random
import logging
from typing import List, Dict, Optional, Any
import requests
from bs4 import BeautifulSoup
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

from .config import (
    USER_AGENTS, SELENIUM_TIMEOUT, PAGE_LOAD_TIMEOUT, 
    REQUEST_DELAY, MAX_RETRIES, TIKTOK_BASE_URL, 
    TIKTOK_SEARCH_URL, TIKTOK_TRENDING_URL
)

logger = logging.getLogger(__name__)

class TikTokScraper:
    def __init__(self, use_proxy: bool = False, proxy_list: List[str] = None):
        self.ua = UserAgent()
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        self.session = None
        self.driver = None
        
    def get_random_user_agent(self) -> str:
        """Lấy random user agent"""
        return random.choice(USER_AGENTS)
    
    def get_next_proxy(self) -> Optional[str]:
        """Lấy proxy tiếp theo trong danh sách"""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def create_session(self) -> requests.Session:
        """Tạo requests session với cấu hình chống detect"""
        session = requests.Session()
        
        # Headers chống detect
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        session.headers.update(headers)
        
        # Proxy nếu có
        if self.use_proxy and self.proxy_list:
            proxy = self.get_next_proxy()
            if proxy:
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
                logger.info(f"Sử dụng proxy: {proxy}")
        
        return session
    
    def create_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Tạo Chrome driver với cấu hình chống detect"""
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument('--headless')
            
            # Các options chống detect
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Tắt load ảnh để tăng tốc
            chrome_options.add_argument('--disable-javascript')  # Có thể tắt JS nếu không cần
            
            # User agent
            chrome_options.add_argument(f'--user-agent={self.get_random_user_agent()}')
            
            # Window size
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Proxy nếu có
            if self.use_proxy and self.proxy_list:
                proxy = self.get_next_proxy()
                if proxy:
                    chrome_options.add_argument(f'--proxy-server={proxy}')
                    logger.info(f"Driver sử dụng proxy: {proxy}")
            
            # Tạo driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Thiết lập timeouts
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            driver.implicitly_wait(SELENIUM_TIMEOUT)
            
            # Script chống detect
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo Chrome driver: {e}")
            return None
    
    def random_delay(self):
        """Random delay giữa các request"""
        delay = random.uniform(REQUEST_DELAY[0], REQUEST_DELAY[1])
        time.sleep(delay)
    
    def search_videos_by_keyword(self, keyword: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video TikTok theo từ khóa
        """
        try:
            logger.info(f"Tìm kiếm video với từ khóa: {keyword}")
            
            if not self.driver:
                self.driver = self.create_driver(headless=True)
                if not self.driver:
                    return []
            
            # URL tìm kiếm
            search_url = f"{TIKTOK_SEARCH_URL}?q={keyword}"
            
            # Truy cập trang tìm kiếm
            self.driver.get(search_url)
            self.random_delay()
            
            videos = []
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll để load thêm video
            while len(videos) < max_results:
                # Scroll xuống
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_delay()
                
                # Lấy video elements
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-e2e="search-card-item"]')
                
                for element in video_elements[len(videos):]:
                    try:
                        video_data = self.extract_video_data_from_element(element)
                        if video_data:
                            videos.append(video_data)
                            if len(videos) >= max_results:
                                break
                    except Exception as e:
                        logger.debug(f"Lỗi khi extract video data: {e}")
                        continue
                
                # Kiểm tra xem có load thêm content không
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
                # Delay để tránh bị chặn
                time.sleep(2)
            
            logger.info(f"Tìm thấy {len(videos)} video cho từ khóa '{keyword}'")
            return videos[:max_results]
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm video: {e}")
            return []
    
    def get_trending_videos(self, country: str = 'US', max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Lấy video trending theo quốc gia
        """
        try:
            logger.info(f"Lấy video trending cho quốc gia: {country}")
            
            if not self.driver:
                self.driver = self.create_driver(headless=True)
                if not self.driver:
                    return []
            
            # URL trending (có thể cần điều chỉnh theo country)
            trending_url = f"{TIKTOK_TRENDING_URL}"
            
            # Truy cập trang trending
            self.driver.get(trending_url)
            self.random_delay()
            
            videos = []
            scroll_attempts = 0
            max_scroll_attempts = 10
            
            while len(videos) < max_results and scroll_attempts < max_scroll_attempts:
                # Tìm video elements
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-e2e="recommend-list-item-container"]')
                
                for element in video_elements[len(videos):]:
                    try:
                        video_data = self.extract_video_data_from_element(element)
                        if video_data:
                            videos.append(video_data)
                            if len(videos) >= max_results:
                                break
                    except Exception as e:
                        logger.debug(f"Lỗi khi extract trending video data: {e}")
                        continue
                
                # Scroll để load thêm
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_delay()
                scroll_attempts += 1
                
                time.sleep(3)  # Đợi load content
            
            logger.info(f"Lấy được {len(videos)} trending video")
            return videos[:max_results]
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy trending video: {e}")
            return []
    
    def extract_video_data_from_element(self, element) -> Optional[Dict[str, Any]]:
        """
        Trích xuất dữ liệu video từ element
        """
        try:
            video_data = {}
            
            # Link video
            link_elem = element.find_element(By.CSS_SELECTOR, 'a')
            video_data['url'] = link_elem.get_attribute('href') if link_elem else ''
            
            # Username
            try:
                username_elem = element.find_element(By.CSS_SELECTOR, '[data-e2e="search-card-user-unique-id"]')
                video_data['username'] = username_elem.text.strip()
            except NoSuchElementException:
                video_data['username'] = ''
            
            # Title/Description
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, '[data-e2e="search-card-desc"]')
                video_data['title'] = title_elem.text.strip()
            except NoSuchElementException:
                video_data['title'] = ''
            
            # View count
            try:
                view_elem = element.find_element(By.CSS_SELECTOR, '[data-e2e="search-card-like-container"]')
                view_text = view_elem.text
                video_data['view_count'] = self.parse_count(view_text)
            except NoSuchElementException:
                video_data['view_count'] = 0
            
            # Like count
            try:
                like_elem = element.find_element(By.CSS_SELECTOR, '[data-e2e="search-card-like-container"]')
                like_text = like_elem.text
                video_data['like_count'] = self.parse_count(like_text)
            except NoSuchElementException:
                video_data['like_count'] = 0
            
            # Duration (nếu có)
            try:
                duration_elem = element.find_element(By.CSS_SELECTOR, '[data-e2e="search-card-video-duration"]')
                video_data['duration'] = duration_elem.text.strip()
            except NoSuchElementException:
                video_data['duration'] = ''
            
            # Thumbnail
            try:
                img_elem = element.find_element(By.CSS_SELECTOR, 'img')
                video_data['thumbnail'] = img_elem.get_attribute('src')
            except NoSuchElementException:
                video_data['thumbnail'] = ''
            
            return video_data if video_data.get('url') else None
            
        except Exception as e:
            logger.debug(f"Lỗi khi extract video data: {e}")
            return None
    
    def parse_count(self, count_text: str) -> int:
        """
        Parse count text (ví dụ: '1.2M', '45.6K') thành số
        """
        try:
            count_text = count_text.strip().upper()
            
            if 'M' in count_text:
                return int(float(count_text.replace('M', '')) * 1_000_000)
            elif 'K' in count_text:
                return int(float(count_text.replace('K', '')) * 1_000)
            else:
                return int(re.sub(r'[^\d]', '', count_text))
                
        except (ValueError, AttributeError):
            return 0
    
    def get_video_details(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Lấy chi tiết video từ URL
        """
        try:
            logger.info(f"Lấy chi tiết video: {video_url}")
            
            if not self.driver:
                self.driver = self.create_driver(headless=True)
                if not self.driver:
                    return None
            
            self.driver.get(video_url)
            self.random_delay()
            
            video_details = {}
            
            # Lấy các thông tin chi tiết
            try:
                # Username
                username_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-username"]')
                video_details['username'] = username_elem.text.strip()
            except NoSuchElementException:
                video_details['username'] = ''
            
            # Description
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-video-desc"]')
                video_details['description'] = desc_elem.text.strip()
            except NoSuchElementException:
                video_details['description'] = ''
            
            # Music info
            try:
                music_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-music"]')
                video_details['music'] = music_elem.text.strip()
            except NoSuchElementException:
                video_details['music'] = ''
            
            # Engagement stats
            try:
                like_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-like-count"]')
                video_details['like_count'] = self.parse_count(like_elem.text)
            except NoSuchElementException:
                video_details['like_count'] = 0
            
            try:
                comment_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-comment-count"]')
                video_details['comment_count'] = self.parse_count(comment_elem.text)
            except NoSuchElementException:
                video_details['comment_count'] = 0
            
            try:
                share_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-share-count"]')
                video_details['share_count'] = self.parse_count(share_elem.text)
            except NoSuchElementException:
                video_details['share_count'] = 0
            
            video_details['url'] = video_url
            
            return video_details
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy chi tiết video: {e}")
            return None
    
    def close(self):
        """Đóng driver và session"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        if self.session:
            self.session.close()
            self.session = None
    
    def __del__(self):
        """Cleanup khi object bị destroy"""
        self.close()