-- ====================================================================
-- Step 1: Định nghĩa KEYSPACE
-- ====================================================================
-- Keyspace được tạo với SimpleStrategy và replication_factor = 3,
-- phù hợp cho một cụm Cassandra có 3 node trong một trung tâm dữ liệu.
-- DURABLE_WRITES = true là mặc định và đảm bảo dữ liệu được ghi vào commit log.
-- ====================================================================

CREATE KEYSPACE IF NOT EXISTS realtime_chat_app
WITH REPLICATION = {
    'class': 'SimpleStrategy',
    'replication_factor': 3
} AND DURABLE_WRITES = true;

-- Sử dụng keyspace vừa tạo cho các lệnh tiếp theo
USE realtime_chat_app;

-- ====================================================================
-- Step 2: Định nghĩa tất cả các TABLE
-- ====================================================================

-- --------------------------------------------------------------------
-- Bảng 1: users_by_id
-- Mục đích: Lưu trữ thông tin gốc của người dùng.
-- Truy vấn: Lấy thông tin chi tiết của người dùng bằng ID.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users_by_id (
    user_id uuid PRIMARY KEY,
    username text,
    password text, -- Luôn lưu trữ mật khẩu đã được băm (hashed)
    avatar text,
    is_online boolean,
    created_at timestamp
);

-- --------------------------------------------------------------------
-- Bảng 2: users_by_username
-- Mục đích: Tra cứu user_id từ username để đăng nhập hoặc kiểm tra tồn tại.
-- Truy vấn: Tìm một người dùng bằng username chính xác.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users_by_username (
    username text PRIMARY KEY,
    user_id uuid
);

-- --------------------------------------------------------------------
-- Bảng 3: friends_by_user
-- Mục đích: Lấy danh sách bạn bè của một người dùng.
-- Truy vấn: Tải danh sách bạn bè của user_id = ?, sắp xếp theo tên.
-- Ghi chú: Dữ liệu được phi chuẩn hóa (friend_username, friend_avatar) để đọc nhanh.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS friends_by_user (
    user_id uuid,
    friend_username text,
    friend_id uuid,
    friend_avatar text,
    since timestamp,
    PRIMARY KEY ((user_id), friend_username)
) WITH CLUSTERING ORDER BY (friend_username ASC);

-- --------------------------------------------------------------------
-- Bảng 4: friend_requests_by_recipient
-- Mục đích: Hiển thị các lời mời kết bạn mà người dùng nhận được.
-- Truy vấn: Tải danh sách lời mời cho recipient_id = ?, sắp xếp theo thời gian mới nhất.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS friend_requests_by_recipient (
    recipient_id uuid,
    created_at timeuuid, -- Dùng timeuuid để đảm bảo duy nhất và có thể sắp xếp
    requester_id uuid,
    requester_username text, -- Phi chuẩn hóa
    status text, -- vd: 'pending'
    PRIMARY KEY ((recipient_id), created_at)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- --------------------------------------------------------------------
-- Bảng 5: conversations_by_user
-- Mục đích: Hiển thị danh sách hội thoại cho người dùng.
-- Truy vấn: Tải danh sách hội thoại của user_id = ?, sắp xếp theo tin nhắn cuối cùng.
-- Ghi chú: Bảng này được phi chuẩn hóa rất nhiều để tối ưu cho việc tải màn hình chính.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations_by_user (
    user_id uuid,
    last_message_timestamp timestamp,
    conversation_id uuid,
    conversation_name text,
    conversation_avatar text,
    conversation_type text, -- 'DIRECT' hoặc 'GROUP'
    last_message_text text,
    last_message_sender text,
    unread_count int,
    PRIMARY KEY ((user_id), last_message_timestamp)
) WITH CLUSTERING ORDER BY (last_message_timestamp DESC);

-- --------------------------------------------------------------------
-- Bảng 6: members_by_conversation
-- Mục đích: Quản lý thành viên trong một hội thoại nhóm.
-- Truy vấn: Lấy danh sách thành viên của conversation_id = ?.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS members_by_conversation (
    conversation_id uuid,
    user_id uuid,
    username text, -- Phi chuẩn hóa
    role text,     -- vd: 'admin' hoặc 'member'
    joined_at timestamp,
    PRIMARY KEY ((conversation_id), user_id)
);

-- --------------------------------------------------------------------
-- Bảng 7: messages_by_conversation
-- Mục đích: Lưu trữ toàn bộ tin nhắn của các hội thoại.
-- Truy vấn: Tải các tin nhắn trong conversation_id = ?, sắp xếp theo thời gian mới nhất (để phân trang).
-- Ghi chú: Đây là bảng sẽ có lượng ghi rất lớn.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages_by_conversation (
    conversation_id uuid,
    message_id timeuuid, -- Dùng timeuuid làm clustering key là lựa chọn tốt nhất
    sender_id uuid,
    sender_username text, -- Phi chuẩn hóa
    text_content text,
    attachments list<text>, -- Danh sách các URL file đính kèm
    PRIMARY KEY ((conversation_id), message_id)
) WITH CLUSTERING ORDER BY (message_id DESC);

-- --------------------------------------------------------------------
-- Bảng 8: blocked_users
-- Mục đích: Quản lý việc người dùng chặn lẫn nhau.
-- Truy vấn: Kiểm tra xem user_id = ? có chặn blocked_user_id = ? không.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blocked_users (
    user_id uuid,         -- Người thực hiện việc chặn
    blocked_user_id uuid, -- Người bị chặn
    blocked_at timestamp,
    PRIMARY KEY ((user_id), blocked_user_id)
);

-- ====================================================================
-- KẾT THÚC SCHEMA
-- ====================================================================