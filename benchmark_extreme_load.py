"""
Extreme Load Benchmark - Test với 1 triệu tin nhắn được ghi đồng thời
Mô phỏng spike traffic: Ví dụ Tết, event lớn
"""

import asyncio
import time
import random
import uuid
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra.query import SimpleStatement, ConsistencyLevel
import statistics
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Configuration
CONTACT_POINTS = ['127.0.0.1']
PORT = 9042
KEYSPACE = 'realtime_chat_app'

# Extreme load parameters
TARGET_MESSAGES = 1_000_000  # 1 triệu tin nhắn
NUM_THREADS = 200            # Tăng concurrency
BATCH_SIZE = 500             # Batch size lớn hơn

def connect_to_cassandra():
    """Kết nối với connection pool tối ưu"""
    
    # Tối ưu execution profile
    profile = ExecutionProfile(
        load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
        request_timeout=30
    )
    
    cluster = Cluster(
        CONTACT_POINTS, 
        port=PORT,
        execution_profiles={EXEC_PROFILE_DEFAULT: profile},
        protocol_version=4
    )
    session = cluster.connect(KEYSPACE)
    
    print(f"✅ Kết nối thành công đến {KEYSPACE}")
    return session, cluster

def get_sample_data(session):
    """Lấy mẫu IDs để test"""
    users = session.execute("SELECT user_id FROM users_by_id LIMIT 1000")
    user_ids = [row.user_id for row in users]
    
    convos = session.execute("SELECT conversation_id FROM conversations_by_user LIMIT 2000")
    conversation_ids = list(set([row.conversation_id for row in convos]))[:1000]
    
    print(f"📋 Lấy mẫu: {len(user_ids)} users, {len(conversation_ids)} conversations")
    return user_ids, conversation_ids

# ============================================================================
# EXTREME LOAD WORKER
# ============================================================================
async def worker_extreme_write(session, conversation_ids, user_ids, prepared_stmt):
    """Worker optimized cho extreme load"""
    conversation_id = random.choice(conversation_ids)
    sender_id = random.choice(user_ids)
    
    start = time.perf_counter()
    
    try:
        future = session.execute_async(
            prepared_stmt,
            (conversation_id, uuid.uuid1(), sender_id, "spike_user", 
             "Spike traffic message", [])
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, future.result)
        
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, True
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, False

async def benchmark_extreme_load(session, conversation_ids, user_ids, target_messages):
    """Benchmark với extreme load"""
    print(f"\n{'='*60}")
    print(f"🔥 EXTREME LOAD BENCHMARK")
    print(f"{'='*60}")
    print(f"Target: {target_messages:,} messages")
    print(f"Concurrency: {NUM_THREADS} threads")
    print(f"Batch size: {BATCH_SIZE}")
    print()
    
    # Prepare statement (tối ưu performance)
    query = """
    INSERT INTO messages_by_conversation 
    (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    prepared_stmt = session.prepare(query)
    prepared_stmt.consistency_level = ConsistencyLevel.ONE  # ONE cho throughput cao nhất
    
    latencies = []
    failures = 0
    milestone_times = []
    milestone_labels = []
    
    start_time = time.time()
    last_report_time = start_time
    last_report_count = 0
    
    # Tạo tasks
    tasks = []
    for i in range(target_messages):
        tasks.append(worker_extreme_write(session, conversation_ids, user_ids, prepared_stmt))
    
    total_completed = 0
    
    # Chạy với batches lớn
    for i in range(0, len(tasks), BATCH_SIZE):
        batch = tasks[i:i+BATCH_SIZE]
        results = await asyncio.gather(*batch)
        
        for latency, success in results:
            total_completed += 1
            latencies.append(latency)
            if not success:
                failures += 1
        
        # Real-time metrics
        current_time = time.time()
        if current_time - last_report_time >= 5.0:  # Report mỗi 5 giây
            elapsed = current_time - start_time
            messages_in_period = total_completed - last_report_count
            current_throughput = messages_in_period / (current_time - last_report_time)
            
            print(f"   ⚡ [{elapsed:.0f}s] Completed: {total_completed:,}/{target_messages:,} "
                  f"({total_completed/target_messages*100:.1f}%) - "
                  f"Current: {current_throughput:.0f} ops/s")
            
            last_report_time = current_time
            last_report_count = total_completed
        
        # Milestones
        progress = total_completed / target_messages
        if progress >= 0.25 and len(milestone_labels) == 0:
            milestone_times.append(time.time() - start_time)
            milestone_labels.append("25%")
            print(f"   ✓ Milestone: 25% @ {milestone_times[-1]:.1f}s")
        elif progress >= 0.50 and len(milestone_labels) == 1:
            milestone_times.append(time.time() - start_time)
            milestone_labels.append("50%")
            print(f"   ✓ Milestone: 50% @ {milestone_times[-1]:.1f}s")
        elif progress >= 0.75 and len(milestone_labels) == 2:
            milestone_times.append(time.time() - start_time)
            milestone_labels.append("75%")
            print(f"   ✓ Milestone: 75% @ {milestone_times[-1]:.1f}s")
    
    total_time = time.time() - start_time
    milestone_times.append(total_time)
    milestone_labels.append("100%")
    
    # Calculate metrics
    throughput = target_messages / total_time
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]
    p99 = statistics.quantiles(latencies, n=100)[98]
    avg = statistics.mean(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)
    
    print(f"\n{'='*60}")
    print(f"🎉 HOÀN THÀNH!")
    print(f"{'='*60}")
    print(f"📊 TỔNG KẾT:")
    print(f"   - Tổng messages: {target_messages:,}")
    print(f"   - Tổng thời gian: {total_time:.2f}s ({total_time/60:.2f} phút)")
    print(f"   - Throughput: {throughput:.2f} ops/s")
    print(f"   - Failures: {failures} ({failures/target_messages*100:.3f}%)")
    print()
    print(f"📈 LATENCY:")
    print(f"   - Min: {min_lat:.2f}ms")
    print(f"   - Avg: {avg:.2f}ms")
    print(f"   - p50: {p50:.2f}ms")
    print(f"   - p95: {p95:.2f}ms")
    print(f"   - p99: {p99:.2f}ms")
    print(f"   - Max: {max_lat:.2f}ms")
    print()
    print(f"⏱️  MILESTONES:")
    for label, t in zip(milestone_labels, milestone_times):
        print(f"   - {label}: {t:.1f}s")
    
    return {
        'target': target_messages,
        'total_time': total_time,
        'throughput': throughput,
        'latencies': latencies,
        'failures': failures,
        'avg': avg,
        'p50': p50,
        'p95': p95,
        'p99': p99,
        'min': min_lat,
        'max': max_lat,
        'milestone_times': milestone_times,
        'milestone_labels': milestone_labels
    }

# ============================================================================
# VISUALIZATION
# ============================================================================
def plot_extreme_load(result):
    """Vẽ biểu đồ extreme load test"""
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    fig.suptitle(f'Extreme Load Test: {result["target"]:,} Messages', 
                 fontsize=18, fontweight='bold')
    
    latencies = result['latencies']
    
    # 1. Summary metrics (text box) - Top left
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')
    
    summary_text = f"""
    PERFORMANCE SUMMARY
    {'='*30}
    
    Total Messages: {result['target']:,}
    Duration: {result['total_time']:.1f}s ({result['total_time']/60:.1f}min)
    Throughput: {result['throughput']:.0f} ops/s
    Failures: {result['failures']} ({result['failures']/result['target']*100:.3f}%)
    
    LATENCY METRICS
    {'='*30}
    Min: {result['min']:.2f}ms
    Avg: {result['avg']:.2f}ms
    p50: {result['p50']:.2f}ms
    p95: {result['p95']:.2f}ms
    p99: {result['p99']:.2f}ms
    Max: {result['max']:.2f}ms
    """
    
    ax1.text(0.1, 0.9, summary_text, transform=ax1.transAxes, 
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 2. Milestone progress - Top middle & right
    ax2 = fig.add_subplot(gs[0, 1:])
    milestones = result['milestone_labels']
    times = result['milestone_times']
    
    ax2.barh(milestones, times, color=['#2ecc71', '#3498db', '#f39c12', '#e74c3c'])
    ax2.set_xlabel('Time (seconds)', fontweight='bold')
    ax2.set_title('Progress Milestones')
    ax2.grid(axis='x', alpha=0.3)
    
    for i, (label, time) in enumerate(zip(milestones, times)):
        ax2.text(time, i, f' {time:.1f}s', va='center', fontweight='bold')
    
    # 3. Latency distribution - Middle left
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(latencies, bins=100, color='#3498db', alpha=0.7, edgecolor='black')
    ax3.axvline(result['p50'], color='green', linestyle='--', linewidth=2, label=f'p50: {result["p50"]:.1f}ms')
    ax3.axvline(result['p95'], color='orange', linestyle='--', linewidth=2, label=f'p95: {result["p95"]:.1f}ms')
    ax3.axvline(result['p99'], color='red', linestyle='--', linewidth=2, label=f'p99: {result["p99"]:.1f}ms')
    ax3.set_xlabel('Latency (ms)', fontweight='bold')
    ax3.set_ylabel('Frequency', fontweight='bold')
    ax3.set_title('Latency Distribution')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # 4. Latency over time (scatter) - Middle middle
    ax4 = fig.add_subplot(gs[1, 1])
    sample_size = min(50000, len(latencies))  # Lấy mẫu để vẽ nhanh hơn
    indices = np.random.choice(len(latencies), sample_size, replace=False)
    sampled_latencies = [latencies[i] for i in sorted(indices)]
    
    ax4.scatter(range(len(sampled_latencies)), sampled_latencies, alpha=0.3, s=1, color='blue')
    ax4.axhline(result['p95'], color='orange', linestyle='--', linewidth=1, label='p95')
    ax4.set_xlabel('Operation #', fontweight='bold')
    ax4.set_ylabel('Latency (ms)', fontweight='bold')
    ax4.set_title(f'Latency Over Time (sample: {sample_size:,})')
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    # 5. CDF - Middle right
    ax5 = fig.add_subplot(gs[1, 2])
    sorted_latencies = np.sort(latencies)
    cumulative = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies) * 100
    ax5.plot(sorted_latencies, cumulative, linewidth=2, color='#2ecc71')
    ax5.axhline(50, color='green', linestyle='--', alpha=0.5, label='p50')
    ax5.axhline(95, color='orange', linestyle='--', alpha=0.5, label='p95')
    ax5.axhline(99, color='red', linestyle='--', alpha=0.5, label='p99')
    ax5.set_xlabel('Latency (ms)', fontweight='bold')
    ax5.set_ylabel('Percentile (%)', fontweight='bold')
    ax5.set_title('Cumulative Distribution (CDF)')
    ax5.legend()
    ax5.grid(alpha=0.3)
    
    # 6. Box plot percentiles - Bottom left
    ax6 = fig.add_subplot(gs[2, 0])
    
    percentile_data = [
        latencies[:int(len(latencies)*0.5)],    # Bottom 50%
        latencies[int(len(latencies)*0.5):int(len(latencies)*0.95)],  # 50-95%
        latencies[int(len(latencies)*0.95):int(len(latencies)*0.99)], # 95-99%
        latencies[int(len(latencies)*0.99):]    # Top 1%
    ]
    
    bp = ax6.boxplot(percentile_data, labels=['0-50%', '50-95%', '95-99%', '99-100%'],
                     patch_artist=True)
    
    colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax6.set_ylabel('Latency (ms)', fontweight='bold')
    ax6.set_title('Latency by Percentile Range')
    ax6.grid(axis='y', alpha=0.3)
    
    # 7. Throughput estimation - Bottom middle
    ax7 = fig.add_subplot(gs[2, 1])
    
    # Calculate throughput per time window
    window_size = max(1, len(latencies) // 100)  # 100 windows
    throughputs = []
    time_points = []
    
    for i in range(0, len(latencies), window_size):
        window = latencies[i:i+window_size]
        if window:
            # Estimate throughput (simplified)
            avg_latency_sec = statistics.mean(window) / 1000
            estimated_throughput = NUM_THREADS / avg_latency_sec if avg_latency_sec > 0 else 0
            throughputs.append(estimated_throughput)
            time_points.append(i / len(latencies) * result['total_time'])
    
    ax7.plot(time_points, throughputs, linewidth=2, color='#9b59b6')
    ax7.axhline(result['throughput'], color='red', linestyle='--', 
               label=f'Avg: {result["throughput"]:.0f} ops/s')
    ax7.set_xlabel('Time (seconds)', fontweight='bold')
    ax7.set_ylabel('Throughput (ops/s)', fontweight='bold')
    ax7.set_title('Estimated Throughput Over Time')
    ax7.legend()
    ax7.grid(alpha=0.3)
    
    # 8. Comparison bar chart - Bottom right
    ax8 = fig.add_subplot(gs[2, 2])
    
    metrics = ['Avg', 'p50', 'p95', 'p99']
    values = [result['avg'], result['p50'], result['p95'], result['p99']]
    colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
    
    bars = ax8.bar(metrics, values, color=colors, alpha=0.7, edgecolor='black')
    ax8.set_ylabel('Latency (ms)', fontweight='bold')
    ax8.set_title('Latency Metrics Comparison')
    ax8.grid(axis='y', alpha=0.3)
    
    for bar in bars:
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}ms',
                ha='center', va='bottom', fontweight='bold')
    
    plt.savefig('extreme_load_benchmark.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Biểu đồ đã lưu: extreme_load_benchmark.png")
    plt.show()

# ============================================================================
# MAIN
# ============================================================================
async def main():
    print("\n" + "="*60)
    print("🔥 EXTREME LOAD BENCHMARK - 1 TRIỆU TIN NHẮN")
    print("="*60)
    print("⚠️  Cảnh báo: Test này sẽ:")
    print("   - Ghi 1,000,000 messages vào database")
    print("   - Tốn nhiều tài nguyên CPU/RAM/Disk")
    print("   - Mất 10-30 phút tùy hardware")
    print("="*60)
    
    response = input("\n⚡ Bạn có muốn tiếp tục? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Đã hủy test")
        return
    
    session, cluster = connect_to_cassandra()
    
    try:
        user_ids, conversation_ids = get_sample_data(session)
        
        result = await benchmark_extreme_load(
            session, conversation_ids, user_ids, TARGET_MESSAGES
        )
        
        plot_extreme_load(result)
        
        print(f"\n✅ Test hoàn thành!")
        print(f"🎉 Cassandra đã xử lý {TARGET_MESSAGES:,} messages trong {result['total_time']/60:.1f} phút")
        print(f"⚡ Throughput trung bình: {result['throughput']:.0f} messages/s")
        
    finally:
        cluster.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
