#!/usr/bin/env python3
"""
Quick Start Script for TikTok Tool CLI
Hướng dẫn nhanh và demo các tính năng chính
"""
import subprocess
import sys
from pathlib import Path
import time

def print_header():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      🎵 TIKTOK TOOL CLI - QUICK START 🎵                     ║
║                                                                              ║
║  Script này sẽ hướng dẫn bạn sử dụng các tính năng chính của tool           ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

def show_menu():
    print("""
📋 CHỌN CHỨC NĂNG MUỐN DEMO:

1. 🔍 Demo Reup Detection (Tìm video trùng lặp)  
2. 🔥 Demo Trending Finder - Quốc gia
3. 🏷️  Demo Trending Finder - Hashtag
4. 📍 Xem danh sách quốc gia hỗ trợ
5. 🔄 Demo Batch Processing
6. 📚 Xem help và tất cả commands
7. ❌ Thoát

""")

def run_command_interactive(command, description):
    """Run command và show output real-time"""
    print(f"\n🚀 {description}")
    print(f"💻 Command: {command}")
    print("="*60)
    
    try:
        # Hỏi user có muốn chạy không
        response = input("\n⚡ Chạy command này? (y/n): ").lower().strip()
        if response != 'y':
            print("⏭️ Bỏ qua command này")
            return
        
        # Run command
        result = subprocess.run(command, shell=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ {description} hoàn thành!")
        else:
            print(f"\n⚠️ {description} có vấn đề (exit code: {result.returncode})")
            
    except KeyboardInterrupt:
        print("\n⚠️ Đã dừng command")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
    
    input("\n📎 Nhấn Enter để tiếp tục...")

def demo_reup_detection():
    """Demo tính năng tìm video trùng lặp"""
    print("""
🔍 DEMO REUP DETECTION

Tính năng này sẽ:
- Tải video TikTok gốc 
- Tạo fingerprint từ video frames
- Tìm kiếm video tương tự trên TikTok
- So sánh độ tương đồng và xuất CSV

⚠️ Lưu ý: Cần URL video TikTok thật để demo
    """)
    
    # Hỏi user nhập URL
    sample_url = "https://www.tiktok.com/@username/video/1234567890123456789"
    url = input(f"\n📹 Nhập URL video TikTok (hoặc Enter để dùng URL mẫu):\n{sample_url}\n\n> ").strip()
    
    if not url:
        url = sample_url
        print("⚠️ Sử dụng URL mẫu (có thể không hoạt động)")
    
    # Commands để demo
    commands = [
        (f'python main.py detect-reup "{url}" --max-results 20', 
         "Tìm video trùng lặp với 20 kết quả"),
        
        (f'python main.py detect-reup "{url}" --threshold 0.9 --max-results 10', 
         "Tìm với ngưỡng cao (90%) và 10 kết quả"),
         
        (f'python main.py detect-reup "{url}" --keywords "funny,viral" --no-csv', 
         "Tìm với từ khóa tùy chỉnh, không lưu CSV")
    ]
    
    for command, description in commands:
        run_command_interactive(command, description)

def demo_trending_country():
    """Demo tìm trending theo quốc gia"""
    print("""
🌍 DEMO TRENDING FINDER - QUỐC GIA

Tính năng này sẽ:
- Tìm video trending theo quốc gia
- Áp dụng bộ lọc (views, likes, duration)
- Phân tích keywords trending
- Xuất kết quả CSV/JSON
    """)
    
    commands = [
        ("python main.py find-trending --country US --max-results 10", 
         "Trending US - 10 video"),
        
        ("python main.py find-trending --country VN --max-results 15 --min-views 50000", 
         "Trending VN - min 50K views"),
         
        ("python main.py find-trending --country JP --max-results 8 --save-json --min-duration 10 --max-duration 60", 
         "Trending Japan - save JSON, 10-60s videos")
    ]
    
    for command, description in commands:
        run_command_interactive(command, description)

def demo_trending_hashtag():
    """Demo tìm trending theo hashtag"""
    print("""
🏷️ DEMO TRENDING FINDER - HASHTAG

Tính năng này sẽ:
- Tìm video trending theo hashtag
- Lọc theo các tiêu chí
- Phân tích từ khóa liên quan
- Tính engagement rate
    """)
    
    # Hỏi user nhập hashtag
    hashtag = input("\n🔥 Nhập hashtag (không cần #, hoặc Enter để dùng 'funny'): ").strip()
    if not hashtag:
        hashtag = "funny"
    
    commands = [
        (f"python main.py find-trending --hashtag {hashtag} --max-results 15", 
         f"Trending #{hashtag} - 15 video"),
        
        (f"python main.py find-trending --hashtag {hashtag} --min-likes 10000 --title-contains laugh", 
         f"#{hashtag} với min 10K likes, title chứa 'laugh'"),
         
        (f"python main.py find-trending --hashtag {hashtag} --max-hours-ago 24 --save-json", 
         f"#{hashtag} trong 24h qua, save JSON")
    ]
    
    for command, description in commands:
        run_command_interactive(command, description)

def show_countries():
    """Hiển thị danh sách quốc gia"""
    command = "python main.py countries"
    run_command_interactive(command, "Xem danh sách mã quốc gia hỗ trợ")

def demo_batch():
    """Demo batch processing"""
    print("""
🔄 DEMO BATCH PROCESSING

Chạy nhiều task từ file cấu hình JSON
File example_config.json có sẵn các task mẫu
    """)
    
    config_file = Path("example_config.json")
    if not config_file.exists():
        print("❌ File example_config.json không tồn tại")
        print("Hãy tạo file này trước khi demo batch")
        return
    
    command = "python main.py batch example_config.json"
    run_command_interactive(command, "Chạy batch từ example_config.json")

def show_help():
    """Hiển thị help và commands"""
    commands = [
        ("python main.py --help", "Help tổng quát"),
        ("python main.py detect-reup --help", "Help cho Reup Detection"),
        ("python main.py find-trending --help", "Help cho Trending Finder"),
        ("python main.py batch --help", "Help cho Batch Processing")
    ]
    
    for command, description in commands:
        run_command_interactive(command, description)

def main():
    """Main function"""
    print_header()
    
    while True:
        show_menu()
        
        try:
            choice = input("👉 Chọn số (1-7): ").strip()
            
            if choice == '1':
                demo_reup_detection()
            elif choice == '2':
                demo_trending_country()
            elif choice == '3':
                demo_trending_hashtag()
            elif choice == '4':
                show_countries()
            elif choice == '5':
                demo_batch()
            elif choice == '6':
                show_help()
            elif choice == '7':
                print("\n👋 Cảm ơn bạn đã sử dụng TikTok Tool CLI!")
                break
            else:
                print("\n❌ Lựa chọn không hợp lệ, vui lòng chọn 1-7")
                
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")

if __name__ == "__main__":
    main()