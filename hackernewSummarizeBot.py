# !/usr/bin/env python
# -*- coding: utf-8 -*

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

article = ""
comments = ""

ARTICLE, COMMENTS = range(2)

h2t = html2text.HTML2Text()
h2t.ignore_tables = True
h2t.ignore_images = True
h2t.google_doc = True
h2t.ignore_links = True

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello, this is a bot for HackerNews to summarize.')

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global article, comments
    text = update.message.text
    links_match = re.search(r"Link:\s+(https://\S+)", text)
    comments_match = re.search(r"Comments:\s+(https://\S+)", text)

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
    comments = all_comments_text
    # Respond to the user
    await update.message.reply_text("正在处理，请稍等，大约需要一分钟。")
    await get_summary_text(update)

async def get_summary_text(update: Update):
    openai.api_key = 'YOUR-KEY'  # 请替换为您的OpenAI API密钥

    messages = [
        {"role": "system", "content": "你是一个善于提取文章文本摘要的高手。"},
        {"role": "user", "content": "你好！这是Hacker News上的一篇文章，请你结合原文和评论对这个内容做一个600字以内的中文总结，简要介绍文章并进行总结，请确保语言流畅、衔接自然，便于快速浏览。"},
        {"role": "assistant", "content": article[0] + "\n" + comments[0]},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=messages
    )
    summary = response['choices'][0]['message']['content']
    await update.message.reply_text(summary)

def main():
    app = ApplicationBuilder().token("YOUR-TOKEN").build()  # 请替换为您的Telegram Bot Token
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
