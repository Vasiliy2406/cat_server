from flask import Flask, request, jsonify
import sqlite3
import time
import telebot
import threading
import os

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ОШИБКА: Переменная BOT_TOKEN не найдена в настройках Render!")
    raise ValueError("BOT_TOKEN is missing") 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY, satiety INTEGER, last_update INTEGER, is_notified INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- БЕЗОПАСНОСТЬ И CORS ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    # Разрешаем браузеру отправлять наш секретный заголовок
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Secret-Key')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    return response

@app.route('/update', methods=['OPTIONS'])
def options_update():
    return jsonify({"status": "ok"}), 200

# --- API ДЛЯ ИГРЫ ---
@app.route('/update', methods=['POST'])
def update_progress():
    # 1. ПРОВЕРКА СЕКРЕТНОГО КЛЮЧА
    secret_key = request.headers.get('X-Secret-Key')
    if secret_key != 'MySuperSecretKey_123': # <--- Твой пароль
        print(f"⚠️ Попытка взлома! Пришел ключ: {secret_key}")
        return jsonify({"error": "Unauthorized"}), 401

    # 2. ПРИЕМ ДАННЫХ
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    user_id = str(data.get('user_id'))
    satiety = int(data.get('satiety'))
    last_time = int(time.time())

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO users (user_id, satiety, last_update, is_notified) 
                 VALUES (?, ?, ?, 0)
                 ON CONFLICT(user_id) DO UPDATE SET 
                 satiety=excluded.satiety, last_update=excluded.last_update, is_notified=0''', 
              (user_id, satiety, last_time))
    
    conn.commit()
    conn.close()
    print(f"📥 Обновление от {user_id}: сытость {satiety}%")
    return jsonify({"status": "ok"}), 200

# --- ФОНОВАЯ ПРОВЕРКА (Уведомления) ---
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
                    print(f"✉️ Уведомление отправлено игроку {user_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки для {user_id}: {e}")
                    c.execute("UPDATE users SET is_notified = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
        
        conn.close()

threading.Thread(target=check_hunger, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
