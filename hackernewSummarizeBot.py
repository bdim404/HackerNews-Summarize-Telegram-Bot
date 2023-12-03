# !/usr/bin/env python
# -*- coding: utf-8 -*

import asyncio
import os
import openai
import html2text
import requests
from telegram import Bot,Update, Message, constants
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
import retrying
from openai.error import ServiceUnavailableError

# 从 .env 文件加载配置
load_dotenv()

# 设置日志记录
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# 从 .env 文件获取配置信息
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_TELEGRAM_USER_IDS = os.getenv("ALLOWED_TELEGRAM_USER_IDS").split(",") if os.getenv(
    "ALLOWED_TELEGRAM_USER_IDS") else []
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


# bot简介以及使用说明
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    logging.info(f"Bot started by user with ID: {user_id}")
    await update.message.reply_text(
        f'Hello, This is a bot used with @hacker_news_feed channel, forword the message to the bot and return the summarize to you.')



# 处理消息是否包含目标链接并进行鉴权
async def handle_message(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    logging.info(f"Message received from user with ID: {user_id}")
    text = update.message.text

    # 如果消息来自用户（私聊消息），则检查用户是否在白名单中
    if update.message.chat.type == 'private':
        if user_id not in ALLOWED_TELEGRAM_USER_IDS:
            await update.message.reply_text("您未被授权使用此bot，请联系机器人管理员。")
            logging.info(f"Error! Your ID: {user_id} are not allowed to use this bot.")
            return

    # 如果消息来自群聊，则检查是否包含目标链接
    if update.message.chat.type == 'group':
        if re.search(r"Link:\s+(https://readhacker.news\S+)", text) is None:
            logging.info(f"Message doesn’t contain Hacker News link")
            return

    # 提取链接
    links_match = re.search(r"Link:\s+(https://readhacker.news\S+)", text)
    comments_match = re.search(r"Comments:\s+(https://readhacker.news\S+)", text)

    links = links_match.group(1) if links_match else None
    comments = comments_match.group(1) if comments_match else None

    # 将链接传递给处理链接函数
    if links and comments:
        asyncio.create_task(handle_links(update, links, comments))
    else:
        logging.info(f"Link or comments not found in the message")




# 处理链接网页内容
async def handle_links(update: Update, links: str, comments: str) -> None:
    user_id = str(update.message.from_user.id)
    logging.info(f"Processing links for user with ID: {user_id}")

    #通过fetch_and_parse_content函数获取文章和评论的文本内容
    all_article_text = await fetch_and_parse_content(links)
    all_comments_text = await fetch_and_parse_content(comments)

    if not all_article_text or not all_comments_text:
        await update.message.reply_text("无法获取文章或评论的内容，请检查链接是否有效。")
        return

    article = all_article_text

    # 截取 comments 内容以确保不超过最大字符长度
    if len(all_comments_text[0]) > MAX_CHAR_LENGTH:
        all_comments_text[0] = truncate_text(all_comments_text[0], MAX_CHAR_LENGTH)

    comments = all_comments_text
    # Respond to the user
    asyncio.create_task(get_and_reply_summary_text(update))

# 将网页内容提取为文本
async def fetch_and_parse_content(url: str):
    response = requests.get(url)
    html = response.text
    all_text = []

    try:
        # 使用BeautifulSoup解析HTML以确保正确性
        soup = BeautifulSoup(html, "html.parser")
        content = str(soup)
        text_content = h2t.handle(content)
        all_text.append(text_content)
    except AssertionError:
        # 记录错误消息
        logging.error("HTML解析错误，目标网站HTML不合法。")
        return []

    return all_text




# 发送消息到 OpenAI API 以生成摘要
@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
async def send_messages_to_openai(messages):
    openai.api_key = OPENAI_API_KEY  # 使用从 .env 文件中获取的 API 密钥
    logging.info(f"Sending messages to OpenAI API")
    # 添加重试逻辑，最多重试5次
    for attempt in range(5):
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo-16k",
                stream=True,
                temperature=1.0,
                messages=messages
            )
            return response
        except ServiceUnavailableError as e:
            logging.warning(f"ServiceUnavailableError: {e}")
            logging.warning(f"Retrying after {2**attempt} seconds...")
            await asyncio.sleep(2**attempt)

    # 如果重试5次后仍然失败，抛出异常或返回默认值
    logging.error("Failed after 5 retries.")
    return None



# 处理从 OpenAI API 返回的信息并向用户回复（优化版）
async def process_openai_response(update, response):
    user_id = str(update.message.from_user.id)
    logging.info(f"Processing OpenAI response for user with ID: {user_id}")

    # 初始回复消息
    reply_message = await update.message.reply_text("正在处理，请稍等，大约需要一分钟。")
    await update.message.reply_chat_action(constants.ChatAction.TYPING)

    # 初始化 summary 和 backoff
    summary = ''
    backoff = 0
    prev = ''

    # 初始化消息列表，用于批量编辑
    messages_to_edit = []

    async for item in response:
        if 'choices' not in item or len(item.choices) == 0:
            continue

        delta = item.choices[0].delta
        finished = item.choices[0]['finish_reason'] == 'stop'

        if 'content' in delta and delta.content is not None:
            summary += delta.content

        cutoff = get_stream_cutoff_values(update, summary)
        cutoff += backoff

        # 如果满足条件或处理结束，准备批量编辑消息
        if abs(len(summary) - len(prev)) > cutoff or finished:
            prev = summary
            messages_to_edit.append(summary)
            backoff += 5

            # 处理一次性批量编辑消息
            await batch_edit_messages(reply_message, messages_to_edit)
            messages_to_edit = []  # 清空消息列表

            # 异步等待一小段时间，以便 Telegram 服务器能够处理编辑请求
            await asyncio.sleep(0.01)

# 批量编辑消息
async def batch_edit_messages(reply_message, messages):
    try:
        # 一次性编辑多个消息
        await reply_message.edit_text("\n".join(messages))
    except (RetryAfter, TimedOut):
        await asyncio.sleep(0.5)
    except Exception:
        pass




# 将文章和评论传递给 OpenAI API 以生成摘要
async def get_and_reply_summary_text(update: Update):
    user_id = str(update.message.from_user.id)
    logging.info(f"Generating summary for user with ID: {user_id}")

    messages = [
        {"role": "system", "content": "你是一个善于提取文章文本摘要的高手。"},
        {"role": "user",
         "content": "你好！这是Hacker News上的一篇文章，请你结合原文和评论对这个内容做一个600字以内的中文总结，简要介绍文章并进行总结，请确保语言流畅、衔接自然，避免套话、空话便于快速浏览。内容如下："},
    ]

    if article:
        messages.append({"role": "assistant", "content": article[0]})
    if comments:
        messages.append({"role": "assistant", "content": comments[0]})

    total_text = "".join([message["content"] for message in messages])

    if len(total_text) > MAX_CHAR_LENGTH:
        messages[-1]["content"] = truncate_text(total_text, MAX_CHAR_LENGTH)

    response = await send_messages_to_openai(messages)
    await process_openai_response(update, response)


# 获取流截止值
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

# 检查消息是否来自群聊
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

# 截取文本以确保不超过最大字符长度
def truncate_text(text, max_length):
    if len(text) <= max_length:
        return text
    else:
        # 从文本的末尾开始删除字符，直到满足最大长度
        return text[:-(len(text) - max_length)]


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()  # 使用从 .env 文件中获取的 Telegram Bot Token
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
    logging.info("Bot application started")

if __name__ == "__main__":
    main()
