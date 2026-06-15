import os
import io
import telebot
import pollinations  # бесплатная генерация изображений
from openai import OpenAI
from flask import Flask, request

# === Конфигурация ===
TG_TOKEN = os.environ.get("TG_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = os.environ.get("BASE_URL")  # например, https://твой-бот.onrender.com

if not TG_TOKEN or not DEEPSEEK_API_KEY or not BASE_URL:
    raise ValueError("Не заданы переменные окружения: TG_TOKEN, DEEPSEEK_API_KEY, BASE_URL")

bot = telebot.TeleBot(TG_TOKEN, threaded=False)
app = Flask(__name__)

# DeepSeek (текстовая модель)
ai_client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY
)

# === Команды ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "🤖 Привет! Я умею:\n"
        "/draw <описание> – нарисовать картинку\n"
        "/image <описание> – то же самое\n"
        "Просто напиши текст – я отвечу через DeepSeek."
    )

# === Генерация изображений через Pollinations (бесплатно) ===
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "❌ Укажите описание после команды. Пример: /draw кот в космосе")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую... (это может занять 5–10 секунд)")

    try:
        # Генерируем изображение
        image = pollinations.Image(prompt=prompt)

        # Конвертируем в байты для отправки в Telegram
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_photo(
            message.chat.id,
            img_byte_arr,
            reply_to_message_id=message.message_id,
            caption=f"✨ {prompt[:100]}"
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка генерации: {str(e)[:400]}",
            message.chat.id,
            status_msg.message_id
        )

# === Обработка любого текста через DeepSeek ===
@bot.message_handler(func=lambda message: True)
def handle_text_chat(message):
    try:
        completion = ai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, completion.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка DeepSeek: {e}")

# === Вебхук для Flask ===
@app.route(f'/{TG_TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def homepage():
    return "Бот активен!", 200

# === Установка вебхука при запуске ===
def set_webhook():
    bot.remove_webhook()
    webhook_url = f"{BASE_URL}/{TG_TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"Webhook установлен на {webhook_url}")

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
