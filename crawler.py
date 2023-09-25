import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup

# Store the last scraped news
last_scraped_title = ""

# Set default intent for discord client
intents = discord.Intents.default()
intents.typing = False
intents.presences = False

# Bot TOKEN, SERVER ID, CHANNEL ID
TOKEN = 'YOUR_TOKEN'
server_id = YOUR_SERVER_ID
channel_id = YOUR_CHANNEL_ID
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    guild = discord.utils.get(bot.guilds, id=GUILD_ID)
    channel = discord.utils.get(guild.text_channels, id=CHANNEL_ID)
    # Start the news scraping task
    news_sender.start(channel)

# Get new information from link per 0.1min (6 sec)
@tasks.loop(minutes=0.1)
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
    link = news["topictitle"].find('a')['href'].strip()
    link_desc = news["topicdesc"].find('a')['href'].strip()
    news_info = f'{"# "+title}\n- 원본 링크 : {link}\n- 긱뉴스 링크 : {news["baseurl"]+link_desc}'
    await channel.send(news_info)

bot.run(TOKEN)
