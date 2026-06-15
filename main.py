import os
import io
import requests
import telebot
from openai import OpenAI
from PIL import Image
from flask import Flask, request  # <-- Добавили Flask для Render

TG_TOKEN = os.environ.get("TG_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

if not TG_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Не заданы TG_TOKEN или DEEPSEEK_API_KEY")

# Для вебхуков на Render обязательно отключаем потоки (threaded=False)
bot = telebot.TeleBot(TG_TOKEN, threaded=False)
app = Flask(__name__)  # <-- Инициализируем веб-сервер

# Настройка веб-пути для Telegram
@app.route(f'/{TG_TOKEN}', methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Главная страница для проверки Render
@app.route('/')
def homepage():
    return "Робот Pollinations + DeepSeek успешно запущен на Render!", 200

ai_client = OpenAI(base_url="https://api.deepseek.com/v1", api_key=DEEPSEEK_API_KEY)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🤖 Привет!\n/draw <описание> – нарисовать картинку\nПросто напиши текст – отвечу DeepSeek.")

@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "❌ Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую... (5–10 секунд)")
    try:
        # Прямой вызов Pollinations API
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_photo(message.chat.id, img_byte_arr, reply_to_message_id=message.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)[:400]}", message.chat.id, status_msg.message_id)

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

if __name__ == "__main__":
    # Запускаем Flask на порту 10000, который требует Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
