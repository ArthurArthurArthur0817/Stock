import yfinance as yf
import numpy as np
import pandas as pd
import talib  # 引入 TA-Lib

def fetch_and_analyze_bollinger_bands(stock_ticker, start_date, end_date, window=5, num_std_dev=1, period=5):
    
    # 抓取股票數據
    data = yf.download(stock_ticker, start=start_date, end=end_date)
    

    # 檢查並轉換 'Close' 欄位為數值型
    close_column = ('Close', stock_ticker)
    if close_column not in data.columns:
        print(f"數據中缺少 'Close' 列，無法計算移動平均！")
        return

    

    if data[close_column].isna().any():  # 使用 .any() 來檢查是否有缺失值
        print("數據中包含缺失值，將自動刪除 NaN 行。")
        # 檢查並刪除 NaN 行
        data = data.dropna(subset=[close_column])

    if data.empty:
        print(f"找不到股票代碼 {stock_ticker} 的數據，請確認代碼或日期是否正確。")
        return

    # 使用 talib 計算布林帶
    close_prices = data[close_column]
    upper_band, middle_band, lower_band = talib.BBANDS(close_prices, timeperiod=window, nbdevup=num_std_dev, nbdevdn=num_std_dev, matype=0)

    # 將布林帶數據加入到 DataFrame 中
    data[('Moving Average', stock_ticker)] = middle_band
    data[('Upper Band', stock_ticker)] = upper_band
    data[('Lower Band', stock_ticker)] = lower_band

    # 確保 'Volume' 列存在並處理
    volume_column = ('Volume', stock_ticker)
    if volume_column not in data.columns:
        print(f"警告：資料中未找到 'Volume' 列。請檢查下載的數據是否正確。")
        return

    volume = data[volume_column]
    
    # 計算過去 period 天的平均成交量
    data[('Avg Volume', stock_ticker)] = volume.rolling(window=period).mean()

    # 設定買賣信號，考慮成交量
    data['Signal'] = 0  # 預設無信號

    # 使用 MultiIndex 正確處理比較操作
    data.loc[(data[close_column] < data[('Lower Band', stock_ticker)]) & 
             (data[volume_column] > data[('Avg Volume', stock_ticker)]), 'Signal'] = 1  # 買入信號

    data.loc[(data[close_column] > data[('Upper Band', stock_ticker)]) & 
             (data[volume_column] > data[('Avg Volume', stock_ticker)]), 'Signal'] = -1  # 賣出信號

    # 顯示結果
    print("\n--- Bollinger Bands Strategy with Dynamic Volume Threshold ---")
    print(data[['Close', 'Moving Average', 'Upper Band', 'Lower Band', 'Volume', 'Avg Volume', 'Signal']].tail(20))  # 顯示最後20筆記錄

# 使用範例
if __name__ == "__main__":
    stock_ticker = "2330.TW"  # 指定股票代碼
    start_date = "2024-09-12"  # 開始日期
    end_date = "2024-09-30"    # 結束日期
    fetch_and_analyze_bollinger_bands(stock_ticker, start_date, end_date)
