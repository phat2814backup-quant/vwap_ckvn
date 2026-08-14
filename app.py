# -*- coding: utf-8 -*-
"""
=============================================================================
MODULE: app.py
TYPE: Web Application
PURPOSE: Multi-period VWAP and ZigZag chart application for Vietnamese stocks
GOVERNANCE: Stable
LAST UPDATED: 2026-08-14
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys

# Thiết lập bảng mã UTF-8 cho stdout trên Windows
sys.stdout.reconfigure(encoding='utf-8')

# Thêm src vào sys.path nếu cần thiết
sys.path.insert(0, 'src')

# Import vnstock
try:
    from vnstock_data import Quote
except ImportError:
    from vnstock.api.quote import Quote

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="VN Stock: Multi-Period VWAP & ZigZag",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thêm CSS tùy chỉnh ép nền trắng và chữ đen (Tránh lỗi không thấy gì do theme hệ thống)
st.markdown("""
<style>
    /* Ép Streamlit dùng nền trắng và chữ tối màu */
    .stApp {
        background-color: #FFFFFF !important;
        color: #212121 !important;
    }
    
    /* Khung nhập liệu và lựa chọn */
    div[data-baseweb="input"] {
        background-color: #F5F5F5 !important;
        color: #212121 !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
    }
    
    div[data-baseweb="select"] {
        background-color: #F5F5F5 !important;
        color: #212121 !important;
        border-radius: 8px !important;
    }
    
    /* Thiết lập lại màu chữ cho toàn bộ văn bản */
    label, p, span, h1, h2, h3, h4, h5, h6, small {
        color: #212121 !important;
    }
    
    /* Điều chỉnh khoảng cách hiển thị tối ưu di động */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Nút bấm Cập Nhật nổi bật, màu xanh lá */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        background-color: #2E7D32 !important;
        color: #FFFFFF !important;
        border: none !important;
        height: 40px;
    }
    .stButton>button:hover {
        background-color: #1B5E20 !important;
        color: #FFFFFF !important;
    }
    
    /* Tiêu đề ứng dụng */
    .main-title {
        font-size: 1.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
        color: #1B5E20 !important;
    }
    .sub-title {
        font-size: 0.9rem;
        text-align: center;
        color: #666666 !important;
        margin-bottom: 1.2rem;
    }
    
    /* Thẻ metric */
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #1B5E20 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 1. HÀM TẢI DỮ LIỆU TỪ VNSTOCK (CÓ CACHE)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)  # Cache trong 5 phút
def fetch_stock_data(symbol: str, timeframe: str) -> dict:
    """Tải dữ liệu lịch sử giá từ vnstock."""
    symbol = symbol.upper().strip()
    if timeframe == "H1":
        timeframe = "1H"
    elif timeframe == "D":
        timeframe = "1D"
        
    today = datetime.now()
    
    # Tối ưu hóa: Nếu là khung 5m hoặc 15m, chỉ tải 3 tháng để tránh quá nặng
    if timeframe in ["5m", "15m"]:
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    else:
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d") # 12 tháng
        
    end_date = today.strftime("%Y-%m-%d")
    interval = timeframe # "5m", "15m", "1H", or "1D"
    
    try:
        # Sử dụng nguồn VCI (nhanh và ổn định cho lịch sử)
        q = Quote(symbol=symbol, source='VCI')
        df = q.history(start=start_date, end=end_date, interval=interval)
        
        if df is None or df.empty:
            return {"df": pd.DataFrame(), "fetch_time": datetime.now()}
            
        # Đảm bảo cột thời gian là datetime
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        # Chuyển đổi tên các cột sang kiểu chuẩn để dễ xử lý
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        return {"df": df, "fetch_time": datetime.now()}
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu cho mã {symbol}: {e}")
        return {"df": pd.DataFrame(), "fetch_time": datetime.now()}

# ---------------------------------------------------------------------------
# 2. TÍNH TOÁN CÁC ĐƯỜNG VWAP ĐA KHUNG THỜI GIAN
# ---------------------------------------------------------------------------
def calculate_vwap(df: pd.DataFrame, period_type: str, price_source: str, break_lines: bool, skip_last_bar: bool) -> pd.Series:
    """
    Tính toán VWAP đa chu kỳ với tùy chọn ngắt kết nối tại ranh giới chu kỳ
    và ẩn giá trị tại nến hiện tại (forming bar).
    """
    n = len(df)
    if n == 0:
        return pd.Series(dtype=float)
        
    # Tính toán Giá Nguồn (Price Source)
    if price_source == "Typical (HLC3)":
        price = (df['high'] + df['low'] + df['close']) / 3.0
    elif price_source == "Weighted (OHLC4)":
        price = (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
    elif price_source == "Median (HL2)":
        price = (df['high'] + df['low']) / 2.0
    else:  # Close
        price = df['close']
        
    vol = df['volume']
    
    # Xác định khóa chu kỳ (Period Key)
    times = df['time']
    if period_type == "Session/Day": # 1 Ngày
        keys = times.dt.date
    elif period_type == "Week": # 1 Tuần
        keys = times.dt.to_period('W').dt.start_time
    elif period_type == "Month": # 1 Tháng
        keys = times.dt.to_period('M').dt.start_time
    elif period_type == "Quarter": # 3 Tháng
        keys = times.dt.to_period('Q').dt.start_time
    elif period_type == "Year": # 12 Tháng / Năm
        keys = times.dt.to_period('Y').dt.start_time
    else:
        keys = pd.Series([0] * n)
        
    # Tính toán Tích lũy tích và Tích lũy khối lượng
    tpv = price * vol
    
    cum_vol = vol.groupby(keys).cumsum()
    cum_tpv = tpv.groupby(keys).cumsum()
    
    vwap = cum_tpv / (cum_vol + 1e-10)
    
    # Tạo đứt đoạn tại ranh giới (Break lines at period boundaries)
    if break_lines and n > 1:
        # Xác định các điểm thay đổi chu kỳ
        is_boundary = keys != keys.shift(1)
        is_boundary.iloc[0] = False  # Bỏ qua dòng đầu tiên
        
        # MQL5 style: Gán nến đầu tiên của kỳ mới bằng NaN để ngắt kết nối
        vwap = vwap.copy()
        vwap.loc[is_boundary] = np.nan
        
    # Ẩn nến cuối cùng (Forming bar)
    if skip_last_bar and n > 0:
        vwap.iloc[-1] = np.nan
        
    return vwap

# ---------------------------------------------------------------------------
# 3. TÍNH TOÁN CHỈ BÁO ZIGZAG (DỊCH TỪ MQL5)
# ---------------------------------------------------------------------------
def calculate_zigzag(df: pd.DataFrame, depth: int = 12, deviation: float = 5.0, backstep: int = 3, deviation_type: str = "Percent") -> pd.Series:
    """
    Thuật toán ZigZag dịch chuẩn xác từ phiên bản MQL5.
    Trả về Series chứa giá trị đỉnh/đáy, các điểm khác bằng NaN.
    """
    n = len(df)
    zigzag = np.zeros(n)
    
    if n < depth:
        return pd.Series([np.nan] * n)
        
    highs = df['high'].values
    lows = df['low'].values
    
    high_map = np.zeros(n)
    low_map = np.zeros(n)
    
    last_low = 0.0
    last_high = 0.0
    
    # 1. Tìm các đỉnh/đáy cực trị ban đầu
    for shift in range(depth, n):
        # Khoảng tìm kiếm từ [shift - depth + 1] đến [shift]
        low_window = lows[shift - depth + 1 : shift + 1]
        min_val = np.min(low_window)
        min_idx = shift - depth + 1 + np.argmin(low_window)
        
        high_window = highs[shift - depth + 1 : shift + 1]
        max_val = np.max(high_window)
        max_idx = shift - depth + 1 + np.argmax(high_window)
        
        # --- Tính Đáy (Low Extreme) ---
        if min_val == last_low:
            val_low = 0.0
        else:
            last_low = min_val
            
            # Tính giới hạn sai số (Deviation)
            if deviation_type == "Percent":
                dev_limit = (lows[shift] * deviation) / 100.0
            else:  # Absolute
                dev_limit = deviation
                
            if (lows[shift] - min_val) > dev_limit:
                val_low = 0.0
            else:
                # Kiểm tra Backstep: loại bỏ đỉnh/đáy cũ cao hơn trong phạm vi backstep
                for back in range(1, backstep + 1):
                    prev_idx = shift - back
                    if prev_idx >= 0:
                        res = low_map[prev_idx]
                        if res != 0.0 and res > min_val:
                            low_map[prev_idx] = 0.0
                val_low = min_val
                
        if lows[shift] == val_low:
            low_map[shift] = val_low
        else:
            low_map[shift] = 0.0
            
        # --- Tính Đỉnh (High Extreme) ---
        if max_val == last_high:
            val_high = 0.0
        else:
            last_high = max_val
            
            # Tính giới hạn sai số (Deviation)
            if deviation_type == "Percent":
                dev_limit = (highs[shift] * deviation) / 100.0
            else:  # Absolute
                dev_limit = deviation
                
            if (max_val - highs[shift]) > dev_limit:
                val_high = 0.0
            else:
                # Kiểm tra Backstep: loại bỏ đỉnh/đáy cũ thấp hơn trong phạm vi backstep
                for back in range(1, backstep + 1):
                    prev_idx = shift - back
                    if prev_idx >= 0:
                        res = high_map[prev_idx]
                        if res != 0.0 and res < max_val:
                            high_map[prev_idx] = 0.0
                val_high = max_val
                
        if highs[shift] == val_high:
            high_map[shift] = val_high
        else:
            high_map[shift] = 0.0

    # 2. Quy trình chọn lọc đỉnh/đáy luân phiên cuối cùng (State Machine)
    # 0 = Extremum (Bắt đầu), 1 = Peak (Tìm đỉnh tiếp theo), -1 = Bottom (Tìm đáy tiếp theo)
    extreme_search = 0  
    last_low = 0.0
    last_high = 0.0
    last_low_pos = 0
    last_high_pos = 0
    
    for shift in range(depth, n):
        val_low = low_map[shift]
        val_high = high_map[shift]
        
        if extreme_search == 0:  # Định vị điểm cực trị đầu tiên
            if last_low == 0.0 and last_high == 0.0:
                if val_high != 0.0:
                    last_high = highs[shift]
                    last_high_pos = shift
                    extreme_search = -1  # Đã có đỉnh, tìm đáy tiếp theo
                    zigzag[shift] = last_high
                elif val_low != 0.0:
                    last_low = lows[shift]
                    last_low_pos = shift
                    extreme_search = 1   # Đã có đáy, tìm đỉnh tiếp theo
                    zigzag[shift] = last_low
                    
        elif extreme_search == 1:  # Đang tìm Đỉnh
            # Nếu thấy đáy mới thấp hơn nữa khi chưa tìm thấy đỉnh
            if val_low != 0.0 and val_low < last_low and val_high == 0.0:
                zigzag[last_low_pos] = 0.0  # Hủy đáy cũ
                last_low_pos = shift
                last_low = val_low
                zigzag[shift] = last_low
                
            # Nếu thấy đỉnh hợp lệ
            if val_high != 0.0 and val_low == 0.0:
                last_high = val_high
                last_high_pos = shift
                zigzag[shift] = last_high
                extreme_search = -1  # Đổi trạng thái sang tìm Đáy tiếp theo
                
        elif extreme_search == -1:  # Đang tìm Đáy
            # Nếu thấy đỉnh mới cao hơn nữa khi chưa tìm thấy đáy
            if val_high != 0.0 and val_high > last_high and val_low == 0.0:
                zigzag[last_high_pos] = 0.0  # Hủy đỉnh cũ
                last_high_pos = shift
                last_high = val_high
                zigzag[shift] = last_high
                
            # Nếu thấy đáy hợp lệ
            if val_low != 0.0 and val_high == 0.0:
                last_low = val_low
                last_low_pos = shift
                zigzag[shift] = last_low
                extreme_search = 1   # Đổi trạng thái sang tìm Đỉnh tiếp theo

    # 3. Chuyển kết quả sang định dạng Pandas Series (các điểm cực trị là giá trị, các điểm khác là NaN)
    zigzag_series = pd.Series([np.nan] * n)
    for i in range(n):
        if zigzag[i] != 0.0:
            zigzag_series.iloc[i] = zigzag[i]
            
    return zigzag_series

# ---------------------------------------------------------------------------
# 4. GIAO DIỆN CHÍNH (ĐÃ DI CHUYỂN BỘ ĐIỀU KHIỂN LÊN TRANG CHÍNH CHO DI ĐỘNG)
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">📈 VN Stock Chart</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Biểu đồ Line Price tích hợp Multi-Period VWAP và ZigZag tương thích Di động</div>', unsafe_allow_html=True)

# Khởi tạo các biến cấu hình ngay trên trang chính (Dạng dòng cột)
col_search, col_tf, col_range, col_btn = st.columns([2, 2, 2, 1])

with col_search:
    selected_stock = st.text_input("🔍 Nhập mã Cổ phiếu:", value="VN30F1M").upper().strip()

with col_tf:
    # Nếu mã là VN30F1M thì hiện thêm khung 5m, 15m
    if selected_stock == "VN30F1M":
        tf_options = ["D (Hàng Ngày)", "H1 (1 Giờ)", "15m (15 Phút)", "5m (5 Phút)"]
        default_tf_idx = 3 # Mặc định 5m
    else:
        tf_options = ["D (Hàng Ngày)", "H1 (1 Giờ)"]
        default_tf_idx = 1 # Mặc định H1
        
    timeframe = st.selectbox("📅 Khung thời gian:", options=tf_options, index=default_tf_idx)
    
    # Trích xuất mã khung thời gian
    if "H1" in timeframe:
        tf_code = "1H"
    elif "15m" in timeframe:
        tf_code = "15m"
    elif "5m" in timeframe:
        tf_code = "5m"
    else:
        tf_code = "1D"

with col_range:
    if tf_code in ["5m", "15m"]:
        range_options = ["1 Tuần", "2 Tuần", "1 Tháng", "3 Tháng"]
        default_range_idx = 0 # Mặc định 1 Tuần
    else:
        range_options = ["12 Tháng", "6 Tháng", "3 Tháng"]
        default_range_idx = 0 # Mặc định 12 Tháng
        
    display_range = st.selectbox("🔍 Phạm vi hiển thị:", options=range_options, index=default_range_idx)

with col_btn:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Khoảng trống căn hàng
    reload_button = st.button("🔄 Cập Nhật")
    if reload_button:
        st.cache_data.clear()

# Cấu hình nâng cao rút gọn trong Expander
with st.expander("⚙️ Thiết Lập Chỉ Báo (VWAP & ZigZag)"):
    st.write("Thay đổi các tham số tính toán của chỉ báo kỹ thuật:")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        price_source = st.selectbox(
            "Giá dùng tính VWAP:",
            options=["Typical (HLC3)", "Weighted (OHLC4)", "Median (HL2)", "Close"],
            index=0
        )
        break_lines = st.checkbox("Ngắt kết nối ranh giới kỳ (MQL5 Style)", value=True)
        skip_last_bar = st.checkbox("Ẩn VWAP ở nến hiện tại (Forming Bar)", value=True)
    with col_v2:
        st.write("Đường VWAP hiển thị:")
        show_vwap_day = st.checkbox("VWAP 1 Ngày (Session) - Chỉ hỗ trợ Intraday", value=(tf_code in ["1H", "15m", "5m"]))
        show_vwap_week = st.checkbox("VWAP 1 Tuần", value=True)
        show_vwap_month = st.checkbox("VWAP 1 Tháng", value=True)
        show_vwap_quarter = st.checkbox("VWAP Quý (3 Tháng)", value=True)
        show_vwap_year = st.checkbox("VWAP 12 Tháng (Năm)", value=True)
        
    st.divider()
    
    col_z1, col_z2 = st.columns(2)
    with col_z1:
        show_zigzag = st.checkbox("Hiển thị chỉ báo ZigZag", value=True)
        zigzag_depth = st.number_input("Depth (Độ sâu cửa sổ):", min_value=1, max_value=100, value=12)
    with col_z2:
        zigzag_deviation = st.number_input("Deviation (Sai số tối thiểu):", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
        zigzag_dev_type = st.selectbox("Loại sai số (Deviation Type):", options=["Percent", "Absolute"], index=0)
        zigzag_backstep = st.number_input("Back Step:", min_value=1, max_value=50, value=3)

# Tải dữ liệu khi có mã cổ phiếu
if selected_stock:
    with st.spinner(f"⏳ Đang tải dữ liệu {selected_stock}..."):
        result = fetch_stock_data(selected_stock, tf_code)
        df = result.get("df", pd.DataFrame())
        fetch_time = result.get("fetch_time", datetime.now())
        
    if df.empty:
        st.warning("⚠️ Không tải được dữ liệu. Vui lòng kiểm tra lại mã cổ phiếu.")
    else:
        # --- Thông tin thẻ Metric ---
        last_row = df.iloc[-1]
        last_price = last_row['close'] * 1000  # Quy đổi về VND
        
        # Định dạng thời gian cập nhật đúng yêu cầu giờ phút nếu có
        if tf_code in ["1H", "15m", "5m"]:
            # Hiển thị giờ phút đầy đủ cho Intraday
            last_time = last_row['time'].strftime('%d/%m/%Y %H:%M')
        else:
            # Chỉ hiển thị ngày cho Daily
            last_time = last_row['time'].strftime('%d/%m/%Y')
            
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mã Cổ Phiếu", selected_stock)
        with col2:
            st.metric("Giá Hiện Tại", f"{last_price:,.0f} đ")
        with col3:
            # Hiển thị thời gian nạp dữ liệu thành công từ API để tránh hiểu nhầm
            st.metric(
                label="Dữ Liệu Tải Lúc",
                value=fetch_time.strftime('%H:%M:%S'),
                delta=f"Nến cuối: {last_time}",
                delta_color="off"
            )

        # --- Tính toán các chỉ báo ---
        # VWAP
        if tf_code in ["1H", "15m", "5m"] and show_vwap_day:
            df['vwap_Day'] = calculate_vwap(df, "Session/Day", price_source, break_lines, skip_last_bar)
        if show_vwap_week:
            df['vwap_Week'] = calculate_vwap(df, "Week", price_source, break_lines, skip_last_bar)
        if show_vwap_month:
            df['vwap_Month'] = calculate_vwap(df, "Month", price_source, break_lines, skip_last_bar)
        if show_vwap_quarter:
            df['vwap_Quarter'] = calculate_vwap(df, "Quarter", price_source, break_lines, skip_last_bar)
        if show_vwap_year:
            df['vwap_Year'] = calculate_vwap(df, "Year", price_source, break_lines, skip_last_bar)
            
        # ZigZag
        if show_zigzag:
            df['zigzag'] = calculate_zigzag(df, zigzag_depth, zigzag_deviation, zigzag_backstep, zigzag_dev_type)
            
        # --- Lọc dữ liệu hiển thị (Slice) theo yêu cầu người dùng ---
        last_date = df['time'].max()
        if tf_code in ["5m", "15m"]:
            if display_range == "2 Tuần":
                start_display = last_date - timedelta(days=14)
            elif display_range == "1 Tháng":
                start_display = last_date - timedelta(days=30)
            elif display_range == "3 Tháng":
                start_display = last_date - timedelta(days=90)
            else: # 1 Tuần
                start_display = last_date - timedelta(days=7)
        else:
            if display_range == "6 Tháng":
                start_display = last_date - timedelta(days=180)
            elif display_range == "3 Tháng":
                start_display = last_date - timedelta(days=90)
            else: # 12 Tháng
                start_display = last_date - timedelta(days=365)
            
        df_plot = df[df['time'] >= start_display].copy()
            
        # --- Khởi tạo Biểu đồ Plotly (Màn hình Trắng/Sáng) ---
        fig = go.Figure()
        
        # 1. Đường giá Close chính (Đường màu xanh lá cây sẫm tăng độ tương phản trên nền trắng)
        fig.add_trace(go.Scatter(
            x=df_plot['time'],
            y=df_plot['close'],
            mode='lines',
            name='Giá Close',
            line=dict(color='#2E7D32', width=2.0),
            hovertemplate='%{x}<br>Giá Close: %{y:.2f}<extra></extra>'
        ))
        
        # 2. Thêm các đường VWAP đứt nét, độ đậm vừa phải trên nền trắng
        vwap_config = {
            "Session/Day": dict(color='#1565C0', width=2.0, dash='solid', name='VWAP Ngày (Session)', col='vwap_Day'),
            "Week": dict(color='#E65100', width=1.2, dash='dash', name='VWAP Tuần', col='vwap_Week'),
            "Month": dict(color='#C62828', width=1.2, dash='dash', name='VWAP Tháng', col='vwap_Month'),
            "Quarter": dict(color='#00838F', width=1.2, dash='dash', name='VWAP Quý', col='vwap_Quarter'),
            "Year": dict(color='#6A1B9A', width=1.5, dash='dash', name='VWAP 12 Tháng', col='vwap_Year')
        }
        
        for p_name, cfg in vwap_config.items():
            col_name = cfg['col']
            if col_name in df_plot.columns:
                fig.add_trace(go.Scatter(
                    x=df_plot['time'],
                    y=df_plot[col_name],
                    mode='lines',
                    name=cfg['name'],
                    line=dict(color=cfg['color'], width=cfg['width'], dash=cfg['dash']),
                    connectgaps=False,  # Ngắt kết nối khi có giá trị NaN
                    hovertemplate=f'%{{x}}<br>{cfg["name"]}: %{{y:.2f}}<extra></extra>'
                ))
            
        # 3. Thêm đường ZigZag: màu xám rất nhạt, nét đứt (chấm), không có dấu chấm tròn
        if show_zigzag and 'zigzag' in df_plot.columns:
            df_zz = df_plot.dropna(subset=['zigzag'])
            if not df_zz.empty:
                fig.add_trace(go.Scatter(
                    x=df_zz['time'],
                    y=df_zz['zigzag'],
                    mode='lines',
                    name='ZigZag',
                    # Line màu xám nhạt, kiểu chấm (dot), độ rộng 1.2
                    line=dict(color='#CCCCCC', width=1.2, dash='dot'),
                    hovertemplate='%{x}<br>Cực trị ZigZag: %{y:.2f}<extra></extra>'
                ))

        # Cấu hình rangebreaks để ẩn các ngày nghỉ cuối tuần, giờ nghỉ đêm và nghỉ trưa
        rbreaks = [dict(bounds=["sat", "mon"])]
        if tf_code in ["1H", "15m", "5m"]:
            rbreaks.append(dict(bounds=[15, 9], pattern="hour"))      # Đêm: 15h00 đến 09h00 sáng hôm sau
            rbreaks.append(dict(bounds=[11.5, 13], pattern="hour"))   # Trưa: 11h30 đến 13h00 trưa cùng ngày

        # --- Định cấu hình Layout Nền Trắng (plotly_white) ---
        fig.update_layout(
            template='plotly_white',
            title=dict(
                text=f"Biểu đồ phân tích kỹ thuật {selected_stock} ({tf_code}) - Lịch sử {display_range}",
                font=dict(size=16, color='#212121')
            ),
            xaxis=dict(
                title=dict(text="Thời gian", font=dict(color='#212121')),
                tickfont=dict(color='#212121'),
                gridcolor='#EAEAEA',
                rangeslider=dict(visible=False), # Tắt slider dưới chân cho gọn màn hình di động
                type='date',
                rangebreaks=rbreaks
            ),
            yaxis=dict(
                title=dict(text="Giá (nghìn VNĐ)", font=dict(color='#212121')),
                tickfont=dict(color='#212121'),
                side="right", # Đặt trục giá bên phải giống TradingView
                gridcolor='#EAEAEA'
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10, color='#212121')
            ),
            margin=dict(l=10, r=10, t=80, b=10),
            height=600,
            hovermode="x unified",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF"
        )
        
        # Hiển thị đồ thị co giãn tự động theo chiều ngang
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # --- Chân trang chú thích sử dụng ---
        st.markdown("""
        *   **Cập nhật**: Bấm nút **[🔄 Cập Nhật]** ở trên cùng để tải lại dữ liệu mới nhất (được lưu cache tối đa 5 phút để tránh quá tải API).
        *   **Độ trễ**: Dữ liệu lịch sử miễn phí từ `vnstock` có độ trễ nhất định so với thời gian thực từ 1 - 15 phút.
        *   **Không vẽ nến cuối**: Các đường VWAP tự động ẩn giá trị tại nến đang chạy cuối cùng để tránh bị nhiễu vẽ lại (repaint).
        """)
