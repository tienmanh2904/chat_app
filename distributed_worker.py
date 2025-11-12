"""
Distributed Locust Worker - Chạy trên Digital Ocean droplets
File này sẽ chạy trên MỖI worker node
"""

from locust import User, task, between, events
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement, ConsistencyLevel
import uuid
import random
import time
import os

# Cassandra cluster IPs (thay bằng IPs thực tế)
CASSANDRA_IPS = os.getenv('CASSANDRA_IPS', '127.0.0.1').split(',')
KEYSPACE = 'realtime_chat_app'

# Global connection
cluster = None
session = None
user_ids = []
conversation_ids = []
prepared_stmt = None

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Khởi tạo connection khi worker start"""
    global cluster, session, user_ids, conversation_ids, prepared_stmt
    
    print(f"🔌 Connecting to Cassandra: {CASSANDRA_IPS}")
    
    cluster = Cluster(CASSANDRA_IPS, port=9042)
    session = cluster.connect(KEYSPACE)
    session.default_timeout = 30.0
    
    # Prepare statement để tối ưu performance
    query = """
    INSERT INTO messages_by_conversation 
    (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    prepared_stmt = session.prepare(query)
    prepared_stmt.consistency_level = ConsistencyLevel.ONE
    
    # Load sample data
    print("📋 Loading sample data...")
    users = session.execute("SELECT user_id FROM users_by_id LIMIT 1000")
    user_ids = [row.user_id for row in users]
    
    convos = session.execute("SELECT conversation_id FROM conversations_by_user LIMIT 2000")
    conversation_ids = list(set([row.conversation_id for row in convos]))[:1000]
    
    print(f"✅ Worker ready: {len(user_ids)} users, {len(conversation_ids)} conversations")

class DistributedCassandraUser(User):
    """User simulation cho distributed load test"""
    
    # Không có wait time → tải tối đa
    wait_time = between(0, 0.1)
    
    @task
    def write_message(self):
        """Ghi message với maximum throughput"""
        conversation_id = random.choice(conversation_ids)
        sender_id = random.choice(user_ids)
        
        start_time = time.time()
        
        try:
            session.execute(
                prepared_stmt,
                (conversation_id, uuid.uuid1(), sender_id, 
                 f"worker_{os.getpid()}", 
                 "Distributed load test", [])
            )
            
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="write_message",
                response_time=total_time,
                response_length=0,
                exception=None,
                context={}
            )
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="write_message",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )

@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Cleanup khi worker stop"""
    global cluster
    if cluster:
        cluster.shutdown()
        print("✅ Worker shutdown")
