import discord
from discord.ext import commands, tasks
from llama import Llama, Dialog
import fire
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote_plus
from typing import List

# Bot TOKEN, SERVER ID, CHANNEL ID
TOKEN = 'YOUR_TOKEN'
server_id = YOUR_SERVER_ID
channel_id = YOUR_CHANNEL_ID

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix='/', intents=intents)

# Initialize Llama for text generation
generator = Llama.build(
    ckpt_dir="llama-2-7b-chat/",
    tokenizer_path="tokenizer.model",
    max_seq_len=1024,
    max_batch_size=4,
)

# Initialize global variables
dialog_prompt: Dialog = [{"role": "system", "content": "You are a kitty deep learning researcher named 'DEV' and 10-year old. Reply with English with Emoji."}]
dialogs_logs: Dialog = []
max_chat_logs: int = 10

# Initialize Selenium for web scraping
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options, service=ChromeService(ChromeDriverManager().install()))

# Store the last scraped news
last_scraped_title = ""

def answer_for_chat(query):
    global dialogs_logs
    try:
        dialog = make_usr_dialog(query)
        dialogs_logs += dialog
        dialog_temp: List[Dialog] = [dialog_prompt + dialogs_logs]
        results = generator.chat_completion(
            dialog_temp,
            max_gen_len=None,
            temperature=0.6,
            top_p=0.9,
        )
        answer = results[-1]["generation"]["content"]
        dialog = make_ai_dialog(answer)
        dialogs_logs += dialog

        if len(dialogs_logs) > max_chat_logs:
            dialogs_logs = dialogs_logs[2:]
    except Exception as e:
        dialogs_logs = []
        answer = "I could not generate message 🥲 ..."

    return answer

# Define a function to make user dialog
def make_usr_dialog(query):
    dialog = [{"role": "user", "content": query}]
    return dialog

# Define a function to make AI dialog
def make_ai_dialog(answer):
    dialog = [{"role": "assistant", "content": answer}]
    return dialog

# Define a function to scrape news
def scrape_news():
    url = 'https://news.hada.io/new'
    baseurl = 'https://news.hada.io/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    news_container = soup.find(class_='topic_row')
    topictitle = news_container.find(class_='topictitle')
    topicdesc = news_container.find(class_='topicdesc')
    return {"baseurl": baseurl, "topictitle": topictitle, "topicdesc": topicdesc}

# Define a function to send news to Discord
async def send_news(channel, news, title):
    link_desc = news["topicdesc"].find('a')['href'].strip()
    news_info = f'{"# "+title}\n- Geek News Link : {news["baseurl"]+link_desc}'
    await channel.send(news_info)

# Discord bot command to chat with Llama
@bot.command()
async def chat(ctx, *, query):
    answer = fire.Fire(answer_for_chat(query))
    await ctx.send(answer)

# Discord bot command to search for papers
@bot.command()
async def paper(ctx, *, query):
    await ctx.send(f"Okay! I'll find an arXiv paper related to {query} 🤗")
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
                        await ctx.send(f"Title: {result_title.text}\nLink: {result_link}")
                    found = True

            if not found:
                await ctx.send(f"There is no paper for {query} 🥲") 
        else:
            await ctx.send(f"There is no paper for {query} 🥲")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)} 🥲 ...")


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    server = discord.utils.get(bot.guilds, id=server_id)
    channel = discord.utils.get(server.text_channels, id=channel_id)
    # Start the news scraping task
    news_sender.start(channel)

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

# Start the bot
if __name__ == "__main__":
    bot.run(TOKEN)
    driver.close()
