"""
SimpleMooncake Implementation
A simplified Python implementation of the Mooncake distributed KVCache system
"""

import time
import threading
from typing import Any, Dict, List, Optional


class SimpleMooncake:
    """简化版 Mooncake 实现"""
    
    def __init__(self):
        """初始化 SimpleMooncake"""
        self.storage: Dict[str, Dict[str, Any]] = {}
        self.access_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()  # 线程安全锁
        
    def put(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """存储对象
        
        Args:
            key: 对象键
            value: 对象值
            ttl: 生存时间（秒），默认3600秒
            
        Returns:
            bool: 存储是否成功
        """
        try:
            current_time = time.time()
            
            with self._lock:
                self.storage[key] = {
                    'value': value,
                    'created_at': current_time,
                    'ttl': ttl,
                    'access_count': 0
                }
                
            return True
            
        except Exception as e:
            print(f"Put error: {e}")
            return False
        
    def get(self, key: str) -> Optional[Any]:
        """获取对象
        
        Args:
            key: 对象键
            
        Returns:
            Optional[Any]: 对象值，如果不存在或已过期则返回None
        """
        try:
            current_time = time.time()
            
            with self._lock:
                if key in self.storage:
                    data = self.storage[key]
                    
                    # 检查 TTL
                    if current_time - data['created_at'] > data['ttl']:
                        # 对象已过期，删除并返回None
                        del self.storage[key]
                        return None
                    
                    # 更新访问统计
                    data['access_count'] += 1
                    self.access_log.append({
                        'key': key,
                        'timestamp': current_time,
                        'operation': 'get'
                    })
                    
                    return data['value']
                    
            return None
            
        except Exception as e:
            print(f"Get error: {e}")
            return None
        
    def delete(self, key: str) -> bool:
        """删除对象
        
        Args:
            key: 对象键
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._lock:
                if key in self.storage:
                    del self.storage[key]
                    return True
                return False
                
        except Exception as e:
            print(f"Delete error: {e}")
            return False
        
    def cleanup_expired(self) -> int:
        """清理过期对象
        
        Returns:
            int: 清理的过期对象数量
        """
        try:
            current_time = time.time()
            expired_keys = []
            
            with self._lock:
                # 收集过期键
                for key, data in self.storage.items():
                    if current_time - data['created_at'] > data['ttl']:
                        expired_keys.append(key)
                
                # 删除过期对象
                for key in expired_keys:
                    del self.storage[key]
                    
            return len(expired_keys)
            
        except Exception as e:
            print(f"Cleanup error: {e}")
            return 0
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 包含统计信息的字典
        """
        try:
            with self._lock:
                total_objects = len(self.storage)
                total_accesses = len(self.access_log)
                
                # 计算内存使用量（估算）
                memory_usage = sum(
                    len(str(data['value'])) + len(str(data['created_at'])) + 
                    len(str(data['ttl'])) + len(str(data['access_count']))
                    for data in self.storage.values()
                )
                
                return {
                    'total_objects': total_objects,
                    'total_accesses': total_accesses,
                    'memory_usage': memory_usage
                }
                
        except Exception as e:
            print(f"Get stats error: {e}")
            return {
                'total_objects': 0,
                'total_accesses': 0,
                'memory_usage': 0
            }