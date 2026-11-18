from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/update', methods=['POST', 'OPTIONS'])
def test_update():
    print("🔥 УРА! ЗАПРОС ДОШЕЛ ДО СЕРВЕРА!")
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
