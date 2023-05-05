import requests

from config import *
import ImageCoder

import asyncio
import logging

from PIL import Image as im
from pillow_heif import register_heif_opener
import io
import numpy as np

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.helper import Helper, HelperMode, Item
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# bot init
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())


async def setup_commands(bot: bot):
    commands = [
        types.BotCommand(command="/start", description="Перезапустить бота"),
        types.BotCommand(command="/encrypt", description="Зашифровать изображение"),
        types.BotCommand(command="/decrypt", description="Расшифровать изображение")
    ]
    await bot.set_my_commands(commands)


# setup parts of bot
async def main(self):
    await setup_commands(bot)


# init
class Messages:
    hy = "Привет, что ты хочешь сделать с изображением?"
    encrypt = "Зашифровать"
    decrypt = "Расшифровать"
    offer_help = "Я могу чем-нибудь еще помочь?"
    unknown_cmd = "Я не знаю, как это сделать, я же всего лишь бот :("
    buttons_below = "Лучше выбери из кнопок ниже..."
    no_photo = "Я же просил фото("
    encrypted_as_document = "Пожалуйста отправь зашифрованное изображение как файл"
    no_password = "Пожалуйста, введи корректный пароль, иначе я буду грустить("
    send_photo = "Хорошо, пришли мне фото."
    create_password = "Окей, придумай пароль: "
    enter_password = "Ладно, но какой пароль?"
    encrypting = "Уже шифрую..."
    decrypting = "Пытаюсь расшифровать..."
    home = "Домой🏠"
    restart = "Если запутался просто перезапусти меня /start"


class Memory(StatesGroup):
    mode = HelperMode.snake_case

    ask = State()
    encrypt = State()
    decrypt = State()
    pas_encrypt = State()
    pas_decrypt = State()
    start = State()


# Functions
async def timer_delete(message: types.Message, seconds=10):
    await asyncio.sleep(seconds)
    await message.delete()


def BioPhoto(img_arr, photo_format):
    img = im.fromarray(img_arr)
    bio = io.BytesIO()
    bio.name = "image." + ("jpg" if photo_format == "JPEG" else photo_format.lower())
    img.save(bio, format=photo_format, quantization=95, subsampling=1)
    bio.seek(0)
    return bio


def resize_to_qhd(img: im.Image):
    K = 2560
    w, h = img.size
    print(w, h)
    if w > h and w > K:
        img = img.resize((K, int(h / (w / K))), im.ANTIALIAS)
    elif h > K:
        img = img.resize((int(w / (h / K)), K), im.ANTIALIAS)
    return img


async def get_url(message: types.Message, file_type=None):
    if file_type is None:
        async with dp.current_state().proxy() as data:
            file_type = data["file_type"]
    if file_type == "photo":
        file_id = message.photo[-1].file_id
    else:  # file_type == "document":
        file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    url = "https://api.telegram.org/file/bot{0}/{1}".format(TOKEN, file_path)
    return url


async def image_from_message(message: types.Message):
    url = await get_url(message)
    print(url)
    url_response = requests.get(url)
    register_heif_opener()
    img: im.Image = im.open(io.BytesIO(url_response.content))
    img_arr = np.array(resize_to_qhd(img))
    return img_arr


async def image_from_message_2jpg(message: types.Message):
    img_arr = await image_from_message(message)
    async with dp.current_state().proxy() as data:
        file_type = data["file_type"]
    if file_type != "photo":
        img = im.open(BioPhoto(img_arr, "JPEG"))
    else:
        img = im.fromarray(img_arr)
    return np.array(img)


def near_hd(shape):
    return shape[0] <= 1280 and shape[1] <= 1280


# Commands
@dp.message_handler(commands=["start"], state='*')
async def cmd_start(message: types.Message):
    await Memory.ask.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [Messages.encrypt, Messages.decrypt]
    keyboard.add(*buttons)
    await message.reply(Messages.hy, reply=False, reply_markup=keyboard)


# Messages
async def cmd_hy(message: types.Message):
    await Memory.ask.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [Messages.encrypt, Messages.decrypt]
    keyboard.add(*buttons)
    await message.reply(Messages.offer_help, reply=False, reply_markup=keyboard)


@dp.message_handler(state = "*", text=Messages.home)
async def cmd_back(message: types.Message):
    await message.reply("Ок", reply_markup=types.ReplyKeyboardRemove())
    await cmd_hy(message)


@dp.message_handler(commands=["encrypt"], state='*')
@dp.message_handler(text=[Messages.encrypt], state=Memory.ask)
async def task(message: types.Message):
    await Memory.encrypt.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(Messages.home)
    await message.reply(Messages.send_photo, reply_markup=keyboard)


@dp.message_handler(commands=["decrypt"], state='*')
@dp.message_handler(text=[Messages.decrypt], state=Memory.ask)
async def task(message: types.Message):
    await Memory.decrypt.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(Messages.home)
    await message.reply(Messages.send_photo, reply_markup=keyboard)


@dp.message_handler(lambda message: message.text not in [Messages.encrypt, Messages.decrypt], state=Memory.ask)
async def unknown_task(message: types.Message):
    await message.reply(Messages.unknown_cmd)
    await message.reply(Messages.buttons_below, reply=False)


@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=[Memory.encrypt])
async def encrypt_photo(message: types.Message, state: FSMContext):
    await Memory.pas_encrypt.set()
    async with state.proxy() as data:
        data["image_id"] = message
        data["file_type"] = message.content_type
    await message.reply(Messages.create_password)


@dp.message_handler(content_types=[types.ContentType.DOCUMENT], state=[Memory.decrypt])
async def decrypt_photo(message: types.Message, state: FSMContext):
    await Memory.pas_decrypt.set()
    async with state.proxy() as data:
        data["image_id"] = message
        data["file_type"] = message.content_type
    await message.reply(Messages.enter_password)


@dp.message_handler(content_types=[types.ContentType.PHOTO], state=[Memory.decrypt])
async def decrypt_photo(message: types.Message):
    await message.reply(Messages.encrypted_as_document)


@dp.message_handler(state=[Memory.encrypt, Memory.decrypt])
async def no_photo(message: types.Message):
    if message.text not in [Messages.encrypt, Messages.decrypt]:
        await message.reply(Messages.no_photo)


@dp.message_handler(state=Memory.pas_encrypt, content_types=types.ContentType.TEXT)
async def encryption(message: types.Message, state: FSMContext):
    await message.reply(Messages.encrypting)
    async with state.proxy() as data:
        image = await image_from_message_2jpg(data["image_id"])
    await bot.send_document(message.from_user.id, document=BioPhoto(ImageCoder.xor(image, message.text), "PNG"))
    return await cmd_hy(message)


@dp.message_handler(state=Memory.pas_decrypt, content_types=types.ContentType.TEXT)
async def decryption(message: types.Message, state: FSMContext):
    await Memory.start.set()
    await message.reply(Messages.decrypting)
    async with state.proxy() as data:
        image = await image_from_message(data["image_id"])
    if near_hd(image.shape):
        await bot.send_photo(message.from_user.id, photo=BioPhoto(ImageCoder.xor(image, message.text), "JPEG"))
    else:
        await bot.send_document(message.from_user.id, document=BioPhoto(ImageCoder.xor(image, message.text), "JPEG"))
    return await cmd_hy(message)


@dp.message_handler(state=[Memory.pas_encrypt, Memory.pas_decrypt])
async def bad_password(message: types.Message):
    return await message.reply(Messages.no_password)


@dp.message_handler(state='*')
async def unknown_cmd(message: types.Message):
    await message.reply(Messages.unknown_cmd)
    return await message.reply(Messages.restart, reply=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    executor.start_polling(dp, skip_updates=False, on_startup=main)
