# -*- coding: utf-8 -*-
"""
=============================================================================
MODULE: vwap.py
TYPE: Feature Engineering
PURPOSE: Calculate multi-period VWAP (Session/Day, Week, Month, Quarter, Year)
GOVERNANCE: Stable
LAST UPDATED: 2026-08-14
=============================================================================
"""

import pandas as pd
import numpy as np

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
