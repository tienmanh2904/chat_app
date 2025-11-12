# Cassandra Chat App Benchmark

A comprehensive benchmark suite for testing Apache Cassandra's performance in a real-time chat application scenario.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Benchmark Tools](#benchmark-tools)
- [Advanced Benchmarks](#advanced-benchmarks)
- [Results](#results)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This project demonstrates Cassandra's capabilities for handling:
- **High write throughput**: Millions of messages inserted concurrently
- **Low read latency**: Fast retrieval of conversation history
- **Fault tolerance**: Replication across 3 nodes
- **Scalability**: Horizontal scaling with consistent performance

### Key Features

- ✅ 3-node Cassandra cluster with Docker
- ✅ Realistic chat app data model (users, conversations, messages)
- ✅ Automated data generation (Faker library)
- ✅ Multiple benchmark tools (Python asyncio, Locust)
- ✅ Comprehensive metrics (throughput, latency p50/p95/p99)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Client Applications                  │
│  (data_generator.py, benchmark.py, locustfile.py)  │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ CQL Protocol (Port 9042)
                  │
┌─────────────────┴───────────────────────────────────┐
│              Cassandra Cluster (RF=3)                │
├─────────────────┬─────────────────┬──────────────────┤
│  cassandra-1    │  cassandra-2    │  cassandra-3     │
│  (Seed Node)    │                 │                  │
│  Port: 9042     │                 │                  │
└─────────────────┴─────────────────┴──────────────────┘
```

### Data Model

**Tables:**
- `users_by_id` - User profiles (partition key: user_id)
- `users_by_username` - User lookup (partition key: username)
- `conversations_by_user` - User's conversation list (partition key: user_id)
- `members_by_conversation` - Conversation members (partition key: conversation_id)
- `messages_by_conversation` - Chat messages (partition key: conversation_id, clustering: timestamp)

## 📦 Prerequisites

### Required Software

- Docker & Docker Compose
- Python 3.10+
- pip (Python package manager)

### Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
cassandra-driver>=3.28.0
faker>=20.0.0
locust>=2.15.0
numpy>=1.24.0
```

## 🚀 Quick Start

### 1. Start Cassandra Cluster

```bash
# Start 3-node cluster
docker-compose up -d

# Wait for nodes to join cluster (2-3 minutes)
docker exec -it cassandra-1 nodetool status

# Expected output: 3 nodes with status "UN" (Up/Normal)
```

### 2. Initialize Schema

```bash
# Apply schema to cluster
docker cp schema.cql cassandra-1:/schema.cql
docker exec -it cassandra-1 cqlsh -f /schema.cql

# Verify tables created
docker exec -it cassandra-1 cqlsh -e "DESCRIBE realtime_chat_app"
```

### 3. Generate Test Data

```bash
# Generate sample data (adjust NUM_USERS, NUM_CONVERSATIONS, NUM_MESSAGES in file)
python3 data_generator.py

# Verify data
python3 data_check.py
```

### 4. Run Benchmarks

#### Quick Start: Run All Benchmarks

```bash
# Run all benchmarks automatically (takes 30-60 minutes)
python3 benchmark_runner.py
```

**This will:**
- ✅ Run all 4 benchmark scenarios
- ✅ Generate charts/graphs for each
- ✅ Create summary report
- ✅ Save all results to timestamped folder

**Output structure:**
```
benchmark_results_20250112_143000/
├── SUMMARY_REPORT.md
├── basic_benchmark.log
├── consistency_level_test.log
├── fault_tolerance_test.log
├── extreme_load_test.log
├── consistency_level_comparison.png
├── fault_tolerance_benchmark.png
└── extreme_load_benchmark.png
```

---

#### Option A: Individual Benchmarks

**Basic Benchmark:**
```bash
python3 benchmark.py
```

**Consistency Level Comparison:**
```bash
python3 benchmark_consistency.py
```

**Fault Tolerance Test:**
```bash
python3 benchmark_fault_tolerance.py
```

**Extreme Load Test (1M messages):**
```bash
python3 benchmark_extreme_load.py
```

---

#### Option B: Locust Web UI Testing

```bash
# Start Locust
locust -f locustfile.py

# Open browser: http://localhost:8089
# Configure:
#   - Number of users: 100
#   - Spawn rate: 10 users/second
#   - Host: http://localhost (not used, but required field)
```

**Locust Dashboard provides:**
- 📊 Real-time charts (RPS, response time)
- 📈 Percentile graphs (p50, p95, p99)
- 📉 Failure rate monitoring
- 💾 Export HTML/CSV reports

## 📁 Project Structure

```
.
├── docker-compose.yml              # Cassandra cluster configuration
├── schema.cql                      # Database schema (keyspace + tables)
├── data_generator.py               # Generate fake users/conversations/messages
├── data_check.py                   # Verify data in database
│
├── benchmark.py                    # Basic asyncio benchmark
├── benchmark_consistency.py        # Consistency level comparison (ONE/QUORUM/ALL)
├── benchmark_fault_tolerance.py    # Node failure simulation
├── benchmark_extreme_load.py       # 1 million messages spike test
├── locustfile.py                   # Locust web UI load testing
│
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🔧 Configuration

### Cassandra Cluster Settings

**docker-compose.yml:**
```yaml
services:
  cassandra-1:
    image: cassandra:4.1
    environment:
      - CASSANDRA_CLUSTER_NAME=ChatAppCluster
      - CASSANDRA_DC=dc1
      - CASSANDRA_RACK=rack1
    healthcheck:
      test: ["CMD-SHELL", "nodetool status"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 90s
```

### Benchmark Parameters

**data_generator.py:**
```python
NUM_USERS = 1000          # Adjust for your test
NUM_CONVERSATIONS = 5000
NUM_MESSAGES = 50000
BATCH_SIZE = 1000         # Concurrent inserts per batch
```

**benchmark.py:**
```python
NUM_OPERATIONS = 10000    # Total operations per test
NUM_THREADS = 50          # Concurrent threads
```

**locustfile.py:**
```python
wait_time = between(1, 3) # User think time (seconds)

@task(3)  # send_message weight
@task(5)  # read_messages weight
@task(2)  # read_conversations weight
```

## 📊 Benchmark Scenarios

### Basic Benchmarks

#### 1. Write Messages (INSERT)
**File:** `benchmark.py`  
**Test:** Insert 10,000 messages concurrently
- Measures write throughput (ops/s)
- Tests Cassandra's optimized write path
- Validates replication across nodes

#### 2. Read Messages (SELECT by conversation)
**File:** `benchmark.py`  
**Test:** Retrieve 50 messages from 10,000 conversations
- Measures read latency (p50, p95, p99)
- Tests partition key efficiency
- Validates clustering order (timestamp DESC)

#### 3. Read Conversations (SELECT by user)
**File:** `benchmark.py`  
**Test:** Load conversation list for 10,000 users
- Measures denormalized table performance
- Tests secondary access patterns
- Validates data locality

## 🚀 Advanced Benchmarks

### 1. Consistency Level Comparison

**File:** `benchmark_consistency.py`

**Purpose:** Compare performance across different consistency levels (ONE, QUORUM, ALL)

**Run:**
```bash
python3 benchmark_consistency.py
```

**What it tests:**
- ✅ Write throughput with ONE (fastest)
- ✅ Write throughput with QUORUM (balanced)
- ✅ Write throughput with ALL (strongest consistency)
- ✅ Latency distribution for each level
- ✅ Trade-off between speed and consistency

**Output:**
- 📊 Comparison charts (throughput, latency p50/p95/p99)
- 📈 Latency distribution histograms
- 📉 CDF (Cumulative Distribution Function)
- 💾 Saved as `consistency_level_comparison.png`

**Expected Results:**
```
ONE:    ~2000 ops/s, p95: 30ms    (Fastest, least consistent)
QUORUM: ~1500 ops/s, p95: 45ms    (Balanced)
ALL:    ~800 ops/s,  p95: 80ms    (Slowest, most consistent)
```

---

### 2. Fault Tolerance Test

**File:** `benchmark_fault_tolerance.py`

**Purpose:** Test system behavior when 1 node fails during operation

**⚠️ Warning:** This script will **stop and restart** a Cassandra node!

**Run:**
```bash
python3 benchmark_fault_tolerance.py
```

**What it tests:**
- ✅ Normal operation (all 3 nodes up)
- ✅ Automatic failover when cassandra-2 stops
- ✅ Performance impact during failure
- ✅ Error rate with QUORUM consistency
- ✅ Recovery after node restart

**Behavior:**
1. Starts benchmark with 10,000 operations
2. After operation 5,000: **stops cassandra-2**
3. Continues testing with 2/3 nodes
4. Measures latency increase and failure rate
5. Restarts cassandra-2 after test

**Output:**
- � Latency over time (shows spike when node dies)
- �📈 Moving average latency
- 📉 Failure rate over time
- 💾 Saved as `fault_tolerance_benchmark.png`

**Expected Results:**
```
Before failure: p95: 40ms, failures: 0%
After failure:  p95: 120ms, failures: 0.1-1%
Conclusion: System remains operational with degraded performance
```

---

### 3. Extreme Load Test (1 Million Messages)

**File:** `benchmark_extreme_load.py`

**Purpose:** Simulate spike traffic (e.g., Tết holiday, major event)

**⚠️ Warning:** 
- Takes 10-30 minutes depending on hardware
- Writes 1,000,000 messages to database
- High CPU/RAM/Disk usage

**Run:**
```bash
python3 benchmark_extreme_load.py
# Confirms with: yes
```

**What it tests:**
- ✅ Sustained high throughput (1M messages)
- ✅ System stability under extreme load
- ✅ Latency degradation over time
- ✅ Memory and disk behavior
- ✅ Real-world spike traffic simulation

**Optimizations used:**
- Prepared statements
- Consistency level ONE (max throughput)
- 200 concurrent threads
- Batch size 500

**Output:**
- 📊 8-panel comprehensive dashboard:
  - Summary metrics
  - Progress milestones (25%, 50%, 75%, 100%)
  - Latency distribution
  - Latency over time
  - CDF curve
  - Box plots by percentile
  - Throughput over time
  - Metrics comparison
- 💾 Saved as `extreme_load_benchmark.png`

**Expected Results:**
```
Duration: 10-20 minutes
Throughput: 800-1500 ops/s sustained
Total: 1,000,000 messages
Latency p95: 50-100ms
Failures: <0.01%
```

**Use case:** Proves Cassandra can handle viral events, holiday traffic spikes

---

### 4. Locust Web UI Testing

**File:** `locustfile.py`

**Purpose:** Interactive load testing with real-time web dashboard

**Run:**
```bash
locust -f locustfile.py

# Open browser: http://localhost:8089
# Configure users and spawn rate
```

**Features:**
- 📊 Real-time charts
- 📈 Response time percentiles
- 📉 RPS (Requests Per Second)
- 💾 Download HTML/CSV reports
- 🔄 Start/stop tests on demand

**Tasks simulated:**
- Send message (weight: 3)
- Read messages (weight: 5)  
- Read conversations (weight: 2)

## 📈 Expected Results

### Basic Performance (Docker local, 3 nodes)

| Metric | Write | Read |
|--------|-------|------|
| **Throughput** | 1,000-2,000 ops/s | 500-1,000 ops/s |
| **Latency p50** | 20-30ms | 60-80ms |
| **Latency p95** | 40-60ms | 100-150ms |
| **Latency p99** | 50-80ms | 150-200ms |

### Extreme Load Performance

| Metric | 1M Messages Test |
|--------|------------------|
| **Duration** | 10-20 minutes |
| **Throughput** | 800-1,500 ops/s |
| **Latency p95** | 50-100ms |
| **Failure Rate** | <0.01% |

### Consistency Level Comparison

| Level | Throughput | p95 Latency | Consistency |
|-------|-----------|-------------|-------------|
| **ONE** | ~2,000 ops/s | 30ms | Weakest |
| **QUORUM** | ~1,500 ops/s | 45ms | Balanced ✅ |
| **ALL** | ~800 ops/s | 80ms | Strongest |

### Production Performance (Dedicated hardware)

| Metric | Write | Read |
|--------|-------|------|
| **Throughput** | 10,000-50,000 ops/s | 5,000-20,000 ops/s |
| **Latency p50** | 2-5ms | 5-10ms |
| **Latency p95** | 10-20ms | 20-30ms |

## 🔍 Monitoring

### Check Cluster Status

```bash
# Node status
docker exec -it cassandra-1 nodetool status

# Table statistics
docker exec -it cassandra-1 nodetool tablestats realtime_chat_app

# Compaction status
docker exec -it cassandra-1 nodetool compactionstats
```

### View Logs

```bash
# Real-time logs
docker logs -f cassandra-1

# Last 100 lines
docker logs cassandra-1 --tail 100
```

### Query Data Manually

```bash
# Connect to cqlsh
docker exec -it cassandra-1 cqlsh

# Run queries
cqlsh> USE realtime_chat_app;
cqlsh:realtime_chat_app> SELECT COUNT(*) FROM users_by_id;
cqlsh:realtime_chat_app> SELECT * FROM messages_by_conversation LIMIT 10;
```

## 🐛 Troubleshooting

### Issue: "No nodes present in the cluster"

**Cause:** Cassandra still starting up

**Solution:**
```bash
# Wait 60-90 seconds, then check logs
docker logs cassandra-1

# Look for: "Starting listening for CQL clients..."
```

### Issue: "Bootstrap Token collision"

**Cause:** Multiple nodes started simultaneously

**Solution:**
```bash
# Stop all containers
docker-compose down -v

# Start sequentially (with delays)
docker-compose up -d cassandra-1
sleep 120
docker-compose up -d cassandra-2
sleep 120
docker-compose up -d cassandra-3
```

### Issue: "Table does not exist"

**Cause:** Schema not applied

**Solution:**
```bash
# Apply schema
docker cp schema.cql cassandra-1:/schema.cql
docker exec -it cassandra-1 cqlsh -f /schema.cql
```

### Issue: Low benchmark performance

**Possible causes:**
1. **Insufficient concurrency** → Increase `NUM_THREADS`
2. **Docker resource limits** → Allocate more CPU/RAM to Docker
3. **Disk I/O bottleneck** → Use SSD for Docker volumes
4. **Small dataset** → Increase test data size

**Solutions:**
```bash
# Increase Docker resources (Docker Desktop → Settings → Resources)
# - CPUs: 4+
# - Memory: 8GB+

# Increase Cassandra heap
docker-compose.yml:
  environment:
    - MAX_HEAP_SIZE=2G
    - HEAP_NEWSIZE=400M
```

### Issue: Connection timeout

**Cause:** Firewall or network issue

**Solution:**
```bash
# Check if port is accessible
telnet 127.0.0.1 9042

# Check container network
docker network inspect code_cassandra-net

# Restart cluster
docker-compose restart
```

## 📚 Additional Resources

### Cassandra Documentation
- [Official Docs](https://cassandra.apache.org/doc/latest/)
- [Data Modeling Best Practices](https://cassandra.apache.org/doc/latest/cassandra/data_modeling/intro.html)
- [Performance Tuning](https://cassandra.apache.org/doc/latest/cassandra/operating/tuning.html)

### Benchmark Tools
- [Locust Documentation](https://docs.locust.io/)
- [NoSQLBench](https://github.com/nosqlbench/nosqlbench)
- [cassandra-stress](https://cassandra.apache.org/doc/latest/cassandra/tools/cassandra_stress.html)

### Python Driver
- [DataStax Python Driver](https://docs.datastax.com/en/developer/python-driver/latest/)
- [Async Queries](https://docs.datastax.com/en/developer/python-driver/latest/execution_profiles.html)

## 🤝 Contributing

Feel free to submit issues or pull requests to improve this benchmark suite.

## 📝 License

This project is for educational purposes as part of a database course assignment.

## 👥 Authors

- Database Assignment - Master's Program

## 🙏 Acknowledgments

- Apache Cassandra community
- DataStax documentation
- Faker library for realistic test data
- Locust.io for load testing framework
