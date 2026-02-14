# src/alx_ehub_course_scraper/courses/course_finder.py
import logging
import re
import time
import json
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime
from enum import Enum

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from .models import Course, CourseList
from .exceptions import CourseNotFoundError, CourseParsingError

# Create logger
logger = logging.getLogger(__name__)

class Platform(Enum):
    """Supported platforms"""
    ATHENA = "athena"
    SAVANNAH = "savannah"
    UNKNOWN = "unknown"

class CourseFinder:
    """
    Discovers and extracts all courses from ALL platforms (Athena & Savannah)
    Uses the EXISTING authenticated driver from main.py
    """
    
    def __init__(self, driver: WebDriver, config: Dict[str, Any]):
        """
        Initialize CourseFinder with EXISTING driver
        
        Args:
            driver: Selenium WebDriver (ALREADY AUTHENTICATED from main.py)
            config: Configuration dictionary (from Config class)
        """
        self.driver = driver
        self.config = config
        
        # Load course config
        self.course_config = config.get('courses', {})
        self.selectors = self.course_config.get('course_selectors', {})
        self.page_config = self.course_config.get('course_page', {})
        
        # Base URLs
        self.athena_base_url = "https://ehub.alxafrica.com"
        self.savannah_base_url = "https://savannah.alxafrica.com"
        
        # Create directories for captures
        self.athena_debug_dir = Path("data/athena_pages")
        self.savannah_debug_dir = Path("data/savannah_pages")
        self.athena_debug_dir.mkdir(parents=True, exist_ok=True)
        self.savannah_debug_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ CourseFinder initialized with multi-platform support")
    
    def find_all_courses(self, save_debug: bool = False, explore_platforms: bool = True) -> CourseList:
        """
        Main method - returns all courses found on ALL platforms
        
        Args:
            save_debug: Save debug HTML for analysis
            explore_platforms: Whether to enter Savannah and Athena and explore
            
        Returns:
            CourseList object containing all courses from all platforms
        """
        logger.info("Starting multi-platform course discovery")
        all_courses = []
        
        try:
            # STEP 1: Discover dashboard courses (main page)
            logger.info("🔍 Discovering dashboard courses...")
            dashboard_courses = self._discover_dashboard_courses(save_debug)
            all_courses.extend(dashboard_courses)
            logger.info(f"✅ Found {len(dashboard_courses)} dashboard courses")
            
            # STEP 2: Discover Savannah courses if requested
            if explore_platforms:
                logger.info("🔍 Discovering Savannah courses...")
                savannah_courses = self._discover_savannah_courses(save_debug)
                all_courses.extend(savannah_courses)
                logger.info(f"✅ Found {len(savannah_courses)} Savannah courses")
                
                # STEP 3: Discover Athena courses - USING CORRECT METHOD NAME
                logger.info("🔍 Discovering Athena courses...")
                athena_courses = self._explore_athena_platforms(save_debug)  # <-- FIXED: _explore_athena_platforms
                all_courses.extend(athena_courses)
                logger.info(f"✅ Found {len(athena_courses)} Athena courses")
            
            # STEP 4: Save comprehensive report
            if save_debug:
                self._save_discovery_report(all_courses)
            
            logger.info(f"✅ Total courses discovered: {len(all_courses)}")
            return CourseList(all_courses)
            
        except Exception as e:
            logger.error(f"Course discovery failed: {e}", exc_info=True)
            raise CourseNotFoundError(f"Failed to discover courses: {e}")
        

    def _ensure_on_dashboard(self):
        """Ensure we're on the main dashboard page"""
        current_url = self.driver.current_url
        logger.debug(f"Current URL: {current_url}")
        
        # If not on dashboard, navigate to it
        if "ehub.alxafrica.com" not in current_url or "/login" in current_url:
            logger.info("Navigating to dashboard")
            self.driver.get("https://ehub.alxafrica.com")
            time.sleep(3)
        
    def _discover_dashboard_courses(self, save_debug: bool = False) -> List[Course]:
        """Discover courses on the main dashboard page"""
        courses = []
        
        try:
            # Ensure on dashboard
            self._ensure_on_dashboard()
            
            # Wait for courses
            self._wait_for_courses()
            
            # Save debug HTML
            if save_debug:
                self._save_dashboard_debug()
            
            # Get containers
            containers = self._get_course_containers()
            logger.info(f"Found {len(containers)} dashboard course containers")
            
            for container in containers:
                try:
                    course = self._parse_course(container)
                    if course:
                        # Check if this is the Savannah entry point
                        if course.name == "Professional Foundations":
                            course.platform = Platform.SAVANNAH  # Mark as Savannah
                        else:
                            course.platform = Platform.ATHENA    # Mark as Athena
                        courses.append(course)
                        logger.debug(f"✅ Parsed dashboard course: {course.name} [{course.platform.value}]")
                except Exception as e:
                    logger.error(f"Failed to parse dashboard course: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Dashboard discovery failed: {e}")
        
        return courses

    def _save_dashboard_debug(self):
        """Save dashboard page HTML for analysis"""
        try:
            debug_dir = Path("data/dashboard_pages")
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = debug_dir / f"dashboard_{timestamp}.html"
            
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            logger.info(f"📄 Dashboard debug HTML saved: {html_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save dashboard debug: {e}")


    def _explore_athena_platforms(self, save_debug: bool) -> List[Course]:
        """
        Click into each Athena course and explore its platform
        """
        athena_courses = []
        athena_names = ["Data Analytics", "Python", "Machine Learning"]
        
        for course_name in athena_names:
            try:
                if self._enter_athena(course_name):
                    # Parse Athena platform content
                    # TODO: After analyzing saved HTML, implement proper parsing
                    logger.info(f"🔍 Need to parse Athena: {course_name}")
                    
                    # Return to dashboard
                    self.driver.back()
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Failed to explore {course_name}: {e}")
                self.driver.get(self.athena_base_url)
                time.sleep(3)
        
        return athena_courses
    
    def _discover_athena_courses(self, save_debug: bool = False) -> List[Course]:
        """Discover courses on Athena platform (main dashboard)"""
        courses = []
        
        try:
            # Ensure on Athena dashboard
            self._ensure_on_athena_dashboard()
            
            # Wait for courses
            self._wait_for_courses()
            
            # Save debug HTML
            if save_debug:
                self._save_athena_debug()
            
            # Get containers
            containers = self._get_course_containers()
            
            for container in containers:
                try:
                    course = self._parse_course(container)
                    if course:
                        course.platform = Platform.ATHENA
                        courses.append(course)
                except Exception as e:
                    logger.error(f"Failed to parse Athena course: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Athena discovery failed: {e}")
        
        return courses
    
    def _discover_savannah_courses(self, save_debug: bool = False) -> List[Course]:
        """
        Discover courses on Savannah platform
        """
        courses = []
        original_window = self.driver.current_window_handle
        
        try:
            # Step 1: Enter Savannah
            if not self._enter_savannah():
                logger.warning("Could not enter Savannah")
                return courses
            
            # Step 2: Wait for page to load
            time.sleep(3)
            
            # Step 3: Save debug HTML
            if save_debug:
                self._save_savannah_debug()
            
            # Step 4: Parse courses from dropdown
            courses = self._parse_savannah_courses()
            
            # Step 5: Return to Athena
            self._return_to_dashboard(original_window)
            
        except Exception as e:
            logger.error(f"Savannah discovery failed: {e}")
            self._return_to_dashboard(original_window)
        
        return courses
    
    def _enter_athena(self, course_name: str) -> bool:
        """
        Click on a specific Athena course to enter its platform
        """
        try:
            containers = self._get_course_containers()
            
            for container in containers:
                name = self._extract_name(container)
                if name and name == course_name:
                    logger.info(f"🚀 Entering Athena: {course_name}")
                    
                    button = container.find_element(By.CSS_SELECTOR, "button")
                    button.click()
                    time.sleep(5)
                    
                    # Save Athena page for analysis
                    self._save_athena_platform_debug(course_name)
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Failed to enter Athena {course_name}: {e}")
            return False

    def _save_athena_platform_debug(self, course_name: str):
        """Save Athena platform page for analysis"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = course_name.lower().replace(' ', '_')
            
            html_file = self.athena_debug_dir / f"athena_{safe_name}_{timestamp}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"📄 Athena platform HTML saved: {html_file}")
            
            screenshot = self.athena_debug_dir / f"athena_{safe_name}_{timestamp}.png"
            self.driver.save_screenshot(str(screenshot))
            logger.info(f"📸 Athena screenshot saved: {screenshot}")
            
        except Exception as e:
            logger.error(f"Failed to save Athena debug: {e}")
    
    def _return_to_dashboard(self, original_window: str = None):
        """Return to main ehub dashboard from any platform (Savannah or Athena)"""
        try:
            # If we have multiple windows, close the platform tab
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                if original_window:
                    self.driver.switch_to.window(original_window)
                logger.info("✅ Closed platform tab, returned to dashboard")
            else:
                # Same tab - go back
                self.driver.back()
                time.sleep(3)
            
            # Ensure we're on the main dashboard
            if "ehub.alxafrica.com" not in self.driver.current_url:
                self.driver.get(self.athena_base_url)  # This should be dashboard_base_url
                time.sleep(3)
            
            logger.info(f"📍 Returned to dashboard: {self.driver.current_url}")
                
        except Exception as e:
            logger.error(f"Failed to return to dashboard: {e}")
            self.driver.get("https://ehub.alxafrica.com")  # Force to dashboard
    
    def _enter_savannah(self) -> bool:
        """
        Find and click the Professional Foundations button to enter Savannah
        """
        try:
            # Store current window handle
            original_window = self.driver.current_window_handle
            
            # Look for Professional Foundations course
            containers = self._get_course_containers()
            
            for container in containers:
                try:
                    name = self._extract_name(container)
                    
                    if name and "Professional Foundations" in name:
                        logger.info(f"✅ Found Savannah entry: {name}")
                        
                        button = container.find_element(By.CSS_SELECTOR, "button")
                        if button and button.is_displayed():
                            logger.info("🚀 Clicking to enter Savannah...")
                            button.click()
                            time.sleep(5)
                            
                            # Check if new tab opened
                            if len(self.driver.window_handles) > 1:
                                new_window = [w for w in self.driver.window_handles if w != original_window][0]
                                self.driver.switch_to.window(new_window)
                                logger.info(f"✅ Switched to new tab: {self.driver.current_url}")
                                
                                # SAVE HTML
                                self._save_savannah_debug()
                                
                                # RETURN TRUE - WE ARE IN SAVANNAH!
                                return True
                            
                            # Check if same tab navigation
                            current_url = self.driver.current_url.lower()
                            if "savanna" in current_url:
                                logger.info(f"✅ In Savannah: {current_url}")
                                self._save_savannah_debug()
                                return True
                                
                except Exception as e:
                    logger.debug(f"Error: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to enter Savannah: {e}")
            return False
            
    def _parse_savannah_courses(self) -> List[Course]:
        """
        Parse courses within Savannah platform
        Courses are in a dropdown menu structure
        """
        courses = []
        
        try:
            # Get Savannah config
            savannah_config = self.config.get('savannah', {})
            selectors = savannah_config.get('selectors', {})
            
            # Step 1: Get current selected course
            current_course = None
            try:
                current_elem = self.driver.find_element(By.CSS_SELECTOR, 
                    "#student-switch-curriculum .fs-4.fw-semibold")
                if current_elem:
                    current_course = current_elem.text.strip()
                    logger.info(f"📌 Current Savannah course: {current_course}")
            except:
                pass
            
            # Step 2: Click the dropdown to reveal all courses
            logger.info("🔽 Opening Savannah dropdown...")
            dropdown = self.driver.find_element(By.CSS_SELECTOR, 
                "#student-switch-curriculum .btn-group > div")
            dropdown.click()
            time.sleep(2)
            
            # Step 3: Get all course items
            course_items = self.driver.find_elements(By.CSS_SELECTOR, 
                ".dropdown-menu-400.fs-5.dropdown-menu li")
            
            logger.info(f"📚 Found {len(course_items)} courses in Savannah dropdown")
            
            # Step 4: Parse each course
            for item in course_items:
                try:
                    # Find the link
                    link = item.find_element(By.CSS_SELECTOR, "a.dropdown-item")
                    
                    # Extract course name
                    name = None
                    try:
                        name_elem = link.find_element(By.CSS_SELECTOR, 
                            ".fs-4.fw-medium, span:first-child")
                        name = name_elem.text.strip()
                    except:
                        name = link.text.split('\n')[0].strip()
                    
                    if not name:
                        continue
                    
                    # Extract href
                    href = link.get_attribute('href')
                    
                    # Extract average if available
                    average = None
                    try:
                        avg_elem = link.find_element(By.CSS_SELECTOR, ".text-muted .fw-medium")
                        if avg_elem:
                            average = avg_elem.text.strip()
                    except:
                        pass
                    
                    # Check if this is the active course
                    is_active = False
                    try:
                        item.find_element(By.CSS_SELECTOR, ".fa-check")
                        is_active = True
                    except:
                        pass
                    
                    # Create course object
                    course = Course(
                        name=name,
                        platform=Platform.SAVANNAH,
                        description=f"Average: {average}" if average else "Savannah course",
                        status="Current" if is_active else "Available",
                        button_text="View Course",
                        button_link=href,
                        metadata={'average': average, 'is_active': is_active}
                    )
                    
                    courses.append(course)
                    logger.debug(f"✅ Parsed Savannah course: {name}")
                    
                except Exception as e:
                    logger.debug(f"Failed to parse Savannah course: {e}")
                    continue
            
            # Step 5: Close dropdown
            try:
                self.driver.find_element(By.CSS_SELECTOR, "body").click()
                time.sleep(1)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Failed to parse Savannah courses: {e}")
        
        return courses

    def _extract_curriculum_id(self, href: str) -> Optional[str]:
        """Extract curriculum ID from href like /curriculums/1/observe"""
        try:
            match = re.search(r'/curriculums/(\d+)/', href)
            if match:
                return match.group(1)
        except:
            pass
        return None
    
    def _ensure_on_athena_dashboard(self):
        """Ensure we're on the Athena dashboard page"""
        current_url = self.driver.current_url
        logger.debug(f"Current URL: {current_url}")
        
        # If not on dashboard, navigate to it
        if "ehub.alxafrica.com" not in current_url or "/login" in current_url:
            logger.info("Navigating to Athena dashboard")
            self.driver.get(self.athena_base_url)
            time.sleep(3)
    
    def _wait_for_courses(self):
        """Wait for courses to load"""
        timeout = self.page_config.get('timeout', 10)
        wait_for = self.page_config.get('wait_for', '.flex.gap-6.my-4')
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )
            logger.debug("✅ Courses loaded successfully")
        except TimeoutException:
            logger.warning(f"⚠️ Timeout waiting for courses with selector: {wait_for}")
            # Try to scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            # Try one more time
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                )
                logger.debug("✅ Courses loaded after scroll")
            except:
                logger.warning("⚠️ Still no courses found after scrolling")
    
    def _get_course_containers(self) -> List[WebElement]:
        """Get all course container elements"""
        container_selector = self.selectors.get('container', '.flex.gap-6.my-4')
        
        try:
            containers = self.driver.find_elements(By.CSS_SELECTOR, container_selector)
            logger.debug(f"Found {len(containers)} elements with selector: {container_selector}")
            return containers
        except Exception as e:
            logger.error(f"Failed to get course containers: {e}")
            return []
    
    def _parse_course(self, container: WebElement) -> Optional[Course]:
        """
        Parse a single course container into a Course object
        """
        try:
            # Extract basic info
            name = self._extract_name(container)
            if not name:
                logger.debug("❌ Course name not found, skipping")
                return None
            
            logger.debug(f"Found course: {name}")
            
            description = self._extract_description(container)
            date, duration = self._extract_metadata(container)
            status = self._extract_status(container)
            button_text, button_link = self._extract_button_info(container)
            icon_svg = self._extract_icon(container)
            
            # Create course object
            course = Course(
                name=name,
                platform=Platform.ATHENA,  # Default to Athena, will be overridden if in Savannah
                description=description,
                start_date=date,
                duration=duration,
                status=status,
                button_text=button_text,
                button_link=button_link,
                icon_svg=icon_svg
            )
            
            logger.debug(f"✅ Successfully parsed: {course.name} [{course.status}]")
            return course
            
        except StaleElementReferenceException:
            logger.warning("Stale element reference, retrying...")
            return None
        except Exception as e:
            logger.error(f"Error parsing course: {e}")
            return None
    
    def _extract_name(self, container: WebElement) -> Optional[str]:
        """Extract course name using multiple selectors"""
        name_selectors = self.selectors.get('name', {})
        
        # Try primary selector (for mobile view)
        primary = name_selectors.get('primary')
        if primary:
            try:
                elements = container.find_elements(By.CSS_SELECTOR, primary)
                for el in elements:
                    if el.text and el.is_displayed():
                        name = el.text.strip()
                        logger.debug(f"✅ Found name with primary selector '{primary}': {name}")
                        return name
            except Exception as e:
                logger.debug(f"Primary selector failed: {e}")
        
        # Try secondary selector (for desktop view)
        secondary = name_selectors.get('secondary')
        if secondary:
            try:
                elements = container.find_elements(By.CSS_SELECTOR, secondary)
                for el in elements:
                    if el.text and el.is_displayed():
                        name = el.text.strip()
                        logger.debug(f"✅ Found name with secondary selector '{secondary}': {name}")
                        return name
            except Exception as e:
                logger.debug(f"Secondary selector failed: {e}")
        
        # Try fallback - look for any span with text that might be a course name
        try:
            spans = container.find_elements(By.CSS_SELECTOR, "span")
            for span in spans:
                text = span.text.strip()
                if text and 3 < len(text) < 50 and span.is_displayed():
                    # Check if it looks like a course name
                    if not any(x in text.lower() for x in ['completed', 'continue', 'start', 'weeks', 'months']):
                        logger.debug(f"✅ Found name with fallback span: {text}")
                        return text
        except:
            pass
        
        return None
    
    def _extract_description(self, container: WebElement) -> Optional[str]:
        """Extract course description"""
        selector = self.selectors.get('description', 'p.text-sm.text-popover-foreground')
        
        try:
            elements = container.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.text and el.is_displayed():
                    desc = el.text.strip()
                    logger.debug(f"Found description: {desc[:50]}...")
                    return desc
        except:
            pass
        
        return None
    
    def _extract_metadata(self, container: WebElement) -> Tuple[Optional[str], Optional[str]]:
        """Extract date and duration"""
        metadata_config = self.selectors.get('metadata', {})
        container_selector = metadata_config.get('container', '.flex.flex-wrap.gap-1.items-center')
        
        date = None
        duration = None
        
        try:
            # Find metadata container
            meta_containers = container.find_elements(By.CSS_SELECTOR, container_selector)
            
            for meta in meta_containers:
                text = meta.text
                if not text:
                    continue
                
                logger.debug(f"Metadata text: {text}")
                
                # Try to extract date (looks like "DD MMM YYYY")
                date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
                if date_match and not date:
                    date = date_match.group(1)
                    logger.debug(f"Found date: {date}")
                
                # Try to extract duration (looks like "X weeks" or "X months")
                duration_match = re.search(r'(\d+\s+(week|month|year)s?)', text, re.IGNORECASE)
                if duration_match and not duration:
                    duration = duration_match.group(1)
                    logger.debug(f"Found duration: {duration}")
            
        except Exception as e:
            logger.debug(f"Failed to extract metadata: {e}")
        
        return date, duration
    
    def _extract_status(self, container: WebElement) -> str:
        """Extract course status (Completed, In Progress, etc.)"""
        status_config = self.selectors.get('status_badge', {})
        selector = status_config.get('selector', '.text-success')
        completed_text = status_config.get('completed_text', 'Completed')
        
        try:
            # Check for status badge
            badges = container.find_elements(By.CSS_SELECTOR, selector)
            for badge in badges:
                if badge.is_displayed() and completed_text in badge.text:
                    logger.debug("Found Completed status")
                    return "Completed"
        except:
            pass
        
        # Check button text for status clues
        try:
            button = container.find_element(By.CSS_SELECTOR, "button")
            if button and button.is_displayed():
                button_text = button.text.lower()
                if 'continue' in button_text:
                    logger.debug("Found In Progress status (Continue button)")
                    return "In Progress"
                elif 'start' in button_text:
                    logger.debug("Found Not Started status (Start button)")
                    return "Not Started"
        except:
            pass
        
        return "Unknown"
    
    def _extract_button_info(self, container: WebElement) -> Tuple[Optional[str], Optional[str]]:
        """Extract button text and link using multiple strategies"""
        try:
            # Find button
            buttons = container.find_elements(By.CSS_SELECTOR, "button")
            
            for button in buttons:
                if not button.is_displayed():
                    continue
                
                button_text = button.text.strip() if button.text else None
                logger.debug(f"Found button: {button_text}")
                
                # Try multiple strategies to extract URL
                url = self._extract_url_from_attributes(button)
                if url:
                    return button_text, url
                
                # Check onclick
                onclick = button.get_attribute('onclick')
                if onclick:
                    url = self._extract_url_from_onclick(onclick)
                    if url:
                        return button_text, url
                
                # Check parent link
                url = self._extract_url_from_parent(button)
                if url:
                    return button_text, url
                
                return button_text, None
                
        except Exception as e:
            logger.debug(f"Failed to extract button info: {e}")
        
        return None, None
    
    def _extract_icon(self, container: WebElement) -> Optional[str]:
        """Extract icon SVG as string"""
        try:
            # Try to find SVG icon
            icons = container.find_elements(By.CSS_SELECTOR, "svg")
            for icon in icons:
                if icon.is_displayed():
                    # Get the SVG as string
                    return icon.get_attribute('outerHTML')
        except Exception as e:
            logger.debug(f"Failed to extract icon: {e}")
        
        return None

    def _extract_url_from_attributes(self, element: WebElement) -> Optional[str]:
        """Check all element attributes for URL-like values"""
        try:
            # Get all attributes using JavaScript
            attrs = self.driver.execute_script("""
                var attrs = {};
                for (var i = 0; i < arguments[0].attributes.length; i++) {
                    var attr = arguments[0].attributes[i];
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            """, element)
            
            # List of attribute names that might contain URLs
            url_attrs = [
                'data-url', 'data-href', 'data-link', 'data-path',
                'data-course-url', 'data-redirect', 'data-target',
                'href', 'data-src', 'data-action'
            ]
            
            for attr_name, attr_value in attrs.items():
                # Check if attribute name contains URL-related keywords
                if any(url_attr in attr_name.lower() for url_attr in ['url', 'href', 'link', 'path', 'redirect']):
                    if attr_value and len(attr_value) > 5:
                        url = attr_value.strip()
                        if url.startswith('/'):
                            url = f"{self.athena_base_url}{url}"
                        return url
                
                # Check if attribute value looks like a URL
                if attr_value and isinstance(attr_value, str):
                    if attr_value.startswith(('http', '/', './', '../')):
                        if attr_value.startswith('/'):
                            attr_value = f"{self.athena_base_url}{attr_value}"
                        return attr_value
                        
        except Exception as e:
            logger.debug(f"Error extracting attributes: {e}")
        
        return None
    
    def _extract_url_from_onclick(self, onclick: str) -> Optional[str]:
        """Extract URL from onclick attribute"""
        patterns = [
            r"['\"](/[^'\"]*)['\"]",
            r"['\"](https?://[^'\"]*)['\"]",
            r"window\.location[= ]+['\"]([^'\"]*)['\"]",
            r"location\.href[= ]+['\"]([^'\"]*)['\"]"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, onclick)
            if match:
                url = match.group(1)
                if url.startswith('/'):
                    url = f"{self.athena_base_url}{url}"
                return url
        
        return None
    
    def _extract_url_from_parent(self, element: WebElement) -> Optional[str]:
        """Check if element is inside a link"""
        try:
            parent_link = element.find_element(By.XPATH, './ancestor::a')
            href = parent_link.get_attribute('href')
            if href and href != '#' and 'javascript:' not in href:
                return href
        except:
            pass
        
        return None
    
    def _save_athena_debug(self):
        """Save Athena page HTML for analysis"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.athena_debug_dir / f"athena_page_{timestamp}.html"
            
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            logger.info(f"📄 Athena debug HTML saved: {html_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save Athena debug HTML: {e}")
    
    def _save_savannah_debug(self):
        """Save Savannah page HTML for analysis"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.savannah_debug_dir / f"savannah_page_{timestamp}.html"
            screenshot_file = self.savannah_debug_dir / f"savannah_page_{timestamp}.png"
            
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"📄 Savannah HTML saved: {html_file}")
            
            self.driver.save_screenshot(str(screenshot_file))
            logger.info(f"📸 Savannah screenshot saved: {screenshot_file}")
            
            logger.info(f"📍 Savannah URL: {self.driver.current_url}")
            logger.info(f"📌 Savannah title: {self.driver.title}")
            
        except Exception as e:
            logger.warning(f"Failed to save Savannah debug: {e}")
    
    def _save_discovery_report(self, courses: List[Course]):
        """Save comprehensive discovery report"""
        try:
            report_dir = Path("data/discovery_reports")
            report_dir.mkdir(parents=True, exist_ok=True)
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_courses': len(courses),
                'by_platform': {
                    'athena': len([c for c in courses if c.platform == Platform.ATHENA]),
                    'savannah': len([c for c in courses if c.platform == Platform.SAVANNAH])
                },
                'courses': [c.to_dict() for c in courses]
            }
            
            filename = report_dir / f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"📄 Discovery report saved: {filename}")
            
        except Exception as e:
            logger.warning(f"Failed to save discovery report: {e}")
    
    def navigate_to_course(self, course: Course) -> bool:
        """
        Navigate to a specific course by clicking its button
        Used when URL couldn't be extracted directly
        """
        try:
            logger.info(f"Navigating to course: {course.name}")
            
            # If we already have a URL, just go there
            if course.full_url:
                self.driver.get(course.full_url)
                return True
            
            # Otherwise find and click the button
            containers = self._get_course_containers()
            
            for container in containers:
                name = self._extract_name(container)
                if name == course.name:
                    button = container.find_element(By.CSS_SELECTOR, "button")
                    if button and button.is_displayed():
                        logger.debug(f"Clicking button for {course.name}")
                        button.click()
                        time.sleep(3)
                        
                        # Store the URL
                        course.button_link = self.driver.current_url
                        logger.info(f"✅ Navigated to: {course.button_link}")
                        return True
            
            logger.warning(f"Could not find container for {course.name}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to {course.name}: {e}")
            return False
    
    def print_courses_summary(self, course_list: CourseList):
        """Print a nice summary of courses with platform info"""
        print("\n" + "="*70)
        print(f"📚 COURSES FOUND: {len(course_list)}")
        print("="*70)
        
        if not course_list:
            print("   No courses found!")
            return
        
        # Group by platform
        athena_courses = [c for c in course_list if c.platform == Platform.ATHENA]
        savannah_courses = [c for c in course_list if c.platform == Platform.SAVANNAH]
        
        if athena_courses:
            print(f"\n🏛️  ATHENA PLATFORM ({len(athena_courses)} courses):")
            print("-" * 70)
            for i, course in enumerate(athena_courses, 1):
                status_color = "✅" if course.status == "Completed" else "🔄" if course.status == "In Progress" else "⏳"
                accessible = "🔗" if course.is_accessible else "🚫"
                print(f"   {accessible} {status_color}  {i}. {course.name}")
                if course.full_url:
                    print(f"       URL: {course.full_url}")
        
        if savannah_courses:
            print(f"\n🌿 SAVANNAH PLATFORM ({len(savannah_courses)} courses):")
            print("-" * 70)
            for i, course in enumerate(savannah_courses, 1):
                status_color = "✅" if course.status == "Completed" else "🔄" if course.status == "In Progress" else "⏳"
                accessible = "🔗" if course.is_accessible else "🚫"
                print(f"   {accessible} {status_color}  {i}. {course.name}")
                if course.full_url:
                    print(f"       URL: {course.full_url}")
        
        print("\n" + "="*70)
        print(f"✅ Total: {len(course_list)} courses ({len(athena_courses)} Athena, {len(savannah_courses)} Savannah)")
        print("="*70)