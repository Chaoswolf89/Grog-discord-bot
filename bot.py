import discord
import os
import time
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

xai_client = Client(api_key=XAI_API_KEY)

conversation_memory = {}
user_cooldowns = {}

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def is_owner(interaction: discord.Interaction):
    return interaction.user.id == BOT_OWNER_ID


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} is online on {len(client.guilds)} servers!")


# ===================== IMAGINE (NSFW) =====================
@tree.command(name="imagine", description="Generate images (NSFW allowed)")
@app_commands.describe(prompt="Describe the image")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        await interaction.followup.send("🎨 Generating...")
        response = xai_client.image.sample(prompt=prompt)
        embed = discord.Embed(title="Generated Image", description=prompt, color=0xFF00FF)
        embed.set_image(url=response.images[0].url)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")


# ===================== BASIC COMMANDS =====================
@tree.command(name="ask", description="Chat with Grok")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.send_message("Chat feature is ready!")

@tree.command(name="help", description="Show commands")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("Use `/ask` and `/imagine`")


# ===================== OWNER COMMANDS =====================
@tree.command(name="servers", description="List servers (Owner only)")
async def servers(interaction: discord.Interaction):
    if not is_owner(interaction):
        return await interaction.response.send_message("Owner only", ephemeral=True)
    await interaction.response.send_message(f"Bot is in {len(client.guilds)} servers.")


client.run(DISCORD_TOKEN)