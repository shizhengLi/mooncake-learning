"""
Unit tests for SimpleMonitor and PerformanceMetrics classes
"""

import unittest
import time
import threading
from unittest.mock import patch, MagicMock
from mooncake.monitoring.simple_monitor import SimpleMonitor, PerformanceMetrics


class TestPerformanceMetrics(unittest.TestCase):
    """Test cases for PerformanceMetrics class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.operation = "test_operation"
        self.duration = 0.1
        self.success = True
        self.data_size = 1024
    
    def test_metrics_creation(self):
        """Test PerformanceMetrics creation"""
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            operation=self.operation,
            duration=self.duration,
            success=self.success,
            data_size=self.data_size
        )
        
        self.assertEqual(metrics.operation, self.operation)
        self.assertEqual(metrics.duration, self.duration)
        self.assertEqual(metrics.success, self.success)
        self.assertEqual(metrics.data_size, self.data_size)
        self.assertIsInstance(metrics.timestamp, float)
    
    def test_metrics_with_defaults(self):
        """Test PerformanceMetrics with default values"""
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            operation=self.operation,
            duration=self.duration,
            success=self.success
        )
        
        self.assertEqual(metrics.operation, self.operation)
        self.assertEqual(metrics.duration, self.duration)
        self.assertEqual(metrics.success, self.success)
        self.assertEqual(metrics.data_size, 0)  # Default value


class TestSimpleMonitor(unittest.TestCase):
    """Test cases for SimpleMonitor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = SimpleMonitor()
        self.operation = "test_operation"
        self.duration = 0.1
        self.success = True
        self.data_size = 1024
    
    def test_monitor_initialization(self):
        """Test SimpleMonitor initialization"""
        self.assertEqual(len(self.monitor.metrics), 0)
        self.assertEqual(len(self.monitor.operation_stats), 0)
        self.assertIsNotNone(self.monitor.lock)
    
    def test_record_operation_basic(self):
        """Test basic operation recording"""
        self.monitor.record_operation(
            operation=self.operation,
            duration=self.duration,
            success=self.success,
            data_size=self.data_size
        )
        
        # Check that metric was recorded
        self.assertEqual(len(self.monitor.metrics), 1)
        self.assertEqual(len(self.monitor.operation_stats), 1)
        
        # Check metric details
        metric = self.monitor.metrics[0]
        self.assertEqual(metric.operation, self.operation)
        self.assertEqual(metric.duration, self.duration)
        self.assertEqual(metric.success, self.success)
        self.assertEqual(metric.data_size, self.data_size)
        
        # Check operation stats
        stats = self.monitor.operation_stats[self.operation]
        self.assertEqual(stats['count'], 1)
        self.assertEqual(stats['total_time'], self.duration)
        self.assertEqual(stats['success_count'], 1)
        self.assertEqual(stats['total_size'], self.data_size)
    
    def test_record_operation_failure(self):
        """Test recording failed operation"""
        self.monitor.record_operation(
            operation=self.operation,
            duration=self.duration,
            success=False,  # Failed operation
            data_size=self.data_size
        )
        
        # Check operation stats for failed operation
        stats = self.monitor.operation_stats[self.operation]
        self.assertEqual(stats['count'], 1)
        self.assertEqual(stats['total_time'], self.duration)
        self.assertEqual(stats['success_count'], 0)  # No success count
        self.assertEqual(stats['total_size'], self.data_size)
    
    def test_record_multiple_operations(self):
        """Test recording multiple operations"""
        operations = ["op1", "op2", "op1", "op3", "op1"]
        durations = [0.1, 0.2, 0.15, 0.05, 0.12]
        successes = [True, True, False, True, True]
        data_sizes = [100, 200, 150, 50, 120]
        
        for i in range(len(operations)):
            self.monitor.record_operation(
                operation=operations[i],
                duration=durations[i],
                success=successes[i],
                data_size=data_sizes[i]
            )
        
        # Check total metrics count
        self.assertEqual(len(self.monitor.metrics), 5)
        
        # Check operation stats for op1 (appears 3 times)
        stats_op1 = self.monitor.operation_stats["op1"]
        self.assertEqual(stats_op1['count'], 3)
        self.assertEqual(stats_op1['total_time'], 0.1 + 0.15 + 0.12)
        self.assertEqual(stats_op1['success_count'], 2)  # 2 out of 3 succeeded
        self.assertEqual(stats_op1['total_size'], 100 + 150 + 120)
        
        # Check operation stats for op2 (appears 1 time)
        stats_op2 = self.monitor.operation_stats["op2"]
        self.assertEqual(stats_op2['count'], 1)
        self.assertEqual(stats_op2['total_time'], 0.2)
        self.assertEqual(stats_op2['success_count'], 1)
        self.assertEqual(stats_op2['total_size'], 200)
    
    def test_get_performance_summary(self):
        """Test getting performance summary"""
        # Record some operations
        self.monitor.record_operation("get", 0.1, True, 1024)
        self.monitor.record_operation("get", 0.15, True, 2048)
        self.monitor.record_operation("get", 0.05, False, 512)  # Failed
        self.monitor.record_operation("put", 0.2, True, 4096)
        self.monitor.record_operation("put", 0.25, True, 8192)
        
        summary = self.monitor.get_performance_summary()
        
        # Check get operation summary
        get_summary = summary["get"]
        self.assertEqual(get_summary['count'], 3)
        self.assertAlmostEqual(get_summary['avg_duration'], (0.1 + 0.15 + 0.05) / 3)
        self.assertAlmostEqual(get_summary['success_rate'], 2/3)
        self.assertAlmostEqual(get_summary['avg_data_size'], (1024 + 2048 + 512) / 3)
        
        # Check put operation summary
        put_summary = summary["put"]
        self.assertEqual(put_summary['count'], 2)
        self.assertAlmostEqual(put_summary['avg_duration'], (0.2 + 0.25) / 2)
        self.assertEqual(put_summary['success_rate'], 1.0)
        self.assertAlmostEqual(put_summary['avg_data_size'], (4096 + 8192) / 2)
    
    def test_get_performance_summary_empty(self):
        """Test getting performance summary with no data"""
        summary = self.monitor.get_performance_summary()
        self.assertEqual(len(summary), 0)
    
    def test_get_recent_metrics(self):
        """Test getting recent metrics"""
        # Record operations with timestamps
        base_time = time.time()
        
        self.monitor.record_operation("op1", 0.1, True, 100)
        time.sleep(0.01)  # Small delay
        
        self.monitor.record_operation("op2", 0.2, True, 200)
        time.sleep(0.01)
        
        self.monitor.record_operation("op3", 0.3, True, 300)
        
        # Get recent metrics (should include all)
        recent = self.monitor.get_recent_metrics(minutes=1)
        self.assertEqual(len(recent), 3)
        
        # Get recent metrics with very short time window
        recent = self.monitor.get_recent_metrics(minutes=0.0001)  # Very recent
        # Since timing is tight, we just check it doesn't crash
        self.assertIsInstance(recent, list)
    
    def test_metrics_limit(self):
        """Test that metrics list is limited to 10000 entries"""
        # Record many operations
        for i in range(15000):  # More than the limit
            self.monitor.record_operation("op", 0.1, True, 100)
        
        # Check that metrics list is limited
        self.assertLessEqual(len(self.monitor.metrics), 10000)
        
        # Check that operation stats still reflect all operations
        stats = self.monitor.operation_stats["op"]
        self.assertEqual(stats['count'], 15000)
    
    def test_concurrent_recording(self):
        """Test concurrent operation recording"""
        def worker(worker_id):
            """Worker function for concurrent testing"""
            for i in range(100):
                self.monitor.record_operation(
                    operation=f"worker_{worker_id}_op",
                    duration=0.01,
                    success=True,
                    data_size=100
                )
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check total metrics count
        self.assertEqual(len(self.monitor.metrics), 1000)  # 10 workers * 100 operations
        
        # Check operation stats
        for i in range(10):
            stats = self.monitor.operation_stats[f"worker_{i}_op"]
            self.assertEqual(stats['count'], 100)
            self.assertEqual(stats['success_count'], 100)
    
    def test_edge_cases(self):
        """Test edge cases"""
        # Test zero duration
        self.monitor.record_operation("zero_duration", 0.0, True, 0)
        
        # Test very large duration
        self.monitor.record_operation("large_duration", 9999.99, True, 999999)
        
        # Test zero data size
        self.monitor.record_operation("zero_size", 0.1, True, 0)
        
        # Test very large data size
        self.monitor.record_operation("large_size", 0.1, True, 10**9)
        
        # Check that all were recorded
        self.assertEqual(len(self.monitor.metrics), 4)
        
        # Check summary includes all operations
        summary = self.monitor.get_performance_summary()
        self.assertEqual(len(summary), 4)
    
    def test_time_precision(self):
        """Test time precision in metrics"""
        start_time = time.time()
        
        # Record operation
        self.monitor.record_operation("timing_test", 0.001, True, 100)
        
        # Check that timestamp is recent
        metric = self.monitor.metrics[0]
        self.assertGreaterEqual(metric.timestamp, start_time)
        self.assertLessEqual(metric.timestamp, time.time())
    
    def test_different_operation_types(self):
        """Test recording different types of operations"""
        operations = ["get", "put", "delete", "cleanup", "stats"]
        
        for op in operations:
            self.monitor.record_operation(op, 0.1, True, 1000)
        
        # Check that all operations are recorded
        summary = self.monitor.get_performance_summary()
        self.assertEqual(len(summary), len(operations))
        
        # Check that each operation has correct stats
        for op in operations:
            self.assertIn(op, summary)
            op_summary = summary[op]
            self.assertEqual(op_summary['count'], 1)
            self.assertEqual(op_summary['success_rate'], 1.0)
            self.assertEqual(op_summary['avg_data_size'], 1000)


if __name__ == '__main__':
    unittest.main()