import yfinance as yf
import talib
import pandas as pd

def fetch_and_analyze_macd(stock_ticker, start_date, end_date, fast_period=12, slow_period=26, signal_period=9):
    # 抓取股票數據
    data = yf.download(stock_ticker, start=start_date, end=end_date)
    
    if data.empty:
        print(f"No data found for {stock_ticker}.")
        return
    
    # 確保 'Close' 欄位是 Series 類型
    close_prices = data['Close'].squeeze()  # 將 DataFrame 或單列數據轉為 Series

    # 檢查類型並轉換為 numpy.ndarray
    if not isinstance(close_prices, pd.Series):
        close_prices = pd.Series(close_prices)
    
    # 計算 MACD 指標
    macd, macd_signal, macd_hist = talib.MACD(
        close_prices.values, 
        fastperiod=fast_period, 
        slowperiod=slow_period, 
        signalperiod=signal_period
    )

    # 將 MACD 結果加入數據表
    data['MACD'] = macd
    data['MACD_Signal'] = macd_signal
    data['MACD_Hist'] = macd_hist

    # 定義買賣信號
    data['Signal'] = 0  # 初始信號為 0 (不變)
    data.loc[(data['MACD'] > data['MACD_Signal']), 'Signal'] = 1   # 買入信號
    data.loc[(data['MACD'] < data['MACD_Signal']), 'Signal'] = -1  # 賣出信號

    # 顯示結果
    print("\n--- MACD Analysis ---")
    print(data[['Close', 'MACD', 'MACD_Signal', 'Signal']].tail(10))  # 顯示最後10筆記錄

# 使用範例
if __name__ == "__main__":
    stock_ticker = "2330.TW"  # 指定股票代碼，例如 AAPL
    start_date = "2024-01-01"  # 開始日期
    end_date = "2024-12-31"    # 結束日期

    fetch_and_analyze_macd(stock_ticker, start_date, end_date)
