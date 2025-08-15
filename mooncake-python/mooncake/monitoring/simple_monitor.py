"""
SimpleMonitor Implementation
Performance monitoring for the Mooncake Python implementation
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""
    timestamp: float
    operation: str
    duration: float
    success: bool
    data_size: int = 0


class SimpleMonitor:
    """简化版性能监控"""
    
    def __init__(self):
        """初始化监控器"""
        self.metrics: List[PerformanceMetrics] = []
        self.operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'success_count': 0,
            'total_size': 0
        })
        self.lock = threading.Lock()
        
    def record_operation(self, operation: str, duration: float, 
                        success: bool, data_size: int = 0):
        """记录操作指标
        
        Args:
            operation: 操作名称
            duration: 操作持续时间（秒）
            success: 操作是否成功
            data_size: 数据大小（字节）
        """
        metric = PerformanceMetrics(
            timestamp=time.time(),
            operation=operation,
            duration=duration,
            success=success,
            data_size=data_size
        )
        
        with self.lock:
            self.metrics.append(metric)
            
            # 更新统计信息
            stats = self.operation_stats[operation]
            stats['count'] += 1
            stats['total_time'] += duration
            if success:
                stats['success_count'] += 1
            stats['total_size'] += data_size
            
            # 保持最近 10000 条记录
            if len(self.metrics) > 10000:
                self.metrics = self.metrics[-10000:]
                
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要
        
        Returns:
            Dict[str, Any]: 性能摘要信息
        """
        summary = {}
        
        with self.lock:
            for operation, stats in self.operation_stats.items():
                if stats['count'] > 0:
                    summary[operation] = {
                        'count': stats['count'],
                        'avg_duration': stats['total_time'] / stats['count'],
                        'success_rate': stats['success_count'] / stats['count'],
                        'avg_data_size': stats['total_size'] / stats['count'] if stats['count'] > 0 else 0
                    }
                    
        return summary
        
    def get_recent_metrics(self, minutes: int = 5) -> List[PerformanceMetrics]:
        """获取最近的指标
        
        Args:
            minutes: 获取最近多少分钟的指标
            
        Returns:
            List[PerformanceMetrics]: 最近的指标列表
        """
        cutoff_time = time.time() - (minutes * 60)
        with self.lock:
            return [m for m in self.metrics if m.timestamp >= cutoff_time]
    
    def reset_metrics(self):
        """重置所有指标"""
        with self.lock:
            self.metrics.clear()
            self.operation_stats.clear()
    
    def get_operation_count(self, operation: str) -> int:
        """获取特定操作的总次数
        
        Args:
            operation: 操作名称
            
        Returns:
            int: 操作总次数
        """
        with self.lock:
            stats = self.operation_stats.get(operation, {})
            return stats.get('count', 0)
    
    def get_operation_success_rate(self, operation: str) -> float:
        """获取特定操作的成功率
        
        Args:
            operation: 操作名称
            
        Returns:
            float: 成功率（0.0-1.0）
        """
        with self.lock:
            stats = self.operation_stats.get(operation, {})
            if stats.get('count', 0) == 0:
                return 0.0
            return stats['success_count'] / stats['count']
    
    def get_average_duration(self, operation: str) -> float:
        """获取特定操作的平均持续时间
        
        Args:
            operation: 操作名称
            
        Returns:
            float: 平均持续时间（秒）
        """
        with self.lock:
            stats = self.operation_stats.get(operation, {})
            if stats.get('count', 0) == 0:
                return 0.0
            return stats['total_time'] / stats['count']
    
    def get_total_data_size(self, operation: str) -> int:
        """获取特定操作的总数据大小
        
        Args:
            operation: 操作名称
            
        Returns:
            int: 总数据大小（字节）
        """
        with self.lock:
            stats = self.operation_stats.get(operation, {})
            return stats.get('total_size', 0)
    
    def get_metrics_count(self) -> int:
        """获取当前存储的指标总数
        
        Returns:
            int: 指标总数
        """
        with self.lock:
            return len(self.metrics)
    
    def get_supported_operations(self) -> List[str]:
        """获取所有已记录的操作类型
        
        Returns:
            List[str]: 操作类型列表
        """
        with self.lock:
            return list(self.operation_stats.keys())