# src/alx_ehub_course_scraper/courses/models.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json

class Platform(Enum):
    """Supported platforms"""
    DASHBOARD = "dashboard"
    ATHENA = "athena"
    SAVANNAH = "savannah"
    UNKNOWN = "unknown"

@dataclass
class Course:
    """Course data model with platform info"""
    name: str
    platform: Platform = Platform.UNKNOWN
    description: Optional[str] = None
    start_date: Optional[str] = None
    duration: Optional[str] = None
    status: str = "Unknown"
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    icon_svg: Optional[str] = None
    course_id: Optional[str] = None
    parent_course: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.course_id and self.name:
            self.course_id = self.name.lower().replace(' ', '_').replace('-', '_')
    
    @property
    def is_accessible(self) -> bool:
        """Check if course has a working link"""
        return bool(self.button_link) and self.button_link != "#" and "javascript:void" not in self.button_link
    
    @property
    def full_url(self) -> Optional[str]:
        """Get full URL with correct base domain"""
        if not self.button_link:
            return None
        if self.button_link.startswith('http'):
            return self.button_link
        if self.button_link.startswith('/'):
            if self.platform == Platform.SAVANNAH:
                return f"https://savannah.alxafrica.com{self.button_link}"
            else:
                return f"https://ehub.alxafrica.com{self.button_link}"
        return self.button_link
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'platform': self.platform.value,
            'description': self.description,
            'start_date': self.start_date,
            'duration': self.duration,
            'status': self.status,
            'button_text': self.button_text,
            'button_link': self.button_link,
            'full_url': self.full_url,
            'course_id': self.course_id,
            'is_accessible': self.is_accessible
        }
    
    def __repr__(self) -> str:
        return f"Course(name='{self.name}', platform={self.platform.value}, status='{self.status}')"

@dataclass
class CourseList:
    """Collection of courses with helper methods"""
    courses: List[Course] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __len__(self) -> int:
        return len(self.courses)
    
    def __getitem__(self, index):
        return self.courses[index]
    
    def accessible_courses(self) -> List[Course]:
        """Get only accessible courses"""
        return [c for c in self.courses if c.is_accessible]
    
    def by_platform(self, platform: Platform) -> List[Course]:
        """Filter courses by platform"""
        return [c for c in self.courses if c.platform == platform]
    
    def by_status(self, status: str) -> List[Course]:
        """Filter courses by status"""
        return [c for c in self.courses if c.status == status]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_courses': len(self.courses),
            'accessible_courses': len(self.accessible_courses()),
            'by_platform': {
                'athena': len(self.by_platform(Platform.ATHENA)),
                'savannah': len(self.by_platform(Platform.SAVANNAH))
            },
            'courses': [c.to_dict() for c in self.courses]
        }
    
    def save_to_file(self, filepath: str):
        """Save course list to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)