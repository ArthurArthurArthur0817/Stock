from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db import get_connection
from trade import get_stock_info, process_trade
from news import fetch_news
import datetime
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
#==============================================================
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db import get_connection
from trade import get_stock_info, process_trade
from strategies import rsi  # 確保 strategies 內有 rsi.py
import subprocess
import os
import datetime
import importlib
from simulation import plot_stock_data, get_random_stock



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


@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    stock_info = session.get("stock_info")  # 嘗試從 session 取回上次選擇的股票
    current_price = None
    strategy_result = None  # **新增變數來儲存策略結果**

    now = datetime.datetime.now()
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=13, minute=30, second=0, microsecond=0)
    is_trading_time = start_time <= now <= end_time

    if request.method == 'POST':
        if 'get_stock_info' in request.form:
            stock_symbol = request.form['stock'].strip()
            if not stock_symbol.isdigit() or (len(stock_symbol) not in [4, 5, 6]):
                flash("Stock symbol must be a 4, 5, or 6-digit code representing a Taiwan stock.")
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time, strategy_result=None)

            stock_symbol = f"{stock_symbol}.TW"
            stock_info, error_message = get_stock_info(stock_symbol)
            if error_message:
                flash(error_message)
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time, strategy_result=None)

            session["stock_info"] = stock_info  # **將股票資訊存入 session**
        
        elif 'apply_strategy' in request.form:
            selected_strategy = request.form['strategy']
            investment_amount = request.form.get('investment_amount', 0)  # 取得投資金額
            strategy_module = f"strategies.{selected_strategy}"

            if stock_info and isinstance(stock_info, dict) and 'symbol' in stock_info:
                try:
                    strategy = importlib.import_module(strategy_module)
                    strategy_result = strategy.run(stock_info['symbol'] + ".TW", float(investment_amount))  # **傳入投資金額**
                except ModuleNotFoundError:
                    flash("Strategy module not found.")
                except AttributeError:
                    flash("Strategy module does not contain a 'run' function.")
            else:
                flash("Stock information is not available or incomplete.")

    return render_template('trade.html', stock_info=stock_info, is_trading_time=is_trading_time, strategy_result=strategy_result)


@app.route('/ai_analysis', methods=['POST'])
def ai_analysis():
    txt_path = "analysis_results.txt"

    # 檢查分析結果檔案是否存在
    if not os.path.exists(txt_path):
        return jsonify({"analysis_result": "❌ 找不到分析結果檔案！"})

    # 執行 Gemini 分析
    process = subprocess.run(["python", "gemini.py"], capture_output=True, text=True)

    # 如果執行失敗，返回錯誤訊息
    if process.returncode != 0:
        error_msg = f"⚠️ 執行 gemini.py 失敗：{process.stderr}"
        print(error_msg)
        return jsonify({"analysis_result": error_msg})

    # 取得 Gemini 分析結果
    analysis_result = process.stdout
    print(f"✅ AI 分析結果：\n{analysis_result}")

    # 以 JSON 格式返回
    return jsonify({"analysis_result": analysis_result})

@app.route('/roi')
def roi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('roi.html')

#相關新聞
# (目前以台積電為例)
@app.route('/news')
def news():
    """ 顯示新聞頁面 """
    news_list = fetch_news()  # 獲取新聞

    if not news_list:
        return render_template('news.html', news_list=[], error="⚠️ 目前沒有可用新聞，請稍後再試！")

    return render_template('news.html', news_list=news_list)


@app.route('/simulation')
def simulation():
    if 'stock_code' not in session:
        session['stock_code'] = get_random_stock()  # 隨機選一支股票
    session['start_index'] = 0  # 初始 index

    plot_path = plot_stock_data(session['stock_code'], session['start_index'])
    if not plot_path:
        return "無法獲取股票數據，請稍後再試"

    return render_template('simulation.html', plot_path=plot_path, stock_code=session['stock_code'])

@app.route('/next_day')
def next_day():
    """確保繪圖函數在 Flask 主線程內執行"""
    with app.app_context():
        session['start_index'] += 1
        plot_path = plot_stock_data(session['stock_code'], session['start_index'])

    if not plot_path:
        return jsonify({'error': '已超出資料範圍'})

    return jsonify({'plot_path': plot_path})




if __name__ == '__main__':
    app.run(debug=True)
