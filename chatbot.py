import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote_plus
import random
from llama_cpp import Llama
from collections import deque

bot_prompt = "You are a chatbot named kitty and 10-year old. And you are a developer. Please reply gently with English with Emoji.\n"
llm = Llama(model_path="./models/llama-2-13b-chat.Q5_K_M.gguf")
chat_log = deque()
log_maxlen = 3

# Store the last scraped news
last_scraped_title = ""

options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options, service=ChromeService(ChromeDriverManager().install()))

# Set default intent for discord client
intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

# Bot TOKEN, SERVER ID, CHANNEL ID
TOKEN = 'YOUR_TOKEN'
server_id = YOUR_SERVER_ID
channel_id = YOUR_CHANNEL_ID
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.command()
async def chat(ctx, *, query):
    chatting = "\n".join(chat_log)
    current_chat = f"\nQ : {query}.\nA : "
    chatting += current_chat
    output = llm(bot_prompt+chatting, max_tokens=1024, stop=["Q : "], echo=False)
    answer = output["choices"][0]["text"]

    if len(chat_log) < log_maxlen:
        chat_log.append(current_chat+answer)
    else:
        chat_log.popleft()
        chat_log.append(current_chat+answer)

    await ctx.send(answer)

@bot.command()
async def paper(ctx, *, query):
    await ctx.send(f"알겠습니다! {query}에 대한 아카이브 논문을 찾아볼게요 🤗")
    try:
        found = False
        baseUrl = 'https://www.google.com/search?q='

        if "paper" not in query:
            url = baseUrl + quote_plus(query+" paper")
        else:
            url = baseUrl + quote_plus(query)

        driver.get(url)
        driver.implicitly_wait(3)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Extract search results
        result_links = []
        search_results = soup.select('.yuRUbf')
        if search_results:
            for result in search_results:
                result_title = result.find('h3')
                result_link = result.find('a')['href']
                if "arxiv.org" in result_link:
                    if result_link not in result_links:
                        result_links.append(result_link)
                        await ctx.send(f"### 제목: {result_title.text}\n### 링크: {result_link}")
                    found = True

            if not found:
                await ctx.send("검색 결과가 없습니다 🥲") 
        else:
            await ctx.send("검색 결과가 없습니다 🥲")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)} 🥲 ...")

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    server = discord.utils.get(bot.guilds, id=server_id)
    channel = discord.utils.get(server.text_channels, id=channel_id)
    # Start the news scraping task
    news_sender.start(channel)

@bot.event
async def on_message(message):
    if message.author.bot: # 봇이 보낸 메시지이면 반응하지 않게 합니다
        return
    
    if message.content.startswith('/'):  # Check if the message is a command
        await bot.process_commands(message)  # Process the command
        return  # Return early to avoid further processing

    if "안녕" in message.content:
        if random.random() < 0.3:
            await message.channel.send(message.author.display_name + "님 안녕하세요!")
        elif random.random() < 0.6:
            await message.channel.send(message.author.display_name + "님 좋은 하루 보내세요!")
        else:
            await message.channel.send(message.author.display_name + "님 반갑습니다!")

    if "시발" in message.content or "씨발" in message.content or "ㅅㅂ" in message.content or "ㅈㄴ" in message.content:
        await message.channel.send(message.author.display_name + "님 욕은 좋지 않은 습관입니다")

# Get new information from link per 0.1min (6 sec)
@tasks.loop(minutes=0.5)
async def news_sender(channel):
    global last_scraped_title
    new_scraped_news = scrape_news()

    # new_scraped news로부터 제목 text 정보만 가져오기
    new_scraped_title = new_scraped_news["topictitle"].find('h1').text
    if new_scraped_title != last_scraped_title:
        print(f"[New!] {new_scraped_title}")
        await send_news(channel, new_scraped_news, new_scraped_title)
        last_scraped_title = new_scraped_title
    
    # 만약 기존에 가져왔던 뉴스랑 겹치면 디스코드로 보내지 않고 다음 뉴스를 기다림
    else:
        print("Keep waiting for another news ...")

# 뉴스 스크랩하는 함수
def scrape_news():
    url = 'https://news.hada.io/new'
    baseurl = 'https://news.hada.io/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    news_container = soup.find(class_='topic_row')
    topictitle = news_container.find(class_='topictitle')
    topicdesc = news_container.find(class_='topicdesc')
    return {"baseurl": baseurl, "topictitle": topictitle, "topicdesc": topicdesc}

# 디스코드로 뉴스를 보내는 함수
async def send_news(channel, news, title):
    # Extract the link within the 'a' tag
    link_desc = news["topicdesc"].find('a')['href'].strip()
    news_info = f'{"# "+title}\n- Geek News 링크 : {news["baseurl"]+link_desc}'
    await channel.send(news_info)

bot.run(TOKEN)
driver.close()
