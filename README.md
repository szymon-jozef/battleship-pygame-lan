![Tests Status](https://github.com/szymon-jozef/battleship-pygame-lan/actions/workflows/python-tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

# LAN game of battleships made with pygame
Classic game of battleships made with python.

Most of the code is well documented with docstrings.

## Screenshots
![Main menu](.github/screenshots/menu.png)
![Settings](.github/screenshots/settings.png)
![Empty board](.github/screenshots/empty_board.png)
![Game](.github/screenshots/game.png)

# Important!
Players __need to__ have different names! Otherwise server won't allow them to play.

# How to play?
1. Go into settings and set your name.
2. One player needs to host the game. All he needs to do is click `Play` and `Host Game`.
3. The other player has to click `Play` and `Join Game`. He needs to type in the IP address that the first player has on his screen.
4. If you want to play it over internet you need to [forward port 6769 on your router](https://en.wikipedia.org/wiki/Port_forwarding).
5. Enjoy!


# Installation instructions
## Source
1. Clone, download or get this repo any way possible
2. Make sure you have [uv](https://docs.astral.sh/uv/#installation) installed.
3. `uv sync`
4. `uv run battleship-pygame-lan`

## Alternative installation
**Not supported, but should work**
Use [pipx](https://pipx.pypa.io/stable/) to install:
```bash
pipx install git+https://github.com/szymon-jozef/battleship-pygame-lan
```
Type in `battleship-pygame-lan` to start.

## Nixos
- Add this repo to your inputs in `flake.nix`:
```nix
inputs = {
    battleship.url = "github:szymon-jozef/battleship-pygame-lan";
}
```
- Add packages and enable it. 
Enabling it exposes port 6769 and adds a .desktop entry.
```nix
imports = [
    inputs.battleship.nixosModules.default
];

programs.battleship-pygame-lan.enable = true;
```

## Windows
Download and run `Battleships-LAN-Windows.exe` from the release tab

## Linux binary
Download `Battleships-LAN-Linux` from the release tab, make it executable and run it. 

## MacOS
Download macos binary from release tab.

# Tech stack
This project utilises technologies like:
- [python](https://www.python.org/) – language, with multiple modules like: logging, socket, threading, json and configparser, importlib, argparse
- [pygame-ce](https://github.com/pygame-community/pygame-ce) – GUI
- [uv](https://docs.astral.sh/uv/) – package management
- [nix](https://nixos.org/) – distribution and devshell
- [mypy](https://mypy-lang.org/) – type checking
- [ruff](https://docs.astral.sh/ruff/) – style checks
- [github actions](https://github.com/features/actions) – unit and CI tests
- [git](https://git-scm.com/) – version control
- [pytest](https://docs.pytest.org/en/stable/) – unit tests
- [appdirs](https://pypi.org/project/appdirs/) – finding user configuration paths
- [pyinstaller](https://pyinstaller.org/en/stable/) – generating .exe file


# Project structure
This project is split into multiple modules:

## Network
All the logic behind networking. It has classes like: `NetworkServer` and `NetworkClient`.
It exposes a TCP socket at port `6769` and connects with it. It sends custom payload using functions in `payloads.py`.
All the information is sent in JSON format.

## Logic
Logic layer of the project. It handles player boards. It has custom Enums like `ShipType`, `FieldState`, `ShotResult`.
It also uses custom exceptions.

## GUI
GUI logic behind everything that is shown. It uses pygame to display everything.

## Game Manager
High abstraction class that bundles logic and networking together. It also has gui_events_queue that hints GUI at actions it should take.

## IO
Saves config to the disk.

# Milestones:
- [x] Game logic
- [x] GUI with pygame
- [x] Network connection
- [X] Distribution 

# Authors:
|Name|Responsible for|
|---|---|
|[Szymon P](https://github.com/szymon-jozef)| Game logic, networking, IO, distribution|
|[Jakub K](https://github.com/Real-Morbius)| GUI|
