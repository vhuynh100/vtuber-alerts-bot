# VTuber Alerts Bot

Discord bot that sends alerts to a specified Discord channel when a YouTube streamer goes live. Discord channels can subscribe to user-specified streamers and will only receive notifications for those streamers.

### Prerequisites:
Python 3.11 or 3.12

## Commands:
/subscribe: Subscribe a Discord channel to alerts for a streamer. Optionally, include a role to be mentioned on alert. Command must be called in the target Discord channel.
```
/subscribe <streamer_channel_id> <(optional) mention>
```

/unsubscribe: Remove a YT channel from a Discord channel's notification list. Command must be called in the target Discord channel.
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

/setuproles: Initiate the setup for adding reaction roles so a user can add or remove reactions to a target message to self-assign roles. Command must be called in the same channel as the target message.
```
/setuproles <message_id>
```

Note: To get a YouTube channel ID,
1. Right click YouTube channel
2. Click "View Page Source"
3. Ctrl+F for "https://www.youtube.com/feeds/videos.xml?channel_id=" or "rssUrl"
4. The channel ID is everything after "channel_id="