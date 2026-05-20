"""
Cache module for CDK Diff Summarizer.
Handles caching of AI responses and diff data.
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
from config import CacheConfig


class CacheManager:
    """File-based cache manager for CDK Diff Summarizer."""
    
    def __init__(self, cache_config: CacheConfig):
        self.cache_dir = Path(cache_config.cache_dir)
        self.ttl_seconds = cache_config.ttl_hours * 3600
        self.max_size_bytes = cache_config.max_cache_size_mb * 1024 * 1024
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create cache index file
        self.index_file = self.cache_dir / "cache_index.json"
        self._load_index()
    
    def _load_index(self):
        """Load cache index from file."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load cache index: {e}")
                self.index = {}
        else:
            self.index = {}
    
    def _save_index(self):
        """Save cache index to file."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache index: {e}")
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if key not in self.index:
            return None
        
        cache_info = self.index[key]
        cache_file = self.cache_dir / f"{key}.cache"
        
        if not cache_file.exists():
            # Remove stale index entry
            del self.index[key]
            self._save_index()
            return None
        
        # Check TTL
        if time.time() - cache_info['timestamp'] > self.ttl_seconds:
            # Remove expired cache
            cache_file.unlink()
            del self.index[key]
            self._save_index()
            return None
        
        try:
            with open(cache_file, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Failed to read cache for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str):
        """Set value in cache."""
        cache_file = self.cache_dir / f"{key}.cache"
        
        try:
            # Write cache file
            with open(cache_file, 'w') as f:
                f.write(value)
            
            # Update index
            self.index[key] = {
                'timestamp': time.time(),
                'size': len(value),
                'file': str(cache_file)
            }
            self._save_index()
            
            # Clean up if needed
            self._cleanup_cache()
            
        except Exception as e:
            print(f"Warning: Failed to write cache for key {key}: {e}")
    
    def delete(self, key: str):
        """Delete value from cache."""
        if key in self.index:
            cache_file = self.cache_dir / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
            del self.index[key]
            self._save_index()
    
    def clear(self):
        """Clear all cache entries."""
        try:
            # Remove all cache files
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            
            # Clear index
            self.index = {}
            self._save_index()
            
            print("Cache cleared successfully")
        except Exception as e:
            print(f"Warning: Failed to clear cache: {e}")
    
    def _cleanup_cache(self):
        """Clean up expired cache entries and enforce size limits."""
        try:
            current_time = time.time()
            
            # Remove expired entries
            expired_keys = []
            for key, info in self.index.items():
                if current_time - info['timestamp'] > self.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
            
            # Check total size and remove oldest entries if needed
            total_size = sum(info['size'] for info in self.index.values())
            if total_size > self.max_size_bytes:
                # Sort by timestamp (oldest first)
                sorted_entries = sorted(self.index.items(), key=lambda x: x[1]['timestamp'])
                
                # Remove oldest entries until under size limit
                for key, info in sorted_entries:
                    self.delete(key)
                    total_size -= info['size']
                    if total_size <= self.max_size_bytes:
                        break
                        
        except Exception as e:
            print(f"Warning: Cache cleanup failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            current_time = time.time()
            total_entries = len(self.index)
            total_size = sum(info['size'] for info in self.index.values())
            expired_entries = sum(1 for info in self.index.values() 
                                if current_time - info['timestamp'] > self.ttl_seconds)
            
            return {
                'total_entries': total_entries,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'expired_entries': expired_entries,
                'max_size_bytes': self.max_size_bytes,
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'ttl_hours': self.ttl_seconds / 3600
            }
        except Exception as e:
            print(f"Warning: Failed to get cache stats: {e}")
            return {}


class DiffCache:
    """Specialized cache for CDK diff data."""
    
    def __init__(self, cache_config: CacheConfig):
        self.cache_manager = CacheManager(cache_config)
    
    def get_diff_summary(self, diff_hash: str) -> Optional[str]:
        """Get cached diff summary."""
        return self.cache_manager.get(f"diff_{diff_hash}")
    
    def set_diff_summary(self, diff_hash: str, summary: str):
        """Cache diff summary."""
        self.cache_manager.set(f"diff_{diff_hash}", summary)
    
    def get_ai_response(self, prompt_hash: str) -> Optional[str]:
        """Get cached AI response."""
        return self.cache_manager.get(f"ai_{prompt_hash}")
    
    def set_ai_response(self, prompt_hash: str, response: str):
        """Cache AI response."""
        self.cache_manager.set(f"ai_{prompt_hash}", response)
    
    def create_diff_hash(self, diff_data: Dict[str, Any]) -> str:
        """Create hash for diff data."""
        diff_str = json.dumps(diff_data, sort_keys=True)
        return hashlib.sha256(diff_str.encode()).hexdigest()
    
    def create_prompt_hash(self, prompt: str, model: str, max_tokens: int) -> str:
        """Create hash for AI prompt."""
        prompt_data = f"{prompt}:{model}:{max_tokens}"
        return hashlib.sha256(prompt_data.encode()).hexdigest() 