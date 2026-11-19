from flask import Flask, request, jsonify
import sqlite3
import time
import telebot
import threading
import os
from collections import defaultdict

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing") 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- ЗАЩИТА ОТ СПАМА ---
request_counts = defaultdict(list)

def is_rate_limited(ip):
    now = time.time()
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 1.0]
    if len(request_counts[ip]) > 5:
        return True
    request_counts[ip].append(now)
    return False

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # ТЕПЕРЬ ЗДЕСЬ ЕСТЬ КОЛОНКА breed
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY, satiety INTEGER, coins INTEGER, breed TEXT, last_update INTEGER, is_notified INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- CORS ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Secret-Key')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    return response

@app.route('/update', methods=['OPTIONS'])
def options_update():
    return jsonify({"status": "ok"}), 200

# --- API ДЛЯ СОХРАНЕНИЯ ---
@app.route('/update', methods=['POST'])
def update_progress():
    ip = request.remote_addr
    
    if is_rate_limited(ip):
        return jsonify({"error": "Too Many Requests"}), 429

    secret_key = request.headers.get('X-Secret-Key')
    if secret_key != 'MySuperSecretKey_123':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    try:
        user_id = str(data.get('user_id'))
        satiety = int(data.get('satiety'))
        client_coins = int(data.get('coins', 0))
        breed = str(data.get('breed', 'orange')) # <--- ЧИТАЕМ ПОРОДУ
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request"}), 400

    last_time = int(time.time())

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # ПРОВЕРКА НА НАКРУТКУ
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    final_coins = client_coins
    if row:
        server_coins = row[0]
        if client_coins > server_coins + 50: 
            final_coins = server_coins
    
    # СОХРАНЕНИЕ (с breed)
    c.execute('''INSERT INTO users (user_id, satiety, coins, breed, last_update, is_notified) 
                 VALUES (?, ?, ?, ?, ?, 0)
                 ON CONFLICT(user_id) DO UPDATE SET 
                 satiety=excluded.satiety, coins=excluded.coins, breed=excluded.breed, last_update=excluded.last_update, is_notified=0''', 
              (user_id, satiety, final_coins, breed, last_time))
    
    conn.commit()
    conn.close()
    
    app.logger.info(f"📥 Игрок: {user_id} | Монеты: {final_coins} | Порода: {breed}")
    return jsonify({"status": "ok"}), 200

# --- API ДЛЯ ЗАГРУЗКИ ---
@app.route('/load/<user_id>', methods=['GET'])
def load_progress(user_id):
    secret_key = request.headers.get('X-Secret-Key')
    if secret_key != 'MySuperSecretKey_123':
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # БЕРЕМ ПОРОДУ ИЗ БАЗЫ
    c.execute("SELECT satiety, coins, breed FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if row:
        app.logger.info(f"☁️ Загрузка для {user_id}: {row[0]}% сытости, {row[1]} монет, порода: {row[2]}")
        return jsonify({"satiety": row[0], "coins": row[1], "breed": row[2]}), 200
    else:
        return jsonify({"error": "User not found"}), 404

# --- ФОНОВАЯ ПРОВЕРКА ---
def check_hunger():
    while True:
        time.sleep(60) 
        current_time = int(time.time())
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT user_id, satiety, last_update FROM users WHERE is_notified = 0")
        users = c.fetchall()
        
        for user in users:
            user_id, satiety, last_update = user
            time_passed = current_time - last_update
            
            if time_passed > 300: 
                try:
                    bot.send_message(user_id, "🐈 Твой котик голодает! Зайди в игру и покорми его.")
                    c.execute("UPDATE users SET is_notified = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
                except Exception as e:
                    c.execute("UPDATE users SET is_notified = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
        
        conn.close()

threading.Thread(target=check_hunger, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
