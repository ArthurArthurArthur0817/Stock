from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection
from trade import get_stock_info, process_trade
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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
                return redirect(url_for('account'))
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
            flash("Registration successful. Please log in.")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    return render_template('register.html')






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
    
    stock_info = None  # 用來存放查詢結果
    current_price = None  # 目前價格

    # 確定交易時間（9:00 AM 到 1:30 PM）
    now = datetime.datetime.now()
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=23, minute=30, second=0, microsecond=0)
    is_trading_time = start_time <= now <= end_time

    if request.method == 'POST':
        if 'get_stock_info' in request.form:  # 查詢股票資訊
            stock_symbol = request.form['stock'].strip()  # 去除多餘空白
            
            # 檢查股票代碼是否為 4 位數字
            if not stock_symbol.isdigit() or len(stock_symbol) != 4:
                flash("Stock symbol must be a 4-digit code representing a Taiwan stock.")
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time)
            
            # 將股票代碼轉換為 Yahoo Finance 格式
            stock_symbol = f"{stock_symbol}.TW"
            
            # 取得股票資訊
            stock_info, error_message = get_stock_info(stock_symbol)
            if error_message:
                flash(error_message)
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time)

        elif 'submit_trade' in request.form:  # 提交交易
            stock_symbol = request.form['stock'].strip()
            user_price = float(request.form['price'])  # 使用者設定的價格
            quantity = int(request.form['quantity'])
            trade_type = request.form['type']

            # 確保股票代碼為有效格式
            if not stock_symbol.endswith(".TW"):
                stock_symbol = f"{stock_symbol}.TW"

            # 驗證交易時間
            if not is_trading_time:
                flash("Currently not within trading hours. Trading is only allowed from 9:00 AM to 1:30 PM.")
                return render_template('trade.html', stock_info=stock_info, is_trading_time=is_trading_time)

            # 再次檢查股票資訊是否存在
            stock_info, error_message = get_stock_info(stock_symbol)
            if error_message:
                flash(error_message)
                return render_template('trade.html', stock_info=None, is_trading_time=is_trading_time)

            current_price = stock_info["current_price"]

            # 驗證價格是否與使用者輸入匹配
            if user_price == current_price:
                # 處理交易邏輯
                if process_trade(session['user_id'], stock_symbol, quantity, user_price, trade_type):
                    flash("Transaction completed successfully.")
                else:
                    flash("Transaction failed. Please check your input or balance.")
            else:
                flash(f"Price mismatch. Current price: {current_price}. Your set price: {user_price}")
    
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

if __name__ == '__main__':
    app.run(debug=True)
