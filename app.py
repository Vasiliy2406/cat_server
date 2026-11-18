from flask import Flask, request, jsonify
import sqlite3
import time
import telebot
import threading
import os

# --- НАСТРОЙКИ ---
# Вставь сюда токен своего бота (получи у @BotFather)
BOT_TOKEN = 'ТВОЙ_ТОКЕН_ЗДЕСЬ'
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
    return jsonify({"status": "ok"}), 200

# --- ФОНОВАЯ ПРОВЕРКА (Уведомления) ---
def check_hunger():
    while True:
        time.sleep(60) # Проверяем раз в минуту (для теста)
        current_time = int(time.time())
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # Ищем тех, кто не заходил больше 5 минут (для теста) и у кого голод падает
        # (В реальной игре тут будет расчет: сколько времени прошло * скорость голода)
        c.execute("SELECT user_id, satiety, last_update FROM users WHERE is_notified = 0")
        users = c.fetchall()
        
        for user in users:
            user_id, satiety, last_update = user
            time_passed = current_time - last_update
            
            # Логика: если прошло больше 5 минут (300 секунд) и сытость была низкой
            if time_passed > 300: # 300 секунд = 5 минут (для теста)
                # В реальности тут надо пересчитать сытость, но для теста просто шлем
                try:
                    bot.send_message(user_id, "🐈 Твой котик голодает! Зайди в игру и покорми его.")
                    # Отмечаем, что уведомление отправлено
                    c.execute("UPDATE users SET is_notified = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
                except Exception as e:
                    print(f"Ошибка отправки для {user_id}: {e}")
        
        conn.close()

# Запускаем фоновую проверку в отдельном потоке
threading.Thread(target=check_hunger, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
