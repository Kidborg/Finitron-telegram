import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram import F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
import g4f
from g4f.client import Client
import json
import time
import base64
import requests
import os
from aiogram.types import InputMediaPhoto


API_TOKEN = "ваш токен"

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

client = Client()


class Form(StatesGroup):
    generate = State()


with open("data.txt", encoding="utf-8") as reglament:
    reglament = " ".join(reglament.readlines())

history = [
    f"Запомни, у тебя есть регламен (который ты представил), ты отвечаешь на вопросы по регламенту: {reglament} и тебя зовут 'Finitron', ты основан на технологии GPT-2000, ты умеешь запоминать предыдущие сообщения"]


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    kb = [
        [
            KeyboardButton(text="Задать вопрос ChatGPT"),
            KeyboardButton(text="Сгенерировать изображение"),
            KeyboardButton(text="Поддержка"),
        ],
        [

        ]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("""Я — Finitron, виртуальный помощник, предназначенный для предоставления информации по Хакатону "Подземелья и драконы".

Я могу помочь изучить новые темы, сформировать идеи, написать код, спланировать работу, распределить задачи и многое другое.

Моя задача — поддерживать вас в процессе участия в Хакатоне. Для получения ответа нажмите кнопку "Задать вопрос ChatGPT"!""",
                         reply_markup=keyboard)


@dp.message(F.text.in_({"Задать вопрос ChatGPT", "Сгенерировать изображение", "Поддержка"}))
async def process_message(message: types.Message, state: FSMContext):
    if message.text == "Задать вопрос ChatGPT":
        await message.answer("Напишите вопрос, и я отвечу на него")
        await state.set_state(Form.generate)
        await state.update_data(generate="text")
    elif message.text == "Сгенерировать изображение":
        await message.answer("Отправьте текст, по которому я сгенерирую изображение")
        await state.set_state(Form.generate)
        await state.update_data(generate="image")
    elif message.text == "Поддержка":
        await message.answer(
            "Если бот не отвечат вам в течение 5 минут, напишите в поддержку @kidborg \nРабочее время пн-вс 10:00-22:00")
    else:
        await message.answer("Ошибочка вышла... Попробуйте еще раз 😖")


@dp.message(StateFilter(Form.generate))
async def echo_message(message: types.Message, state: FSMContext):
    global history
    data = await state.get_data()
    generate = data.get("generate")
    if generate == "text":
        reply_text = ""
        msg = await message.reply("Подождите, сейчас вам отвечу...")
        try:
            response = await g4f.ChatCompletion.create_async(
                model="gpt-4o",
                messages=[{"role": "user",
                           "content": "Предыдущие запросы: " + "\n".join(history) + ". Вопрос: " + message.text}],
                provider="ваш provider"
            )
            reply_text = response
        except Exception as e:
            pass

        if reply_text == "":
            await bot.edit_message_text("Вы ввели меня в заблуждение 😯. Попробуйте еще раз задать вопрос", chat_id=msg.chat.id, message_id=msg.message_id)
        else:
            history.append(message.text)
            await bot.edit_message_text(reply_text, chat_id=msg.chat.id, message_id=msg.message_id)
    elif generate == "image":
        msg = await message.reply("Подождите, сейчас вам отвечу...")
        create_image(message.text)
        await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await bot.send_photo(message.chat.id, photo=types.FSInputFile("image.jpg"),
                             reply_markup=get_back_to_menu_markup())
    else:
        await message.reply("Error x2", reply_markup=get_back_to_menu_markup())


def get_back_to_menu_markup():
    button = InlineKeyboardButton(text="Вернуться в меню", callback_data="back_to_menu")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


@dp.callback_query(lambda c: c.data == 'back_to_menu')
async def process_callback_back_to_menu(callback_query: types.CallbackQuery):
    await send_welcome(callback_query.message)


def create_image(prompt):
    class Text2ImageAPI:
        def __init__(self, url, api_key, secret_key):
            self.URL = url
            self.AUTH_HEADERS = {
                'X-Key': f'Key {api_key}',
                'X-Secret': f'Secret {secret_key}',
            }

        def get_model(self):
            response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
            data = response.json()
            return data[0]['id']

        def generate(self, prompt, model, images=1, width=1024, height=1024):
            params = {
                "type": "GENERATE",
                "numImages": images,
                "width": width,
                "height": height,
                "generateParams": {
                    "query": f"{prompt}"
                }
            }

            data = {
                'model_id': (None, model),
                'params': (None, json.dumps(params), 'application/json')
            }
            response = requests.post(self.URL + 'key/api/v1/text2image/run', headers=self.AUTH_HEADERS, files=data)
            data = response.json()
            return data['uuid']

        def check_generation(self, request_id, attempts=10, delay=10):
            while attempts > 0:
                response = requests.get(self.URL + 'key/api/v1/text2image/status/' + request_id,
                                        headers=self.AUTH_HEADERS)
                data = response.json()
                if data['status'] == 'DONE':
                    return data['images']

                attempts -= 1
                time.sleep(delay)

    api = Text2ImageAPI('https://api-key.fusionbrain.ai/', 'ваш api key',
                        'ваш secret key')
    model_id = api.get_model()
    uuid = api.generate(" ".join(prompt.split()), model_id)
    images = api.check_generation(uuid)

    image_base64 = images[0]

    image_data = base64.b64decode(image_base64)

    with open("image.jpg", "wb") as file:
        file.write(image_data)


async def main():
    # Start polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())


