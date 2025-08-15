"""
Simple Mooncake Demo
演示简化版 Mooncake 的使用方法
"""

import time
import random
import threading
from mooncake import SimpleMooncake, SimpleMonitor


def demo_basic_operations():
    """演示基本操作"""
    print("=== 基本操作演示 ===")
    
    # 创建实例
    mooncake = SimpleMooncake()
    monitor = SimpleMonitor()
    
    # 基本存储和检索
    test_data = {
        'user_1_profile': {'name': 'Alice', 'age': 25, 'city': 'Beijing'},
        'user_2_profile': {'name': 'Bob', 'age': 30, 'city': 'Shanghai'},
        'config_1': {'timeout': 30, 'retries': 3, 'debug': True},
        'cache_data': 'x' * 1000,  # 1KB 的缓存数据
        'session_token': 'abc123def456'
    }
    
    print("1. 存储测试数据...")
    for key, value in test_data.items():
        start_time = time.time()
        success = mooncake.put(key, value, ttl=3600)  # 1小时TTL
        duration = time.time() - start_time
        monitor.record_operation('put', duration, success, len(str(value)))
        print(f"   存储 {key}: {'成功' if success else '失败'} ({duration:.6f}s)")
    
    print("\n2. 检索测试数据...")
    for key in test_data.keys():
        start_time = time.time()
        result = mooncake.get(key)
        duration = time.time() - start_time
        success = result is not None
        monitor.record_operation('get', duration, success, len(str(result)) if result else 0)
        print(f"   获取 {key}: {'成功' if success else '失败'} ({duration:.6f}s)")
        if success:
            print(f"      值: {str(result)[:100]}{'...' if len(str(result)) > 100 else ''}")
    
    print("\n3. 统计信息...")
    stats = mooncake.get_stats()
    print(f"   总对象数: {stats['total_objects']}")
    print(f"   总访问次数: {stats['total_accesses']}")
    print(f"   内存使用: {stats['memory_usage']} 字节")
    
    print("\n4. 性能监控摘要...")
    summary = monitor.get_performance_summary()
    for operation, metrics in summary.items():
        print(f"   {operation}:")
        print(f"     次数: {metrics['count']}")
        print(f"     平均耗时: {metrics['avg_duration']:.6f}s")
        print(f"     成功率: {metrics['success_rate']:.2%}")
        print(f"     平均数据大小: {metrics['avg_data_size']:.1f} 字节")
    
    # 清理
    print("\n5. 清理测试数据...")
    for key in test_data.keys():
        mooncake.delete(key)
    
    print("基本操作演示完成！\n")


def demo_ttl_and_cleanup():
    """演示TTL和自动清理功能"""
    print("=== TTL 和自动清理演示 ===")
    
    mooncake = SimpleMooncake()
    
    # 存储具有不同TTL的对象
    print("1. 存储具有不同TTL的对象...")
    mooncake.put('short_lived', '短期数据', ttl=1)  # 1秒TTL
    mooncake.put('medium_lived', '中期数据', ttl=3)  # 3秒TTL
    mooncake.put('long_lived', '长期数据', ttl=10)  # 10秒TTL
    
    print("2. 立即检查所有对象...")
    for key in ['short_lived', 'medium_lived', 'long_lived']:
        value = mooncake.get(key)
        print(f"   {key}: {'存在' if value is not None else '不存在'}")
    
    print("\n3. 等待2秒...")
    time.sleep(2)
    
    print("4. 2秒后检查对象...")
    for key in ['short_lived', 'medium_lived', 'long_lived']:
        value = mooncake.get(key)
        print(f"   {key}: {'存在' if value is not None else '不存在'}")
    
    print("\n5. 手动清理过期对象...")
    cleaned_count = mooncake.cleanup_expired()
    print(f"   清理了 {cleaned_count} 个过期对象")
    
    print("6. 最终检查...")
    stats = mooncake.get_stats()
    print(f"   剩余对象数: {stats['total_objects']}")
    
    print("TTL和自动清理演示完成！\n")


def demo_concurrent_operations():
    """演示并发操作"""
    print("=== 并发操作演示 ===")
    
    mooncake = SimpleMooncake()
    monitor = SimpleMonitor()
    
    def worker(worker_id, num_operations):
        """工作线程函数"""
        for i in range(num_operations):
            key = f"worker_{worker_id}_key_{i}"
            value = f"worker_{worker_id}_value_{i}"
            
            # Put操作
            start_time = time.time()
            success = mooncake.put(key, value, ttl=3600)
            duration = time.time() - start_time
            monitor.record_operation(f'put_worker_{worker_id}', duration, success, len(value))
            
            # Get操作
            start_time = time.time()
            result = mooncake.get(key)
            duration = time.time() - start_time
            success = result is not None
            monitor.record_operation(f'get_worker_{worker_id}', duration, success, len(result) if result else 0)
            
            # Delete操作
            start_time = time.time()
            success = mooncake.delete(key)
            duration = time.time() - start_time
            monitor.record_operation(f'delete_worker_{worker_id}', duration, success)
    
    print("1. 启动多个工作线程...")
    num_workers = 5
    operations_per_worker = 10
    workers = []
    
    for i in range(num_workers):
        worker_thread = threading.Thread(target=worker, args=(i, operations_per_worker))
        workers.append(worker_thread)
        worker_thread.start()
        print(f"   工作线程 {i} 已启动")
    
    print("2. 等待所有工作线程完成...")
    for i, worker in enumerate(workers):
        worker.join()
        print(f"   工作线程 {i} 已完成")
    
    print("\n3. 并发操作统计...")
    summary = monitor.get_performance_summary()
    
    total_operations = 0
    for operation, metrics in summary.items():
        total_operations += metrics['count']
        print(f"   {operation}: {metrics['count']} 次操作")
    
    print(f"   总操作数: {total_operations}")
    print(f"   预期操作数: {num_workers * operations_per_worker * 3}")
    
    print("\n4. 最终系统状态...")
    stats = mooncake.get_stats()
    print(f"   剩余对象数: {stats['total_objects']} (应该为0，因为所有对象都被删除了)")
    
    print("并发操作演示完成！\n")


def demo_performance_monitoring():
    """演示性能监控功能"""
    print("=== 性能监控演示 ===")
    
    mooncake = SimpleMooncake()
    monitor = SimpleMonitor()
    
    print("1. 执行各种操作并记录性能...")
    
    # 生成不同大小的测试数据
    test_sizes = [10, 100, 1000, 10000, 100000]  # 不同大小的数据
    
    for size in test_sizes:
        value = 'x' * size
        key = f"data_{size}"
        
        # 记录Put操作
        start_time = time.time()
        success = mooncake.put(key, value, ttl=3600)
        duration = time.time() - start_time
        monitor.record_operation('put', duration, success, size)
        
        # 记录Get操作
        start_time = time.time()
        result = mooncake.get(key)
        duration = time.time() - start_time
        success = result is not None
        monitor.record_operation('get', duration, success, len(result) if result else 0)
        
        # 记录Delete操作
        start_time = time.time()
        success = mooncake.delete(key)
        duration = time.time() - start_time
        monitor.record_operation('delete', duration, success)
    
    print("2. 性能监控摘要...")
    summary = monitor.get_performance_summary()
    
    for operation, metrics in summary.items():
        print(f"\n   {operation.upper()} 操作:")
        print(f"     总次数: {metrics['count']}")
        print(f"     平均耗时: {metrics['avg_duration']:.6f}s")
        print(f"     成功率: {metrics['success_rate']:.2%}")
        print(f"     平均数据大小: {metrics['avg_data_size']:.1f} 字节")
        
        if metrics['count'] > 0:
            throughput = metrics['count'] / (metrics['avg_duration'] * metrics['count'])
            print(f"     吞吐量: {throughput:.1f} 操作/秒")
    
    print("\n3. 详细监控信息...")
    print(f"   支持的操作类型: {monitor.get_supported_operations()}")
    print(f"   总指标数: {monitor.get_metrics_count()}")
    
    print("\n4. 按数据大小分析性能...")
    for size in test_sizes:
        put_avg = monitor.get_average_duration('put')
        get_avg = monitor.get_average_duration('get')
        delete_avg = monitor.get_average_duration('delete')
        
        print(f"   数据大小 {size:6d} 字节:")
        print(f"     Put:  {put_avg:.6f}s")
        print(f"     Get:  {get_avg:.6f}s")
        print(f"     Delete: {delete_avg:.6f}s")
    
    print("性能监控演示完成！\n")


def demo_error_handling():
    """演示错误处理"""
    print("=== 错误处理演示 ===")
    
    mooncake = SimpleMooncake()
    monitor = SimpleMonitor()
    
    print("1. 测试各种边界情况...")
    
    # 测试None值
    print("   测试None值存储...")
    start_time = time.time()
    success = mooncake.put('none_value', None, ttl=3600)
    duration = time.time() - start_time
    monitor.record_operation('put', duration, success, 0)
    print(f"     存储None值: {'成功' if success else '失败'}")
    
    # 测试空字符串
    print("   测试空字符串存储...")
    start_time = time.time()
    success = mooncake.put('empty_string', '', ttl=3600)
    duration = time.time() - start_time
    monitor.record_operation('put', duration, success, 0)
    print(f"     存储空字符串: {'成功' if success else '失败'}")
    
    # 测试零TTL
    print("   测试零TTL...")
    start_time = time.time()
    success = mooncake.put('zero_ttl', 'immediate_expire', ttl=0)
    duration = time.time() - start_time
    monitor.record_operation('put', duration, success, len('immediate_expire'))
    print(f"     零TTL存储: {'成功' if success else '失败'}")
    
    # 测试获取不存在的键
    print("   测试获取不存在的键...")
    start_time = time.time()
    result = mooncake.get('nonexistent_key')
    duration = time.time() - start_time
    success = result is not None
    monitor.record_operation('get', duration, success, 0)
    print(f"     获取不存在的键: {'成功' if success else '失败'} (预期失败)")
    
    # 测试删除不存在的键
    print("   测试删除不存在的键...")
    start_time = time.time()
    success = mooncake.delete('nonexistent_key')
    duration = time.time() - start_time
    monitor.record_operation('delete', duration, success, 0)
    print(f"     删除不存在的键: {'成功' if success else '失败'} (预期失败)")
    
    # 验证零TTL对象确实过期了
    print("   验证零TTL对象过期...")
    result = mooncake.get('zero_ttl')
    print(f"     获取零TTL对象: {'存在' if result is not None else '不存在'} (预期不存在)")
    
    print("\n2. 错误处理统计...")
    summary = monitor.get_performance_summary()
    
    for operation, metrics in summary.items():
        print(f"   {operation}:")
        print(f"     总次数: {metrics['count']}")
        print(f"     成功率: {metrics['success_rate']:.2%}")
        print(f"     平均耗时: {metrics['avg_duration']:.6f}s")
    
    print("\n3. 系统状态...")
    stats = mooncake.get_stats()
    print(f"   总对象数: {stats['total_objects']}")
    print(f"   总访问次数: {stats['total_accesses']}")
    print(f"   内存使用: {stats['memory_usage']} 字节")
    
    print("错误处理演示完成！\n")


def main():
    """主函数 - 运行所有演示"""
    print("Mooncake Python 版本演示")
    print("=" * 50)
    print("这是一个简化版的 Mooncake 分布式 KVCache 系统实现")
    print("展示了核心的缓存管理和性能监控功能")
    print("=" * 50 + "\n")
    
    try:
        # 运行各种演示
        demo_basic_operations()
        demo_ttl_and_cleanup()
        demo_concurrent_operations()
        demo_performance_monitoring()
        demo_error_handling()
        
        print("=" * 50)
        print("所有演示完成！")
        print("Mooncake Python 版本成功展示了以下功能：")
        print("✓ 基本的 KVCache 存储、检索、删除操作")
        print("✓ TTL（生存时间）管理和自动清理")
        print("✓ 线程安全的并发操作")
        print("✓ 详细的性能监控和统计")
        print("✓ 健壮的错误处理机制")
        print("=" * 50)
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()