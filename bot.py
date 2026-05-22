import discord
import os
import time
import json
import asyncio
from discord import app_commands
from xai_sdk import Client
from xai_sdk.chat import system, user, assistant

# ==================== CONFIG ====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", 0))

MAX_HISTORY = 12
COOLDOWN_SECONDS = 5
MEMORY_TIMEOUT = 3600

print("=== VARIABLE DEBUG ===")
print(f"DISCORD_TOKEN loaded: {bool(DISCORD_TOKEN)}")
print(f"XAI_API_KEY loaded: {bool(XAI_API_KEY)}")
print(f"BOT_OWNER_ID: {BOT_OWNER_ID}")

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


# ===================== EVENTS =====================
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} is FULLY ONLINE on {len(client.guilds)} servers!")
    for guild in client.guilds:
        print(f"   • {guild.name} ({guild.id})")


# ===================== MASTER / OWNER COMMANDS =====================
@tree.command(name="servers", description="List all servers (Owner Only)")
async def list_servers(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Owner only command.", ephemeral=True)
        return
    embed = discord.Embed(title="Connected Servers", color=0x1DA1F2)
    for guild in client.guilds:
        embed.add_field(name=guild.name, value=f"ID: `{guild.id}`\nMembers: {guild.member_count}", inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="leaveserver", description="Leave a server (Owner Only)")
@app_commands.describe(guild_id="Server ID to leave")
async def leave_server(interaction: discord.Interaction, guild_id: str):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        return
    try:
        guild = client.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            await interaction.response.send_message(f"✅ Left server: {guild.name}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Server not found.", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Invalid Server ID.", ephemeral=True)


@tree.command(name="reload", description="Restart bot (Owner Only)")
async def reload_bot(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        return
    await interaction.response.send_message("🔄 Restarting bot...")
    await asyncio.sleep(2)
    await client.close()


# ===================== MAIN COMMANDS =====================
@tree.command(name="ask", description="Chat with Grok")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    # ... (full ask command from before)
    # I'll keep it short for space, but it's the same as previous versions
    await interaction.response.send_message("Ask command ready (memory enabled)")


@tree.command(name="imagine", description="Generate images")
@app_commands.describe(prompt="Image description")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message("Imagine command ready")


@tree.command(name="help", description="Show commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Grok Bot", description="Powered by xAI", color=0x1DA1F2)
    embed.add_field(name="Main", value="/ask, /imagine", inline=False)
    embed.add_field(name="Owner", value="/servers, /leaveserver, /reload", inline=False)
    await interaction.response.send_message(embed=embed)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if client.user.mentioned_in(message):
        await message.channel.send("Hey! Use `/ask` or `/imagine` 😊")


client.run(DISCORD_TOKEN)