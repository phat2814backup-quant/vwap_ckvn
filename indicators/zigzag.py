# -*- coding: utf-8 -*-
"""
=============================================================================
MODULE: zigzag.py
TYPE: Feature Engineering
PURPOSE: Calculate MT5 ZigZag (Depth, Deviation, Backstep) swing points
GOVERNANCE: Stable
LAST UPDATED: 2026-08-14
=============================================================================
"""

import pandas as pd
import numpy as np

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
