"""
Benchmark Script for Cassandra Chat App
Test 3 kịch bản:
1. Write Messages (INSERT)
2. Read Messages (SELECT by conversation)
3. Read Conversations (SELECT by user)
"""

import asyncio
import time
import random
import uuid
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement, ConsistencyLevel
import statistics

# Configuration
CONTACT_POINTS = ['127.0.0.1']
PORT = 9042
KEYSPACE = 'realtime_chat_app'

# Benchmark parameters
NUM_OPERATIONS = 10000  # Số operations mỗi test
NUM_THREADS = 50        # Số concurrent threads

def connect_to_cassandra():
    """Kết nối đến Cassandra"""
    cluster = Cluster(CONTACT_POINTS, port=PORT)
    session = cluster.connect(KEYSPACE)
    print(f"✅ Kết nối thành công đến {KEYSPACE}")
    return session, cluster

def get_sample_data(session):
    """Lấy mẫu IDs để test"""
    # Lấy 100 user IDs
    users = session.execute("SELECT user_id FROM users_by_id LIMIT 100")
    user_ids = [row.user_id for row in users]
    
    # Lấy 100 conversation IDs
    convos = session.execute("SELECT conversation_id FROM conversations_by_user LIMIT 500")
    
    # Loại bỏ duplicates thủ công
    conversation_ids = list(set([row.conversation_id for row in convos]))[:100]
    
    print(f"📋 Lấy mẫu: {len(user_ids)} users, {len(conversation_ids)} conversations")
    return user_ids, conversation_ids

# ============================================================================
# BENCHMARK 1: WRITE MESSAGES
# ============================================================================
async def worker_write_message(session, conversation_ids, user_ids):
    """Worker function: Ghi 1 message"""
    conversation_id = random.choice(conversation_ids)
    sender_id = random.choice(user_ids)
    
    query = """
    INSERT INTO messages_by_conversation 
    (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    start = time.perf_counter()
    
    future = session.execute_async(
        query,
        (conversation_id, uuid.uuid1(), sender_id, "benchmark_user", 
         "Benchmark test message", [])
    )
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, future.result)
    
    latency_ms = (time.perf_counter() - start) * 1000
    return latency_ms

async def benchmark_write_messages(session, conversation_ids, user_ids, num_ops):
    """Benchmark: INSERT messages"""
    print(f"\n{'='*60}")
    print(f"📝 BENCHMARK 1: WRITE MESSAGES")
    print(f"{'='*60}")
    print(f"Số operations: {num_ops:,}")
    print(f"Concurrency: {NUM_THREADS} threads")
    
    latencies = []
    start_time = time.time()
    
    # Tạo tasks
    tasks = []
    for _ in range(num_ops):
        tasks.append(worker_write_message(session, conversation_ids, user_ids))
    
    # Chạy concurrent với batch
    batch_size = NUM_THREADS
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*batch)
        latencies.extend(results)
        
        # Progress
        if (i + batch_size) % 1000 == 0:
            print(f"   ✓ Hoàn thành: {min(i+batch_size, num_ops):,}/{num_ops:,}")
    
    total_time = time.time() - start_time
    
    # Calculate metrics
    throughput = num_ops / total_time
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]
    p99 = statistics.quantiles(latencies, n=100)[98]
    
    print(f"\n📊 KẾT QUẢ:")
    print(f"   - Tổng thời gian: {total_time:.2f}s")
    print(f"   - Throughput: {throughput:.2f} ops/s")
    print(f"   - Latency p50: {p50:.2f}ms")
    print(f"   - Latency p95: {p95:.2f}ms")
    print(f"   - Latency p99: {p99:.2f}ms")
    
    return {
        'total_time': total_time,
        'throughput': throughput,
        'p50': p50,
        'p95': p95,
        'p99': p99
    }

# ============================================================================
# BENCHMARK 2: READ MESSAGES
# ============================================================================
async def worker_read_messages(session, conversation_ids):
    """Worker function: Đọc messages của 1 conversation"""
    conversation_id = random.choice(conversation_ids)
    
    query = """
    SELECT sender_username, text_content, attachments
    FROM messages_by_conversation
    WHERE conversation_id = %s
    LIMIT 50
    """
    
    start = time.perf_counter()
    
    future = session.execute_async(query, (conversation_id,))
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, future.result)
    
    latency_ms = (time.perf_counter() - start) * 1000
    return latency_ms

async def benchmark_read_messages(session, conversation_ids, num_ops):
    """Benchmark: SELECT messages"""
    print(f"\n{'='*60}")
    print(f"📖 BENCHMARK 2: READ MESSAGES")
    print(f"{'='*60}")
    print(f"Số operations: {num_ops:,}")
    print(f"Concurrency: {NUM_THREADS} threads")
    
    latencies = []
    start_time = time.time()
    
    tasks = []
    for _ in range(num_ops):
        tasks.append(worker_read_messages(session, conversation_ids))
    
    batch_size = NUM_THREADS
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*batch)
        latencies.extend(results)
        
        if (i + batch_size) % 1000 == 0:
            print(f"   ✓ Hoàn thành: {min(i+batch_size, num_ops):,}/{num_ops:,}")
    
    total_time = time.time() - start_time
    throughput = num_ops / total_time
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]
    p99 = statistics.quantiles(latencies, n=100)[98]
    
    print(f"\n📊 KẾT QUẢ:")
    print(f"   - Tổng thời gian: {total_time:.2f}s")
    print(f"   - Throughput: {throughput:.2f} ops/s")
    print(f"   - Latency p50: {p50:.2f}ms")
    print(f"   - Latency p95: {p95:.2f}ms")
    print(f"   - Latency p99: {p99:.2f}ms")
    
    return {
        'total_time': total_time,
        'throughput': throughput,
        'p50': p50,
        'p95': p95,
        'p99': p99
    }

# ============================================================================
# MAIN
# ============================================================================
async def main():
    print("\n" + "="*60)
    print("🚀 CASSANDRA BENCHMARK - CHAT APP")
    print("="*60)
    
    session, cluster = connect_to_cassandra()
    
    try:
        # Lấy sample data
        user_ids, conversation_ids = get_sample_data(session)
        
        # Benchmark 1: Write Messages
        write_results = await benchmark_write_messages(
            session, conversation_ids, user_ids, NUM_OPERATIONS
        )
        
        # Benchmark 2: Read Messages
        read_results = await benchmark_read_messages(
            session, conversation_ids, NUM_OPERATIONS
        )
        
        # Summary
        print(f"\n{'='*60}")
        print("📈 TỔNG KẾT")
        print("="*60)
        print(f"WRITE: {write_results['throughput']:.0f} ops/s (p95: {write_results['p95']:.1f}ms)")
        print(f"READ:  {read_results['throughput']:.0f} ops/s (p95: {read_results['p95']:.1f}ms)")
        print("="*60 + "\n")
        
    finally:
        cluster.shutdown()

if __name__ == "__main__":
    asyncio.run(main())