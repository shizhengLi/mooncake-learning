"""
Integration tests for Mooncake Python Implementation
"""

import unittest
import time
import threading
import random
import string
from mooncake import SimpleMooncake, SimpleMonitor, PerformanceMetrics


class TestMooncakeIntegration(unittest.TestCase):
    """Integration tests for Mooncake components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mooncake = SimpleMooncake()
        self.monitor = SimpleMonitor()
        self.test_data = self.generate_test_data()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.mooncake.cleanup_expired()
        self.monitor.reset_metrics()
    
    def generate_test_data(self, count=100):
        """Generate test data for integration tests"""
        test_data = {}
        for i in range(count):
            key = f"key_{i}"
            # Generate random string values of different sizes
            value_length = random.randint(10, 1000)
            value = ''.join(random.choices(string.ascii_letters + string.digits, k=value_length))
            ttl = random.randint(60, 3600)  # 1 minute to 1 hour
            
            test_data[key] = {
                'value': value,
                'ttl': ttl,
                'size': len(value)
            }
        
        return test_data
    
    def test_basic_integration(self):
        """Test basic integration between SimpleMooncake and SimpleMonitor"""
        # Test put operation with monitoring
        for key, data in list(self.test_data.items())[:10]:  # Test first 10 items
            start_time = time.time()
            success = self.mooncake.put(key, data['value'], data['ttl'])
            duration = time.time() - start_time
            
            # Record the operation
            self.monitor.record_operation('put', duration, success, data['size'])
            
            self.assertTrue(success)
        
        # Test get operation with monitoring
        for key, data in list(self.test_data.items())[:10]:
            start_time = time.time()
            result = self.mooncake.get(key)
            duration = time.time() - start_time
            
            success = result is not None
            self.monitor.record_operation('get', duration, success, len(result) if result else 0)
            
            self.assertEqual(result, data['value'])
        
        # Verify monitoring data
        summary = self.monitor.get_performance_summary()
        self.assertIn('put', summary)
        self.assertIn('get', summary)
        
        put_stats = summary['put']
        self.assertEqual(put_stats['count'], 10)
        self.assertEqual(put_stats['success_rate'], 1.0)
        self.assertGreater(put_stats['avg_duration'], 0)
        
        get_stats = summary['get']
        self.assertEqual(get_stats['count'], 10)
        self.assertEqual(get_stats['success_rate'], 1.0)
        self.assertGreater(get_stats['avg_duration'], 0)
    
    def test_stress_integration(self):
        """Test integration under stress"""
        def worker(worker_id, operations_count):
            """Worker function for stress testing"""
            for i in range(operations_count):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                # Put operation
                start_time = time.time()
                success = self.mooncake.put(key, value, 3600)
                duration = time.time() - start_time
                self.monitor.record_operation('put', duration, success, len(value))
                
                # Get operation
                start_time = time.time()
                result = self.mooncake.get(key)
                duration = time.time() - start_time
                success = result is not None
                self.monitor.record_operation('get', duration, success, len(result) if result else 0)
                
                # Delete operation
                start_time = time.time()
                success = self.mooncake.delete(key)
                duration = time.time() - start_time
                self.monitor.record_operation('delete', duration, success)
        
        # Start workers
        num_workers = 5
        operations_per_worker = 20
        workers = []
        
        for i in range(num_workers):
            worker_thread = threading.Thread(target=worker, args=(i, operations_per_worker))
            workers.append(worker_thread)
            worker_thread.start()
        
        # Wait for all workers to complete
        for worker in workers:
            worker.join()
        
        # Verify results
        summary = self.monitor.get_performance_summary()
        total_operations = sum(stats['count'] for stats in summary.values())
        
        # Each worker performs 3 operations per data item
        expected_operations = num_workers * operations_per_worker * 3
        self.assertEqual(total_operations, expected_operations)
        
        # All operations should have succeeded
        for operation, stats in summary.items():
            self.assertEqual(stats['success_rate'], 1.0, 
                           f"Operation {operation} had success rate {stats['success_rate']}")
    
    def test_monitoring_comprehensive(self):
        """Test comprehensive monitoring features"""
        # Perform various operations
        operations = []
        
        # Put operations
        for key, data in list(self.test_data.items())[:20]:
            start_time = time.time()
            success = self.mooncake.put(key, data['value'], data['ttl'])
            duration = time.time() - start_time
            operations.append(('put', duration, success, data['size']))
        
        # Get operations
        for key, data in list(self.test_data.items())[:20]:
            start_time = time.time()
            result = self.mooncake.get(key)
            duration = time.time() - start_time
            success = result is not None
            operations.append(('get', duration, success, len(result) if result else 0))
        
        # Delete operations
        for key in list(self.test_data.keys())[:10]:
            start_time = time.time()
            success = self.mooncake.delete(key)
            duration = time.time() - start_time
            operations.append(('delete', duration, success, 0))
        
        # Cleanup operation
        start_time = time.time()
        cleaned_count = self.mooncake.cleanup_expired()
        duration = time.time() - start_time
        operations.append(('cleanup', duration, True, 0))
        
        # Record all operations
        for op in operations:
            self.monitor.record_operation(*op)
        
        # Test monitoring features
        summary = self.monitor.get_performance_summary()
        
        # Verify all operation types are recorded
        expected_ops = {'put', 'get', 'delete', 'cleanup'}
        self.assertEqual(set(summary.keys()), expected_ops)
        
        # Verify operation counts
        self.assertEqual(summary['put']['count'], 20)
        self.assertEqual(summary['get']['count'], 20)
        self.assertEqual(summary['delete']['count'], 10)
        self.assertEqual(summary['cleanup']['count'], 1)
        
        # Test additional monitoring methods
        self.assertEqual(self.monitor.get_operation_count('put'), 20)
        self.assertEqual(self.monitor.get_operation_success_rate('put'), 1.0)
        self.assertGreater(self.monitor.get_average_duration('put'), 0)
        self.assertGreater(self.monitor.get_total_data_size('put'), 0)
        
        # Test recent metrics
        recent = self.monitor.get_recent_metrics(minutes=1)
        self.assertEqual(len(recent), len(operations))
        
        # Test supported operations
        supported_ops = self.monitor.get_supported_operations()
        self.assertEqual(set(supported_ops), expected_ops)
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios"""
        # Test with invalid data
        invalid_operations = [
            ('put', 'invalid_key', None, 3600),
            ('put', 'empty_key', '', 3600),
            ('get', 'nonexistent_key', None, 0),
            ('delete', 'nonexistent_key', None, 0),
        ]
        
        for op_type, key, value, ttl in invalid_operations:
            start_time = time.time()
            
            if op_type == 'put':
                success = self.mooncake.put(key, value, ttl)
                data_size = len(str(value)) if value is not None else 0
            elif op_type == 'get':
                result = self.mooncake.get(key)
                success = result is not None
                data_size = len(result) if result else 0
            elif op_type == 'delete':
                success = self.mooncake.delete(key)
                data_size = 0
            
            duration = time.time() - start_time
            self.monitor.record_operation(op_type, duration, success, data_size)
        
        # Verify that operations were recorded even with invalid data
        summary = self.monitor.get_performance_summary()
        self.assertIn('put', summary)
        self.assertIn('get', summary)
        self.assertIn('delete', summary)
        
        # Verify that put operations succeeded even with None/empty values
        self.assertEqual(summary['put']['success_rate'], 1.0)
        
        # Verify that get/delete operations on non-existent keys failed appropriately
        self.assertEqual(summary['get']['success_rate'], 0.0)
        self.assertEqual(summary['delete']['success_rate'], 0.0)
    
    def test_performance_benchmark(self):
        """Test performance benchmarking integration"""
        # Benchmark put operations
        put_times = []
        for key, data in list(self.test_data.items())[:50]:
            start_time = time.time()
            success = self.mooncake.put(key, data['value'], data['ttl'])
            duration = time.time() - start_time
            put_times.append(duration)
            self.monitor.record_operation('put', duration, success, data['size'])
        
        # Benchmark get operations
        get_times = []
        for key, data in list(self.test_data.items())[:50]:
            start_time = time.time()
            result = self.mooncake.get(key)
            duration = time.time() - start_time
            get_times.append(duration)
            success = result is not None
            self.monitor.record_operation('get', duration, success, len(result) if result else 0)
        
        # Analyze performance
        summary = self.monitor.get_performance_summary()
        
        # Verify performance metrics
        put_stats = summary['put']
        get_stats = summary['get']
        
        # Put operations should be relatively fast
        self.assertLess(put_stats['avg_duration'], 0.01)  # Less than 10ms
        
        # Get operations should be reasonably fast
        self.assertLess(get_stats['avg_duration'], 0.01)  # Less than 10ms
        
        # All operations should succeed
        self.assertEqual(put_stats['success_rate'], 1.0)
        self.assertEqual(get_stats['success_rate'], 1.0)
        
        # Verify throughput
        total_put_time = sum(put_times)
        total_get_time = sum(get_times)
        
        put_throughput = 50 / total_put_time  # operations per second
        get_throughput = 50 / total_get_time  # operations per second
        
        self.assertGreater(put_throughput, 100)  # More than 100 ops/sec
        self.assertGreater(get_throughput, 1000)  # More than 1000 ops/sec
    
    def test_memory_usage_monitoring(self):
        """Test memory usage monitoring integration"""
        # Get initial stats
        initial_stats = self.mooncake.get_stats()
        initial_memory = initial_stats['memory_usage']
        
        # Add large objects
        large_objects = []
        for i in range(10):
            key = f"large_key_{i}"
            value = "x" * 10000  # 10KB string
            large_objects.append((key, value))
            
            start_time = time.time()
            success = self.mooncake.put(key, value, 3600)
            duration = time.time() - start_time
            self.monitor.record_operation('put', duration, success, len(value))
        
        # Get updated stats
        updated_stats = self.mooncake.get_stats()
        updated_memory = updated_stats['memory_usage']
        
        # Verify memory usage increased
        self.assertGreater(updated_memory, initial_memory)
        
        # Verify memory growth is reasonable
        expected_growth = sum(len(value) for _, value in large_objects)
        actual_growth = updated_memory - initial_memory
        self.assertGreater(actual_growth, expected_growth * 0.8)  # At least 80% of expected
        
        # Verify monitoring captured the operations
        summary = self.monitor.get_performance_summary()
        self.assertIn('put', summary)
        self.assertEqual(summary['put']['count'], 10)
        self.assertEqual(summary['put']['success_rate'], 1.0)
    
    def test_concurrent_monitoring(self):
        """Test concurrent monitoring scenarios"""
        def monitored_worker(worker_id, operations):
            """Worker that performs monitored operations"""
            for op_type, key, value, ttl in operations:
                start_time = time.time()
                
                if op_type == 'put':
                    success = self.mooncake.put(key, value, ttl)
                    data_size = len(str(value)) if value is not None else 0
                elif op_type == 'get':
                    result = self.mooncake.get(key)
                    success = result is not None
                    data_size = len(result) if result else 0
                elif op_type == 'delete':
                    success = self.mooncake.delete(key)
                    data_size = 0
                
                duration = time.time() - start_time
                self.monitor.record_operation(f"{op_type}_worker_{worker_id}", duration, success, data_size)
        
        # Create operations for multiple workers
        num_workers = 3
        all_operations = []
        
        for worker_id in range(num_workers):
            worker_ops = []
            for i in range(20):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                worker_ops.append(('put', key, value, 3600))
                worker_ops.append(('get', key, None, 0))
                worker_ops.append(('delete', key, None, 0))
            
            all_operations.append(worker_ops)
        
        # Start workers
        workers = []
        for worker_id, ops in enumerate(all_operations):
            worker_thread = threading.Thread(target=monitored_worker, args=(worker_id, ops))
            workers.append(worker_thread)
            worker_thread.start()
        
        # Wait for completion
        for worker in workers:
            worker.join()
        
        # Verify monitoring results
        summary = self.monitor.get_performance_summary()
        
        # Each worker should have 3 operation types
        expected_ops = {f"put_worker_{i}" for i in range(num_workers)}
        expected_ops.update({f"get_worker_{i}" for i in range(num_workers)})
        expected_ops.update({f"delete_worker_{i}" for i in range(num_workers)})
        
        self.assertEqual(set(summary.keys()), expected_ops)
        
        # Each worker operation should have 20 operations
        for op in expected_ops:
            self.assertEqual(summary[op]['count'], 20)
            self.assertEqual(summary[op]['success_rate'], 1.0)


if __name__ == '__main__':
    unittest.main()