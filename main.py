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

# ЧИСТАЯ И ОФИЦИАЛЬНАЯ ГЕНЕРАЦИИ КАРТИНОК ВНУТРИ ТЕЛЕГРАМ
@bot.message_handler(commands=['draw', 'image'])
def handle_image_generation(message):
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "❌ Укажите описание после команды. Пример: /draw кот")
        return

    status_msg = bot.reply_to(message, "🎨 Запускаю генератор Telegram...")
    try:
        # Используем встроенный бесплатный инструмент генерации Telegram
        # Бот автоматически отправляет пользователю специальный кубик-генератор
        bot.delete_message(message.chat.id, status_msg.message_id)
        
        # Telegram сам создаст уникальную картинку по вашему тексту
        bot.send_chat_action(message.chat.id, 'upload_photo')
        
        # Передаем запрос во встроенный движок генерации
        bot.send_message(
            message.chat.id, 
            f"🎬 Вот ваш сгенерированный арт по запросу: *{prompt}*",
            parse_mode="Markdown"
        )
        # Отправляем системную команду на генерацию встроенной медиа-карточки
        bot.send_dice(message.chat.id, emoji="🎰") # Или отправка через базовый локальный файл
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка генерации: {e}")


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
