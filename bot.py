# =============================================
# GROK DISCORD BOT - CLEAN + EXPLICIT VERSION
# =============================================

import discord
import os
import time
import json
import random
from discord import app_commands
from xai_sdk import Client
from xai_sdk.chat import system, user, assistant

# ==================== CONFIG ====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", 0))

if not DISCORD_TOKEN or not XAI_API_KEY:
    print("❌ Missing DISCORD_TOKEN or XAI_API_KEY!")
    exit(1)

print("✅ Tokens loaded successfully!")
print(f"   Discord token starts with: {DISCORD_TOKEN[:4]}... ends with: ...{DISCORD_TOKEN[-4:]}")
print(f"   XAI key starts with: {XAI_API_KEY[:6]}")

xai_client = Client(api_key=XAI_API_KEY)

# ==================== MEMORY ====================
MEMORY_FILE = "conversation_memory.json"
conversation_memory = {}
user_cooldowns = {}
MAX_HISTORY = 12
COOLDOWN_SECONDS = 6
START_TIME = time.time()

def load_memory():
    global conversation_memory
    try:
        with open(MEMORY_FILE, "r") as f:
            conversation_memory = json.load(f)
    except:
        conversation_memory = {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(conversation_memory, f, indent=2)

load_memory()

def is_owner(interaction: discord.Interaction):
    return interaction.user.id == BOT_OWNER_ID

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ==================== EVENTS ====================
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} is online on {len(client.guilds)} servers!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if client.user.mentioned_in(message):
        replies = ["Yeah? What's up?", "You rang?", "I'm here. What's on your mind?", "Sup. Hit me with it.", "You got my attention 👀"]
        await message.channel.send(random.choice(replies))

# ==================== COMMANDS ====================

@tree.command(name="ask", description="Chat with Grok (with memory)")
@app_commands.describe(question="What do you want to ask?")
async def ask(interaction: discord.Interaction, question: str):
    user_id = str(interaction.user.id)
    now = time.time()

    if user_id in user_cooldowns and now - user_cooldowns[user_id] < COOLDOWN_SECONDS:
        await interaction.response.send_message("⏳ Slow down a bit.", ephemeral=True)
        return
    user_cooldowns[user_id] = now

    await interaction.response.defer()
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []

    try:
        chat = xai_client.chat.create(model="grok-4")   # ← FIXED
        chat.append(system("You are Grok, helpful, witty, and a little chaotic. Remember previous messages."))

        for msg in conversation_memory[user_id][-MAX_HISTORY:]:
            if msg["role"] == "user":
                chat.append(user(msg["content"]))
            else:
                chat.append(assistant(msg["content"]))

        chat.append(user(question))
        response = await chat.sample()
        reply_text = response.text

        conversation_memory[user_id].append({"role": "user", "content": question})
        conversation_memory[user_id].append({"role": "assistant", "content": reply_text})
        save_memory()

        await interaction.followup.send(reply_text)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:200]}")

@tree.command(name="imagine", description="Generate images with Grok (NSFW allowed)")
@app_commands.describe(prompt="Describe what you want to see")
async def imagine(interaction: discord.Interaction, prompt: str):
    user_id = str(interaction.user.id)
    now = time.time()

    if user_id in user_cooldowns and now - user_cooldowns[user_id] < COOLDOWN_SECONDS:
        await interaction.response.send_message("⏳ Slow down.", ephemeral=True)
        return
    user_cooldowns[user_id] = now

    await interaction.response.defer()
    try:
        await interaction.followup.send("🎨 Generating...")

        response = xai_client.image.sample(
            prompt=prompt,
            model="grok-imagine-image-quality"   # ← FIXED
        )

        embed = discord.Embed(title="Grok Imagine", description=prompt[:200], color=0xFF00FF)
        embed.set_image(url=response.images[0].url)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:200]}")

@tree.command(name="help", description="Show all commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Grok Bot Commands", color=0x00FFAA)
    embed.add_field(name="/ask [question]", value="Chat with Grok (remembers your conversation)", inline=False)
    embed.add_field(name="/imagine [prompt]", value="Generate images (NSFW allowed)", inline=False)
    embed.add_field(name="/ping", value="Check bot latency", inline=True)
    embed.add_field(name="/uptime", value="How long the bot has been running", inline=True)
    embed.add_field(name="/stats", value="Show your memory & cooldown status", inline=True)
    embed.add_field(name="/memory", value="Clear your conversation memory", inline=True)
    if is_owner(interaction):
        embed.add_field(name="/servers", value="List all servers (Owner only)", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(client.latency * 1000)}ms")

@tree.command(name="uptime", description="How long the bot has been running")
async def uptime(interaction: discord.Interaction):
    uptime_seconds = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await interaction.response.send_message(f"⏱️ Uptime: {hours}h {minutes}m {seconds}s")

@tree.command(name="stats", description="Show your memory and cooldown stats")
async def stats(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    mem_count = len(conversation_memory.get(user_id, []))
    await interaction.response.send_message(
        f"**Your stats:**\n"
        f"• Messages in memory: {mem_count}\n"
        f"• Cooldown active: {'Yes' if user_id in user_cooldowns else 'No'}"
    )

@tree.command(name="memory", description="Clear your conversation memory")
async def memory_clear(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in conversation_memory:
        conversation_memory[user_id] = []
        save_memory()
        await interaction.response.send_message("🧹 Your conversation memory has been cleared.")
    else:
        await interaction.response.send_message("No memory to clear.")

@tree.command(name="servers", description="List all servers (Owner only)")
async def servers(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        return
    guilds = [f"• {g.name} ({g.member_count} members)" for g in client.guilds]
    await interaction.response.send_message("**Servers I'm in:**\n" + "\n".join(guilds))

client.run(DISCORD_TOKEN)