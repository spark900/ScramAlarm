#!/bin/bash
PROJECT_DIR="/home/artem/projects/ScramAlarm"
ENV_BIN="$PROJECT_DIR/.wake-env/bin"

# If adding, listing, or clearing, run the CLI utility directly
if [[ "$1" == "add" || "$1" == "list" || "$1" == "clear" ]]; then
    cd "$PROJECT_DIR"
    source "$ENV_BIN/activate"
    PYTHONPATH=. python -m alarm_tui "$@"
    deactivate
    exit 0
fi

# Ensure audio and display tokens cross the tmux boundary
export XDG_RUNTIME_DIR="/run/user/1000"
export ALSA_CARD="default"

# Force the main persistent background daemon to start with the 'run' command
if ! tmux has-session -t alarm_tui 2>/dev/null; then
    tmux new-session -d -s alarm_tui "cd $PROJECT_DIR && source $ENV_BIN/activate && export PYTHONPATH=. && python -m alarm_tui run"
fi

# Bring the interface right to your current terminal window
tmux attach-session -t alarm_tui
