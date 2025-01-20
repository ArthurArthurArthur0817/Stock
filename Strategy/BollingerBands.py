import yfinance as yf
import numpy as np
import pandas as pd
import talib  

def fetch_and_analyze_bollinger_bands(stock_ticker, start_date, end_date, window=5, num_std_dev=1):
    
    # 抓取股票數據
    data = yf.download(stock_ticker, start=start_date, end=end_date)

    # 檢查並轉換 'Close' 欄位為數值型
    if ('Close', stock_ticker) not in data.columns:
        print(f"數據中缺少 'Close' 列，無法計算移動平均！")
        return

    # 提取特定股票（如 AAPL）的 'Close' 列
    close_prices = data[('Close', stock_ticker)]


    if close_prices.isna().any():
        print("數據中包含缺失值，將自動刪除 NaN 行。")
        data = data.dropna(subset=[('Close', stock_ticker)])

    if data.empty:
        print(f"找不到股票代碼 {stock_ticker} 的數據，請確認代碼或日期是否正確。")
        return

    # 使用 talib 計算布林帶
    upper_band, middle_band, lower_band = talib.BBANDS(close_prices, timeperiod=window, nbdevup=num_std_dev, nbdevdn=num_std_dev, matype=0)

    # 將布林帶數據加入到 DataFrame 中
    data[('Moving Average', stock_ticker)] = middle_band
    data[('Upper Band', stock_ticker)] = upper_band
    data[('Lower Band', stock_ticker)] = lower_band

    # 刪除 NaN 行
    data = data[['Close', 'Moving Average', 'Upper Band', 'Lower Band']].dropna()

    # 設定買賣信號
    data['Signal'] = np.where(data[('Close', stock_ticker)] < data[('Lower Band', stock_ticker)], 1, 0)  # 買入信號
    data['Signal'] = np.where(data[('Close', stock_ticker)] > data[('Upper Band', stock_ticker)], -1, data['Signal'])  # 賣出信號

    # 顯示結果
    print("\n--- Bollinger Bands Strategy ---")
    print(data[['Close', 'Moving Average', 'Upper Band', 'Lower Band', 'Signal']].tail(20))  # 顯示最後10筆記錄

# 使用範例
if __name__ == "__main__":
    stock_ticker = "2330.TW"  # 指定股票代碼
    start_date = "2024-09-12"  # 開始日期
    end_date = "2024-09-30"    # 結束日期
    fetch_and_analyze_bollinger_bands(stock_ticker, start_date, end_date)
