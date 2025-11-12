"""
Distributed Benchmark - Ghi 1 triệu tin nhắn từ nhiều máy
Không cần Locust, chỉ cần Python

ARCHITECTURE:
  Coordinator (1 máy) → Điều phối
  Workers (N máy)     → Ghi data song song

USAGE:
  # Trên coordinator:
  python3 distributed_benchmark.py --mode coordinator --workers 4

  # Trên mỗi worker:
  python3 distributed_benchmark.py --mode worker --coordinator-ip 10.0.0.10 --worker-id 1
"""

import asyncio
import socket
import pickle
import time
import uuid
import random
import argparse
import json
from cassandra.cluster import Cluster
from cassandra.query import ConsistencyLevel
import statistics

# Configuration
COORDINATOR_PORT = 50000
CASSANDRA_IPS = ['127.0.0.1']  # Sửa thành IPs thực tế
KEYSPACE = 'realtime_chat_app'

# ============================================================================
# COORDINATOR MODE
# ============================================================================
class Coordinator:
    def __init__(self, num_workers, target_messages):
        self.num_workers = num_workers
        self.target_messages = target_messages
        self.workers = []
        self.results = []
        
    async def start(self):
        """Start coordinator server"""
        server = await asyncio.start_server(
            self.handle_worker, '0.0.0.0', COORDINATOR_PORT
        )
        
        addr = server.sockets[0].getsockname()
        print(f"🎛️  Coordinator listening on {addr}")
        print(f"⏳ Waiting for {self.num_workers} workers to connect...")
        
        async with server:
            await server.serve_forever()
    
    async def handle_worker(self, reader, writer):
        """Handle worker connection"""
        addr = writer.get_extra_info('peername')
        print(f"👷 Worker connected from {addr}")
        
        # Register worker
        self.workers.append({
            'addr': addr,
            'reader': reader,
            'writer': writer
        })
        
        # If all workers connected, start benchmark
        if len(self.workers) == self.num_workers:
            await self.run_distributed_benchmark()
    
    async def run_distributed_benchmark(self):
        """Điều phối benchmark across workers"""
        print(f"\n{'='*60}")
        print(f"🚀 STARTING DISTRIBUTED BENCHMARK")
        print(f"{'='*60}")
        print(f"Workers: {self.num_workers}")
        print(f"Target: {self.target_messages:,} messages")
        print(f"Per worker: {self.target_messages // self.num_workers:,} messages")
        print()
        
        # Send workload to each worker
        messages_per_worker = self.target_messages // self.num_workers
        
        tasks = []
        for i, worker in enumerate(self.workers):
            task = {
                'worker_id': i + 1,
                'target_messages': messages_per_worker,
                'cassandra_ips': CASSANDRA_IPS,
                'keyspace': KEYSPACE
            }
            
            # Send task
            data = pickle.dumps(task)
            worker['writer'].write(len(data).to_bytes(4, 'big'))
            worker['writer'].write(data)
            await worker['writer'].drain()
            
            print(f"✉️  Sent task to Worker #{i+1}: {messages_per_worker:,} messages")
            
            # Collect result
            tasks.append(self.receive_result(worker))
        
        # Wait for all workers to complete
        print(f"\n⏳ Waiting for workers to complete...")
        start_time = time.time()
        
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Aggregate results
        self.print_summary(results, total_time)
        
        # Close connections
        for worker in self.workers:
            worker['writer'].close()
            await worker['writer'].wait_closed()
    
    async def receive_result(self, worker):
        """Receive result from worker"""
        length_bytes = await worker['reader'].read(4)
        length = int.from_bytes(length_bytes, 'big')
        
        data = await worker['reader'].read(length)
        result = pickle.loads(data)
        
        print(f"✅ Received result from Worker #{result['worker_id']}")
        return result
    
    def print_summary(self, results, total_time):
        """In tổng kết kết quả"""
        print(f"\n{'='*60}")
        print(f"🎉 DISTRIBUTED BENCHMARK COMPLETED")
        print(f"{'='*60}\n")
        
        total_messages = sum(r['total_messages'] for r in results)
        total_failures = sum(r['failures'] for r in results)
        
        # Aggregate latencies
        all_latencies = []
        for r in results:
            all_latencies.extend(r['latencies'])
        
        throughput = total_messages / total_time
        p50 = statistics.median(all_latencies)
        p95 = statistics.quantiles(all_latencies, n=20)[18]
        p99 = statistics.quantiles(all_latencies, n=100)[98]
        
        print(f"📊 OVERALL RESULTS:")
        print(f"   - Total messages: {total_messages:,}")
        print(f"   - Total time: {total_time:.2f}s ({total_time/60:.2f} min)")
        print(f"   - Throughput: {throughput:.0f} messages/s")
        print(f"   - Failures: {total_failures} ({total_failures/total_messages*100:.3f}%)")
        print()
        print(f"📈 LATENCY:")
        print(f"   - p50: {p50:.2f}ms")
        print(f"   - p95: {p95:.2f}ms")
        print(f"   - p99: {p99:.2f}ms")
        print()
        print(f"👷 PER WORKER BREAKDOWN:")
        for r in results:
            print(f"   Worker #{r['worker_id']}: "
                  f"{r['total_messages']:,} messages in {r['duration']:.1f}s "
                  f"({r['throughput']:.0f} ops/s)")
        print()
        
        # Save results
        with open('distributed_results.json', 'w') as f:
            json.dump({
                'total_messages': total_messages,
                'total_time': total_time,
                'throughput': throughput,
                'p50': p50,
                'p95': p95,
                'p99': p99,
                'workers': results
            }, f, indent=2)
        
        print(f"💾 Results saved to: distributed_results.json")

# ============================================================================
# WORKER MODE
# ============================================================================
class Worker:
    def __init__(self, coordinator_ip, worker_id):
        self.coordinator_ip = coordinator_ip
        self.worker_id = worker_id
        
    async def connect_and_work(self):
        """Connect to coordinator and execute workload"""
        print(f"👷 Worker #{self.worker_id} connecting to {self.coordinator_ip}:{COORDINATOR_PORT}")
        
        reader, writer = await asyncio.open_connection(
            self.coordinator_ip, COORDINATOR_PORT
        )
        
        print(f"✅ Connected to coordinator")
        
        # Receive task
        length_bytes = await reader.read(4)
        length = int.from_bytes(length_bytes, 'big')
        
        data = await reader.read(length)
        task = pickle.loads(data)
        
        print(f"\n📋 Received task:")
        print(f"   - Messages to write: {task['target_messages']:,}")
        print(f"   - Cassandra: {task['cassandra_ips']}")
        print()
        
        # Execute benchmark
        result = await self.run_benchmark(task)
        
        # Send result back
        data = pickle.dumps(result)
        writer.write(len(data).to_bytes(4, 'big'))
        writer.write(data)
        await writer.drain()
        
        print(f"✅ Sent result back to coordinator")
        
        writer.close()
        await writer.wait_closed()
    
    async def run_benchmark(self, task):
        """Execute actual benchmark"""
        cluster = Cluster(task['cassandra_ips'], port=9042)
        session = cluster.connect(task['keyspace'])
        
        # Prepare statement
        query = """
        INSERT INTO messages_by_conversation 
        (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        prepared_stmt = session.prepare(query)
        prepared_stmt.consistency_level = ConsistencyLevel.ONE
        
        # Get sample data
        print(f"📋 Loading sample data...")
        users = session.execute("SELECT user_id FROM users_by_id LIMIT 1000")
        user_ids = [row.user_id for row in users]
        
        convos = session.execute("SELECT conversation_id FROM conversations_by_user LIMIT 2000")
        conversation_ids = list(set([row.conversation_id for row in convos]))[:1000]
        
        print(f"✅ Loaded {len(user_ids)} users, {len(conversation_ids)} conversations")
        
        # Run benchmark
        latencies = []
        failures = 0
        batch_size = 500
        
        print(f"\n🚀 Starting benchmark...")
        start_time = time.time()
        
        for i in range(0, task['target_messages'], batch_size):
            tasks = []
            
            for _ in range(min(batch_size, task['target_messages'] - i)):
                conversation_id = random.choice(conversation_ids)
                sender_id = random.choice(user_ids)
                
                start = time.perf_counter()
                
                try:
                    future = session.execute_async(
                        prepared_stmt,
                        (conversation_id, uuid.uuid1(), sender_id, 
                         f"worker_{self.worker_id}", 
                         "Distributed test", [])
                    )
                    
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, future.result)
                    
                    latency = (time.perf_counter() - start) * 1000
                    latencies.append(latency)
                except Exception as e:
                    failures += 1
            
            # Progress
            if (i + batch_size) % 10000 == 0:
                elapsed = time.time() - start_time
                current_throughput = (i + batch_size) / elapsed
                print(f"   ✓ Progress: {i+batch_size:,}/{task['target_messages']:,} "
                      f"({current_throughput:.0f} ops/s)")
        
        duration = time.time() - start_time
        throughput = task['target_messages'] / duration
        
        print(f"\n✅ Worker #{self.worker_id} completed!")
        print(f"   - Duration: {duration:.2f}s")
        print(f"   - Throughput: {throughput:.0f} ops/s")
        print(f"   - Failures: {failures}")
        
        cluster.shutdown()
        
        return {
            'worker_id': self.worker_id,
            'total_messages': task['target_messages'],
            'duration': duration,
            'throughput': throughput,
            'failures': failures,
            'latencies': latencies[:10000]  # Chỉ gửi sample để tiết kiệm bandwidth
        }

# ============================================================================
# MAIN
# ============================================================================
async def main():
    parser = argparse.ArgumentParser(description='Distributed Cassandra Benchmark')
    parser.add_argument('--mode', choices=['coordinator', 'worker'], required=True,
                       help='Run as coordinator or worker')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of workers (coordinator mode)')
    parser.add_argument('--target', type=int, default=1000000,
                       help='Total messages to write (coordinator mode)')
    parser.add_argument('--coordinator-ip', type=str, default='127.0.0.1',
                       help='Coordinator IP (worker mode)')
    parser.add_argument('--worker-id', type=int, default=1,
                       help='Worker ID (worker mode)')
    
    args = parser.parse_args()
    
    if args.mode == 'coordinator':
        coordinator = Coordinator(args.workers, args.target)
        await coordinator.start()
    else:
        worker = Worker(args.coordinator_ip, args.worker_id)
        await worker.connect_and_work()

if __name__ == "__main__":
    asyncio.run(main())
