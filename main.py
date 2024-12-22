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

company_icons = {
    "hololive": "https://upload.wikimedia.org/wikipedia/commons/4/48/Hololive_logo.png",
    "nijisanji": "https://upload.wikimedia.org/wikipedia/commons/archive/7/73/20240308191045%21Nijisanji_Logo.png",
    "indie": "",
}

# List of YouTube channel IDs
youtube_channel_ids = [
    # Nijisanji EN
    # "UCIeSUTOTkF9Hs7q3SGcO-Ow", # Elira Pendora
    # "UCu-J8uIXuLZh16gG-cT1naw", # Finana Ryugu

    # "UCwaS8_S7kMiKA3izlTWHbQg",  # Maria Marionette
    # "UCBURM8S4LH7cRZ0Clea9RDA", # Reimu Endou
    # "UChKXd7oqD18qiIYBoRIHTlw", # Meloco Kyoran
    # "UCR6qhsLpn62WVxCBK1dkLow", # Enna Alouette

    # # Hololive EN Girls
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

class Streamer:
    def __init__(self, channel_id, name, company):
        self.channel_id = channel_id
        self.name = name
        self.company = company

assignments = {
    #       discord_channel_id_1:
    #       {
    #           "streamers": [Streamer_1, Streamer_2, ...],
    #       },
}

# Track video IDs already checked
checked_videos = {} # {streamer_channel_id: set(checked_videos)}

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
    global assignments, checked_videos

    for discord_channel_id, data in assignments.items():
        streamers = data.get("streamers", [])
        
        for streamer in streamers:
            if streamer.channel_id not in checked_videos:
                checked_videos[streamer.channel_id] = set()

            video_ids = fetch_recent_video_ids(streamer.channel_id)
            
            new_videos = [video for video in video_ids if video not in checked_videos[streamer.channel_id]] # Filter out already-checked videos
            if not new_videos:
                print(f"skipping {streamer.name} because no new videos to check...") # TODO: Delete
                continue  # Skip if no new videos to check
            
            print(f"new videos detected for {streamer.name}. checking if videos are live...") # TODO: Delete
            live_videos = check_videos_live(new_videos)
            checked_videos[streamer.channel_id].update(new_videos)

            for video_id, channel_title, title, link in live_videos:
                print(f"notifying about {streamer.name}'s video {title}") # TODO: Delete
                # Notify only the appropriate Discord channels
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
                        url=company_icons.get(streamer.company, "")
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

def save_assignments():
    """Save assignments to a file to persist assignments dict"""
    with open("assignments.json", "w") as f:
        json.dump(
            {
                k: {
                    "streamers": [{"channel_id": s.channel_id, "name": s.name, "company": s.company} for s in v["streamers"]],
                }
                for k, v in assignments.items()
            },
            f,
        )

def load_assignments():
    """Load assignments from file"""
    global assignments
    try:
        with open("assignments.json", "r") as f:
            data = json.load(f)
            assignments = {
                int(k): {
                    "streamers": [Streamer(s["channel_id"], s["name"], s.get("company", "indie")) for s in v.get("streamers", [])],
                }
                for k, v in data.items()
            }
    except FileNotFoundError:
        assignments = {}

"""Discord Bot Functions"""
@tree.command(name="listassignments", description="List the streamers assigned to the Discord channel")
async def list_assignments(interaction: discord.Interaction):
    # View list of assignments
    discord_channel_id = interaction.channel_id
    channel_assignments = assignments.get(discord_channel_id, [])
    
    assignment_names = [f"`{streamer.name}`" for streamer in channel_assignments.get("streamers")]
    formatted_names = ", ".join(assignment_names) if assignment_names else "No streamers assigned."
    await interaction.response.send_message(f"✅ This Discord channel is subscribed to notifications for: {formatted_names}")

@tree.command(name="assign", description="Assign a streamer to a Discord channel")
async def assign_to_discord_channel(interaction: discord.Interaction, streamer_channel_id: str):
    """ Add a YouTube channel ID to this Discord channel's notification list. """
    # 2 options: channel (string: channel), mention (string: role or "None")
    global assignments
    discord_channel_id = interaction.channel_id

    streamer_name = get_channel_name(streamer_channel_id)
    if streamer_name == "Unknown":
        await interaction.response.send_message(f"⚠️ Could not fetch channel name. Please try again later.")
        return
    
    if "hololive" in streamer_name.lower():
        streamer_company = "hololive"
    elif "nijisanji" or "にじさんじ" in streamer_name.lower():
        streamer_company = "nijisanji"
    else:
        streamer_company = "indie"

    if discord_channel_id not in assignments:
        assignments[discord_channel_id] = {"streamers": [], "checked_videos": set()}

    streamer_to_assign = Streamer(streamer_channel_id, streamer_name, streamer_company)

    if streamer_to_assign not in assignments[discord_channel_id]["streamers"]:
        assignments[discord_channel_id]["streamers"].append(streamer_to_assign)
        await interaction.response.send_message(f"✅ Subscribed to notifications for `{streamer_to_assign.name}` in this Discord channel.")
    else:
        await interaction.response.send_message(f"⚠️ This channel is already subscribed to notifications for `{streamer_to_assign.name}`.")

    save_assignments()

@tree.command(name="unassign", description="Remove a streamer from a Discord channel")
async def unassign_from_discord_channel(interaction: discord.Interaction, streamer_channel_id: str):
    """ Remove a YouTube channel ID from this Discord channel's notification list. """
    global assignments
    discord_channel_id = interaction.channel_id

    streamer_name = get_channel_name(streamer_channel_id)

    if discord_channel_id not in assignments:
        await interaction.response.send_message(f"⚠️ This channel has no assignments.")
        return

    data = assignments[discord_channel_id]
    streamers = data.get("streamers", [])

    for streamer in streamers:
        if streamer.channel_id == streamer_channel_id:
            streamers.remove(streamer)
            await interaction.response.send_message(f"✅ Unsubscribed from notifications for `{streamer_name}` in this Discord channel.")
            if assignments[discord_channel_id] == []:
                del assignments[discord_channel_id]
            break
    else:
        await interaction.response.send_message(f"⚠️ This channel is not subscribed to `{streamer_name}`.")

    save_assignments()

@tasks.loop(minutes=5) # TODO: Change to 3 minutes when done testing
async def periodic_live_stream_check():
    await check_for_live_streams()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_assignments()
    await tree.sync() # Sync commands to the server
    periodic_live_stream_check.start()

bot.run(DISCORD_TOKEN)
