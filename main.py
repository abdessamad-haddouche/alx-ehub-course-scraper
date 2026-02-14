"""
MAIN.PY - ALX EHUB COURSE SCRAPER
Simple Selenium setup to visit ALX ehub
"""
import sys
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alx_ehub_course_scraper.driver_manager import DriverManager
from alx_ehub_course_scraper.config import Config

def visit_alx_ehub():
    """Setup Selenium and visit ALX ehub"""
    print("🎯 ALX EHUB COURSE SCRAPER")
    print("=" * 40)
    
    # Initialize config and driver manager
    config = Config()
    driver_manager = DriverManager()
    
    # Target URL
    url = "https://ehub.alxafrica.com/"
    
    # Create output folder for this session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(f"data/ehub_capture_{timestamp}")
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output folder: {output_folder}")
    
    driver = None
    try:
        print("🌐 Starting browser...")
        print(f"   Browser: {config.default_browser}")
        print(f"   Headless: {config.headless_mode}")
        print(f"   Stealth mode: {config.data['browser_defaults']['stealth_mode']}")
        
        # Get the driver with your configuration
        driver = driver_manager.get_driver(
            browser=config.default_browser,
            headless=config.headless_mode,
            stealth=config.data['browser_defaults']['stealth_mode']
        )
        
        print(f"📥 Loading: {url}")
        driver.get(url)
        
        # Wait for page to load
        import time
        time.sleep(3)
        
        # Save page info
        print(f"📄 Page title: {driver.title}")
        print(f"🌐 Current URL: {driver.current_url}")
        
        # Save HTML
        html_file = output_folder / "page.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"💾 HTML saved: {html_file}")
        
        # Save screenshot
        screenshot = output_folder / "page.png"
        driver.save_screenshot(str(screenshot))
        print(f"📸 Screenshot saved: {screenshot}")
        
        # Keep browser open for a moment
        print("\n⏱️  Keeping browser open for 10 seconds...")
        time.sleep(10)
        
        print(f"\n✅ SUCCESS! Check {output_folder} for captured data")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            print("🧹 Browser closed")

def main():
    """Main entry point"""
    visit_alx_ehub()

if __name__ == "__main__":
    main()