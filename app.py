from flask import Flask, request, jsonify

app = Flask(__name__)

# --- РАЗРЕШАЕМ CORS ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Secret-Key')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    return response

@app.route('/update', methods=['POST', 'OPTIONS'])
def test_update():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    print("🔥 УРА! ЗАПРОС POST ДОШЕЛ ДО СЕРВЕРА!")
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
