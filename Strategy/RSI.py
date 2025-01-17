import yfinance as yf
import talib
import pandas as pd

def fetch_and_analyze_rsi(stock_ticker, start_date, end_date, rsi_period=14, overbought=70, oversold=30):
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
    
    # 計算 RSI
    data['RSI'] = talib.RSI(close_prices.values, timeperiod=5)

    # 定義買賣信號
    data['Signal'] = 0
    data.loc[data['RSI'] > overbought, 'Signal'] = -1  # 賣出信號
    data.loc[data['RSI'] < oversold, 'Signal'] = 1    # 買入信號

     
      
     
    # 顯示結果
    print("\n--- RSI Analysis ---")
    print(data[['Close', 'RSI', 'Signal']].tail(10))  # 顯示最後10筆記錄

# 使用範例
if __name__ == "__main__":
    stock_ticker = "2330.TW"  # 指定股票代碼，例如 AAPL
    start_date = "2024-09-12"  # 開始日期
    end_date = "2024-09-30"    # 結束日期

    fetch_and_analyze_rsi(stock_ticker, start_date, end_date)
