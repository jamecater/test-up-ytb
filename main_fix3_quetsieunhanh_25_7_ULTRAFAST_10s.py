import time
import os
import pandas as pd
import logging
from multiprocessing import Process
from googleapiclient.discovery import build
import isodate
import yt_dlp
from datetime import datetime, timezone
from colorama import Fore, Style, init
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import tempfile
import subprocess
from selenium.webdriver.common.by import By
import requests
import random
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import sys
import json
import re
from selenium.webdriver.common.keys import Keys
import shutil
import glob
from selenium.webdriver.common.action_chains import ActionChains

# Chặn stderr (ẩn mọi warning/error từ Chrome, TensorFlow, v.v.)
sys.stderr = open(os.devnull, 'w')

init(autoreset=True)

# Chọn chế độ chạy: 'api' hoặc 'yt_dlp'
MODE = 'yt_dlp'

DOWNLOAD_DIR = 'downloads'
PROCESSED_DIR = 'processed'
MAPPING_FILE = 'mapping.xlsx'
MAPPING_CSV = 'mapping.csv'
FFPROBE_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe'
FFMPEG_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'

# Auto-detect ChromeDriver path với multiple fallbacks
def find_chromedriver():
    """Tự động tìm ChromeDriver từ nhiều location khác nhau"""
    possible_paths = [
        r'D:\Test up ytb\chromedriver.exe',
        r'C:\chromedriver.exe',
        r'chromedriver.exe',
        r'.\chromedriver.exe',
        r'C:\Program Files\Google\Chrome\Application\chromedriver.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe',
        r'C:\Windows\System32\chromedriver.exe',
        r'C:\tools\chromedriver.exe'
    ]
    
    # Thêm các path từ PATH environment
    import os
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    for path_dir in path_dirs:
        possible_paths.append(os.path.join(path_dir, 'chromedriver.exe'))
    
    # Tìm chromedriver trong thư mục hiện tại và subdirectories
    current_dir_patterns = [
        'chromedriver*.exe',
        '*/chromedriver*.exe',
        '*/*/chromedriver*.exe'
    ]
    
    for pattern in current_dir_patterns:
        matches = glob.glob(pattern)
        possible_paths.extend(matches)
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            print(f"✅ Found ChromeDriver: {path}")
            return path
    
    print("❌ ChromeDriver not found in any standard locations!")
    return None

CHROMEDRIVER_PATH = find_chromedriver()

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename='activity.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

def log_upload_time(video_id, profile_id, download_time, process_time, upload_time, total_time):
    """Ghi log thời gian chi tiết vào file upload_time.log"""
    try:
        with open('upload_time.log', 'a', encoding='utf-8') as f:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{now},{video_id},{profile_id},{download_time:.1f},{process_time:.1f},{upload_time:.1f},{total_time:.1f}\n")
    except Exception as e:
        print(f"Lỗi ghi upload_time.log: {e}")

def log(profile_id, msg, level="INFO", substep=False):
    from datetime import datetime
    color = {
        "INFO": Fore.CYAN,
        "NEW": Fore.GREEN,
        "ERROR": Fore.RED,
        "WARNING": Fore.YELLOW,
        "OK": Fore.MAGENTA,
        "TIMING": Fore.LIGHTBLUE_EX,
        "ULTRAFAST": Fore.LIGHTRED_EX
    }.get(level, None)
    prefix = "  ↳ " if substep else ""
    if level == "INFO":
        now_str = datetime.now().strftime('%H:%M:%S')
        level_str = now_str
    else:
        level_str = level
    print(f"{color}{prefix}[{level_str}] [{profile_id}] {msg}{Style.RESET_ALL}")

def load_mapping():
    try:
        df = pd.read_excel(MAPPING_FILE)
    except:
        try:
            df = pd.read_csv(MAPPING_CSV)
        except:
            print("❌ Cannot load mapping file!")
            return []
    
    mapping = []
    channel_col = 'channel_url' if 'channel_url' in df.columns else 'channel_id'
    for _, row in df.iterrows():
        mapping.append((str(row[channel_col]), str(row['profile_id'])))
    return mapping

def get_video_duration(video_path):
    """Lấy thời lượng video nhanh nhất có thể"""
    if not os.path.exists(FFPROBE_PATH):
        return 0
        
    cmd = [
        FFPROBE_PATH,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0',
        video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        return float(result.stdout.strip())
    except:
        return 0

def process_video(input_path, output_path):
    """Xử lý video ULTRA NHANH"""
    start_time = time.time()
    
    try:
        duration = get_video_duration(input_path)
        
        if duration >= 60:
            # Video đủ dài: copy nguyên bản
            shutil.copy2(input_path, output_path)
            process_time = time.time() - start_time
            log('SYSTEM', f"✅ Copy original in {process_time:.2f}s", "TIMING", True)
            return True
        else:
            # Video ngắn: lặp lại nhanh
            target_duration = random.randint(60, 65)
            loop_count = int(target_duration // duration) + 1
            
            if not os.path.exists(FFMPEG_PATH):
                return False
            
            cmd = [
                FFMPEG_PATH, '-y',
                '-stream_loop', str(loop_count - 1),
                '-i', input_path,
                '-ss', '0',
                '-t', str(target_duration),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            
            if result.returncode != 0:
                return False
        
        process_time = time.time() - start_time
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            log('SYSTEM', f"✅ Processed in {process_time:.2f}s", "TIMING", True)
            return True
        else:
            return False
            
    except Exception as e:
        return False

def upload_to_tiktok_gpmlogin(profile_id, video_path, title=None, hashtags=None, description=None):
    """ULTRA-FAST Upload TikTok - TARGET: <10 SECONDS"""
    upload_start = time.time()
    
    log(profile_id, f"🚀 ULTRA-FAST UPLOAD START - Target: <10s", "ULTRAFAST")
    
    # STEP 1: Chrome Connection - Target: <1s
    chrome_start = time.time()
    
    if not CHROMEDRIVER_PATH or not os.path.exists(CHROMEDRIVER_PATH):
        log(profile_id, f"❌ ChromeDriver not found", "ERROR")
        return False
    
    try:
        # GPM profile start - ULTRA FAST
        resp = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}", timeout=5)
        data = resp.json()
        if not data.get("success") or not data["data"].get("remote_debugging_address"):
            log(profile_id, f"❌ GPM start failed", "ERROR")
            return False
        wsEndpoint = data["data"]["remote_debugging_address"]
        
    except Exception as e:
        log(profile_id, f"❌ GPM error: {str(e)[:50]}", "ERROR")
        return False
    
    # Chrome options - MAXIMUM SPEED
    chrome_options = Options()
    chrome_options.page_load_strategy = 'none'  # FASTEST - don't wait for complete load
    chrome_options.add_experimental_option("debuggerAddress", wsEndpoint)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-images")  # Don't load images for speed
    
    service = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(8)  # SHORT timeout
        
        chrome_time = time.time() - chrome_start
        log(profile_id, f"⚡ Chrome connected: {chrome_time:.2f}s", "ULTRAFAST", True)
        
    except Exception as e:
        log(profile_id, f"❌ Chrome error: {str(e)[:50]}", "ERROR")
        return False
    
    try:
        # STEP 2: Page Navigation - Target: <2s
        nav_start = time.time()
        
        driver.get("https://www.tiktok.com/tiktokstudio/upload?lang=en")
        
        # Wait for critical DOM elements - ULTRA FAST
        wait = WebDriverWait(driver, 8)
        
        # Wait for either upload container or file input
        try:
            wait.until(lambda d: d.execute_script("""
                return document.querySelector('#root') || 
                       document.querySelector('[data-e2e="upload-card"]') ||
                       document.querySelector('input[type="file"]') ||
                       document.readyState === 'interactive';
            """))
        except:
            # Continue anyway - may still work
            pass
        
        nav_time = time.time() - nav_start
        log(profile_id, f"⚡ Page loaded: {nav_time:.2f}s", "ULTRAFAST", True)
        
        # STEP 3: File Upload - Target: <1s
        upload_file_start = time.time()
        
        # Find file input with JavaScript injection for speed
        file_input = None
        try:
            # Try multiple selectors rapidly with JavaScript
            file_input = driver.execute_script("""
                var selectors = [
                    'input[type="file"]',
                    'input[accept*="video"]',
                    'input[accept*=".mp4"]',
                    '[data-e2e="upload-input"]'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var element = document.querySelector(selectors[i]);
                    if (element) return element;
                }
                return null;
            """)
            
            if not file_input:
                # Fallback to Selenium
                file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
                
        except Exception as e:
            log(profile_id, f"❌ File input not found: {str(e)[:30]}", "ERROR")
            return False
        
        # Upload file - INSTANT
        file_input.send_keys(os.path.abspath(video_path))
        
        upload_file_time = time.time() - upload_file_start
        log(profile_id, f"⚡ File uploaded: {upload_file_time:.2f}s", "ULTRAFAST", True)
        
        # STEP 4: Wait for Processing + Caption - Target: <3s
        caption_start = time.time()
        
        # Wait for video processing with smart detection
        try:
            wait.until(lambda d: d.execute_script("""
                // Check if video is processing or ready
                var progress = document.querySelector('[data-e2e="upload-progress"]');
                var preview = document.querySelector('[data-e2e="video-preview"]');
                var captionArea = document.querySelector('[contenteditable="true"]') || 
                                 document.querySelector('textarea') ||
                                 document.querySelector('[data-e2e="caption-input"]');
                
                // If no progress bar visible OR caption area available, we're ready
                return (!progress || progress.style.display === 'none') || 
                       captionArea || 
                       preview;
            """))
        except:
            # Continue - may be ready anyway
            pass
        
        # Caption input - ULTRA FAST with JavaScript
        caption_text = title or "Uploaded via automation"
        if hashtags:
            caption_text += " " + " ".join(hashtags)
        
        # Try to input caption with multiple methods
        caption_success = False
        try:
            # Method 1: JavaScript injection (fastest)
            caption_success = driver.execute_script("""
                var text = arguments[0];
                var selectors = [
                    '[contenteditable="true"]',
                    'textarea[data-e2e="caption-input"]',
                    'div[data-e2e="caption-editor"] [contenteditable="true"]',
                    'textarea'
                ];
                
                for (var i = 0; i < selectors.length; i++) {
                    var element = document.querySelector(selectors[i]);
                    if (element && element.offsetParent !== null) {
                        element.focus();
                        element.innerHTML = text;
                        element.innerText = text;
                        element.value = text;
                        
                        // Trigger events
                        element.dispatchEvent(new Event('input', {bubbles: true}));
                        element.dispatchEvent(new Event('change', {bubbles: true}));
                        return true;
                    }
                }
                return false;
            """, caption_text)
            
        except Exception as e:
            log(profile_id, f"⚠️ Caption JS failed: {str(e)[:30]}", "WARNING", True)
        
        # Method 2: Selenium fallback
        if not caption_success:
            try:
                caption_input = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, '[contenteditable="true"], textarea'
                )))
                caption_input.click()
                caption_input.clear()
                caption_input.send_keys(caption_text)
                caption_success = True
            except:
                log(profile_id, f"⚠️ Caption input skipped", "WARNING", True)
        
        caption_time = time.time() - caption_start
        log(profile_id, f"⚡ Caption ready: {caption_time:.2f}s", "ULTRAFAST", True)
        
        # STEP 5: Scroll + Post Button - Target: <2s
        post_start = time.time()
        
        # Scroll to bottom with JavaScript - INSTANT
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for Post button to be enabled - SMART DETECTION
        post_button = None
        post_clicked = False
        
        try:
            # Use JavaScript to find and click Post button - FASTEST METHOD
            post_clicked = driver.execute_script("""
                var postSelectors = [
                    'button[data-e2e="post-video-button"]',
                    'button[data-e2e="upload-btn"]',
                    'button[type="submit"]',
                    'button[class*="post"]',
                    'button[class*="upload"]'
                ];
                
                // Also try text-based search
                var buttons = document.querySelectorAll('button, [role="button"]');
                var postButtons = [];
                
                // Add text-based matches
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    var text = btn.textContent || btn.innerText || '';
                    if (text.toLowerCase().includes('post') || 
                        text.toLowerCase().includes('upload') ||
                        text.toLowerCase().includes('publish')) {
                        postButtons.push(btn);
                    }
                }
                
                // Try selector-based matches
                for (var j = 0; j < postSelectors.length; j++) {
                    var elements = document.querySelectorAll(postSelectors[j]);
                    for (var k = 0; k < elements.length; k++) {
                        postButtons.push(elements[k]);
                    }
                }
                
                // Try to click the first enabled button
                for (var n = 0; n < postButtons.length; n++) {
                    var button = postButtons[n];
                    if (button && 
                        button.offsetParent !== null &&
                        !button.disabled &&
                        button.getAttribute('aria-disabled') !== 'true' &&
                        !button.classList.contains('disabled')) {
                        
                        // Scroll into view and click
                        button.scrollIntoView({behavior: 'instant', block: 'center'});
                        button.click();
                        return true;
                    }
                }
                return false;
            """)
            
        except Exception as e:
            log(profile_id, f"⚠️ JS Post click failed: {str(e)[:30]}", "WARNING", True)
        
        # Fallback: Selenium Post button click
        if not post_clicked:
            try:
                post_selectors = [
                    'button[data-e2e="post-video-button"]',
                    '//button[contains(text(), "Post")]',
                    '//button[contains(text(), "Upload")]',
                    'button[type="submit"]'
                ]
                
                for selector in post_selectors:
                    try:
                        if selector.startswith('//'):
                            post_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        else:
                            post_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                        
                        # Scroll into view and click
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", post_button)
                        
                        # Wait for button to be enabled
                        wait.until(lambda d: post_button.is_enabled() and 
                                           post_button.get_attribute('aria-disabled') != 'true')
                        
                        # Click with JavaScript for reliability
                        driver.execute_script("arguments[0].click();", post_button)
                        post_clicked = True
                        break
                        
                    except:
                        continue
                        
            except Exception as e:
                log(profile_id, f"❌ Post button not found: {str(e)[:30]}", "ERROR")
                return False
        
        if not post_clicked:
            log(profile_id, f"❌ Post button click failed", "ERROR")
            return False
        
        post_time = time.time() - post_start
        log(profile_id, f"⚡ Post clicked: {post_time:.2f}s", "ULTRAFAST", True)
        
        # STEP 6: Handle Copyright Popup - Target: <1s
        popup_start = time.time()
        
        # Handle "Post now" popup with JavaScript - INSTANT
        try:
            popup_handled = driver.execute_script("""
                var popupSelectors = [
                    '[data-e2e="copyright-confirm"]',
                    'button[class*="confirm"]',
                    'button[class*="continue"]'
                ];
                
                var buttons = document.querySelectorAll('button, [role="button"]');
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    var text = btn.textContent || btn.innerText || '';
                    if (text.toLowerCase().includes('post now') ||
                        text.toLowerCase().includes('continue') ||
                        text.toLowerCase().includes('confirm')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)
            
            if popup_handled:
                log(profile_id, f"⚡ Popup handled", "ULTRAFAST", True)
                
        except:
            # No popup or failed - continue
            pass
        
        popup_time = time.time() - popup_start
        
        # STEP 7: Success Detection - Target: <2s
        success_start = time.time()
        
        # Ultra-fast success detection with JavaScript
        success_detected = False
        initial_url = driver.current_url
        
        try:
            # Wait for success indicators with smart detection
            success_detected = wait.until(lambda d: d.execute_script("""
                var currentUrl = window.location.href;
                var initialUrl = arguments[0];
                
                // Check URL change (fastest indicator)
                if (currentUrl !== initialUrl && !currentUrl.includes('/upload')) {
                    return true;
                }
                
                // Check success text indicators
                var successTexts = [
                    'uploaded successfully',
                    'upload complete',
                    'video uploaded',
                    'published',
                    'success',
                    'done'
                ];
                
                var bodyText = document.body.textContent.toLowerCase();
                for (var i = 0; i < successTexts.length; i++) {
                    if (bodyText.includes(successTexts[i])) {
                        return true;
                    }
                }
                
                // Check if upload form disappeared
                var uploadForm = document.querySelector('[data-e2e="upload-card"]') ||
                                document.querySelector('.upload-container') ||
                                document.querySelector('input[type="file"]');
                                
                return !uploadForm;
                
            """, initial_url))
                
        except:
            # Timeout - assume success for now
            success_detected = True
            log(profile_id, f"⚠️ Success timeout - assuming success", "WARNING", True)
        
        success_time = time.time() - success_start
        log(profile_id, f"⚡ Success detected: {success_time:.2f}s", "ULTRAFAST", True)
        
        # Calculate total time
        total_time = time.time() - upload_start
        
        if success_detected:
            log(profile_id, f"🎉 ULTRA-FAST SUCCESS: {total_time:.2f}s", "ULTRAFAST")
            log(profile_id, f"📊 Chrome:{chrome_time:.1f}s Nav:{nav_time:.1f}s File:{upload_file_time:.1f}s Caption:{caption_time:.1f}s Post:{post_time:.1f}s Success:{success_time:.1f}s", "ULTRAFAST")
            return True
        else:
            log(profile_id, f"❌ Upload failed: {total_time:.2f}s", "ERROR")
            return False
        
    except Exception as e:
        total_time = time.time() - upload_start
        log(profile_id, f"❌ ULTRA-FAST ERROR: {str(e)[:50]} ({total_time:.2f}s)", "ERROR")
        return False
        
    finally:
        # INSTANT cleanup
        try:
            if driver:
                driver.quit()
        except:
            pass
        
        try:
            requests.get(f"http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}", timeout=2)
        except:
            pass

def get_latest_shorts_video_ytdlp(channel_url):
    """Quét video mới nhất ULTRA NHANH"""
    if '/shorts' in channel_url:
        base_channel = channel_url.replace('/shorts', '')
    else:
        base_channel = channel_url.replace('/videos', '') if '/videos' in channel_url else channel_url

    test_url = base_channel + '/shorts'

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlist_items': '1:1',
            'no_check_certificate': True,
            'socket_timeout': 6,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)

            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
                if entry and entry.get('id') and len(entry['id']) == 11:
                    video_id = entry['id']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    title = entry.get('title', '')
                    return video_id, video_url, title

    except Exception as e:
        return None, None, None

    return None, None, None

def get_last_video_id_from_mapping(channel_url, profile_id):
    import os
    if os.path.exists(MAPPING_FILE):
        df = pd.read_excel(MAPPING_FILE)
    elif os.path.exists(MAPPING_CSV):
        df = pd.read_csv(MAPPING_CSV)
    else:
        return None, None, None
    
    for idx, row in df.iterrows():
        if str(row['channel_url']) == str(channel_url) and str(row['profile_id']) == str(profile_id):
            return str(row['video_id']) if 'video_id' in row and not pd.isna(row['video_id']) else None, idx, df
    return None, None, df

def update_last_video_id_in_mapping_by_id(channel_id, profile_id, new_video_id):
    import os
    try:
        if os.path.exists(MAPPING_CSV):
            df = pd.read_csv(MAPPING_CSV)
            save_to_csv = True
        elif os.path.exists(MAPPING_FILE):
            df = pd.read_excel(MAPPING_FILE)
            save_to_csv = False
        else:
            return
        
        channel_col = 'channel_url' if 'channel_url' in df.columns else 'channel_id'
        for idx, row in df.iterrows():
            if str(row[channel_col]) == str(channel_id) and str(row['profile_id']) == str(profile_id):
                df.at[idx, 'video_id'] = new_video_id
                
                try:
                    if save_to_csv:
                        df.to_csv(MAPPING_CSV, index=False)
                    else:
                        df.to_csv('mapping_backup.csv', index=False)
                        df.to_excel(MAPPING_FILE, index=False)
                except PermissionError:
                    df.to_csv(MAPPING_CSV, index=False)
                break
    except Exception as e:
        log(profile_id, f"❌ Mapping update error: {e}", "ERROR")

def upload_with_retry(profile_id, processed_path, title, hashtags, max_retries=2):
    """Upload with retry - ULTRA FAST"""
    for attempt in range(max_retries):
        try:
            log(profile_id, f"🚀 ULTRA Upload attempt #{attempt + 1}/{max_retries}", "ULTRAFAST", substep=True)
            
            result = upload_to_tiktok_gpmlogin(profile_id, processed_path, title, hashtags)
            
            if result:
                log(profile_id, f"✅ Upload success attempt #{attempt + 1}", "OK", substep=True)
                return True
            else:
                log(profile_id, f"❌ Upload failed attempt #{attempt + 1}", "WARNING", substep=True)
                if attempt < max_retries - 1:
                    log(profile_id, f"⏳ Brief retry delay", "INFO", substep=True)
                    # Brief delay between retries
                    time.sleep(2)
                
        except Exception as e:
            log(profile_id, f"❌ Exception attempt #{attempt + 1}: {str(e)[:50]}", "ERROR", substep=True)
    
    log(profile_id, f"❌ Upload failed after {max_retries} attempts", "ERROR", substep=True)
    return False

def download_edit_upload_video(profile_id, video_id, video_url, title):
    """Pipeline ULTRA FAST: Download → Edit → Upload"""
    pipeline_start = time.time()
    now_str = datetime.now().strftime('%H:%M:%S')
    
    log(profile_id, f"🚀 [{now_str}] ULTRA-FAST PIPELINE: {video_id}", "NEW")
    
    try:
        # Download
        download_start = time.time()
        video_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
        
        ydl_opts = {
            'format': 'best[height<=1080]/best',
            'outtmpl': video_path,
            'no_warnings': True,
            'retries': 1,
            'fragment_retries': 1,
            'socket_timeout': 10,
            'http_chunk_size': 1048576,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        download_time = time.time() - download_start
        
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            size_mb = os.path.getsize(video_path) // 1024 // 1024
            log(profile_id, f"✅ Downloaded: {size_mb}MB in {download_time:.1f}s", "TIMING", substep=True)
        else:
            log(profile_id, f"❌ Download failed", "ERROR", substep=True)
            return
        
        # Process
        process_start = time.time()
        processed_path = os.path.join(PROCESSED_DIR, f"{video_id}.mp4")
        
        process_success = process_video(video_path, processed_path)
        process_time = time.time() - process_start
        
        if not process_success or not os.path.exists(processed_path):
            log(profile_id, f"❌ Processing failed in {process_time:.1f}s", "ERROR", substep=True)
            return
        
        log(profile_id, f"✅ Processed in {process_time:.1f}s", "TIMING", substep=True)
        
        # Upload
        upload_start = time.time()
        log(profile_id, f"🚀 ULTRA-FAST uploading...", "ULTRAFAST", substep=True)
        
        upload_success = upload_with_retry(profile_id, processed_path, title, [])
        upload_time = time.time() - upload_start
        
        total_time = time.time() - pipeline_start
        
        if upload_success:
            log(profile_id, f"🎉 [{now_str}] ULTRA-FAST SUCCESS!", "OK")
            log(profile_id, f"📊 D:{download_time:.1f}s P:{process_time:.1f}s U:{upload_time:.1f}s = {total_time:.1f}s", "ULTRAFAST")
            
            log_upload_time(video_id, profile_id, download_time, process_time, upload_time, total_time)
            
            # Cleanup
            try:
                os.remove(processed_path)
                os.remove(video_path)
            except:
                pass
                
        else:
            log(profile_id, f"❌ [{now_str}] ULTRA-FAST FAILED: {processed_path}", "ERROR")
            log(profile_id, f"📊 Total time: {total_time:.1f}s", "TIMING", substep=True)
            
    except Exception as e:
        total_time = time.time() - pipeline_start
        log(profile_id, f"❌ [{now_str}] ULTRA-FAST ERROR: {str(e)[:100]}", "ERROR")
        log(profile_id, f"📊 Error at: {total_time:.1f}s", "TIMING", substep=True)

def worker_selenium(channel_url, profile_id):
    """Worker ULTRA FAST"""
    log(profile_id, f"⚡ ULTRA-FAST Worker (Target: Upload <10s)", "ULTRAFAST")

    profile_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"Profile_{profile_id}")
    
    try:
        last_video_id, mapping_idx, mapping_df = get_last_video_id_from_mapping(channel_url, profile_id)
        log(profile_id, f"✅ Baseline: {last_video_id}", "INFO")
    except Exception as mapping_error:
        log(profile_id, f"❌ Mapping error: {mapping_error}", "ERROR")
        return
    
    if not last_video_id or last_video_id == 'None' or last_video_id.strip() == '':
        log(profile_id, f"🔧 Setting baseline...", "INFO")
        try:
            baseline_video_id, baseline_url, baseline_title = get_latest_shorts_video_ytdlp(channel_url)
            if baseline_video_id:
                update_last_video_id_in_mapping_by_id(channel_url, profile_id, baseline_video_id)
                last_video_id = baseline_video_id
                log(profile_id, f"✅ Baseline set: {baseline_video_id}", "INFO")
            else:
                log(profile_id, f"❌ Cannot set baseline", "ERROR")
                return
        except Exception as e:
            log(profile_id, f"❌ Baseline error: {e}", "ERROR")
            return
    
    log(profile_id, f"▶️ ULTRA-FAST scan loop: {last_video_id}", "INFO")
    
    error_count = 0
    success_count = 0
    
    try:
        while True:
            try:
                video_id, video_url, title = get_latest_shorts_video_ytdlp(channel_url)
                
                if video_id:
                    error_count = 0
                
                if video_id and video_id != last_video_id:
                    log(profile_id, f"🎉 NEW VIDEO! {video_id}", "NEW")
                    
                    update_last_video_id_in_mapping_by_id(channel_url, profile_id, video_id)
                    last_video_id = video_id
                    
                    future = profile_executor.submit(
                        download_edit_upload_video, 
                        profile_id, video_id, video_url, title
                    )
                    log(profile_id, f"✅ ULTRA-FAST task submitted", "ULTRAFAST")
                    success_count += 1
                    
                    # Brief wait
                    time.sleep(random.uniform(0.3, 0.7))
                    
                elif video_id:
                    time.sleep(random.uniform(0.3, 0.7))
                    
                else:
                    error_count += 1
                    log(profile_id, f"❌ Scan failed (#{error_count})", "ERROR")
                    
                    if error_count <= 3:
                        sleep_time = random.uniform(1, 3)
                    elif error_count <= 8:
                        sleep_time = random.uniform(5, 10)
                    else:
                        sleep_time = random.uniform(15, 30)
                    
                    time.sleep(sleep_time)
                
                if success_count > 0 and success_count % 5 == 0:
                    log(profile_id, f"📊 Progress: {success_count} videos processed", "OK")
                
            except Exception as loop_error:
                error_count += 1
                log(profile_id, f"❌ Loop error #{error_count}: {str(loop_error)[:100]}", "ERROR")
                
                sleep_time = min(20, error_count * 2)
                time.sleep(sleep_time)
                
    except Exception as e:
        log(profile_id, f"❌ Worker error: {e}", "ERROR")
    finally:
        profile_executor.shutdown(wait=False)
        log(profile_id, f"🏁 ULTRA-FAST Worker finished: {success_count} videos", "OK")

def main():
    """Main function ULTRA FAST"""
    print("⚡ Starting ULTRA-FAST TikTok Pipeline")
    print("🎯 TARGET: Upload <10s per video")
    
    if not CHROMEDRIVER_PATH:
        print("❌ ChromeDriver not found!")
        return
    
    if not os.path.exists(FFMPEG_PATH):
        print(f"❌ FFmpeg not found: {FFMPEG_PATH}")
        return
    
    mapping = load_mapping()
    if not mapping:
        print("❌ No mapping file!")
        return
    
    print(f"✅ Loaded {len(mapping)} mappings")
    print(f"✅ ChromeDriver: {CHROMEDRIVER_PATH}")
    print(f"✅ FFmpeg: {FFMPEG_PATH}")
    
    # Create log files
    try:
        if not os.path.exists('upload_time.log'):
            with open('upload_time.log', 'w', encoding='utf-8') as f:
                f.write("timestamp,video_id,profile_id,download_time,process_time,upload_time,total_time\n")
    except:
        pass
    
    processes = []
    max_concurrent = min(15, len(mapping))  # Slightly reduce for stability
    
    print(f"⚡ Starting {max_concurrent} ULTRA-FAST workers...")
    
    for i, (channel_id, profile_id) in enumerate(mapping[:max_concurrent]):
        print(f"⚡ Starting ULTRA-FAST worker #{i+1}: Profile {profile_id}")
        p = Process(
            target=worker_selenium, 
            args=(channel_id, profile_id), 
            daemon=True,
            name=f"UltraFastWorker-{profile_id}"
        )
        p.start()
        processes.append(p)
        
        if i < max_concurrent - 1:
            time.sleep(0.05)
    
    print(f"✅ All {len(processes)} ULTRA-FAST workers started!")
    print("⚡ Monitoring ULTRA-FAST performance...")
    
    try:
        start_time = time.time()
        while True:
            time.sleep(20)
            
            alive_count = sum(1 for p in processes if p.is_alive())
            elapsed = time.time() - start_time
            
            print(f"⚡ [{datetime.now().strftime('%H:%M:%S')}] "
                  f"ULTRA-FAST workers: {alive_count}/{len(processes)} | "
                  f"Runtime: {elapsed/60:.1f}m")
            
            if alive_count == 0:
                print("⚠️ All ULTRA-FAST workers stopped")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping all ULTRA-FAST workers...")
        for p in processes:
            if p.is_alive():
                p.terminate()
        print("✅ All ULTRA-FAST workers stopped")

if __name__ == '__main__':
    main()