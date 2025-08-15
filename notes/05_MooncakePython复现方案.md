# Mooncake Python 复现方案

## 1. 复现目标与策略

### 1.1 复现目标

基于对 Mooncake 项目的深入分析，我们计划用 Python 复现其核心功能，主要目标包括：

1. **教育目的**：通过实现理解分布式系统设计原理
2. **功能验证**：验证 Mooncake 核心设计的正确性
3. **性能对比**：与原版进行性能对比分析
4. **扩展实验**：在新版本上实验新的优化策略

### 1.2 复现策略

考虑到复杂度和开发时间，我们提供三种复现方案：

1. **完整复现**：复现所有核心功能（推荐 6-8 个月）
2. **核心功能复现**：复现最关键的功能（推荐 2-3 个月）
3. **简化版复现**：复现基础功能用于教学（推荐 2-4 周）

## 2. 系统架构设计

### 2.1 整体架构

```python
# Mooncake Python 版整体架构
class MooncakePython:
    def __init__(self):
        self.transfer_engine = TransferEngine()
        self.store = MooncakeStore()
        self.metadata_manager = MetadataManager()
        self.topology_manager = TopologyManager()
        
    def start(self):
        """启动 Mooncake 服务"""
        self.transfer_engine.start()
        self.store.start()
        self.metadata_manager.start()
        
    def stop(self):
        """停止 Mooncake 服务"""
        self.transfer_engine.stop()
        self.store.stop()
        self.metadata_manager.stop()
```

### 2.2 核心组件关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  (LLM Serving Interface, Query Processing)                  │
├─────────────────────────────────────────────────────────────┤
│                    Mooncake Python                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Transfer      │  │    Store        │  │   Metadata      │  │
│  │    Engine       │  │   Manager       │  │   Manager       │  │
│  │                 │  │                 │  │                 │  │
│  │ • Protocol      │  │ • Object        │  │ • Distributed   │  │
│  │   Management    │  │   Storage       │  │   Metadata     │  │
│  │ • Topology      │  │ • Cache         │  │ • Consistency   │  │
│  │   Awareness     │  │   Management    │  │   Management    │  │
│  │ • Batch         │  │ • Replica       │  │ • Lease         │  │
│  │   Transfer      │  │   Management    │  │   Management    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                     │
│  (TCP/UDP Sockets, Threading, AsyncIO, Local Storage)      │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心功能复现方案

### 3.1 Transfer Engine 复现

#### 3.1.1 基础架构

```python
import asyncio
import socket
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time
import json

@dataclass
class TransferRequest:
    """传输请求数据结构"""
    request_id: str
    source_addr: str
    target_addr: str
    data: bytes
    offset: int = 0
    length: int = 0
    priority: int = 0
    timeout: float = 30.0

@dataclass
class TransferStatus:
    """传输状态数据结构"""
    request_id: str
    status: str  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    progress: float = 0.0
    error_message: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0

class Transport(ABC):
    """传输协议抽象基类"""
    
    @abstractmethod
    async def submit_transfer(self, request: TransferRequest) -> TransferStatus:
        """提交传输请求"""
        pass
    
    @abstractmethod
    async def get_status(self, request_id: str) -> TransferStatus:
        """获取传输状态"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查传输协议是否可用"""
        pass

class TcpTransport(Transport):
    """TCP 传输实现"""
    
    def __init__(self, buffer_size: int = 65536):
        self.buffer_size = buffer_size
        self.active_connections: Dict[str, socket.socket] = {}
        self.connection_lock = threading.Lock()
        
    async def submit_transfer(self, request: TransferRequest) -> TransferStatus:
        """TCP 传输实现"""
        try:
            start_time = time.time()
            
            # 建立连接
            conn = await self._get_connection(request.target_addr)
            
            # 发送数据
            header = self._create_header(request)
            conn.sendall(header + request.data)
            
            # 等待确认
            response = conn.recv(1024)
            
            end_time = time.time()
            
            return TransferStatus(
                request_id=request.request_id,
                status="COMPLETED",
                progress=1.0,
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            return TransferStatus(
                request_id=request.request_id,
                status="FAILED",
                error_message=str(e)
            )
    
    def _create_header(self, request: TransferRequest) -> bytes:
        """创建传输头"""
        header = {
            "request_id": request.request_id,
            "length": len(request.data),
            "offset": request.offset
        }
        return json.dumps(header).encode() + b'\n'

class TransferEngine:
    """传输引擎核心类"""
    
    def __init__(self):
        self.transports: Dict[str, Transport] = {}
        self.active_transfers: Dict[str, TransferStatus] = {}
        self.transfer_queue: asyncio.Queue = asyncio.Queue()
        self.topology_manager = TopologyManager()
        self.running = False
        
    def register_transport(self, name: str, transport: Transport):
        """注册传输协议"""
        self.transports[name] = transport
        
    def start(self):
        """启动传输引擎"""
        self.running = True
        asyncio.create_task(self._process_transfers())
        
    async def _process_transfers(self):
        """处理传输队列"""
        while self.running:
            try:
                request = await self.transfer_queue.get()
                
                # 选择最优传输协议
                transport = self._select_optimal_transport(request)
                
                # 执行传输
                status = await transport.submit_transfer(request)
                
                # 更新状态
                self.active_transfers[request.request_id] = status
                
            except Exception as e:
                print(f"Transfer processing error: {e}")
                
    def _select_optimal_transport(self, request: TransferRequest) -> Transport:
        """选择最优传输协议"""
        # 简化版：基于数据大小选择
        if len(request.data) < 1024:  # 小数据
            return self.transports.get("tcp", self.transports["local"])
        else:  # 大数据
            return self.transports.get("tcp", self.transports["local"])
            
    async def submit_transfer(self, request: TransferRequest) -> str:
        """提交传输请求"""
        await self.transfer_queue.put(request)
        return request.request_id
```

#### 3.1.2 拓扑感知实现

```python
import psutil
import platform
from typing import List, Tuple
import subprocess

class TopologyInfo:
    """拓扑信息数据结构"""
    
    def __init__(self):
        self.numa_nodes: List[int] = []
        self.cpu_cores: List[int] = []
        self.network_interfaces: List[str] = []
        self.memory_info: Dict[str, Any] = {}
        
    def discover(self):
        """自动发现系统拓扑"""
        self._discover_numa()
        self._discover_cpu()
        self._discover_network()
        self._discover_memory()
        
    def _discover_numa(self):
        """发现 NUMA 节点"""
        try:
            # Linux 系统
            result = subprocess.run(['lscpu'], capture_output=True, text=True)
            if 'NUMA node(s)' in result.stdout:
                numa_count = int([line for line in result.stdout.split('\n') 
                                if 'NUMA node(s)' in line][0].split(':')[-1].strip())
                self.numa_nodes = list(range(numa_count))
        except:
            # 默认单个 NUMA 节点
            self.numa_nodes = [0]
            
    def _discover_cpu(self):
        """发现 CPU 信息"""
        self.cpu_cores = list(range(psutil.cpu_count()))
        
    def _discover_network(self):
        """发现网络接口"""
        self.network_interfaces = list(psutil.net_if_addrs().keys())
        
    def _discover_memory(self):
        """发现内存信息"""
        self.memory_info = {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available
        }

class TopologyManager:
    """拓扑管理器"""
    
    def __init__(self):
        self.topology_info = TopologyInfo()
        self.path_cache: Dict[str, str] = {}
        
    def initialize(self):
        """初始化拓扑管理"""
        self.topology_info.discover()
        
    def select_optimal_path(self, source: str, destination: str) -> str:
        """选择最优传输路径"""
        cache_key = f"{source}->{destination}"
        
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]
            
        # 简化版路径选择算法
        if source == destination:
            optimal_path = "local"
        elif self._is_same_network(source, destination):
            optimal_path = "tcp"
        else:
            optimal_path = "tcp"
            
        self.path_cache[cache_key] = optimal_path
        return optimal_path
        
    def _is_same_network(self, source: str, destination: str) -> bool:
        """判断是否在同一网络"""
        # 简化实现
        return True
```

### 3.2 Mooncake Store 复现

#### 3.2.1 元数据管理

```python
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import os

@dataclass
class ReplicaInfo:
    """副本信息"""
    replica_id: str
    location: str
    status: str  # CREATING, COMPLETE, FAILED
    size: int = 0
    created_time: datetime = field(default_factory=datetime.now)
    
@dataclass
class ObjectMetadata:
    """对象元数据"""
    object_key: str
    size: int
    replicas: List[ReplicaInfo] = field(default_factory=list)
    created_time: datetime = field(default_factory=datetime.now)
    lease_expiry: datetime = field(default_factory=datetime.now)
    soft_pin_expiry: Optional[datetime] = None
    access_count: int = 0
    last_access_time: datetime = field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.lease_expiry
        
    def is_soft_pinned(self) -> bool:
        """检查是否被软 pin"""
        return self.soft_pin_expiry and datetime.now() <= self.soft_pin_expiry

class MetadataShard:
    """元数据分片"""
    
    def __init__(self, shard_id: int):
        self.shard_id = shard_id
        self.metadata: Dict[str, ObjectMetadata] = {}
        self.lock = threading.RLock()
        self.last_access = datetime.now()
        
    def get(self, key: str) -> Optional[ObjectMetadata]:
        """获取元数据"""
        with self.lock:
            self.last_access = datetime.now()
            return self.metadata.get(key)
            
    def put(self, key: str, metadata: ObjectMetadata):
        """存储元数据"""
        with self.lock:
            self.last_access = datetime.now()
            self.metadata[key] = metadata
            
    def remove(self, key: str) -> bool:
        """删除元数据"""
        with self.lock:
            if key in self.metadata:
                del self.metadata[key]
                return True
            return False
            
    def cleanup_expired(self) -> List[str]:
        """清理过期元数据"""
        with self.lock:
            expired_keys = []
            for key, metadata in self.metadata.items():
                if metadata.is_expired():
                    expired_keys.append(key)
                    
            for key in expired_keys:
                del self.metadata[key]
                
            return expired_keys

class MetadataManager:
    """元数据管理器"""
    
    def __init__(self, num_shards: int = 1024):
        self.num_shards = num_shards
        self.shards: List[MetadataShard] = [
            MetadataShard(i) for i in range(num_shards)
        ]
        self.gc_thread = None
        self.running = False
        
    def get_shard(self, key: str) -> MetadataShard:
        """获取分片"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self.shards[hash_value % self.num_shards]
        
    def get_metadata(self, key: str) -> Optional[ObjectMetadata]:
        """获取对象元数据"""
        shard = self.get_shard(key)
        metadata = shard.get(key)
        
        if metadata:
            metadata.last_access_time = datetime.now()
            metadata.access_count += 1
            
        return metadata
        
    def create_object(self, key: str, size: int, ttl_seconds: int = 3600,
                     soft_ttl_seconds: int = 0) -> ObjectMetadata:
        """创建对象元数据"""
        now = datetime.now()
        metadata = ObjectMetadata(
            object_key=key,
            size=size,
            lease_expiry=now + timedelta(seconds=ttl_seconds)
        )
        
        if soft_ttl_seconds > 0:
            metadata.soft_pin_expiry = now + timedelta(seconds=soft_ttl_seconds)
            
        shard = self.get_shard(key)
        shard.put(key, metadata)
        
        return metadata
        
    def add_replica(self, key: str, replica: ReplicaInfo):
        """添加副本信息"""
        metadata = self.get_metadata(key)
        if metadata:
            metadata.replicas.append(replica)
            
    def remove_object(self, key: str) -> bool:
        """删除对象"""
        shard = self.get_shard(key)
        return shard.remove(key)
        
    def start_gc_thread(self):
        """启动垃圾回收线程"""
        self.running = True
        self.gc_thread = threading.Thread(target=self._gc_loop)
        self.gc_thread.daemon = True
        self.gc_thread.start()
        
    def _gc_loop(self):
        """垃圾回收循环"""
        while self.running:
            try:
                for shard in self.shards:
                    expired_keys = shard.cleanup_expired()
                    if expired_keys:
                        print(f"Cleaned up {len(expired_keys)} expired objects")
                        
                time.sleep(60)  # 每分钟清理一次
                
            except Exception as e:
                print(f"GC error: {e}")
                time.sleep(10)
```

#### 3.2.2 存储后端实现

```python
import os
import shutil
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import pickle

@dataclass
class StorageConfig:
    """存储配置"""
    root_dir: str
    max_size: int  # 最大存储大小（字节）
    cleanup_threshold: float = 0.8  # 清理阈值
    backup_enabled: bool = True

class StorageBackend:
    """存储后端抽象类"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.lock = threading.RLock()
        self.ensure_directory()
        
    def ensure_directory(self):
        """确保存储目录存在"""
        os.makedirs(self.config.root_dir, exist_ok=True)
        
    def get_object_path(self, key: str) -> str:
        """获取对象存储路径"""
        # 使用两级目录结构避免单目录文件过多
        hash_value = hash(key) % 1000
        dir_path = os.path.join(self.config.root_dir, f"{hash_value:03d}")
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{hash(key)}.obj")
        
    def store_object(self, key: str, data: bytes) -> bool:
        """存储对象"""
        try:
            with self.lock:
                # 检查存储空间
                if not self.check_storage_space(len(data)):
                    return False
                    
                path = self.get_object_path(key)
                
                # 备份现有文件
                if os.path.exists(path) and self.config.backup_enabled:
                    backup_path = path + ".bak"
                    shutil.copy2(path, backup_path)
                    
                # 写入新文件
                with open(path, 'wb') as f:
                    f.write(data)
                    
                return True
                
        except Exception as e:
            print(f"Storage error: {e}")
            return False
            
    def retrieve_object(self, key: str) -> Optional[bytes]:
        """检索对象"""
        try:
            path = self.get_object_path(key)
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return f.read()
            return None
            
        except Exception as e:
            print(f"Retrieval error: {e}")
            return None
            
    def delete_object(self, key: str) -> bool:
        """删除对象"""
        try:
            path = self.get_object_path(key)
            if os.path.exists(path):
                os.remove(path)
                
                # 删除备份文件
                backup_path = path + ".bak"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                    
                return True
            return False
            
        except Exception as e:
            print(f"Delete error: {e}")
            return False
            
    def check_storage_space(self, required_size: int) -> bool:
        """检查存储空间"""
        try:
            total_size = self.get_total_size()
            available_space = self.config.max_size - total_size
            
            if available_space >= required_size:
                return True
                
            # 空间不足，尝试清理
            if total_size > self.config.max_size * self.config.cleanup_threshold:
                self.cleanup_old_objects()
                available_space = self.config.max_size - self.get_total_size()
                
            return available_space >= required_size
            
        except Exception as e:
            print(f"Space check error: {e}")
            return False
            
    def get_total_size(self) -> int:
        """获取总存储大小"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(self.config.root_dir):
                for file in files:
                    if not file.endswith('.bak'):
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
            return total_size
            
        except Exception as e:
            print(f"Size calculation error: {e}")
            return 0
            
    def cleanup_old_objects(self):
        """清理旧对象"""
        try:
            # 获取所有文件及其访问时间
            files = []
            for root, dirs, fs in os.walk(self.config.root_dir):
                for file in fs:
                    if not file.endswith('.bak'):
                        file_path = os.path.join(root, file)
                        access_time = os.path.getatime(file_path)
                        files.append((access_time, file_path))
                        
            # 按访问时间排序，删除最旧的文件
            files.sort(key=lambda x: x[0])
            
            current_size = self.get_total_size()
            target_size = self.config.max_size * 0.7  # 清理到 70%
            
            for access_time, file_path in files:
                if current_size <= target_size:
                    break
                    
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                current_size -= file_size
                
                print(f"Cleaned up old file: {file_path}")
                
        except Exception as e:
            print(f"Cleanup error: {e}")

class TieredStorageManager:
    """分层存储管理器"""
    
    def __init__(self):
        self.memory_cache: Dict[str, bytes] = {}
        self.memory_limit = 100 * 1024 * 1024  # 100MB 内存缓存
        self.disk_storage = StorageBackend(
            StorageConfig(
                root_dir="/tmp/mooncake_disk",
                max_size=10 * 1024 * 1024 * 1024  # 10GB 磁盘存储
            )
        )
        
    def store_object(self, key: str, data: bytes, use_memory: bool = True) -> bool:
        """存储对象（分层存储）"""
        # 总是存储到磁盘
        disk_success = self.disk_storage.store_object(key, data)
        
        # 根据大小决定是否缓存到内存
        if use_memory and len(data) < 1024 * 1024:  # 小于 1MB 的对象缓存到内存
            self._add_to_memory_cache(key, data)
            
        return disk_success
        
    def retrieve_object(self, key: str) -> Optional[bytes]:
        """检索对象（优先从内存）"""
        # 先检查内存缓存
        if key in self.memory_cache:
            return self.memory_cache[key]
            
        # 从磁盘读取
        data = self.disk_storage.retrieve_object(key)
        if data is not None and len(data) < 1024 * 1024:
            self._add_to_memory_cache(key, data)
            
        return data
        
    def _add_to_memory_cache(self, key: str, data: bytes):
        """添加到内存缓存"""
        # 简单的 LRU 策略
        if len(self.memory_cache) * 1024 > self.memory_limit:
            # 删除最旧的条目
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
            
        self.memory_cache[key] = data
```

### 3.3 客户端接口实现

```python
import asyncio
import threading
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import json
import socket

@dataclass
class ClientConfig:
    """客户端配置"""
    master_address: str = "localhost:8080"
    local_address: str = "localhost:0"
    timeout: float = 30.0
    retry_count: int = 3

class MooncakeClient:
    """Mooncake 客户端"""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.transfer_engine = TransferEngine()
        self.metadata_client = MetadataClient(config.master_address)
        self.local_cache: Dict[str, bytes] = {}
        self.running = False
        
    def start(self):
        """启动客户端"""
        self.running = True
        self.transfer_engine.start()
        self.metadata_client.connect()
        
    def stop(self):
        """停止客户端"""
        self.running = False
        self.transfer_engine.stop()
        self.metadata_client.disconnect()
        
    async def put(self, key: str, data: bytes, ttl_seconds: int = 3600) -> bool:
        """存储对象"""
        try:
            # 1. 向 Master 申请存储位置
            locations = await self.metadata_client.allocate_storage(
                key, len(data), ttl_seconds
            )
            
            if not locations:
                return False
                
            # 2. 并行写入多个副本
            tasks = []
            for location in locations:
                task = self._write_to_location(location, data)
                tasks.append(task)
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 3. 检查写入结果
            success_count = sum(1 for result in results if result is True)
            
            # 4. 通知 Master 写入完成
            if success_count > 0:
                await self.metadata_client.complete_put(key, success_count)
                return True
            else:
                await self.metadata_client.fail_put(key)
                return False
                
        except Exception as e:
            print(f"Put error: {e}")
            return False
            
    async def get(self, key: str) -> Optional[bytes]:
        """获取对象"""
        try:
            # 1. 检查本地缓存
            if key in self.local_cache:
                return self.local_cache[key]
                
            # 2. 向 Master 查询对象位置
            locations = await self.metadata_client.get_locations(key)
            
            if not locations:
                return None
                
            # 3. 从最优位置读取
            for location in locations:
                data = await self._read_from_location(location)
                if data is not None:
                    # 缓存到本地
                    if len(data) < 1024 * 1024:  # 小于 1MB 的对象缓存
                        self.local_cache[key] = data
                    return data
                    
            return None
            
        except Exception as e:
            print(f"Get error: {e}")
            return None
            
    async def _write_to_location(self, location: Dict[str, Any], data: bytes) -> bool:
        """写入指定位置"""
        try:
            request = TransferRequest(
                request_id=f"put_{location['replica_id']}",
                source_addr=self.config.local_address,
                target_addr=location['address'],
                data=data
            )
            
            await self.transfer_engine.submit_transfer(request)
            return True
            
        except Exception as e:
            print(f"Write to location error: {e}")
            return False
            
    async def _read_from_location(self, location: Dict[str, Any]) -> Optional[bytes]:
        """从指定位置读取"""
        try:
            # 简化实现：直接从存储后端读取
            storage = TieredStorageManager()
            return storage.retrieve_object(location['object_key'])
            
        except Exception as e:
            print(f"Read from location error: {e}")
            return None

class MetadataClient:
    """元数据客户端"""
    
    def __init__(self, master_address: str):
        self.master_address = master_address
        self.socket: Optional[socket.socket] = None
        self.lock = threading.Lock()
        
    def connect(self):
        """连接到 Master"""
        try:
            host, port = self.master_address.split(':')
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, int(port)))
            print(f"Connected to Master at {self.master_address}")
            
        except Exception as e:
            print(f"Failed to connect to Master: {e}")
            
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            
    async def allocate_storage(self, key: str, size: int, ttl_seconds: int) -> List[Dict[str, Any]]:
        """申请存储位置"""
        try:
            request = {
                'action': 'allocate',
                'key': key,
                'size': size,
                'ttl': ttl_seconds
            }
            
            response = await self._send_request(request)
            return response.get('locations', [])
            
        except Exception as e:
            print(f"Allocate storage error: {e}")
            return []
            
    async def get_locations(self, key: str) -> List[Dict[str, Any]]:
        """获取对象位置"""
        try:
            request = {
                'action': 'get_locations',
                'key': key
            }
            
            response = await self._send_request(request)
            return response.get('locations', [])
            
        except Exception as e:
            print(f"Get locations error: {e}")
            return []
            
    async def complete_put(self, key: str, success_count: int):
        """通知 Put 完成"""
        request = {
            'action': 'complete_put',
            'key': key,
            'success_count': success_count
        }
        await self._send_request(request)
        
    async def fail_put(self, key: str):
        """通知 Put 失败"""
        request = {
            'action': 'fail_put',
            'key': key
        }
        await self._send_request(request)
        
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到 Master"""
        try:
            with self.lock:
                if not self.socket:
                    self.connect()
                    
                # 发送请求
                message = json.dumps(request) + '\n'
                self.socket.send(message.encode())
                
                # 接收响应
                response = self.socket.recv(4096)
                return json.loads(response.decode())
                
        except Exception as e:
            print(f"Send request error: {e}")
            return {}
```

## 4. 简化版实现方案（2-4 周）

### 4.1 核心功能简化

```python
class SimpleMooncake:
    """简化版 Mooncake 实现"""
    
    def __init__(self):
        self.storage = {}
        self.metadata = {}
        self.access_log = []
        
    def put(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """存储对象"""
        try:
            import time
            self.storage[key] = {
                'value': value,
                'created_at': time.time(),
                'ttl': ttl,
                'access_count': 0
            }
            return True
        except Exception as e:
            print(f"Put error: {e}")
            return False
            
    def get(self, key: str) -> Optional[Any]:
        """获取对象"""
        try:
            import time
            if key in self.storage:
                data = self.storage[key]
                
                # 检查 TTL
                if time.time() - data['created_at'] > data['ttl']:
                    del self.storage[key]
                    return None
                    
                # 更新访问统计
                data['access_count'] += 1
                self.access_log.append({
                    'key': key,
                    'timestamp': time.time(),
                    'operation': 'get'
                })
                
                return data['value']
            return None
            
        except Exception as e:
            print(f"Get error: {e}")
            return None
            
    def delete(self, key: str) -> bool:
        """删除对象"""
        try:
            if key in self.storage:
                del self.storage[key]
                return True
            return False
            
        except Exception as e:
            print(f"Delete error: {e}")
            return False
            
    def cleanup_expired(self):
        """清理过期对象"""
        try:
            import time
            current_time = time.time()
            expired_keys = []
            
            for key, data in self.storage.items():
                if current_time - data['created_at'] > data['ttl']:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                del self.storage[key]
                
            return len(expired_keys)
            
        except Exception as e:
            print(f"Cleanup error: {e}")
            return 0
            
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_objects': len(self.storage),
            'total_accesses': len(self.access_log),
            'memory_usage': sum(len(str(data['value'])) for data in self.storage.values())
        }
```

### 4.2 性能监控简化

```python
import time
import threading
from typing import Dict, Any, List
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    operation: str
    duration: float
    success: bool
    data_size: int = 0

class SimpleMonitor:
    """简化版性能监控"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'success_count': 0,
            'total_size': 0
        })
        self.lock = threading.Lock()
        
    def record_operation(self, operation: str, duration: float, 
                        success: bool, data_size: int = 0):
        """记录操作指标"""
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
        """获取性能摘要"""
        summary = {}
        
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
        """获取最近的指标"""
        cutoff_time = time.time() - (minutes * 60)
        with self.lock:
            return [m for m in self.metrics if m.timestamp >= cutoff_time]
```

### 4.3 使用示例

```python
def demo_simple_mooncake():
    """演示简化版 Mooncake 使用"""
    # 创建实例
    mooncake = SimpleMooncake()
    monitor = SimpleMonitor()
    
    # 模拟数据存储
    import time
    import random
    
    print("=== Simple Mooncake Demo ===")
    
    # 存储一些测试数据
    test_data = {
        f'key_{i}': f'value_{i}' * random.randint(10, 100)
        for i in range(100)
    }
    
    print(f"Storing {len(test_data)} objects...")
    
    # 存储操作
    for key, value in test_data.items():
        start_time = time.time()
        success = mooncake.put(key, value, ttl=random.randint(300, 3600))
        duration = time.time() - start_time
        
        monitor.record_operation('put', duration, success, len(value))
        
    print(f"Stored {len(test_data)} objects")
    
    # 读取操作
    print("Retrieving objects...")
    retrieved_count = 0
    for key in test_data.keys():
        start_time = time.time()
        value = mooncake.get(key)
        duration = time.time() - start_time
        
        success = value is not None
        if success:
            retrieved_count += 1
            
        monitor.record_operation('get', duration, success)
        
    print(f"Retrieved {retrieved_count} objects")
    
    # 显示统计信息
    stats = mooncake.get_stats()
    print("\n=== Storage Statistics ===")
    print(f"Total objects: {stats['total_objects']}")
    print(f"Total accesses: {stats['total_accesses']}")
    print(f"Memory usage: {stats['memory_usage']} bytes")
    
    # 显示性能统计
    perf_summary = monitor.get_performance_summary()
    print("\n=== Performance Summary ===")
    for operation, metrics in perf_summary.items():
        print(f"{operation}:")
        print(f"  Count: {metrics['count']}")
        print(f"  Avg duration: {metrics['avg_duration']:.4f}s")
        print(f"  Success rate: {metrics['success_rate']:.2%}")
        print(f"  Avg data size: {metrics['avg_data_size']:.1f} bytes")
        
    # 清理过期对象
    cleaned_count = mooncake.cleanup_expired()
    print(f"\nCleaned up {cleaned_count} expired objects")

if __name__ == "__main__":
    demo_simple_mooncake()
```

## 5. 完整版实现方案（6-8 个月）

### 5.1 项目结构

```
mooncake-python/
├── mooncake/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── transfer_engine.py
│   │   ├── mooncake_store.py
│   │   ├── metadata_manager.py
│   │   └── topology_manager.py
│   ├── transport/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── tcp_transport.py
│   │   └── udp_transport.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── backends.py
│   │   └── tiered_storage.py
│   ├── client/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── config.py
│   ├── server/
│   │   ├── __init__.py
│   │   ├── master.py
│   │   └── worker.py
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   └── monitoring.py
│   └── utils/
│       ├── __init__.py
│       ├── serialization.py
│       └── crypto.py
├── examples/
│   ├── simple_demo.py
│   ├── performance_test.py
│   └── distributed_test.py
├── tests/
│   ├── test_transfer_engine.py
│   ├── test_mooncake_store.py
│   ├── test_client.py
│   └── test_integration.py
├── docs/
│   ├── README.md
│   ├── API.md
│   └── ARCHITECTURE.md
├── requirements.txt
├── setup.py
└── README.md
```

### 5.2 开发计划

#### 第一阶段：基础架构（4 周）
- [ ] 项目结构搭建
- [ ] 核心数据结构定义
- [ ] 基础传输协议实现
- [ ] 简单存储后端

#### 第二阶段：核心功能（6 周）
- [ ] 完整的 Transfer Engine
- [ ] 元数据管理系统
- [ ] 分层存储实现
- [ ] 客户端接口

#### 第三阶段：高级功能（4 周）
- [ ] 拓扑感知优化
- [ ] 批量传输优化
- [ ] 性能监控系统
- [ ] 故障恢复机制

#### 第四阶段：测试优化（4 周）
- [ ] 单元测试编写
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档完善

#### 第五阶段：部署发布（2 周）
- [ ] 打包发布
- [ ] 示例代码
- [ ] 用户文档
- [ ] 社区反馈

### 5.3 技术选型

**核心依赖**：
- `asyncio` - 异步编程
- `aiohttp` - HTTP 客户端/服务器
- `numpy` - 数值计算
- `psutil` - 系统信息
- `pydantic` - 数据验证

**开发工具**：
- `pytest` - 单元测试
- `black` - 代码格式化
- `mypy` - 类型检查
- `sphinx` - 文档生成

## 6. 核心功能复现（2-3 个月）

### 6.1 关键功能列表

1. **Transfer Engine 核心**
   - [ ] 多协议支持（TCP/UDP）
   - [ ] 批量传输
   - [ ] 基础拓扑感知
   - [ ] 异步处理

2. **Mooncake Store 核心**
   - [ ] 元数据分片管理
   - [ ] 分层存储
   - [ ] 租约机制
   - [ ] 副本管理

3. **客户端接口**
   - [ ] 基本操作（put/get/delete）
   - [ ] 批量操作
   - [ ] 缓存管理
   - [ ] 错误处理

### 6.2 实现优先级

1. **最高优先级**：
   - 基本的数据存储和检索
   - 元数据管理
   - 网络传输

2. **中等优先级**：
   - 分层存储
   - 批量操作
   - 性能监控

3. **低优先级**：
   - 高级拓扑优化
   - 故障恢复
   - 管理接口

## 7. 教育价值

### 7.1 学习要点

通过实现 Mooncake Python 版本，可以学习到：

1. **分布式系统设计**
   - 分布式架构模式
   - 一致性和可用性
   - 故障处理机制

2. **高性能编程**
   - 异步编程模型
   - 内存管理优化
   - 网络编程

3. **系统架构**
   - 分层架构设计
   - 模块化设计
   - 接口设计

4. **性能优化**
   - 缓存策略
   - 负载均衡
   - 资源管理

### 7.2 实验项目

1. **性能对比实验**
   - 与 Redis 性能对比
   - 不同缓存策略对比
   - 网络协议性能对比

2. **扩展性实验**
   - 水平扩展测试
   - 负载均衡测试
   - 故障恢复测试

3. **算法优化实验**
   - 缓存替换算法
   - 负载均衡算法
   - 数据分布算法

## 8. 总结

Mooncake Python 版本的复现具有以下价值：

1. **教育价值**：深入理解分布式系统设计原理
2. **实践价值**：获得实际系统开发经验
3. **研究价值**：为系统优化提供实验平台
4. **职业价值**：提升技术能力和项目经验

建议根据实际需求和时间投入选择合适的复现方案，从简化版开始，逐步完善功能。这个过程不仅能深入理解 Mooncake 的设计思想，还能提升分布式系统开发能力。