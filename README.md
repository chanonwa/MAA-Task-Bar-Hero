# MAA TaskBar Hero

A visual automation tool for the Steam game **TaskBarHero**. It reads the game screen with screenshots and template matching, then plays your farming route with normal mouse and keyboard input. It runs the route, opens chest drops, stashes loot, and fights act bosses with your soulstones.

This is [chanonwa](https://github.com/chanonwa)'s extended version of [Marcus-Xu-04/MAA-Task-Bar-Hero](https://github.com/Marcus-Xu-04/MAA-Task-Bar-Hero), the original project by Marcus-Xu-04. It is maintained separately: changes here are not sent to the original, and updates from it are not pulled in.

## What's new

Each release lists what it adds. See **[Releases](https://github.com/chanonwa/MAA-Task-Bar-Hero/releases)**; the latest is [1.4](https://github.com/chanonwa/MAA-Task-Bar-Hero/releases/tag/v1.4).

## Download and run

**Windows app:** download the zip from the latest release, extract all of it, and run `MAA Task Bar Hero.exe` inside the extracted folder.

**From source:**

1. Install Python 3, then run `py -3 -m pip install -r requirements.txt`.
2. Start the GUI with `Start MAA Task Bar Hero.bat`.
3. To build the Windows app yourself, run `Build Windows App.bat`.

In the GUI, add stages to the farming cycle, tick the options you want, and press **Save and Start**.

## Before you start

* Set the game language to **English** and the game zoom to **1x / 100%**.
* Keep the STASH, HERO, and PORTAL windows open.
* The bot uses your real mouse, so don't use the mouse while it runs. Press **Ctrl + Shift + F12** to stop it.

## Troubleshooting

**The app can't find the game window.** Make sure TaskBarHero is running and not minimized.

**"MAA Task Bar Hero is already open."** Only one copy can run at a time, so two copies can't fight over the game. Use the window that's already open; the message brings it to the front.

**The bot doesn't click the game.** Turn off *Background input mode*. Foreground mouse mode is more reliable.

**The bot can't find a stage.** Check the zoom is 1x and the PORTAL window is open. A stage marked `[Unavailable]` is missing its template in `templates/levels/`.

**Adding templates.** A stage needs `templates/levels/level_<act>_<stage>.png`. A difficulty needs `templates/difficulty/anchor_difficulty_<name>.png`. A soulstone difficulty needs its icon in `soulstone_icon_templates` and its tooltip title in `soulstone_title_templates` (`config.json`).

**Reporting a problem.** Use **Export Debug ZIP** in the GUI and include the zip. It holds the logs and screenshots that show what the bot saw.

## Disclaimer

The bot doesn't read game memory, modify game files, inject code, or intercept network traffic. It only looks at the screen and sends normal input. It's shared for learning and automation research; use it at your own risk. Game updates or different display setups can break it.

## Credits

Original concept and direction by **Marcus-Xu-04**. Improvements by **Chanon Wa**.
