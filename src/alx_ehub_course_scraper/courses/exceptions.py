# src/alx_ehub_course_scraper/courses/exceptions.py
class CourseError(Exception):
    """Base exception for course-related errors"""
    pass

class CourseNotFoundError(CourseError):
    """Raised when no courses are found"""
    pass

class CourseParsingError(CourseError):
    """Raised when a course cannot be parsed"""
    pass

class InvalidCourseDataError(CourseError):
    """Raised when course data is invalid"""
    pass