import discord
import os
import asyncio
import time
from discord import app_commands
from xai_sdk import Client
from xai_sdk.chat import system, user, assistant

# Config
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
MAX_HISTORY = 15          # Keep only last 15 messages per channel
COOLDOWN_SECONDS = 3      # Prevent spam

if not DISCORD_TOKEN or not XAI_API_KEY:
    print("❌ Missing DISCORD_TOKEN or XAI_API_KEY!")
    exit(1)

xai_client = Client(api_key=XAI_API_KEY)

# Memory: {channel_id: {"chat": chat_object, "last_used": timestamp}}
conversation_memory = {}
user_cooldowns = {}  # {user_id: timestamp}

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} is online on {len(client.guilds)} server(s)")

# Helper: Clean old memory
def cleanup_memory():
    current_time = time.time()
    for channel_id in list(conversation_memory.keys()):
        if current_time - conversation_memory[channel_id]["last_used"] > 3600:  # 1 hour
            del conversation_memory[channel_id]

# Slash Command: /ask
@tree.command(name="ask", description="Ask Grok (with memory)")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    user_id = interaction.user.id
    channel_id = str(interaction.channel_id)
    current_time = time.time()

    # Cooldown check
    if user_id in user_cooldowns and current_time - user_cooldowns[user_id] < COOLDOWN_SECONDS:
        await interaction.response.send_message("⏳ Please wait a few seconds before asking again.", ephemeral=True)
        return

    user_cooldowns[user_id] = current_time
    await interaction.response.defer()

    try:
        cleanup_memory()

        # Get or create conversation
        if channel_id not in conversation_memory:
            chat = xai_client.chat.create(model="grok-4")
            chat.append(system("You are Grok, a helpful, witty, and truthful AI built by xAI."))
            conversation_memory[channel_id] = {"chat": chat, "last_used": current_time}
        else:
            conversation_memory[channel_id]["last_used"] = current_time
            chat = conversation_memory[channel_id]["chat"]

        # Add user message
        chat.append(user(question))

        # Get response
        response = await chat.sample()
        chat.append(assistant(response.text))

        # Trim history if too long
        if len(chat.messages) > MAX_HISTORY * 2:
            chat.messages = chat.messages[-MAX_HISTORY*2:]

        # Send response
        reply = response.text
        if len(reply) > 1900:
            await interaction.followup.send(reply[:1900])
            await interaction.followup.send(reply[1900:])
        else:
            await interaction.followup.send(reply)

    except Exception as e:
        await interaction.followup.send(f"❌ Sorry, something went wrong: {str(e)[:500]}")

# Clear memory command
@tree.command(name="clear", description="Clear conversation memory in this channel")
async def clear(interaction: discord.Interaction):
    channel_id = str(interaction.channel_id)
    if channel_id in conversation_memory:
        del conversation_memory[channel_id]
        await interaction.response.send_message("🧹 Conversation memory cleared!", ephemeral=True)
    else:
        await interaction.response.send_message("No memory to clear in this channel.", ephemeral=True)

# Help command
@tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Grok Bot Commands",
        description="I'm powered by Grok from xAI!",
        color=0x00ff00
    )
    embed.add_field(name="/ask [question]", value="Talk to Grok (remembers conversation)", inline=False)
    embed.add_field(name="/clear", value="Clear memory in current channel", inline=False)
    embed.add_field(name="/help", value="Show this message", inline=False)
    await interaction.response.send_message(embed=embed)

# Mention response
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if client.user.mentioned_in(message):
        await message.channel.send("Hey! Use `/ask` to talk to me 😊")

client.run(DISCORD_TOKEN)