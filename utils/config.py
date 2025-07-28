"""
Cấu hình global cho TikTok Tool
"""
import os
from pathlib import Path

# Thư mục gốc của project
BASE_DIR = Path(__file__).parent.parent

# Thư mục lưu downloads
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"

# Tạo các thư mục nếu chưa tồn tại
for dir_path in [DOWNLOADS_DIR, TEMP_DIR, OUTPUT_DIR]:
    dir_path.mkdir(exist_ok=True)

# TikTok URLs
TIKTOK_BASE_URL = "https://www.tiktok.com"
TIKTOK_SEARCH_URL = "https://www.tiktok.com/search/video"
TIKTOK_TRENDING_URL = "https://www.tiktok.com/trending"

# User Agents rotator
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Selenium/Browser config
SELENIUM_TIMEOUT = 10
PAGE_LOAD_TIMEOUT = 30
IMPLICIT_WAIT = 5

# Video processing config
FRAME_EXTRACTION_INTERVAL = 1  # Extract 1 frame per second
SIMILARITY_THRESHOLD = 0.8     # 80% similarity threshold
MAX_VIDEO_DURATION = 300       # 5 minutes max

# Scraping config
REQUEST_DELAY = (1, 3)         # Random delay between requests (min, max seconds)
MAX_RETRIES = 3
CONCURRENT_WORKERS = 5

# Countries mapping
COUNTRIES = {
    'US': 'United States',
    'VN': 'Vietnam', 
    'JP': 'Japan',
    'KR': 'South Korea',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'FR': 'France',
    'IT': 'Italy',
    'ES': 'Spain',
    'BR': 'Brazil',
    'IN': 'India',
    'CN': 'China',
    'RU': 'Russia',
    'AU': 'Australia',
    'CA': 'Canada'
}

# Output formats
CSV_ENCODING = 'utf-8-sig'
JSON_ENCODING = 'utf-8'

# Hash algorithm config
HASH_SIZE = 16
HIGHFREQ_FACTOR = 4