import discord
import os
import time
import random
from discord import app_commands
from xai_sdk import Client
from xai_sdk.chat import system, user, assistant

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")

if not DISCORD_TOKEN or not XAI_API_KEY:
    print("❌ Missing tokens!")
    exit(1)

print("✅ Tokens loaded successfully!")

xai_client = Client(api_key=XAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} is online!")


@tree.command(name="ask", description="Chat with Grok")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        chat = xai_client.chat.create(model="grok-4")
        chat.append(system("You are a helpful and fun Grok bot."))
        chat.append(user(question))
        response = await chat.sample()
        await interaction.followup.send(response.text)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:200]}")


@tree.command(name="imagine", description="Generate images")
@app_commands.describe(prompt="Describe the image")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        await interaction.followup.send("🎨 Generating...")
        response = xai_client.image.sample(prompt=prompt)
        embed = discord.Embed(title="Grok Imagine", description=prompt[:200], color=0xFF00FF)
        embed.set_image(url=response.images[0].url)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:200]}")


@tree.command(name="help", description="Show commands")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("Use /ask and /imagine")


client.run(DISCORD_TOKEN)