# 🌐 Distributed Load Testing Guide

## Ghi 1 Triệu Tin Nhắn Đồng Thời Từ Nhiều Máy

Hướng dẫn này mô tả 3 phương pháp test distributed load với nhiều Digital Ocean droplets.

---

## 📊 Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────┐
│                    INTERNET                              │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬────────────┬──────────────┐
    │            │            │            │              │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐
│Droplet1│  │Droplet2│  │Droplet3│  │Droplet4│  │Droplet5│
│MASTER  │  │WORKER 1│  │WORKER 2│  │WORKER 3│  │WORKER 4│
│(Web UI)│  │        │  │        │  │        │  │        │
└───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
    │           │            │            │            │
    └───────────┴────────────┴────────────┴────────────┘
                             │
                    ┌────────▼─────────┐
                    │ Cassandra Cluster│
                    │   (3 nodes)      │
                    └──────────────────┘
```

**Workload phân chia:**
- 1M messages / 4 workers = **250K messages per worker**
- Tất cả workers ghi **đồng thời**
- Coordinator tổng hợp kết quả

---

## 🚀 Phương Pháp 1: Distributed Locust (Khuyến nghị)

### **Ưu điểm:**
- ✅ Web UI đẹp, real-time
- ✅ Auto scaling workers
- ✅ Built-in metrics aggregation
- ✅ Easy setup

### **Setup trên Digital Ocean:**

#### **Bước 1: Tạo Droplets**

```bash
# Tạo 5 droplets (1 master + 4 workers)
# Specs khuyến nghị:
# - Master: 2 vCPU, 4GB RAM
# - Workers: 2 vCPU, 2GB RAM mỗi cái
# - OS: Ubuntu 22.04 LTS
```

#### **Bước 2: Setup Master Node**

```bash
# SSH vào master droplet
ssh root@<master_ip>

# Update & install Python
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip git

# Install dependencies
pip3 install locust cassandra-driver

# Clone repo
git clone https://github.com/tienmanh2904/chat_app.git
cd chat_app

# Sửa CASSANDRA_IPS trong distributed_worker.py
nano distributed_worker.py
# Thay CASSANDRA_IPS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']

# Start Locust Master
locust -f distributed_worker.py \
  --master \
  --master-bind-port=5557 \
  --web-host=0.0.0.0 \
  --web-port=8089

# Mở browser: http://<master_ip>:8089
```

#### **Bước 3: Setup Worker Nodes**

```bash
# SSH vào mỗi worker droplet (lặp lại cho 4 workers)
ssh root@<worker_ip>

# Install Python & dependencies
apt-get update
apt-get install -y python3 python3-pip
pip3 install locust cassandra-driver

# Clone repo
git clone https://github.com/tienmanh2904/chat_app.git
cd chat_app

# Sửa CASSANDRA_IPS
nano distributed_worker.py
# Thay CASSANDRA_IPS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']

# Start Locust Worker
locust -f distributed_worker.py \
  --worker \
  --master-host=<master_ip> \
  --master-port=5557
```

#### **Bước 4: Chạy Test**

1. Mở browser: `http://<master_ip>:8089`
2. Configure:
   - **Number of users:** 1000 (mỗi user ghi liên tục)
   - **Spawn rate:** 100 users/s
   - **Host:** http://localhost (không quan trọng)
3. Click **"Start swarming"**
4. Chờ đến khi đạt 1 triệu requests
5. Download report (HTML/CSV)

**Kết quả mong đợi:**
```
Total requests: 1,000,000
Duration: 10-15 minutes
Throughput: 1,000-1,500 requests/s
Failures: <0.1%
```

---

## 🚀 Phương Pháp 2: Python Distributed Benchmark

### **Ưu điểm:**
- ✅ Không cần Locust
- ✅ Kiểm soát chi tiết hơn
- ✅ Custom protocol

### **Setup:**

#### **Bước 1: Setup Coordinator**

```bash
# SSH vào coordinator droplet
ssh root@<coordinator_ip>

# Install dependencies
apt-get update
apt-get install -y python3 python3-pip
pip3 install cassandra-driver

# Clone repo
git clone https://github.com/tienmanh2904/chat_app.git
cd chat_app

# Sửa CASSANDRA_IPS trong distributed_benchmark.py
nano distributed_benchmark.py
# Thay: CASSANDRA_IPS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']

# Start coordinator (chờ 4 workers)
python3 distributed_benchmark.py \
  --mode coordinator \
  --workers 4 \
  --target 1000000
```

#### **Bước 2: Setup Workers**

```bash
# SSH vào mỗi worker (lặp lại 4 lần)
ssh root@<worker_ip>

# Install
apt-get update && apt-get install -y python3 python3-pip
pip3 install cassandra-driver

# Clone repo
git clone https://github.com/tienmanh2904/chat_app.git
cd chat_app

# Sửa CASSANDRA_IPS
nano distributed_benchmark.py

# Start worker (thay worker-id: 1, 2, 3, 4)
python3 distributed_benchmark.py \
  --mode worker \
  --coordinator-ip <coordinator_ip> \
  --worker-id 1
```

#### **Kết quả:**

Coordinator sẽ tự động:
1. Phân chia workload (250K messages/worker)
2. Gửi tasks cho workers
3. Thu thập kết quả
4. Tính metrics tổng hợp
5. Lưu vào `distributed_results.json`

---

## 🚀 Phương Pháp 3: Apache JMeter Distributed

### **Setup (Tóm tắt):**

```bash
# Master
jmeter -n -t cassandra_test.jmx \
  -R <worker1_ip>,<worker2_ip>,<worker3_ip>,<worker4_ip> \
  -l results.jtl

# Workers
jmeter-server
```

**Nhược điểm:** Phức tạp hơn, cần tạo JMX file

---

## 📊 So Sánh Các Phương Pháp

| Tiêu chí | Locust | Python Custom | JMeter |
|----------|--------|---------------|--------|
| **Dễ setup** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Web UI** | ✅ Có | ❌ Không | ✅ Có |
| **Real-time metrics** | ✅ Có | ❌ Không | ⚠️ Limited |
| **Custom logic** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Cassandra support** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Khuyến nghị** | ✅ Best | ⚠️ Advanced | ❌ Complex |

---

## 💰 Chi Phí Digital Ocean

### **Cấu hình khuyến nghị:**

| Node | Specs | Giá/giờ | Giá/tháng |
|------|-------|---------|-----------|
| Master | 2 vCPU, 4GB | $0.036 | $24 |
| Worker 1-4 | 2 vCPU, 2GB | $0.018 | $12 |

**Tổng chi phí test 1 giờ:** ~$0.11  
**Tổng chi phí nếu chạy full tháng:** ~$72

**💡 Tip:** Dùng "Hourly Billing" → Chỉ trả tiền khi chạy → ~$0.20 cho 1 test session

---

## 🎯 Kịch Bản Test Thực Tế

### **Scenario 1: Black Friday Sale**

```
Target: 1M messages trong 10 phút
Workers: 4 droplets
User simulation: 
  - 1000 users concurrent
  - Mỗi user gửi liên tục
  - Spawn rate: 100 users/s
```

### **Scenario 2: New Year's Eve**

```
Target: 1M messages trong 5 phút
Workers: 8 droplets
Spike pattern:
  - 0-1 min: 500 users
  - 1-2 min: 1500 users (spike)
  - 2-5 min: 1000 users (sustained)
```

### **Scenario 3: Viral Event**

```
Target: 5M messages trong 30 phút
Workers: 10 droplets
Pattern: Exponential growth
  - 0-5 min: 500 users
  - 5-10 min: 2000 users
  - 10-30 min: 5000 users
```

---

## 📈 Metrics Thu Thập

### **Từ Locust Dashboard:**
- 📊 RPS (Requests Per Second) - Real-time
- 📈 Response time distribution
- 📉 Failure rate
- 💾 Total requests completed

### **Từ Cassandra:**
```bash
# Trên cassandra node
nodetool tablestats realtime_chat_app

# Metrics quan tâm:
# - Write latency
# - Pending compactions
# - Memtable flush count
# - SSTables count
```

### **Từ System:**
```bash
# CPU usage
top

# Disk I/O
iostat -x 1

# Network
iftop
```

---

## ✅ Checklist Trước Khi Chạy

- [ ] Cassandra cluster đang chạy (3 nodes, all UN)
- [ ] Test data đã được generate
- [ ] Firewall rules cho phép:
  - Port 9042 (Cassandra CQL)
  - Port 5557 (Locust master-worker communication)
  - Port 8089 (Locust web UI)
- [ ] DNS/IPs đã được cấu hình đúng
- [ ] Workers có thể kết nối đến Cassandra
- [ ] Master có thể nhận connections từ workers

---

## 🐛 Troubleshooting

### **Workers không connect được đến Master**

```bash
# Kiểm tra firewall
ufw status
ufw allow 5557

# Kiểm tra Locust đang chạy
ps aux | grep locust

# Kiểm tra network
telnet <master_ip> 5557
```

### **Cassandra timeout**

```bash
# Tăng timeout trong code
session.default_timeout = 60.0

# Hoặc sử dụng ONE thay vì QUORUM
consistency_level = ConsistencyLevel.ONE
```

### **Low throughput**

```bash
# Tăng workers
# Tăng concurrent users
# Giảm wait time giữa requests

# Locust:
wait_time = between(0, 0.1)  # Gần như không đợi
```

---

## 📊 Kết Quả Mong Đợi

### **Với 4 Workers (2 vCPU mỗi cái):**

```
Total messages: 1,000,000
Duration: 10-15 minutes
Aggregate throughput: 1,000-1,500 messages/s
Per-worker throughput: 250-375 messages/s

Latency:
  p50: 20-40ms
  p95: 60-120ms
  p99: 100-200ms

Failures: <0.1%
```

### **Với 10 Workers:**

```
Total messages: 1,000,000
Duration: 5-8 minutes
Aggregate throughput: 2,000-3,000 messages/s

Latency:
  p50: 15-30ms
  p95: 40-80ms
  p99: 60-120ms
```

---

## 🎉 Kết Luận

**Khuyến nghị cho assignment:**

1. **Dùng Locust distributed** - Dễ demo, có web UI đẹp
2. **4 workers** là đủ cho 1M messages
3. **Chi phí ~$0.20** cho 1 test session
4. **Screenshots** từ Locust web UI rất impressive cho báo cáo

**Alternative:**
- Nếu không có budget → Dùng `distributed_benchmark.py` trên local VMs
- Nếu cần control tuyệt đối → Dùng Python custom

**Proof cho assignment:**
- ✅ Screenshots Locust dashboard (4 workers connected)
- ✅ Real-time RPS graph hitting 1000+ ops/s
- ✅ Total requests: 1,000,000
- ✅ Failure rate: <0.1%
- ✅ Cassandra metrics (nodetool tablestats)
