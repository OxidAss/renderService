import os
import requests
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Поддерживает несколько ID через запятую: "123456,-789012"
CHAT_IDS = [cid.strip() for cid in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if cid.strip()]
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram_message(chat_id, text):
    """Отправляет сообщение в Telegram. Не бросает исключения наружу."""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Отправлено в чат {chat_id}")
    except Exception as e:
        print(f"Ошибка Telegram: {e}")

def handle_telegram_notification(data):
    """Форматирует и отправляет уведомление."""
    nickname = data.get("nickname", "Unknown")
    ip = data.get("ip", "Unknown")
    server = data.get("server", "Unknown")
    timestamp = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")

    # Точный текст, который вы просили
    message = (
        f"<b>Подозрительный вход</b>\n\n"
        f"Под ником <code>{nickname}</code> была попытка входа с неизвестного айпи адреса (<code>{ip}</code>).\n\n"
        f"Время: <code>{timestamp}</code>"
    )

    for chat_id in CHAT_IDS:
        send_telegram_message(chat_id, message)

@app.route("/health")
def health():
    """Health check для Render"""
    return "OK", 200

@app.route("/notify", methods=["POST"])
def notify():
    if not BOT_TOKEN or not CHAT_IDS:
        return jsonify({"error": "Telegram не настроен"}), 500

    data = request.get_json(silent=True)
    if not data or "nickname" not in data or "ip" not in data:
        return jsonify({"error": "Неверный формат запроса"}), 400

    # Отправка в фоне, чтобы сразу вернуть 202 моду
    threading.Thread(target=handle_telegram_notification, args=(data,), daemon=True).start()

    return jsonify({"status": "accepted"}), 202

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
