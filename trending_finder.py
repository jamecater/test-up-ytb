"""
Module tìm video TikTok đang trending theo quốc gia hoặc hashtag
"""
import logging
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import re
from collections import Counter
from tqdm import tqdm

from utils.scraper import TikTokScraper
from utils.config import OUTPUT_DIR, CSV_ENCODING, JSON_ENCODING, COUNTRIES

logger = logging.getLogger(__name__)

class TrendingFinder:
    def __init__(self, use_proxy: bool = False, proxy_list: List[str] = None):
        self.scraper = TikTokScraper(use_proxy, proxy_list)
        self.output_dir = OUTPUT_DIR
        
    def find_trending_videos(self,
                           country: Optional[str] = None,
                           hashtag: Optional[str] = None,
                           max_results: int = 100,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Tìm video trending theo quốc gia hoặc hashtag
        """
        try:
            if country and hashtag:
                logger.warning("⚠️ Chỉ nên chọn country HOẶC hashtag, không nên cả hai")
                
            if hashtag:
                logger.info(f"🔥 Tìm video trending cho hashtag: #{hashtag}")
                trending_videos = self._find_trending_by_hashtag(hashtag, max_results)
            elif country:
                logger.info(f"🌍 Tìm video trending cho quốc gia: {country}")
                trending_videos = self._find_trending_by_country(country, max_results)
            else:
                logger.info("🌐 Tìm video trending global")
                trending_videos = self._find_trending_global(max_results)
            
            if not trending_videos:
                logger.warning("⚠️ Không tìm thấy video trending nào")
                return []
            
            logger.info(f"📋 Tìm thấy {len(trending_videos)} video trending")
            
            # Áp dụng filters nếu có
            if filters:
                trending_videos = self._apply_filters(trending_videos, filters)
                logger.info(f"🔍 Sau khi lọc còn: {len(trending_videos)} video")
            
            # Làm giàu thông tin video
            enriched_videos = self._enrich_video_info(trending_videos)
            
            return enriched_videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tìm trending videos: {e}")
            return []
    
    def _find_trending_by_hashtag(self, hashtag: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Tìm video trending theo hashtag
        """
        try:
            # Chuẩn hoá hashtag
            if not hashtag.startswith('#'):
                hashtag = f"#{hashtag}"
            
            search_keyword = hashtag.replace('#', '')
            
            # Tìm kiếm video với hashtag
            videos = self.scraper.search_videos_by_keyword(search_keyword, max_results)
            
            # Lọc video có hashtag chính xác
            filtered_videos = []
            for video in videos:
                title = video.get('title', '').lower()
                if hashtag.lower() in title:
                    video['source_type'] = 'hashtag'
                    video['source_value'] = hashtag
                    filtered_videos.append(video)
            
            return filtered_videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tìm trending by hashtag: {e}")
            return []
    
    def _find_trending_by_country(self, country: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Tìm video trending theo quốc gia
        """
        try:
            # Validate country code
            if country.upper() not in COUNTRIES:
                logger.warning(f"⚠️ Mã quốc gia '{country}' không được hỗ trợ")
                logger.info(f"Các mã quốc gia hỗ trợ: {list(COUNTRIES.keys())}")
                return []
            
            # Lấy trending videos (TikTok thường hiển thị trending theo vùng)
            videos = self.scraper.get_trending_videos(country, max_results)
            
            # Thêm thông tin source
            for video in videos:
                video['source_type'] = 'country'
                video['source_value'] = country.upper()
                video['country_name'] = COUNTRIES[country.upper()]
            
            return videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tìm trending by country: {e}")
            return []
    
    def _find_trending_global(self, max_results: int) -> List[Dict[str, Any]]:
        """
        Tìm video trending global (mặc định)
        """
        try:
            videos = self.scraper.get_trending_videos('US', max_results)  # Default to US
            
            for video in videos:
                video['source_type'] = 'global'
                video['source_value'] = 'global'
            
            return videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tìm trending global: {e}")
            return []
    
    def _apply_filters(self, videos: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Áp dụng các bộ lọc cho danh sách video
        """
        try:
            filtered_videos = videos.copy()
            
            # Filter by view count
            min_views = filters.get('min_views', 0)
            if min_views > 0:
                filtered_videos = [v for v in filtered_videos if v.get('view_count', 0) >= min_views]
                logger.info(f"🔍 Lọc theo min_views {min_views}: còn {len(filtered_videos)} video")
            
            # Filter by like count
            min_likes = filters.get('min_likes', 0)
            if min_likes > 0:
                filtered_videos = [v for v in filtered_videos if v.get('like_count', 0) >= min_likes]
                logger.info(f"🔍 Lọc theo min_likes {min_likes}: còn {len(filtered_videos)} video")
            
            # Filter by duration (in seconds)
            min_duration = filters.get('min_duration_seconds', 0)
            max_duration = filters.get('max_duration_seconds', float('inf'))
            
            if min_duration > 0 or max_duration < float('inf'):
                duration_filtered = []
                for video in filtered_videos:
                    duration_str = video.get('duration', '')
                    duration_seconds = self._parse_duration_to_seconds(duration_str)
                    
                    if min_duration <= duration_seconds <= max_duration:
                        duration_filtered.append(video)
                
                filtered_videos = duration_filtered
                logger.info(f"🔍 Lọc theo duration {min_duration}-{max_duration}s: còn {len(filtered_videos)} video")
            
            # Filter by upload time (hours ago)
            max_hours_ago = filters.get('max_hours_ago', None)
            if max_hours_ago:
                cutoff_time = datetime.now() - timedelta(hours=max_hours_ago)
                time_filtered = []
                
                for video in filtered_videos:
                    # Note: TikTok không luôn cung cấp thời gian upload chính xác
                    # Đây là placeholder logic
                    upload_date = video.get('upload_date', '')
                    if self._is_recent_enough(upload_date, cutoff_time):
                        time_filtered.append(video)
                
                filtered_videos = time_filtered
                logger.info(f"🔍 Lọc theo thời gian upload ({max_hours_ago}h): còn {len(filtered_videos)} video")
            
            # Filter by keyword in title
            keyword_filter = filters.get('title_contains', '')
            if keyword_filter:
                keyword_filtered = []
                for video in filtered_videos:
                    title = video.get('title', '').lower()
                    if keyword_filter.lower() in title:
                        keyword_filtered.append(video)
                
                filtered_videos = keyword_filtered
                logger.info(f"🔍 Lọc theo keyword '{keyword_filter}': còn {len(filtered_videos)} video")
            
            return filtered_videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi apply filters: {e}")
            return videos
    
    def _parse_duration_to_seconds(self, duration_str: str) -> int:
        """
        Parse duration string thành seconds
        """
        try:
            if not duration_str:
                return 0
            
            # Format có thể là: "1:23", "0:45", "23s", v.v.
            duration_str = duration_str.strip()
            
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes * 60 + seconds
                elif len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
            
            # Format "23s"
            if duration_str.endswith('s'):
                return int(duration_str[:-1])
            
            # Chỉ là số
            if duration_str.isdigit():
                return int(duration_str)
            
            return 0
            
        except (ValueError, IndexError):
            return 0
    
    def _is_recent_enough(self, upload_date: str, cutoff_time: datetime) -> bool:
        """
        Kiểm tra xem video có được upload trong khoảng thời gian cho phép không
        """
        try:
            # TikTok upload date format có thể khác nhau
            # Đây là placeholder implementation
            if not upload_date:
                return True  # Không có thông tin thì coi như OK
            
            # Parse upload_date và so sánh với cutoff_time
            # Format thường gặp: "YYYYMMDD" hoặc "YYYY-MM-DD"
            if len(upload_date) == 8 and upload_date.isdigit():
                upload_dt = datetime.strptime(upload_date, '%Y%m%d')
                return upload_dt >= cutoff_time
            
            return True  # Fallback
            
        except:
            return True
    
    def _enrich_video_info(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Làm giàu thông tin cho các video
        """
        try:
            enriched_videos = []
            
            with tqdm(total=len(videos), desc="🔄 Enriching video info", unit="video") as pbar:
                for video in videos:
                    try:
                        # Lấy thông tin chi tiết
                        detailed_info = self.scraper.get_video_details(video['url'])
                        
                        if detailed_info:
                            # Merge thông tin
                            enriched_video = {
                                'url': video['url'],
                                'video_id': self._extract_video_id(video['url']),
                                'username': detailed_info.get('username', video.get('username', '')),
                                'title': detailed_info.get('description', video.get('title', '')),
                                'view_count': video.get('view_count', 0),
                                'like_count': detailed_info.get('like_count', video.get('like_count', 0)),
                                'comment_count': detailed_info.get('comment_count', 0),
                                'share_count': detailed_info.get('share_count', 0),
                                'music': detailed_info.get('music', ''),
                                'duration': video.get('duration', ''),
                                'duration_seconds': self._parse_duration_to_seconds(video.get('duration', '')),
                                'thumbnail': video.get('thumbnail', ''),
                                'hashtags': self._extract_hashtags(detailed_info.get('description', '')),
                                'source_type': video.get('source_type', ''),
                                'source_value': video.get('source_value', ''),
                                'country_name': video.get('country_name', ''),
                                'scraped_at': datetime.now().isoformat(),
                                'engagement_rate': self._calculate_engagement_rate(
                                    detailed_info.get('like_count', 0),
                                    detailed_info.get('comment_count', 0),
                                    detailed_info.get('share_count', 0),
                                    video.get('view_count', 0)
                                )
                            }
                        else:
                            # Fallback to original video info
                            enriched_video = {
                                'url': video['url'],
                                'video_id': self._extract_video_id(video['url']),
                                'username': video.get('username', ''),
                                'title': video.get('title', ''),
                                'view_count': video.get('view_count', 0),
                                'like_count': video.get('like_count', 0),
                                'comment_count': 0,
                                'share_count': 0,
                                'music': '',
                                'duration': video.get('duration', ''),
                                'duration_seconds': self._parse_duration_to_seconds(video.get('duration', '')),
                                'thumbnail': video.get('thumbnail', ''),
                                'hashtags': [],
                                'source_type': video.get('source_type', ''),
                                'source_value': video.get('source_value', ''),
                                'country_name': video.get('country_name', ''),
                                'scraped_at': datetime.now().isoformat(),
                                'engagement_rate': 0
                            }
                        
                        enriched_videos.append(enriched_video)
                        
                    except Exception as e:
                        logger.debug(f"⚠️ Lỗi khi enrich video {video.get('url', 'Unknown')}: {e}")
                        # Thêm video gốc nếu không enrich được
                        enriched_videos.append(video)
                    finally:
                        pbar.update(1)
            
            return enriched_videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi enrich video info: {e}")
            return videos
    
    def _extract_video_id(self, url: str) -> str:
        """
        Trích xuất video ID từ URL
        """
        try:
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
            
            return ''
            
        except:
            return ''
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """
        Trích xuất hashtags từ text
        """
        try:
            if not text:
                return []
            
            hashtag_pattern = r'#\w+'
            hashtags = re.findall(hashtag_pattern, text)
            return [tag.lower() for tag in hashtags]
            
        except:
            return []
    
    def _calculate_engagement_rate(self, likes: int, comments: int, shares: int, views: int) -> float:
        """
        Tính engagement rate
        """
        try:
            if views <= 0:
                return 0.0
            
            total_engagement = likes + comments + shares
            engagement_rate = (total_engagement / views) * 100
            return round(engagement_rate, 2)
            
        except:
            return 0.0
    
    def analyze_trending_keywords(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phân tích từ khóa trending từ danh sách video
        """
        try:
            logger.info("📊 Phân tích trending keywords...")
            
            # Thu thập text từ titles
            all_text = []
            all_hashtags = []
            all_music = []
            
            for video in videos:
                title = video.get('title', '')
                hashtags = video.get('hashtags', [])
                music = video.get('music', '')
                
                if title:
                    all_text.append(title.lower())
                
                if hashtags:
                    all_hashtags.extend(hashtags)
                
                if music:
                    all_music.append(music)
            
            # Tách từ từ titles (loại bỏ hashtags và mentions)
            words = []
            for text in all_text:
                # Bỏ hashtags và mentions
                clean_text = re.sub(r'[#@]\w+', '', text)
                # Tách từ
                text_words = re.findall(r'\b\w+\b', clean_text)
                words.extend([w for w in text_words if len(w) > 2])  # Bỏ từ quá ngắn
            
            # Count frequencies
            word_counter = Counter(words)
            hashtag_counter = Counter(all_hashtags)
            music_counter = Counter(all_music)
            
            # Get top items
            top_words = word_counter.most_common(20)
            top_hashtags = hashtag_counter.most_common(15)
            top_music = music_counter.most_common(10)
            
            analysis = {
                'total_videos_analyzed': len(videos),
                'top_keywords': [{'keyword': word, 'count': count} for word, count in top_words],
                'top_hashtags': [{'hashtag': tag, 'count': count} for tag, count in top_hashtags],
                'top_music': [{'track': track, 'count': count} for track, count in top_music],
                'analysis_date': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Phân tích xong: {len(top_words)} keywords, {len(top_hashtags)} hashtags, {len(top_music)} music tracks")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi analyze trending keywords: {e}")
            return {}
    
    def save_results_to_csv(self, videos: List[Dict[str, Any]], 
                           source_type: str, source_value: str) -> str:
        """
        Lưu kết quả ra file CSV
        """
        try:
            # Tạo tên file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trending_{source_type}_{source_value}_{timestamp}.csv"
            filepath = self.output_dir / filename
            
            if videos:
                df = pd.DataFrame(videos)
                
                # Sắp xếp theo view count
                df = df.sort_values('view_count', ascending=False)
                
                # Lưu file
                df.to_csv(filepath, index=False, encoding=CSV_ENCODING)
                
                logger.info(f"💾 Đã lưu {len(videos)} video vào: {filepath}")
            else:
                # Tạo file rỗng với header
                columns = [
                    'url', 'video_id', 'username', 'title', 'view_count', 'like_count',
                    'comment_count', 'share_count', 'music', 'duration', 'duration_seconds',
                    'thumbnail', 'hashtags', 'source_type', 'source_value', 'country_name',
                    'scraped_at', 'engagement_rate'
                ]
                empty_df = pd.DataFrame(columns=columns)
                empty_df.to_csv(filepath, index=False, encoding=CSV_ENCODING)
                logger.info(f"💾 Đã tạo file CSV rỗng: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu CSV: {e}")
            return ""
    
    def save_results_to_json(self, videos: List[Dict[str, Any]], 
                           source_type: str, source_value: str) -> str:
        """
        Lưu kết quả ra file JSON
        """
        try:
            # Tạo tên file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trending_{source_type}_{source_value}_{timestamp}.json"
            filepath = self.output_dir / filename
            
            # Chuẩn bị data
            data = {
                'source_type': source_type,
                'source_value': source_value,
                'total_videos': len(videos),
                'scraped_at': datetime.now().isoformat(),
                'videos': videos
            }
            
            # Lưu file
            with open(filepath, 'w', encoding=JSON_ENCODING) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Đã lưu {len(videos)} video vào JSON: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu JSON: {e}")
            return ""
    
    def run_trending_analysis(self,
                            country: Optional[str] = None,
                            hashtag: Optional[str] = None,
                            max_results: int = 100,
                            filters: Optional[Dict[str, Any]] = None,
                            save_csv: bool = True,
                            save_json: bool = False,
                            analyze_keywords: bool = True) -> Dict[str, Any]:
        """
        Chạy toàn bộ quy trình phân tích trending
        """
        try:
            logger.info("🚀 Bắt đầu quy trình Trending Analysis")
            
            # Find trending videos
            trending_videos = self.find_trending_videos(
                country=country,
                hashtag=hashtag,
                max_results=max_results,
                filters=filters
            )
            
            # Determine source info
            if hashtag:
                source_type = "hashtag"
                source_value = hashtag.replace('#', '')
            elif country:
                source_type = "country"
                source_value = country.upper()
            else:
                source_type = "global"
                source_value = "global"
            
            # Save results
            csv_path = ""
            json_path = ""
            
            if save_csv:
                csv_path = self.save_results_to_csv(trending_videos, source_type, source_value)
            
            if save_json:
                json_path = self.save_results_to_json(trending_videos, source_type, source_value)
            
            # Analyze keywords
            keyword_analysis = {}
            if analyze_keywords and trending_videos:
                keyword_analysis = self.analyze_trending_keywords(trending_videos)
            
            # Create summary
            result = {
                'source_type': source_type,
                'source_value': source_value,
                'filters_applied': filters or {},
                'total_videos_found': len(trending_videos),
                'videos': trending_videos,
                'keyword_analysis': keyword_analysis,
                'csv_path': csv_path,
                'json_path': json_path,
                'completed_at': datetime.now().isoformat()
            }
            
            # Log summary
            if trending_videos:
                total_views = sum(v.get('view_count', 0) for v in trending_videos)
                avg_views = total_views // len(trending_videos) if trending_videos else 0
                
                logger.info(f"🎯 Tóm tắt kết quả:")
                logger.info(f"   • Tổng số video trending: {len(trending_videos)}")
                logger.info(f"   • Tổng lượt xem: {total_views:,}")
                logger.info(f"   • Lượt xem trung bình: {avg_views:,}")
                
                if csv_path:
                    logger.info(f"   • File CSV: {csv_path}")
                if json_path:
                    logger.info(f"   • File JSON: {json_path}")
                
                if keyword_analysis:
                    top_words = keyword_analysis.get('top_keywords', [])[:5]
                    if top_words:
                        logger.info(f"   • Top keywords: {[w['keyword'] for w in top_words]}")
            else:
                logger.info("🎯 Không tìm thấy video trending nào")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong quy trình trending analysis: {e}")
            return {
                'source_type': source_type if 'source_type' in locals() else '',
                'source_value': source_value if 'source_value' in locals() else '',
                'total_videos_found': 0,
                'videos': [],
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }
        finally:
            # Cleanup
            self.scraper.close()
    
    def __del__(self):
        """Cleanup khi object bị destroy"""
        if hasattr(self, 'scraper'):
            self.scraper.close()