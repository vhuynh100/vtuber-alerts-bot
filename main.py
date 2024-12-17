import os
import discord
from googleapiclient.discovery import build
from discord.ext import commands, tasks
from dotenv import load_dotenv
import requests
import xml.etree.ElementTree as ET

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# List of YouTube channel IDs (multiple VTubers)
YOUTUBE_CHANNEL_IDS = [
    # "UCIeSUTOTkF9Hs7q3SGcO-Ow", # Elira Pendora
    # "UCJubINhCcFXlsBwnHp0wl_g", # Maimoto Keisuke
    # "UCwaS8_S7kMiKA3izlTWHbQg",  # Maria Marionette
    # "UCBURM8S4LH7cRZ0Clea9RDA", # Reimu Endou,
    "UChKXd7oqD18qiIYBoRIHTlw", # Meloco Kyoran
]

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store the user's chosen channel
active_channel_id = None

# Track video IDs already checked
checked_videos = set()

def fetch_recent_video_ids(channel_id):
    """Fetch recent video IDs from a YouTube channel's RSS feed."""
    video_ids = []
    response = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}") # Send an HTTP GET request

    if response.status_code == 200:
        root = ET.fromstring(response.content) # Parse XML content
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            video_id = entry.find("{http://www.w3.org/2005/Atom}id").text.split(":")[-1]
            video_ids.append(video_id)
    else:
        print(f"Error: Unable to fetch RSS feed for channel id: {channel_id}. Status code: {response.status_code}")

    return video_ids

def check_videos_live(video_ids):
    """Check if videos are live using the YouTube API."""
    live_videos = [] # (title, link) tuples
    if not video_ids:
        return live_videos # No videos to check
    
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "id": ",".join(video_ids),  # Comma-separated video IDs
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(url, params)
    if response.status_code == 200:
        data = response.json()
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            if snippet.get("liveBroadcastContent") == "live": # Check if the stream has started
                video_id = item["id"]
                title = item["snippet"]["title"]
                link = f"https://www.youtube.com/watch?v={video_id}"
                live_videos.append((title, link))
    else:
        print(f"Error: Unable to fetch video details. Status code: {response.status_code}")

    return live_videos

async def check_for_live_streams():
    """Fetch recent videos, check if they are live, and notify Discord."""
    if active_channel_id is None:
            return  # Don't proceed if no channel is set

    global checked_videos
    for channel_id in YOUTUBE_CHANNEL_IDS:
        video_ids = fetch_recent_video_ids(channel_id)
        
        new_videos = [video for video in video_ids if video not in checked_videos] # Filter out already-checked videos
        if not new_videos:
            continue  # Skip if no new videos to check
        
        live_videos = check_videos_live(new_videos)

        for title, link in live_videos:
            checked_videos.update(new_videos)
            channel = bot.get_channel(active_channel_id)
            if channel:
                await channel.send(f"🎉 **{title}** is live! Watch here: {link}")

"""Discord Bot Functions"""
@bot.command(name="setchannel")
async def set_channel(ctx):
    global active_channel_id
    active_channel_id = ctx.channel.id
    await ctx.send(f"✅ This channel (`{ctx.channel.name}`) is now set for VTuber live notifications!")

@tasks.loop(seconds=15)
async def periodic_live_stream_check():
    await check_for_live_streams()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    periodic_live_stream_check.start()

bot.run(DISCORD_TOKEN)
