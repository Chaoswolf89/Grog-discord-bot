import discord
import os
import time
from discord import app_commands
from xai_sdk import Client
from xai_sdk.chat import system, user, assistant

# ==================== CONFIG ====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")

MAX_HISTORY = 12
COOLDOWN_SECONDS = 5
MEMORY_TIMEOUT = 3600

if not DISCORD_TOKEN or not XAI_API_KEY:
    print("❌ Missing DISCORD_TOKEN or XAI_API_KEY!")
    exit(1)

xai_client = Client(api_key=XAI_API_KEY)

conversation_memory = {}
user_cooldowns = {}

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ===================== EVENTS =====================
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} is online on {len(client.guilds)} servers!")
    for guild in client.guilds:
        print(f"   • {guild.name} ({guild.id})")

    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="/ask | /imagine")
    )


def cleanup_memory():
    now = time.time()
    for cid in list(conversation_memory.keys()):
        if now - conversation_memory[cid]["last_used"] > MEMORY_TIMEOUT:
            del conversation_memory[cid]


# ===================== COMMANDS =====================
@tree.command(name="ask", description="Chat with Grok (with memory)")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    user_id = interaction.user.id
    channel_id = str(interaction.channel_id)
    now = time.time()

    if user_id in user_cooldowns and now - user_cooldowns[user_id] < COOLDOWN_SECONDS:
        await interaction.response.send_message("⏳ Please wait a moment.", ephemeral=True)
        return

    user_cooldowns[user_id] = now
    await interaction.response.defer()

    try:
        cleanup_memory()
        if channel_id not in conversation_memory:
            chat = xai_client.chat.create(model="grok-4")
            chat.append(system("You are Grok, a helpful, witty, and truthful AI built by xAI."))
            conversation_memory[channel_id] = {"chat": chat, "last_used": now}
        else:
            conversation_memory[channel_id]["last_used"] = now
            chat = conversation_memory[channel_id]["chat"]

        chat.append(user(question))
        response = await chat.sample()
        chat.append(assistant(response.text))

        if len(chat.messages) > MAX_HISTORY * 2:
            chat.messages = chat.messages[-MAX_HISTORY * 2:]

        reply = response.text
        if len(reply) > 1900:
            await interaction.followup.send(reply[:1900])
            await interaction.followup.send(reply[1900:])
        else:
            await interaction.followup.send(reply)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:300]}")


@tree.command(name="imagine", description="Generate images with Grok Imagine")
@app_commands.describe(
    prompt="Describe the image",
    aspect_ratio="Image shape",
    resolution="Quality level",
    num_images="Number of images (1-4)"
)
@app_commands.choices(
    aspect_ratio=[
        app_commands.Choice(name="Square 1:1", value="1:1"),
        app_commands.Choice(name="Widescreen 16:9", value="16:9"),
        app_commands.Choice(name="Vertical 9:16", value="9:16"),
        app_commands.Choice(name="Landscape 3:2", value="3:2"),
        app_commands.Choice(name="Portrait 2:3", value="2:3"),
    ],
    resolution=[
        app_commands.Choice(name="1K Standard", value="1k"),
        app_commands.Choice(name="2K High Quality", value="2k"),
    ]
)
async def imagine(
    interaction: discord.Interaction,
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
    num_images: int = 1
):
    user_id = interaction.user.id
    now = time.time()

    if user_id in user_cooldowns and now - user_cooldowns[user_id] < COOLDOWN_SECONDS:
        await interaction.response.send_message("⏳ Please wait before generating more.", ephemeral=True)
        return

    user_cooldowns[user_id] = now
    await interaction.response.defer()

    try:
        await interaction.followup.send(f"🎨 Generating {num_images} image(s)... ({aspect_ratio}, {resolution})")

        response = xai_client.image.sample(
            prompt=prompt,
            model="grok-imagine-image-quality",
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            n=num_images
        )

        for i, img in enumerate(response.images if hasattr(response, 'images') else [response]):
            embed = discord.Embed(
                title=f"Grok Imagine #{i+1