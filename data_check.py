"""
Script kiểm tra dữ liệu trong Cassandra
"""
from cassandra.cluster import Cluster

def check_data():
    """Kiểm tra số lượng dữ liệu trong từng bảng"""
    
    # Kết nối
    cluster = Cluster(['127.0.0.1'], port=9042)
    session = cluster.connect('realtime_chat_app')
    
    print("\n" + "="*60)
    print("📊 KIỂM TRA DỮ LIỆU TRONG DATABASE")
    print("="*60 + "\n")
    
    # Kiểm tra Users
    print("👤 USERS:")
    try:
        # Đếm users_by_id
        count_query = "SELECT COUNT(*) FROM users_by_id"
        result = session.execute(count_query)
        count = result.one().count
        print(f"   - Tổng users (users_by_id): {count:,}")
        
        # Lấy mẫu 5 users
        sample_query = "SELECT username, is_online, created_at FROM users_by_id LIMIT 5"
        rows = session.execute(sample_query)
        print(f"   - Mẫu 5 users:")
        for row in rows:
            print(f"      • {row.username} (Online: {row.is_online}) - Created: {row.created_at}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    print()
    
    # Kiểm tra Conversations
    print("💬 CONVERSATIONS:")
    try:
        # Đếm conversations_by_user
        count_query = "SELECT COUNT(*) FROM conversations_by_user"
        result = session.execute(count_query)
        count = result.one().count
        print(f"   - Tổng conversations_by_user entries: {count:,}")
        
        # Lấy mẫu 5 conversations
        sample_query = """
        SELECT conversation_name, conversation_type, last_message_text 
        FROM conversations_by_user LIMIT 5
        """
        rows = session.execute(sample_query)
        print(f"   - Mẫu 5 conversations:")
        for row in rows:
            print(f"      • {row.conversation_name} ({row.conversation_type})")
            print(f"        Last msg: {row.last_message_text}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    print()
    
    # Kiểm tra Messages
    print("📨 MESSAGES:")
    try:
        # Đếm messages (chậm với bảng lớn, nên dùng LIMIT)
        # Lưu ý: COUNT(*) trên bảng lớn rất chậm trong Cassandra
        sample_query = "SELECT COUNT(*) FROM messages_by_conversation LIMIT 100000"
        result = session.execute(sample_query)
        count = result.one().count
        print(f"   - Số messages (mẫu 100k đầu): {count:,}")
        
        # Lấy mẫu messages
        sample_query = """
        SELECT sender_username, text_content, attachments 
        FROM messages_by_conversation LIMIT 10
        """
        rows = session.execute(sample_query)
        print(f"   - Mẫu 10 messages:")
        for row in rows:
            attachments = f" [+{len(row.attachments)} files]" if row.attachments else ""
            content = row.text_content[:50] + "..." if len(row.text_content) > 50 else row.text_content
            print(f"      • {row.sender_username}: {content}{attachments}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    print()
    
    # Kiểm tra Members
    print("👥 MEMBERS:")
    try:
        count_query = "SELECT COUNT(*) FROM members_by_conversation LIMIT 100000"
        result = session.execute(count_query)
        count = result.one().count
        print(f"   - Tổng members entries: {count:,}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    print("\n" + "="*60)
    print("✅ HOÀN THÀNH KIỂM TRA")
    print("="*60 + "\n")
    
    # Đóng kết nối
    cluster.shutdown()

if __name__ == "__main__":
    check_data()