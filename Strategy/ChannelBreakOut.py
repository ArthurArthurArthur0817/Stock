import yfinance as yf
import talib
import pandas as pd
import numpy as np

def fetch_and_analyze_channel_breakout(stock_ticker, start_date, end_date, period=5):
    # 抓取股票數據
    data = yf.download(stock_ticker, start=start_date, end=end_date)
    

    if data.empty:
        print(f"No data found for {stock_ticker}.")
        return

    # 展開 MultiIndex，只選取 Price 層級的列名
    data.columns = data.columns.get_level_values(0)

    # 確保需要的列名存在
    required_columns = ['High', 'Low', 'Close']
    if not all(col in data.columns for col in required_columns):
        print(f"Missing required columns: {', '.join(col for col in required_columns if col not in data.columns)}")
        return

     
   
    # 檢查 NaN 值，並丟棄包含 NaN 的行
    data = data.dropna(subset=['High', 'Low'])

    # 確保 'High' 和 'Low' 是 pandas.Series 並轉為 numpy.ndarray
    high_prices = data['High'].values  # 轉為 numpy.ndarray
    low_prices = data['Low'].values   # 轉為 numpy.ndarray

    # 確保 high_prices 和 low_prices 是一維陣列
    high_prices = np.asarray(data['High']).flatten()  # 強制轉為一維
    low_prices = np.asarray(data['Low']).flatten()    # 強制轉為一維

    data['High_Channel'] = talib.MAX(high_prices, timeperiod=period)
    data['Low_Channel'] = talib.MIN(low_prices, timeperiod=period)

   


    # 確保通道數據已完整 (過濾掉含有 NaN 的行)
    data.dropna(subset=['High_Channel', 'Low_Channel'], inplace=True)

    # 定義信號
    data['Signal'] = 0
    data.loc[data['Close'] > data['High_Channel'].shift(1), 'Signal'] = 1  # 買入信號,Close 大於前一天的 High_Channel 
    data.loc[data['Close'] < data['Low_Channel'].shift(1), 'Signal'] = -1 # 賣出信號,Close 小於前一天的 Low_Channel

    # 計算持倉：連續持倉的狀態
    data['Position'] = data['Signal'].replace(0, np.nan).ffill()


    # 顯示結果
    print("\n--- Channel Breakout Strategy ---")
    print(data[['Close', 'High_Channel', 'Low_Channel', 'Signal', 'Position']].tail(20)) 

# 使用範例
if __name__ == "__main__":
    stock_ticker = "2330.TW"  # 指定股票代碼
    start_date = "2024-09-12"  # 開始日期
    end_date = "2024-09-30"    # 結束日期

    fetch_and_analyze_channel_breakout(stock_ticker, start_date, end_date)
