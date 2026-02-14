"""
MAIN.PY - ALX EHUB COURSE SCRAPER
Professional scraper with authentication and course discovery
"""
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alx_ehub_course_scraper.driver_manager import DriverManager
from alx_ehub_course_scraper.config import Config
from alx_ehub_course_scraper.auth.login_manager import LoginManager, AuthStatus
from alx_ehub_course_scraper.courses import CourseFinder, CourseList

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

def initialize_browser(config: Config, logger: logging.Logger) -> Optional[any]:
    """
    Initialize and start the browser
    
    Args:
        config: Config instance
        logger: Logger instance
    
    Returns:
        WebDriver instance or None if failed
    """
    try:
        print("\n🌐 Starting browser...")
        driver_manager = DriverManager()
        driver = driver_manager.get_driver(
            browser=config.default_browser,
            headless=config.headless_mode,
            stealth=config.data['browser_defaults']['stealth_mode']
        )
        logger.info(f"Browser started successfully: {config.default_browser}")
        return driver
    except Exception as e:
        logger.error(f"Failed to start browser: {e}")
        print(f"❌ Failed to start browser: {e}")
        return None

def authenticate(driver, config: Config, logger: logging.Logger) -> Optional[LoginManager]:
    """
    Handle authentication and return LoginManager instance
    
    Args:
        driver: WebDriver instance
        config: Config instance
        logger: Logger instance
    
    Returns:
        LoginManager instance if authenticated, None otherwise
    """
    print("\n🔐 AUTHENTICATING...")
    print("=" * 50)
    
    try:
        # Initialize login manager
        print("🔑 Initializing LoginManager...")
        login_manager = LoginManager(driver, config.data)
        logger.info("LoginManager initialized")
        
        # Perform authentication
        print("\n🔄 Checking login status...")
        auth_result = login_manager.ensure_logged_in()
        
        # Handle result
        if auth_result.status in [AuthStatus.SESSION_RESTORED, AuthStatus.AUTHENTICATED]:
            print(f"\n✅ {auth_result.message}")
            if auth_result.user_id:
                print(f"   User ID: {auth_result.user_id}")
            if auth_result.session_file:
                print(f"   Session: {auth_result.session_file}")
            
            logger.info(f"Authentication successful: {auth_result.status.value}")
            
            # List saved sessions
            print("\n📊 Active sessions:")
            sessions = login_manager.session_manager.list_sessions()
            if sessions:
                for session in sessions:
                    print(f"   - {session['email']} (last used: {session['last_used'][:10]})")
            else:
                print("   No saved sessions found")
            
            return login_manager
        else:
            print(f"\n❌ Authentication failed: {auth_result.message}")
            logger.error(f"Authentication failed: {auth_result.message}")
            return None
            
    except Exception as e:
        logger.exception("Error during authentication")
        print(f"\n❌ Authentication error: {e}")
        return None

def test_course_discovery(driver, config: Config, logger: logging.Logger) -> bool:
    """
    Test course discovery functionality
    
    Args:
        driver: WebDriver instance
        config: Config instance
        logger: Logger instance
    
    Returns:
        bool: True if course discovery successful
    """
    print("\n📚 TESTING COURSE DISCOVERY")
    print("=" * 50)
    
    try:
        # Initialize course finder
        print("🔍 Initializing CourseFinder...")
        course_finder = CourseFinder(driver, config.data)
        logger.info("CourseFinder initialized")
        
        # Discover courses
        print("\n🔄 Discovering courses...")
        courses = course_finder.find_all_courses(save_debug=True)
        
        # Print summary
        print(f"\n✅ Found {len(courses)} courses total")
        print(f"   Accessible: {len(courses.accessible_courses())}")
        print(f"   Completed: {len(courses.by_status('Completed'))}")
        print(f"   In Progress: {len(courses.by_status('In Progress'))}")
        
        # Print detailed list
        print("\n📋 Course List:")
        for i, course in enumerate(courses, 1):
            status_icon = "✅" if course.status == "Completed" else "🔄" if course.status == "In Progress" else "⏳"
            accessible_icon = "🔗" if course.is_accessible else "🚫"
            print(f"   {i}. {accessible_icon} {status_icon} {course.name}")
            if course.full_url:
                print(f"       URL: {course.full_url}")
        
        # Save to file
        output_dir = Path("data/course_lists")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"courses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        courses.save_to_file(str(output_file))
        print(f"\n💾 Course list saved to: {output_file}")
        
        logger.info(f"Course discovery completed: {len(courses)} courses found")
        return True
        
    except Exception as e:
        logger.exception("Error during course discovery")
        print(f"\n❌ Course discovery failed: {e}")
        return False

def run_interactive_mode(driver, config: Config, logger: logging.Logger):
    """
    Run interactive mode with menu
    
    Args:
        driver: WebDriver instance
        config: Config instance
        logger: Logger instance
    """
    while True:
        print("\n" + "="*60)
        print("🎯 ALX EHUB SCRAPER - INTERACTIVE MODE")
        print("="*60)
        print("1. Test Course Discovery")
        print("2. List Saved Sessions")
        print("3. Clear Current Session")
        print("4. Re-authenticate")
        print("5. Exit")
        print("="*60)
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            test_course_discovery(driver, config, logger)
            
        elif choice == "2":
            print("\n📊 SAVED SESSIONS:")
            login_manager = LoginManager(driver, config.data)
            sessions = login_manager.session_manager.list_sessions()
            if sessions:
                for session in sessions:
                    print(f"   - {session['email']}")
                    print(f"     Last used: {session['last_used']}")
                    print(f"     Expires: {session['expires_at']}")
            else:
                print("   No saved sessions found")
                
        elif choice == "3":
            login_manager = LoginManager(driver, config.data)
            if login_manager.logout():
                print("✅ Session cleared")
            else:
                print("❌ Failed to clear session")
                
        elif choice == "4":
            print("\n🔄 Re-authenticating...")
            login_manager = LoginManager(driver, config.data)
            result = login_manager.ensure_logged_in()
            if result.status in [AuthStatus.AUTHENTICATED, AuthStatus.SESSION_RESTORED]:
                print(f"✅ {result.message}")
            else:
                print(f"❌ {result.message}")
                
        elif choice == "5":
            print("\n👋 Exiting interactive mode...")
            break
        else:
            print("❌ Invalid choice")

def main():
    """Main entry point"""
    # Setup logging
    logger = setup_logging()
    
    print("\n" + "="*60)
    print("🎯 ALX EHUB COURSE SCRAPER")
    print("="*60)
    
    # Initialize config
    logger.info("Loading configuration")
    config = Config()
    
    # Initialize browser
    driver = initialize_browser(config, logger)
    if not driver:
        print("❌ Failed to initialize browser. Exiting.")
        return
    
    try:
        # Authenticate
        login_manager = authenticate(driver, config, logger)
        if not login_manager:
            print("\n❌ Authentication failed. Exiting.")
            return
        
        print("\n✨ Authentication successful! Ready to scrape.")
        
        # Ask user what to do next
        print("\n" + "="*60)
        print("🎯 SELECT MODE:")
        print("="*60)
        print("1. Quick Course Discovery Test")
        print("2. Interactive Mode (Menu)")
        print("3. Exit")
        print("="*60)
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # Quick course discovery test
            test_course_discovery(driver, config, logger)
            
            # Keep browser open
            print("\n⏱️  Browser will stay open for 30 seconds...")
            logger.info("Waiting for manual inspection")
            time.sleep(30)
            
        elif choice == "2":
            # Interactive mode
            run_interactive_mode(driver, config, logger)
            
        elif choice == "3":
            print("\n👋 Exiting...")
            
        else:
            print("❌ Invalid choice. Exiting.")
        
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        logger.info("Application interrupted by user")
        
    except Exception as e:
        logger.exception("Fatal error in main")
        print(f"\n💥 Fatal error: {e}")
        
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")
            print("\n🧹 Browser closed. Goodbye!")

if __name__ == "__main__":
    main()