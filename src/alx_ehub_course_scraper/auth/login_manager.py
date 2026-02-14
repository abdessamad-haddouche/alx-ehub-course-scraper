"""
Login Manager for ALX ehub
Handles authentication with per-user session management
"""
import pickle
import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv

# Create a logger for your module
logger = logging.getLogger(__name__)

class AuthStatus(Enum):
    """Authentication status enum"""
    AUTHENTICATED = "authenticated"
    SESSION_RESTORED = "session_restored"
    LOGIN_FAILED = "login_failed"
    INVALID_CREDENTIALS = "invalid_credentials"
    SESSION_EXPIRED = "session_expired"

@dataclass
class SessionInfo:
    """Session metadata"""
    user_id: str
    email: str
    created_at: str
    last_used: str
    expires_at: str
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires

@dataclass
class AuthResult:
    """Authentication result"""
    status: AuthStatus
    message: str
    user_id: Optional[str] = None
    session_file: Optional[Path] = None
    
class LoginError(Exception):
    """Custom exception for login errors"""
    pass

class LoginManager:
    """
    Main authentication manager with per-user session handling
    """
    
    def __init__(self, driver: WebDriver, config: Dict[str, Any]):
        self.driver = driver
        self.config = config
        self.session_manager = SessionManager()
        
        # Load credentials
        load_dotenv()
        self.email = os.getenv('ALX_EMAIL')
        self.password = os.getenv('ALX_PASSWORD')
        
        if not self.email or not self.password:
            raise LoginError("ALX_EMAIL and ALX_PASSWORD must be set in .env")
        
        # Get auth config
        self.auth_config = config.get('auth', {})
        self.timeouts = self.auth_config.get('timeouts', {
            'page_load': 10,
            'element_wait': 10,
            'post_login_wait': 3
        })
        
        logger.info(f"LoginManager initialized for user: {self.email}")
    
    def ensure_logged_in(self) -> AuthResult:
        """
        Main method - ensures user is logged in
        Uses per-user session management
        """
        logger.info(f"Starting authentication for {self.email}")
        
        # Step 1: Try to load user's saved session
        session_info = self.session_manager.load_session(self.driver, self.email)
        
        if session_info:
            logger.info(f"Session loaded for {self.email} (created: {session_info.created_at})")
            
            # Step 2: Verify session works
            if self._is_authenticated():
                return AuthResult(
                    status=AuthStatus.SESSION_RESTORED,
                    message=f"Session restored for {self.email}",
                    user_id=session_info.user_id,
                    session_file=self.session_manager._get_session_file(self.email)
                )
            else:
                logger.warning(f"Session invalid for {self.email}, clearing...")
                self.session_manager.clear_session(self.email)
        
        # Step 3: Perform fresh login
        logger.info(f"No valid session for {self.email}, performing login")
        return self._perform_login()
    
    def _is_authenticated(self) -> bool:
        """Check if current session is authenticated"""
        current_url = self.driver.current_url.lower()
        page_source = self.driver.page_source.lower()
        
        # If we're on login page, definitely not authenticated
        if 'login' in current_url or 'signin' in current_url:
            logger.debug("On login page - not authenticated")
            return False
        
        # METHOD 1: Check for user profile image (STRONGEST indicator)
        try:
            profile_images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='profilePhoto']")
            if profile_images and profile_images[0].is_displayed():
                logger.debug("✅ Found profile image - authenticated")
                return True
        except Exception as e:
            logger.debug(f"Profile image check failed: {e}")
        
        # METHOD 2: Check for greeting with name
        try:
            greeting = self.driver.find_elements(By.CSS_SELECTOR, "p.flex.text-3xl.font-bold")
            if greeting and greeting[0].is_displayed() and "Hello" in greeting[0].text:
                logger.debug(f"✅ Found greeting: {greeting[0].text} - authenticated")
                return True
        except Exception as e:
            logger.debug(f"Greeting check failed: {e}")
        
        # METHOD 3: Check for points display
        try:
            points = self.driver.find_elements(By.CSS_SELECTOR, "span.font-bold.text-sm.text-card-foreground")
            if points and points[0].is_displayed() and points[0].text.isdigit():
                logger.debug(f"✅ Found points: {points[0].text} - authenticated")
                return True
        except Exception as e:
            logger.debug(f"Points check failed: {e}")
        
        # METHOD 4: Check for notification bell with red circle
        try:
            notification = self.driver.find_elements(By.CSS_SELECTOR, "svg circle[fill='#FF6B5E']")
            if notification:
                logger.debug("✅ Found notification bell - authenticated")
                return True
        except Exception as e:
            logger.debug(f"Notification check failed: {e}")
        
        # METHOD 5: Check for absence of login form (fallback)
        try:
            login_forms = self.driver.find_elements(By.CSS_SELECTOR, "form.space-y-4")
            if not login_forms:
                # If no login form and we're not on login page, assume authenticated
                logger.debug("No login form found - assuming authenticated")
                return True
        except:
            pass
        
        logger.debug("No authentication indicators found")
        return False
    
    def _perform_login(self) -> AuthResult:
        """Perform fresh login and save session"""
        try:
            # Navigate to login page
            login_url = self.auth_config.get('urls', {}).get(
                'login',
                'https://ehub.alxafrica.com/login'
            )
            
            logger.info(f"Navigating to {login_url}")
            self.driver.get(login_url)
            
            # Wait for page to load
            import time
            time.sleep(2)
            
            # === CAPTURE LOGIN PAGE FOR ANALYSIS ===
            try:
                # Create login_pages directory
                login_pages_dir = Path("data/login_pages")
                login_pages_dir.mkdir(parents=True, exist_ok=True)
                
                # Create filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = login_pages_dir / f"login_page_{timestamp}.html"
                screenshot_file = login_pages_dir / f"login_page_{timestamp}.png"
                
                # Save HTML
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info(f"📄 Login page HTML saved: {html_file}")
                
                # Save screenshot
                self.driver.save_screenshot(str(screenshot_file))
                logger.info(f"📸 Login page screenshot saved: {screenshot_file}")
                
                # Log all input fields found
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input")
                logger.debug(f"Found {len(inputs)} input fields on login page:")
                for i, inp in enumerate(inputs):
                    try:
                        input_type = inp.get_attribute("type")
                        input_name = inp.get_attribute("name")
                        input_id = inp.get_attribute("id")
                        input_class = inp.get_attribute("class")
                        logger.debug(f"  Input {i+1}: type={input_type}, name={input_name}, id={input_id}, class={input_class}")
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"Could not save login page for analysis: {e}")
            # === END CAPTURE ===
            
            # Wait for form
            if not self._wait_for_login_form():
                return AuthResult(
                    status=AuthStatus.LOGIN_FAILED,
                    message="Login form not found"
                )
            
            # Fill credentials
            if not self._fill_credentials():
                return AuthResult(
                    status=AuthStatus.LOGIN_FAILED,
                    message="Could not fill login form"
                )
            
            # Submit
            if not self._submit_form():
                return AuthResult(
                    status=AuthStatus.LOGIN_FAILED,
                    message="Could not submit login form"
                )
            
            # Wait for redirect and page load
            time.sleep(self.timeouts.get('post_login_wait', 5))
            
            # Verify login
            if self._is_authenticated():
                # Save session for this user
                session_info = self.session_manager.save_session(self.driver, self.email)
                
                logger.info(f"Login successful for {self.email}")
                return AuthResult(
                    status=AuthStatus.AUTHENTICATED,
                    message=f"Login successful for {self.email}",
                    user_id=session_info.user_id,
                    session_file=self.session_manager._get_session_file(self.email)
                )
            else:
                return AuthResult(
                    status=AuthStatus.LOGIN_FAILED,
                    message="Still not authenticated after login"
                )
                
        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            return AuthResult(
                status=AuthStatus.LOGIN_FAILED,
                message=f"Login error: {str(e)}"
            )
        
    def get_user_info(self) -> Dict[str, str]:
        """Extract user information from logged-in page"""
        user_info = {}
        
        try:
            # Get user name from greeting
            greeting = self.driver.find_elements(By.CSS_SELECTOR, "p.flex.text-3xl.font-bold")
            if greeting:
                # Extract name from "Hello Name!"
                text = greeting[0].text
                if "Hello" in text:
                    user_info['name'] = text.replace("Hello", "").replace("!", "").strip()
        except:
            pass
        
        try:
            # Get user points
            points = self.driver.find_elements(By.CSS_SELECTOR, "span.font-bold.text-sm.text-card-foreground")
            if points and points[0].text.isdigit():
                user_info['points'] = points[0].text
        except:
            pass
        
        try:
            # Get profile image URL
            profile_img = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='profilePhoto']")
            if profile_img:
                user_info['profile_image'] = profile_img[0].get_attribute('src')
        except:
            pass
        
        return user_info
    
    def _wait_for_login_form(self) -> bool:
        """Wait for login form to appear"""
        try:
            selectors = self.auth_config.get('selectors', {}).get('login_page_indicators', [])
            wait = WebDriverWait(self.driver, self.timeouts.get('element_wait', 10))
            
            # Try to find the main form first
            form_selector = self.auth_config.get('selectors', {}).get('login_form', {}).get('form', 'form.space-y-4')
            
            try:
                # Wait for the specific form
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, form_selector)))
                logger.debug(f"Login form found with selector: {form_selector}")
                return True
            except:
                # Fall back to other indicators
                for selector in selectors:
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        logger.debug(f"Login form indicator found: {selector}")
                        return True
                    except:
                        continue
            
            return False
        except Exception as e:
            logger.error(f"Error waiting for login form: {e}")
            return False
    
    def _fill_credentials(self) -> bool:
        """Fill email and password"""
        try:
            form_selectors = self.auth_config.get('selectors', {}).get('login_form', {})
            
            # Email field - using name attribute which is more stable
            email_selector = form_selectors.get('email', "input[name='email']")
            email_field = self._find_element(email_selector)
            
            if not email_field:
                # Try alternative selectors
                alt_selectors = ["input[type='text'][placeholder*='email']", "#:r0:-form-item"]
                for selector in alt_selectors:
                    email_field = self._find_element(selector)
                    if email_field:
                        break
            
            if email_field:
                email_field.clear()
                email_field.send_keys(self.email)
                logger.debug("Email field filled")
            else:
                logger.error("Email field not found")
                return False
            
            # Password field
            password_selector = form_selectors.get('password', "input[name='password']")
            password_field = self._find_element(password_selector)
            
            if not password_field:
                # Try alternative selectors
                alt_selectors = ["input[type='password']", "#:r1:-form-item"]
                for selector in alt_selectors:
                    password_field = self._find_element(selector)
                    if password_field:
                        break
            
            if password_field:
                password_field.clear()
                password_field.send_keys(self.password)
                logger.debug("Password field filled")
            else:
                logger.error("Password field not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill credentials: {e}")
            return False

    
    def _submit_form(self) -> bool:
        """Submit login form"""
        try:
            form_selectors = self.auth_config.get('selectors', {}).get('login_form', {})
            submit_selector = form_selectors.get('submit', "button[type='submit']")
            
            # Try to find submit button
            submit_button = self._find_element(submit_selector)
            
            if not submit_button:
                # Try by text content
                try:
                    submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
                except:
                    pass
            
            if submit_button:
                # Check if button is enabled
                if submit_button.is_enabled():
                    submit_button.click()
                    logger.debug("Login form submitted")
                    return True
                else:
                    logger.error("Submit button is disabled")
                    return False
            
            logger.error("Submit button not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to submit form: {e}")
            return False
    
    def _find_element(self, selector: str):
        """Find element with multiple selector support"""
        # Handle multiple selectors (comma-separated)
        for single_selector in selector.split(','):
            single_selector = single_selector.strip()
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, single_selector)
                if element.is_displayed():
                    return element
            except:
                continue
        return None
    
    def logout(self) -> bool:
        """Logout and clear session"""
        try:
            # Clear session for this user
            self.session_manager.clear_session(self.email)
            
            # Try to click logout if possible
            try:
                logout_btn = self.driver.find_element(By.CSS_SELECTOR, "a[href*='logout']")
                logout_btn.click()
            except:
                pass
            
            logger.info(f"Logged out and cleared session for {self.email}")
            return True
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    def switch_user(self, new_email: str, new_password: str) -> AuthResult:
        """Switch to different user account"""
        self.email = new_email
        self.password = new_password
        logger.info(f"Switching to user: {new_email}")
        return self.ensure_logged_in()


class SessionManager:
    """
    Manages user sessions with proper organization
    """
    
    def __init__(self, base_dir: Path = Path("data/sessions")):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Session manager initialized at {self.base_dir}")
    
    def _get_user_dir(self, email: str) -> Path:
        """Get user-specific directory (sanitized email)"""
        # Sanitize email for filesystem
        sanitized = email.lower().replace('@', '_at_').replace('.', '_dot_')
        user_dir = self.base_dir / sanitized
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _get_session_file(self, email: str, archive: bool = False) -> Path:
        """Get session file path for user"""
        user_dir = self._get_user_dir(email)
        
        if archive:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return user_dir / f"session_{timestamp}.pkl"
        else:
            return user_dir / "session.pkl"  # Current session
    
    def _get_metadata_file(self, email: str) -> Path:
        """Get metadata file path for user"""
        return self._get_user_dir(email) / "metadata.json"
    
    def save_session(self, driver: WebDriver, email: str) -> SessionInfo:
        """
        Save current session with metadata
        
        Args:
            driver: Selenium WebDriver
            email: User email
            
        Returns:
            SessionInfo object
        """
        user_dir = self._get_user_dir(email)
        session_file = self._get_session_file(email)
        metadata_file = self._get_metadata_file(email)
        
        # Archive existing session if it exists
        if session_file.exists():
            archive_file = self._get_session_file(email, archive=True)
            session_file.rename(archive_file)
            logger.info(f"Archived previous session to {archive_file}")
        
        # Save cookies
        cookies = driver.get_cookies()
        with open(session_file, 'wb') as f:
            pickle.dump(cookies, f)
        
        # Create session info
        session_info = SessionInfo(
            user_id=hashlib.md5(email.encode()).hexdigest()[:12],
            email=email,
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(days=7)).isoformat(),
        )
        
        # Save metadata
        with open(metadata_file, 'w') as f:
            json.dump(asdict(session_info), f, indent=2)
        
        logger.info(f"Session saved for {email} at {session_file}")
        return session_info
    
    def load_session(self, driver: WebDriver, email: str) -> Optional[SessionInfo]:
        """
        Load session for user if valid
        
        Args:
            driver: Selenium WebDriver
            email: User email
                
        Returns:
            SessionInfo if loaded successfully, None otherwise
        """
        session_file = self._get_session_file(email)
        metadata_file = self._get_metadata_file(email)
        
        # Check if session exists
        if not session_file.exists() or not metadata_file.exists():
            logger.info(f"No session found for {email}")
            return None
        
        # Load metadata
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                session_info = SessionInfo(**metadata)
        except Exception as e:
            logger.error(f"Failed to load metadata for {email}: {e}")
            return None
        
        # Check if session is expired
        if session_info.is_expired():
            logger.info(f"Session expired for {email} (expired: {session_info.expires_at})")
            self.clear_session(email)
            return None
        
        # Load cookies
        try:
            with open(session_file, 'rb') as f:
                cookies = pickle.load(f)
            
            # Navigate to domain first
            driver.get("https://ehub.alxafrica.com")
            
            # Add cookies - silently ignore SameSite errors
            successful_cookies = 0
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                    successful_cookies += 1
                except Exception as e:
                    # Log only at debug level for SameSite errors
                    if "SameSite" in str(e):
                        logger.debug(f"Skipped cookie {cookie.get('name')} - SameSite restriction")
                    else:
                        logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")
                    continue
            
            logger.debug(f"Loaded {successful_cookies}/{len(cookies)} cookies")
            
            # Refresh to apply cookies
            driver.refresh()
            
            # Update last used
            session_info.last_used = datetime.now().isoformat()
            with open(metadata_file, 'w') as f:
                json.dump(asdict(session_info), f, indent=2)
            
            logger.info(f"Session loaded for {email}")
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to load cookies for {email}: {e}")
            return None
        
    def clear_session(self, email: str) -> bool:
        """
        Clear all session data for a specific user
        
        Args:
            email: User email
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_dir = self._get_user_dir(email)
            
            # Delete session file
            session_file = user_dir / "session.pkl"
            if session_file.exists():
                session_file.unlink()
                logger.debug(f"Deleted session file: {session_file}")
            
            # Delete metadata file
            metadata_file = user_dir / "metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()
                logger.debug(f"Deleted metadata file: {metadata_file}")
            
            # Remove user directory if empty
            if user_dir.exists() and not any(user_dir.iterdir()):
                user_dir.rmdir()
                logger.debug(f"Removed empty directory: {user_dir}")
            
            logger.info(f"Session cleared for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear session for {email}: {e}")
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions with metadata"""
        sessions = []
        
        for user_dir in self.base_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            metadata_file = user_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        sessions.append(metadata)
                except:
                    continue
        
        return sessions
