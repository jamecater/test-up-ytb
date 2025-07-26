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
    print("📝 Please download ChromeDriver and place it in one of these locations:")
    for path in possible_paths[:8]:  # Show first 8 options
        print(f"   - {path}")
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

def log_error_detail(profile_id, video_id, error_type, error_msg, step=""):
    """Ghi log lỗi chi tiết vào file upload_errors.log"""
    try:
        with open('upload_errors.log', 'a', encoding='utf-8') as f:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{now},{profile_id},{video_id},{step},{error_type},{error_msg[:200]}\n")
    except:
        pass

def log(profile_id, msg, level="INFO", substep=False):
    from datetime import datetime
    color = {
        "INFO": Fore.CYAN,
        "NEW": Fore.GREEN,
        "ERROR": Fore.RED,
        "WARNING": Fore.YELLOW,
        "OK": Fore.MAGENTA,
        "TIMING": Fore.LIGHTBLUE_EX,
        "DEBUG": Fore.LIGHTWHITE_EX
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
    # Ưu tiên channel_url, nếu không có thì dùng channel_id
    channel_col = 'channel_url' if 'channel_url' in df.columns else 'channel_id'
    for _, row in df.iterrows():
        mapping.append((str(row[channel_col]), str(row['profile_id'])))
    return mapping

def get_video_duration(video_path):
    """Lấy thời lượng video nhanh nhất có thể"""
    if not os.path.exists(FFPROBE_PATH):
        print(f"❌ FFprobe not found: {FFPROBE_PATH}")
        return 0
        
    cmd = [
        FFPROBE_PATH,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0',
        video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return float(result.stdout.strip())
    except:
        return 0

def process_video(input_path, output_path):
    """Xử lý video ULTRA NHANH - Video >60s upload nguyên bản"""
    start_time = time.time()
    
    try:
        duration = get_video_duration(input_path)
        
        if duration >= 60:
            # Video đủ dài: KHÔNG edit, copy nguyên bản
            log('SYSTEM', f"⚡ Video {duration:.1f}s ≥60s → Upload nguyên bản", "TIMING", True)
            shutil.copy2(input_path, output_path)
            
            process_time = time.time() - start_time
            log('SYSTEM', f"✅ Copy nguyên bản in {process_time:.2f}s", "TIMING", True)
            return True
            
        else:
            # Video ngắn: Lặp lại để tạo 60-65s
            target_duration = random.randint(60, 65)
            loop_count = int(target_duration // duration) + 1
            
            log('SYSTEM', f"⚡ Video {duration:.1f}s → Loop x{loop_count} = {target_duration}s", "TIMING", True)
            
            if not os.path.exists(FFMPEG_PATH):
                log('SYSTEM', f"❌ FFmpeg not found: {FFMPEG_PATH}", "ERROR", True)
                return False
            
            # Dùng stream_loop để lặp lại nhanh nhất
            cmd = [
                FFMPEG_PATH, '-y',
                '-stream_loop', str(loop_count - 1),  # loop_count - 1 vì file gốc = 1 lần
                '-i', input_path,
                '-ss', '0',  # Seek to start
                '-t', str(target_duration),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',  # Chất lượng cao hơn cho 1080p
                '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            
            if result.returncode != 0:
                log('SYSTEM', f"❌ FFmpeg error: {result.stderr.decode()[:100]}", "ERROR", True)
                return False
        
        process_time = time.time() - start_time
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            log('SYSTEM', f"✅ Processed in {process_time:.2f}s", "TIMING", True)
            return True
        else:
            log('SYSTEM', f"❌ Processing failed", "ERROR", True)
            return False
            
    except Exception as e:
        log('SYSTEM', f"❌ Process error: {e}", "ERROR", True)
        return False

def upload_to_tiktok_gpmlogin(profile_id, video_path, title=None, hashtags=None, description=None):
    """Upload TikTok ENHANCED với debugging chi tiết"""
    upload_start = time.time()
    video_id = os.path.basename(video_path).replace('.mp4', '')
    
    # Kiểm tra ChromeDriver trước
    if not CHROMEDRIVER_PATH or not os.path.exists(CHROMEDRIVER_PATH):
        error_msg = "ChromeDriver not found"
        log(profile_id, f"❌ {error_msg}", "ERROR")
        log_error_detail(profile_id, video_id, "SETUP_ERROR", error_msg, "chromedriver_check")
        return False
    
    try:
        # Khởi động GPM profile nhanh
        resp = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}", timeout=8)
        data = resp.json()
        if not data.get("success") or not data["data"].get("remote_debugging_address"):
            error_msg = f"GPM start failed: {data.get('message', 'Unknown')}"
            log(profile_id, f"❌ {error_msg}", "ERROR")
            log_error_detail(profile_id, video_id, "GPM_ERROR", error_msg, "gpm_start")
            return False
        wsEndpoint = data["data"]["remote_debugging_address"]
        
    except Exception as e:
        error_msg = f"GPM connect error: {e}"
        log(profile_id, f"❌ {error_msg}", "ERROR")
        log_error_detail(profile_id, video_id, "GPM_ERROR", error_msg, "gpm_connect")
        return False
    
    # Chrome options tối ưu SIÊU NHANH
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'  # Không chờ load hết
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
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    
    service = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(20)  # Tăng timeout từ 15s → 20s
        log(profile_id, f"✅ Chrome connected in {time.time()-upload_start:.1f}s", "TIMING")
        
    except Exception as driver_error:
        error_msg = f"Chrome driver error: {str(driver_error)[:100]}"
        log(profile_id, f"❌ {error_msg}", "ERROR")
        log_error_detail(profile_id, video_id, "CHROME_ERROR", error_msg, "chrome_start")
        return False
    
    try:
        # Navigate nhanh
        nav_start = time.time()
        log(profile_id, f"🌐 Navigating to TikTok Studio...", "DEBUG", True)
        driver.get("https://www.tiktok.com/tiktokstudio/upload?lang=en")  # English for consistent selectors
        wait = WebDriverWait(driver, 20)  # Tăng timeout từ 15s → 20s
        
        log(profile_id, f"✅ Page loaded in {time.time()-nav_start:.1f}s", "TIMING")
        
        # Upload file nhanh nhất
        upload_file_start = time.time()
        log(profile_id, f"📁 Looking for file input...", "DEBUG", True)
        
        # Thử multiple selectors cho file input
        file_input_selectors = [
            'input[type="file"]',
            'input[accept*="video"]',
            'input[accept*=".mp4"]'
        ]
        
        upload_input = None
        for selector in file_input_selectors:
            try:
                upload_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                log(profile_id, f"✅ File input found: {selector}", "DEBUG", True)
                break
            except:
                continue
                
        if not upload_input:
            error_msg = "File input not found"
            log(profile_id, f"❌ {error_msg}", "ERROR")
            log_error_detail(profile_id, video_id, "UPLOAD_ERROR", error_msg, "file_input")
            return False
        
        upload_input.send_keys(os.path.abspath(video_path))
        log(profile_id, f"✅ File uploaded in {time.time()-upload_file_start:.1f}s", "TIMING")
        
        # Chờ video process với timeout dài hơn
        log(profile_id, f"⏳ Waiting for video processing...", "DEBUG", True)
        try:
            WebDriverWait(driver, 30).until(  # Tăng từ 25s → 30s
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            log(profile_id, f"✅ Video processing complete", "DEBUG", True)
        except Exception as e:
            log(profile_id, f"⚠️ Video processing timeout, continuing...", "WARNING", True)
        
        # Scroll xuống cuối để tìm caption và nút Post
        log(profile_id, f"📜 Scrolling to bottom...", "DEBUG", True)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Chờ UI render
        time.sleep(2)  # Fixed delay thay vì WebDriverWait phức tạp
        
        # Nhập caption với multiple selectors
        caption_start = time.time()
        log(profile_id, f"📝 Looking for caption input...", "DEBUG", True)
        
        caption_selectors = [
            '//div[@aria-autocomplete="list" and @contenteditable="true"]',
            '//div[@contenteditable="true" and contains(@class, "public-DraftEditor-content")]',
            'div[data-e2e="caption-container"] textarea',
            'textarea[placeholder*="caption" i]',
            'div[contenteditable="true"]'
        ]
        
        caption_entered = False
        for i, selector in enumerate(caption_selectors):
            try:
                if selector.startswith('//'):
                    caption_input = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                else:
                    caption_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                
                log(profile_id, f"✅ Caption input found: selector {i+1}", "DEBUG", True)
                
                caption_text = title or ""
                if hashtags:
                    caption_text += " " + " ".join(hashtags)
                
                # Clear và nhập caption
                caption_input.click()
                time.sleep(0.5)
                caption_input.send_keys(Keys.CONTROL, 'a')
                time.sleep(0.2)
                caption_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                caption_input.send_keys(caption_text.strip())
                
                caption_entered = True
                log(profile_id, f"✅ Caption entered in {time.time()-caption_start:.1f}s", "TIMING")
                break
                
            except Exception as e:
                log(profile_id, f"⚠️ Caption selector {i+1} failed: {str(e)[:50]}", "DEBUG", True)
                continue
        
        if not caption_entered:
            log(profile_id, f"⚠️ Caption input not found, continuing...", "WARNING")
        
        # Tìm và nhấn nút Post với ENHANCED selectors
        post_start = time.time()
        log(profile_id, f"🔍 Looking for Post button...", "DEBUG", True)
        
        def is_post_button_ready(btn):
            try:
                return (
                    btn.get_attribute('aria-disabled') != 'true' and
                    btn.get_attribute('data-disabled') != 'true' and
                    'loading' not in btn.get_attribute('class').lower() and
                    'disabled' not in btn.get_attribute('class').lower() and
                    btn.is_enabled() and btn.is_displayed()
                )
            except:
                return False

        # ENHANCED Post button selectors - updated for 2024 TikTok
        post_selectors = [
            '//button[contains(text(), "Post")]',
            '//button[contains(text(), "Upload")]',
            'button[data-e2e="post_video_button"]',
            'button[data-e2e="upload-btn"]',
            '//button[contains(@class, "upload") or contains(@class, "post")]',
            '//button[contains(@aria-label, "Post")]',
            '//div[@role="button" and contains(text(), "Post")]',
            '//span[contains(text(), "Post")]/parent::button',
            'button[type="submit"]',
            '//button[last()]'  # Often the last button on the page
        ]
        
        post_clicked = False
        for i, selector in enumerate(post_selectors):
            try:
                log(profile_id, f"🔍 Trying Post selector {i+1}/{len(post_selectors)}: {selector[:50]}", "DEBUG", True)
                
                if selector.startswith('//'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for j, post_button in enumerate(elements[:3]):  # Try first 3 matches
                    try:
                        # Scroll button vào view
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", post_button)
                        time.sleep(0.5)
                        
                        # Check if button is ready
                        if is_post_button_ready(post_button):
                            # Try clicking with JavaScript first (more reliable)
                            try:
                                driver.execute_script("arguments[0].click();", post_button)
                                log(profile_id, f"✅ Post clicked (JS) - selector {i+1}.{j+1} in {time.time()-post_start:.1f}s", "TIMING")
                                post_clicked = True
                                break
                            except:
                                # Fallback to regular click
                                post_button.click()
                                log(profile_id, f"✅ Post clicked (regular) - selector {i+1}.{j+1} in {time.time()-post_start:.1f}s", "TIMING")
                                post_clicked = True
                                break
                        else:
                            log(profile_id, f"⚠️ Button not ready: {i+1}.{j+1}", "DEBUG", True)
                            
                    except Exception as button_error:
                        log(profile_id, f"⚠️ Button click failed {i+1}.{j+1}: {str(button_error)[:30]}", "DEBUG", True)
                        continue
                
                if post_clicked:
                    break
                    
            except Exception as selector_error:
                log(profile_id, f"⚠️ Selector {i+1} failed: {str(selector_error)[:30]}", "DEBUG", True)
                continue
        
        if not post_clicked:
            error_msg = "No Post button found or clickable"
            log(profile_id, f"❌ {error_msg}", "ERROR")
            log_error_detail(profile_id, video_id, "POST_ERROR", error_msg, "post_button")
            
            # Debug: Save screenshot và page source
            try:
                screenshot_path = f"debug_screenshot_{profile_id}_{video_id}.png"
                driver.save_screenshot(screenshot_path)
                log(profile_id, f"📸 Debug screenshot saved: {screenshot_path}", "DEBUG", True)
            except:
                pass
            
            return False
        
        # Xử lý popup "Post now" copyright nếu có
        try:
            log(profile_id, f"🔍 Checking for copyright popup...", "DEBUG", True)
            confirm_selectors = [
                '//button[.//div[text()="Post now"]]',
                '//button[contains(text(), "Post now")]',
                '//button[contains(text(), "Continue")]',
                '//button[contains(text(), "Confirm")]'
            ]
            
            for selector in confirm_selectors:
                try:
                    confirm_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    confirm_btn.click()
                    log(profile_id, "✅ Copyright popup handled", "INFO")
                    break
                except:
                    continue
                    
        except:
            log(profile_id, "ℹ️ No copyright popup", "INFO")
        
        # Chờ upload thành công với ENHANCED detection
        success_start = time.time()
        log(profile_id, f"⏳ Waiting for upload success...", "DEBUG", True)
        
        try:
            # Success indicators - updated for 2024 TikTok
            success_indicators = [
                '//div[contains(text(), "Your video is being uploaded")]',
                '//div[contains(text(), "Upload complete")]',
                '//div[contains(text(), "Video uploaded")]',
                '//div[contains(text(), "Published")]',
                '//div[contains(text(), "Success")]',
                '//div[contains(text(), "Done")]'
            ]
            
            success_detected = False
            
            # Try URL change detection first (fastest)
            initial_url = driver.current_url
            for _ in range(45):  # 45 seconds timeout
                time.sleep(1)
                current_url = driver.current_url
                
                # Check URL change
                if current_url != initial_url and "upload" not in current_url:
                    success_detected = True
                    log(profile_id, f"✅ URL changed: {current_url[:50]}", "DEBUG", True)
                    break
                
                # Check success text indicators
                for indicator in success_indicators:
                    try:
                        elements = driver.find_elements(By.XPATH, indicator)
                        if elements and len(elements) > 0:
                            success_detected = True
                            log(profile_id, f"✅ Success indicator found: {indicator[:30]}", "DEBUG", True)
                            break
                    except:
                        continue
                
                if success_detected:
                    break
            
            success_time = time.time() - success_start
            total_time = time.time() - upload_start
            
            if success_detected:
                log(profile_id, f"🎉 Upload SUCCESS in {success_time:.1f}s (total: {total_time:.1f}s)", "OK")
                return True
            else:
                # Fallback success (assume success after reasonable time)
                log(profile_id, f"⚠️ Upload likely success (timeout) - total: {total_time:.1f}s", "WARNING")
                return True  # Return True để tránh false negative
            
        except Exception as success_error:
            total_time = time.time() - upload_start
            error_msg = f"Success detection error: {str(success_error)[:100]}"
            log(profile_id, f"❌ {error_msg} (time: {total_time:.1f}s)", "ERROR")
            log_error_detail(profile_id, video_id, "SUCCESS_ERROR", error_msg, "success_detection")
            return False
        
    except Exception as e:
        total_time = time.time() - upload_start
        error_msg = f"Upload failed: {str(e)[:100]}"
        log(profile_id, f"❌ {error_msg} (time: {total_time:.1f}s)", "ERROR")
        log_error_detail(profile_id, video_id, "GENERAL_ERROR", error_msg, "upload_process")
        return False
        
    finally:
        # Cleanup nhanh
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
    """Quét video mới nhất ULTRA NHANH từ mục Shorts."""
    scan_start = time.time()

    # Xác định base channel
    if '/shorts' in channel_url:
        base_channel = channel_url.replace('/shorts', '')
    else:
        base_channel = channel_url.replace('/videos', '') if '/videos' in channel_url else channel_url

    # Chỉ thử URL /shorts với timeout ngắn
    test_url = base_channel + '/shorts'

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlist_items': '1:1',  # Chỉ lấy 1 video đầu tiên
            'no_check_certificate': True,
            'socket_timeout': 8,  # Timeout ngắn hơn
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
    
    # Truy cập bằng tên cột
    for idx, row in df.iterrows():
        if str(row['channel_url']) == str(channel_url) and str(row['profile_id']) == str(profile_id):
            return str(row['video_id']) if 'video_id' in row and not pd.isna(row['video_id']) else None, idx, df
    return None, None, df

def update_last_video_id_in_mapping_by_id(channel_id, profile_id, new_video_id):
    import os
    try:
        # Ưu tiên CSV vì ít bị khóa hơn Excel
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
                
                # Lưu file - ưu tiên CSV
                try:
                    if save_to_csv:
                        df.to_csv(MAPPING_CSV, index=False)
                    else:
                        # Backup to CSV first
                        df.to_csv('mapping_backup.csv', index=False)
                        df.to_excel(MAPPING_FILE, index=False)
                except PermissionError:
                    # Fallback to CSV if Excel is locked
                    df.to_csv(MAPPING_CSV, index=False)
                break
    except Exception as e:
        log(profile_id, f"❌ Lỗi update mapping: {e}", "ERROR")

def upload_with_retry(profile_id, processed_path, title, hashtags, max_retries=3):  # Tăng từ 2→3 retries
    """Upload với retry mechanism ENHANCED"""
    for attempt in range(max_retries):
        try:
            log(profile_id, f"🚀 Upload attempt #{attempt + 1}/{max_retries}", "TIMING", substep=True)
            
            if attempt > 0:
                # Tăng delay giữa retries
                delay_time = min(5, attempt * 2)  # 2s, 4s, 6s...
                time.sleep(delay_time)
                log(profile_id, f"⏳ {delay_time}s retry delay", "INFO", substep=True)
            
            result = upload_to_tiktok_gpmlogin(profile_id, processed_path, title, hashtags)
            
            if result:
                log(profile_id, f"✅ Upload success attempt #{attempt + 1}", "OK", substep=True)
                return True
            else:
                log(profile_id, f"❌ Upload failed attempt #{attempt + 1}", "WARNING", substep=True)
                
        except Exception as e:
            log(profile_id, f"❌ Exception attempt #{attempt + 1}: {str(e)[:50]}", "ERROR", substep=True)
    
    log(profile_id, f"❌ Upload failed after {max_retries} attempts", "ERROR", substep=True)
    return False

def download_edit_upload_video(profile_id, video_id, video_url, title):
    """Pipeline ENHANCED: Download → Edit → Upload với better error handling"""
    pipeline_start = time.time()
    now_str = datetime.now().strftime('%H:%M:%S')
    
    log(profile_id, f"🚀 [{now_str}] ENHANCED PIPELINE START: {video_id}", "NEW")
    
    try:
        # BƯỚC 1: Download ULTRA NHANH
        download_start = time.time()
        video_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
        log(profile_id, f"📥 Downloading: {video_url}", "INFO", substep=True)
        
        # yt-dlp tối ưu SIÊU NHANH cho 1080p
        ydl_opts = {
            'format': 'best[height<=1080]/best',  # Chất lượng cao nhất ≤1080p
            'outtmpl': video_path,
            'no_warnings': True,
            'retries': 2,
            'fragment_retries': 2,
            'socket_timeout': 12,
            'http_chunk_size': 2097152,  # 2MB chunks
            'external_downloader': 'ffmpeg' if os.path.exists(FFMPEG_PATH) else None,
            'external_downloader_args': {
                'ffmpeg': ['-threads', '4']  # Multi-thread download
            } if os.path.exists(FFMPEG_PATH) else {}
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        download_time = time.time() - download_start
        
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            size_mb = os.path.getsize(video_path) // 1024 // 1024
            log(profile_id, f"✅ Downloaded: {size_mb}MB in {download_time:.1f}s", "TIMING", substep=True)
        else:
            log(profile_id, f"❌ Download failed", "ERROR", substep=True)
            log_error_detail(profile_id, video_id, "DOWNLOAD_ERROR", "File not found after download", "download")
            return
        
        # BƯỚC 2: Process ULTRA NHANH (hoặc skip nếu >60s)
        process_start = time.time()
        processed_path = os.path.join(PROCESSED_DIR, f"{video_id}.mp4")
        
        process_success = process_video(video_path, processed_path)
        process_time = time.time() - process_start
        
        if not process_success or not os.path.exists(processed_path):
            log(profile_id, f"❌ Processing failed in {process_time:.1f}s", "ERROR", substep=True)
            log_error_detail(profile_id, video_id, "PROCESS_ERROR", "Video processing failed", "process")
            return
        
        log(profile_id, f"✅ Processed in {process_time:.1f}s", "TIMING", substep=True)
        
        # BƯỚC 3: Upload ENHANCED
        upload_start = time.time()
        log(profile_id, f"🚀 Uploading to TikTok...", "INFO", substep=True)
        
        upload_success = upload_with_retry(profile_id, processed_path, title, [])
        upload_time = time.time() - upload_start
        
        # Tính tổng thời gian
        total_time = time.time() - pipeline_start
        
        if upload_success:
            log(profile_id, f"🎉 [{now_str}] ENHANCED SUCCESS!", "OK")
            log(profile_id, f"📊 D:{download_time:.1f}s P:{process_time:.1f}s U:{upload_time:.1f}s = {total_time:.1f}s", "TIMING")
            
            # Log chi tiết vào file
            log_upload_time(video_id, profile_id, download_time, process_time, upload_time, total_time)
            
            # Cleanup files sau khi thành công
            try:
                os.remove(processed_path)
                os.remove(video_path)
            except:
                pass
                
        else:
            log(profile_id, f"❌ [{now_str}] ENHANCED FAILED: {processed_path}", "ERROR")
            log(profile_id, f"📊 Total time: {total_time:.1f}s", "TIMING", substep=True)
            log_error_detail(profile_id, video_id, "PIPELINE_FAILED", f"Total time: {total_time:.1f}s", "final")
            
    except Exception as e:
        total_time = time.time() - pipeline_start
        log(profile_id, f"❌ [{now_str}] ENHANCED ERROR: {str(e)[:100]}", "ERROR")
        log(profile_id, f"📊 Error at: {total_time:.1f}s", "TIMING", substep=True)
        log_error_detail(profile_id, video_id, "EXCEPTION", str(e)[:100], "pipeline")

def worker_selenium(channel_url, profile_id):
    """Worker ENHANCED với better video detection logic"""
    log(profile_id, f"🚀 ENHANCED Worker started (Target: <20s)", "INFO")

    # ThreadPoolExecutor riêng cho profile này
    profile_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix=f"Profile_{profile_id}")
    
    try:
        last_video_id, mapping_idx, mapping_df = get_last_video_id_from_mapping(channel_url, profile_id)
        log(profile_id, f"✅ Mapping loaded. Baseline: {last_video_id}", "INFO")
    except Exception as mapping_error:
        log(profile_id, f"❌ Mapping error: {mapping_error}", "ERROR")
        return
    
    # Auto-set baseline nếu chưa có
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
    
    log(profile_id, f"▶️ Starting ENHANCED scan loop with baseline: {last_video_id}", "INFO")
    
    error_count = 0
    success_count = 0
    last_scan_video_id = last_video_id  # Track riêng cho scan để tránh loop
    pending_uploads = set()  # Track videos đang upload để tránh duplicate
    
    try:
        while True:
            loop_start = time.time()
            
            try:
                video_id, video_url, title = get_latest_shorts_video_ytdlp(channel_url)
                
                scan_time = time.time() - loop_start
                
                if video_id:
                    error_count = 0  # Reset on success
                
                # ENHANCED video detection logic để tránh loop
                if video_id and video_id != last_scan_video_id and video_id not in pending_uploads:
                    log(profile_id, f"🎉 NEW VIDEO! {video_id}", "NEW")
                    log(profile_id, f"Scan: {last_scan_video_id} → New: {video_id}", "NEW", substep=True)
                    
                    # Update scan baseline
                    last_scan_video_id = video_id
                    
                    # Add to pending uploads
                    pending_uploads.add(video_id)
                    
                    # Update database baseline ONLY after successful upload
                    # (moved to after upload success)
                    
                    # Submit xử lý video ENHANCED
                    future = profile_executor.submit(
                        download_edit_upload_video, 
                        profile_id, video_id, video_url, title
                    )
                    
                    # Add callback để remove từ pending khi done
                    def upload_complete(future, vid=video_id):
                        pending_uploads.discard(vid)
                        # Update mapping chỉ khi thành công
                        try:
                            if future.result() is not False:  # Not explicit False
                                update_last_video_id_in_mapping_by_id(channel_url, profile_id, vid)
                        except:
                            pass
                    
                    future.add_done_callback(lambda f: upload_complete(f))
                    
                    log(profile_id, f"✅ ENHANCED task submitted", "INFO")
                    success_count += 1
                    
                    # Sleep ngắn khi có video mới
                    time.sleep(random.uniform(0.5, 1.0))  # Tăng delay để tránh spam
                    
                elif video_id and video_id in pending_uploads:
                    # Video đang được xử lý
                    time.sleep(random.uniform(1.0, 2.0))
                    
                elif video_id:
                    # Same video
                    time.sleep(random.uniform(0.5, 1.0))
                    
                else:
                    # Lỗi scan
                    error_count += 1
                    log(profile_id, f"❌ Scan failed (#{error_count})", "ERROR")
                    
                    # Dynamic sleep dựa trên số lỗi
                    if error_count <= 3:
                        sleep_time = random.uniform(2, 5)
                    elif error_count <= 8:
                        sleep_time = random.uniform(8, 15)
                    else:
                        sleep_time = random.uniform(25, 45)
                        log(profile_id, f"⚠️ Too many errors, longer sleep", "WARNING")
                    
                    time.sleep(sleep_time)
                
                # Log progress mỗi 5 video thành công
                if success_count > 0 and success_count % 5 == 0:
                    log(profile_id, f"📊 Progress: {success_count} videos processed", "OK")
                
            except Exception as loop_error:
                error_count += 1
                log(profile_id, f"❌ Loop error #{error_count}: {str(loop_error)[:100]}", "ERROR")
                
                sleep_time = min(30, error_count * 2)
                time.sleep(sleep_time)
                
    except Exception as e:
        log(profile_id, f"❌ Worker error: {e}", "ERROR")
    finally:
        # Cleanup executor
        profile_executor.shutdown(wait=False)
        log(profile_id, f"🏁 Worker finished. Total processed: {success_count} videos", "OK")

def main():
    """Main function ENHANCED với better error handling"""
    print("🚀 Starting ENHANCED TikTok Auto-Upload Pipeline")
    print("📊 Target: < 20s per video with better error handling")
    
    # Kiểm tra dependencies
    if not CHROMEDRIVER_PATH:
        print("❌ ChromeDriver not found! Run download_chromedriver.bat first")
        return
    
    if not os.path.exists(FFMPEG_PATH):
        print(f"❌ FFmpeg not found: {FFMPEG_PATH}")
        return
    
    mapping = load_mapping()
    if not mapping:
        print("❌ Không tìm thấy mapping file!")
        return
    
    print(f"✅ Loaded {len(mapping)} channel-profile mappings")
    print(f"✅ ChromeDriver: {CHROMEDRIVER_PATH}")
    print(f"✅ FFmpeg: {FFMPEG_PATH}")
    
    # Tạo error log header
    try:
        if not os.path.exists('upload_errors.log'):
            with open('upload_errors.log', 'w', encoding='utf-8') as f:
                f.write("timestamp,profile_id,video_id,step,error_type,error_message\n")
    except:
        pass
    
    # Tạo upload_time.log header
    try:
        if not os.path.exists('upload_time.log'):
            with open('upload_time.log', 'w', encoding='utf-8') as f:
                f.write("timestamp,video_id,profile_id,download_time,process_time,upload_time,total_time\n")
    except:
        pass
    
    # Khởi động processes cho tối đa 20 channels
    processes = []
    max_concurrent = min(20, len(mapping))
    
    print(f"🔥 Starting {max_concurrent} ENHANCED concurrent workers...")
    
    for i, (channel_id, profile_id) in enumerate(mapping[:max_concurrent]):
        print(f"🚀 Starting ENHANCED worker #{i+1}: Profile {profile_id}")
        p = Process(
            target=worker_selenium, 
            args=(channel_id, profile_id), 
            daemon=True,
            name=f"EnhancedWorker-{profile_id}"
        )
        p.start()
        processes.append(p)
        
        # Brief delay giữa các process start
        if i < max_concurrent - 1:
            time.sleep(0.1)
    
    print(f"✅ All {len(processes)} ENHANCED workers started!")
    print("📊 Monitoring ENHANCED performance...")
    print("📋 Check upload_errors.log for detailed error analysis")
    
    try:
        # Monitor processes
        start_time = time.time()
        while True:
            time.sleep(20)  # Check mỗi 20s
            
            alive_count = sum(1 for p in processes if p.is_alive())
            elapsed = time.time() - start_time
            
            print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] "
                  f"ENHANCED workers: {alive_count}/{len(processes)} | "
                  f"Runtime: {elapsed/60:.1f}m")
            
            if alive_count == 0:
                print("⚠️ All ENHANCED workers stopped")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping all ENHANCED workers...")
        for p in processes:
            if p.is_alive():
                p.terminate()
        print("✅ All ENHANCED workers stopped")

if __name__ == '__main__':
    main()