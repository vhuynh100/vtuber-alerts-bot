# VTuber Alerts Bot

Discord bot that sends alerts to a specified Discord channel when a YouTube streamer goes live. Discord channels can subscribe to user-specified streamers and will only receive notifications for those streamers.

### Prerequisites:
Python 3.11 or 3.12

### To run the bot locally:
```
py main.py
```

### To run the bot remotely:
Start a new tmux session:
```
tmux new -s mysession
```
Activate the virtual environment:
```
source venv/bin/activate
```
Run the script:
```
python main.py
```
Detach from the session (script will still run in the background): Press `Ctrl` + `b` and then `d`
Reattach later (and check on status):
```
tmux attach -t mysession
```
From inside the session, exit the session and close running processes within it:
```
exit
```
Kill session by name:
```
tmux kill-session -t mysession
```
Kill all tmux sessions:
```
tmux kill-server
```
View all running tmux sessions:
```
tmux ls
```

## Commands:
/subscribe: Subscribe a Discord channel to alerts for a streamer. Optionally, include a role to be mentioned on alert.
```
/subscribe <streamer_channel_id> <(optional) mention>
```

/unsubscribe: Remove a YT channel from a Discord channel's notification list.
```
/unsubscribe <streamer_channel_id>
```

/alerts: List the streamers the Discord channel is subscribed to alerts for
```
/alerts
```

/quicklist: View a quick list of YT channel ids available to subscribe to.
```
/quicklist
```

Note: To get a YouTube channel ID,
1. Right click YouTube channel
2. Click "View Page Source"
3. Ctrl+F for "https://www.youtube.com/feeds/videos.xml?channel_id=" or "rssUrl"
4. The channel ID is everything after "channel_id="