# ⚡ LagoFast Event Auto Tool (Chia Sẻ Sự Kiện & Quay Thưởng)

Công cụ desktop Windows với giao diện đồ họa hiện đại (**CustomTkinter Dark Mode**), hỗ trợ xử lý đa luồng (multi-threading) cho danh sách tài khoản LagoFast: tự động chia sẻ sự kiện nhận lượt quay và tiến hành quay thưởng may mắn.

---

## 🚀 Các tính năng chính

1. **Quản lý danh sách tài khoản linh hoạt**:
   - Nhập dạng `email|login_credential`, `email----login_credential`, hoặc chỉ chuỗi `login_credential`.
   - Tool tự động truy vấn thông tin Email thực tế qua API nếu chỉ nhập token/credential.
   - Hỗ trợ dán trực tiếp danh sách (Paste Modal), nhập từ file `.txt` / `.csv`, xóa đã chọn, xóa toàn bộ.
   - Tự động lưu cache (`accounts_cache.json`) để không bị mất dữ liệu khi tắt app.

2. **Chức năng thao tác**:
   - **⚡ CHẠY TẤT CẢ (Auto All)**: Tự động chạy toàn bộ quy trình: Kiểm tra thông tin -> Chia sẻ sự kiện nhận lượt -> Quay sạch tất cả lượt còn lại -> Cập nhật quà trúng.
   - **📤 Chia sẻ sự kiện**: Gửi request chia sẻ nhận lượt quay (`/api/act/v1/change/get/{aid}/share_activity`).
   - **🎲 Quay thưởng (Lucky Draw)**: Quay thưởng may mắn (`/api/act/v1/luck/draw/{aid}`), hỗ trợ quay 1 lần hoặc quay hết lượt.
   - **🔍 Kiểm tra Info**: Cập nhật email, số lượt quay hiện tại và trạng thái chia sẻ.
   - **🛑 Dừng lại (Stop)**: Dừng an toàn tất cả luồng đang chạy bất kỳ lúc nào.

3. **Giao diện & Tiện ích**:
   - Thống kê trực quan: Tổng tài khoản, Đã chia sẻ, Tổng lượt quay, Phần thưởng trúng.
   - Bảng danh sách tài khoản (Treeview) hiển thị STT, Email, Token rút gọn, Lượt quay, Trạng thái, Quà trúng.
   - Chuột phải trên từng dòng để thao tác riêng cho tài khoản đó (Chạy lẻ, sao chép token, xóa).
   - Thanh tiến độ (Progress bar) & Nhật ký chi tiết theo thời gian thực (Live colored logs).
   - Xuất kết quả ra file `.csv` có UTF-8 BOM hiển thị tiếng Việt chuẩn trên Excel.
   - Tùy chỉnh: Event AID, Số luồng (1 - 10 threads), Độ trễ (delay giây).

---

## 📋 Hướng dẫn lấy `login-credential` trên LagoFast

1. Mở trình duyệt Chrome/Edge và truy cập trang sự kiện:
   `https://www.lagofast.com/vi/act/?aid=7f01ceea3e054f9aa7a3f92c4aea8a86`
2. Đăng nhập vào tài khoản Google / LagoFast của bạn.
3. Nhấn **F12** (hoặc chuột phải chọn **Kiểm tra / Inspect**):
   - Chuyển sang tab **Network** (Mạng), lọc từ khóa `member` hoặc `act`.
   - Tìm request `member/detail` hoặc `remain/times`.
   - Trong mục **Request Headers**, sao chép giá trị của `login-credential`.
   *(Ví dụ: `20260930202934000000000001750220_dd2bb9ad64f943bf9a04`)*

---

## 💻 Cách sử dụng

### 1. Khởi chạy nhanh
- Nhấp đúp chuột vào file `run.bat`
- Hoặc mở terminal trong thư mục `df-tool` và chạy:
  ```bash
  python main.py
  ```

### 2. Thao tác trên giao diện
- **Bước 1**: Nhấn nút **➕ Dán danh sách** hoặc **📂 Nhập File** để nạp danh sách tài khoản.
- **Bước 2**: Tùy chỉnh số luồng (mặc định 3 luồng) và delay (mặc định 1 giây).
- **Bước 3**: Nhấn **⚡ CHẠY TẤT CẢ** để tool tự động chia sẻ sự kiện và quay thưởng.
- **Bước 4**: Nhấn **💾 Xuất CSV** để lưu báo cáo danh sách quà tặng đã trúng thưởng.

---

## 📦 Đóng gói thành file `.exe` độc lập

Nếu bạn muốn chạy ứng dụng mà không cần cài đặt Python:
1. Nhấp đúp chuột vào file `build_exe.bat`.
2. Chờ PyInstaller đóng gói xong.
3. File `.exe` sẽ được tạo tại thư mục:
   `dist\LagoFast_Event_Tool\LagoFast_Event_Tool.exe`
