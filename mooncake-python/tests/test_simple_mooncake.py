"""
Unit tests for SimpleMooncake class
"""

import unittest
import time
import threading
from unittest.mock import patch, MagicMock
from mooncake.core.simple_mooncake import SimpleMooncake


class TestSimpleMooncake(unittest.TestCase):
    """Test cases for SimpleMooncake class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mooncake = SimpleMooncake()
        self.test_key = "test_key"
        self.test_value = "test_value"
        self.test_ttl = 3600
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'mooncake'):
            self.mooncake.cleanup_expired()
    
    def test_put_basic(self):
        """Test basic put operation"""
        # Test successful put
        result = self.mooncake.put(self.test_key, self.test_value, self.test_ttl)
        self.assertTrue(result)
        
        # Test putting None value
        result = self.mooncake.put("none_key", None, self.test_ttl)
        self.assertTrue(result)
        
        # Test putting empty string
        result = self.mooncake.put("empty_key", "", self.test_ttl)
        self.assertTrue(result)
    
    def test_put_with_exception(self):
        """Test put operation with exception"""
        # Mock time.time to raise exception
        with patch('time.time', side_effect=Exception("Time error")):
            result = self.mooncake.put("error_key", "error_value", self.test_ttl)
            self.assertFalse(result)
    
    def test_get_basic(self):
        """Test basic get operation"""
        # Put a value first
        self.mooncake.put(self.test_key, self.test_value, self.test_ttl)
        
        # Get the value
        result = self.mooncake.get(self.test_key)
        self.assertEqual(result, self.test_value)
        
        # Get non-existent key
        result = self.mooncake.get("non_existent_key")
        self.assertIsNone(result)
    
    def test_get_expired_object(self):
        """Test get operation with expired object"""
        # Put a value with very short TTL
        self.mooncake.put(self.test_key, self.test_value, 0.1)  # 100ms TTL
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Try to get expired value
        result = self.mooncake.get(self.test_key)
        self.assertIsNone(result)
        
        # Verify the expired object was cleaned up
        self.assertNotIn(self.test_key, self.mooncake.storage)
    
    def test_get_with_exception(self):
        """Test get operation with exception"""
        # Put a value first
        self.mooncake.put(self.test_key, self.test_value, self.test_ttl)
        
        # Mock time.time to raise exception
        with patch('time.time', side_effect=Exception("Time error")):
            result = self.mooncake.get(self.test_key)
            self.assertIsNone(result)
    
    def test_delete_basic(self):
        """Test basic delete operation"""
        # Put a value first
        self.mooncake.put(self.test_key, self.test_value, self.test_ttl)
        
        # Delete the value
        result = self.mooncake.delete(self.test_key)
        self.assertTrue(result)
        
        # Verify deletion
        result = self.mooncake.get(self.test_key)
        self.assertIsNone(result)
        
        # Delete non-existent key
        result = self.mooncake.delete("non_existent_key")
        self.assertFalse(result)
    
    def test_delete_with_exception(self):
        """Test delete operation with exception"""
        # Mock to cause exception during deletion
        original_storage = self.mooncake.storage
        self.mooncake.storage = MagicMock()
        self.mooncake.storage.__delitem__.side_effect = Exception("Delete error")
        
        result = self.mooncake.delete(self.test_key)
        self.assertFalse(result)
        
        # Restore original storage
        self.mooncake.storage = original_storage
    
    def test_cleanup_expired_basic(self):
        """Test basic cleanup expired operation"""
        # Put multiple values with different TTLs
        self.mooncake.put("key1", "value1", 0.1)  # Will expire
        self.mooncake.put("key2", "value2", 10.0)  # Will not expire
        self.mooncake.put("key3", "value3", 0.1)  # Will expire
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Cleanup expired objects
        cleaned_count = self.mooncake.cleanup_expired()
        self.assertEqual(cleaned_count, 2)
        
        # Verify remaining objects
        self.assertIn("key2", self.mooncake.storage)
        self.assertNotIn("key1", self.mooncake.storage)
        self.assertNotIn("key3", self.mooncake.storage)
    
    def test_cleanup_expired_with_exception(self):
        """Test cleanup expired operation with exception"""
        # Mock to cause exception during cleanup
        original_storage = self.mooncake.storage
        self.mooncake.storage = MagicMock()
        self.mooncake.storage.items.side_effect = Exception("Mock exception")
        
        result = self.mooncake.cleanup_expired()
        self.assertEqual(result, 0)
        
        # Restore original storage
        self.mooncake.storage = original_storage
    
    def test_get_stats_basic(self):
        """Test basic get_stats operation"""
        # Empty stats
        stats = self.mooncake.get_stats()
        self.assertEqual(stats['total_objects'], 0)
        self.assertEqual(stats['total_accesses'], 0)
        self.assertEqual(stats['memory_usage'], 0)
        
        # Put some values
        self.mooncake.put("key1", "value1", self.test_ttl)
        self.mooncake.put("key2", "value2", self.test_ttl)
        
        # Get some values to generate access logs
        self.mooncake.get("key1")
        self.mooncake.get("key2")
        self.mooncake.get("key1")  # Access key1 twice
        
        # Get stats
        stats = self.mooncake.get_stats()
        self.assertEqual(stats['total_objects'], 2)
        self.assertEqual(stats['total_accesses'], 3)
        self.assertGreater(stats['memory_usage'], 0)
    
    def test_concurrent_access(self):
        """Test concurrent access to SimpleMooncake"""
        def worker(worker_id):
            """Worker function for concurrent testing"""
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                # Put
                self.mooncake.put(key, value, self.test_ttl)
                
                # Get
                result = self.mooncake.get(key)
                self.assertEqual(result, value)
                
                # Delete
                self.mooncake.delete(key)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all objects are deleted
        stats = self.mooncake.get_stats()
        self.assertEqual(stats['total_objects'], 0)
    
    def test_large_values(self):
        """Test handling of large values"""
        # Create a large value
        large_value = "x" * 1000000  # 1MB string
        
        # Put large value
        result = self.mooncake.put("large_key", large_value, self.test_ttl)
        self.assertTrue(result)
        
        # Get large value
        result = self.mooncake.get("large_key")
        self.assertEqual(result, large_value)
        
        # Delete large value
        result = self.mooncake.delete("large_key")
        self.assertTrue(result)
    
    def test_special_characters(self):
        """Test handling of special characters in keys and values"""
        # Test special characters in keys
        special_keys = [
            "key with spaces",
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key@with#symbols",
            "key/with/slashes",
            "unicode_key_中文",
            "emoji_key_🚀"
        ]
        
        for key in special_keys:
            value = f"value_for_{key}"
            # Put
            result = self.mooncake.put(key, value, self.test_ttl)
            self.assertTrue(result, f"Failed to put key: {key}")
            
            # Get
            result = self.mooncake.get(key)
            self.assertEqual(result, value, f"Failed to get key: {key}")
            
            # Delete
            result = self.mooncake.delete(key)
            self.assertTrue(result, f"Failed to delete key: {key}")
    
    def test_zero_ttl(self):
        """Test objects with zero TTL (expire immediately)"""
        # Put with zero TTL
        result = self.mooncake.put("zero_ttl_key", "zero_ttl_value", 0)
        self.assertTrue(result)
        
        # Try to get immediately (should be expired)
        result = self.mooncake.get("zero_ttl_key")
        self.assertIsNone(result)
    
    def test_negative_ttl(self):
        """Test objects with negative TTL (treated as zero)"""
        # Put with negative TTL
        result = self.mooncake.put("negative_ttl_key", "negative_ttl_value", -1)
        self.assertTrue(result)
        
        # Try to get immediately (should be expired)
        result = self.mooncake.get("negative_ttl_key")
        self.assertIsNone(result)
    
    def test_overwrite_existing_key(self):
        """Test overwriting existing key"""
        # Put initial value
        self.mooncake.put(self.test_key, "initial_value", self.test_ttl)
        
        # Verify initial value
        result = self.mooncake.get(self.test_key)
        self.assertEqual(result, "initial_value")
        
        # Overwrite with new value
        self.mooncake.put(self.test_key, "new_value", self.test_ttl)
        
        # Verify new value
        result = self.mooncake.get(self.test_key)
        self.assertEqual(result, "new_value")
        
        # Verify stats reflect the overwrite
        stats = self.mooncake.get_stats()
        self.assertEqual(stats['total_objects'], 1)  # Still one object


if __name__ == '__main__':
    unittest.main()