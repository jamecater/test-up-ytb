"""
Module tìm video TikTok trùng lặp (Reup Detection)
"""
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from utils.video_downloader import TikTokDownloader
from utils.hash_processor import VideoHashProcessor
from utils.scraper import TikTokScraper
from utils.config import (
    OUTPUT_DIR, SIMILARITY_THRESHOLD, CSV_ENCODING,
    CONCURRENT_WORKERS, MAX_RETRIES
)

logger = logging.getLogger(__name__)

class ReupDetector:
    def __init__(self, use_proxy: bool = False, proxy_list: List[str] = None):
        self.downloader = TikTokDownloader()
        self.hash_processor = VideoHashProcessor()
        self.scraper = TikTokScraper(use_proxy, proxy_list)
        self.output_dir = OUTPUT_DIR
        
    def detect_reups(self, 
                    original_video_url: str,
                    max_search_results: int = 100,
                    similarity_threshold: float = SIMILARITY_THRESHOLD,
                    search_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Tìm các video trùng lặp với video gốc
        """
        try:
            logger.info(f"🔍 Bắt đầu tìm video trùng lặp cho: {original_video_url}")
            
            # Bước 1: Tải và phân tích video gốc
            logger.info("📥 Đang tải video gốc...")
            original_info = self.downloader.get_video_info(original_video_url)
            if not original_info:
                logger.error("❌ Không thể lấy thông tin video gốc")
                return []
            
            original_video_path = self.downloader.download_video(original_video_url)
            if not original_video_path:
                logger.error("❌ Không thể tải video gốc")
                return []
            
            # Bước 2: Tạo fingerprint cho video gốc
            logger.info("🔑 Đang tạo fingerprint video gốc...")
            original_fingerprint = self.hash_processor.create_video_fingerprint(original_video_path)
            if not original_fingerprint:
                logger.error("❌ Không thể tạo fingerprint cho video gốc")
                return []
            
            logger.info(f"✅ Đã tạo fingerprint với {original_fingerprint['extracted_frames']} frames")
            
            # Bước 3: Tạo từ khóa tìm kiếm
            if not search_keywords:
                search_keywords = self.downloader.generate_search_keywords(original_info)
            
            logger.info(f"🔎 Từ khóa tìm kiếm: {search_keywords}")
            
            # Bước 4: Tìm kiếm video tương tự
            candidate_videos = self._search_candidate_videos(
                search_keywords, max_search_results
            )
            
            if not candidate_videos:
                logger.warning("⚠️ Không tìm thấy video ứng viên nào")
                return []
            
            logger.info(f"📋 Tìm thấy {len(candidate_videos)} video ứng viên")
            
            # Bước 5: So sánh fingerprint
            duplicate_videos = self._compare_with_candidates(
                original_fingerprint, candidate_videos, similarity_threshold
            )
            
            logger.info(f"🎯 Tìm thấy {len(duplicate_videos)} video trùng lặp")
            
            # Bước 6: Làm giàu thông tin và sắp xếp
            enriched_duplicates = self._enrich_duplicate_info(duplicate_videos, original_info)
            
            return enriched_duplicates
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong quá trình detect reup: {e}")
            return []
        finally:
            # Cleanup
            self.scraper.close()
    
    def _search_candidate_videos(self, keywords: List[str], max_results: int) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video ứng viên dựa trên từ khóa
        """
        try:
            all_candidates = []
            results_per_keyword = max_results // len(keywords) if keywords else max_results
            
            for keyword in keywords:
                logger.info(f"🔍 Tìm kiếm với từ khóa: '{keyword}'")
                
                videos = self.scraper.search_videos_by_keyword(
                    keyword, max_results=results_per_keyword
                )
                
                if videos:
                    logger.info(f"✅ Tìm thấy {len(videos)} video cho '{keyword}'")
                    all_candidates.extend(videos)
                else:
                    logger.warning(f"⚠️ Không tìm thấy video nào cho '{keyword}'")
            
            # Loại bỏ duplicate URLs
            unique_candidates = []
            seen_urls = set()
            
            for video in all_candidates:
                url = video.get('url', '')
                if url and url not in seen_urls:
                    unique_candidates.append(video)
                    seen_urls.add(url)
            
            logger.info(f"📋 Có {len(unique_candidates)} video ứng viên duy nhất")
            return unique_candidates
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tìm kiếm candidate videos: {e}")
            return []
    
    def _compare_with_candidates(self, 
                               original_fingerprint: Dict[str, Any], 
                               candidates: List[Dict[str, Any]], 
                               threshold: float) -> List[Dict[str, Any]]:
        """
        So sánh fingerprint video gốc với các ứng viên
        """
        try:
            duplicates = []
            
            # Sử dụng ThreadPoolExecutor để xử lý song song
            with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
                # Submit tasks
                future_to_video = {
                    executor.submit(self._compare_single_candidate, original_fingerprint, candidate, threshold): candidate
                    for candidate in candidates
                }
                
                # Process results với progress bar
                with tqdm(total=len(candidates), desc="🔄 So sánh videos", unit="video") as pbar:
                    for future in as_completed(future_to_video):
                        candidate = future_to_video[future]
                        try:
                            result = future.result()
                            if result:
                                duplicates.append(result)
                                logger.info(f"✅ Tìm thấy trùng lặp: {candidate.get('url', 'Unknown')} "
                                          f"(Similarity: {result['similarity']:.2%})")
                        except Exception as e:
                            logger.debug(f"⚠️ Lỗi khi so sánh {candidate.get('url', 'Unknown')}: {e}")
                        finally:
                            pbar.update(1)
            
            # Sắp xếp theo độ tương đồng
            duplicates.sort(key=lambda x: x['similarity'], reverse=True)
            
            return duplicates
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi so sánh với candidates: {e}")
            return []
    
    def _compare_single_candidate(self, 
                                 original_fingerprint: Dict[str, Any], 
                                 candidate: Dict[str, Any], 
                                 threshold: float) -> Optional[Dict[str, Any]]:
        """
        So sánh một video ứng viên với video gốc
        """
        try:
            video_url = candidate.get('url')
            if not video_url:
                return None
            
            # Tải video ứng viên (chỉ tải nếu cần thiết)
            candidate_video_path = self.downloader.download_video(video_url)
            if not candidate_video_path:
                logger.debug(f"⚠️ Không thể tải video: {video_url}")
                return None
            
            # Tạo fingerprint cho video ứng viên
            candidate_fingerprint = self.hash_processor.create_video_fingerprint(candidate_video_path)
            if not candidate_fingerprint:
                logger.debug(f"⚠️ Không thể tạo fingerprint: {video_url}")
                return None
            
            # So sánh fingerprints
            similarity = self.hash_processor.compare_fingerprints(
                original_fingerprint, candidate_fingerprint
            )
            
            # Nếu độ tương đồng >= threshold thì coi là trùng lặp
            if similarity >= threshold:
                result = candidate.copy()
                result['similarity'] = similarity
                result['candidate_fingerprint'] = candidate_fingerprint
                return result
            
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ Lỗi khi so sánh candidate: {e}")
            return None
        finally:
            # Cleanup candidate video file
            if 'candidate_video_path' in locals() and candidate_video_path:
                try:
                    os.remove(candidate_video_path)
                except:
                    pass
    
    def _enrich_duplicate_info(self, duplicates: List[Dict[str, Any]], original_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Làm giàu thông tin cho các video trùng lặp
        """
        try:
            enriched = []
            
            for duplicate in duplicates:
                # Lấy thông tin chi tiết từ scraper
                detailed_info = self.scraper.get_video_details(duplicate['url'])
                
                if detailed_info:
                    # Merge thông tin
                    enriched_duplicate = {
                        'url': duplicate['url'],
                        'username': detailed_info.get('username', duplicate.get('username', '')),
                        'title': detailed_info.get('description', duplicate.get('title', '')),
                        'view_count': duplicate.get('view_count', 0),
                        'like_count': detailed_info.get('like_count', duplicate.get('like_count', 0)),
                        'comment_count': detailed_info.get('comment_count', 0),
                        'share_count': detailed_info.get('share_count', 0),
                        'music': detailed_info.get('music', ''),
                        'similarity_percent': round(duplicate['similarity'] * 100, 2),
                        'duration': duplicate.get('duration', ''),
                        'thumbnail': duplicate.get('thumbnail', ''),
                        'detected_at': datetime.now().isoformat()
                    }
                else:
                    # Fallback to original duplicate info
                    enriched_duplicate = {
                        'url': duplicate['url'],
                        'username': duplicate.get('username', ''),
                        'title': duplicate.get('title', ''),
                        'view_count': duplicate.get('view_count', 0),
                        'like_count': duplicate.get('like_count', 0),
                        'comment_count': 0,
                        'share_count': 0,
                        'music': '',
                        'similarity_percent': round(duplicate['similarity'] * 100, 2),
                        'duration': duplicate.get('duration', ''),
                        'thumbnail': duplicate.get('thumbnail', ''),
                        'detected_at': datetime.now().isoformat()
                    }
                
                enriched.append(enriched_duplicate)
            
            return enriched
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi enrich duplicate info: {e}")
            return duplicates
    
    def save_results_to_csv(self, duplicates: List[Dict[str, Any]], original_url: str) -> str:
        """
        Lưu kết quả ra file CSV
        """
        try:
            # Tạo tên file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_id = self.downloader.extract_video_id(original_url) or "unknown"
            filename = f"reup_detection_{original_id}_{timestamp}.csv"
            filepath = self.output_dir / filename
            
            # Tạo DataFrame
            if duplicates:
                df = pd.DataFrame(duplicates)
                
                # Sắp xếp theo độ tương đồng
                df = df.sort_values('similarity_percent', ascending=False)
                
                # Lưu file
                df.to_csv(filepath, index=False, encoding=CSV_ENCODING)
                
                logger.info(f"💾 Đã lưu {len(duplicates)} kết quả vào: {filepath}")
            else:
                # Tạo file rỗng với header
                empty_df = pd.DataFrame(columns=[
                    'url', 'username', 'title', 'view_count', 'like_count',
                    'comment_count', 'share_count', 'music', 'similarity_percent',
                    'duration', 'thumbnail', 'detected_at'
                ])
                empty_df.to_csv(filepath, index=False, encoding=CSV_ENCODING)
                logger.info(f"💾 Đã tạo file kết quả rỗng: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu CSV: {e}")
            return ""
    
    def run_detection(self, 
                     original_video_url: str,
                     max_search_results: int = 100,
                     similarity_threshold: float = SIMILARITY_THRESHOLD,
                     search_keywords: Optional[List[str]] = None,
                     save_csv: bool = True) -> Dict[str, Any]:
        """
        Chạy toàn bộ quy trình detect reup
        """
        try:
            logger.info("🚀 Bắt đầu quy trình Reup Detection")
            
            # Detect duplicates
            duplicates = self.detect_reups(
                original_video_url, 
                max_search_results, 
                similarity_threshold,
                search_keywords
            )
            
            # Save results
            csv_path = ""
            if save_csv:
                csv_path = self.save_results_to_csv(duplicates, original_video_url)
            
            # Summary
            result = {
                'original_url': original_video_url,
                'total_duplicates_found': len(duplicates),
                'duplicates': duplicates,
                'csv_path': csv_path,
                'search_keywords': search_keywords,
                'similarity_threshold': similarity_threshold,
                'completed_at': datetime.now().isoformat()
            }
            
            # Log summary
            if duplicates:
                avg_similarity = sum(d['similarity_percent'] for d in duplicates) / len(duplicates)
                logger.info(f"🎯 Tóm tắt kết quả:")
                logger.info(f"   • Tổng số video trùng lặp: {len(duplicates)}")
                logger.info(f"   • Độ tương đồng trung bình: {avg_similarity:.1f}%")
                logger.info(f"   • Độ tương đồng cao nhất: {duplicates[0]['similarity_percent']:.1f}%")
                if csv_path:
                    logger.info(f"   • File kết quả: {csv_path}")
            else:
                logger.info("🎯 Không tìm thấy video trùng lặp nào")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong quy trình detection: {e}")
            return {
                'original_url': original_video_url,
                'total_duplicates_found': 0,
                'duplicates': [],
                'csv_path': "",
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