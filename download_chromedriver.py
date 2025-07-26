#!/usr/bin/env python3
"""
ChromeDriver Auto-Download Helper
Tự động download ChromeDriver phù hợp với phiên bản Chrome hiện tại
"""

import os
import requests
import zipfile
import json
import subprocess
import sys
from pathlib import Path

def get_chrome_version():
    """Lấy phiên bản Chrome hiện tại"""
    try:
        # Windows
        if os.name == 'nt':
            import winreg
            reg_path = r"SOFTWARE\Google\Chrome\BLBeacon"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                version, _ = winreg.QueryValueEx(key, "version")
                return version
        else:
            # Linux/Mac
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True)
            return result.stdout.split()[-1]
    except:
        print("❌ Cannot detect Chrome version")
        return None

def get_chromedriver_url(chrome_version):
    """Lấy URL download ChromeDriver phù hợp"""
    try:
        major_version = chrome_version.split('.')[0]
        
        # Chrome 115+: sử dụng Chrome for Testing API
        if int(major_version) >= 115:
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            response = requests.get(api_url)
            data = response.json()
            
            # Tìm version gần nhất
            for version_data in reversed(data['versions']):
                if version_data['version'].startswith(major_version):
                    downloads = version_data['downloads']
                    if 'chromedriver' in downloads:
                        for platform_data in downloads['chromedriver']:
                            if platform_data['platform'] == 'win32':
                                return platform_data['url']
        
        # Chrome < 115: sử dụng old API
        else:
            old_api_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            response = requests.get(old_api_url)
            driver_version = response.text.strip()
            return f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
            
    except Exception as e:
        print(f"❌ Error getting ChromeDriver URL: {e}")
        return None

def download_chromedriver():
    """Download và cài đặt ChromeDriver"""
    print("🚀 ChromeDriver Auto-Download Helper")
    print("=" * 50)
    
    # Kiểm tra Chrome version
    print("🔍 Detecting Chrome version...")
    chrome_version = get_chrome_version()
    
    if not chrome_version:
        print("❌ Chrome not found or cannot detect version")
        print("📝 Please install Google Chrome first")
        return False
    
    print(f"✅ Chrome version: {chrome_version}")
    
    # Lấy download URL
    print("🔍 Getting ChromeDriver download URL...")
    download_url = get_chromedriver_url(chrome_version)
    
    if not download_url:
        print("❌ Cannot find compatible ChromeDriver")
        print("📝 Please download manually from: https://chromedriver.chromium.org/")
        return False
    
    print(f"✅ ChromeDriver URL: {download_url}")
    
    # Download file
    print("📥 Downloading ChromeDriver...")
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        zip_path = "chromedriver_temp.zip"
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("✅ Download completed")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False
    
    # Extract file
    print("📂 Extracting ChromeDriver...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to current directory
            zip_ref.extractall(".")
            
            # Find chromedriver.exe file
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file == "chromedriver.exe":
                        src_path = os.path.join(root, file)
                        dst_path = "chromedriver.exe"
                        
                        # Move to main directory if needed
                        if src_path != dst_path:
                            if os.path.exists(dst_path):
                                os.remove(dst_path)
                            os.rename(src_path, dst_path)
                        
                        print(f"✅ ChromeDriver extracted: {os.path.abspath(dst_path)}")
                        break
        
        # Cleanup
        os.remove(zip_path)
        
        # Clean up extracted directories
        for item in os.listdir("."):
            if os.path.isdir(item) and "chromedriver" in item.lower():
                import shutil
                shutil.rmtree(item)
        
        print("🎉 ChromeDriver installation completed!")
        print(f"📍 Location: {os.path.abspath('chromedriver.exe')}")
        return True
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False

def main():
    """Main function"""
    if download_chromedriver():
        print("\n✅ SUCCESS! ChromeDriver is ready to use")
        print("🚀 You can now run the TikTok pipeline")
    else:
        print("\n❌ FAILED! Please download ChromeDriver manually")
        print("📝 Instructions:")
        print("   1. Go to: https://chromedriver.chromium.org/")
        print("   2. Download ChromeDriver for your Chrome version")
        print("   3. Extract chromedriver.exe to this folder")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()