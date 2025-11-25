"""Local cache for simulations (for development/offline use)."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class SimulationCache:
    """Cache last N simulations locally."""

    CACHE_DIR = Path(__file__).parent.parent / "export"
    CACHE_FILE = CACHE_DIR / "simulation_cache.json"
    MAX_CACHED = 10

    @classmethod
    def save_simulation(cls, simulation_data: Dict[str, Any]) -> bool:
        """Save simulation to cache."""
        try:
            cls.CACHE_DIR.mkdir(exist_ok=True)
            
            # Load existing cache
            cache = cls._load_cache()
            
            # Add new simulation with metadata
            entry = {
                "id": simulation_data.get("id", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "data": simulation_data
            }
            
            cache.insert(0, entry)  # Most recent first
            cache = cache[:cls.MAX_CACHED]  # Keep last N
            
            # Write back
            with open(cls.CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2, default=str)
            
            return True
        
        except Exception as e:
            print(f"Cache save error: {e}")
            return False

    @classmethod
    def get_simulations(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Get cached simulations."""
        cache = cls._load_cache()
        return [entry["data"] for entry in cache[:limit]]

    @classmethod
    def get_simulation(cls, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get specific simulation from cache."""
        cache = cls._load_cache()
        for entry in cache:
            if entry["data"].get("id") == simulation_id:
                return entry["data"]
        return None

    @classmethod
    def clear_cache(cls) -> bool:
        """Clear cache."""
        try:
            if cls.CACHE_FILE.exists():
                cls.CACHE_FILE.unlink()
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False

    @classmethod
    def _load_cache(cls) -> List[Dict[str, Any]]:
        """Load cache file."""
        if not cls.CACHE_FILE.exists():
            return []
        
        try:
            with open(cls.CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return []
