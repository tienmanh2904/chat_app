"""
Locust benchmark file cho Cassandra Chat App
Chạy: locust -f locustfile.py --host=http://localhost
Truy cập: http://localhost:8089
"""

from locust import User, task, between, events
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
import uuid
import random
import time

# Global connection pool
cluster = None
session = None
user_ids = []
conversation_ids = []

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Khởi tạo connection khi Locust start"""
    global cluster, session, user_ids, conversation_ids
    
    cluster = Cluster(['127.0.0.1'], port=9042)
    session = cluster.connect('realtime_chat_app')
    
    # Prepare statements
    session.default_timeout = 30.0
    
    # Load sample data
    users = session.execute("SELECT user_id FROM users_by_id LIMIT 100")
    user_ids = [row.user_id for row in users]
    
    convos = session.execute("SELECT conversation_id FROM conversations_by_user LIMIT 500")
    conversation_ids = list(set([row.conversation_id for row in convos]))[:100]
    
    print(f"✅ Loaded {len(user_ids)} users, {len(conversation_ids)} conversations")

class CassandraUser(User):
    """Mô phỏng 1 user sử dụng chat app"""
    
    # Thời gian đợi giữa các tasks (1-3 giây)
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
    
    @task(3)  # Weight = 3 (chạy nhiều hơn)
    def send_message(self):
        """Task: Gửi 1 tin nhắn"""
        conversation_id = random.choice(conversation_ids)
        sender_id = random.choice(user_ids)
        
        query = """
        INSERT INTO messages_by_conversation 
        (conversation_id, message_id, sender_id, sender_username, text_content, attachments)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        start_time = time.time()
        try:
            self.session.execute(
                query,
                (conversation_id, uuid.uuid1(), sender_id, "locust_user", 
                 "Load test message", [])
            )
            # Báo cáo thành công
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="send_message",
                response_time=total_time,
                response_length=0,
                exception=None,
                context={}
            )
        except Exception as e:
            # Báo cáo lỗi
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="send_message",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
    
    @task(5)  # Weight = 5 (chạy nhiều nhất)
    def read_messages(self):
        """Task: Đọc tin nhắn"""
        conversation_id = random.choice(conversation_ids)
        
        query = """
        SELECT sender_username, text_content, attachments
        FROM messages_by_conversation
        WHERE conversation_id = %s
        LIMIT 50
        """
        
        start_time = time.time()
        try:
            result = list(self.session.execute(query, (conversation_id,)))
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="read_messages",
                response_time=total_time,
                response_length=len(result),
                exception=None,
                context={}
            )
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="read_messages",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
    
    @task(2)  # Weight = 2
    def read_conversations(self):
        """Task: Lấy danh sách hội thoại"""
        user_id = random.choice(user_ids)
        
        query = """
        SELECT conversation_id, conversation_name, last_message_text
        FROM conversations_by_user
        WHERE user_id = %s
        LIMIT 20
        """
        
        start_time = time.time()
        try:
            result = list(self.session.execute(query, (user_id,)))
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="read_conversations",
                response_time=total_time,
                response_length=len(result),
                exception=None,
                context={}
            )
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="CQL",
                name="read_conversations",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )

@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Đóng connection khi Locust stop"""
    global cluster
    if cluster:
        cluster.shutdown()
        print("✅ Closed Cassandra connection")