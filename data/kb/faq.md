Khi container Docker không kết nối được tới service khác, nguyên nhân phổ biến nhất là dùng sai hostname. Trong cùng một docker-compose network, các service phải tham chiếu nhau bằng service name chứ không phải localhost.

Policy hoàn tiền của công ty: khách hàng được hoàn tiền 100% trong vòng 14 ngày kể từ ngày mua nếu sản phẩm còn nguyên seal. Sau 14 ngày, chỉ hỗ trợ đổi sản phẩm tương đương, không hoàn tiền mặt.

Giờ làm việc của bộ phận hỗ trợ khách hàng: 8:00–18:00 từ Thứ Hai đến Thứ Sáu theo giờ Việt Nam (UTC+7). Ngoài giờ này, khách hàng có thể gửi email tới support@example.com và sẽ được phản hồi trong vòng 24 giờ làm việc.

Để reset mật khẩu tài khoản, người dùng truy cập trang đăng nhập, bấm "Quên mật khẩu", nhập email đã đăng ký. Hệ thống sẽ gửi link reset có hiệu lực trong 30 phút. Nếu không nhận được email, kiểm tra thư mục Spam trước khi liên hệ support.

Khi deploy ứng dụng Python lên production, nên tắt debug mode và chạy với gunicorn hoặc uvicorn thay vì development server. Development server của Flask/FastAPI không chịu được tải và rò rỉ thông tin nhạy cảm qua error page.

Chính sách bảo mật PII: dữ liệu cá nhân của user (tên, email, số điện thoại, địa chỉ) được lưu mã hóa AES-256 ở database. TTL mặc định là 2 năm kể từ lần đăng nhập cuối; sau đó bị anonymize tự động. Người dùng có thể yêu cầu xóa ngay bằng cách gửi request tới privacy@example.com.
