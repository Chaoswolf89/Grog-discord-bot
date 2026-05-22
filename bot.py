import discord
import os
import asyncio
from discord import app_commands
from xai_sdk import Client
from xai_sdk.chat import system, user

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")

if not DISCORD_TOKEN or not XAI_API_KEY:
    print("❌ Missing DISCORD_TOKEN or XAI_API_KEY!")
    exit(1)

# Initialize Grok client
xai_client = Client(api_key=XAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot is online as {client.user} on {len(client.guilds)} server(s)")

# Slash Command: /ask
@tree.command(name="ask", description="Ask Grok anything")
@app_commands.describe(question="Your question for Grok")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()

    try:
        chat = xai_client.chat.create(model="grok-4")  # or "grok-3" / "grok-2"
        chat.append(system("You are a helpful, witty, and truthful assistant."))
        chat.append(user(question))

        response = await chat.sample()
        
        # Split long responses if needed
        if len(response.text) > 1900:
            await interaction.followup.send(response.text[:1900])
            await interaction.followup.send(response.text[1900:])
        else:
            await interaction.followup.send(response.text)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

# Optional: Respond when mentioned
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if client.user.mentioned_in(message):
        await message.channel.send("Hey! Use `/ask` to talk to me 😊")

client.run(DISCORD_TOKEN)