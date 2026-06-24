# RA Tracker

Desktop application to track your RetroAchievements progress. Displays all achievements earned by a user, grouped by game, with detailed statistics and game information.

## Features

- **Login with RetroAchievements** — Enter your API Key and username to fetch your achievements
- **Credential encryption** — API Key and username are encrypted with RSA-4096 and saved locally
- **Disk cache** — Achievements, badges, and game data are cached to avoid repeated API calls
- **Auto-login** — Saved credentials are loaded automatically on startup
- **Grouped by game** — Achievements are displayed in collapsible sections per game
- **Achievement details** — Click any achievement to see game cover art, statistics, publisher/developer info, and per-achievement stats
- **Hardcore mode** — Hardcore achievements are highlighted with a gold border
- **Badge preloading** — Badges are fetched in parallel for a smooth scrolling experience
- **Logout** — Removes saved credentials and clears displayed data

## Requirements

- Python 3.10+
- Windows (tested on Windows 10/11)

## Installation

1. Clone or download this repository
2. Create a virtual environment and activate it:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the application:

   ```
   python main.py
   ```

## Building a Standalone Executable

You can build a single `.exe` file with PyInstaller:

```
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=RetroAchievements.ico --add-data "ra_tracker\images;ra_tracker\images" --add-data "ra_tracker\fonts;ra_tracker\fonts" main.py
```

The executable will be created in the `dist/` folder. The `--add-data` flag bundles the images folder so the logo and icon work correctly. The `--noconsole` flag hides the terminal window.

## Usage

1. Get your API Key from [RetroAchievements](https://retroachievements.org/controlpanel.php)
2. Open RA Tracker and enter your **API Key** and **Username**
3. Click **Login** — your credentials are saved and achievements are fetched automatically
4. Browse achievements grouped by game. Click any achievement to view details.
5. Use **Clear Cache** to force a fresh fetch from the API
6. Use **Logout** to remove saved credentials and clear the display

## Project Structure

```
ra_tracker/
├── __init__.py              Package entry point
├── gui.py                   Application entry point (run())
├── main_window.py           MainWindow — main UI logic
├── api.py                   RAClient — RetroAchievements API wrapper
├── cache.py                 Disk cache for achievements, badges, game data
├── credential_manager.py    RSA-4096 credential encryption/decryption
├── fetch_worker.py          FetchWorker — background thread for API calls
├── achievement_card.py      AchievementCard — individual achievement widget
├── achievement_dialog.py    AchievementDetailDialog — detailed achievement view
├── collapsible_section.py   CollapsibleSection — expandable game group
└── images/
    ├── RetroAchievements.png    Application logo
    └── RetroAchievements.ico    Application icon
```

## Data Storage

- **Credentials**: `%USERPROFILE%\.ra_tracker\private_key.pem` + `credentials.enc`
- **Cache**: `%USERPROFILE%\.ra_tracker\cache/` — achievements JSON, badge PNGs, game data JSON

## License

MIT — free to use, modify, and distribute.
