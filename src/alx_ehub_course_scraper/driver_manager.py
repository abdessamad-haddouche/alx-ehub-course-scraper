import os
import requests
import zipfile
import shutil
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from typing import Optional
from .config import Config

class DriverManager:
    """Manages WebDriver setup for Windows browsers"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None
        self.config = Config()
        self.supported_browsers = ['chrome', 'firefox']
        
    def get_driver(self, browser: Optional[str] = None, headless: Optional[bool] = None, stealth: bool = False) -> webdriver.Remote:
        """Get WebDriver for Windows browsers"""
        browser = browser or self.config.default_browser
        headless = headless if headless is not None else self.config.headless_mode
        
        browser = browser.lower()
        
        if browser not in self.supported_browsers:
            raise ValueError(f"Browser '{browser}' not supported. Available: {self.supported_browsers}")
        
        if browser == 'chrome':
            return self._get_chrome_driver(headless, stealth)
        elif browser == 'firefox':
            return self._get_firefox_driver(headless, stealth)
        else:
            raise ValueError(f"Unsupported browser: {browser}")
    
    def _get_chrome_driver(self, headless: bool = False, stealth: bool = False) -> webdriver.Chrome:
        """Setup Chrome driver for Windows with proper error handling"""
        options = ChromeOptions()
        
        # Basic options
        if headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Window size from config
        window_size = self.config.data['browser_defaults']['window_size']
        options.add_argument(f'--window-size={window_size["width"]},{window_size["height"]}')
        
        # Anti-detection options
        if stealth or self.config.data['browser_defaults']['stealth_mode']:
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
        
        # Windows ChromeDriver setup with proper handling
        driver_dir = Path(self.config.get_driver_cache_path('chrome'))
        driver_path = driver_dir / 'chromedriver.exe'
        
        # Check if driver exists and is valid
        if self._is_driver_valid(driver_path):
            print("✅ Using existing ChromeDriver")
            service = ChromeService(str(driver_path))
            driver = webdriver.Chrome(service=service, options=options)
            self.driver = driver
            return driver
        
        # Download/update driver
        print("📥 Downloading/updating ChromeDriver for Windows...")
        
        # Clean up any existing files
        if driver_dir.exists():
            shutil.rmtree(driver_dir, ignore_errors=True)
        
        driver_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            url = 'https://storage.googleapis.com/chrome-for-testing-public/144.0.7559.96/win64/chromedriver-win64.zip'
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            zip_path = driver_dir / 'chromedriver.zip'
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(driver_dir)
            
            # Move the executable
            extracted_path = driver_dir / 'chromedriver-win64' / 'chromedriver.exe'
            if extracted_path.exists():
                extracted_path.rename(driver_path)
                
                # Clean up
                zip_path.unlink(missing_ok=True)
                shutil.rmtree(driver_dir / 'chromedriver-win64', ignore_errors=True)
                
                print("✅ ChromeDriver installed successfully!")
            else:
                raise FileNotFoundError("ChromeDriver executable not found in downloaded zip")
                
        except Exception as e:
            print(f"❌ Failed to download ChromeDriver: {e}")
            raise
        
        service = ChromeService(str(driver_path))
        driver = webdriver.Chrome(service=service, options=options)
        
        if stealth or self.config.data['browser_defaults']['stealth_mode']:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver = driver
        return driver

    def _is_driver_valid(self, driver_path: Path) -> bool:
        """Check if existing driver is valid and up-to-date"""
        if not driver_path.exists():
            return False
        
        try:
            # Try to get version
            result = subprocess.run([str(driver_path), '--version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and '144.0.7559' in result.stdout:
                return True
        except:
            pass
        
        return False
    
    def _get_firefox_driver(self, headless: bool = False, stealth: bool = False) -> webdriver.Firefox:
        """Setup Firefox driver for Windows"""
        options = FirefoxOptions()
        
        if headless:
            options.add_argument('--headless')
        
        window_size = self.config.data['browser_defaults']['window_size']
        options.add_argument(f'--width={window_size["width"]}')
        options.add_argument(f'--height={window_size["height"]}')
        
        if stealth or self.config.data['browser_defaults']['stealth_mode']:
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference('useAutomationExtension', False)
            options.set_preference("general.useragent.override", 
                                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0")
        
        cache_path = self.config.get_driver_cache_path('firefox')
        os.environ['WDM_LOCAL_CACHE'] = cache_path
        
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        self.driver = driver
        return driver
    
    def close_driver(self) -> None:
        """Close the current driver with proper error handling"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                # Silently ignore errors during cleanup
                # Browser may have already closed or connection lost
                pass
            finally:
                self.driver = None
    
    def get_available_browsers(self) -> list[str]:
        """Get list of available Windows browsers"""
        return self.supported_browsers