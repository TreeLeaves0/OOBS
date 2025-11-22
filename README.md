this is slopcoded by ai dont look at the code too much its bad but it works

# OOBS - Foxhole Hex Player Tracker

See which Steam players are in your hex and check if they are Colonial or Warden. An open source alternative to WOBS

---

## Setup

### 1. Make sure you have Python
You need Python installed on your computer.

### 2. Download the Code
- Download the ZIP folder.
- Extract it somewhere.

### 3. Open Steam console
- Press **Windows + R**.
- Type `steam://open/console` and hit Enter
- In the Steam console, type `log_ipc 1` and hit Enter
- Steam will show where logs are saved. Example:

```

C:\Program Files (x86)\Steam\logs\ipc_SteamClient.log

````

### 4. Edit config.json
- Open `config.json`.
- Put the log path in `log_path`. You need double backslashes (`\\`) for each backslash, like:

```json
"log_path": "C:\\Program Files (x86)\\Steam\\logs\\ipc_SteamClient.log"
````

### 5. Get a Steam API key

* Go to https://steamcommunity.com/dev/apikey
* Enter any domain.
* Copy the API key Steam gives you into `config.json` under `api_key`.

### 6. Install requests

* Run `setup.bat`, or just run:

```
pip install requests
```

### 7. Run the tracker

* Open `start.bat` (or run the Python script yourself).

---

## How it works

* When you enter a hex, you’ll see all players in it.
* If a new player enters your hex, they’ll show up automatically.
* If you want to check whether a player is Warden or Colonial, press the /p button and paste it in chat. If you can private message the player, they are Colonial if you cannot, they are a Warden.
