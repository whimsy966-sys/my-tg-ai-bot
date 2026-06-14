import os
import io
import urllib.parse
import requests
import telebot
from openai import OpenAI
from flask import Flask, request

# Секреты из переменных окружения
TG_TOKEN = os.environ.get("TG_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

bot = telebot.TeleBot(TG_TOKEN, threaded=False)
app = Flask(__name__)

# DeepSeek клиент (OpenAI-совместимый)
# Используем быструю модель deepseek-chat (аналог "flash")
ai_client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY
)

@app.route(f'/{TG_TOKEN}', methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def homepage():
    return "Бот активен!", 200

# Генерация изображений через Pollinations.ai (Flux Schnell Fork)
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую изображение...")

    try:
        # Кодируем промпт для URL
        safe_prompt = urllib.parse.quote(prompt)
        # Используем модель flux (быстрая Schnell-версия)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?model=flux"

        resp = requests.get(image_url, timeout=60)

        if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.send_photo(
                message.chat.id,
                io.BytesIO(resp.content),
                reply_to_message_id=message.message_id
            )
        else:
            bot.edit_message_text(
                f"❌ Ошибка генерации. Код: {resp.status_code}",
                message.chat.id,
                status_msg.message_id
            )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка: {str(e)[:400]}",
            message.chat.id,
            status_msg.message_id
        )

# Текстовый чат (DeepSeek Chat – быстрый, "flash")
@bot.message_handler(func=lambda message: True)
def handle_text_chat(message):
    try:
        completion = ai_client.chat.completions.create(
            model="deepseek-chat",  # самая быстрая модель DeepSeek
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, completion.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка DeepSeek: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
