from flask import Flask, request, jsonify
import sqlite3
import time
import telebot
import threading
import os

# --- НАСТРОЙКИ ---
# Берем токен из переменных окружения Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ОШИБКА: Переменная BOT_TOKEN не найдена в настройках Render!")
    # Специально вызываем ошибку, чтобы Render показал, что не так
    raise ValueError("BOT_TOKEN is missing") 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Таблица: user_id, satiety, last_update, is_notified
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY, satiety INTEGER, last_update INTEGER, is_notified INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- API ДЛЯ ИГРЫ ---
@app.route('/update', methods=['POST'])
def update_progress():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    user_id = str(data.get('user_id'))
    satiety = int(data.get('satiety'))
    last_time = int(time.time())

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Если пользователь уже есть, обновляем данные. Если нет - создаем.
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
        time.sleep(60) # Проверяем раз в минуту (для теста)
        current_time = int(time.time())
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Ищем тех, кому еще не отправляли уведомление
        c.execute("SELECT user_id, satiety, last_update FROM users WHERE is_notified = 0")
        users = c.fetchall()
        
        for user in users:
            user_id, satiety, last_update = user
            time_passed = current_time - last_update
            
            # Логика: если прошло больше 5 минут (300 секунд) и сытость была низкой
            if time_passed > 300: 
                try:
                    # Отправляем сообщение
                    bot.send_message(user_id, "🐈 Твой котик голодает! Зайди в игру и покорми его.")
                    # Отмечаем, что уведомление отправлено
                    c.execute("UPDATE users SET is_notified = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    print(f"✉️ Уведомление отправлено игроку {user_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки для {user_id}: {e}")
                    # Если бот заблокирован, тоже ставим флаг, чтобы не спамить
                    c.execute("UPDATE users SET is_notified = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
        
        conn.close()

# Запускаем фоновую проверку в отдельном потоке
threading.Thread(target=check_hunger, daemon=True).start()

if __name__ == '__main__':
    # Render автоматически передает порт через переменную окружения PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
