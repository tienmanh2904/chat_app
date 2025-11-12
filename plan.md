# **Kế Hoạch 7 Ngày: Benchmark Cassandra cho Ứng Dụng Chat**

**Mục tiêu:** Chứng minh sức mạnh (khả năng mở rộng, thông lượng ghi/đọc cao) của Cassandra thông qua việc thiết kế CSDL và benchmark các truy vấn cốt lõi của một ứng dụng chat.

**Thành viên nhóm (5 người):**

* **Team A (2 người): Data Model & Data Gen** (Thiết kế mô hình dữ liệu & Tạo dữ liệu giả)  
* **Team B (2 người): Benchmark & Scripts** (Xây dựng kịch bản & Viết mã benchmark)  
* **Team C (1 người): DevOps & Quản lý** (Triển khai CSDL & Điều phối chung)

## **Giai đoạn 1: Thiết Kế & Chuẩn Bị (Ngày 1 \- 2\)**

### **Ngày 1: Hoàn thiện Thiết kế & Môi trường**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **1.1: Phân tích & Chốt Data Model** | Team A (2) | Dựa trên file Google Sheet (tab "Query"), hoàn thiện thiết kế các bảng (tables) trên Cassandra. **Quan trọng:** Phải là thiết kế hướng-truy-vấn (query-driven design). | \- File CQL (schema) định nghĩa tất cả keyspaces và tables. \- Ví dụ: messages\_by\_conversation, conversations\_by\_user. |
| **1.2: Thiết lập Môi trường CSDL** | Team C (1) | \- Cài đặt một cụm (cluster) Cassandra. **Khuyến nghị:** Dùng Docker Compose để nhanh chóng tạo 3-5 node. \- Áp dụng file schema (từ Task 1.1) để tạo bảng. | \- Cụm Cassandra đang chạy, sẵn sàng kết nối. |
| **1.3: Định nghĩa Kịch bản Benchmark** | Team B (2) | \- Chọn ra 3-5 truy vấn "nặng" và quan trọng nhất từ file Google Sheet để benchmark. \- **Gợi ý:** 1\. Gửi tin nhắn (Write-heavy), 2\. Tải 50 tin nhắn gần nhất (Read-heavy), 3\. Tải danh sách hội thoại của User (Read-heavy). \- Quyết định các chỉ số cần đo: Thông lượng (Ops/sec) và Độ trễ (p95, p99 Latency). | \- Tài liệu mô tả rõ 3-5 kịch bản benchmark. |

### **Ngày 2: Hoàn thiện Công cụ**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **2.1: Bắt đầu Viết Script Tạo Dữ Liệu** | Team A (2) | \- Bắt đầu viết script (Python/Java/Go) để tạo dữ liệu giả (fake data) một cách hiệu quả. \- Dữ liệu cần thực tế: users, conversations, messages (có timestamp). \- **Mục tiêu:** Phải có khả năng tạo *hàng triệu* (hoặc tỉ) bản ghi. | \- Script tạo dữ liệu (chưa chạy, chỉ mới hoàn thiện code). |
| **2.2: Chọn Tool & Viết Script Benchmark** | Team B (2) | \- Quyết định công cụ benchmark. **Khuyến nghị:** Dùng cassandra-stress (công cụ có sẵn) hoặc tự viết script (ví dụ: dùng Python asyncio \+ cassandra-driver). Tự viết sẽ linh hoạt hơn. \- Viết code để thực thi song song các kịch bản đã chọn (Task 1.3). | \- Mã nguồn (source code) cho các script benchmark. |
| **2.3: "Sanity Check" Môi trường** | Team C (1) | \- Hỗ trợ Team B kết nối thử vào cluster. \- Theo dõi (monitor) cơ bản cluster Cassandra (ví dụ: nodetool status). | \- Xác nhận tất cả thành viên có thể kết nối tới CSDL. |

## **Giai đoạn 2: Tạo Dữ Liệu & Chạy Benchmark (Ngày 3 \- 5\)**

### **Ngày 3: "Nạp" Dữ Liệu (Data Loading)**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **3.1: Chạy Script Data Gen** | Team A (2) | \- Chạy script đã viết (Task 2.1) để "bơm" một lượng lớn dữ liệu vào CSDL. \- **Đây là task tốn thời gian, có thể chạy ngầm.** \- **Mục tiêu:** Ít nhất 1 triệu users, 10 triệu conversations, 100 triệu messages. (Càng nhiều càng tốt). | \- CSDL Cassandra chứa đầy dữ liệu. |
| **3.2: Tinh chỉnh Script Benchmark** | Team B (2) | \- Chạy thử benchmark với lượng dữ liệu nhỏ để kiểm tra script. \- Đảm bảo script có thể ghi lại kết quả (latency, throughput) vào file log/CSV. | \- Script benchmark đã được kiểm thử và sẵn sàng. |
| **3.3: Theo dõi Cụm (Cluster Monitoring)** | Team C (1) | \- Theo dõi cluster trong quá trình "bơm" dữ liệu. \- Đảm bảo không node nào bị "chết" (down). | \- Cụm CSDL ổn định. |

### **Ngày 4: Chạy Benchmark (Lần 1\)**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **4.1: Thực thi Benchmark Kịch bản 1 & 2** | Team B (2) | \- Chạy benchmark cho 2 kịch bản đầu (ví dụ: Gửi tin nhắn, Tải tin nhắn). \- Chạy với các mức độ tải khác nhau (ví dụ: 1000, 5000, 10000 requests/giây). | \- File kết quả (CSV/logs) cho 2 kịch bản. |
| **4.2: Phân tích kết quả (Sơ bộ)** | Team A (2) | \- Bắt đầu phân tích kết quả thô từ Team B. \- Tạo các biểu đồ đầu tiên (ví dụ: Thông lượng (Ops/sec) vs Độ trễ (Latency)). | \- Vài biểu đồ sơ bộ. |
| **4.3: Theo dõi & Tinh chỉnh (Nếu cần)** | Team C (1) | \- Theo dõi sát sao cluster khi đang bị "stress test". \- Ghi lại các thông số của server (CPU, Load, Disk I/O) nếu có thể. | \- Ghi chú về tình trạng cluster khi chịu tải. |

### **Ngày 5: Chạy Benchmark (Lần 2\) & Phân tích**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **5.1: Thực thi Kịch bản còn lại** | Team B (2) | \- Chạy benchmark cho các kịch bản còn lại. \- Thử nghiệm "thêm node" (nếu có thể): Thêm 1-2 node vào cluster (Task 1.2 nếu dùng Docker thì rất dễ) và chạy lại benchmark để so sánh. | \- Toàn bộ file kết quả benchmark thô. |
| **5.2: Hoàn thiện Phân tích & Trực quan hóa** | Team A (2) | \- Tổng hợp tất cả kết quả. \- Tạo bộ biểu đồ hoàn chỉnh (dùng Excel, Google Sheets, hoặc Matplotlib) để "kể chuyện". \- **Câu chuyện cần kể:** "Khi tải tăng, Cassandra vẫn giữ độ trễ ổn định", "Khi thêm node, thông lượng tăng tuyến tính". | \- Bộ biểu đồ (charts) hoàn chỉnh. |

## **Giai đoạn 3: Tổng Hợp & Báo Cáo (Ngày 6 \- 7\)**

### **Ngày 6: Chuẩn bị Báo cáo**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **6.1: Viết Báo cáo & Làm Slides** | Cả nhóm (5) | \- **Team A (Data):** Chuẩn bị phần "Tại sao chọn Cassandra" và "Thiết kế Data Model". \- **Team B (Benchmark):** Chuẩn bị phần "Kịch bản Benchmark" và trình bày các biểu đồ kết quả. \- **Team C (DevOps):** Chuẩn bị phần "Kiến trúc hệ thống" và "Kết quả khi Scale (thêm node)". | \- Bản nháp (draft) của slide thuyết trình. |
| **6.2: Tổng hợp Code** | Team C (1) | \- Gom tất cả code (Schema CQL, Script Data Gen, Script Benchmark) vào một thư mục/repository. | \- Mã nguồn dự án đã được sắp xếp. |

### **Ngày 7: Finalize & Diễn tập**

| Task | Người phụ trách | Chi tiết công việc | Kết quả (Deliverable) |
| :---- | :---- | :---- | :---- |
| **7.1: Hoàn thiện Slide & Báo cáo** | Cả nhóm (5) | \- Rà soát lại nội dung, câu chữ, và các biểu đồ. \- Đảm bảo các con số benchmark "biết nói" và thể hiện rõ sức mạnh của Cassandra. | \- Bộ slide và báo cáo cuối cùng. |
| **7.2: Thuyết trình thử (Internal)** | Cả nhóm (5) | \- Cả nhóm trình bày thử cho nhau nghe. \- Góp ý và chỉnh sửa lần cuối. | \- Sẵn sàng cho buổi bảo vệ dự án. |

