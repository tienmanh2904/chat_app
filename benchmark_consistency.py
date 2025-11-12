"""
Benchmark Consistency Levels - Test hiệu suất với các mức độ consistency khác nhau
So sánh: ONE vs QUORUM vs ALL
"""

import asyncio
import time
import random
import uuid
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement, ConsistencyLevel
import statistics
import matplotlib.pyplot as plt
import numpy as np

# Configuration
CONTACT_POINTS = ['127.0.0.1']
PORT = 9042
KEYSPACE = 'realtime_chat_app'

# Test parameters
NUM_OPERATIONS = 5000
NUM_THREADS = 50

# Mapping consistency level values to names
CL_NAMES = {
    ConsistencyLevel.ONE: 'ONE',
    ConsistencyLevel.QUORUM: 'QUORUM',
    ConsistencyLevel.ALL: 'ALL'
}

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
    
    print(f"📋 Lấy mẫu: {len(user_ids)} users, {len(conversation_ids)} conversations")
    return user_ids, conversation_ids

# ============================================================================
# WRITE BENCHMARK với các Consistency Level khác nhau
# ============================================================================
async def worker_write_cl(session, conversation_ids, user_ids, consistency_level):
    """Worker: Write với consistency level chỉ định"""
    conversation_id = random.choice(conversation_ids)
    sender_id = random.choice(user_ids)
    
    query = """
    INSERT INTO messages_by_conversation 
    (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    statement = SimpleStatement(query, consistency_level=consistency_level)
    
    start = time.perf_counter()
    
    try:
        future = session.execute_async(
            statement,
            (conversation_id, uuid.uuid1(), sender_id, "benchmark_user", 
             "Consistency test message", [])
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, future.result)
        
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, True
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, False

async def benchmark_consistency_level(session, conversation_ids, user_ids, 
                                     consistency_level, num_ops):
    """Benchmark với 1 consistency level"""
    cl_name = CL_NAMES.get(consistency_level, str(consistency_level))
    print(f"\n{'='*60}")
    print(f"🔍 Testing Consistency Level: {cl_name}")
    print(f"{'='*60}")
    
    latencies = []
    failures = 0
    start_time = time.time()
    
    tasks = []
    for _ in range(num_ops):
        tasks.append(worker_write_cl(session, conversation_ids, user_ids, consistency_level))
    
    batch_size = NUM_THREADS
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*batch)
        
        for latency, success in results:
            latencies.append(latency)
            if not success:
                failures += 1
        
        if (i + batch_size) % 1000 == 0:
            print(f"   ✓ Progress: {min(i+batch_size, num_ops):,}/{num_ops:,}")
    
    total_time = time.time() - start_time
    
    # Calculate metrics
    throughput = num_ops / total_time
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)
    avg = statistics.mean(latencies)
    
    print(f"\n📊 Kết quả {cl_name}:")
    print(f"   - Throughput: {throughput:.2f} ops/s")
    print(f"   - Latency avg: {avg:.2f}ms")
    print(f"   - Latency p50: {p50:.2f}ms")
    print(f"   - Latency p95: {p95:.2f}ms")
    print(f"   - Latency p99: {p99:.2f}ms")
    print(f"   - Failures: {failures}/{num_ops} ({failures/num_ops*100:.2f}%)")
    
    return {
        'cl_name': cl_name,
        'throughput': throughput,
        'avg': avg,
        'p50': p50,
        'p95': p95,
        'p99': p99,
        'failures': failures,
        'latencies': latencies
    }

# ============================================================================
# VISUALIZATION
# ============================================================================
def plot_consistency_comparison(results):
    """Vẽ biểu đồ so sánh các consistency levels"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Consistency Level Performance Comparison', fontsize=16, fontweight='bold')
    
    cl_names = [r['cl_name'] for r in results]
    colors = ['#2ecc71', '#3498db', '#e74c3c']
    
    # 1. Throughput comparison
    ax1 = axes[0, 0]
    throughputs = [r['throughput'] for r in results]
    bars1 = ax1.bar(cl_names, throughputs, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Throughput (ops/s)', fontweight='bold')
    ax1.set_title('Write Throughput by Consistency Level')
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}',
                ha='center', va='bottom', fontweight='bold')
    
    # 2. Latency comparison (p50, p95, p99)
    ax2 = axes[0, 1]
    x = np.arange(len(cl_names))
    width = 0.25
    
    p50s = [r['p50'] for r in results]
    p95s = [r['p95'] for r in results]
    p99s = [r['p99'] for r in results]
    
    ax2.bar(x - width, p50s, width, label='p50', color='#2ecc71', alpha=0.7, edgecolor='black')
    ax2.bar(x, p95s, width, label='p95', color='#f39c12', alpha=0.7, edgecolor='black')
    ax2.bar(x + width, p99s, width, label='p99', color='#e74c3c', alpha=0.7, edgecolor='black')
    
    ax2.set_ylabel('Latency (ms)', fontweight='bold')
    ax2.set_title('Latency Percentiles by Consistency Level')
    ax2.set_xticks(x)
    ax2.set_xticklabels(cl_names)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # 3. Latency distribution (histogram)
    ax3 = axes[1, 0]
    for i, result in enumerate(results):
        ax3.hist(result['latencies'], bins=50, alpha=0.5, label=result['cl_name'], 
                color=colors[i], edgecolor='black')
    
    ax3.set_xlabel('Latency (ms)', fontweight='bold')
    ax3.set_ylabel('Frequency', fontweight='bold')
    ax3.set_title('Latency Distribution')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # 4. Cumulative Distribution Function (CDF)
    ax4 = axes[1, 1]
    for i, result in enumerate(results):
        sorted_latencies = np.sort(result['latencies'])
        cumulative = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies) * 100
        ax4.plot(sorted_latencies, cumulative, label=result['cl_name'], 
                color=colors[i], linewidth=2)
    
    ax4.set_xlabel('Latency (ms)', fontweight='bold')
    ax4.set_ylabel('Percentile (%)', fontweight='bold')
    ax4.set_title('Cumulative Latency Distribution (CDF)')
    ax4.legend()
    ax4.grid(alpha=0.3)
    ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='p50')
    ax4.axhline(y=95, color='orange', linestyle='--', alpha=0.5, label='p95')
    ax4.axhline(y=99, color='red', linestyle='--', alpha=0.5, label='p99')
    
    plt.tight_layout()
    plt.savefig('consistency_level_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Biểu đồ đã lưu: consistency_level_comparison.png")
    plt.show()

def print_summary_table(results):
    """In bảng tổng kết"""
    print(f"\n{'='*80}")
    print("📊 BẢNG TỔNG KẾT SO SÁNH CONSISTENCY LEVELS")
    print(f"{'='*80}")
    print(f"{'Metric':<20} {'ONE':<20} {'QUORUM':<20} {'ALL':<20}")
    print(f"{'-'*80}")
    
    # Throughput
    throughputs = [r['throughput'] for r in results]
    print(f"{'Throughput (ops/s)':<20} {throughputs[0]:<20.2f} {throughputs[1]:<20.2f} {throughputs[2]:<20.2f}")
    
    # Latency p50
    p50s = [r['p50'] for r in results]
    print(f"{'Latency p50 (ms)':<20} {p50s[0]:<20.2f} {p50s[1]:<20.2f} {p50s[2]:<20.2f}")
    
    # Latency p95
    p95s = [r['p95'] for r in results]
    print(f"{'Latency p95 (ms)':<20} {p95s[0]:<20.2f} {p95s[1]:<20.2f} {p95s[2]:<20.2f}")
    
    # Latency p99
    p99s = [r['p99'] for r in results]
    print(f"{'Latency p99 (ms)':<20} {p99s[0]:<20.2f} {p99s[1]:<20.2f} {p99s[2]:<20.2f}")
    
    # Failures
    failures = [r['failures'] for r in results]
    print(f"{'Failures':<20} {failures[0]:<20} {failures[1]:<20} {failures[2]:<20}")
    
    print(f"{'='*80}")
    
    # Analysis
    print(f"\n🔍 PHÂN TÍCH:")
    print(f"   - Fastest: {results[0]['cl_name']} ({throughputs[0]:.0f} ops/s)")
    print(f"   - Slowest: {results[2]['cl_name']} ({throughputs[2]:.0f} ops/s)")
    print(f"   - Speed difference: {throughputs[0]/throughputs[2]:.2f}x")
    print(f"   - Trade-off: {results[0]['cl_name']} nhanh nhưng ít đảm bảo, {results[2]['cl_name']} chậm nhưng đảm bảo cao")

# ============================================================================
# MAIN
# ============================================================================
async def main():
    print("\n" + "="*60)
    print("🚀 CONSISTENCY LEVEL BENCHMARK")
    print("="*60)
    
    session, cluster = connect_to_cassandra()
    
    try:
        user_ids, conversation_ids = get_sample_data(session)
        
        # Test 3 consistency levels
        results = []
        
        # 1. ONE (fastest, least consistent)
        result_one = await benchmark_consistency_level(
            session, conversation_ids, user_ids, 
            ConsistencyLevel.ONE, NUM_OPERATIONS
        )
        results.append(result_one)
        
        await asyncio.sleep(2)  # Cool down
        
        # 2. QUORUM (balanced)
        result_quorum = await benchmark_consistency_level(
            session, conversation_ids, user_ids, 
            ConsistencyLevel.QUORUM, NUM_OPERATIONS
        )
        results.append(result_quorum)
        
        await asyncio.sleep(2)  # Cool down
        
        # 3. ALL (slowest, most consistent)
        result_all = await benchmark_consistency_level(
            session, conversation_ids, user_ids, 
            ConsistencyLevel.ALL, NUM_OPERATIONS
        )
        results.append(result_all)
        
        # Summary
        print_summary_table(results)
        
        # Visualization
        plot_consistency_comparison(results)
        
    finally:
        cluster.shutdown()

if __name__ == "__main__":
    asyncio.run(main())