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

# Chặn stderr (ẩn mọi warning/error từ Chrome, TensorFlow, v.v.)
sys.stderr = open(os.devnull, 'w')

init(autoreset=True)

# Chọn chế độ chạy: 'api' hoặc 'yt_dlp'
MODE = 'yt_dlp'  # hoặc 'yt_dlp'

DOWNLOAD_DIR = 'downloads'
PROCESSED_DIR = 'processed'
MAPPING_FILE = 'mapping.xlsx'
MAPPING_CSV = 'mapping.csv'
FFPROBE_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe'
FFMPEG_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'
CHROMEDRIVER_PATH = r'D:\Test up ytb\chromedriver.exe'

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename='activity.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

def log(profile_id, msg, level="INFO", substep=False):
    from datetime import datetime
    color = {
        "INFO": Fore.CYAN,
        "NEW": Fore.GREEN,
        "ERROR": Fore.RED,
        "WARNING": Fore.YELLOW,
        "OK": Fore.MAGENTA
    }.get(level, None)
    prefix = "   ↳ " if substep else ""
    if level == "INFO":
        now_str = datetime.now().strftime('%H:%M:%S')
        level_str = now_str
    else:
        level_str = level
    print(f"{color}{prefix}[{level_str}] [{profile_id}] {msg}{Style.RESET_ALL}")

def load_mapping():
    df = pd.read_excel(MAPPING_FILE)
    mapping = []
    # Ưu tiên channel_url, nếu không có thì dùng channel_id
    channel_col = 'channel_url' if 'channel_url' in df.columns else 'channel_id'
    for _, row in df.iterrows():
        mapping.append((str(row[channel_col]), str(row['profile_id'])))
    return mapping

def get_video_duration(video_path):
    cmd = [
        FFPROBE_PATH,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    return float(info['format']['duration'])

def process_video(input_path, output_path):
    duration = get_video_duration(input_path)
    target_duration = random.randint(60, 65)
    if duration >= 60:
        # Nếu đủ dài, chỉ cắt 60-65s đầu
        cmd = [
            FFMPEG_PATH, '-y',
            '-i', input_path,
            '-t', str(target_duration),
            '-c', 'copy',
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    # Nếu ngắn hơn 60s, nhân bản
    repeat_count = int(target_duration // duration) + 2  # +2 để chắc chắn đủ dài
    abs_input = os.path.abspath(input_path).replace('\\', '/')
    list_file = input_path + '_concat.txt'
    with open(list_file, 'w', encoding='utf-8') as f:
        for _ in range(repeat_count):
            f.write(f"file '{abs_input}'\n")
    temp_concat = input_path + '_concat.mp4'
    cmd_concat = [
        FFMPEG_PATH, '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        temp_concat
    ]
    result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not os.path.exists(temp_concat) or os.path.getsize(temp_concat) == 0:
        log('SYSTEM', f'Lỗi concat video: {temp_concat}\n{result.stderr.decode()}', 'ERROR', substep=True)
        os.remove(list_file)
        return
    # Cắt đúng target_duration
    cmd_cut = [
        FFMPEG_PATH, '-y',
        '-i', temp_concat,
        '-t', str(target_duration),
        '-c', 'copy',
        output_path
    ]
    subprocess.run(cmd_cut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(list_file)
    os.remove(temp_concat)

# Sửa hàm upload_to_tiktok_gpmlogin để nhận thêm title, hashtags

def upload_to_tiktok_gpmlogin(profile_id, video_path, title=None, hashtags=None, description=None):
    try:
        resp = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}")
        data = resp.json()
        if not data.get("success") or not data["data"].get("remote_debugging_address"):
            log(profile_id, f"Lỗi khởi động profile Gpmlogin: {data.get('message', 'Unknown error')}", "ERROR")
            return False
        wsEndpoint = data["data"]["remote_debugging_address"]
    except Exception as e:
        log(profile_id, f"Lỗi khởi động profile Gpmlogin: {e}", "ERROR")
        return False
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_experimental_option("debuggerAddress", wsEndpoint)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    service = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)  # 30s timeout cho page load
        log(profile_id, f"Đã kết nối profile {profile_id}", "INFO")
    except Exception as driver_error:
        log(profile_id, f"Lỗi kết nối Chrome driver: {driver_error}", "ERROR")
        return False
    try:
        driver.get("https://www.tiktok.com/tiktokstudio/upload?lang=jp")
        wait = WebDriverWait(driver, 15)
        
        # Upload video nhanh nhất có thể
        upload_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
        upload_input.send_keys(os.path.abspath(video_path))
        log(profile_id, "Đã gửi file vào input.", "INFO")
        
        # Chờ video load xong và scroll xuống để tìm các ô nhập liệu
        time.sleep(3)  # Chờ video load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.3)  # hoặc nhỏ hơn, chỉ cần trang kịp render nút Post
        # Nhập caption (mô tả) vào TikTok với xpath mới
        try:
            # Thử xpath mới cho tiêu đề video TikTok
            caption_input = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@aria-autocomplete="list" and @class="notranslate public-DraftEditor-content" and @contenteditable="true"]')))
            caption_text = title or ""
            if hashtags:
                caption_text += " " + " ".join(hashtags)
            caption_input.click()
            caption_input.send_keys(Keys.CONTROL, 'a')
            caption_input.send_keys(Keys.BACKSPACE)
            caption_input.send_keys(caption_text.strip())
            log(profile_id, f"Đã nhập caption với xpath mới: {caption_text.strip()}", "INFO")
        except Exception as e:
            # Fallback: thử xpath cũ
            try:
                caption_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-e2e="caption-container"] textarea')))
                caption_text = title or ""
                if hashtags:
                    caption_text += " " + " ".join(hashtags)
                caption_input.clear()
                caption_input.send_keys(caption_text.strip())
                log(profile_id, f"Đã nhập caption với xpath cũ: {caption_text.strip()}", "INFO")
            except Exception as e2:
                log(profile_id, f"Không tìm thấy ô nhập caption: {e2}", "WARNING")
        # Nhập Description nếu có
        if description:
            try:
                desc_input = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.public-DraftEditor-content[contenteditable="true"]')
                ))
                desc_input.click()
                desc_input.send_keys(Keys.CONTROL, 'a')
                desc_input.send_keys(Keys.BACKSPACE)
                # Loại bỏ emoji/icon khỏi description
                def remove_emoji(text):
                    emoji_pattern = re.compile(
                        "["
                        u"\U0001F600-\U0001F64F"  # emoticons
                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                        u"\U00002700-\U000027BF"  # Dingbats
                        u"\U000024C2-\U0001F251"  # Enclosed characters
                        "]+", flags=re.UNICODE)
                    return emoji_pattern.sub(r'', text)
                clean_description = remove_emoji(description.strip())
                desc_input.send_keys(clean_description)
                log(profile_id, f"Đã nhập Description: {clean_description}", "INFO")
            except Exception as e:
                log(profile_id, f"Không tìm thấy ô nhập Description: {e}", "WARNING")
        # Tìm và nhấn nút upload nhanh nhất có thể
        def is_post_button_ready(btn):
            try:
                aria_disabled = btn.get_attribute('aria-disabled')
                data_disabled = btn.get_attribute('data-disabled')
                class_attr = btn.get_attribute('class')
                return (
                    aria_disabled == 'false' and
                    data_disabled == 'false' and
                    'Button__root--loading-false' in class_attr and
                    'Button__root--loading-true' not in class_attr
                )
            except:
                return False

        try:
            # Thử tìm nút Upload video trước
            upload_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Upload video")]')))
            log(profile_id, "Tìm thấy nút Upload video, nhấn ngay!", "INFO")
            upload_btn.click()
        except:
            try:
                # Thử tìm nút Post với data-e2e
                post_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-e2e="post_video_button"]')))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", post_btn)
                WebDriverWait(driver, 30).until(lambda d: is_post_button_ready(post_btn))
                log(profile_id, "Tìm thấy nút Post, nút đã sáng, nhấn ngay!", "INFO")
                post_btn.click()
            except:
                # Thử tìm nút Post với text
                post_btn = wait.until(EC.presence_of_element_located((By.XPATH, '//button[contains(text(), "Post")]')))
                WebDriverWait(driver, 30).until(lambda d: is_post_button_ready(post_btn))
                log(profile_id, "Tìm thấy nút Post bằng text, nút đã sáng, nhấn ngay!", "INFO")
                post_btn.click()

        log(profile_id, "Đã nhấn nút upload!", "INFO")
        # Sau khi bấm Post, nếu hiện Post now trong 2s thì bấm luôn
        try:
            confirm_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//div[text()="Post now"]]'))
            )
            log(profile_id, "Phát hiện popup copyright, tự động nhấn 'Post now'", "INFO")
            confirm_btn.click()
            time.sleep(1)
        except Exception:
            log(profile_id, "Không xuất hiện popup copyright, tiếp tục bình thường.", "INFO")
        
        # Chờ upload hoàn tất - kiểm tra URL thay đổi hoặc element biến mất
        log(profile_id, "Đang chờ video đăng lên...", "INFO")
        try:
            WebDriverWait(driver, 60).until(lambda driver: driver.current_url != "https://www.tiktok.com/tiktokstudio/upload?lang=jp")
        except:
            # Fallback: chờ một thời gian cố định
            time.sleep(30)
        
        log(profile_id, "Video đã đăng thành công.", "OK")
        driver.quit()
        try:
            requests.get(f"http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}")
        except:
            pass
        return True
    except Exception as e:
        log(profile_id, f"Lỗi upload TikTok: {e}", "ERROR")
        # Safe cleanup khi có lỗi
        try:
            if 'driver' in locals():
                driver.quit()
        except Exception as cleanup_error:
            log(profile_id, f"Lỗi cleanup driver: {cleanup_error}", "WARNING")
        
        try:
            requests.get(f"http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}", timeout=5)
        except Exception as close_error:
            log(profile_id, f"Lỗi đóng GPM profile: {close_error}", "WARNING")
        
        return False

# Hàm download_video cũ - đã thay thế bằng logic mới trong download_edit_upload_video
def download_video(video_url, output_path):
    """Hàm cũ - chỉ giữ để tương thích - logic mới ở download_edit_upload_video"""
    pass

def download_latest_shorts(channel_url, return_id_and_recent=False):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlist_items': '1',
        'ffmpeg_location': r'C:\ffmpeg-7.1.1-essentials_build\bin',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info and info['entries']:
                latest = info['entries'][0]
                video_id = latest['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
                ydl_detail_opts = {'quiet': True, 'no_warnings': True, 'ffmpeg_location': r'C:\ffmpeg-7.1.1-essentials_build\bin'}
                with yt_dlp.YoutubeDL(ydl_detail_opts) as ydl2:
                    detail = ydl2.extract_info(video_url, download=False)
                    is_recent = False
                    timestamp = detail.get('timestamp', None)
                    if timestamp is not None:
                        now = int(time.time())
                        video_time = int(timestamp)
                        if now - video_time <= 120:
                            is_recent = True
                    # Lấy tiêu đề, mô tả và hashtag
                    title = detail.get('title', '')
                    description = detail.get('description', '')
                    hashtags = []
                    if 'tags' in detail and detail['tags']:
                        hashtags = [f"#{tag}" for tag in detail['tags'] if tag]
                    if os.path.exists(video_path):
                        if return_id_and_recent:
                            return None, video_id, is_recent, title, hashtags, description
                        return None
                    if is_recent:
                        ydl_download_opts = {
                            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
                            'outtmpl': video_path,
                            'quiet': True,
                            'no_warnings': True,
                            'ffmpeg_location': r'C:\ffmpeg-7.1.1-essentials_build\bin'
                        }
                        with yt_dlp.YoutubeDL(ydl_download_opts) as ydl3:
                            ydl3.download([video_url])
                        if os.path.exists(video_path):
                            if return_id_and_recent:
                                return video_path, video_id, is_recent, title, hashtags, description
                            return video_path
                    else:
                        if return_id_and_recent:
                            return None, video_id, is_recent, title, hashtags, description
                        return None
    except Exception as e:
        print(f"Lỗi tải video: {e}")
    if return_id_and_recent:
        return None, None, False, '', [], ''
    return None

def get_latest_shorts_video_ytdlp(channel_url):
    """Chỉ trả về video mới nhất từ mục Shorts."""
    import time

    # Xác định base channel
    if '/shorts' in channel_url:
        base_channel = channel_url.replace('/shorts', '')
    else:
        base_channel = channel_url.replace('/videos', '') if '/videos' in channel_url else channel_url

    # Chỉ thử URL /shorts
    urls_to_try = [
        base_channel + '/shorts',
    ]

    t_start = time.time()

    for test_url in urls_to_try:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlist_items': '1:1',  # Chỉ lấy 1 video đầu tiên
                'no_check_certificate': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)

                if 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    if entry and entry.get('id') and len(entry['id']) == 11:
                        video_id = entry['id']
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        title = entry.get('title', '')
                        t_end = time.time()
                        print(f"🚀 yt-dlp quét SIÊU NHANH trong {t_end-t_start:.2f}s (từ shorts)")
                        return video_id, video_url, title

        except Exception as e:
            t_end = time.time()
            print(f"❌ Không lấy được video từ /shorts sau {t_end-t_start:.2f}s: {str(e)[:100]}")
            return None, None, None

    t_end = time.time()
    print(f"🚀 yt-dlp quét trong {t_end-t_start:.2f}s - Không tìm thấy video")
    return None, None, None

def get_last_video_id_from_mapping(channel_url, profile_id):
    import os
    if os.path.exists(MAPPING_FILE):
        df = pd.read_excel(MAPPING_FILE)
        print(f"✅ Đã đọc từ {MAPPING_FILE}")
    elif os.path.exists(MAPPING_CSV):
        df = pd.read_csv(MAPPING_CSV)
        print(f"✅ Đã đọc từ {MAPPING_CSV}")
    else:
        print(f"❌ Không tìm thấy {MAPPING_FILE} hoặc {MAPPING_CSV}")
        return None, None, None
    
    print(f"🔍 Columns: {list(df.columns)}")
    print(f"🔍 Shape: {df.shape}")
    
    # Truy cập bằng tên cột
    for idx, row in df.iterrows():
        if str(row['channel_url']) == str(channel_url) and str(row['profile_id']) == str(profile_id):
            return str(row['video_id']) if 'video_id' in row and not pd.isna(row['video_id']) else None, idx, df
    return None, None, df

def update_last_video_id_in_mapping(idx, df, new_video_id):
    import os
    if 'video_id' not in df.columns:
        df['video_id'] = None
    df.at[idx, 'video_id'] = new_video_id
    # Lưu theo format gốc
    if os.path.exists(MAPPING_FILE):
        df.to_excel(MAPPING_FILE, index=False)
    else:
        df.to_csv(MAPPING_CSV, index=False)

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
                    log(profile_id, f"⚠️ Excel bị khóa, đã chuyển sang CSV", "WARN")
                break
    except Exception as e:
        log(profile_id, f"❌ Lỗi update mapping: {e}", "ERROR")

def get_last_video_id_from_mapping_by_id(channel_id, profile_id):
    import os
    if os.path.exists(MAPPING_FILE):
        df = pd.read_excel(MAPPING_FILE)
    elif os.path.exists(MAPPING_CSV):
        df = pd.read_csv(MAPPING_CSV)
    else:
        return None
    channel_col = 'channel_url' if 'channel_url' in df.columns else 'channel_id'
    for idx, row in df.iterrows():
        if str(row[channel_col]) == str(channel_id) and str(row['profile_id']) == str(profile_id):
            return str(row['video_id']) if 'video_id' in row and not pd.isna(row['video_id']) else None
    return None

def worker_selenium(channel_url, profile_id):
    log(profile_id, f"🚀 Worker started for profile {profile_id}, channel {channel_url} (yt-dlp SIÊU NHANH)", "INFO")

    try:
        last_video_id, mapping_idx, mapping_df = get_last_video_id_from_mapping(channel_url, profile_id)
        log(profile_id, f"Đã load mapping thành công. last_video_id: {last_video_id}", "INFO")
    except Exception as mapping_error:
        log(profile_id, f"Lỗi load mapping: {mapping_error}", "ERROR")
        return
    
    # 🆕 NẾU CHƯA CÓ VIDEO_ID BASELINE → TỰ ĐỘNG SET VIDEO MỚI NHẤT LÀM BASELINE
    if not last_video_id or last_video_id == 'None' or last_video_id.strip() == '':
        log(profile_id, f"🔧 Chưa có video_id baseline, tự động lấy video mới nhất làm baseline...", "INFO")
        try:
            baseline_video_id, baseline_url, baseline_title = get_latest_shorts_video_ytdlp(channel_url)
            if baseline_video_id:
                update_last_video_id_in_mapping_by_id(channel_url, profile_id, baseline_video_id)
                last_video_id = baseline_video_id
                log(profile_id, f"✅ Đã set baseline: {baseline_video_id} - {baseline_title}", "INFO")
                log(profile_id, f"⏳ Từ lần sau sẽ phát hiện video mới hơn baseline này", "INFO")
            else:
                log(profile_id, f"❌ Không thể lấy video baseline", "ERROR")
                return
        except Exception as e:
            log(profile_id, f"❌ Lỗi set baseline: {e}", "ERROR")
            return
    
    log(profile_id, f"▶️ Bắt đầu vòng lặp quét với baseline: {last_video_id}", "INFO")
    
    error_count = 0  # Đếm số lỗi liên tiếp
    
    try:
        import time
        while True:
            try:
                t0 = time.time()
                log(profile_id, "🚀 Đang quét video mới nhất bằng yt-dlp...", "INFO")
                video_id, video_url, title = get_latest_shorts_video_ytdlp(channel_url)
                t1 = time.time()
                log(profile_id, f"⚡ Thời gian quét: {t1-t0:.2f}s | video_id: {video_id}", "INFO")
                
                # Reset error count nếu quét thành công
                if video_id:
                    error_count = 0
                
                # So sánh video_id hiện tại với baseline
                if video_id and video_id != last_video_id:
                    log(profile_id, f"🎉 PHÁT HIỆN VIDEO MỚI!", "NEW")
                    log(profile_id, f"   📊 Baseline: {last_video_id}", "NEW", substep=True)
                    log(profile_id, f"   🆕 Video mới: {video_id}", "NEW", substep=True)
                    log(profile_id, f"   🔗 URL: {video_url}", "NEW", substep=True)
                    log(profile_id, f"   📝 Title: {title}", "NEW", substep=True)
                    
                    # Cập nhật baseline mới
                    update_last_video_id_in_mapping_by_id(channel_url, profile_id, video_id)
                    last_video_id = video_id  # Cập nhật ngay tại đây!
                    
                    # Xử lý video SIÊU NHANH trong background
                    log(profile_id, f"🚀 Bắt đầu xử lý video {video_id} (Tải→Edit→Upload GPM)...", "INFO")
                    future = edit_upload_pool.submit(download_edit_upload_video, profile_id, video_id, video_url, title)
                    log(profile_id, f"✅ Đã submit task xử lý video vào queue", "INFO")
                    
                    # Sleep ngắn khi có video mới
                    time.sleep(random.uniform(0.5, 1.0))
                    
                elif video_id:
                    log(profile_id, f"⏸️ Video hiện tại giống baseline: {video_id}", "INFO")
                    # Sleep ngắn khi video giống baseline
                    time.sleep(random.uniform(0.5, 1.0))
                    
                else:
                    # Không lấy được video_id = LỖI
                    error_count += 1
                    log(profile_id, f"❌ Không lấy được video_id (lỗi #{error_count})", "ERROR")
                    
                    # SMART SLEEP: Sleep lâu dần khi lỗi nhiều lần
                    if error_count <= 3:
                        sleep_time = random.uniform(2, 5)  # Lỗi ít: 2-5s
                    elif error_count <= 10:
                        sleep_time = random.uniform(10, 20)  # Lỗi nhiều: 10-20s
                    else:
                        sleep_time = random.uniform(30, 60)  # Lỗi rất nhiều: 30-60s
                        log(profile_id, f"⚠️ Channel có vấn đề, sleep lâu để tránh spam", "WARN")
                    
                    log(profile_id, f"💤 Sleep {sleep_time:.1f}s do lỗi...", "INFO")
                    time.sleep(sleep_time)
                
            except Exception as loop_error:
                error_count += 1
                log(profile_id, f"❌ Lỗi trong vòng lặp quét (#{error_count}): {loop_error}", "ERROR")
                
                # Sleep lâu khi có exception
                sleep_time = min(30, error_count * 2)  # Tối đa 30s
                log(profile_id, f"💤 Sleep {sleep_time}s do exception...", "INFO")
                time.sleep(sleep_time)
                
    except Exception as e:
        log(profile_id, f"❌ Lỗi: {e}", "ERROR")

# Tạo ThreadPoolExecutor toàn cục cho edit+upload - TĂNG LÊN 20 để xử lý SIÊU NHANH
edit_upload_pool = ThreadPoolExecutor(max_workers=20)

def upload_with_retry(profile_id, processed_path, title, hashtags, max_retries=2):
    """Upload với retry mechanism để handle Chrome crashes"""
    for attempt in range(max_retries):
        try:
            log(profile_id, f"🚀 Upload attempt #{attempt + 1}/{max_retries}", "INFO", substep=True)
            
            # Thêm delay nhỏ giữa các lần retry để Chrome recover
            if attempt > 0:
                import time
                time.sleep(5)  # Wait 5s before retry
                log(profile_id, f"⏳ Chờ 5s trước khi retry...", "INFO", substep=True)
            
            result = upload_to_tiktok_gpmlogin(profile_id, processed_path, title, hashtags)
            
            if result:
                log(profile_id, f"✅ Upload thành công ở attempt #{attempt + 1}", "INFO", substep=True)
                return True
            else:
                log(profile_id, f"❌ Upload failed attempt #{attempt + 1}", "WARNING", substep=True)
                
        except Exception as e:
            log(profile_id, f"❌ Exception ở attempt #{attempt + 1}: {e}", "ERROR", substep=True)
    
    log(profile_id, f"❌ Upload thất bại sau {max_retries} attempts", "ERROR", substep=True)
    return False

def download_edit_upload_video(profile_id, video_id, video_url, title):
    """Download → Edit → Upload video SIÊU NHANH"""
    import time
    from datetime import datetime
    
    start_time = time.time()
    now_str = datetime.now().strftime('%H:%M:%S')
    
    try:
        # Bước 1: Download video
        video_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
        log(profile_id, f"📥 Đang tải video: {video_url}", "INFO", substep=True)
        
        # Sử dụng yt-dlp để download với chất lượng thấp để nhanh
        ydl_opts = {
            'format': 'worst[height<=1080]/worst',  # Chất lượng thấp để nhanh nhất
            'outtmpl': video_path,
            'quiet': True,
            'no_warnings': True,
            'retries': 3,  # Chỉ 3 retry thay vì 10
            'fragment_retries': 3,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        t_download = time.time()
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            log(profile_id, f"✅ Đã tải xong: {os.path.getsize(video_path)//1024//1024}MB trong {t_download-start_time:.1f}s", "INFO", substep=True)
        else:
            log(profile_id, f"❌ Lỗi tải video: File không tồn tại hoặc rỗng", "ERROR", substep=True)
            return
        
        # Bước 2: Edit video SIÊU NHANH
        processed_path = os.path.join(PROCESSED_DIR, f"{video_id}.mp4")
        log(profile_id, f"⚡ Đang edit video SIÊU NHANH...", "INFO", substep=True)
        
        process_video(video_path, processed_path)
        
        t_edit = time.time()
        if os.path.exists(processed_path) and os.path.getsize(processed_path) > 0:
            log(profile_id, f"✅ Đã edit xong trong {t_edit-t_download:.1f}s", "INFO", substep=True)
        else:
            log(profile_id, f"❌ Lỗi edit video: File không tồn tại", "ERROR", substep=True)
            return
        
        # Bước 3: Upload lên TikTok với retry
        log(profile_id, f"🚀 Mở GPM profile để upload...", "INFO", substep=True)
        upload_success = upload_with_retry(profile_id, processed_path, title, [])
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        if upload_success:
            log(profile_id, f"🎉 [{now_str}] HOÀN THÀNH! Tổng thời gian: {elapsed:.1f}s", "INFO", substep=True)
        else:
            log(profile_id, f"❌ [{now_str}] Lỗi upload video: {processed_path} | Tổng thời gian: {elapsed:.1f}s", "ERROR", substep=True)
            
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        log(profile_id, f"❌ [{now_str}] Lỗi xử lý video {video_id}: {e} | Thời gian: {elapsed:.1f}s", "ERROR", substep=True)

def edit_and_upload(profile_id, video_path, processed_path, title, hashtags, start_time, description=None):
    t_edit_start = time.time()
    process_video(video_path, processed_path)
    t_edit_end = time.time()
    log('SYSTEM', f"Đã xử lý xong video: {processed_path} (edit_time: {t_edit_end-t_edit_start:.2f}s)", "INFO", substep=True)
    # Upload ngay sau khi xử lý xong
    log(profile_id, f"Đang upload video: {processed_path}", "INFO", substep=True)
    upload_success = upload_to_tiktok_gpmlogin(profile_id, processed_path, title, hashtags, description)
    end_time = time.time()
    elapsed = end_time - start_time
    from datetime import datetime
    now_str = datetime.now().strftime('%H:%M:%S')
    if upload_success:
        log(profile_id, f"[{now_str}] Đã upload xong video: {processed_path} | Tổng thời gian: {elapsed:.2f} giây", "INFO", substep=True)
    else:
        log(profile_id, f"[{now_str}] Lỗi upload video: {processed_path} | Tổng thời gian: {elapsed:.2f} giây", "ERROR", substep=True)

# Đã loại bỏ worker_ytdlp cũ - chỉ dùng worker_selenium với yt-dlp mới

def main():
    mapping = load_mapping()
    if not mapping:
        print("Không tìm thấy mapping hoặc file mapping.xlsx bị lỗi!")
        return
    # Bỏ hoàn toàn phần xử lý lại video đã tải về trong downloads/
    # Chỉ khởi động các worker cho từng channel/profile
    processes = []
    for channel_id, profile_id in mapping:
        p = Process(target=worker_selenium, args=(channel_id, profile_id), daemon=True)
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

if __name__ == '__main__':
    main()
