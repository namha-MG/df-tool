# ⚡ LagoFast Event Auto Tool (Hỗ Trợ Username/Password & Token)

Công cụ desktop Windows với giao diện đồ họa hiện đại (**CustomTkinter Dark Mode**), hỗ trợ xử lý đa luồng (multi-threading) cho danh sách tài khoản LagoFast: tự động đăng nhập bằng **Username / Password** hoặc **Token**, chia sẻ sự kiện nhận lượt quay và tiến hành quay thưởng may mắn.

---

## 🎯 Tính năng mới cập nhật

### 1. Đăng nhập trực tiếp bằng `Username / Password`
- Bạn có thể nhập danh sách tài khoản theo định dạng:
  ```text
  username|password
  email@gmail.com|matkhau123
  email@gmail.com----matkhau123
  ```
- Tool tích hợp sẵn trình điều khiển tự động (**Selenium**):
  - Tự động mở trang đăng nhập LagoFast.
  - Tự điền tài khoản, mật khẩu và bấm đăng nhập.
  - Nếu xuất hiện hình kéo mảnh ghép Captcha, bạn chỉ cần kéo mảnh ghép trong 2 giây.
  - Tool tự động trích xuất token `Login-Credential` và lưu vĩnh viễn vào bộ nhớ đệm (`accounts_cache.json`), **không bao giờ phải đăng nhập lại lần 2**!

### 2. Cơ chế "Mỗi tài khoản chỉ chạy thành công 1 lần"
- **Tự động bỏ qua tài khoản đã hoàn thành**:
  - Khi một tài khoản đã thực hiện xong các bước (Chia sẻ sự kiện + Quay sạch các lượt quay), tài khoản sẽ được đánh dấu **`Hoàn tất`** (Cột `Xong?` hiển thị **`Có`**).
  - Tùy chọn **`[x] Chỉ chạy 1 lần (Bỏ qua acc đã xong)`** được bật mặc định. Khi bạn nhấn **⚡ CHẠY TẤT CẢ**, tool sẽ chỉ quét và chạy những tài khoản chưa xong, tuyệt đối không chạy lặp lại các tài khoản đã hoàn tất.
- **Linh hoạt chạy lại**:
  - Nếu bạn muốn chạy lại tài khoản đã hoàn tất: Bỏ tích chọn mục *Chỉ chạy 1 lần*, hoặc nhấn nút **`🔄 Reset trạng thái`** để đặt lại trạng thái cho toàn bộ danh sách, hoặc chuột phải vào tài khoản chọn *Chạy tài khoản này*.

---

## 📋 Các định dạng nhập tài khoản được hỗ trợ

Trong tab **📥 Nhập Tài Khoản**, bạn có thể dán hoặc chọn file `.txt` chứa danh sách theo các định dạng sau:

| Định dạng | Ví dụ | Cơ chế hoạt động |
|---|---|---|
| `username\|password` | `user01\|Pass123456` | Tự động mở trình duyệt đăng nhập lấy token rồi chạy |
| `email\|password` | `mymail@gmail.com\|Pass123456` | Tự động mở trình duyệt đăng nhập lấy token rồi chạy |
| `email\|password\|token` | `mail@gmail.com\|Pass123\|202609...` | Sử dụng ngay token có sẵn mà không cần mở trình duyệt |
| `email\|login_credential` | `mail@gmail.com\|20260930..._dd2bb9...` | Chạy trực tiếp qua API siêu tốc |
| `login_credential` | `20260930202934000000000001750220_...` | Tool tự gọi API lấy email thực tế tương ứng |

---

## 🚀 Hướng dẫn khởi chạy & sử dụng

1. **Khởi chạy ứng dụng**:
   - Nhấp đúp chuột vào file [run.bat](file:///c:/Users/t5240/Documents/PJ/DF%20Tool/df-tool/run.bat) (hoặc chạy lệnh `python main.py` trong thư mục [df-tool](file:///c:/Users/t5240/Documents/PJ/DF%20Tool/df-tool)).
2. **Nạp danh sách tài khoản**:
   - Chuyển sang tab **📥 Nhập Tài Khoản (Username/Pass/Token)**.
   - Dán danh sách hoặc bấm **📂 Chọn File .TXT / .CSV**, sau đó bấm **➕ Thêm vào danh sách**.
3. **Chạy tự động**:
   - Quay lại tab **⚡ Điều Khiển & Danh Sách**.
   - Bấm nút **⚡ CHẠY TẤT CẢ (Chia sẻ + Quay)**.
   - Các tài khoản sau khi hoàn thành sẽ hiển thị quà trúng và được đánh dấu hoàn tất.
4. **Xuất kết quả**:
   - Bấm **💾 Xuất CSV** để lưu file thống kê quà đã trúng.
