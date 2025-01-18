import os
import discord
from googleapiclient.discovery import build
from discord.ext import commands, tasks
from dotenv import load_dotenv
import requests
import xml.etree.ElementTree as ET
import time
import json
from datetime import datetime

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

    # "UC4WvIIAo89_AzGUh1AZ6Dkg", # Rosemi Lovelock
    # "UCgA2jKRkqpY_8eysPUs8sjw", # Petra Gurin

    # "UCR6qhsLpn62WVxCBK1dkLow", # Enna Alouette
    # "UC47rNmkDcNgbOcM-2BwzJTQ", "Millie Parfait"
    # "UCBURM8S4LH7cRZ0Clea9RDA", # Reimu Endou
    

    # "UCwaS8_S7kMiKA3izlTWHbQg",  # Maria Marionette

    # "UCGhqxhovNfaPBpxfCruy9EA", # Fulgur Ovid

    # "UChKXd7oqD18qiIYBoRIHTlw", # Meloco Kyoran

    # # Hololive EN Girls
    # Myth
    # "UCHsx4Hqa-1ORjQTh9TYDhww",  # Takanashi Kiara
    # "UCL_qhgtOy0dy1Agp8vkySQg",  # Mori Calliope
    # "UCMwGHR0BTZuLsmjY_NT5Pwg",  # Ninomae Ina'nis
    # "UCoSrY_IQQVpmIRZ9Xf-y93g",  # Gawr Gura

    # # Promise
    # "UC8rcEBzJSleTkf_-agPM20g",  # IRyS
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

subscriptions = {
    #       discord_channel_id_1:
    #       {
    #           "streamers": [Streamer_1, Streamer_2, ...],
    #           "checked_videos": {} # Track video IDs already checked # {streamer.channel_id: {"all": set(), "live": set(), "upcoming": set()}}
    #       },
}

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
    live_videos = [] # (video_id, channel_title, title, link, scheduled_start_time, actual_start_time, concurrent_viewers) tuples
    upcoming_videos = [] # (video_id, channel_title, title, link, scheduled_start_time) tuples
    if not video_ids:
        return live_videos, upcoming_videos # No videos to check
    
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,liveStreamingDetails",
        "id": ",".join(video_ids),  # Comma-separated video IDs
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(url, params)
    if response.status_code == 200:
        data = response.json()
        # print(data) # TODO: Delete
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            live_details = item.get("liveStreamingDetails", {})

            video_id = item["id"]
            title = item["snippet"]["title"]
            channel_title = item["snippet"]["channelTitle"]
            link = f"https://www.youtube.com/watch?v={video_id}"
            scheduled_start_time = live_details.get("scheduledStartTime", "")
            
            if snippet.get("liveBroadcastContent") == "live": # Check if stream has started
                actual_start_time = live_details.get("actualStartTime", "")
                concurrent_viewers = live_details.get("concurrentViewers", "")
                live_videos.append((video_id, channel_title, title, link, scheduled_start_time, actual_start_time, concurrent_viewers))
            
            elif snippet.get("liveBroadcastContent") == "upcoming": # Check if stream is upcoming
                # scheduled_start_time = item.get("liveStreamingDetails", {}).get("scheduledStartTime", "")
                upcoming_videos.append((video_id, channel_title, title, link, scheduled_start_time))
    else:
        print(f"Error: Unable to fetch video details. Status code: {response.status_code}")

    return live_videos, upcoming_videos

async def check_for_live_streams():
    """Fetch recent videos, check if they are live, and notify Discord."""
    global subscriptions

    for discord_channel_id, data in subscriptions.items(): # 1: {"streamers": ["12345"], "checked_videos": {"12345": "all": set(123, 543, 654), "live": set(123, 543), "upcoming": set()}}
        streamers = data.get("streamers", []) # ["12345"]
        checked_videos = data.get("checked_videos", {}) # {streamer.channel_id: {"all": set(), "live": set(), "upcoming": set()}}
        # print(f"initial checked videos for {discord_channel_id}: {checked_videos}") # TODO: Delete

        for streamer in streamers: # "12345" (streamer.channel_id)
            if streamer.channel_id not in checked_videos:
                checked_videos[streamer.channel_id] = {"all": set(), "live": set(), "upcoming": set()}
                
            await recheck_upcoming(streamer, checked_videos, discord_channel_id)

            video_ids = fetch_recent_video_ids(streamer.channel_id) # video_ids = [123, 543, 654]

            new_videos = [video for video in video_ids if video not in checked_videos[streamer.channel_id]["all"]] # Filter out already-checked videos
            # new_videos = [] TODO: Delete
            if not new_videos:
                print(f"skipping {streamer.name} because no new videos to check...") # TODO: Delete
                continue  # Skip if no new videos to check

            print(f"new videos detected for {streamer.name}. checking if videos are live...") # TODO: Delete
            live_videos, upcoming_videos = check_videos_live(new_videos) # live_videos = ["123"], upcoming = ["543"]

            checked_videos[streamer.channel_id]["all"].update(new_videos) # [123, 543, 654]
            checked_videos[streamer.channel_id]["live"].update(video[0] for video in live_videos) # [123]
            checked_videos[streamer.channel_id]["upcoming"].update(video[0] for video in upcoming_videos) # [543]

            if live_videos:
                await send_embed(live_videos, streamer, discord_channel_id, "live")

            if upcoming_videos:
                await send_embed(upcoming_videos, streamer, discord_channel_id, "upcoming")

            subscriptions[discord_channel_id]["checked_videos"] = checked_videos

        save_subscriptions()

async def recheck_upcoming(streamer, checked_videos, discord_channel_id):
    # Re-check videos in the "upcoming" set to see if they are now live
    upcoming_to_check = list(checked_videos[streamer.channel_id]["upcoming"]) # [543]
    new_live_videos, new_upcoming_videos = check_videos_live(upcoming_to_check)

    # Remove videos that are now live from the "upcoming" set
    checked_videos[streamer.channel_id]["upcoming"].difference_update( # []
        video[0] for video in new_live_videos
    )

    if new_live_videos:
        await send_embed(new_live_videos, streamer, discord_channel_id, "live")

async def send_embed(videos, streamer, discord_channel_id, status):
    """ Send alert into a specific Discord channel, depending on if the stream is live or upcoming. """
    if status == "upcoming":
        for video_id, channel_title, title, link, scheduled_start_time in videos:
            channel = bot.get_channel(discord_channel_id)
            if channel:
                embed = discord.Embed(
                    color=discord.Color.blue(),
                    title="UPCOMING on YouTube",
                    url=link,
                    description=title,
                )
                embed.set_author(
                    name=channel_title, 
                )
                embed.set_thumbnail(
                    url=company_icons.get(streamer.company, "")
                )
                embed.add_field(name=":clock3: Scheduled", value=f"<t:{int(datetime.strptime(scheduled_start_time, '%Y-%m-%dT%H:%M:%SZ').timestamp())}:d> <t:{int(datetime.strptime(scheduled_start_time, '%Y-%m-%dT%H:%M:%SZ').timestamp())}:t>")
                # embed.add_field(name=":clock3: Upcoming", value=f"<t:{int(datetime.strptime(scheduled_start_time, '%Y-%m-%dT%H:%M:%SZ').timestamp())}:t>", inline=True)
                # embed.add_field(name="Viewers", value=f"{} watching now", inline=True) # TODO: use "concurrentViewers" field in YT API response JSON
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                try:
                    response = requests.head(thumbnail_url)
                    if response.status_code != 200:
                        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                except Exception as e:
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                embed.set_image(url=thumbnail_url)
                await channel.send(embed=embed)

    elif status == "live":
        for video_id, channel_title, title, link, scheduled_start_time, actual_start_time, concurrent_viewers in videos:
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
                embed.add_field(
                    name=":red_circle: Live", 
                    value=f"<t:{int(datetime.strptime(actual_start_time, '%Y-%m-%dT%H:%M:%SZ').timestamp())}:R>", 
                    inline=True
                )
                embed.add_field(
                    name=":clock3: Scheduled", 
                    value=f"<t:{int(datetime.strptime(scheduled_start_time, '%Y-%m-%dT%H:%M:%SZ').timestamp())}:d> <t:{int(datetime.strptime(scheduled_start_time, '%Y-%m-%dT%H:%M:%SZ').timestamp())}:t>", 
                    inline=True
                )
                embed.add_field(name=":busts_in_silhouette: Viewers", value=f"{int(concurrent_viewers)} watching now", inline=False)
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                try:
                    response = requests.head(thumbnail_url)
                    if response.status_code != 200:
                        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                except Exception as e:
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                embed.set_image(url=thumbnail_url)
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

def save_subscriptions():
    """Save subscriptions to a file to persist subscriptions dict. Serialize code into a usable format for JSON compatibility."""
    with open("subscriptions.json", "w") as f:
        json.dump(
            {
                k: {
                    "streamers": [{"channel_id": s.channel_id, "name": s.name, "company": s.company} for s in v["streamers"]],
                    "checked_videos": {
                        streamer_id: {
                            "all": list(video_sets.get("all", set())),
                            "live": list(video_sets.get("live", set())),
                            "upcoming": list(video_sets.get("upcoming", set())),
                        }
                        for streamer_id, video_sets in v.get("checked_videos", {}).items()
                    },
                }
                for k, v in subscriptions.items()
            },
            f,
        )

def load_subscriptions():
    """Load subscriptions from file. Deserialize JSON into usable code."""
    global subscriptions
    try:
        with open("subscriptions.json", "r") as f:
            data = json.load(f)
            subscriptions = {
                int(k): {
                    "streamers": [Streamer(s["channel_id"], s["name"], s.get("company", "indie")) for s in v.get("streamers", [])],
                    "checked_videos": {
                        streamer_id: {
                            "all": set(video_sets.get("all", [])),
                            "live": set(video_sets.get("live", [])),
                            "upcoming": set(video_sets.get("upcoming", [])),
                        }
                        for streamer_id, video_sets in v.get("checked_videos", {}).items()
                    },
                }
                for k, v in data.items()
            }
    except FileNotFoundError:
        subscriptions = {}

"""Discord Bot Functions"""
@tree.command(name="subscriptions", description="List the streamers the Discord channel is subscribed to alerts for")
async def list_subscriptions(interaction: discord.Interaction):
    # View list of subscriptions
    discord_channel_id = interaction.channel_id
    channel_subscriptions = subscriptions.get(discord_channel_id, [])

    if not channel_subscriptions:
        await interaction.response.send_message(f":warning: This Discord channel has no subscriptions.")
    else:
        subscription_names = [f"`{streamer.name} ({streamer.channel_id})`" for streamer in channel_subscriptions.get("streamers")]
        formatted_names = ", ".join(subscription_names) if subscription_names else ":warning: No streamers assigned."
        await interaction.response.send_message(f"✅ This Discord channel is subscribed to notifications for: {formatted_names}")

@tree.command(name="subscribe", description="Subscribe a Discord channel to alerts for a streamer")
async def subscribe_to_channel(interaction: discord.Interaction, streamer_channel_id: str):
    """ Add a YouTube channel ID to this Discord channel's notification list. """
    # 2 options: channel (string: channel), mention (string: role or "None")
    global subscriptions
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

    if discord_channel_id not in subscriptions:
        subscriptions[discord_channel_id] = {
            "streamers": [],
            "checked_videos": {}
        }

    streamer_to_assign = Streamer(streamer_channel_id, streamer_name, streamer_company)

    if streamer_to_assign not in subscriptions[discord_channel_id]["streamers"]:
        subscriptions[discord_channel_id]["streamers"].append(streamer_to_assign)
        await interaction.response.send_message(f"✅ Subscribed to notifications for `{streamer_to_assign.name} ({streamer_to_assign.channel_id})` in this Discord channel.")
    else:
        await interaction.response.send_message(f"⚠️ This channel is already subscribed to notifications for `{streamer_to_assign.name} ({streamer_to_assign.channel_id})`.")

    save_subscriptions()

@tree.command(name="unsubscribe", description="Remove a streamer from a Discord channel")
async def unsubscribe_from_channel(interaction: discord.Interaction, streamer_channel_id: str):
    """ Remove a YouTube channel ID from this Discord channel's notification list. """
    global subscriptions
    discord_channel_id = interaction.channel_id

    streamer_name = get_channel_name(streamer_channel_id)

    if discord_channel_id not in subscriptions:
        await interaction.response.send_message(f"⚠️ This channel has no subscriptions.")
        return

    data = subscriptions[discord_channel_id]
    streamers = data.get("streamers", [])

    for streamer in streamers:
        if streamer.channel_id == streamer_channel_id:
            streamers.remove(streamer)
            await interaction.response.send_message(f"✅ Unsubscribed from notifications for `{streamer_name} ({streamer_channel_id})` in this Discord channel.")
            if subscriptions[discord_channel_id] == []:
                del subscriptions[discord_channel_id]
            break
    else:
        await interaction.response.send_message(f"⚠️ This channel is not subscribed to `{streamer_name} ({streamer_channel_id})`.")

    save_subscriptions()

@tree.command(name="list", description="View quick list of YT channel ids available to subscribe to")
async def list_ids(interaction: discord.Interaction):
    embed = discord.Embed(
        color=discord.Color.blue(),
        title="List of channel IDs",
    )
    embed.add_field(name=":rainbow: Nijisanji", value=f"""
    Elira Pendora: UCIeSUTOTkF9Hs7q3SGcO-Ow
    Finana Ryugu: UCu-J8uIXuLZh16gG-cT1naw

    Rosemi Lovelock: UC4WvIIAo89\\_AzGUh1AZ6Dkg
    Petra Gurin: UCgA2jKRkqpY\\_8eysPUs8sjw

    Enna Alouette: UCR6qhsLpn62WVxCBK1dkLow
    Millie Parfait: UC47rNmkDcNgbOcM-2BwzJTQ
    Reimu Endou: UCBURM8S4LH7cRZ0Clea9RDA
    
    Maria Marionette: UCwaS8\\_S7kMiKA3izlTWHbQg
    Fulgur Ovid: UCGhqxhovNfaPBpxfCruy9EA
    Meloco Kyoran: UChKXd7oqD18qiIYBoRIHTlw
    """, inline=False)
    embed.add_field(name=":arrow_forward: Hololive", value=f"""
    Takanashi Kiara: UCHsx4Hqa-1ORjQTh9TYDhww  
    Mori Calliope: UCL\\_qhgtOy0dy1Agp8vkySQg  
    Ninomae Ina'nis: UCMwGHR0BTZuLsmjY\\_NT5Pwg  
    Gawr Gura: UCoSrY\\_IQQVpmIRZ9Xf-y93g  

    IRyS: UC8rcEBzJSleTkf\\_-agPM20g
    Ouro Kronii: UCmbs8T6MWqUHP1tIQvSgKrg  
    Nanashi Mumei: UC3n5uGu18FoCy23ggWWp8tA  
    Hakos Baelz: UCgmPnx-EEeOrZSg5Tiw7ZRQ  

    Shiori Novella: UCgnfPPb9JI3e9A4cXHnWbyg  
    Koseki Bijou: UC9p\\_lqQ0FEDz327Vgf5JwqA  
    Nerissa Ravencroft: UC\\_sFNM0z0MWm9A6WlKPuMMg  
    FUWAMOCO: UCt9H\\_RpQzhxzlyBxFqrdHqA  

    Elizabeth Rose Bloodflame: UCW5uhrG1eCBYditmhL0Ykjw  
    Raora Panthera: UCl69AEx4MdqMZH7Jtsm7Tig  
    Gigi Murin: UCDHABijvPBnJm7F-KlNME3w  
    Cecilia Immergreen: UCvN5h1ShZtc7nly3pezRayg  
    """, inline=False)

    await interaction.response.send_message(embed=embed)

@tasks.loop(minutes=5) # TODO: Change to 3 or 5 minutes when done testing
async def periodic_live_stream_check():
    await check_for_live_streams()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_subscriptions()
    await tree.sync() # Sync commands to the server
    periodic_live_stream_check.start()

bot.run(DISCORD_TOKEN)
