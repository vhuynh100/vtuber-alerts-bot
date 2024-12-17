# VTuber Alerts Bot

Discord bot that sends alerts to a specified channel when a streamer goes live.

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