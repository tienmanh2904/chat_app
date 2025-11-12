"""
Data Generator Script for Cassandra Chat App Benchmark
Tạo dữ liệu giả cho:
- Users (1 triệu)
- Conversations (10 triệu)
- Messages (100 triệu)
"""

import asyncio
import uuid
import random
from datetime import datetime, timedelta
from cassandra.cluster import Cluster, NoHostAvailable
from cassandra.query import SimpleStatement
from cassandra.util import uuid_from_time
from faker import Faker
import time

# ============================================================================
# CONFIGURATION
# ============================================================================
CONTACT_POINTS = ['127.0.0.1']
PORT = 9042
KEYSPACE = 'realtime_chat_app'

# Số lượng dữ liệu cần tạo
NUM_USERS = 1000          # Test với 1000 users trước
NUM_CONVERSATIONS = 5000  # 5000 conversations
NUM_MESSAGES = 50000      # 50000 messages

# Kích thước batch để tránh quá tải bộ nhớ
BATCH_SIZE = 1000

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
def connect_to_cassandra():
    """Kết nối đến Cassandra cluster"""
    try:
        cluster = Cluster(CONTACT_POINTS, port=PORT)
        session = cluster.connect(KEYSPACE)
        print(f"✅ Kết nối đến Cassandra thành công! (Keyspace: {KEYSPACE})")
        return session, cluster
    except NoHostAvailable as e:
        print(f"❌ Lỗi kết nối: Không thể kết nối đến {CONTACT_POINTS}:{PORT}")
        print(f"   Chi tiết: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
        return None, None

# ============================================================================
# DATA MODEL FUNCTIONS
# ============================================================================
def create_fake_user(faker_instance):
    """
    Tạo 1 user giả
    Returns: dict với user_id, username, password, avatar, is_online, created_at
    """
    return {
        'user_id': uuid.uuid4(),
        'username': faker_instance.user_name() + str(random.randint(1, 9999)),  # Đảm bảo unique
        'password': 'hashed_password_123',  # Mật khẩu giả đã băm
        'avatar': faker_instance.image_url(),
        'is_online': random.choice([True, False]),
        'created_at': datetime.now() - timedelta(days=random.randint(0, 365))
    }

def create_fake_conversation(user_list, faker_instance, is_group=False):
    """
    Tạo 1 conversation giả
    Returns: dict với conversation_id, type, name, members
    """
    if is_group:
        # Group chat: 3-10 members
        num_members = random.randint(3, min(10, len(user_list)))
        members = random.sample(user_list, num_members)
        conv_type = 'GROUP'
        conv_name = f"Group: {faker_instance.catch_phrase()}"
    else:
        # Direct chat: 2 members
        members = random.sample(user_list, 2)
        conv_type = 'DIRECT'
        conv_name = f"{members[0]['username']} & {members[1]['username']}"
    
    return {
        'conversation_id': uuid.uuid4(),
        'conversation_type': conv_type,
        'conversation_name': conv_name,
        'conversation_avatar': faker_instance.image_url() if is_group else None,
        'members': members,
        'created_at': datetime.now() - timedelta(days=random.randint(0, 90))
    }

def create_fake_message(conversation, faker_instance):
    """
    Tạo 1 message giả trong conversation
    Returns: dict với message_id, conversation_id, sender, content, timestamp
    """
    sender = random.choice(conversation['members'])
    timestamp = datetime.now() - timedelta(minutes=random.randint(0, 10080))  # Trong 1 tuần
    
    # Tạo attachments ngẫu nhiên (20% tin nhắn có file đính kèm)
    attachments = []
    if random.random() < 0.2:
        num_attachments = random.randint(1, 3)
        attachments = [faker_instance.image_url() for _ in range(num_attachments)]
    
    return {
        'message_id': uuid_from_time(timestamp),  # timeuuid based on timestamp
        'conversation_id': conversation['conversation_id'],
        'sender_id': sender['user_id'],
        'sender_username': sender['username'],
        'text_content': faker_instance.sentence(nb_words=random.randint(3, 20)),
        'attachments': attachments,
        'timestamp': timestamp
    }

# ============================================================================
# ASYNC INSERT FUNCTIONS
# ============================================================================
async def insert_user_async(session, user_data):
    """INSERT 1 user vào 2 bảng: users_by_id và users_by_username"""
    query_by_id = """
    INSERT INTO users_by_id (user_id, username, password, avatar, is_online, created_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    query_by_username = """
    INSERT INTO users_by_username (username, user_id)
    VALUES (%s, %s)
    """
    
    loop = asyncio.get_event_loop()
    
    # Chạy song song 2 INSERTs
    futures = [
        session.execute_async(query_by_id, (
            user_data['user_id'], user_data['username'], user_data['password'],
            user_data['avatar'], user_data['is_online'], user_data['created_at']
        )),
        session.execute_async(query_by_username, (
            user_data['username'], user_data['user_id']
        ))
    ]
    
    for future in futures:
        await loop.run_in_executor(None, future.result)

async def insert_conversation_async(session, convo_data):
    """
    INSERT conversation và members vào:
    - conversations_by_user (cho mỗi member)
    - members_by_conversation
    """
    loop = asyncio.get_event_loop()
    futures = []
    
    # INSERT vào conversations_by_user cho mỗi member
    query_conv_by_user = """
    INSERT INTO conversations_by_user 
    (user_id, last_message_timestamp, conversation_id, conversation_name, 
     conversation_avatar, conversation_type, last_message_text, 
     last_message_sender, unread_count)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    for member in convo_data['members']:
        futures.append(session.execute_async(query_conv_by_user, (
            member['user_id'],
            convo_data['created_at'],
            convo_data['conversation_id'],
            convo_data['conversation_name'],
            convo_data['conversation_avatar'],
            convo_data['conversation_type'],
            'No messages yet',  # Placeholder
            None,
            0
        )))
    
    # INSERT vào members_by_conversation
    query_members = """
    INSERT INTO members_by_conversation 
    (conversation_id, user_id, username, role, joined_at)
    VALUES (%s, %s, %s, %s, %s)
    """
    
    for i, member in enumerate(convo_data['members']):
        role = 'admin' if i == 0 else 'member'  # First member là admin
        futures.append(session.execute_async(query_members, (
            convo_data['conversation_id'],
            member['user_id'],
            member['username'],
            role,
            convo_data['created_at']
        )))
    
    # Đợi tất cả hoàn thành
    for future in futures:
        await loop.run_in_executor(None, future.result)

async def insert_message_async(session, msg_data):
    """INSERT 1 message vào messages_by_conversation"""
    query = """
    INSERT INTO messages_by_conversation 
    (conversation_id, message_id, sender_id, sender_username, 
     text_content, attachments)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    future = session.execute_async(query, (
        msg_data['conversation_id'],
        msg_data['message_id'],
        msg_data['sender_id'],
        msg_data['sender_username'],
        msg_data['text_content'],
        msg_data['attachments']
    ))
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, future.result)

# ============================================================================
# DATA SEEDING LOGIC
# ============================================================================
async def seed_users(session, num_users):
    """Tạo và INSERT users vào database"""
    print(f"\n{'='*60}")
    print(f"📝 Bắt đầu tạo {num_users:,} users...")
    print(f"{'='*60}")
    
    fake = Faker()
    users = []
    tasks = []
    start_time = time.time()
    
    for i in range(num_users):
        user = create_fake_user(fake)
        users.append(user)
        tasks.append(insert_user_async(session, user))
        
        # Chạy batch để tránh quá tải bộ nhớ
        if len(tasks) >= BATCH_SIZE:
            await asyncio.gather(*tasks)
            tasks = []
            
            # Progress update
            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"   ✓ Đã tạo: {i+1:,}/{num_users:,} users ({rate:.0f} users/s)")
    
    # Chạy nốt phần còn lại
    if tasks:
        await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    print(f"✅ Hoàn thành tạo {num_users:,} users trong {total_time:.2f}s")
    print(f"   Tốc độ trung bình: {num_users/total_time:.0f} users/s\n")
    
    return users

async def seed_conversations(session, users, num_conversations):
    """Tạo và INSERT conversations vào database"""
    print(f"\n{'='*60}")
    print(f"💬 Bắt đầu tạo {num_conversations:,} conversations...")
    print(f"{'='*60}")
    
    fake = Faker()
    conversations = []
    tasks = []
    start_time = time.time()
    
    for i in range(num_conversations):
        # 70% direct chat, 30% group chat
        is_group = random.random() < 0.3
        convo = create_fake_conversation(users, fake, is_group)
        conversations.append(convo)
        tasks.append(insert_conversation_async(session, convo))
        
        # Chạy batch
        if len(tasks) >= BATCH_SIZE // 5:  # Nhỏ hơn vì conversation insert phức tạp hơn
            await asyncio.gather(*tasks)
            tasks = []
            
            # Progress update
            if (i + 1) % 500 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"   ✓ Đã tạo: {i+1:,}/{num_conversations:,} conversations ({rate:.0f} convos/s)")
    
    # Chạy nốt phần còn lại
    if tasks:
        await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    print(f"✅ Hoàn thành tạo {num_conversations:,} conversations trong {total_time:.2f}s")
    print(f"   Tốc độ trung bình: {num_conversations/total_time:.0f} convos/s\n")
    
    return conversations

async def seed_messages(session, conversations, num_messages):
    """Tạo và INSERT messages vào database"""
    print(f"\n{'='*60}")
    print(f"📨 Bắt đầu tạo {num_messages:,} messages...")
    print(f"{'='*60}")
    
    fake = Faker()
    tasks = []
    start_time = time.time()
    
    for i in range(num_messages):
        # Chọn conversation ngẫu nhiên
        convo = random.choice(conversations)
        msg = create_fake_message(convo, fake)
        tasks.append(insert_message_async(session, msg))
        
        # Chạy batch
        if len(tasks) >= BATCH_SIZE:
            await asyncio.gather(*tasks)
            tasks = []
            
            # Progress update
            if (i + 1) % 5000 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"   ✓ Đã tạo: {i+1:,}/{num_messages:,} messages ({rate:.0f} msgs/s)")
    
    # Chạy nốt phần còn lại
    if tasks:
        await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    print(f"✅ Hoàn thành tạo {num_messages:,} messages trong {total_time:.2f}s")
    print(f"   Tốc độ trung bình: {num_messages/total_time:.0f} msgs/s\n")

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================
async def main():
    """Main function để điều phối toàn bộ quá trình tạo dữ liệu"""
    print("\n" + "="*60)
    print("🚀 DATA GENERATOR - CASSANDRA CHAT APP BENCHMARK")
    print("="*60)
    
    # Kết nối
    session, cluster = connect_to_cassandra()
    if not session:
        print("❌ Không thể tiếp tục do lỗi kết nối.")
        return
    
    try:
        # Bước 1: Tạo Users
        users = await seed_users(session, NUM_USERS)
        
        # Bước 2: Tạo Conversations
        conversations = await seed_conversations(session, users, NUM_CONVERSATIONS)
        
        # Bước 3: Tạo Messages
        await seed_messages(session, conversations, NUM_MESSAGES)
        
        print("\n" + "="*60)
        print("🎉 HOÀN THÀNH TẠO DỮ LIỆU!")
        print("="*60)
        print(f"   📊 Tổng kết:")
        print(f"   - Users: {NUM_USERS:,}")
        print(f"   - Conversations: {NUM_CONVERSATIONS:,}")
        print(f"   - Messages: {NUM_MESSAGES:,}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình tạo dữ liệu: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Đóng kết nối
        print("🔌 Đóng kết nối...")
        cluster.shutdown()

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    # Chạy async main
    asyncio.run(main())