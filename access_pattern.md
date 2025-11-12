### 1. Xác thực (Authentication)

*   **Query:** Đăng ký tài khoản (kiểm tra username tồn tại).
    *   **Access Pattern:** `SELECT user_id FROM users_by_username WHERE username = ?;`
*   **Query:** Tạo tài khoản mới.
    *   **Access Pattern:** `INSERT INTO users (user_id, username, password, avatar, isOnline) VALUES (?, ?, ?, ?, ?);` và `INSERT INTO users_by_username (username, user_id) VALUES (?, ?);`
*   **Query:** Đăng nhập.
    *   **Access Pattern:** `SELECT * FROM users_by_username WHERE username = ?;` sau đó lấy `user_id` để truy vấn vào bảng `users`.

### 2. Người dùng (User)

*   **Query:** Lấy thông tin hồ sơ cá nhân.
    *   **Access Pattern:** `SELECT * FROM users WHERE user_id = ?;`
*   **Query:** Cập nhật hồ sơ (ví dụ: avatar).
    *   **Access Pattern:** `UPDATE users SET avatar = ? WHERE user_id = ?;`
*   **Query:** Tìm kiếm người dùng theo username chính xác.
    *   **Access Pattern:** `SELECT * FROM users_by_username WHERE username = ?;`

### 3. Trạng thái (Presence)

*   **Query:** Cập nhật trạng thái online/offline của người dùng.
    *   **Access Pattern:** `UPDATE users SET isOnline = ? WHERE user_id = ?;`

### 4. Lời mời kết bạn (Friend Request)

*   **Query:** Gửi lời mời kết bạn.
    *   **Access Pattern:** `INSERT INTO friend_requests (request_id, requester_id, recipient_id, status, createdAt) VALUES (uuid(), ?, ?, 'pending', toTimestamp(now()));`
*   **Query:** Xem danh sách lời mời đã gửi.
    *   **Access Pattern:** `SELECT * FROM friend_requests_by_requester WHERE requester_id = ?;`
*   **Query:** Xem danh sách lời mời nhận được.
    *   **Access Pattern:** `SELECT * FROM friend_requests_by_recipient WHERE recipient_id = ?;`
*   **Query:** Chấp nhận/Từ chối lời mời.
    *   **Access Pattern:**
        *   Khi chấp nhận:
            1.  `INSERT INTO friends_by_user (user_id, friend_id, since) VALUES (?, ?, toTimestamp(now()));` (Thực hiện cho cả hai người dùng).
            2.  `DELETE FROM friend_requests_by_recipient WHERE recipient_id = ? AND createdAt = ?;`
        *   Khi từ chối:
            1.  `DELETE FROM friend_requests_by_recipient WHERE recipient_id = ? AND createdAt = ?;`

### 5. Bạn bè (Friend)

*   **Query:** Tải danh sách bạn bè của một người dùng.
    *   **Access Pattern:** `SELECT * FROM friends_by_user WHERE user_id = ?;`
*   **Query:** Hủy kết bạn.
    *   **Access Pattern:** `DELETE FROM friends_by_user WHERE user_id = ? AND friend_id = ?;` (Thực hiện cho cả hai người dùng).

### 6. Hội thoại (Conversation)

*   **Query:** Tải danh sách hội thoại của một người dùng.
    *   **Access Pattern:** `SELECT * FROM conversations_by_user WHERE user_id = ?;`
*   **Query:** Tạo hội thoại 1-1.
    *   **Access Pattern:**
        1.  Tạo một `conversation_id` mới.
        2.  `INSERT INTO conversations (conversation_id, type, createdAt) VALUES (?, 'DIRECT', toTimestamp(now()));`
        3.  `INSERT INTO conversations_by_user (user_id, conversation_id, type) VALUES (?, ?, 'DIRECT');` (Thực hiện cho cả hai người dùng).
*   **Query:** Tạo nhóm (group).
    *   **Access Pattern:**
        1.  `INSERT INTO conversations (conversation_id, type, name, admin_id, createdAt) VALUES (?, 'GROUP', ?, ?, toTimestamp(now()));`
        2.  Với mỗi thành viên, bao gồm cả admin: `INSERT INTO conversations_by_user (user_id, conversation_id, type, name) VALUES (?, ?, 'GROUP', ?);`
*   **Query:** Thêm/Xóa thành viên khỏi nhóm.
    *   **Access Pattern:**
        *   Thêm: `INSERT INTO conversations_by_user (user_id, conversation_id, type, name) VALUES (?, ?, 'GROUP', ?);`
        *   Xóa: `DELETE FROM conversations_by_user WHERE user_id = ? AND conversation_id = ?;`
*   **Query:** Rời nhóm.
    *   **Access Pattern:** `DELETE FROM conversations_by_user WHERE user_id = ? AND conversation_id = ?;`

### 7. Tin nhắn (Message)

*   **Query:** Tải 50 tin nhắn mới nhất trong một hội thoại.
    *   **Access Pattern:** `SELECT * FROM messages_by_conversation WHERE conversation_id = ? ORDER BY message_id DESC LIMIT 50;` (Giả định `message_id` là `TIMEUUID` để có thể sắp xếp theo thời gian).
*   **Query:** Gửi tin nhắn.
    *   **Access Pattern:** `INSERT INTO messages_by_conversation (conversation_id, message_id, user_id, text, createdAt) VALUES (?, now(), ?, ?, toTimestamp(now()));`
*   **Query:** Đánh dấu đã đọc tin nhắn cuối cùng trong hội thoại.
    *   **Access Pattern:** `UPDATE conversations_by_user SET last_read_message_id = ? WHERE user_id = ? AND conversation_id = ?;`
*   **Query:** Đếm số tin nhắn chưa đọc (thường được xử lý ở client hoặc dùng một cơ chế khác như counter table nếu cần độ chính xác cao).
    *   **Access Pattern:** `SELECT count(*) FROM messages_by_conversation WHERE conversation_id = ? AND message_id > ?;` (Với `?` là `last_read_message_id`. **Lưu ý:** Truy vấn này có thể không hiệu quả với lượng dữ liệu lớn).

### 8. Tìm kiếm (Search)

*   **Query:** Tìm kiếm hội thoại theo tên.
    *   **Access Pattern:** Trong Cassandra, việc tìm kiếm theo một phần của chuỗi (LIKE '%...%') là không hiệu quả. Cần tích hợp với một công cụ tìm kiếm chuyên dụng như Elasticsearch hoặc Solr.
*   **Query:** Tìm kiếm tin nhắn trong lịch sử.
    *   **Access Pattern:** Tương tự như tìm kiếm hội thoại, đây là một tác vụ yêu cầu full-text search và nên được xử lý bởi một hệ thống bên ngoài được tích hợp với Cassandra.

### 9. Cài đặt/Quyền riêng tư (Settings/Privacy)

*   **Query:** Chặn một người dùng.
    *   **Access Pattern:** `INSERT INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?);`
*   **Query:** Kiểm tra một người dùng có bị chặn hay không.
    *   **Access Pattern:** `SELECT blocked_user_id FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?;`

Lưu ý rằng các bảng như `users_by_username`, `friend_requests_by_requester`, `conversations_by_user` là các bảng được tạo ra để phục vụ riêng cho các mẫu truy cập cụ thể, đây là một thực hành phổ biến trong Cassandra để đảm bảo hiệu suất đọc tối ưu.