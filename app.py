from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_connection
from trade import process_trade

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

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 查詢用戶的資產（從 users 表中取得 balance 欄位）
        cursor.execute("SELECT balance FROM users WHERE id = %s", (session['user_id'],))
        user_balance = cursor.fetchone()
        
        if user_balance is None:
            flash('No portfolio found for this user. Please check your data.')
            return redirect(url_for('account'))  # 或其他適當的處理

        user_balance = user_balance['balance']
        
        # 查詢用戶持有的股票（仍然從 portfolios 表中取得）
        cursor.execute("SELECT stock, quantity FROM portfolios WHERE user_id = %s", (session['user_id'],))
        stocks = cursor.fetchall()
        
        if not stocks:
            flash('No stocks found in your portfolio.')
        
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('portfolio'))  # 或其他適當的錯誤處理頁面
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return render_template('account.html', balance=user_balance, stocks=stocks)




# 交易頁面
@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        stock = request.form['stock']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        trade_type = request.form['type']  # BUY or SELL
        if process_trade(session['user_id'], stock, quantity, price, trade_type):
            flash("Transaction successful!")
        else:
            flash("Transaction failed. Please check your input or balance.")
        return redirect(url_for('account'))
    return render_template('trade.html')

if __name__ == '__main__':
    app.run(debug=True)
