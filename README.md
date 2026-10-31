# MAA TaskBar Hero

A visual automation tool for the Steam game **TaskBarHero**. It reads the game screen with screenshots and template matching, then plays your farming route with normal mouse and keyboard input. It runs the route, opens chest drops, stashes loot, fights act bosses with your soulstones, and synthesizes items in the Cube when your inventory is full, then sorts your stash.

This is [chanonwa](https://github.com/chanonwa)'s extended version of [Marcus-Xu-04/MAA-Task-Bar-Hero](https://github.com/Marcus-Xu-04/MAA-Task-Bar-Hero), the original project by Marcus-Xu-04. It is maintained separately: changes here are not sent to the original, and updates from it are not pulled in.

## What's new

Each release lists what it adds. See **[Releases](https://github.com/chanonwa/MAA-Task-Bar-Hero/releases)**; the latest is [1.5.2](https://github.com/chanonwa/MAA-Task-Bar-Hero/releases/tag/v1.5.2).

## Download and run

**Windows app:** download the zip from the latest release, extract all of it, and run `MAA Task Bar Hero.exe` inside the extracted folder.

**From source:**

1. Install Python 3, then run `py -3 -m pip install -r requirements.txt`.
2. Start the GUI with `Start MAA Task Bar Hero.bat`.
3. To build the Windows app yourself, run `Build Windows App.bat`.

In the GUI, add stages to the farming cycle, tick the options you want, and press **Save and Start**.

## Farming cycle

With one stage, the bot stays on it. With several, it moves on after each blue chest, or after 2 clears without one, and starts the list again when it reaches the end.

Chests come at about the same rate wherever you farm, roughly one blue every 5 minutes and one common every 3, so a longer list doesn't add many. Over an hour of testing, moving through Torment 3-1 and low Normal stages gave about 12 blue chests an hour, about 5 of them from Torment 3-1. Staying on Torment 3-1 gives about 10 an hour, all at its top chest level. A longer list trades top-level chests for lower ones.

## Plaguelands

Tick *Plaguelands when Contamination is over half*. Every 10 minutes the bot reads Contamination on the PORTAL's Plaguelands tab. When it's over half, the bot enters at the hardest difficulty that has the tab and the highest Plague Intensity you've unlocked. Inside, it opens chests and stashes loot, and it saves boss runs for later. When the game sends you out at 0 Contamination, it goes back to the first stage of your farming cycle.

If 15 minutes pass without a clear, it leaves and doesn't enter again until you restart the bot.

## Before you start

* Set the game language to **English** and the game zoom to **1x / 100%**.
* Keep the STASH, HERO, and PORTAL windows open, with the HERO panel on its **Inventory** tab. If you hide the panels with the button on the battle bar, or close STASH or PORTAL, the bot opens them again.
* The bot uses your real mouse, so don't use the mouse while it runs. Press **Ctrl + Shift + F12** to stop it.

## Troubleshooting

**The app can't find the game window.** Make sure TaskBarHero is running and not minimized.

**"MAA Task Bar Hero is already open."** Only one copy can run at a time, so two copies can't fight over the game. Use the window that's already open; the message brings it to the front.

**The bot doesn't click the game.** Make sure the game window isn't minimized or covered. The game only takes clicks from the real mouse, so the bot can't run in the background.

**The bot can't find a stage.** Check the zoom is 1x and the PORTAL window is open. A stage marked `[Unavailable]` is missing its template in `templates/levels/`.

**Cube synthesis doesn't run.** It runs only when the backpack's 21 visible slots are still full after stashing and *Cube synthesis when the inventory is full* is ticked. After a run that combined nothing, it waits 10 minutes before trying again. It combines Lv.80~90 gear and materials only, so gear from low stages stays in your stash until you clear it. Items at or above the *Synthesize up to* grade are locked first and never combined, and neither are soulstones. To protect any other item, lock it yourself with ALT + left click; the bot keeps those locks.

**The stash order changed after a synthesis.** That's the bot sorting it: it takes everything into the backpack, sorts it, and stashes it back from tab 1, so the best grades end up first.

**A stage restarted.** The bot never presses the stage you're already on, because that restarts its progress. If you see a restart, use **Export Debug ZIP** and report it.

**Adding templates.** A stage needs `templates/levels/level_<act>_<stage>.png`. A difficulty needs `templates/difficulty/anchor_difficulty_<name>.png`. Soulstones of all four difficulties are recognized by their icon (`soulstone_icon_templates`) and tooltip title (`soulstone_title_templates`) in `config.json`. The bot finds them in the stash and the backpack.

**Reporting a problem.** Use **Export Debug ZIP** in the GUI and include the zip. It holds the logs and screenshots that show what the bot saw.

## Disclaimer

The bot doesn't read game memory, modify game files, inject code, or intercept network traffic. It only looks at the screen and sends normal input. It's shared for learning and automation research; use it at your own risk. Game updates or different display setups can break it.

## Credits

Original concept and direction by **Marcus-Xu-04**. Improvements by **Chanon Wa**.
