"""
MAIN.PY - ALX EHUB COURSE SCRAPER
Scraper with logging and authentication
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alx_ehub_course_scraper.driver_manager import DriverManager
from alx_ehub_course_scraper.config import Config
from alx_ehub_course_scraper.auth.login_manager import LoginManager, AuthStatus

def setup_logging():
    """Configure logging for the entire application"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("webdriver_manager").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("LOGGING CONFIGURED SUCCESSFULLY")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)
    
    return logger

def test_auth(driver, config, logger):
    """
    Test authentication flow with provided driver and config
    
    Args:
        driver: WebDriver instance
        config: Config instance
        logger: Logger instance
    
    Returns:
        bool: True if authentication successful
    """
    print("\n🔐 TESTING AUTHENTICATION FLOW")
    print("=" * 50)
    
    try:
        # Log configuration
        logger.info("Starting authentication test")
        logger.debug(f"Browser: {config.default_browser}")
        logger.debug(f"Headless mode: {config.headless_mode}")
        
        # Initialize login manager
        print("\n🔑 Initializing LoginManager...")
        login_manager = LoginManager(driver, config.data)
        logger.info("LoginManager initialized")
        
        # Test authentication
        print("\n🔄 Testing authentication...")
        auth_result = login_manager.ensure_logged_in()
        
        # Handle result
        if auth_result.status in [AuthStatus.SESSION_RESTORED, AuthStatus.AUTHENTICATED]:
            print(f"\n✅ {auth_result.message}")
            if auth_result.user_id:
                print(f"   User ID: {auth_result.user_id}")
            if auth_result.session_file:
                print(f"   Session: {auth_result.session_file}")
            
            logger.info(f"Authentication successful: {auth_result.status.value}")
            
            # List sessions
            print("\n📊 Listing saved sessions:")
            sessions = login_manager.session_manager.list_sessions()
            if sessions:
                for session in sessions:
                    print(f"   - {session['email']} (last used: {session['last_used'][:10]})")
            else:
                print("   No saved sessions found")
            
            return True
        else:
            print(f"\n❌ {auth_result.message}")
            logger.error(f"Authentication failed: {auth_result.message}")
            return False
        
    except Exception as e:
        logger.exception("Error during authentication test")
        print(f"\n❌ Error: {e}")
        return False

def main():
    """Main entry point"""
    # Setup logging first
    logger = setup_logging()
    
    print("\n🎯 ALX EHUB COURSE SCRAPER - AUTH TEST")
    print("=" * 60)
    
    # Initialize config and driver manager ONCE
    logger.info("Initializing configuration")
    config = Config()
    driver_manager = DriverManager()
    
    driver = None
    try:
        print("\n🌐 Starting browser...")
        driver = driver_manager.get_driver(
            browser=config.default_browser,
            headless=config.headless_mode,
            stealth=config.data['browser_defaults']['stealth_mode']
        )
        logger.info("Browser started successfully")
        
        # Run authentication test
        success = test_auth(driver, config, logger)
        
        if success:
            print("\n✨ Authentication test PASSED!")
            logger.info("Authentication test completed successfully")
            
            # Keep browser open for inspection
            print("\n⏱️  Browser will stay open for 15 seconds...")
            logger.info("Waiting for manual inspection")
            import time
            time.sleep(15)
        else:
            print("\n❌ Authentication test FAILED!")
            logger.error("Authentication test failed")
        
    except Exception as e:
        logger.exception("Fatal error in main")
        print(f"\n💥 Fatal error: {e}")
        
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")
            print("🧹 Browser closed")

if __name__ == "__main__":
    main()