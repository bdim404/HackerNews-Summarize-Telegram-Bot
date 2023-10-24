# !/usr/bin/env python
# -*- coding: utf-8 -*

import os
import openai
import html2text
import requests
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    ApplicationBuilder,
)
import re
from dotenv import load_dotenv
import logging
import urllib.parse

# 从 .env 文件加载配置
load_dotenv()

# 设置日志记录
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger = logging.getLogger()
root_logger.addHandler(console_handler)

# 从 .env 文件获取配置信息
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS").split(",") if os.getenv("ADMIN_USER_IDS") else []
ALLOWED_TELEGRAM_USER_IDS = os.getenv("ALLOWED_TELEGRAM_USER_IDS").split(",") if os.getenv(
    "ALLOWED_TELEGRAM_USER_IDS") else []
ALLOWED_TELEGRAM_GROUP_IDS = os.getenv("ALLOWED_TELEGRAM_GROUP_IDS").split(",") if os.getenv(
    "ALLOWED_TELEGRAM_GROUP_IDS") else []

article = ""
comments = ""

ARTICLE, COMMENTS = range(2)

h2t = html2text.HTML2Text()
h2t.ignore_tables = True
h2t.ignore_images = True
h2t.google_doc = True
h2t.ignore_links = True

# 最大字符长度，根据您的需求进行调整
MAX_CHAR_LENGTH = 8000


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    logging.info(f"Bot started by user with ID: {user_id}")
    await update.message.reply_text(
        f'Hello, This is a bot used with @hacker_news_feed channel, forword the message to the bot and return the summarize to you.')


async def handle_message(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    logging.info(f"Message received from user with ID: {user_id}")
    global article, comments
    user_id = str(update.message.from_user.id)

    # 鉴权：检查用户是否在白名单中
    if user_id not in ALLOWED_TELEGRAM_USER_IDS:
        await update.message.reply_text("You are not allowed to use this bot.")
        logging.info(f"Error! Your ID: {user_id} are not allowed to use this bot.")
        return

    text = update.message.text
    links_match = re.search(r"Link:\s+(https://\S+)", text)
    comments_match = re.search(r"Comments:\s+(https://\S+)", text)

#验证链接是否来自Hacker News
    if links_match:
        links = links_match.group(1)
        if not is_valid_link(links):
            await update.message.reply_text("警告！你发送了包含错误的链接的消息，请转发正确的消息。")
            user_id = str(update.message.from_user.id)
            logging.info(f"User ID: {user_id} send a wrong links")
            return

    if comments_match:
        comments = comments_match.group(1)
        if not is_valid_link(comments):
            await update.message.reply_text("警告！你发送了包含错误的链接的消息，请转发正确的消息。")
            user_id = str(update.message.from_user.id)
            logging.info(f"User ID: {user_id} send a wrong links")
            return

    if links_match:
        links = links_match.group(1)
    if comments_match:
        comments = comments_match.group(1)

    all_article_text = []
    response = requests.get(links)
    html = response.text
    content = h2t.handle(html)
    text_content = html2text.html2text(content)
    all_article_text.append(text_content)

    all_comments_text = []
    response = requests.get(comments)
    html = response.text
    content = h2t.handle(html)
    text_content = html2text.html2text(content)
    all_comments_text.append(text_content)

    article = all_article_text

    # 截取 comments 内容以确保不超过最大字符长度
    if len(all_comments_text[0]) > MAX_CHAR_LENGTH:
        all_comments_text[0] = truncate_text(all_comments_text[0], MAX_CHAR_LENGTH)

    comments = all_comments_text
    # Respond to the user
    await update.message.reply_text("正在处理，请稍等，大约需要一分钟。")
    await get_summary_text(update)


async def get_summary_text(update: Update):
    user_id = str(update.message.from_user.id)
    logging.info(f"Generating summary for user with ID: {user_id}")

    openai.api_key = OPENAI_API_KEY  # 使用从 .env 文件中获取的 API 密钥

    messages = [
        {"role": "system", "content": "你是一个善于提取文章文本摘要的高手。"},
        {"role": "user",
         "content": "你好！这是Hacker News上的一篇文章，请你结合原文和评论对这个内容做一个600字以内的中文总结，简要介绍文章并进行总结，请确保语言流畅、衔接自然，避免套话、空话便于快速浏览。内容如下："},
        {"role": "assistant", "content": article[0] + "\n" + comments[0]},
    ]

    # 截取内容以确保不超过最大字符长度
    total_text = "".join([message["content"] for message in messages])
    if len(total_text) > MAX_CHAR_LENGTH:
        messages[2]["content"] = truncate_text(total_text, MAX_CHAR_LENGTH)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=messages
    )
    summary = response['choices'][0]['message']['content']
    await update.message.reply_text(summary)


def truncate_text(text, max_length):
    if len(text) <= max_length:
        return text
    else:
        # 从文本的末尾开始删除字符，直到满足最大长度
        return text[:-(len(text) - max_length)]


#验证域名是否来自redhacker.news
def is_valid_link(link):
    parsed_url = urllib.parse.urlparse(link)
    return parsed_url.netloc == "readhacker.news"

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()  # 使用从 .env 文件中获取的 Telegram Bot Token
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
    logging.info("Bot application started")

if __name__ == "__main__":
    main()
