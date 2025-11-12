# 🚀 Quick Start Guide - Cassandra Benchmark Suite

## ⚡ 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Cassandra Cluster

```bash
docker-compose up -d

# Wait 2-3 minutes, then verify
docker exec -it cassandra-1 nodetool status
# Should see 3 nodes with "UN" status
```

### 3. Initialize Database

```bash
docker cp schema.cql cassandra-1:/schema.cql
docker exec -it cassandra-1 cqlsh -f /schema.cql
```

### 4. Generate Test Data

```bash
# For quick test (1K users, 5K conversations, 50K messages)
python3 data_generator.py

# For full test (1M users, 10M conversations, 100M messages)
# Edit NUM_USERS, NUM_CONVERSATIONS, NUM_MESSAGES in data_generator.py first
```

### 5. Run Benchmarks

#### Option 1: Run Everything (Recommended for Assignment)

```bash
python3 benchmark_runner.py
# Takes 30-60 minutes
# Generates all charts and reports automatically
```

#### Option 2: Run Individual Tests

```bash
# Basic performance (5 minutes)
python3 benchmark.py

# Consistency comparison (10 minutes)
python3 benchmark_consistency.py

# Fault tolerance (10 minutes)
python3 benchmark_fault_tolerance.py

# Extreme load - 1M messages (20-30 minutes)
python3 benchmark_extreme_load.py

# Interactive web UI
locust -f locustfile.py
# Open http://localhost:8089
```

---

## 📊 What You Get

### Charts Generated:

1. **consistency_level_comparison.png**
   - Throughput comparison (ONE/QUORUM/ALL)
   - Latency percentiles
   - Distribution histograms
   - CDF curves

2. **fault_tolerance_benchmark.png**
   - Latency over time (with node failure marked)
   - Moving average
   - Before/after comparison
   - Failure rate

3. **extreme_load_benchmark.png**
   - 8-panel comprehensive dashboard
   - Progress milestones
   - Throughput analysis
   - Full latency metrics

### Reports:

- **SUMMARY_REPORT.md** - Master summary with all results
- Individual log files for each benchmark
- HTML/CSV exports from Locust (if used)

---

## 🎯 Expected Timeline

| Task | Duration | Status Check |
|------|----------|--------------|
| Setup cluster | 5 min | `docker ps` shows 3 containers |
| Generate data | 5-10 min | `python3 data_check.py` |
| Basic benchmark | 5 min | `benchmark.py` completes |
| Consistency test | 10 min | Chart saved |
| Fault tolerance | 10 min | Node restarts successfully |
| Extreme load | 20-30 min | 1M messages written |
| **Total** | **~60 min** | All charts + reports ready |

---

## ✅ Checklist for Assignment Submission

- [ ] Cassandra cluster running (3 nodes, all UN)
- [ ] Schema applied successfully
- [ ] Test data generated (check with `data_check.py`)
- [ ] All 4 benchmarks completed
- [ ] Charts generated:
  - [ ] consistency_level_comparison.png
  - [ ] fault_tolerance_benchmark.png
  - [ ] extreme_load_benchmark.png
- [ ] SUMMARY_REPORT.md exists
- [ ] README.md reviewed

---

## 🐛 Quick Troubleshooting

### "No nodes present in cluster"
```bash
# Wait longer, check logs
docker logs cassandra-1 | grep "Starting listening for CQL clients"
```

### "Table does not exist"
```bash
# Re-apply schema
docker exec -it cassandra-1 cqlsh -f /schema.cql
```

### "Connection timeout"
```bash
# Restart cluster
docker-compose restart
sleep 60
docker exec -it cassandra-1 nodetool status
```

### Low performance
```bash
# Allocate more resources to Docker
# Docker Desktop → Settings → Resources
# - CPUs: 4+
# - Memory: 8GB+
```

---

## 📚 Next Steps

1. **Analyze Results:** Open generated charts and reports
2. **Write Report:** Use metrics from SUMMARY_REPORT.md
3. **Locust Demo:** Run `locust -f locustfile.py` for live demo
4. **Cleanup:** `docker-compose down -v` when done

---

**Need help?** Check the full [README.md](README.md) for detailed documentation.
