#!/usr/bin/env python3
"""
TikTok Tool CLI - Tool tìm video TikTok trùng lặp và trending
"""
import click
import logging
import sys
from typing import List, Optional
from pathlib import Path
import colorama
from colorama import Fore, Style
import json

from reup_detector import ReupDetector
from trending_finder import TrendingFinder
from utils.config import COUNTRIES, SIMILARITY_THRESHOLD

# Initialize colorama
colorama.init()

def setup_logging(verbose: bool = False):
    """Thiết lập logging"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Formatter với colors
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': Fore.CYAN,
            'INFO': Fore.GREEN,
            'WARNING': Fore.YELLOW,
            'ERROR': Fore.RED,
            'CRITICAL': Fore.MAGENTA
        }
        
        def format(self, record):
            log_color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
            return super().format(record)
    
    formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

def print_banner():
    """In banner tool"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                            🎵 TIKTOK TOOL CLI 🎵                            ║
║                                                                              ║
║  🔍 Chức năng 1: Tìm video TikTok trùng lặp (Reup Detection)                ║
║  🔥 Chức năng 2: Tìm video TikTok trending theo quốc gia/hashtag            ║
║                                                                              ║
║  Phát triển bởi: Tâm Kem | Version: 1.0                                ║
╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--proxy', help='Proxy server (format: http://host:port)')
@click.pass_context
def cli(ctx, verbose, proxy):
    """TikTok Tool CLI - Tìm video trùng lặp và trending"""
    print_banner()
    setup_logging(verbose)
    
    # Store context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['proxy'] = [proxy] if proxy else []

@cli.command()
@click.argument('video_url')
@click.option('--max-results', '-m', default=100, help='Số lượng video ứng viên tối đa để tìm kiếm')
@click.option('--threshold', '-t', default=SIMILARITY_THRESHOLD, help='Ngưỡng độ tương đồng (0.0-1.0)')
@click.option('--keywords', '-k', help='Từ khóa tìm kiếm (cách nhau bởi dấu phẩy)')
@click.option('--no-csv', is_flag=True, help='Không lưu file CSV')
@click.pass_context
def detect_reup(ctx, video_url, max_results, threshold, keywords, no_csv):
    """
    🔍 Tìm video TikTok trùng lặp (Reup Detection)
    
    VIDEO_URL: Link video TikTok gốc hoặc video ID
    
    Ví dụ:
    
    \b
    python main.py detect-reup "https://www.tiktok.com/@user/video/123456789"
    python main.py detect-reup "123456789" --threshold 0.85
    python main.py detect-reup "https://..." --keywords "funny,meme,viral"
    """
    try:
        proxy_list = ctx.obj.get('proxy', [])
        use_proxy = len(proxy_list) > 0
        
        # Parse keywords
        search_keywords = None
        if keywords:
            search_keywords = [k.strip() for k in keywords.split(',')]
        
        print(f"{Fore.GREEN}🚀 Bắt đầu Reup Detection...{Style.RESET_ALL}")
        print(f"📹 Video gốc: {video_url}")
        print(f"🎯 Ngưỡng tương đồng: {threshold:.1%}")
        print(f"📊 Số video ứng viên tối đa: {max_results}")
        
        if search_keywords:
            print(f"🔎 Từ khóa tìm kiếm: {', '.join(search_keywords)}")
        
        # Initialize detector
        detector = ReupDetector(use_proxy=use_proxy, proxy_list=proxy_list)
        
        # Run detection
        result = detector.run_detection(
            original_video_url=video_url,
            max_search_results=max_results,
            similarity_threshold=threshold,
            search_keywords=search_keywords,
            save_csv=not no_csv
        )
        
        # Print results
        print(f"\n{Fore.YELLOW}📋 KẾT QUẢ REUP DETECTION:{Style.RESET_ALL}")
        print(f"   • Video gốc: {result['original_url']}")
        print(f"   • Tổng video trùng lặp: {Fore.GREEN}{result['total_duplicates_found']}{Style.RESET_ALL}")
        
        if result['total_duplicates_found'] > 0:
            duplicates = result['duplicates']
            avg_similarity = sum(d['similarity_percent'] for d in duplicates) / len(duplicates)
            print(f"   • Độ tương đồng trung bình: {avg_similarity:.1f}%")
            print(f"   • Độ tương đồng cao nhất: {duplicates[0]['similarity_percent']:.1f}%")
            
            print(f"\n{Fore.CYAN}🔝 TOP 5 VIDEO TRÙNG LẶP:{Style.RESET_ALL}")
            for i, video in enumerate(duplicates[:5], 1):
                print(f"   {i}. @{video['username']} - {video['similarity_percent']:.1f}%")
                print(f"      👀 {video['view_count']:,} views | ❤️ {video['like_count']:,} likes")
                print(f"      🔗 {video['url']}")
                print()
        
        if result.get('csv_path'):
            print(f"💾 File kết quả: {Fore.GREEN}{result['csv_path']}{Style.RESET_ALL}")
        
        if result.get('error'):
            print(f"{Fore.RED}❌ Lỗi: {result['error']}{Style.RESET_ALL}")
            sys.exit(1)
        
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi không mong đợi: {e}{Style.RESET_ALL}")
        sys.exit(1)

@cli.command()
@click.option('--country', '-c', help=f'Mã quốc gia ({", ".join(list(COUNTRIES.keys())[:10])}...)')
@click.option('--hashtag', '-h', help='Hashtag (không cần dấu #)')
@click.option('--max-results', '-m', default=100, help='Số lượng video tối đa')
@click.option('--min-views', type=int, help='Lượt xem tối thiểu')
@click.option('--min-likes', type=int, help='Lượt thích tối thiểu')
@click.option('--min-duration', type=int, help='Độ dài tối thiểu (giây)')
@click.option('--max-duration', type=int, help='Độ dài tối đa (giây)')
@click.option('--max-hours-ago', type=int, help='Video được đăng trong vòng X giờ')
@click.option('--title-contains', help='Tiêu đề chứa từ khóa')
@click.option('--no-csv', is_flag=True, help='Không lưu file CSV')
@click.option('--save-json', is_flag=True, help='Lưu file JSON')
@click.option('--no-keywords', is_flag=True, help='Không phân tích keywords')
@click.pass_context
def find_trending(ctx, country, hashtag, max_results, min_views, min_likes, 
                 min_duration, max_duration, max_hours_ago, title_contains,
                 no_csv, save_json, no_keywords):
    """
    🔥 Tìm video TikTok trending theo quốc gia hoặc hashtag
    
    Ví dụ:
    
    \b
    python main.py find-trending --country US --max-results 50
    python main.py find-trending --hashtag funny --min-views 10000
    python main.py find-trending --country VN --min-duration 15 --max-duration 60
    python main.py find-trending --hashtag meme --save-json
    """
    try:
        if not country and not hashtag:
            print(f"{Fore.YELLOW}⚠️ Vui lòng chọn --country hoặc --hashtag{Style.RESET_ALL}")
            print("Sử dụng --help để xem hướng dẫn")
            sys.exit(1)
        
        if country and hashtag:
            print(f"{Fore.YELLOW}⚠️ Chỉ nên chọn country HOẶC hashtag, không nên cả hai{Style.RESET_ALL}")
            print("Tiếp tục với hashtag...")
            country = None
        
        # Validate country
        if country and country.upper() not in COUNTRIES:
            print(f"{Fore.RED}❌ Mã quốc gia '{country}' không hợp lệ{Style.RESET_ALL}")
            print(f"Các mã quốc gia hỗ trợ: {', '.join(list(COUNTRIES.keys()))}")
            sys.exit(1)
        
        proxy_list = ctx.obj.get('proxy', [])
        use_proxy = len(proxy_list) > 0
        
        # Build filters
        filters = {}
        if min_views:
            filters['min_views'] = min_views
        if min_likes:
            filters['min_likes'] = min_likes
        if min_duration:
            filters['min_duration_seconds'] = min_duration
        if max_duration:
            filters['max_duration_seconds'] = max_duration
        if max_hours_ago:
            filters['max_hours_ago'] = max_hours_ago
        if title_contains:
            filters['title_contains'] = title_contains
        
        print(f"{Fore.GREEN}🚀 Bắt đầu Trending Analysis...{Style.RESET_ALL}")
        
        if country:
            print(f"🌍 Quốc gia: {COUNTRIES[country.upper()]} ({country.upper()})")
        if hashtag:
            print(f"🔥 Hashtag: #{hashtag}")
        
        print(f"📊 Số video tối đa: {max_results}")
        
        if filters:
            print(f"🔍 Bộ lọc: {filters}")
        
        # Initialize finder
        finder = TrendingFinder(use_proxy=use_proxy, proxy_list=proxy_list)
        
        # Run analysis
        result = finder.run_trending_analysis(
            country=country,
            hashtag=hashtag,
            max_results=max_results,
            filters=filters if filters else None,
            save_csv=not no_csv,
            save_json=save_json,
            analyze_keywords=not no_keywords
        )
        
        # Print results
        print(f"\n{Fore.YELLOW}📋 KẾT QUẢ TRENDING ANALYSIS:{Style.RESET_ALL}")
        print(f"   • Nguồn: {result['source_type']} - {result['source_value']}")
        print(f"   • Tổng video trending: {Fore.GREEN}{result['total_videos_found']}{Style.RESET_ALL}")
        
        if result['total_videos_found'] > 0:
            videos = result['videos']
            total_views = sum(v.get('view_count', 0) for v in videos)
            avg_views = total_views // len(videos) if videos else 0
            
            print(f"   • Tổng lượt xem: {total_views:,}")
            print(f"   • Lượt xem trung bình: {avg_views:,}")
            
            print(f"\n{Fore.CYAN}🔝 TOP 5 VIDEO TRENDING:{Style.RESET_ALL}")
            for i, video in enumerate(videos[:5], 1):
                print(f"   {i}. @{video['username']}")
                print(f"      📱 {video['title'][:80]}...")
                print(f"      👀 {video['view_count']:,} views | ❤️ {video['like_count']:,} likes")
                print(f"      🔗 {video['url']}")
                print()
        
        # Keyword analysis
        if result.get('keyword_analysis') and result['keyword_analysis']:
            analysis = result['keyword_analysis']
            top_keywords = analysis.get('top_keywords', [])[:10]
            top_hashtags = analysis.get('top_hashtags', [])[:10]
            
            if top_keywords:
                print(f"{Fore.MAGENTA}📊 TOP KEYWORDS TRENDING:{Style.RESET_ALL}")
                for kw in top_keywords:
                    print(f"   • {kw['keyword']} ({kw['count']})")
                print()
            
            if top_hashtags:
                print(f"{Fore.MAGENTA}🏷️ TOP HASHTAGS TRENDING:{Style.RESET_ALL}")
                for tag in top_hashtags:
                    print(f"   • {tag['hashtag']} ({tag['count']})")
                print()
        
        # File paths
        if result.get('csv_path'):
            print(f"💾 File CSV: {Fore.GREEN}{result['csv_path']}{Style.RESET_ALL}")
        if result.get('json_path'):
            print(f"💾 File JSON: {Fore.GREEN}{result['json_path']}{Style.RESET_ALL}")
        
        if result.get('error'):
            print(f"{Fore.RED}❌ Lỗi: {result['error']}{Style.RESET_ALL}")
            sys.exit(1)
        
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi không mong đợi: {e}{Style.RESET_ALL}")
        sys.exit(1)

@cli.command()
def countries():
    """📍 Hiển thị danh sách mã quốc gia được hỗ trợ"""
    print(f"{Fore.CYAN}🌍 DANH SÁCH MÃ QUỐC GIA HỖ TRỢ:{Style.RESET_ALL}\n")
    
    for code, name in COUNTRIES.items():
        print(f"   {Fore.GREEN}{code:3}{Style.RESET_ALL} - {name}")
    
    print(f"\n{Fore.YELLOW}Sử dụng: python main.py find-trending --country US{Style.RESET_ALL}")

@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
def batch(config_file):
    """
    🔄 Chạy batch từ file cấu hình JSON
    
    CONFIG_FILE: Đường dẫn đến file cấu hình JSON
    
    Format file JSON:
    {
      "tasks": [
        {
          "type": "reup_detect",
          "video_url": "https://...",
          "max_results": 100,
          "threshold": 0.8
        },
        {
          "type": "trending",
          "country": "US",
          "max_results": 50,
          "filters": {"min_views": 10000}
        }
      ]
    }
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        tasks = config.get('tasks', [])
        print(f"{Fore.GREEN}🔄 Bắt đầu batch với {len(tasks)} tasks...{Style.RESET_ALL}\n")
        
        for i, task in enumerate(tasks, 1):
            task_type = task.get('type')
            print(f"{Fore.CYAN}📋 Task {i}/{len(tasks)}: {task_type}{Style.RESET_ALL}")
            
            if task_type == 'reup_detect':
                detector = ReupDetector()
                result = detector.run_detection(
                    original_video_url=task['video_url'],
                    max_search_results=task.get('max_results', 100),
                    similarity_threshold=task.get('threshold', SIMILARITY_THRESHOLD),
                    search_keywords=task.get('keywords'),
                    save_csv=task.get('save_csv', True)
                )
                print(f"   ✅ Tìm thấy {result['total_duplicates_found']} video trùng lặp")
                
            elif task_type == 'trending':
                finder = TrendingFinder()
                result = finder.run_trending_analysis(
                    country=task.get('country'),
                    hashtag=task.get('hashtag'),
                    max_results=task.get('max_results', 100),
                    filters=task.get('filters'),
                    save_csv=task.get('save_csv', True),
                    save_json=task.get('save_json', False)
                )
                print(f"   ✅ Tìm thấy {result['total_videos_found']} video trending")
            
            print()
        
        print(f"{Fore.GREEN}🎉 Hoàn thành tất cả {len(tasks)} tasks!{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi khi chạy batch: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == '__main__':
    cli()