import os
import discord
from googleapiclient.discovery import build
from discord.ext import commands, tasks
from dotenv import load_dotenv
import requests
import xml.etree.ElementTree as ET
import time
import json

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# List of YouTube channel IDs (multiple VTubers)
youtube_channel_ids = [
    ## Nijisanji EN
    "UCIeSUTOTkF9Hs7q3SGcO-Ow", # Elira Pendora
    # "UCwaS8_S7kMiKA3izlTWHbQg",  # Maria Marionette
    # "UCBURM8S4LH7cRZ0Clea9RDA", # Reimu Endou
    # "UChKXd7oqD18qiIYBoRIHTlw", # Meloco Kyoran

    ## Hololive EN Girls
    # Myth
    # "UCHsx4Hqa-1ORjQTh9TYDhww",  # Takanashi Kiara
    # "UCL_qhgtOy0dy1Agp8vkySQg",  # Mori Calliope
    # "UCMwGHR0BTZuLsmjY_NT5Pwg",  # Ninomae Ina'nis
    # "UCoSrY_IQQVpmIRZ9Xf-y93g",  # Gawr Gura

    # # Promise
    # "UC8rcEBzJSleTkf_-agPM20g",  # IRyS
    # "UCO_aKKYxn4tvrqPjcTzZ6EQ",  # Ceres Fauna
    # "UCmbs8T6MWqUHP1tIQvSgKrg",  # Ouro Kronii
    # "UC3n5uGu18FoCy23ggWWp8tA",  # Nanashi Mumei
    # "UCgmPnx-EEeOrZSg5Tiw7ZRQ",  # Hakos Baelz

    # # Advent
    # "UCgnfPPb9JI3e9A4cXHnWbyg",  # Shiori Novella
    # "UC9p_lqQ0FEDz327Vgf5JwqA",  # Koseki Bijou 	
    # "UC_sFNM0z0MWm9A6WlKPuMMg",  # Nerissa Ravencroft
    # "UCt9H_RpQzhxzlyBxFqrdHqA",  # FUWAMOCO

    # # Justice
    # "UCW5uhrG1eCBYditmhL0Ykjw",  # Elizabeth Rose Bloodflame
    # "UCl69AEx4MdqMZH7Jtsm7Tig",  # Raora Panthera
    # "UCDHABijvPBnJm7F-KlNME3w",  # Gigi Murin
    # "UCvN5h1ShZtc7nly3pezRayg",  # Cecilia Immergreen
]

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot) # Initialize CommandTree for slash commands

routes = {} # {discord_channel_id: [yt_channel_1, yt_channel_2, ...]}

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

    return video_ids[:5]

def check_videos_live(video_ids):
    """Check if videos are live using the YouTube API."""
    live_videos = [] # (channel_title, title, link) tuples
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
                channel_title = item["snippet"]["channelTitle"]
                link = f"https://www.youtube.com/watch?v={video_id}"
                live_videos.append((video_id, channel_title, title, link))
    else:
        print(f"Error: Unable to fetch video details. Status code: {response.status_code}")

    return live_videos

async def check_for_live_streams():
    """Fetch recent videos, check if they are live, and notify Discord."""
    global checked_videos, routes

    for channel_id in youtube_channel_ids:
        video_ids = fetch_recent_video_ids(channel_id)
        
        new_videos = [video for video in video_ids if video not in checked_videos] # Filter out already-checked videos
        if not new_videos:
            # print("skipping channel because no new videos to check...") # TODO: Delete
            continue  # Skip if no new videos to check
        
        # print("new videos detected. checking if videos are live...") # TODO: Delete
        live_videos = check_videos_live(new_videos)

        for video_id, channel_title, title, link in live_videos:
            checked_videos.update(new_videos)
            
            # Notify only the appropriate Discord channels
            for discord_channel_id, streamer_channel_ids in routes.items():
                if channel_id in streamer_channel_ids:
                    channel = bot.get_channel(discord_channel_id)
                    if channel:
                        embed = discord.Embed(
                            color=discord.Color.blue(),
                            title="LIVE on YouTube",
                            url=link,
                            description=title,
                        )
                        embed.set_author(
                            name=channel_title,
                        )
                        embed.set_thumbnail(
                            # url="https://upload.wikimedia.org/wikipedia/commons/4/48/Hololive_logo.png" # TODO: Dynamically add logo
                            url="https://upload.wikimedia.org/wikipedia/commons/archive/7/73/20240308191045%21Nijisanji_Logo.png"
                        )
                        embed.add_field(name=":clock3: Live", value=f"<t:{int(time.time())}:R>", inline=True)
                        # embed.add_field(name="Viewers", value=f"{} watching now", inline=True) # TODO: use "concurrentViewers" field in YT API response JSON
                        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                        embed.set_image(url=thumbnail_url)
                        # embed.set_footer(text="Youtube • 7/30/2023 4:01 PM") # TODO: Add stream date
                        await channel.send(embed=embed)

def get_channel_name(channel_id: str) -> str:
    """Fetch the channel name from YouTube's RSS feed."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            root = ET.fromstring(response.content)
            title_element = root.find("{http://www.w3.org/2005/Atom}title")
            if title_element is not None:
                return title_element.text
        except ET.ParseError as e:
            print(f"Error parsing RSS feed: {e}")
    else:
        print(f"Failed to fetch RSS feed for channel {channel_id}. Status code: {response.status_code}")
    
    return "Unknown"

def save_routes():
    """Save routes to a file to persist routes dict"""
    with open("routes.json", "w") as f:
        json.dump(routes, f)

def load_routes():
    """Load routes from file"""
    global routes
    try:
        with open("routes.json", "r") as f:
            routes = json.load(f)
    except FileNotFoundError:
        routes = {}

"""Discord Bot Functions"""
# @tree.command(name="route", description="Configure a route")
# async def configure_route(interaction: discord.Interaction):
    # Configure a route (view list)

@tree.command(name="assign", description="Assign a streamer to a route")
async def assign_to_route(interaction: discord.Interaction, streamer_channel_id: str):
    """ Add a YouTube channel ID to this Discord channel's notification list. """
    # 2 options: channel (string: channel), mention (string: role or "None")
    global routes
    discord_channel_id = interaction.channel_id

    streamer_name = get_channel_name(streamer_channel_id)

    if discord_channel_id not in routes:
        routes[discord_channel_id] = []

    if streamer_channel_id not in routes[discord_channel_id]:
        routes[discord_channel_id].append(streamer_channel_id)
        await interaction.response.send_message(f"✅ Subscribed to notifications for `{streamer_name}` in this Discord channel.")
    else:
        await interaction.response.send_message(f"⚠️ This channel is already subscribed to notifications for `{streamer_name}`.")

    save_routes()

@tree.command(name="unassign", description="Remove a streamer from a route")
async def unassign_from_route(interaction: discord.Interaction, streamer_channel_id: str):
    """ Remove a YouTube channel ID from this Discord channel's notification list. """
    global routes
    discord_channel_id = interaction.channel_id

    streamer_name = get_channel_name(streamer_channel_id)

    if discord_channel_id in routes and streamer_channel_id in routes[discord_channel_id]:
        routes[discord_channel_id].remove(streamer_channel_id)
        await interaction.response.send_message(f"✅ Unsubscribed from notifications for `{streamer_name}` in this Discord channel.")
    else:
        await interaction.response.send_message(f"⚠️ This channel is not subscribed to `{streamer_name}`.")

    save_routes()

@tasks.loop(seconds=15) # TODO: Change to 3 minutes when done testing
async def periodic_live_stream_check():
    await check_for_live_streams()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_routes()
    await tree.sync() # Sync commands to the server
    periodic_live_stream_check.start()

bot.run(DISCORD_TOKEN)
