# -*- coding: utf-8 -*-
"""
=============================================================================
MODULE: mbfx.py
TYPE: Feature Engineering
PURPOSE: Calculate MBFX Timing Indicator (DEMA-based oscillation & trend filter)
GOVERNANCE: Stable
LAST UPDATED: 2026-08-15
=============================================================================
"""

import pandas as pd
import numpy as np

def calculate_mbfx(df: pd.DataFrame, length: int = 7, filter_val: float = 0.2) -> tuple:
    """
    Tính toán chỉ báo MBFX Timing Indicator từ dữ liệu OHLC.
    Trả về: (MBFX_Series, Color_Series)
    Color_Series: 0 (Lime: tăng), 1 (Red: giảm), 2 (Gold: đi ngang)
    """
    n = len(df)
    mbfx = np.zeros(n)
    color_idx = np.zeros(n)
    
    if n == 0:
        return pd.Series(mbfx), pd.Series(color_idx)
        
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # ld80 = 100 * (H + L + C) / 3
    ld80 = 100.0 * (high + low + close) / 3.0
    
    # ld32 = ld80 - ld80_prev
    ld32 = np.zeros(n)
    ld32[1:] = ld80[1:] - ld80[:-1]
    
    # Khởi tạo các biến trung gian
    v112 = np.zeros(n)
    v120 = np.zeros(n)
    v128 = np.zeros(n)
    v208 = np.zeros(n)
    v136 = np.zeros(n)
    v152 = np.zeros(n)
    v56 = np.zeros(n)
    
    v160 = np.zeros(n)
    v168 = np.zeros(n)
    v176 = np.zeros(n)
    v184 = np.zeros(n)
    v192 = np.zeros(n)
    v200 = np.zeros(n)
    v72 = np.zeros(n)
    
    ld96 = 3.0 / (length + 2)
    ld104 = 1.0 - ld96
    
    mbfx[0] = 50.0
    color_idx[0] = 2 # Sideways
    
    for i in range(1, n):
        # Smoothing Layer 1
        v112[i] = ld104 * v112[i-1] + ld96 * ld32[i]
        v120[i] = ld96 * v112[i] + ld104 * v120[i-1]
        ld40 = 1.5 * v112[i] - v120[i] / 2.0
        
        # Smoothing Layer 2
        v128[i] = ld104 * v128[i-1] + ld96 * ld40
        v208[i] = ld96 * v128[i] + ld104 * v208[i-1]
        ld48 = 1.5 * v128[i] - v208[i] / 2.0
        
        # Smoothing Layer 3
        v136[i] = ld104 * v136[i-1] + ld96 * ld48
        v152[i] = ld96 * v136[i] + ld104 * v152[i-1]
        v56[i] = 1.5 * v136[i] - v152[i] / 2.0
        
        # Volatility calculation
        v160[i] = ld104 * v160[i-1] + ld96 * abs(ld32[i])
        v168[i] = ld96 * v160[i] + ld104 * v168[i-1]
        ld64 = 1.5 * v160[i] - v168[i] / 2.0
        
        # Volatility smoothing
        v176[i] = ld104 * v176[i-1] + ld96 * ld64
        v184[i] = ld96 * v176[i] + ld104 * v184[i-1]
        ld144 = 1.5 * v176[i] - v184[i] / 2.0
        
        v192[i] = ld104 * v192[i-1] + ld96 * ld144
        v200[i] = ld96 * v192[i] + ld104 * v200[i-1]
        v72[i] = 1.5 * v192[i] - v200[i] / 2.0
        
        if v72[i] > 1e-10:
            val = 50.0 * (v56[i] / v72[i] + 1.0)
            mbfx[i] = max(0.0, min(100.0, val))
        else:
            mbfx[i] = mbfx[i-1]
            
        if mbfx[i] > mbfx[i-1] + filter_val:
            color_idx[i] = 0 # Lime
        elif mbfx[i] < mbfx[i-1] - filter_val:
            color_idx[i] = 1 # Red
        else:
            color_idx[i] = 2 # Gold
            
    return pd.Series(mbfx, index=df.index), pd.Series(color_idx, index=df.index)
