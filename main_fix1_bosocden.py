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

init(autoreset=True)

# Chọn chế độ chạy: 'api' hoặc 'yt_dlp'
MODE = 'yt_dlp'  # hoặc 'yt_dlp'
# Nếu dùng API, có thể thêm nhiều key để tự động chuyển khi quotaExceeded
API_KEYS = [
    'AIzaSyDmotQwBdqNQKLaiC7RZp_PwK8glkuPKOI',
    # Thêm key khác nếu có
]

DOWNLOAD_DIR = 'downloads'
PROCESSED_DIR = 'processed'
MAPPING_FILE = 'mapping.xlsx'
FFPROBE_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe'
FFMPEG_PATH = r'C:\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'
CHROMEDRIVER_PATH = r'C:\Users\Administrator\Desktop\Test up ytb\chromedriver.exe'

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    filename='activity.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

def log(profile, msg, step=None):
    now = datetime.now().strftime('%H:%M:%S')
    color = {
        "START": Fore.CYAN,
        "PROCESS": Fore.YELLOW,
        "UPLOAD": Fore.MAGENTA,
        "DONE": Fore.GREEN,
        "ERROR": Fore.RED,
        "INFO": Fore.WHITE
    }.get(step, Fore.WHITE)
    emoji = {
        "START": "*",
        "PROCESS": "~",
        "UPLOAD": "^",
        "DONE": "+",
        "ERROR": "!",
        "INFO": "i"
    }
    step_str = f"[{step}]" if step else ""
    print(f"{color}[{now}] [{profile}] {step_str} {emoji.get(step, '')} {msg}{Style.RESET_ALL}")

def load_mapping():
    df = pd.read_excel(MAPPING_FILE)
    mapping = []
    for _, row in df.iterrows():
        # Có thể là channel_id hoặc youtube_url tùy file mapping
        mapping.append((str(row.get('channel_id', row.get('youtube_url'))), str(row['profile_id'])))
    return mapping

def process_video(input_path, output_path):
    probe = subprocess.run([
        FFPROBE_PATH, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height,duration', '-of', 'json', input_path
    ], stdout=subprocess.PIPE)
    import json, math
    info = json.loads(probe.stdout)
    duration = float(info['streams'][0]['duration'])
    if duration < 59.9:
        random_duration = random.randint(60, 65)
        loop_count = math.ceil(random_duration / duration) - 1
        cmd = [
            FFMPEG_PATH, "-y",
            "-stream_loop", str(loop_count),
            "-i", input_path,
            "-t", str(random_duration),
            "-c", "copy",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", input_path,
            "-t", "60",
            "-c", "copy",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Sửa hàm upload_to_tiktok_gpmlogin để nhận thêm title, hashtags

def upload_to_tiktok_gpmlogin(profile_id, video_path, title=None, hashtags=None):
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
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    log(profile_id, f"Đã kết nối profile {profile_id}", "INFO")
    try:
        driver.get("https://www.tiktok.com/tiktokstudio/upload?lang=vi")
        wait = WebDriverWait(driver, 15)
        upload_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
        upload_input.send_keys(os.path.abspath(video_path))
        log(profile_id, "Đã gửi file vào input.", "INFO")
        # Đợi caption input xuất hiện và nhập tiêu đề + hashtag
        try:
            caption_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-e2e="caption-container"] textarea')))
            caption_text = title or ""
            if hashtags:
                caption_text += " " + " ".join(hashtags)
            caption_input.clear()
            caption_input.send_keys(caption_text.strip())
            log(profile_id, f"Đã nhập caption: {caption_text.strip()}", "INFO")
        except Exception as e:
            log(profile_id, f"Không tìm thấy ô nhập caption: {e}", "ERROR")
        post_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-e2e="post_video_button"]')))
        log(profile_id, "Nút Post đã sẵn sàng.", "INFO")
        try:
            turn_on_btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Turn on")]')))
            turn_on_btn.click()
        except:
            pass
        post_btn.click()
        log(profile_id, "Đã nhấn nút Post!", "INFO")
        import time
        try:
            confirm_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//div[text()="Post now"]]'))
            )
            log(profile_id, "Phát hiện popup copyright, tự động nhấn 'Post now'", "INFO")
            confirm_btn.click()
            time.sleep(1)
        except Exception:
            log(profile_id, "Không xuất hiện popup copyright, tiếp tục bình thường.", "INFO")
        log(profile_id, "Đang chờ video đăng lên...", "INFO")
        WebDriverWait(driver, 60).until(EC.staleness_of(post_btn))
        log(profile_id, "Video đã đăng thành công.", "INFO")
        driver.quit()
        try:
            requests.get(f"http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}")
        except:
            pass
        return True
    except Exception as e:
        log(profile_id, f"Lỗi upload TikTok: {e}", "ERROR")
        driver.quit()
        try:
            requests.get(f"http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}")
        except:
            pass
        return False

def get_latest_shorts_api(channel_id, last_video_id=None, max_results=5, api_keys=None):
    if api_keys is None:
        api_keys = API_KEYS
    for api_key in api_keys:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
            req = youtube.search().list(
                part='snippet',
                channelId=channel_id,
                maxResults=max_results,
                order='date',
                type='video'
            )
            res = req.execute()
            video_ids = [item['id']['videoId'] for item in res['items']]
            videos_req = youtube.videos().list(
                part='contentDetails,snippet',
                id=','.join(video_ids)
            )
            videos_res = videos_req.execute()
            now_utc = datetime.now(timezone.utc)
            for item in videos_res['items']:
                duration = isodate.parse_duration(item['contentDetails']['duration']).total_seconds()
                video_id = item['id']
                published_at = item['snippet']['publishedAt']
                published_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                seconds_ago = (now_utc - published_time).total_seconds()
                if duration <= 60 and video_id != last_video_id and 0 <= seconds_ago <= 60:
                    title = item['snippet']['title']
                    return {
                        'video_id': video_id,
                        'title': title,
                        'published_at': published_at,
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    }
            return None
        except Exception as e:
            if hasattr(e, 'resp') and hasattr(e, 'content') and b'quotaExceeded' in e.content:
                log(channel_id, f"API key {api_key} quota exceeded, thử key tiếp theo...", 'ERROR')
                continue
            else:
                log(channel_id, f"Lỗi YouTube API: {e}", 'ERROR')
                break
    log(channel_id, "Tất cả API key đã hết quota hoặc lỗi khác!", 'ERROR')
    return None

def download_latest_shorts(channel_url, return_id_and_recent=False):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlist_items': '1',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info and info['entries']:
                latest = info['entries'][0]
                video_id = latest['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
                ydl_detail_opts = {'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_detail_opts) as ydl2:
                    detail = ydl2.extract_info(video_url, download=False)
                    is_recent = False
                    if 'timestamp' in detail:
                        now = int(time.time())
                        video_time = int(detail['timestamp'])
                        if now - video_time <= 120:
                            is_recent = True
                    # Lấy tiêu đề và hashtag
                    title = detail.get('title', '')
                    hashtags = []
                    if 'tags' in detail and detail['tags']:
                        hashtags = [f"#{tag}" for tag in detail['tags'] if tag]
                    if os.path.exists(video_path):
                        if return_id_and_recent:
                            return None, video_id, is_recent, title, hashtags
                        return None
                    if is_recent:
                        ydl_download_opts = {
                            'format': 'best[ext=mp4]/best',
                            'outtmpl': video_path,
                            'quiet': True,
                            'no_warnings': True
                        }
                        with yt_dlp.YoutubeDL(ydl_download_opts) as ydl3:
                            ydl3.download([video_url])
                        if os.path.exists(video_path):
                            if return_id_and_recent:
                                return video_path, video_id, is_recent, title, hashtags
                            return video_path
                    else:
                        if return_id_and_recent:
                            return None, video_id, is_recent, title, hashtags
                        return None
    except Exception as e:
        print(f"Lỗi tải video: {e}")
    if return_id_and_recent:
        return None, None, False, '', []
    return None

def worker_api(channel_id, profile_id, api_keys):
    print(f"Worker started for profile {profile_id}, channel {channel_id}")
    last_video_id = None
    while True:
        t0 = time.time()
        log(profile_id, "Bắt đầu quét video mới (API)", "START")
        video_info = get_latest_shorts_api(channel_id, last_video_id, api_keys=api_keys)
        log(profile_id, f"Quét xong metadata: {time.time()-t0:.2f}s", "INFO")
        if video_info:
            video_id = video_info['video_id']
            video_url = video_info['url']
            log(profile_id, f"Phát hiện shorts mới: {video_id} - {video_url}", "INFO")
            video_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
            # Tải video
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': video_path,
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            if os.path.exists(video_path):
                log(profile_id, f"Bắt đầu xử lý video {video_id}", "PROCESS")
                process_start = time.time()
                processed_path = os.path.join(PROCESSED_DIR, os.path.basename(video_path))
                process_video(video_path, processed_path)
                log(profile_id, f"Đã xử lý video: {processed_path} ({time.time()-process_start:.2f}s)", "PROCESS")
                upload_start = time.time()
                log(profile_id, f"Bắt đầu upload TikTok", "UPLOAD")
                success = upload_to_tiktok_gpmlogin(profile_id, processed_path)
                if success:
                    log(profile_id, f"Đã upload và xóa file: {processed_path} (upload {time.time()-upload_start:.2f}s, tổng {time.time()-t0:.2f}s)", "DONE")
                    try:
                        os.remove(processed_path)
                    except Exception as e:
                        log(profile_id, f"Lỗi xóa file: {e}", "ERROR")
                else:
                    log(profile_id, f"Upload thất bại, giữ lại file: {processed_path}", "ERROR")
                last_video_id = video_id
        time.sleep(1)

# Sửa worker_ytdlp để truyền title, hashtags vào upload_to_tiktok_gpmlogin

def worker_ytdlp(channel_url, profile_id):
    print(f"Worker started for profile {profile_id}, channel {channel_url}")
    last_video_id = None
    error_count = 0
    while True:
        try:
            t0 = time.time()
            log(profile_id, "Bắt đầu quét video mới", "START")
            result = download_latest_shorts(channel_url, return_id_and_recent=True)
            if result is None or len(result) < 5:
                time.sleep(0.3)
                continue
            video_path, video_id, is_recent, title, hashtags = result
            log(profile_id, f"Quét xong metadata: {time.time()-t0:.2f}s", "INFO")
            if video_id is None:
                time.sleep(0.3)
                continue
            if video_id == last_video_id:
                time.sleep(0.3)
                continue
            if not is_recent:
                last_video_id = video_id
                time.sleep(0.3)
                continue
            if video_path and is_recent:
                log(profile_id, f"Tiêu đề: {title}", "INFO")
                if hashtags:
                    log(profile_id, f"Hashtag: {' '.join(hashtags)}", "INFO")
                else:
                    log(profile_id, "Không có hashtag", "INFO")
                log(profile_id, f"Bắt đầu xử lý video {video_id}", "PROCESS")
                process_start = time.time()
                processed_path = os.path.join(PROCESSED_DIR, os.path.basename(video_path))
                process_video(video_path, processed_path)
                log(profile_id, f"Đã xử lý video: {processed_path} ({time.time()-process_start:.2f}s)", "PROCESS")
                upload_start = time.time()
                log(profile_id, f"Bắt đầu upload TikTok", "UPLOAD")
                success = upload_to_tiktok_gpmlogin(profile_id, processed_path, title, hashtags)
                if success:
                    log(profile_id, f"Đã upload và xóa file: {processed_path} (upload {time.time()-upload_start:.2f}s, tổng {time.time()-t0:.2f}s)", "DONE")
                    try:
                        os.remove(processed_path)
                        if os.path.exists(video_path):
                            os.remove(video_path)
                    except Exception as e:
                        log(profile_id, f"Lỗi xóa file: {e}", "ERROR")
                else:
                    log(profile_id, f"Upload thất bại, giữ lại file: {processed_path}", "ERROR")
                last_video_id = video_id
                error_count = 0  # reset error count nếu thành công
            else:
                last_video_id = video_id
            time.sleep(0.3)
        except Exception as e:
            error_count += 1
            log(profile_id, f"Lỗi yt-dlp hoặc xử lý: {e}", "ERROR")
            if error_count > 5:
                log(profile_id, "Quá nhiều lỗi liên tiếp, tạm nghỉ 5 giây", "ERROR")
                time.sleep(5)
                error_count = 0
            else:
                time.sleep(1)

def main():
    mapping = load_mapping()
    if not mapping:
        print("Không tìm thấy mapping hoặc file mapping.xlsx bị lỗi!")
        return
    processes = []
    for channel_id, profile_id in mapping:
        if MODE == 'api':
            p = Process(target=worker_api, args=(channel_id, profile_id, API_KEYS), daemon=True)
        else:
            p = Process(target=worker_ytdlp, args=(channel_id, profile_id), daemon=True)
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

if __name__ == '__main__':
    main() 