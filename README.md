# Mooncake 分布式KVCache系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Language](https://img.shields.io/badge/language-C++-orange.svg)](https://isocpp.org/)
[![Architecture](https://img.shields.io/badge/architecture-distributed-green.svg)](https://en.wikipedia.org/wiki/Distributed_computing)

> **Mooncake** 是一个高性能的分布式 KVCache 系统，专为大规模 LLM 推理场景设计。由 Moonshot AI 开发，在 FAST 2025 会议上发表。

## 项目概述

Mooncake 是 Kimi 智能助手背后的核心技术，通过创新的分离式架构和智能缓存管理，实现了显著的性能提升：

### 核心特性

- **分离式架构**：独创的 Prefill 和 Decode 阶段分离设计
- **智能缓存**：基于租约的 KVCache 管理机制
- **高性能**：在真实 workload 下处理 75% 更多请求
- **可扩展**：支持动态资源调整和水平扩展

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│              (LLM Serving Interface)                        │
├─────────────────────────────────────────────────────────────┤
│                    Mooncake Core                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Transfer      │  │    Mooncake     │  │   Topology      │  │
│  │    Engine       │  │     Store       │  │   Manager       │  │
│  │                 │  │                 │  │                 │  │
│  │ " Multi-Protocol│  │ " Metadata      │  │ " Hardware      │  │
│  │ " Topology      │  │ " Tiered        │  │ " Discovery     │  │
│  │ " Zero-Copy     │  │ " Lease         │  │ " Path          │  │
│  │ " Batch         │  │ " Replica       │  │ " Load          │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                     │
│        (RDMA, TCP, CXL, NVMe-oF, Memory Management)         │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. Transfer Engine 传输引擎

**核心功能**：
- 多协议支持：统一支持 TCP、RDMA、CXL、NVMe-oF
- 拓扑感知：基于硬件拓扑智能选择最优传输路径
- 零拷贝传输：通过 RDMA 实现真正的零拷贝数据传输
- 批量优化：智能批量传输减少网络开销

**核心接口**：
```cpp
class TransferEngine {
private:
    std::shared_ptr<TransferMetadata> metadata_;
    std::shared_ptr<MultiTransport> multi_transports_;
    std::shared_ptr<Topology> local_topology_;
    std::vector<MemoryRegion> local_memory_regions_;
    
public:
    // 提交传输请求
    Status submitTransfer(BatchID batch_id, const std::vector<TransferRequest>& entries);
    // 注册本地内存
    int registerLocalMemory(void* addr, size_t length, const std::string& location);
    // 分配批量ID
    BatchID allocateBatchID(size_t batch_size);
};
```

#### 2. Mooncake Store 存储系统

**核心功能**：
- 元数据分片：1024 个分片支持高并发访问
- 分层存储：内存、SSD、远程存储三级存储架构
- 租约管理：基于租约的缓存生命周期管理
- 副本管理：智能的副本放置和数据冗余

**核心接口**：
```cpp
class MasterService {
private:
    static constexpr size_t kNumShards = 1024;
    
    struct MetadataShard {
        mutable Mutex mutex;
        std::unordered_map<std::string, ObjectMetadata> metadata GUARDED_BY(mutex);
    };
    
    std::array<MetadataShard, kNumShards> metadata_shards_;
    
public:
    // 授予租约
    void GrantLease(const uint64_t ttl, const uint64_t soft_ttl);
    // 获取分片索引
    size_t getShardIndex(const std::string& key) const;
    // 分配副本
    Replica::Descriptor allocateReplica(SegmentID segment_id, const std::vector<uint64_t>& lengths);
};
```

#### 3. 拓扑管理器

**核心功能**：
- 自动发现：自动发现系统硬件拓扑信息
- 路径优化：基于 NUMA 亲和性选择最优数据路径
- 负载均衡：在多个可用路径间实现智能负载均衡

## 技术创新

### 1. 架构创新

#### KVCache 为中心的分离式架构
- **创新点**：将 KVCache 作为系统的一等公民进行专门设计
- **优势**：支持 Prefill 和 Decode 阶段的完全分离和独立扩展
- **效果**：在真实 workload 下提升 75% 的请求处理能力

#### 分离式 Prefill-Decode 架构
- **创新点**：首创 XpYd 弹性架构，Prefill 和 Decode 阶段完全解耦
- **优势**：支持动态资源调整，提高资源利用率
- **效果**：特定场景下实现高达 525% 的吞吐量提升

```cpp
// 弹性架构实现
class ElasticArchitecture {
private:
    struct ResourceConfig {
        int prefill_nodes;
        int decode_nodes;
        double prefill_load;
        double decode_load;
    };
    
public:
    // 自动伸缩
    void autoScale() {
        double prefill_ratio = current_config_.prefill_load / current_config_.prefill_nodes;
        double decode_ratio = current_config_.decode_load / current_config_.decode_nodes;
        
        if (prefill_ratio > decode_ratio * 1.5) {
            addPrefillNode();
        } else if (decode_ratio > prefill_ratio * 1.5) {
            addDecodeNode();
        }
    }
};
```

### 2. 传输创新

#### 统一多协议传输抽象
- **创新点**：提供统一的传输接口，屏蔽底层协议差异
- **优势**：简化开发，自动选择最优传输协议
- **效果**：支持协议间的智能切换和故障转移

#### 拓扑感知路径选择
- **创新点**：基于硬件拓扑的智能路径选择算法
- **优势**：考虑 NUMA 亲和性，选择最优数据传输路径
- **效果**：显著降低数据传输延迟

```cpp
// 拓扑感知路径选择
class TopologyAwareSelector {
public:
    std::string selectOptimalPath(const std::string& src_location, 
                                 const std::string& dst_location) {
        // 1. 分析源和目标的硬件位置
        auto src_numa = getNumaNode(src_location);
        auto dst_numa = getNumaNode(dst_location);
        
        // 2. 同 NUMA 节点优先
        if (src_numa == dst_numa) {
            return "local_memory";
        }
        
        // 3. 选择最优 RDMA 设备
        auto best_device = selectOptimalDevice(src_numa, dst_numa);
        return "rdma:" + best_device;
    }
};
```

#### 零拷贝数据传输
- **创新点**：利用 RDMA 和 GPUDirect 技术实现真正的零拷贝
- **优势**：消除内存拷贝开销，显著降低传输延迟
- **效果**：充分利用硬件带宽能力

### 3. 存储创新

#### 分层存储架构
- **创新点**：内存、SSD、远程存储三级存储架构
- **优势**：在性能和成本间找到最优平衡
- **效果**：支持数据的透明迁移和智能调度

#### 租约管理机制
- **创新点**：基于租约的缓存生命周期管理
- **优势**：硬租约保证基本功能，软租约优化性能
- **效果**：支持 VIP 机制和预测性淘汰

```cpp
// 租约管理机制
class LeaseManager {
private:
    struct LeaseInfo {
        std::chrono::steady_clock::time_point hard_expiry;
        std::optional<std::chrono::steady_clock::time_point> soft_expiry;
        bool is_pinned;
    };
    
public:
    void grantLease(const std::string& key, uint64_t ttl_ms, 
                   uint64_t soft_ttl_ms = 0, bool pin = false) {
        auto now = std::chrono::steady_clock::now();
        LeaseInfo lease;
        lease.hard_expiry = now + std::chrono::milliseconds(ttl_ms);
        
        if (soft_ttl_ms > 0) {
            lease.soft_expiry = now + std::chrono::milliseconds(soft_ttl_ms);
        }
        
        lease.is_pinned = pin;
        active_leases_[key] = lease;
    }
};
```

#### 智能副本管理
- **创新点**：基于访问模式的动态副本策略
- **优势**：智能的副本放置和数据冗余
- **效果**：在性能和成本间找到最优平衡

## 性能优化

### 1. 内存管理优化

#### 内存池技术
- **优势**：减少内存分配开销，提高内存利用率
- **实现**：预分配内存池，支持不同大小的内存块
- **效果**：显著降低内存分配和释放的开销

#### NUMA 感知分配
- **优势**：考虑 NUMA 拓扑优化内存访问
- **实现**：优先在本地 NUMA 节点分配内存
- **效果**：减少跨 NUMA 节点的内存访问开销

### 2. 网络传输优化

#### 批量传输优化
- **优势**：减少网络开销，提高传输效率
- **实现**：智能聚合小数据量的传输请求
- **效果**：显著提高网络吞吐量

#### 多路径传输
- **优势**：提高传输可靠性和性能
- **实现**：在多个可用路径间实现负载均衡
- **效果**：支持路径故障时的自动切换

### 3. 系统级优化

#### 预测性早期拒绝
- **优势**：在系统过载前进行预防性控制
- **实现**：基于负载预测的早期拒绝机制
- **效果**：避免系统性能的急剧下降

```cpp
// 预测性早期拒绝
class PredictiveAdmission {
public:
    AdmissionResult shouldAdmit(const RequestInfo& request) {
        // 1. 更新负载预测
        updateLoadPrediction();
        
        // 2. 检查紧急状态
        if (predictor_.current_load > emergency_threshold_) {
            return AdmissionResult::REJECT_EMERGENCY;
        }
        
        // 3. 预测性拒绝
        if (predictor_.predicted_load > critical_threshold_) {
            if (request.priority < priority_threshold_) {
                return AdmissionResult::REJECT_PREDICTIVE;
            }
        }
        
        return AdmissionResult::ADMIT;
    }
};
```

#### 批量聚合传输
- **优势**：减少网络开销，提高传输效率
- **实现**：基于大小、时间、数量的批量触发策略
- **效果**：显著提高小数据量传输的效率

## 开发指南

### 环境配置
- **编译器**：支持 C++17 及以上
- **依赖库**：RDMA 库、Boost、Protocol Buffers
- **操作系统**：Linux（推荐 Ubuntu 20.04+）

### 构建系统
- **构建工具**：CMake 3.10+
- **单元测试**：Google Test
- **性能测试**：自定义性能测试框架

### 开发规范
- **代码风格**：遵循 Google C++ 风格指南
- **代码审查**：所有代码需要经过审查才能合并
- **测试覆盖**：核心功能需要达到 80% 以上的测试覆盖率

## 文档结构

| 文档 | 描述 |
|------|------|
| [01_Mooncake项目概述与背景分析.md](./notes/01_Mooncake项目概述与背景分析.md) | 项目背景和概述分析 |
| [02_Mooncake核心实现深度解析.md](./notes/02_Mooncake核心实现深度解析.md) | 核心实现深度解析 |
| [03_Mooncake核心创新点与技术特色分析.md](./notes/03_Mooncake核心创新点与技术特色分析.md) | 核心创新点和技术特色分析 |
| [04_Mooncake技术Lead面试题与答案.md](./notes/04_Mooncake技术Lead面试题与答案.md) | 技术Lead面试题和答案 |
| [05_MooncakePython复现方案.md](./notes/05_MooncakePython复现方案.md) | Python复现方案 |
| [06_技术总结.md](./notes/06_技术总结.md) | 技术总结和展望 |

## 项目特色

### 技术领先
- **学术发表**：在顶级会议 FAST 2025 发表
- **工业验证**：在 Kimi 智能助手大规模应用
- **性能卓越**：多项性能指标领先行业

### 开源友好
- **代码质量**：高质量的 C++ 代码实现
- **文档完善**：详细的技术文档和使用指南
- **社区活跃**：活跃的开源社区支持

### 教育价值
- **系统设计**：展示了分布式系统的最佳实践
- **性能优化**：提供了丰富的性能优化技术
- **工程实践**：体现了大型软件工程的实践经验

## Python 复现方案

我们提供了完整的 Python 复现方案，包括：

### 1. 完整版复现（6-8 个月）
- **目标**：复现所有核心功能
- **范围**：包括 Transfer Engine、Mooncake Store、拓扑管理等
- **价值**：深入理解分布式系统设计原理

### 2. 核心功能复现（2-3 个月）
- **目标**：复现最关键的功能
- **范围**：重点实现存储、传输、元数据管理
- **价值**：验证 Mooncake 核心设计的正确性

### 3. 简化版复现（2-4 周）
- **目标**：复现基础功能用于教学
- **范围**：基本的缓存管理和网络传输
- **价值**：提供学习和实验的平台

详细的复现方案请参考：[05_MooncakePython复现方案.md](./notes/05_MooncakePython复现方案.md)

## 性能指标

### 吞吐量提升
- **真实 workload**：75% 的请求处理能力提升
- **特定场景**：高达 525% 的吞吐量提升
- **资源利用率**：显著提高资源利用效率

### 延迟优化
- **P50 延迟**：降低 40% 以上
- **P99 延迟**：降低 60% 以上
- **尾延迟**：显著改善尾延迟性能

### 可扩展性
- **水平扩展**：支持线性水平扩展
- **动态调整**：支持动态资源调整
- **负载均衡**：智能的负载均衡算法

## 快速开始

### 环境要求
- Linux 系统
- C++17 编译器
- RDMA 硬件支持（可选）
- 足够的内存和存储空间

### 编译安装
```bash
git clone https://github.com/kvcache-ai/Mooncake.git
cd Mooncake
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### 运行测试
```bash
# 运行单元测试
./bin/unit_tests

# 运行性能测试
./bin/performance_tests

# 启动示例服务
./bin/mooncake_server --config config/example.yaml
```

## 许可证

本项目采用 MIT 许可证，详情请参见 [LICENSE](LICENSE) 文件。

## 致谢

- **Moonshot AI**：开发并开源 Mooncake 项目
- **FAST 2025**：发表 Mooncake 技术论文
- **社区贡献者**：为项目发展做出贡献的所有人

## 相关链接

- [Mooncake GitHub Repository](https://github.com/kvcache-ai/Mooncake)
- [FAST 2025 Conference](https://www.usenix.org/conference/fast25)
- [Moonshot AI](https://www.moonshot.cn/)
- [Kimi 智能助手](https://kimi.moonshot.cn/)

---

<div align="center">

**Mooncake 分布式KVCache系统**

*为大规模 LLM 推理场景设计的高性能分布式缓存系统*

[返回顶部](#mooncake-分布式kvcache系统)

</div>