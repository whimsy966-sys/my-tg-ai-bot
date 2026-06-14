import os
import io
import telebot
import requests
from openai import OpenAI
from flask import Flask, request
from huggingface_hub import InferenceClient  # <-- добавили

# Секреты
TG_TOKEN = os.environ.get("TG_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")

bot = telebot.TeleBot(TG_TOKEN, threaded=False)
app = Flask(__name__)

# DeepSeek (быстрая модель)
ai_client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY
)

# Новый клиент для генерации изображений через Hugging Face InferenceClient
image_client = InferenceClient(
    provider="nscale",
    api_key=HF_TOKEN
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

# Генерация изображений (новая версия)
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую...")

    try:
        # Генерируем изображение через InferenceClient
        image = image_client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-schnell"
        )

        # Преобразуем PIL Image в байты для отправки в Telegram
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_photo(
            message.chat.id,
            img_byte_arr,
            reply_to_message_id=message.message_id
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка генерации: {str(e)[:400]}",
            message.chat.id,
            status_msg.message_id
        )

# Текстовый чат DeepSeek Flash
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
