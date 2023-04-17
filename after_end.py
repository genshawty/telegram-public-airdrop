from dotenv import dotenv_values
config = dotenv_values("functions/.env")
API_TOKEN = config["TOKEN"]

import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.markdown import text as md_text
# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(lambda msg: msg.chat.type != types.ChatType.PRIVATE)
async def help_msg(message: types.Message):
    return

@dp.message_handler()
async def echo(message: types.Message):
    # old style:
    # await bot.send_message(message.chat.id, message.text)
    t = md_text(
        "*The airdrop has ended*!",
        "We will notify the winners about result in January!"
    )
    await message.answer(t, parse_mode="Markdown")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)