import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class Config:
    def __init__(self) -> None:
        # Load environment variables
        load_dotenv()
        
        self.base_dir: Path = Path(__file__).parent.parent.parent
        self.config_dir: Path = self.base_dir / "config"
        self.data: Dict[str, Any] = {}
        self._load_all_configs()
        
    def _load_all_configs(self) -> None:
        """Load all configuration files"""
        # Load main settings
        settings_file = self.config_dir / "settings.json"
        with open(settings_file, 'r') as f:
            self.data = json.load(f)
        
        # TODO: Load other configs when needed
        # websites_file = self.config_dir / "websites.json"
        # candidates_file = self.config_dir / "candidates.json"
    
    def get_driver_cache_path(self, browser: str) -> str:
        """Get driver cache path with environment override"""
        browser = browser.lower()
        
        # Check environment override first
        env_var: str = f"{browser.upper()}_DRIVER_CACHE"
        env_path: Optional[str] = os.getenv(env_var)
        
        if env_path:
            path: Path = Path(env_path)
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        
        # Fall back to default
        default_path: Path = self.base_dir / self.data['drivers']['default_cache_path'] / browser
        default_path.mkdir(parents=True, exist_ok=True)
        return str(default_path)
    
    @property
    def default_browser(self) -> str:
        return os.getenv('DEFAULT_BROWSER', self.data['browser_defaults']['default_browser'])
    
    @property
    def headless_mode(self) -> bool:
        env_value = os.getenv('HEADLESS_MODE', str(self.data['browser_defaults']['headless'])).lower()
        return env_value == 'true'