"""
Module xử lý perceptual hash của video frames
"""
import cv2
import numpy as np
import imagehash
from PIL import Image
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import os

from .config import FRAME_EXTRACTION_INTERVAL, HASH_SIZE, HIGHFREQ_FACTOR, TEMP_DIR

logger = logging.getLogger(__name__)

class VideoHashProcessor:
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True)
    
    def extract_frames(self, video_path: str, interval: int = FRAME_EXTRACTION_INTERVAL) -> List[np.ndarray]:
        """
        Trích xuất frames từ video theo khoảng thời gian
        """
        try:
            frames = []
            
            # Mở video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Không thể mở video: {video_path}")
                return []
            
            # Lấy thông tin video
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30  # Default FPS
            
            frame_interval = int(fps * interval)  # Frame cách bao nhiêu frame
            
            frame_count = 0
            extracted_count = 0
            
            logger.info(f"Đang trích xuất frames từ video (FPS: {fps}, interval: {interval}s)")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Chỉ lấy frame theo interval
                if frame_count % frame_interval == 0:
                    frames.append(frame)
                    extracted_count += 1
                
                frame_count += 1
            
            cap.release()
            logger.info(f"Đã trích xuất {extracted_count} frames từ {frame_count} frames tổng")
            
            return frames
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất frames: {e}")
            return []
    
    def frame_to_hash(self, frame: np.ndarray, hash_type: str = 'phash') -> Optional[imagehash.ImageHash]:
        """
        Chuyển đổi frame thành perceptual hash
        """
        try:
            # Chuyển từ BGR (OpenCV) sang RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Tính hash theo loại
            if hash_type == 'phash':
                return imagehash.phash(pil_image, hash_size=HASH_SIZE, highfreq_factor=HIGHFREQ_FACTOR)
            elif hash_type == 'dhash':
                return imagehash.dhash(pil_image, hash_size=HASH_SIZE)
            elif hash_type == 'ahash':
                return imagehash.average_hash(pil_image, hash_size=HASH_SIZE)
            elif hash_type == 'whash':
                return imagehash.whash(pil_image, hash_size=HASH_SIZE)
            else:
                return imagehash.phash(pil_image, hash_size=HASH_SIZE)
                
        except Exception as e:
            logger.error(f"Lỗi khi tính hash cho frame: {e}")
            return None
    
    def video_to_hashes(self, video_path: str, hash_type: str = 'phash') -> List[imagehash.ImageHash]:
        """
        Tạo danh sách hash cho tất cả frames của video
        """
        try:
            # Trích xuất frames
            frames = self.extract_frames(video_path)
            if not frames:
                return []
            
            # Tính hash cho từng frame
            hashes = []
            for i, frame in enumerate(frames):
                frame_hash = self.frame_to_hash(frame, hash_type)
                if frame_hash:
                    hashes.append(frame_hash)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Đã xử lý {i + 1}/{len(frames)} frames")
            
            logger.info(f"Đã tạo {len(hashes)} hashes từ video")
            return hashes
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo hashes cho video: {e}")
            return []
    
    def compare_hash_sequences(self, hashes1: List[imagehash.ImageHash], 
                             hashes2: List[imagehash.ImageHash],
                             max_distance: int = 5) -> float:
        """
        So sánh hai chuỗi hash và trả về độ tương đồng (0-1)
        """
        try:
            if not hashes1 or not hashes2:
                return 0.0
            
            # Nếu số lượng hash khác nhau quá nhiều, có thể không phải cùng video
            len_diff = abs(len(hashes1) - len(hashes2))
            max_len = max(len(hashes1), len(hashes2))
            
            if len_diff / max_len > 0.5:  # Khác nhau hơn 50%
                logger.debug("Độ dài hash sequences khác nhau quá nhiều")
                return 0.0
            
            # So sánh từng cặp hash
            min_len = min(len(hashes1), len(hashes2))
            matching_frames = 0
            
            for i in range(min_len):
                distance = hashes1[i] - hashes2[i]
                if distance <= max_distance:
                    matching_frames += 1
            
            similarity = matching_frames / min_len
            logger.debug(f"Matching frames: {matching_frames}/{min_len}, similarity: {similarity:.3f}")
            
            return similarity
            
        except Exception as e:
            logger.error(f"Lỗi khi so sánh hash sequences: {e}")
            return 0.0
    
    def compare_videos(self, video_path1: str, video_path2: str, 
                      hash_type: str = 'phash', max_distance: int = 5) -> float:
        """
        So sánh hai video và trả về độ tương đồng
        """
        try:
            logger.info(f"Đang so sánh video: {Path(video_path1).name} vs {Path(video_path2).name}")
            
            # Tạo hash cho cả hai video
            hashes1 = self.video_to_hashes(video_path1, hash_type)
            hashes2 = self.video_to_hashes(video_path2, hash_type)
            
            if not hashes1 or not hashes2:
                logger.warning("Không thể tạo hash cho một trong hai video")
                return 0.0
            
            # So sánh hash sequences
            similarity = self.compare_hash_sequences(hashes1, hashes2, max_distance)
            
            logger.info(f"Độ tương đồng: {similarity:.3f}")
            return similarity
            
        except Exception as e:
            logger.error(f"Lỗi khi so sánh videos: {e}")
            return 0.0
    
    def save_frame(self, frame: np.ndarray, filename: str) -> str:
        """
        Lưu frame ra file (để debug)
        """
        try:
            filepath = self.temp_dir / filename
            cv2.imwrite(str(filepath), frame)
            return str(filepath)
        except Exception as e:
            logger.error(f"Lỗi khi lưu frame: {e}")
            return ""
    
    def create_video_fingerprint(self, video_path: str) -> dict:
        """
        Tạo fingerprint tổng hợp cho video
        """
        try:
            # Tạo các loại hash khác nhau
            phashes = self.video_to_hashes(video_path, 'phash')
            dhashes = self.video_to_hashes(video_path, 'dhash')
            
            # Lấy thông tin video
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            fingerprint = {
                'video_path': video_path,
                'phashes': [str(h) for h in phashes],
                'dhashes': [str(h) for h in dhashes],
                'duration': duration,
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'extracted_frames': len(phashes)
            }
            
            logger.info(f"Đã tạo fingerprint cho video: {len(phashes)} phashes, {len(dhashes)} dhashes")
            return fingerprint
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo video fingerprint: {e}")
            return {}
    
    def compare_fingerprints(self, fp1: dict, fp2: dict, weight_phash: float = 0.7) -> float:
        """
        So sánh hai fingerprint và trả về độ tương đồng có trọng số
        """
        try:
            if not fp1 or not fp2:
                return 0.0
            
            # Chuyển hash strings về ImageHash objects
            phashes1 = [imagehash.hex_to_hash(h) for h in fp1.get('phashes', [])]
            phashes2 = [imagehash.hex_to_hash(h) for h in fp2.get('phashes', [])]
            dhashes1 = [imagehash.hex_to_hash(h) for h in fp1.get('dhashes', [])]
            dhashes2 = [imagehash.hex_to_hash(h) for h in fp2.get('dhashes', [])]
            
            # So sánh pHash (quan trọng hơn)
            phash_sim = self.compare_hash_sequences(phashes1, phashes2)
            
            # So sánh dHash
            dhash_sim = self.compare_hash_sequences(dhashes1, dhashes2)
            
            # Tính điểm tổng hợp
            weighted_similarity = (phash_sim * weight_phash + 
                                 dhash_sim * (1 - weight_phash))
            
            logger.debug(f"pHash sim: {phash_sim:.3f}, dHash sim: {dhash_sim:.3f}, "
                        f"weighted: {weighted_similarity:.3f}")
            
            return weighted_similarity
            
        except Exception as e:
            logger.error(f"Lỗi khi so sánh fingerprints: {e}")
            return 0.0