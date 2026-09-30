# ⚡ LagoFast Event Auto Tool (Chia Sẻ Sự Kiện & Quay Thưởng)

Công cụ desktop Windows với giao diện đồ họa hiện đại (**CustomTkinter Dark Mode**), hỗ trợ xử lý đa luồng (multi-threading) cho danh sách tài khoản LagoFast: tự động chia sẻ sự kiện nhận lượt quay và tiến hành quay thưởng may mắn.

---

## 🔑 Hướng dẫn lấy `Login-Credential` cực nhanh (Chỉ mất 5 giây)

Khi bạn đăng nhập tài khoản Google trên web LagoFast, hệ thống sẽ lưu token xác thực vào cookie mang tên `Login-Credential`. Dưới đây là 3 cách lấy:

### ⚡ Cách 1: Dùng lệnh 1-Click (Khuyên dùng - Nhanh nhất)
1. Trong tool, chuyển sang tab **📥 Nhập Tài Khoản / Email**.
2. Nhấn nút **🌐 Mở trang sự kiện LagoFast trên trình duyệt** và đăng nhập Google.
3. Nhấn nút **📋 Copy mã lấy Token nhanh (1-Click)** trên tool (hoặc copy đoạn mã bên dưới):
   ```javascript
   copy(document.cookie.match(/Login-Credential=([^;]+)/)[1]); alert("Đã copy token!");
   ```
4. Trên trình duyệt web LagoFast, nhấn **F12** -> chọn tab **Console** -> nhấn `Ctrl + V` để dán và gõ `Enter`.
5. Token sẽ được **tự động copy vào bộ nhớ tạm**! Bạn chỉ cần quay lại tool và dán vào ô nhập theo dạng: `email@gmail.com|token`.

---

### 🍪 Cách 2: Xem trực tiếp trong Cookie (F12)
1. Trên trang web LagoFast đã đăng nhập, nhấn phím **F12** (hoặc chuột phải chọn *Kiểm tra / Inspect*).
2. Chọn tab **Application** (Ứng dụng) ở thanh menu trên cùng.
3. Ở cột bên trái, tìm mục **Storage** -> mở **Cookies** -> nhấp vào `https://www.lagofast.com`.
4. Tìm dòng có tên là `Login-Credential`.
5. Cột **Value** chính là chuỗi token cần lấy (dạng: `20260930..._dd2bb9ad64f943bf9a04`). Nhấp đúp và sao chép.

---

### 🌐 Cách 3: Lấy từ tab Network (Mạng)
1. Nhấn **F12** -> chuyển sang tab **Network** (Mạng).
2. Lọc từ khóa `member` hoặc `act`.
3. Tìm bất kỳ request nào như `member/detail` hoặc `remain/times`.
4. Nhìn vào khung **Request Headers** ở bên phải, copy giá trị của dòng `login-credential`.

---

## 🚀 Các tính năng chính của ứng dụng

Ứng dụng chia làm 2 Tab rõ ràng:

### 1. Tab ⚡ Điều Khiển & Danh Sách
- **Thống kê tổng quan**: Số tài khoản, Đã chia sẻ, Tổng lượt quay khả dụng, Phần thưởng đã trúng.
- **⚡ CHẠY TẤT CẢ (Auto All)**: Tự động chạy toàn bộ quy trình: Lấy email -> Chia sẻ sự kiện nhận lượt -> Quay sạch tất cả lượt còn lại -> Cập nhật quà trúng.
- **📤 Chia sẻ sự kiện**: Gửi request chia sẻ nhận lượt quay (`/api/act/v1/change/get/{aid}/share_activity`).
- **🎲 Quay thưởng (Lucky Draw)**: Quay thưởng may mắn (`/api/act/v1/luck/draw/{aid}`).
- **🔍 Kiểm tra Info**: Cập nhật email, số lượt quay hiện tại và trạng thái chia sẻ.
- **🛑 Dừng lại (Stop)**: Dừng an toàn tất cả luồng đang chạy bất kỳ lúc nào.
- **💾 Xuất CSV**: Xuất danh sách kết quả trúng thưởng ra file `.csv` chuẩn Excel.

### 2. Tab 📥 Nhập Tài Khoản / Email
- **Khung nhập liệu đa dòng**: Cho phép tự do nhập, dán danh sách tài khoản.
- Hỗ trợ các định dạng:
  - `email|login_credential` (Khuyên dùng)
  - `email----login_credential`
  - Chỉ chuỗi `login_credential` (tool tự động lấy email qua API)
- **Nút 📂 Chọn File .TXT / .CSV**: Nạp file tài khoản trực tiếp vào tool.
- **Nút ➕ Thêm vào danh sách**: Nối thêm tài khoản vào danh sách hiện tại.
- **Nút 🔄 Thay thế danh sách**: Xóa cũ và thay thế toàn bộ bằng danh sách mới.
- **Khung hướng dẫn tích hợp**: Có sẵn nút mở web và nút copy lệnh trích xuất token 1-click.

---

## 💻 Cách khởi chạy tool

1. **Khởi chạy nhanh**:
   - Nhấp đúp vào file `run.bat` (hoặc chạy lệnh `python main.py`).
2. **Đóng gói file .exe độc lập**:
   - Nhấp đúp vào file `build_exe.bat`. File `.exe` sẽ được tạo tại thư mục `dist\LagoFast_Event_Tool\LagoFast_Event_Tool.exe`.
