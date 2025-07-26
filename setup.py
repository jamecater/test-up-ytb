#!/usr/bin/env python3
"""
Setup script for TikTok Tool CLI
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ required, found {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def install_requirements():
    """Install required packages"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    command = f"{sys.executable} -m pip install -r {requirements_file}"
    return run_command(command, "Installing Python packages")

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = ["downloads", "temp", "output", "utils"]
    
    for dir_name in directories:
        dir_path = Path(__file__).parent / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"   📂 {dir_name}/")
    
    print("✅ Directories created successfully")
    return True

def test_installation():
    """Test if installation works"""
    print("🧪 Testing installation...")
    
    try:
        # Test imports
        import click
        import yt_dlp
        import cv2
        import imagehash
        import selenium
        import pandas
        import numpy
        import requests
        import bs4
        import colorama
        import tqdm
        import fake_useragent
        import webdriver_manager
        
        print("✅ All required packages imported successfully")
        
        # Test CLI
        command = f"{sys.executable} main.py --help"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ CLI working correctly")
            return True
        else:
            print("❌ CLI test failed")
            print(result.stderr)
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def show_usage_examples():
    """Show usage examples"""
    print("\n" + "="*60)
    print("🎉 Installation completed successfully!")
    print("="*60)
    print("\n📖 Quick start examples:")
    print("\n🔍 Reup Detection:")
    print('   python main.py detect-reup "https://www.tiktok.com/@user/video/123"')
    print("\n🔥 Trending Videos:")
    print("   python main.py find-trending --country US --max-results 50")
    print("   python main.py find-trending --hashtag funny")
    print("\n📍 List supported countries:")
    print("   python main.py countries")
    print("\n📚 Full help:")
    print("   python main.py --help")
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("🎵 TikTok Tool CLI Setup")
    print("="*40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        print("\n❌ Failed to install requirements")
        print("Try running manually: pip install -r requirements.txt")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("\n⚠️ Installation completed but testing failed")
        print("You may need to install additional dependencies manually")
    
    # Show usage examples
    show_usage_examples()

if __name__ == "__main__":
    main()