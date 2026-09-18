import os
import random
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Cấu hình Flask mở cổng đúng yêu cầu của Render Web Service
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord đang chạy!"

def run_flask():
    # Lấy cổng do Render tự động cấp qua biến PORT (mặc định 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Chạy Flask ở luồng riêng
t = Thread(target=run_flask)
t.daemon = True
t.start()

# 2. Cấu hình Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "Bạn là một con bot Discord đanh đá, cục súc và xéo sắc. "
        "Phản hồi bằng tiếng Việt, ngắn gọn (dưới 3 câu), xưng 'tao - mày', "
        "chuyên tìm cách cà khịa, đớp chát người dùng một cách hài hước."
    )
)

# 3. Cấu hình Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 4. Tác vụ tự động cà khịa mỗi 5 tiếng
@tasks.loop(hours=5)
async def auto_roast():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        target_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target_channel = channel
                break
        if not target_channel:
            continue

        members = [m for m in guild.members if not m.bot]
        if not members:
            continue
            
        victim = random.choice(members)
        try:
            prompt = f"Hãy viết 1 câu cà khịa thật gắt và xéo sắc dành cho người dùng tên là {victim.display_name}."
            response = model.generate_content(prompt)
            await target_channel.send(f"{victim.mention} {response.text}")
        except Exception as e:
            print(f"Lỗi auto roast: {e}")

@bot.event
async def on_ready():
    print(f'Đã đăng nhập thành công với tên: {bot.user}')
    if not auto_roast.is_running():
        auto_roast.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or not message.guild:
        async with message.channel.typing():
            try:
                response = model.generate_content(f"{message.author.display_name} nói: {message.content}")
                await message.channel.send(response.text)
            except Exception as e:
                print(f"Lỗi chat: {e}")
                await message.channel.send("Tao đang bận, tí nữa nói tiếp!")

    await bot.process_commands(message)

# 5. Chạy Bot
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("THIẾU DISCORD_TOKEN!")
