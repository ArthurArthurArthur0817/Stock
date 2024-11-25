from db import get_connection

def process_trade(user_id, stock, quantity, price, trade_type):
    """
    執行股票交易邏輯，包含買入和賣出。
    :param user_id: 當前用戶ID
    :param stock: 股票名稱
    :param quantity: 交易數量
    :param price: 單價
    :param trade_type: 交易類型 ('BUY' 或 'SELL')
    :return: 成功返回 True，失敗返回 False
    """
    try:
        connection = get_connection()
        cursor = connection.cursor()

        if trade_type == 'BUY':
            total_cost = quantity * price
            # 確認餘額是否足夠
            cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
            balance = cursor.fetchone()[0]
            if balance < total_cost:
                return False

            # 更新用戶餘額
            cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total_cost, user_id))
            # 更新或插入持有股票
            cursor.execute(
                "INSERT INTO portfolios (user_id, stock, quantity) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE quantity = quantity + %s",
                (user_id, stock, quantity, quantity)
            )
        elif trade_type == 'SELL':
            # 確認持有股票數量是否足夠
            cursor.execute("SELECT quantity FROM portfolios WHERE user_id = %s AND stock = %s", (user_id, stock))
            current_quantity = cursor.fetchone()
            if not current_quantity or current_quantity[0] < quantity:
                return False

            total_earnings = quantity * price
            # 更新用戶餘額
            cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (total_earnings, user_id))
            # 更新持有股票數量
            cursor.execute(
                "UPDATE portfolios SET quantity = quantity - %s WHERE user_id = %s AND stock = %s",
                (quantity, user_id, stock)
            )
        else:
            return False

        # 記錄交易
        cursor.execute(
            "INSERT INTO transactions (user_id, stock, quantity, price, type) VALUES (%s, %s, %s, %s, %s)",
            (user_id, stock, quantity, price, trade_type)
        )
        connection.commit()
        return True
    except Exception as e:
        print(f"Error in process_trade: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
