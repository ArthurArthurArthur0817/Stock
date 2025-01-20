import yfinance as yf
import pandas as pd

def fetch_and_analyze_greedy(stock_ticker, start_date, end_date):
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
    
    # 添加貪婪策略的信號
    data['Signal'] = 0
    data['Change'] = data['Close'].diff()  # 計算每日收盤價變化

    # 定義買入、賣出、不變的信號
    data.loc[data['Change'] > 0, 'Signal'] = 1   # 當天價格上漲，買入
    data.loc[data['Change'] < 0, 'Signal'] = -1  # 當天價格下跌，賣出
    data.loc[data['Change'] == 0, 'Signal'] = 0  # 價格不變，保持不動

    # 顯示結果
    print("\n--- Greedy Strategy Analysis ---")
    print(data[['Close', 'Change', 'Signal']].tail(10))  # 顯示最後10筆記錄

# 使用範例
if __name__ == "__main__":
    stock_ticker = "2330.TW"  # 指定股票代碼，例如 2330.TW
    start_date = "2024-09-12"  # 開始日期
    end_date = "2024-09-30"    # 結束日期

    fetch_and_analyze_greedy(stock_ticker, start_date, end_date)
