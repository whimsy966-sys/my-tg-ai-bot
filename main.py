import os
import telebot
import requests
import io
from openai import OpenAI
from flask import Flask, request

# Секреты
TG_TOKEN = os.environ.get("TG_TOKEN")
TEXT_AI_API_KEY = os.environ.get("TEXT_AI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")

bot = telebot.TeleBot(TG_TOKEN, threaded=False)
app = Flask(__name__)

# Groq (быстрый и бесплатный)
ai_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=TEXT_AI_API_KEY
)

@app.route(f'/{TG_TOKEN}', methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def homepage():
    return "Бот активен на Render! 🚀", 200

# ==================== FLUX ====================
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    # Чистим команду и упоминания
    prompt = message.text.replace('/draw', '').replace('/image', '').replace(bot.username, '').strip()
    
    if not prompt:
        bot.reply_to(message, "Укажите, что нарисовать! Пример: /draw кот в шляпе")
        return
    
    status_msg = bot.reply_to(message, "🎨 Генерирую Flux... (это может занять 10–30 сек)")

    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
        
        response = requests.post(
            url,
            headers=headers,
            json={"inputs": prompt},
            timeout=120
        )
        
        if response.status_code == 200:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.send_photo(
                message.chat.id,
                io.BytesIO(response.content),
                caption=f"✅ Flux: {prompt[:50]}...",
                reply_to_message_id=message.message_id
            )
        else:
            bot.edit_message_text(
                f"❌ Ошибка Flux ({response.status_code}): {response.text[:300]}",
                message.chat.id,
                status_msg.message_id
            )
    except Exception as e:
        bot.edit_message_text("❌ Не удалось сгенерировать изображение. Проверьте HF_TOKEN и доступность модели.", 
                              message.chat.id, status_msg.message_id)


# ==================== GROQ (Llama 3) ====================
@bot.message_handler(func=lambda message: True)
def handle_text_chat(message):
    if message.text.startswith(('/draw', '/image')):
        return  # уже обработано выше
    
    try:
        completion = ai_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, completion.choices.message.content)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка Groq: {str(e)}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)    if not prompt:
        bot.reply_to(message, "Укажите, что нарисовать после команды. Пример: /draw кот")
        return
    status_msg = bot.reply_to(message, "🎨 Рисую картинку Flux...")
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(
            "https://huggingface.co", 
            headers=headers, 
            json={"inputs": prompt}
        )
        if response.status_code == 200:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.send_photo(message.chat.id, io.BytesIO(response.content), reply_to_message_id=message.message_id)
        else:
            bot.edit_message_text(f"Ошибка Flux. Код: {response.status_code}", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text("Не удалось сгенерировать изображение.", message.chat.id, status_msg.message_id)

# 2. Текстовый чат Llama 3 (Groq)
@bot.message_handler(func=lambda message: True)
def handle_text_chat(message):
    try:
        completion = ai_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, completion.choices.message.content)
    except Exception as e:
        bot.reply_to(message, f"Ошибка текста: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
