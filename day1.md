# **Kế Hoạch Chi Tiết Ngày 1: Setup & Thiết Kế**

Dưới đây là các bước chi tiết cho 3 task song song của Ngày 1, bao gồm các công cụ cần cài đặt và các bước thực thi.

## **Task 1.1: Phân tích & Chốt Data Model (Team A \- 2 người)**

**Mục tiêu:** Dịch các yêu cầu truy vấn (queries) từ Google Sheet thành một file schema.cql hoàn chỉnh cho Cassandra.

**Công cụ cần cài đặt/chuẩn bị:**

1. **Truy cập Google Sheet:** (Đã có) Link đến file "Chat app \- Query".  
2. **Trình soạn thảo mã (Code Editor):** Bất kỳ trình nào (VS Code, Sublime Text, Notepad++).  
3. **(Tùy chọn) Công cụ vẽ sơ đồ:** draw.io (hoặc Lucidchart) để phác thảo các luồng truy cập dữ liệu (access patterns) nếu cần.

**Các bước thực hiện chi tiết:**

1. **Họp phân tích (1 giờ):**  
   * Mở tab "Query" trong file Google Sheet.  
   * Đi qua *từng* truy vấn (query) và xác định rõ "Access Pattern" (Cách thức truy cập dữ liệu).  
   * **Ví dụ:**  
     * **Query:** "Tải 50 tin nhắn mới nhất trong 1 hội thoại".  
     * **Access Pattern:** SELECT \* FROM messages WHERE conversation\_id \= ? ORDER BY timestamp DESC LIMIT 50\.  
     * **Query:** "Tải danh sách hội thoại của 1 user".  
     * **Access Pattern:** SELECT \* FROM conversations\_by\_user WHERE user\_id \= ?.  
2. **Thiết kế Bảng (Tables) (2-3 giờ):**  
   * Với mỗi *access pattern* đã xác định, thiết kế một bảng (table) để phục vụ *chính xác* truy vấn đó. Đây là nguyên tắc vàng: **"Query-Driven Design"**.  
   * **Quan trọng:** Xác định PRIMARY KEY (bao gồm Partition Key và Clustering Columns) cho từng bảng.  
     * **Ví dụ 1 (Tải tin nhắn):** Bảng messages\_by\_conversation  
       * PRIMARY KEY ((conversation\_id), timestamp)  
       * WITH CLUSTERING ORDER BY (timestamp DESC)  
       * *Giải thích:* conversation\_id là Partition Key (gom tin nhắn theo phòng chat, giúp đọc nhanh). timestamp là Clustering Column (sắp xếp tin nhắn theo thời gian giảm dần).  
     * **Ví dụ 2 (Tải hội thoại):** Bảng conversations\_by\_user  
       * PRIMARY KEY ((user\_id), last\_message\_timestamp)  
       * WITH CLUSTERING ORDER BY (last\_message\_timestamp DESC)  
       * *Giải thích:* user\_id là Partition Key. last\_message\_timestamp dùng để sắp xếp các hội thoại (đưa hội thoại mới nhất lên đầu).  
   * **Chấp nhận Denormalization (Phi chuẩn hóa):** Dữ liệu sẽ bị lặp lại ở nhiều bảng để tối ưu cho việc đọc. Đừng cố gắng "JOIN" như SQL.  
3. **Viết Schema CQL (1-2 giờ):**  
   * Tạo một file tên schema.cql.  
   * **Bước 1:** Định nghĩa KEYSPACE. (Đặt tên, chọn replication\_factor \= 3 vì chúng ta sẽ chạy 3 node).  
     CREATE KEYSPACE IF NOT EXISTS chat\_app  
     WITH replication \= {  
       'class': 'SimpleStrategy',  
       'replication\_factor': 3  
     };  
     USE chat\_app;

   * **Bước 2:** Định nghĩa tất cả các TABLE (dựa trên Bước 2\) và TYPE (nếu cần, ví dụ: user\_info).  
4. **Review chéo (1 giờ):**  
   * Team A tự kiểm tra: "File schema.cql này có trả lời được *tất cả* các truy vấn trong Google Sheet không?".  
   * "Partition key có nguy cơ bị 'hot' (quá tải) không?".  
   * Gửi file schema.cql cho Team C.

## **Task 1.2: Thiết lập Môi trường CSDL (Team C \- 1 người)**

**Mục tiêu:** Cài đặt một cụm (cluster) Cassandra 3-node bằng Docker và áp dụng schema từ Team A.

**Công cụ cần cài đặt:**

1. **Docker Desktop:** Công cụ quan trọng nhất. Tải và cài đặt từ trang chủ của Docker (docker.com). Đảm bảo Docker đang chạy.  
2. **Terminal/PowerShell:** Có sẵn trên mọi HĐH.  
3. **(Tùy chọn) VS Code \+ Docker Extension:** Giúp quản lý container dễ dàng hơn.

**Các bước thực hiện chi tiết:**

1. **Tạo file docker-compose.yml (1 giờ):**  
   * Tạo một thư mục cho dự án (ví dụ: cassandra-benchmark).  
   * Trong thư mục đó, tạo file docker-compose.yml.  
   * *Nội dung file docker-compose.yml (để tạo 3 node):*  
     version: '3.8'  
     services:  
       cassandra-1:  
         image: cassandra:latest  
         container\_name: cassandra-1  
         hostname: cassandra-1  
         ports:  
           \- "9042:9042" \# Port cho client (Team B) kết nối  
         environment:  
           \- CASSANDRA\_SEEDS=cassandra-1  
           \- CASSANDRA\_CLUSTER\_NAME=ChatAppCluster  
           \- CASSANDRA\_DC=dc1  
           \- CASSANDRA\_RACK=rack1  
         networks:  
           \- cassandra-net

       cassandra-2:  
         image: cassandra:latest  
         container\_name: cassandra-2  
         hostname: cassandra-2  
         depends\_on:  
           \- cassandra-1  
         environment:  
           \- CASSANDRA\_SEEDS=cassandra-1  
           \- CASSANDRA\_CLUSTER\_NAME=ChatAppCluster  
           \- CASSANDRA\_DC=dc1  
           \- CASSANDRA\_RACK=rack1  
         networks:  
           \- cassandra-net

       cassandra-3:  
         image: cassandra:latest  
         container\_name: cassandra-3  
         hostname: cassandra-3  
         depends\_on:  
           \- cassandra-1  
         environment:  
           \- CASSANDRA\_SEEDS=cassandra-1  
           \- CASSANDRA\_CLUSTER\_NAME=ChatAppCluster  
           \- CASSANDRA\_DC=dc1  
           \- CASSANDRA\_RACK=rack1  
         networks:  
           \- cassandra-net

     networks:  
       cassandra-net:  
         driver: bridge

2. **Khởi chạy Cluster (30 phút):**  
   * Mở Terminal/PowerShell, cd vào thư mục chứa file docker-compose.yml.  
   * Chạy lệnh: docker-compose up \-d  
   * Chờ khoảng 2-3 phút cho các node khởi động và liên kết với nhau.  
3. **Kiểm tra Cluster (30 phút):**  
   * Chạy lệnh: docker exec \-it cassandra-1 nodetool status  
   * **Kết quả mong đợi:** Bạn thấy 3 node (cassandra-1, 2, 3\) và tất cả đều có trạng thái UN (Up/Normal). Nếu thấy UJ (Up/Joining) thì chờ thêm chút.  
4. **Áp dụng Schema (30 phút):**  
   * Nhận file schema.cql từ Team A. Đặt file này vào cùng thư mục.  
   * Chạy lệnh từ máy host (máy của bạn) để "đẩy" file schema vào container:  
     docker exec \-i cassandra-1 cqlsh \< schema.cql

   * *Xác minh (Tùy chọn):* docker exec \-it cassandra-1 cqlsh, sau đó USE chat\_app; và DESCRIBE TABLES; để xem các bảng đã được tạo.  
5. **Thông báo cho Nhóm (15 phút):**  
   * Báo cho Team A và B: "Cluster đã sẵn sàng\!"  
   * Địa chỉ kết nối (Contact Point): 127.0.0.1  
   * Port: 9042

## **Task 1.3: Định nghĩa Kịch bản Benchmark (Team B \- 2 người)**

**Mục tiêu:** Chốt 3-5 kịch bản (truy vấn) quan trọng nhất để "stress test" và các chỉ số cần đo.

**Công cụ cần cài đặt:**

1. **Python 3.x:** Tải và cài đặt từ python.org. (Khuyến nghị Python 3.9+).  
2. **Pip:** (Thường đi kèm Python). Cần để cài thư viện.  
3. **Thư viện Cassandra:** Mở Terminal/PowerShell, chạy:  
   pip install cassandra-driver

4. **(Tùy chọn) Thư viện asyncio:** Có sẵn trong Python. Team B nên tìm hiểu về asyncio và session.execute\_async() để thực hiện nhiều request song song.

**Các bước thực hiện chi tiết:**

1. **Họp chốt Kịch bản (1 giờ):**  
   * Rà soát file Google Sheet (tab "Query") và Kế hoạch (Task 1.3 Gợi ý).  
   * **Chốt 3 kịch bản quan trọng nhất:**  
     1. **Write (Gửi tin nhắn):** INSERT INTO messages\_by\_conversation (...) VALUES (...). Đây là kịch bản *write-heavy* cốt lõi.  
     2. **Read (Tải tin nhắn):** SELECT \* FROM messages\_by\_conversation WHERE conversation\_id \= ? LIMIT 50\. Đây là kịch bản *read-heavy* phổ biến nhất khi người dùng mở phòng chat.  
     3. **Read (Tải danh sách hội thoại):** SELECT \* FROM conversations\_by\_user WHERE user\_id \= ? LIMIT 30\. Đây là kịch bản "mở ứng dụng".  
2. **Định nghĩa Chỉ số (Metrics) (30 phút):**  
   * **Thông lượng (Throughput):** Ops/giây (Số lượng INSERT hoặc SELECT thành công mỗi giây).  
   * **Độ trễ (Latency):**  
     * **p95** (95% số request hoàn thành dưới X mili-giây).  
     * **p99** (99% số request hoàn thành dưới Y mili-giây).  
   * *Lý do:* Không dùng độ trễ trung bình (average) vì nó ẩn đi các giá trị ngoại lệ (outliers). p99 phản ánh trải nghiệm của 1% người dùng "xui xẻo" nhất, đây là chỉ số quan trọng.  
3. **Viết tài liệu mô tả (1-2 giờ):**  
   * Tạo một file benchmark\_scenarios.md.  
   * Mô tả rõ từng kịch bản (Tên, Câu lệnh CQL, Input, Output cần đo).  
   * Xác định mục tiêu tải (ví dụ: Thử nghiệm ở các mức 1000, 5000, 10000 requests/giây).  
4. **Viết Code "Kết nối Thử" (1-2 giờ):**  
   * Dựa trên thông tin từ Team C (Task 1.2), Team B bắt đầu viết các hàm cơ bản (Task 2.2) ngay trong Ngày 1\.  
   * Tạo file benchmark.py.  
   * Viết hàm connect\_to\_cassandra() và một hàm test\_connection() để đảm bảo kết nối thành công tới cluster Docker.  
     from cassandra.cluster import Cluster

     def connect\_to\_cassandra():  
         \# cluster \= Cluster(\['127.0.0.1'\], port=9042)  
         \# session \= cluster.connect('chat\_app')  
         \# return session  
         pass \# Viết code kết nối ở đây

     def test\_connection(session):  
         \# row \= session.execute("SELECT cluster\_name FROM system.local").one()  
         \# print(f"Connected to cluster: {row.cluster\_name}")  
         pass \# Viết code test ở đây

     if \_\_name\_\_ \== "\_\_main\_\_":  
         \# session \= connect\_to\_cassandra()  
         \# test\_connection(session)  
         print("Chuẩn bị script benchmark...")  
