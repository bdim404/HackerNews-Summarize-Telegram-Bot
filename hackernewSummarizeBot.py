# !/usr/bin/env python
# -*- coding: utf-8 -*

import asyncio
import os
import openai
import html2text
import requests
from telegram import Update, Message, constants
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
import sys
from html2text import HTML2Text
from bs4 import BeautifulSoup

# 从 .env 文件加载配置
load_dotenv()

# 设置日志记录
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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

#处理HTML标签
def element_style(attrs, style_def, parent_style):
    tag = style_def['tag']

    # 检查是否存在'class'属性，如果不存在，返回空字符串
    class_attr = attrs.get('class', '')

    # 在处理'class'属性时不会抛出AssertionError
    if class_attr is not None:
        class_attr = ' '.join(class_attr)
    else:
        class_attr = ''

    attrs = {key: value for key, value in attrs.items() if key != 'class'}
    attrs['class'] = class_attr

    return attrs

h2t = HTML2Text()
h2t.handle_class = element_style
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

    text = update.message.text
    links_match = re.search(r"Link:\s+(https://\S+)", text)
    comments_match = re.search(r"Comments:\s+(https://\S+)", text)

    # 如果消息来自用户（私聊消息），则检查用户是否在白名单中
    if update.message.chat.type == 'private':
        if user_id not in ALLOWED_TELEGRAM_USER_IDS:
            await update.message.reply_text("您未被授权使用此bot，请联系机器人管理员。")
            logging.info(f"Error! Your ID: {user_id} are not allowed to use this bot.")
            return

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

    try:
        # 使用BeautifulSoup解析HTML以确保正确性
        soup = BeautifulSoup(html, "html.parser")
        content = str(soup)
        text_content = html2text.html2text(content)
        all_article_text.append(text_content)
    except AssertionError:
        # 发送错误消息给用户
        await update.message.reply_text("HTML解析错误，目标网站HTML不合法。")
        return

    all_comments_text = []
    response = requests.get(comments)
    html = response.text

    try:
        # 使用BeautifulSoup解析HTML以确保正确性
        soup = BeautifulSoup(html, "html.parser")
        content = str(soup)
        text_content = html2text.html2text(content)
        all_comments_text.append(text_content)
    except AssertionError:
        # 发送错误消息给用户
        await update.message.reply_text("HTML解析错误，目标网站HTML不合法。")
        return

    article = all_article_text

    # 截取 comments 内容以确保不超过最大字符长度
    if len(all_comments_text[0]) > MAX_CHAR_LENGTH:
        all_comments_text[0] = truncate_text(all_comments_text[0], MAX_CHAR_LENGTH)

    comments = all_comments_text
    # Respond to the user
    asyncio.create_task(get_and_reply_summary_text(update))


async def get_and_reply_summary_text(update: Update):
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

    reply_message = await update.message.reply_text("正在处理，请稍等，大约需要一分钟。")
    await update.message.reply_chat_action(constants.ChatAction.TYPING)
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo-16k",
        stream=True,
        temperature=1.0,
        messages=messages
    )
    summary = ''
    '''
    Each stream reponse JSON looks like this:
    {
        "id": "chatcmpl-123",
        "object": "chat.completion.chunk",
        "created": 1694268190,
        "model": "gpt-3.5-turbo-0613",
        "choices": [
            {
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": null
            }
        ]
    }
    '''
    backoff = 0
    prev = ''
    async for item in response:
        # only consider response that has the 'choice' attribute,
        # which contains the content we want
        if 'choices' not in item or len(item.choices) == 0:
            continue
        # we take the 'delta' object out to concentrate on it
        delta = item.choices[0].delta
        finished = item.choices[0]['finish_reason'] == 'stop'
        # as long as there's content attribute, means it's not finished yet.
        # although OpenAI API also hints a 'stop' in 'finish_reason' field.
        if 'content' in delta and delta.content is not None:
            # we and append the delta content to our 'summary'
            summary += delta.content
        # then we try to update our reply with a not-finished-yet 'summary'
        cutoff = get_stream_cutoff_values(update, summary)
        cutoff += backoff
        if abs(len(summary) - len(prev)) > cutoff or finished:
            prev = summary
            try: 
                await reply_message.edit_text(summary)
            except RetryAfter as e:
                backoff += 5
                await asyncio.sleep(e.retry_after)
                continue

            except TimedOut:
                backoff += 5
                await asyncio.sleep(0.5)
                continue

            except Exception:
                backoff += 5
                continue

            await asyncio.sleep(0.01)


def get_stream_cutoff_values(update: Update, content: str) -> int:
    """
    Gets the stream cutoff values for the message length
    """
    if is_group_chat(update):
        # group chats have stricter flood limits
        return 180 if len(content) > 1000 else 120 if len(content) > 200 \
            else 90 if len(content) > 50 else 50
    return 90 if len(content) > 1000 else 45 if len(content) > 200 \
        else 25 if len(content) > 50 else 15


def is_group_chat(update: Update) -> bool:
    """
    Checks if the message was sent from a group chat
    """
    if not update.effective_chat:
        return False
    return update.effective_chat.type in [
        constants.ChatType.GROUP,
        constants.ChatType.SUPERGROUP
    ]


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
