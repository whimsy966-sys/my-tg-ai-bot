import os
import socket

def set_custom_dns():
    try:
        # Используем публичный DNS-сервер Google
        custom_dns = '8.8.8.8'
        org_resolver = socket.socket
        def custom_getaddrinfo(*args, **kwargs):
            if args and args[0] and 'api-inference.huggingface.co' in args[0]:
                # Перенаправляем трафик к нужному API через публичный DNS
                return org_resolver.getaddrinfo('api-inference.huggingface.co', args[1], *args[2:])
            return org_resolver.getaddrinfo(*args, **kwargs)
        socket.getaddrinfo = custom_getaddrinfo
        print('custom dns resolver set')
    except Exception as e:
        print(f'dns setup error: {e}')
set_custom_dns()
import os
import io
import telebot
import requests
from openai import OpenAI
from flask import Flask, request

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

# Hugging Face Flux Schnell (быстрая генерация)
HF_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"

@app.route(f'/{TG_TOKEN}', methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def homepage():
    return "Бот активен!", 200

# Генерация изображений
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую Flux Schnell...")

    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(HF_API_URL, headers=headers, json={"inputs": prompt}, timeout=60)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_photo(
                    message.chat.id,
                    io.BytesIO(response.content),
                    reply_to_message_id=message.message_id
                )
            else:
                # Возможно, ошибка в JSON
                error_json = response.json()
                bot.edit_message_text(
                    f"❌ Ошибка модели: {error_json.get('error', 'неизвестно')}",
                    message.chat.id,
                    status_msg.message_id
                )
        else:
            bot.edit_message_text(
                f"❌ Ошибка HF API: {response.status_code}",
                message.chat.id,
                status_msg.message_id
            )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка соединения: {str(e)[:400]}",
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
