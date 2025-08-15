# Mooncake Python Implementation

A simplified Python implementation of the Mooncake distributed KVCache system, following Test-Driven Development (TDD) principles.

## Overview

This project implements a simplified version of Mooncake, a high-performance distributed KVCache system designed for large-scale LLM inference scenarios. The implementation focuses on core functionality while demonstrating proper software engineering practices.

## Features

### Core Functionality
- **KVCache Management**: Basic key-value cache storage and retrieval
- **TTL Support**: Time-to-live for automatic cache expiration
- **Thread Safety**: Concurrent access support with proper locking
- **Memory Management**: Efficient memory usage with automatic cleanup

### Performance Monitoring
- **Operation Tracking**: Record duration, success rate, and data size for all operations
- **Performance Metrics**: Comprehensive statistics and performance analysis
- **Real-time Monitoring**: Live performance monitoring with configurable retention
- **Throughput Analysis**: Operations per second and latency measurements

### Error Handling
- **Graceful Degradation**: Robust error handling for edge cases
- **Exception Safety**: Proper exception handling and resource cleanup
- **Boundary Conditions**: Handling of None values, empty strings, and zero TTL

## Architecture

```
mooncake-python/
├── mooncake/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── simple_mooncake.py          # Core KVCache implementation
│   ├── monitoring/
│   │   ├── __init__.py
│   │   └── simple_monitor.py           # Performance monitoring
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_simple_mooncake.py         # Unit tests for core functionality
│   ├── test_simple_monitor.py          # Unit tests for monitoring
│   └── test_integration.py             # Integration tests
├── examples/
│   ├── __init__.py
│   └── simple_demo.py                  # Demo program
└── requirements.txt
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mooncake-python
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Operations

```python
from mooncake import SimpleMooncake, SimpleMonitor

# Create instances
mooncake = SimpleMooncake()
monitor = SimpleMonitor()

# Store data
mooncake.put("user_1", {"name": "Alice", "age": 25}, ttl=3600)

# Retrieve data
user_data = mooncake.get("user_1")
print(user_data)  # {"name": "Alice", "age": 25}

# Delete data
mooncake.delete("user_1")
```

### Performance Monitoring

```python
# Record operation performance
start_time = time.time()
success = mooncake.put("key", "value", ttl=3600)
duration = time.time() - start_time
monitor.record_operation('put', duration, success, len("value"))

# Get performance summary
summary = monitor.get_performance_summary()
print(summary)
# Output: {'put': {'count': 1, 'avg_duration': 0.000001, 'success_rate': 1.0, 'avg_data_size': 5.0}}
```

### TTL and Cleanup

```python
# Store with TTL
mooncake.put("temp_data", "expires_soon", ttl=10)  # 10 seconds

# Check if data exists (will be None after TTL expires)
data = mooncake.get("temp_data")

# Manual cleanup of expired objects
cleaned_count = mooncake.cleanup_expired()
print(f"Cleaned {cleaned_count} expired objects")
```

## Running Tests

This project follows Test-Driven Development (TDD) principles:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_simple_mooncake.py -v
python -m pytest tests/test_simple_monitor.py -v
python -m pytest tests/test_integration.py -v

# Run with coverage
pip install pytest-cov
python -m pytest --cov=mooncake tests/
```

## Demo Program

Run the comprehensive demo to see all features in action:

```bash
PYTHONPATH=. python examples/simple_demo.py
```

The demo includes:
- Basic operations (put/get/delete)
- TTL and automatic cleanup
- Concurrent operations
- Performance monitoring
- Error handling

## API Reference

### SimpleMooncake

#### `__init__()`
Initialize a new SimpleMooncake instance.

#### `put(key: str, value: Any, ttl: int = 3600) -> bool`
Store a key-value pair with optional TTL.

- `key`: Unique identifier for the value
- `value`: Data to store (any Python object)
- `ttl`: Time-to-live in seconds (default: 3600)
- Returns: True if successful, False otherwise

#### `get(key: str) -> Optional[Any]`
Retrieve a value by key.

- `key`: Identifier of the value to retrieve
- Returns: The stored value or None if not found/expired

#### `delete(key: str) -> bool`
Delete a key-value pair.

- `key`: Identifier of the value to delete
- Returns: True if successful, False otherwise

#### `cleanup_expired() -> int`
Remove all expired objects from cache.

- Returns: Number of expired objects removed

#### `get_stats() -> Dict[str, Any]`
Get cache statistics.

- Returns: Dictionary with total_objects, total_accesses, and memory_usage

### SimpleMonitor

#### `__init__()`
Initialize a new SimpleMonitor instance.

#### `record_operation(operation: str, duration: float, success: bool, data_size: int = 0)`
Record an operation's performance metrics.

- `operation`: Name of the operation (e.g., 'put', 'get', 'delete')
- `duration`: Operation duration in seconds
- `success`: Whether the operation succeeded
- `data_size`: Size of data processed in bytes

#### `get_performance_summary() -> Dict[str, Any]`
Get performance summary for all operations.

- Returns: Dictionary with operation statistics

#### `get_recent_metrics(minutes: int = 5) -> List[PerformanceMetrics]`
Get metrics from the last N minutes.

- `minutes`: Time window in minutes (default: 5)
- Returns: List of recent performance metrics

## Performance Characteristics

Based on test results, the implementation demonstrates:

- **High Throughput**: 100,000+ operations per second for basic operations
- **Low Latency**: Sub-millisecond response times for cache operations
- **Thread Safety**: Proper concurrent access handling
- **Memory Efficiency**: Automatic cleanup and memory management

## Educational Value

This implementation serves as an educational tool for understanding:

1. **Distributed Systems Concepts**: Caching, TTL, concurrency
2. **Performance Monitoring**: Metrics collection and analysis
3. **Test-Driven Development**: Writing tests before implementation
4. **Software Engineering Best Practices**: Code organization, documentation, testing

## Limitations

This is a simplified implementation with some limitations:

- Single-node only (no distributed features)
- In-memory storage only (no persistence)
- Basic eviction policies (no LRU/LFU advanced algorithms)
- No network communication (local only)

## Future Enhancements

Potential improvements for a more complete implementation:

1. **Distributed Features**: Multi-node support and replication
2. **Persistence**: Disk-based storage and backup
3. **Advanced Eviction**: LRU, LFU, and adaptive policies
4. **Network API**: REST/gRPC interface for remote access
5. **Clustering**: Automatic discovery and load balancing

## Contributing

This project follows TDD principles. When contributing:

1. Write tests for new functionality
2. Ensure all tests pass
3. Update documentation as needed
4. Follow the existing code style

## License

This project is for educational purposes. See LICENSE file for details.

## Acknowledgments

This implementation is based on the Mooncake system described in the FAST 2025 paper by Moonshot AI. It serves as an educational tool for understanding distributed KVCache systems.