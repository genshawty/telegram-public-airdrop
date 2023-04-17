import re
from dotenv import dotenv_values
import logging
import requests
import json

import os
import random

from aiogram.utils.markdown import text as md_text
from aiogram.utils.markdown import link, bold
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import sqlite3
from datetime import datetime
from captcha.image import ImageCaptcha
from functions.google import add_row, update_info
from functions.settings import CHANNEL_ID, HASHTAGS, POST_LINK, RETWEET_URL
from functions.discord import search_discord_member
# from functions.settings import RETWEET_URL

config = dotenv_values("functions/.env")
API_TOKEN = config["TOKEN"]


# Configure logging
logger = logging.getLogger()

now = datetime.now()
# dd/mm/YY H:M:S
dt_string = now.strftime("%d.%m.%Y %H.%M.%S")
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", dt_string + ".log")
print(log_file)
with open(log_file, mode='a+'): pass
    

logging.basicConfig(level=logging.INFO, 
                    filename = log_file,
                    format = "%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
                    datefmt='%H:%M:%S',
                    force=True,
                )

db = sqlite3.connect('data/users.db')
    # sqlite_create_table_query = '''CREATE TABLE IF NOT EXISTS users (
                                # username TEXT,
                                # chat_id INTEGER PRIMARY KEY,
                                # user_id INTEGER,
                                # twitter TEXT NOT NULL,
                                # email TEXT NOT NULL,
                                # metamask TEXT NOT NULL);'''

db_cursor = db.cursor()

# For example use simple MemoryStorage for Dispatcher.
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# class to control Form.twitter running
class StatusStatesGroup(StatesGroup):
    # status: "started" - just for first message
    # status: "confirmaton" - twitter data is processing and there is no need to read another messages
    def set_twitter_status(self, status: str):
        # print('setting status')
        self.twitter_status = status
    
    def get_twitter_status(self) -> str:
        # print('getting status')
        return self.twitter_status

# class to read and write captcha code
class CaptchaStatesGroup(StatesGroup):
    def set_code(self, code: str):
        self.password = code
    def get_code(self) -> str:
        return self.password
    
# Initialization of our form to store users data
class Form(StatusStatesGroup):
    twitter = State()
    discord = State()
    metamask = State()
    # email = State()

class Captcha_Form(CaptchaStatesGroup):
    code = State()

def write_captcha(id: int, code: str):
    id = str(id)
    filepath = "captcha/{}.txt".format(id)

    with open(filepath, "w") as f:
        f.write(code)

def read_captcha(id: int) -> str:
    id = str(id)
    filepath = "captcha/{}.txt".format(id)

    with open(filepath, "r") as f:
        return f.read().strip()

def generate_captcha(id: int, text: str):
    image = ImageCaptcha(280, 90)
    data = image.generate(text)  
    image.write(text, 'data/{}.png'.format(id))

def generate_text() -> str:
    # without: "o", "l", "s", "h", "8"
    alpha = "abcdefgijkmnpqrtuvwxyz012345679"
    a_list = random.sample(list([i for i in alpha]), 4)

    return ''.join(a_list)

@dp.message_handler(lambda msg: msg.chat.type != types.ChatType.PRIVATE)
async def help_msg(message: types.Message):
    return

# Start message, just inform people whats happenning, something can be easily added here
@dp.message_handler(commands='start')
@dp.message_handler(state="*", commands='start')
async def welcome_func(message: types.Message):
    logger.info(f"{message.from_user.username} - started conversation")

    try:
        os.remove("data/{}.png".format(message.chat.id))
        os.remove("captcha/{}.txt".format(message.chat.id))
    except:
        pass

    text = generate_text()
    generate_captcha(message.chat.id, text)

    write_captcha(message.chat.id, text)

    await Captcha_Form.code.set()
    await bot.send_photo(chat_id=message.chat.id, photo=open("data/{}.png".format(message.chat.id), "rb") ,caption="Please enter the captcha (4 characters, case insensitive): ")

@dp.message_handler(state=Captcha_Form.code)
async def captcha_func(message: types.Message, state: FSMContext):
    """
    Starting message
    """
    # logger.info(message.from_user.username)
    if message.text.lower() != read_captcha(message.chat.id):
        text = generate_text()
        generate_captcha(message.chat.id, text)
        write_captcha(message.chat.id, text)

        # await Captcha_Form.code.set()
        return await bot.send_photo(chat_id=message.chat.id, photo=open("data/{}.png".format(message.chat.id), "rb") ,caption="Incorrect code, please repeat: ")
    # delete captcha message 
    try:
        os.remove("data/{}.png".format(message.chat.id))
        os.remove("captcha/{}.txt".format(message.chat.id))
    except:
        pass
    welcome_text = md_text(
        "Hi, *{}*!".format(message.from_user.first_name),
        "💎Thanks for joining the Drop for Cheelee community activities!💎",
        "Community drop - 1,250,000 tokens are to be dropped to the lucky ones in two stages. 50% of them - in December and another 50% - after the launch of the app.",
        "We are happy to announce the beginning of our token launch and the new incentivized programs for our community🔥\n",
        "To participate you need to join our social media channels: ",
        "1. [Discord](https://discord.gg/cheelee)",
        "2. [Twitter](https://twitter.com/Cheelee_Tweet)",
        "3. [Telegram](https://t.me/CheeleeCommunity_EN)\n",
        "If you have any questions feel free to ask it on our social media channels\n",
        "🔔PLEASE NOTE: You will be able to claim your rewards after the mainnet launch of $CHEEL token. We will notify the winners about the time of claim and procedure on our social media channels.\n",
        bold("To start enter: /drop"), sep="\n"
    )
    await state.finish()
    await bot.send_message(message.chat.id, text=welcome_text, parse_mode="Markdown")

# Cancel function
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    logger.info(f"{message.from_user.username} - cancelling execution")
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Canceled\nType /drop to restart.', reply_markup=types.ReplyKeyboardRemove())

# Entry for collecting the information, also could be restarted with same command
@dp.message_handler(state="*", commands='drop')
async def cmd_start(message: types.Message):
    logger.info(f"{message.from_user.username} - started /drop")
    """
    Conversation's entry point
    """
    # Set state

    tasks_text = md_text(
        "😎Tasks:",
        '1. Join Cheelee discord channel and react to announcements https://discord.gg/cheelee',
        "2. Join [Cheelee Telegram channel](https://t.me/CheeleeCommunity_EN)",
        "3. Follow [Cheelee on Twitter](https://twitter.com/Cheelee_Tweet)",
        "4. Retweet: [tweet]({})".format(RETWEET_URL),
        "5. Send your crypto wallet address",
        "If you want to cancel data collection, enter: /cancel", sep="\n\n"
    )

    # in_db, registered = check_db(message.from_id)
    in_db, registered = check_db(message.from_id)
    
    if registered:
        await Form.metamask.set()
        return await message.answer("You have already registered, if you want to change your metamask address enter it, otherwise please use /cancel")

    if check_if_member(message.from_id):
        await Form.twitter.set()
        await message.answer(tasks_text, parse_mode="Markdown")
        await message.answer("We will only check your retweet after the drop is finished!\nMake sure you don’t remove any of your tweets and retweets, otherwise you won’t get your coins!", parse_mode="Markdown")
        await message.answer("Complete all tasks and send us your twitter account: ")
        if not in_db:
            start_time = make_date()
            command = "INSERT INTO users(username,chat_id,user_id,twitter,discord,email,metamask,finished,start_time) VALUES ('{}','{}', '{}', '','','','', '0', '{}')".format(message.from_user.username, message.chat.id, message.from_id, start_time)
            db_cursor.execute(command)
            db.commit()
            db_cursor.execute("SELECT * from users WHERE user_id={}".format(message.from_id))
            
            row = list(db_cursor.fetchall()[0])
            # def add_row(username, twitter, metamask, email, chat_id, user_id):
            try:
                add_row(logger, row[0], message.from_user.username, "", "", "", "", message.chat.id, message.from_id, 0, start_time)
            except Exception as E: 
                print(E)
                logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)
            
        logger.info(f"{message.from_user.username} - finished /drop")
    else:
        return await message.answer("Please join our Telegram channel: {} then press /drop again".format(CHANNEL_ID))

def make_date() -> str:
    now = datetime.now()

    return now.strftime("%d/%m %H:%M:%S")

def check_db(user_id: int):
    '''
    -> in_database, registered
    '''
    db_cursor.execute("SELECT * from users WHERE user_id={}".format(user_id))
    # db_cursor.execute("SELECT * from users WHERE user_id=123")
    r = db_cursor.fetchall()
    if len(r) == 0:
        return False, False
    if r[0][-2] == 0:
        return True, False
    return True, True

def update_db(user_id:int, field: str, value: str):
    fields_nums = {
        "username": 1,
        "chat_id": 2,
        "user_id": 3,
        "twitter": 4,
        "discord": 5,
        "email": 6,
        "metamask": 7,
        "finished": 8,
        "start_time": 9
    }
    db_cursor.execute("SELECT * from users WHERE user_id={}".format(user_id))
            
    row = list(db_cursor.fetchall()[0])
    row[fields_nums[field]] = value

    db_cursor.execute("REPLACE INTO users (id, username,chat_id,user_id,twitter,discord,email,metamask,finished,start_time) VALUES ('{}','{}','{}', '{}', '{}','{}','{}','{}','{}','{}')".format(*row))

    db.commit()
    update_info(logger, field, row)

def check_if_member(user_id: int):
    # return True
    logger.info(f"{user_id} - checking membership in telegram")
    r = requests.get(f"https://api.telegram.org/bot{API_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}")
    if r.status_code != 200:
        return False
    
    ans = json.loads(r.text)
    if ans["ok"] and ans["result"]["status"] != "left":
        return True
    return False

def check_if_twitter_used(name: str):
    '''
    True if used so need to reject application
    '''
    db_cursor.execute("SELECT * from users WHERE twitter=\"{}\"".format(name))
    # db_cursor.execute("SELECT * from users WHERE user_id=123")
    r = db_cursor.fetchall()
    if len(r) == 0:
        return False

    if r[0][-2] == 0:
        return False
    return True

def check_valid_twitter(message: types.Message):
    text = message.text

    if text[0] == "@":
        text = text[1:]
    if "twitter.com/" in text:
        text = text.split("twitter.com/")[-1].split("/")[0]
    text = text.lower()

    return check_if_twitter_used(text)

# Collect user's twitter
@dp.message_handler(lambda msg: not check_valid_twitter(msg) ,state=Form.twitter)
async def process_name(message: types.Message, state: FSMContext):
    """
    Process user twitter
    """    
    logger.info(f"{message.from_user.username} - started collecting twitter")
    async with state.proxy() as data:
        data["email"] = "-"
        if message.text.startswith("@"):
            data["twitter"] = message.text[1:]
        else:
            data['twitter'] = message.text
    Form.set_twitter_status(Form, "confirmation")
    try:
        update_db(message.from_id, "twitter", data["twitter"])
    except Exception as E: 
            print(E)
            logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)
    

    await Form.discord.set()

    await message.answer("Please enter your Discord account (username or server nickname) in format *name#numbers* and ensure you are server member", parse_mode="Markdown")

@dp.message_handler(check_valid_twitter,state=Form.twitter)
async def process_name_already_used(message: types.Message, state: FSMContext):
    await message.answer("This twitter address has already been used, try another or contact support.")

def check_valid_metamask(message: types.Message):
    regex = re.compile(r'^0x[a-fA-F0-9]{40}$')
    if re.fullmatch(regex, message.text):
        return True
    else:
        return False

def check_valid_discord(name_param):
    name = name_param.text
    tg_name = name_param.from_user.username
    if "#" in name:
        username, discr = name.split("#")
        if all([x.isdigit() for x in discr]):
            if search_discord_member(tg_name, logger, username, str(discr)):
                return True
    return False

@dp.message_handler(check_valid_discord ,state=Form.discord)
async def process_discord(message: types.Message, state: FSMContext):
    """
    Process user twitter
    """    
    logger.info(f"{message.from_user.username} - started collecting discord")
    text = "#".join(map(lambda x: x.strip(), message.text.split("#")))
    async with state.proxy() as data:
        data["discord"] = text
    try:
        update_db(message.from_id, "discord", data["discord"])
    except Exception as E: 
        print(E)
        logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)

    await Form.metamask.set()

    await message.answer("Please enter your Metamask wallet address:")

@dp.message_handler(lambda msg: not check_valid_discord(msg),state=Form.discord)
async def process_name_already_used(message: types.Message, state: FSMContext):
    await message.answer("This discord account is invalid, here are some tips:\n\n1) Make sure you are discord server member ✅\n\n2) Remove all outlier symbols from your nickname ❗️\n\n3) If those tips did not work, contact support ⚒")

def check_valid_metamask(message: types.Message):
    regex = re.compile(r'^0x[a-fA-F0-9]{40}$')
    if re.fullmatch(regex, message.text):
        return True
    else:
        return False

@dp.message_handler(check_valid_metamask, state=Form.metamask)
async def enter_metamask(message: types.Message, state: FSMContext):
    logger.info(f"{message.from_user.username} - twitter completed, entering metamask")
    # Update state and data
    async with state.proxy() as data:
        if data.get("twitter") == None:
            logger.info(f"{message.from_user.username} - update_db field: metamask, value: {message.text}")
            try:
                update_db(message.from_user.id, "metamask", message.text)
            except Exception as E: 
                print(E)
                logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)
            await state.finish()
            return await message.reply("Successfully edited information 😎")

        data["metamask"] = message.text
        try:
            update_db(message.from_user.id, "metamask", message.text)
            logger.info(f"{message.from_user.username} - update_db field: metamask, value: {message.text}")
        except Exception as E: 
            print(E)
            logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)

        finish_text = md_text(
            "*Congrats*! *You’ve* successfully registered!✨",
            "We will notify the winners about the time of claim and procedure on our social media channels by 26th of December.",
            "The claim of the rewards will be available after the mainnet launch of $CHEEL token.", sep="\n\n"
        )
        await bot.send_photo(
                    chat_id=message.chat.id, 
                    photo=open("data/airdrop_poster.png", "rb"),
                    caption=finish_text, 
                    parse_mode="Markdown"
                )
        try:
            update_db(message.from_id, "finished", "1")
        except Exception as E: 
            print(E)
            logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)

        # logger.info(f"{message.from_user.username} - update_row google")

    await state.finish()

@dp.message_handler(lambda message: not check_valid_metamask(message), state=Form.metamask)
async def wrong_metamask_entered(message: types.Message, state: FSMContext):
    return await message.reply("Please enter a valid Ethereum/Polygon address. The address should start with 0x and have 42 symbols.")

# def check_email(message: types.Message):
#     regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
#     if re.fullmatch(regex, message.text):
#         return True
#     else:
#         return False

# @dp.message_handler(check_email, state=Form.email)
# async def process_email(message: types.Message, state: FSMContext):
#     async with state.proxy() as data:
#         data["email"] = message.text
#         try:
#             update_db(message.from_id, "email", data["email"])
#         except Exception as E: 
#             print(E)
#             logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)

#         finish_text = md_text(
#             "*Congrats*! *You’ve* successfully registered!✨",
#             "We will notify the winners about the time of claim and procedure on our social media channels by 26th of December.",
#             "The claim of the rewards will be available after the mainnet launch of $CHEEL token.", sep="\n\n"
#         )
#         await bot.send_photo(
#                     chat_id=message.chat.id, 
#                     photo=open("data/airdrop_poster.png", "rb"),
#                     caption=finish_text, 
#                     parse_mode="Markdown"
#                 )
#         try:
#             update_db(message.from_id, "finished", "1")
#         except Exception as E: 
#             print(E)
#             logger.warning(f"{message.from_user.username} - ERROR ADDING NEW ROW ", E)

#         # logger.info(f"{message.from_user.username} - update_row google")

#     await state.finish()

# @dp.message_handler(lambda msg: not check_email(msg), state=Form.email)
# async def process_email(message: types.Message, state: FSMContext):
#     return await message.reply("Please enter a valid email address")

@dp.message_handler(state="*", commands='help')
async def help_msg(message: types.Message):
    help_text = md_text(
        "List of commands:",
        "/start - Start the conversation with Cheelee Drop Bot",
        "/drop - Start entering data to participate in the Drop",
        "/cancel - Cancel all actions", sep="\n\t"
    )
    await message.answer(help_text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)