# -*- coding: utf-8 -*-
"""
=============================================================================
MODULE: fetch.py
TYPE: Data Provider
PURPOSE: Fetch historical stock data with VCI/KBS fallback logic and GMT+7 time
GOVERNANCE: Stable
LAST UPDATED: 2026-08-14
=============================================================================
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone

try:
    from vnstock_data import Quote
except ImportError:
    from vnstock.api.quote import Quote

# Múi giờ Việt Nam (GMT+7)
vn_tz = timezone(timedelta(hours=7))

@st.cache_data(ttl=300)  # Cache trong 5 phút
def fetch_stock_data(symbol: str, timeframe: str) -> dict:
    """Tải dữ liệu lịch sử giá từ vnstock."""
    symbol = symbol.upper().strip()
    if timeframe == "H1":
        timeframe = "1H"
    elif timeframe == "D":
        timeframe = "1D"
        
    today = datetime.now(vn_tz)
    
    # Tối ưu hóa: Nếu là khung 5m hoặc 15m, chỉ tải 3 tháng để tránh quá nặng
    if timeframe in ["5m", "15m"]:
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    else:
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d") # 12 tháng
        
    end_date = today.strftime("%Y-%m-%d")
    interval = timeframe # "5m", "15m", "1H", or "1D"
    
    try:
        # Sử dụng nguồn VCI trước (nhanh và ổn định cho lịch sử)
        q = Quote(symbol=symbol, source='VCI')
        df = q.history(start=start_date, end=end_date, interval=interval)
    except Exception as e_vci:
        # Nếu VCI bị chặn kết nối ở Cloud, tự động fallback sang KBS làm dự phòng
        try:
            q = Quote(symbol=symbol, source='kbs')
            df = q.history(start=start_date, end=end_date, interval=interval)
        except Exception as e_kbs:
            st.error(f"Lỗi tải dữ liệu cho mã {symbol} từ cả VCI ({e_vci}) và KBS ({e_kbs})")
            return {"df": pd.DataFrame(), "fetch_time": datetime.now(vn_tz)}
            
    try:
        if df is None or df.empty:
            return {"df": pd.DataFrame(), "fetch_time": datetime.now(vn_tz)}
            
        # Đảm bảo cột thời gian là datetime
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        # Chuyển đổi tên các cột sang kiểu chuẩn để dễ xử lý
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        return {"df": df, "fetch_time": datetime.now(vn_tz)}
    except Exception as e:
        st.error(f"Lỗi xử lý dữ liệu cho mã {symbol}: {e}")
        return {"df": pd.DataFrame(), "fetch_time": datetime.now(vn_tz)}
