"""
Fault Tolerance Benchmark - Test khả năng chống chịu lỗi của Cassandra
Kịch bản: Tắt 1 node trong quá trình chạy benchmark
"""

import asyncio
import time
import random
import uuid
import subprocess
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement, ConsistencyLevel
import statistics
import matplotlib.pyplot as plt
from datetime import datetime

# Configuration
CONTACT_POINTS = ['127.0.0.1']
PORT = 9042
KEYSPACE = 'realtime_chat_app'

# Test parameters
NUM_OPERATIONS = 10000
NUM_THREADS = 50
NODE_TO_KILL = 'cassandra-2'  # Node sẽ bị tắt
KILL_AT_OPERATION = 5000       # Tắt node sau operation thứ 5000

def connect_to_cassandra():
    """Kết nối đến Cassandra"""
    cluster = Cluster(CONTACT_POINTS, port=PORT)
    session = cluster.connect(KEYSPACE)
    print(f"✅ Kết nối thành công đến {KEYSPACE}")
    return session, cluster

def get_sample_data(session):
    """Lấy mẫu IDs để test"""
    users = session.execute("SELECT user_id FROM users_by_id LIMIT 100")
    user_ids = [row.user_id for row in users]
    
    convos = session.execute("SELECT conversation_id FROM conversations_by_user LIMIT 500")
    conversation_ids = list(set([row.conversation_id for row in convos]))[:100]
    
    return user_ids, conversation_ids

def kill_node(node_name):
    """Tắt 1 Cassandra node"""
    try:
        subprocess.run(['docker', 'stop', node_name], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def start_node(node_name):
    """Khởi động lại node"""
    try:
        subprocess.run(['docker', 'start', node_name], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ============================================================================
# BENCHMARK với Node Failure
# ============================================================================
async def worker_write_fault_tolerant(session, conversation_ids, user_ids):
    """Worker: Write message với fault tolerance"""
    conversation_id = random.choice(conversation_ids)
    sender_id = random.choice(user_ids)
    
    query = """
    INSERT INTO messages_by_conversation 
    (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    # Sử dụng QUORUM để vẫn hoạt động khi 1 node down
    statement = SimpleStatement(query, consistency_level=ConsistencyLevel.QUORUM)
    
    start = time.perf_counter()
    
    try:
        future = session.execute_async(
            statement,
            (conversation_id, uuid.uuid1(), sender_id, "fault_test", 
             "Fault tolerance test", [])
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, future.result)
        
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, True, 'success'
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        error_type = type(e).__name__
        return latency_ms, False, error_type

async def benchmark_fault_tolerance(session, conversation_ids, user_ids, num_ops):
    """Benchmark với node failure simulation"""
    print(f"\n{'='*60}")
    print(f"🛡️ FAULT TOLERANCE BENCHMARK")
    print(f"{'='*60}")
    print(f"Sẽ tắt node '{NODE_TO_KILL}' sau {KILL_AT_OPERATION} operations")
    print(f"Consistency Level: QUORUM (cần 2/3 nodes)")
    print()
    
    latencies = []
    failures = []
    timestamps = []
    error_types = []
    node_killed = False
    operation_count = 0
    
    start_time = time.time()
    
    tasks = []
    for _ in range(num_ops):
        tasks.append(worker_write_fault_tolerant(session, conversation_ids, user_ids))
    
    batch_size = NUM_THREADS
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*batch)
        
        for latency, success, error_type in results:
            operation_count += 1
            elapsed = time.time() - start_time
            
            latencies.append(latency)
            timestamps.append(elapsed)
            
            if not success:
                failures.append({
                    'operation': operation_count,
                    'timestamp': elapsed,
                    'error': error_type
                })
                error_types.append(error_type)
            
            # Tắt node khi đạt số operation chỉ định
            if operation_count == KILL_AT_OPERATION and not node_killed:
                print(f"\n🔴 KILLING NODE: {NODE_TO_KILL} (operation {operation_count})")
                if kill_node(NODE_TO_KILL):
                    print(f"   ✓ Node {NODE_TO_KILL} stopped")
                    node_killed = True
                else:
                    print(f"   ✗ Failed to stop node")
        
        if (i + batch_size) % 1000 == 0:
            print(f"   ✓ Progress: {min(i+batch_size, num_ops):,}/{num_ops:,} "
                  f"(Failures: {len(failures)})")
    
    total_time = time.time() - start_time
    
    # Restart node
    if node_killed:
        print(f"\n🟢 RESTARTING NODE: {NODE_TO_KILL}")
        if start_node(NODE_TO_KILL):
            print(f"   ✓ Node {NODE_TO_KILL} restarted")
        else:
            print(f"   ✗ Failed to restart node")
    
    # Calculate metrics
    throughput = num_ops / total_time
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)
    
    # Metrics before/after failure
    latencies_before = [latencies[i] for i in range(min(KILL_AT_OPERATION, len(latencies)))]
    latencies_after = [latencies[i] for i in range(KILL_AT_OPERATION, len(latencies))]
    
    p95_before = statistics.quantiles(latencies_before, n=20)[18] if len(latencies_before) > 20 else 0
    p95_after = statistics.quantiles(latencies_after, n=20)[18] if len(latencies_after) > 20 else 0
    
    print(f"\n📊 KẾT QUẢ TỔNG THỂ:")
    print(f"   - Tổng operations: {num_ops:,}")
    print(f"   - Throughput: {throughput:.2f} ops/s")
    print(f"   - Latency p50: {p50:.2f}ms")
    print(f"   - Latency p95: {p95:.2f}ms")
    print(f"   - Latency p99: {p99:.2f}ms")
    print(f"   - Total failures: {len(failures)} ({len(failures)/num_ops*100:.2f}%)")
    
    print(f"\n📊 SO SÁNH TRƯỚC/SAU KHI TẮT NODE:")
    print(f"   - p95 TRƯỚC: {p95_before:.2f}ms")
    print(f"   - p95 SAU: {p95_after:.2f}ms")
    print(f"   - Tăng: {((p95_after/p95_before - 1) * 100) if p95_before > 0 else 0:.1f}%")
    
    if error_types:
        print(f"\n❌ LOẠI LỖI:")
        from collections import Counter
        error_counts = Counter(error_types)
        for error, count in error_counts.most_common():
            print(f"   - {error}: {count} lần")
    
    return {
        'latencies': latencies,
        'timestamps': timestamps,
        'failures': failures,
        'kill_point': KILL_AT_OPERATION,
        'p95_before': p95_before,
        'p95_after': p95_after,
        'total_time': total_time
    }

# ============================================================================
# VISUALIZATION
# ============================================================================
def plot_fault_tolerance(result):
    """Vẽ biểu đồ fault tolerance"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Fault Tolerance: Impact of Node Failure', fontsize=16, fontweight='bold')
    
    latencies = result['latencies']
    timestamps = result['timestamps']
    failures = result['failures']
    kill_point = result['kill_point']
    
    # 1. Latency over time
    ax1 = axes[0, 0]
    ax1.scatter(timestamps, latencies, alpha=0.5, s=1, color='blue')
    
    # Mark failure point
    if kill_point < len(timestamps):
        kill_time = timestamps[kill_point-1] if kill_point > 0 else 0
        ax1.axvline(x=kill_time, color='red', linestyle='--', linewidth=2, 
                   label=f'Node killed at {kill_time:.1f}s')
    
    # Mark failures
    if failures:
        failure_times = [timestamps[f['operation']-1] for f in failures if f['operation']-1 < len(timestamps)]
        failure_latencies = [latencies[f['operation']-1] for f in failures if f['operation']-1 < len(latencies)]
        ax1.scatter(failure_times, failure_latencies, color='red', s=50, 
                   marker='x', label='Failed operations', zorder=5)
    
    ax1.set_xlabel('Time (seconds)', fontweight='bold')
    ax1.set_ylabel('Latency (ms)', fontweight='bold')
    ax1.set_title('Latency Over Time (with Node Failure)')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # 2. Moving average latency
    ax2 = axes[0, 1]
    window_size = 100
    moving_avg = []
    for i in range(len(latencies)):
        start_idx = max(0, i - window_size + 1)
        moving_avg.append(statistics.mean(latencies[start_idx:i+1]))
    
    ax2.plot(timestamps, moving_avg, color='blue', linewidth=2, label='Moving average (100 ops)')
    
    if kill_point < len(timestamps):
        kill_time = timestamps[kill_point-1] if kill_point > 0 else 0
        ax2.axvline(x=kill_time, color='red', linestyle='--', linewidth=2, 
                   label=f'Node killed')
    
    ax2.set_xlabel('Time (seconds)', fontweight='bold')
    ax2.set_ylabel('Avg Latency (ms)', fontweight='bold')
    ax2.set_title('Moving Average Latency')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # 3. Latency distribution before/after
    ax3 = axes[1, 0]
    latencies_before = latencies[:kill_point]
    latencies_after = latencies[kill_point:]
    
    ax3.hist(latencies_before, bins=50, alpha=0.7, label='Before failure', 
            color='green', edgecolor='black')
    ax3.hist(latencies_after, bins=50, alpha=0.7, label='After failure', 
            color='orange', edgecolor='black')
    
    ax3.set_xlabel('Latency (ms)', fontweight='bold')
    ax3.set_ylabel('Frequency', fontweight='bold')
    ax3.set_title('Latency Distribution: Before vs After Node Failure')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # 4. Failure rate over time
    ax4 = axes[1, 1]
    
    # Calculate failure rate per time window
    time_windows = []
    failure_rates = []
    window_duration = 1.0  # 1 second windows
    
    max_time = max(timestamps)
    current_time = 0
    
    while current_time < max_time:
        next_time = current_time + window_duration
        
        # Count operations in window
        ops_in_window = sum(1 for t in timestamps if current_time <= t < next_time)
        
        # Count failures in window
        failures_in_window = sum(1 for f in failures 
                                if f['operation']-1 < len(timestamps) and 
                                current_time <= timestamps[f['operation']-1] < next_time)
        
        if ops_in_window > 0:
            failure_rate = (failures_in_window / ops_in_window) * 100
        else:
            failure_rate = 0
        
        time_windows.append(current_time + window_duration/2)
        failure_rates.append(failure_rate)
        
        current_time = next_time
    
    ax4.plot(time_windows, failure_rates, color='red', linewidth=2)
    
    if kill_point < len(timestamps):
        kill_time = timestamps[kill_point-1] if kill_point > 0 else 0
        ax4.axvline(x=kill_time, color='darkred', linestyle='--', linewidth=2, 
                   label='Node killed')
    
    ax4.set_xlabel('Time (seconds)', fontweight='bold')
    ax4.set_ylabel('Failure Rate (%)', fontweight='bold')
    ax4.set_title('Failure Rate Over Time')
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('fault_tolerance_benchmark.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Biểu đồ đã lưu: fault_tolerance_benchmark.png")
    plt.show()

# ============================================================================
# MAIN
# ============================================================================
async def main():
    print("\n" + "="*60)
    print("🛡️ FAULT TOLERANCE BENCHMARK")
    print("="*60)
    print("⚠️  Lưu ý: Script này sẽ TẮT và KHỞI ĐỘNG LẠI node Cassandra")
    print("="*60)
    
    session, cluster = connect_to_cassandra()
    
    try:
        user_ids, conversation_ids = get_sample_data(session)
        
        result = await benchmark_fault_tolerance(
            session, conversation_ids, user_ids, NUM_OPERATIONS
        )
        
        plot_fault_tolerance(result)
        
        print(f"\n✅ Test hoàn thành!")
        print(f"📊 Kết luận: Cassandra tiếp tục hoạt động với {result['failures'].__len__()} lỗi "
              f"khi 1/3 nodes down (QUORUM)")
        
    finally:
        cluster.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
