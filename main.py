import os
import telebot
import requests
import io
from openai import OpenAI
from flask import Flask, request

# Секреты из переменных окружения
TG_TOKEN = os.environ.get("TG_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")   # <-- новый ключ
HF_TOKEN = os.environ.get("HF_TOKEN")

bot = telebot.TeleBot(TG_TOKEN, threaded=False)
app = Flask(__name__)

# DeepSeek клиент (OpenAI-совместимый)
ai_client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY
)

# URL модели Flux (Hugging Face)
FLUX_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"

@app.route(f'/{TG_TOKEN}', methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def homepage():
    return "Бот активен!", 200

# Генерация изображений (Flux)
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую изображение...")
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(FLUX_API_URL, headers=headers, json={"inputs": prompt})

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
                error_data = response.json()
                error_text = error_data.get("error", "Неизвестная ошибка HF")
                bot.edit_message_text(
                    f"Ошибка модели: {error_text}",
                    message.chat.id,
                    status_msg.message_id
                )
        else:
            bot.edit_message_text(
                f"Ошибка HF API. Код: {response.status_code}",
                message.chat.id,
                status_msg.message_id
            )
    except Exception as e:
        bot.edit_message_text(
            "Не удалось сгенерировать изображение.",
            message.chat.id,
            status_msg.message_id
        )

# Текстовый чат через DeepSeek
@bot.message_handler(func=lambda message: True)
def handle_text_chat(message):
    try:
        completion = ai_client.chat.completions.create(
            model="deepseek-chat",          # или "deepseek-reasoner" для рассуждений
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, completion.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, f"Ошибка DeepSeek: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))# Генерация изображений через Flux
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    # Извлекаем текст после команды
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Рисую изображение...")
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(FLUX_API_URL, headers=headers, json={"inputs": prompt})
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "image" in content_type:
                # Это картинка – отправляем
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_photo(
                    message.chat.id,
                    io.BytesIO(response.content),
                    reply_to_message_id=message.message_id
                )
            else:
                # Вероятно, JSON с ошибкой/предупреждением
                error_data = response.json()
                error_text = error_data.get("error", "Неизвестная ошибка HF")
                bot.edit_message_text(
                    f"Ошибка модели: {error_text}",
                    message.chat.id,
                    status_msg.message_id
                )
        else:
            bot.edit_message_text(
                f"Ошибка HF API. Код: {response.status_code}",
                message.chat.id,
                status_msg.message_id
            )
    except Exception as e:
        bot.edit_message_text(
            "Не удалось сгенерировать изображение.",
            message.chat.id,
            status_msg.message_id
        )

# Текстовый чат с Llama 3 (Groq)
@bot.message_handler(func=lambda message: True)
def handle_text_chat(message):
    try:
        completion = ai_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, completion.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, f"Ошибка текстовой модели: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
