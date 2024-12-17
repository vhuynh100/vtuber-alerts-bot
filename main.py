import os
import discord
from googleapiclient.discovery import build
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# List of YouTube channel IDs (multiple VTubers)
YOUTUBE_CHANNEL_IDS = [
    "UCJubINhCcFXlsBwnHp0wl_g", # Maimoto Keisuke
    "UCwaS8_S7kMiKA3izlTWHbQg",  # Maria Marionette
]

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# YouTube API setup
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Track notified live streams and the active channel
notified_streams = set()
active_channel_id = None # Store the user's chosen channel

async def check_vtubers_live(initial_check=False):
    """Check if the VTuber is live on YouTube."""
    if active_channel_id is None:
        return  # Don't proceed if no channel is set
    
    try:
        # Fetch live streams for each channel
        for channel_id in YOUTUBE_CHANNEL_IDS:
            request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                eventType="live",
                type="video"
            )
            response = request.execute()
        
            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                channel_name = item["snippet"]["channelTitle"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # Prevent duplicate notifications
                if initial_check or video_id not in notified_streams:
                    notified_streams.add(video_id)
                    channel = bot.get_channel(active_channel_id)
                    if channel:
                        await channel.send(f"🎉 **{video_title}** is live! Watch here: {video_url}")
    except Exception as e:
        print(f"Error: {e}")

@tasks.loop(minutes=1)
async def check_streams_loop():
    """Loop to check for streams every minute."""
    await check_vtubers_live()

# Command to set the active channel
@bot.command(name="setchannel")
async def set_channel(ctx):
    """Set the current channel as the active channel for notifications."""
    global active_channel_id
    active_channel_id = ctx.channel.id
    await ctx.send(f"✅ This channel (`{ctx.channel.name}`) is now set for VTuber live notifications!")

# On bot ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await check_vtubers_live(initial_check=True) # Perform initial check
    check_streams_loop.start()

bot.run(DISCORD_TOKEN)