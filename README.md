# VN Stock: Multi-Period VWAP & ZigZag Web App

Ứng dụng Streamlit hiển thị biểu đồ giá trực tuyến tích hợp các chỉ báo **Multi-Period VWAP** (Session, Tuần, Tháng, Quý, Năm) và thuật toán **ZigZag** chuẩn MT5. 

Giao diện ứng dụng được thiết kế tối ưu, có chiều cao tự động thích ứng với điện thoại di động và tắt các cử chỉ kéo zoom/pan gây kẹt màn hình giúp cuộn trang mượt mà.

---

## 🚀 Các Tính Năng Chính (Core Features)

1.  **Tra cứu mã chứng khoán**: Hỗ trợ toàn bộ mã cổ phiếu, chứng quyền, chỉ số Việt Nam và hợp đồng tương lai chỉ số (**`VN30F1M`**).
2.  **Khung thời gian linh hoạt**:
    *   Cổ phiếu thường: Hỗ trợ khung Daily (D) và 1 Giờ (H1).
    *   Hợp đồng `VN30F1M`: Hỗ trợ thêm các khung thời gian ngắn hạn **`15m`** (15 Phút) và **`5m`** (5 Phút).
3.  **Tự động điều chỉnh phạm vi hiển thị (Display Slicing)**:
    *   Khung H1 & D: Phạm vi hiển thị **12 Tháng, 6 Tháng, 3 Tháng**.
    *   Khung 5m & 15m: Phạm vi hiển thị **1 Tuần, 2 Tuần, 1 Tháng, 3 Tháng** để tránh quá tải trình duyệt di động.
4.  **Tích hợp Multi-Period VWAP**:
    *   Đường VWAP tự động ngắt kết nối (bị đứt đoạn) khi đi qua ranh giới chu kỳ (ngày, tuần, tháng, quý, năm) giống MQL5.
    *   Tự động ẩn giá trị tại nến hiện tại (Forming bar) để tránh hiện tượng vẽ lại chỉ báo (repainting).
    *   Hỗ trợ tự động chuyển đổi nguồn dữ liệu dự phòng (Fallback) từ **VCI** sang **KBS** nếu nguồn mặc định bị lỗi kết nối hoặc chặn IP trên Cloud.
5.  **Thuật toán ZigZag chuẩn MT5**:
    *   Được dịch nguyên bản từ máy thế thái cực (State Machine) của MQL5 (Depth=12, Deviation=2.0, Backstep=3).
    *   Được hiển thị dưới dạng đường đứt nét màu xám nhạt (`#CCCCCC`) không chứa các nốt tròn gây rối mắt.
6.  **Tối ưu hóa hiển thị di động**:
    *   Chiều cao biểu đồ tự động co giãn (420px trên điện thoại / 580px trên máy tính).
    *   Tắt các thao tác phóng to/thu nhỏ bằng cử chỉ kéo thả (`dragmode=False`, `scrollZoom=False`) để tránh cản trở thao tác vuốt cuộn trang trên điện thoại.

---

## 🛠️ Cài Đặt & Chạy Dưới Local (Installation & Local Run)

### 1. Chuẩn bị môi trường
Yêu cầu hệ thống đã cài đặt **Python 3.11** hoặc **Python 3.12**.

Mở Command Prompt hoặc Terminal tại thư mục chứa mã nguồn và cài đặt thư viện:
```bash
pip install -r requirements.txt
```

### 2. Khởi chạy ứng dụng
Chạy lệnh Streamlit để khởi chạy giao diện web:
```bash
streamlit run app.py --server.port 8505
```
Hoặc trên Windows, bạn chỉ cần nhấp đúp vào tệp **`run_app.bat`** để chạy trực tiếp trên cổng `8505`.

---

## ☁️ Hướng Dẫn Deploy Lên Streamlit Cloud

1.  Đẩy toàn bộ mã nguồn của thư mục này lên một repository công khai (hoặc riêng tư) trên tài khoản GitHub của bạn (ví dụ: `https://github.com/username/vwap_ckvn`).
2.  Truy cập vào **[share.streamlit.io](https://share.streamlit.io/)** và đăng nhập bằng tài khoản GitHub của bạn.
3.  Bấm vào **Create app** và điền thông tin cấu hình:
    *   **Repository**: Chọn repo của bạn (ví dụ: `username/vwap_ckvn`).
    *   **Branch**: Điền là **`main`**.
    *   **Main file path**: Điền là **`app.py`**.
4.  Bấm **Deploy!**. Ứng dụng sẽ được khởi tạo môi trường và sẵn sàng chạy trực tuyến sau 1-2 phút.

---

## 📝 Ghi Chú Phát Triển (Future Scope)
*   **Hiện tại**: Ứng dụng tập trung tối đa cho dữ liệu chứng khoán và phái sinh Việt Nam thông qua thư viện `vnstock`.
*   **Tương lai**: Cấu trúc thư mục được tách biệt sẵn sàng cho việc tích hợp thêm dữ liệu đa tài sản quốc tế như Vàng (**`XAUUSD`**), Ngoại hối (Forex) và Tiền điện tử.

---

## 📄 Bản Quyền (License)
Dự án được phân phối theo giấy phép mã nguồn mở **MIT License**. Chi tiết xem tại tệp `LICENSE`.
