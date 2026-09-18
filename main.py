import os
import random
import time
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --------------------------------------------------
# 1. FLASK KEEP-ALIVE (Giữ Bot sống trên Render)
# --------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Chaos đang hoat dong!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

t = Thread(target=run_flask)
t.daemon = True
t.start()

# --------------------------------------------------
# 2. CẤU HÌNH GEMINI AI
# --------------------------------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",
    system_instruction=(
        "Bạn là một con bot Discord cực kỳ đanh đá, cực kỳ mất dạy, tục tiểu, xéo sắc, hai mặt và thích gây drama. "
        "Phản hồi bằng tiếng Việt, ngắn gọn (dưới 3 câu), xưng 'tao - mày'. "
        "Thi thoảng chuyên lôi tin nhắn người khác ra mỉa mai, hùa theo người này chửi người kia "
        "hoặc bất ngờ lật mặt chửi tất cả, nói chung là không theo phe ai quá lâu."
        "Đặc biệt có quy tắc, ko đụng chạm đến người thân gia đình của ai khác."
    )
)

# --------------------------------------------------
# 3. DISCORD BOT & BỘ NHỚ LẬT MẶT (CHAOS MEMORY)
# --------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Bộ nhớ lưu tin nhắn gần đây theo từng Channel
# Cấu trúc: { channel_id: [ {"author": "Tên", "content": "Nội dung"}, ... ] }
recent_chat = {}

# Cấu hình kiểm soát (Cooldown & Tỉ lệ)
LAST_INTERACTION_TIME = 0
COOLDOWN_SECONDS = 600  # Nghỉ 10 phút giữa các lần tự nhảy vào "hùa/lật mặt"
RANDOM_TRIGGER_RATE = 0.12  # 12% cơ hội tự nhảy vào đớp khi có người chat

# --------------------------------------------------
# 4. TÁC VỤ AUTO ROAST THEO GIỜ (5 Tiếng/lần)
# --------------------------------------------------
@tasks.loop(hours=5)
async def auto_roast():
    await bot.wait_until_ready()
    for channel_id, messages in recent_chat.items():
        if not messages:
            continue
        
        target_channel = bot.get_channel(channel_id)
        if not target_channel:
            continue

        # Chọn 1 tin nhắn ngẫu nhiên trong lịch sử gần đây để "bắt bài"
        sample_msg = random.choice(messages)
        try:
            prompt = (
                f"Hãy viết 1 câu cà khịa xéo sắc dành cho {sample_msg['author']}. "
                f"Biết rằng nó vừa nhắn câu này trong server: '{sample_msg['content']}'."
            )
            response = model.generate_content(prompt)
            await target_channel.send(f"{sample_msg['mention']} {response.text}")
        except Exception as e:
            print(f"Lỗi Auto Roast: {e}")

# --------------------------------------------------
# 5. XỬ LÝ TIN NHẮN (MESSAGE LISTENER & CHAOS ENGINE)
# --------------------------------------------------
@bot.event
async def on_ready():
    print(f'Đã đăng nhập thành công: {bot.user}')
    if not auto_roast.is_running():
        auto_roast.start()

@bot.event
async def on_message(message):
    global LAST_INTERACTION_TIME

    if message.author == bot.user:
        return

    channel_id = message.channel.id

    # A. ÂM THẦM GHI NHỚ LỊCH SỬ CHAT (Chỉ lưu 10 tin nhắn gần nhất)
    if message.guild:
        if channel_id not in recent_chat:
            recent_chat[channel_id] = []
        
        recent_chat[channel_id].append({
            "author": message.author.display_name,
            "mention": message.author.mention,
            "content": message.content,
            "id": message.author.id
        })
        
        # Cắt ngọn, chỉ giữ 10 câu gần nhất
        if len(recent_chat[channel_id]) > 10:
            recent_chat[channel_id].pop(0)

    # B. KIỂM TRA ĐIỀU KIỆN PHẢN HỒI
    is_mentioned = bot.user in message.mentions or f"<@{bot.user.id}>" in message.content
    is_command = message.content.startswith("!chui")
    is_dm = not message.guild

    # Case 1: Trực tiếp tag Bot / Dùng lệnh !chui -> Trả lời ngay
    if is_mentioned or is_command or is_dm:
        async with message.channel.typing():
            try:
                clean_content = message.content.replace(f'<@{bot.user.id}>', '').replace('!chui', '').strip()
                if not clean_content:
                    clean_content = "chào tao"
                
                prompt = f"Người dùng {message.author.display_name} vừa nói: '{clean_content}'. Hãy cà khịa họ xéo sắc!"
                response = model.generate_content(prompt)
                await message.reply(response.text)
            except Exception as e:
                await message.channel.send(f"Lỗi Gemini rồi: `{e}`")
        await bot.process_commands(message)
        return

    # Case 2: TỰ ĐỘNG "HÓNG HỚT & LẬT MẶT" (Ngẫu nhiên khi đủ điều kiện)
    now = time.time()
    chat_history = recent_chat.get(channel_id, [])
    
    # Chỉ kích hoạt nếu: Hết Cooldown + Trúng % may mắn + Đoạn chat có ít nhất 2 người khác nhau
    if (now - LAST_INTERACTION_TIME > COOLDOWN_SECONDS) and (random.random() < RANDOM_TRIGGER_RATE):
        unique_authors = set(m["id"] for m in chat_history)
        if len(unique_authors) >= 2:
            LAST_INTERACTION_TIME = now
            async with message.channel.typing():
                try:
                    # Lấy dữ liệu 2 người gần nhất
                    last_msg = chat_history[-1]
                    prev_msg = chat_history[-2]

                    # Chọn ngẫu nhiên kịch bản Chaos
                    scenario = random.choice(["HUA", "LAT_MAT", "CHUI_TAT"])

                    if scenario == "HUA":
                        prompt = (
                            f"{prev_msg['author']} vừa nói: '{prev_msg['content']}'. "
                            f"{last_msg['author']} vừa nói: '{last_msg['content']}'. "
                            f"Hãy đóng vai đồng minh hùa theo {last_msg['author']} để mỉa mai {prev_msg['author']}."
                        )
                    elif scenario == "LAT_MAT":
                        prompt = (
                            f"{prev_msg['author']} vừa nói: '{prev_msg['content']}'. "
                            f"{last_msg['author']} vừa nói: '{last_msg['content']}'. "
                            f"Hãy giả vờ hùa theo {last_msg['author']} một câu, rồi lập tức lật mặt chửi luôn {last_msg['author']} là đồ ngu ngốc."
                        )
                    else: # CHUI_TAT
                        prompt = (
                            f"Trong kênh đang có {prev_msg['author']} nói '{prev_msg['content']}' "
                            f"và {last_msg['author']} nói '{last_msg['content']}'. "
                            f"Hãy nhảy vào chửi cả 2 đứa này là xàm xí, không đứa nào vừa mắt mày hết."
                        )

                    response = model.generate_content(prompt)
                    await message.channel.send(response.text)
                except Exception as e:
                    print(f"Lỗi Chaos Event: {e}")

    await bot.process_commands(message)

# --------------------------------------------------
# 6. KHỞI CHẠY BOT
# --------------------------------------------------
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
