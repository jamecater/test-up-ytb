"""
Module tải video TikTok sử dụng yt-dlp
"""
import os
import yt_dlp
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import re

from .config import DOWNLOADS_DIR, USER_AGENTS

logger = logging.getLogger(__name__)

class TikTokDownloader:
    def __init__(self):
        self.download_dir = DOWNLOADS_DIR
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Trích xuất video ID từ TikTok URL
        """
        try:
            # Pattern cho TikTok URLs
            patterns = [
                r'tiktok\.com/@[\w\.-]+/video/(\d+)',
                r'tiktok\.com/.*video/(\d+)',
                r'vm\.tiktok\.com/([A-Za-z0-9]+)',
                r'tiktok\.com/t/([A-Za-z0-9]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
                    
            # Nếu input đã là video ID
            if re.match(r'^\d+$', url.strip()):
                return url.strip()
                
            logger.warning(f"Không thể trích xuất video ID từ URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất video ID: {e}")
            return None
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin video mà không tải về
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractaudio': False,
                'outtmpl': '%(id)s.%(ext)s',
                'user-agent': USER_AGENTS[0]
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'id': info.get('id'),
                    'title': info.get('title', ''),
                    'uploader': info.get('uploader', ''),
                    'uploader_id': info.get('uploader_id', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'comment_count': info.get('comment_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'webpage_url': info.get('webpage_url', ''),
                    'upload_date': info.get('upload_date', ''),
                    'tags': info.get('tags', [])
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin video {url}: {e}")
            return None
    
    def download_video(self, url: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        Tải video TikTok về thư mục downloads
        """
        try:
            # Tạo thư mục downloads nếu chưa có
            self.download_dir.mkdir(exist_ok=True)
            
            # Cấu hình yt-dlp
            if output_filename:
                outtmpl = str(self.download_dir / output_filename)
            else:
                outtmpl = str(self.download_dir / '%(id)s.%(ext)s')
            
            ydl_opts = {
                'outtmpl': outtmpl,
                'format': 'best[height<=720]',  # Tải chất lượng vừa phải để tăng tốc
                'user-agent': USER_AGENTS[0],
                'quiet': False,
                'no_warnings': False
            }
            
            logger.info(f"Đang tải video từ: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Lấy thông tin video trước
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id')
                
                # Tải video
                ydl.download([url])
                
                # Tìm file đã tải
                for file_path in self.download_dir.glob(f"{video_id}.*"):
                    if file_path.suffix in ['.mp4', '.webm', '.mkv']:
                        logger.info(f"Đã tải xong: {file_path}")
                        return str(file_path)
                        
            logger.error(f"Không tìm thấy file video đã tải")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi tải video {url}: {e}")
            return None
    
    def download_thumbnail(self, url: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Tải thumbnail của video
        """
        try:
            if not output_path:
                output_path = str(self.download_dir / '%(id)s_thumb.%(ext)s')
            
            ydl_opts = {
                'outtmpl': output_path,
                'writethumbnail': True,
                'skip_download': True,
                'user-agent': USER_AGENTS[0],
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id')
                ydl.download([url])
                
                # Tìm thumbnail đã tải
                for file_path in self.download_dir.glob(f"{video_id}_thumb.*"):
                    if file_path.suffix in ['.jpg', '.jpeg', '.png', '.webp']:
                        return str(file_path)
                        
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi tải thumbnail {url}: {e}")
            return None
    
    def extract_hashtags_from_description(self, description: str) -> list:
        """
        Trích xuất hashtags từ mô tả video
        """
        if not description:
            return []
            
        hashtag_pattern = r'#\w+'
        hashtags = re.findall(hashtag_pattern, description)
        return [tag.lower() for tag in hashtags]
    
    def generate_search_keywords(self, video_info: dict) -> list:
        """
        Tạo từ khóa tìm kiếm từ thông tin video
        """
        keywords = []
        
        # Từ title
        if video_info.get('title'):
            title_words = re.findall(r'\w+', video_info['title'].lower())
            keywords.extend(title_words[:5])  # Lấy 5 từ đầu
        
        # Từ hashtags
        if video_info.get('description'):
            hashtags = self.extract_hashtags_from_description(video_info['description'])
            keywords.extend([tag[1:] for tag in hashtags[:3]])  # Bỏ dấu # và lấy 3 tag đầu
        
        # Username
        if video_info.get('uploader_id'):
            keywords.append(video_info['uploader_id'])
        
        return list(set(keywords))  # Remove duplicates