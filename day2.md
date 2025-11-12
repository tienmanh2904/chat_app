# **Kế Hoạch Chi Tiết Ngày 2: Hoàn Thiện Công Cụ (Scripts)**

Ngày 2 là ngày "lập trình" chính để chuẩn bị 2 script quan trọng nhất: Tạo dữ liệu (Data Gen) và Đo lường (Benchmark).

## **Task 2.1: Viết Script Tạo Dữ Liệu (Team A \- 2 người)**

**Mục tiêu:** Hoàn thiện script (Python) có khả năng "bơm" hàng triệu/tỉ bản ghi (users, conversations, messages) vào CSDL Cassandra một cách nhanh chóng.

**Công cụ cần cài đặt/sử dụng:**

1. **Python 3.x:** (Đã cài từ Ngày 1).  
2. **Thư viện (Cài đặt qua pip):**  
   * cassandra-driver: Để kết nối và ghi dữ liệu.  
   * faker: Để tạo dữ liệu giả (tên, nội dung tin nhắn...) cho thực tế.  
   * *Lệnh cài đặt:* pip install cassandra-driver faker  
3. **Thư viện (Có sẵn trong Python):**  
   * uuid: Để tạo uuid và timeuuid (rất quan trọng cho message\_id).  
   * asyncio: Để thực hiện ghi dữ liệu song song (cực kỳ quan trọng để tăng tốc).  
   * random: Để chọn user, conversation ngẫu nhiên.

**Các bước thực hiện chi tiết:**

1. **Khởi tạo Script (data\_generator.py):**  
   * Import các thư viện cần thiết.  
   * Viết hàm connect\_to\_cassandra() (tương tự Task 1.3, Team B).  
2. **Viết các hàm tạo mô hình (Data Model Functions):**  
   * Viết các hàm nhỏ để tạo đối tượng giả, ví dụ:  
     * def create\_fake\_user(faker\_instance): (Trả về: user\_id, username, avatar\_url).  
     * def create\_fake\_conversation(user\_list): (Trả về: conversation\_id, title).  
     * def create\_fake\_message(sender\_id, content): (Trả về: message\_id (dùng uuid.uuid1()), sender\_id, content, timestamp).  
3. **Viết Logic "Bơm" Dữ Liệu (Data Seeding Logic):**  
   * Đây là phần quan trọng nhất. Phải sử dụng asyncio và session.execute\_async() để gửi hàng nghìn request cùng lúc.  
   * *Tránh:* Dùng vòng for và session.execute() đơn lẻ (sẽ mất hàng ngày).  
   * *Nên dùng:*  
     import asyncio  
     from cassandra.cluster import Cluster  
     from faker import Faker  
     import uuid

     \# ... (Hàm kết nối) ...

     async def insert\_user(session, user\_data):  
         query \= "INSERT INTO users (user\_id, username) VALUES (?, ?)"  
         await session.execute\_async(query, \[user\_data\['id'\], user\_data\['name'\]\])

     async def main():  
         session \= connect\_to\_cassandra('chat\_app')  
         fake \= Faker()

         tasks \= \[\]  
         num\_users\_to\_create \= 1000000 \# 1 triệu users

         print(f"Bắt đầu tạo {num\_users\_to\_create} users...")  
         for \_ in range(num\_users\_to\_create):  
             user \= {'id': uuid.uuid4(), 'name': fake.name()}  
             tasks.append(insert\_user(session, user))

             \# Chạy song song mỗi 1000 tasks để tránh quá tải bộ nhớ  
             if len(tasks) \> 1000:  
                 await asyncio.gather(\*tasks)  
                 tasks \= \[\]

         \# Chạy nốt phần còn lại  
         if tasks:  
             await asyncio.gather(\*tasks)

         print("Hoàn thành tạo users.")

     \# if \_\_name\_\_ \== "\_\_main\_\_":  
     \#    asyncio.run(main())

4. **Hoàn thiện Logic cho 3 bảng:**  
   * **Logic Users:** Chạy main() để tạo 1 triệu users. Lưu user\_id vào một danh sách (list) để dùng cho bước sau.  
   * **Logic Conversations:** Tạo 10 triệu conversations. Với mỗi conversation, chọn 2 user\_id ngẫu nhiên từ danh sách users. **Lưu ý:** Phải INSERT vào bảng conversations\_by\_user 2 lần (cho cả 2 user).  
   * **Logic Messages:** Tạo 100 triệu messages. Với mỗi message, chọn 1 conversation\_id ngẫu nhiên và 1 sender\_id (là 1 trong 2 user của convo đó). INSERT vào bảng messages\_by\_conversation.  
5. **Kết quả:** File data\_generator.py sẵn sàng để chạy (nhưng chưa chạy, chỉ hoàn thiện code).

## **Task 2.2: Viết Script Benchmark (Team B \- 2 người)**

**Mục tiêu:** Hoàn thiện script (Python) để thực thi 3 kịch bản đã chốt, chạy song song, và đo lường (Thông lượng, Độ trễ p95/p99).

**Công cụ cần cài đặt/sử dụng:**

1. **Python 3.x:** (Đã cài).  
2. **Thư viện (Cài đặt qua pip):**  
   * cassandra-driver: (Đã cài).  
   * numpy: Cách dễ nhất để tính toán percentile (p95/p99).  
   * *Lệnh cài đặt:* pip install numpy  
3. **Thư viện (Có sẵn trong Python):**  
   * asyncio: Để chạy benchmark song song.  
   * time: Dùng time.monotonic() để đo độ trễ chính xác.  
   * statistics: (Thay thế cho numpy nếu không muốn cài thêm).  
   * csv: Để ghi kết quả ra file.

**Các bước thực hiện chi tiết:**

1. **Khởi tạo Script (benchmark.py):**  
   * Hoàn thiện hàm connect\_to\_cassandra() (đã viết nháp ở Ngày 1).  
2. **Viết hàm thực thi Kịch bản (Worker Functions):**  
   * Viết 3 hàm async (mỗi hàm cho 1 kịch bản), nhận session và data làm đầu vào.  
   * Các hàm này phải đo thời gian và trả về latency.  
     import time  
     import uuid

     async def worker\_write\_message(session, convo\_id, user\_id):  
         query \= "INSERT INTO messages\_by\_conversation (conversation\_id, timestamp, message\_id, sender\_id, content) VALUES (?, now(), ?, ?, ?)"  
         msg\_id \= uuid.uuid1()

         start\_time \= time.monotonic()  
         try:  
             await session.execute\_async(query, \[convo\_id, msg\_id, user\_id, "Nội dung benchmark"\])  
             end\_time \= time.monotonic()  
             return (end\_time \- start\_time) \* 1000 \# Trả về mili-giây  
         except Exception as e:  
             return \-1 \# Đánh dấu lỗi

     \# (Viết hàm tương tự cho 2 kịch bản Read)  
     \# async def worker\_read\_messages(session, convo\_id): ...  
     \# async def worker\_read\_conversations(session, user\_id): ...

3. **Viết hàm Điều phối (Runner Function):**  
   * Hàm này nhận: kịch\_bản, concurrency (số lượng request chạy song song), duration (thời gian chạy).  
   * Sử dụng asyncio.gather() để chạy số lượng concurrency các worker cùng lúc.  
   * Liên tục chạy trong duration giây.  
   * Thu thập tất cả giá trị latency (ms) vào một danh sách lớn.  
4. **Viết hàm Báo cáo (Reporter Function):**  
   * Sau khi Runner chạy xong, hàm này nhận danh sách latencies.  
   * **Tính toán:**  
     * total\_requests: (Tổng số request thành công).  
     * throughput\_ops\_sec: (Tổng request / duration).  
     * p95\_latency: numpy.percentile(latencies, 95).  
     * p99\_latency: numpy.percentile(latencies, 99).  
     * median\_latency: numpy.percentile(latencies, 50).  
   * **Kết quả:** In ra console VÀ ghi vào file results.csv (để Team A có thể vẽ biểu đồ sau này).  
5. **Kết quả:** File benchmark.py sẵn sàng để chạy.

## **Task 2.3: "Sanity Check" Môi trường (Team C \- 1 người)**

**Mục tiêu:** Đảm bảo Team B kết nối được vào cluster và cluster ổn định.

**Công cụ cần sử dụng:**

1. **Docker Desktop:** (Đã cài).  
2. **Terminal / PowerShell:** (Có sẵn).  
3. **Công cụ giao tiếp:** (Chat/Call với Team B).

**Các bước thực hiện chi tiết:**

1. **Hỗ trợ kết nối (1-2 giờ):**  
   * Chủ động liên hệ Team B.  
   * Hỏi: "File benchmark.py (phần test connection từ Ngày 1\) của các bạn đã chạy được chưa?".  
   * **Nếu chưa:** Team C phải gỡ lỗi (troubleshoot):  
     * Chạy docker ps. Kiểm tra container cassandra-1 có đang chạy và map 9042:9042 không?  
     * Kiểm tra docker-compose.yml (Ngày 1\) xem có sai sót gì không.  
     * Đảm bảo Team B dùng đúng địa chỉ: 127.0.0.1 và port 9042\.  
2. **Chạy nodetool (Định kỳ / Khi Team B test):**  
   * Trong khi Team B chạy thử code kết nối, Team C mở Terminal và chạy lệnh:  
     docker exec \-it cassandra-1 nodetool status

   * **Kết quả mong đợi:** Cả 3 node đều UN (Up/Normal).  
3. **Kiểm tra Logs (Khi có lỗi):**  
   * Nếu Team B báo lỗi (ví dụ: "Connection refused"), Team C chạy:  
     docker logs cassandra-1

   * Đọc log để xem lý do (ví dụ: node bị OOM, disk đầy, v.v.).  
4. **(Tùy chọn) Cài đặt cqlsh bên ngoài (Host):**  
   * Để dễ dàng kiểm tra, Team C có thể cài cqlsh (client của Cassandra) trên máy thật của mình (thường đi kèm khi cài pip install cassandra-driver) và thử kết nối.  
   * Chạy: cqlsh 127.0.0.1 9042\. Nếu vào được là thành công.  
5. **Kết quả (Deliverable):** Xác nhận bằng lời/tin nhắn: "Team B đã kết nối thành công. Cluster ổn định."