#!/bin/bash
#
# Script setup Distributed Locust trên Digital Ocean Droplets
# Chạy script này để tự động setup master + workers
#

set -e

echo "=================================================="
echo "  DISTRIBUTED LOCUST SETUP FOR CASSANDRA BENCH   "
echo "=================================================="
echo ""

# ============================================================================
# CONFIGURATION - SỬA PHẦN NÀY
# ============================================================================

# IP của Cassandra cluster (phân cách bằng dấu phẩy)
CASSANDRA_IPS="10.0.0.1,10.0.0.2,10.0.0.3"

# IP của Master node (droplet chạy web UI)
MASTER_IP="10.0.0.10"

# Số lượng workers
NUM_WORKERS=4

# Target: 1 triệu messages
TARGET_MESSAGES=1000000

# Spawn rate (users/giây)
SPAWN_RATE=1000

# ============================================================================
# FUNCTIONS
# ============================================================================

setup_python() {
    echo "📦 Installing Python dependencies..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip
    pip3 install locust cassandra-driver
}

setup_master() {
    echo "🎛️  Setting up MASTER node..."
    
    # Copy locust file
    cat > /tmp/distributed_worker.py <<'EOF'
# Nội dung file distributed_worker.py ở trên
EOF
    
    # Start master
    echo "🚀 Starting Locust Master on port 8089..."
    export CASSANDRA_IPS="$CASSANDRA_IPS"
    
    nohup locust -f /tmp/distributed_worker.py \
        --master \
        --master-bind-port=5557 \
        --web-host=0.0.0.0 \
        --web-port=8089 \
        > /var/log/locust_master.log 2>&1 &
    
    echo "✅ Master started!"
    echo "   Web UI: http://$MASTER_IP:8089"
    echo "   Master port: 5557"
}

setup_worker() {
    local worker_id=$1
    
    echo "👷 Setting up WORKER #$worker_id..."
    
    export CASSANDRA_IPS="$CASSANDRA_IPS"
    
    nohup locust -f /tmp/distributed_worker.py \
        --worker \
        --master-host=$MASTER_IP \
        --master-port=5557 \
        > /var/log/locust_worker_$worker_id.log 2>&1 &
    
    echo "✅ Worker #$worker_id started!"
}

# ============================================================================
# MAIN
# ============================================================================

echo "📋 Configuration:"
echo "   Cassandra IPs: $CASSANDRA_IPS"
echo "   Master IP: $MASTER_IP"
echo "   Workers: $NUM_WORKERS"
echo "   Target: $TARGET_MESSAGES messages"
echo ""

read -p "⚡ Continue? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "❌ Cancelled"
    exit 1
fi

# Detect node type
echo ""
echo "🔍 Select node type:"
echo "   1) Master (Web UI + coordinator)"
echo "   2) Worker (load generator)"
echo ""
read -p "Choice (1 or 2): " node_type

setup_python

if [ "$node_type" = "1" ]; then
    setup_master
    
    echo ""
    echo "=================================================="
    echo "✅ MASTER NODE READY"
    echo "=================================================="
    echo ""
    echo "📊 Web UI: http://$MASTER_IP:8089"
    echo "🔌 Master port: 5557"
    echo ""
    echo "Next steps:"
    echo "  1. Setup workers on other droplets (choose option 2)"
    echo "  2. Open web UI and configure:"
    echo "     - Number of users: $(($TARGET_MESSAGES / 10))"
    echo "     - Spawn rate: $SPAWN_RATE"
    echo "  3. Click 'Start swarming'"
    echo ""
    
elif [ "$node_type" = "2" ]; then
    echo ""
    read -p "Worker ID (1-$NUM_WORKERS): " worker_id
    
    setup_worker $worker_id
    
    echo ""
    echo "=================================================="
    echo "✅ WORKER #$worker_id READY"
    echo "=================================================="
    echo ""
    echo "Connected to master: $MASTER_IP:5557"
    echo "Logs: /var/log/locust_worker_$worker_id.log"
    echo ""
else
    echo "❌ Invalid choice"
    exit 1
fi

echo "Check status:"
echo "  ps aux | grep locust"
echo ""
