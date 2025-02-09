from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db import get_connection
from trade import get_stock_info, process_trade
import datetime
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 計算風險分數的函式
def calculate_risk_score(answers):
    """計算使用者的投資風險評估分數"""
    score = sum(map(int, answers.values()))  # 將所有選項數值加總

    # 根據分數分類風險類型
    if score <= 10:
        return "保守型投資者", -1
    elif 11 <= score <= 18:
        return "穩健型投資者", 0
    else:
        return "積極型投資者", 1
        
# 登入頁面
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user['id']
                return redirect(url_for('main'))
            else:
                flash("Invalid username or password.")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    return render_template('login.html')

# 註冊頁面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            connection.commit()
            #flash("Registration successful. Please log in.")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    return render_template('register.html')


@app.route('/main')
def main():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('main.html')




# 用戶帳戶頁面
@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 查詢用戶資產
        cursor.execute("SELECT balance FROM users WHERE id = %s", (session['user_id'],))
        user_balance = cursor.fetchone()
        
        if user_balance is None:
            flash('No portfolio found for this user. Please check your data.')
            return redirect(url_for('account'))

        user_balance = user_balance['balance']
        
        # 查詢用戶持有的股票並合併相同股票的數量
        cursor.execute("""
            SELECT stock, SUM(quantity) as total_quantity
            FROM portfolios
            WHERE user_id = %s
            GROUP BY stock
        """, (session['user_id'],))
        stocks = cursor.fetchall()
        
        # 獲取 portfolios 表中的數據
        cursor.execute("SELECT * FROM portfolios WHERE user_id = %s", (session['user_id'],))
        portfolios = cursor.fetchall()

        # 為每支股票添加即時價格
        for portfolio in portfolios:
            stock_symbol = portfolio['stock']
            stock_info, error = get_stock_info(stock_symbol)
            portfolio['price'] = stock_info['current_price'] if stock_info else None
            
            
        
            
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('account'))
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return render_template('account.html', balance=user_balance, stocks=stocks, portfolios=portfolios)




@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    stock_info = None
    current_price = None

    now = datetime.datetime.now()
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=23, minute=30, second=0, microsecond=0)
    is_trading_time = start_time <= now <= end_time

    if request.method == 'POST':
        if 'get_stock_info' in request.form:
            stock_symbol = request.form['stock'].strip()
            # 更新股票代碼驗證：允許 4、5 或 6 位數字
            if not stock_symbol.isdigit() or (len(stock_symbol) not in [4, 5, 6]):
                flash("Stock symbol must be a 4, 5, or 6-digit code representing a Taiwan stock.")
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time)

            stock_symbol = f"{stock_symbol}.TW"
            stock_info, error_message = get_stock_info(stock_symbol)
            if error_message:
                flash(error_message)
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time)

        elif 'submit_trade' in request.form:
            stock_symbol = request.form['stock'].strip()
            user_price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            trade_type = request.form['type']
            current_price = float(request.form['current_price'])

            if not is_trading_time:
                flash("Currently not within trading hours. Trading is only allowed from 9:00 AM to 1:30 PM.")
                return render_template('trade.html', stock_info=stock_info, is_trading_time=is_trading_time)

            price_tolerance = 0.01
            if not (current_price * (1 - price_tolerance) <= user_price <= current_price * (1 + price_tolerance)):
                flash(f"Price mismatch. Current price: {current_price}. Your set price: {user_price}")
                return render_template('trade.html', stock_info=stock_info, is_trading_time=is_trading_time)

            success, message = process_trade(session['user_id'], stock_symbol, quantity, user_price, trade_type)
            if success:
                flash("Transaction completed successfully.")
            else:
                flash(message)

    return render_template('trade.html', stock_info=stock_info, is_trading_time=is_trading_time)


@app.route('/transaction')
def transaction():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # 獲取 transaction 表中的數據
    cursor.execute("SELECT stock, quantity, price, transaction_time, type FROM transactions")
    transactions = cursor.fetchall()

    cursor.close()
    connection.close()
    return render_template('transaction.html', transactions=transactions)



@app.route('/teach')
def teach():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('teach.html')

@app.route('/risk')
def risk():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('risk.html')

@app.route('/result', methods=['POST'])
def result():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    answers = request.form
    stock_type = request.form.get('stock_type', "未選擇")

    risk_type, risk_value = calculate_risk_score(answers)

    try:
        with open("risk_type.txt", "w", encoding="utf-8") as file:
            file.write(f"{stock_type},{risk_value}\n")
    except Exception as e:
        'print(f"寫入 risk_type.txt 失敗: {e}")'

    return render_template("risk_result.html", risk_type=risk_type)



# 計算 CAGR
def calculate_cagr(stock_code):
    stock = yf.Ticker(stock_code)
    df = stock.history(period="max")  # 取得所有歷史數據

    if df.empty:
        return None  # 沒有數據則回傳 None

    start_price = df["Close"].iloc[0]  # 最早的收盤價
    end_price = df["Close"].iloc[-1]  # 最新的收盤價
    years = (df.index[-1] - df.index[0]).days / 365  # 計算經過的年數
    cagr = ((end_price / start_price) ** (1 / years)) - 1  # CAGR 計算公式
    return cagr * 100  # 轉成百分比

# 預測未來收益
def predict_future_value(initial_investment, cagr, months):
    years = months / 12  # 換算成年
    final_value = initial_investment * ((1 + cagr / 100) ** years)  # 預測最終價值
    profit = final_value - initial_investment  # 計算總收益
    return final_value, profit

# 將月份轉換為 yfinance 可接受的 period 格式
def get_valid_period(months):
    if months <= 1:
        return "1mo"
    elif months <= 3:
        return "3mo"
    elif months <= 6:
        return "6mo"
    elif months <= 12:
        return "1y"
    elif months <= 24:
        return "2y"
    elif months <= 60:
        return "5y"
    elif months <= 120:
        return "10y"
    else:
        return "max"

# 繪製 K 線圖
def plot_comparison(stock_code, months):
    period = get_valid_period(months)
    stock = yf.Ticker(stock_code)
    market = yf.Ticker("^TWII")  # 台灣加權指數

    df_stock = stock.history(period=period)
    df_market = market.history(period=period)

    print(df_stock.head())  # 檢查是否有資料
    print(df_market.head())  # 檢查是否有資料

    if df_stock.empty or df_market.empty:
        return None  # 沒數據就不畫圖

    df_stock["Return"] = df_stock["Close"].pct_change().cumsum() * 100
    df_market["Return"] = df_market["Close"].pct_change().cumsum() * 100

    plt.figure(figsize=(8, 5))
    plt.plot(df_stock.index, df_stock["Return"], label=f"{stock_code} (%)", color="blue")
    plt.plot(df_market.index, df_market["Return"], label="^TWII (%)", color="red")
    plt.xlabel("Period")
    plt.ylabel("Price change (%)")
    plt.title(f"{stock_code} vs ^TWII")
    plt.legend()
    plt.grid()

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    return f"data:image/png;base64,{plot_url}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    stock_code = data.get("stock_code")
    initial_investment = float(data.get("initial_investment"))
    months = int(data.get("months"))

    cagr = calculate_cagr(stock_code)
    if cagr is None:
        return jsonify({"error": "股票代號無效或無數據"})

    final_value, profit = predict_future_value(initial_investment, cagr, months)
    plot_url = plot_comparison(stock_code, months)

    return jsonify({
        "cagr": round(cagr, 2),
        "final_value": round(final_value, 2),
        "profit": round(profit, 2),
        "plot_url": plot_url
    })

@app.route('/roi')
def roi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('roi.html')


if __name__ == '__main__':
    app.run(debug=True)
