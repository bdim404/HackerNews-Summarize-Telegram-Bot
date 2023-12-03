# HackerNews-Summarize-Telegram-Bot

[![Github Pages](https://github.com/polyrabbit/hacker-news-digest/actions/workflows/static.yml/badge.svg)](https://github.com/polyrabbit/hacker-news-digest/actions/workflows/static.yml)
[![license](https://img.shields.io/badge/LICENSE-BSD3%20Clause%20Liscense-blue?style=flat-square)](https://github.com/bdim404/HackerNews-Summarize-Telegram-Bot/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/polyrabbit/hacker-news-digest/pulls)
[![Hacker News](https://camo.githubusercontent.com/73322cbcbf1c517bb5d3d8d4e724f81091fc767ccc278b44f1ee1a1179e9ad38/68747470733a2f2f736869656c64732e696f2f62616467652f4861636b65722532304e6577732d6630363532663f6c6f676f3d79253230636f6d62696e61746f72267374796c653d666c61742d737175617265266c6f676f436f6c6f723d7768697465)](https://hackernews.betacat.io/)

## Introduce

This is a bot used with this [Hacker News Feed Telegram chnnel](https://t.me/hacker_news_feed), forword the message to the bot and return the summarize to you.

## Quickstart

1. Download and open this repository with `git clone https://github.com/bdim404/HackerNews-Summarize-Telegram-Bot.git`


2. Customize the configuration by copying `.env.example` and renaming it to `.env`, then editing the required parameters as desired:

| Parameter                   | Description                                                                                                                                                                                                                   |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `OPENAI_API_KEY`            | Your OpenAI API key, you can get it from [here](https://platform.openai.com/account/api-keys)                                                                                                                                 |
| `TELEGRAM_BOT_TOKEN`        | Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather) (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))                                                                  |
| `ADMIN_USER_IDS`            | Telegram user IDs of admins. These users have access to special admin commands, information and no budget restrictions. Admin IDs don't have to be added to `ALLOWED_TELEGRAM_USER_IDS`. **Note**: by default, no admin (`-`) |
| `ALLOWED_TELEGRAM_USER_IDS` | A comma-separated list of Telegram user IDs that are allowed to interact with the bot (use [getidsbot](https://t.me/getidsbot) to find your user ID). **Note**: by default, *everyone* is allowed (`*`)                       |

3. Install the dependencies using `requirements.txt` file:
```shell
pip install -r requirements.txt
```

4. Use the following command to start the bot:
```
python hackernewSummarizeBot.py
```
