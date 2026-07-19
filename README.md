# alarm-tui

A minimal, self-contained terminal alarm clock built for Arch Linux. No
background GUI process, no external sound files that can go missing, no
mystery daemons — just a fast TUI (built with [Textual](https://textual.textualize.io/))
that fits naturally into a `tmux`-centric or dropdown-terminal workflow.

## Why CLI/TUI instead of a GUI

Arch users overwhelmingly favor minimal resource footprints, terminal-native
workflows, and predictable, inspectable software. A TUI built on Textual
gives you the visual clarity of a GUI — panels, a live table, color, focus
handling — while remaining a single lightweight process you can dock into
a `tmux` pane, a scratchpad terminal (`kitty --class scratchpad`, `st`,
`alacritty`, etc.), or an SSH session, with zero display-server dependency.

## Features

- **Flexible time input** — `+30m`, `+1h30m`, `07:30`, or an absolute
  `2026-07-20 07:30`.
- **Embedded audio, no external files** — the alarm tone is *synthesized*
  in-memory at import time (see `alarm_tui/audio.py`) rather than read from
  a `.wav` on disk. This gets you the same guarantee as a Base64-embedded
  audio blob — the sound can never go missing or reference a broken path —
  without a wall of opaque text sitting in the source. Swap in your own
  PCM/Base64 decoding there if you'd rather ship a recorded sound.
- **The Wake-Up Locksmith** — dismissing a ringing alarm requires typing a
  freshly generated, cryptographically random 20+ character alphanumeric
  code exactly. `Ctrl+C`, `Ctrl+Z`, and `Ctrl+\` are intercepted and
  disabled for the duration of the ring (`alarm_tui/security.py`).
- **Snooze penalty** — every snooze adds 5 characters to the *next*
  dismissal code, so repeated snoozing gets progressively harder to escape.
- **Fail-safe visual flash** — the ringing screen cycles through
  high-contrast foreground/background color pairs every 400ms, so you'll
  notice the alarm even with system audio muted.
- **systemd `--user` integration** — survives terminal closures by running
  inside a detached `tmux` session managed by a systemd unit (see below).

## Project structure

```
alarm-tui/
├── PKGBUILD
├── README.md
├── pyproject.toml
├── requirements.txt
├── systemd/
│   └── alarm-tui.service
└── alarm_tui/
    ├── __init__.py
    ├── __main__.py
    ├── app.py          # Textual TUI: MainScreen + RingingScreen
    ├── audio.py         # in-memory tone synthesis + looped playback
    ├── cli.py            # argparse entry point (run / add / list / clear)
    ├── security.py       # dismissal-code generation + Ctrl+C shielding
    ├── storage.py         # JSON-backed alarm persistence
    └── timeparse.py        # +30m / 07:30 / absolute timestamp parsing
```

## Installation

### Option A — PKGBUILD (recommended on Arch)

```bash
git clone https://github.com/yourname/alarm-tui.git
cd alarm-tui
makepkg -si
```

`python-textual` and `python-simpleaudio` are not in the official
repositories — they're on the AUR. If you're using an AUR helper instead of
building this PKGBUILD directly, install those two first:

```bash
yay -S python-textual python-simpleaudio
```

`python-rich`, `alsa-lib`, and `tmux` are in the official `[extra]`
repository and will be pulled in normally by `pacman`.

### Option B — pip (any Linux, including non-Arch)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m alarm_tui
```

`simpleaudio` compiles a small C extension against ALSA, so make sure
`alsa-lib` (runtime) and its headers are present when installing via pip:

```bash
sudo pacman -S alsa-lib alsa-utils
```

## Usage

```bash
alarm-tui                     # launch the interactive TUI
alarm-tui add +30m "Coffee"   # add an alarm without opening the TUI
alarm-tui list                # list all stored alarms
alarm-tui clear               # remove finished alarms
alarm-tui clear --all         # remove every alarm
```

Inside the TUI:

| Key | Action                    |
|-----|---------------------------|
| `a` | Focus the add-alarm form  |
| `d` | Delete the selected alarm |
| `q` | Quit                      |

When an alarm fires, the screen locks into ringing mode. Type the exact
code shown on screen and press Enter to dismiss it, or hit **Snooze** to
push it back 5 minutes (at the cost of a longer code next time).

## Running as a systemd `--user` service

Because a TUI needs a real terminal to draw into, the shipped unit starts
alarm-tui inside a detached `tmux` session rather than as a bare background
process. This is exactly the workflow the app is designed for: dock a
terminal into it whenever you want to check on or manage your alarms.

```bash
systemctl --user enable --now alarm-tui.service
loginctl enable-linger "$USER"   # optional: keep it running after logout
```

Then, whenever you want to interact with it:

```bash
tmux attach -t alarm-tui
```

Detach again with the usual `Ctrl+b d` — alarm-tui keeps running, and any
alarm you've scheduled will still fire (with full audio + flash + locksmith
dismissal) the next time you attach, or immediately if you're already
attached when it triggers.

## Data storage

Alarms persist as JSON at `$XDG_DATA_HOME/alarm-tui/alarms.json` (falling
back to `~/.local/share/alarm-tui/alarms.json`). There is no other state.

## License

MIT
