#!/bin/bash
PROJECT_DIR="/home/artem/Projects/ScramAlarm"
# Point PYTHONPATH to the parent of the actual inner package
MODULE_DIR="$PROJECT_DIR/alarm_tui"
ENV_BIN="$PROJECT_DIR/.wak-env/bin"

# CLI utility shortcuts (add, list, clear)
if [[ "$1" == "add" || "$1" == "list" || "$1" == "clear" ]]; then
    cd "$PROJECT_DIR"
    source "$ENV_BIN/activate"
    export PYTHONPATH="$MODULE_DIR"
    python -m alarm_tui "$@"
    deactivate
    exit 0
fi

export XDG_RUNTIME_DIR="/run/user/1000"
export ALSA_CARD="default"

# We use "alarm-tui" (hyphen) to match the systemd service configurations exactly
if ! tmux has-session -t alarm-tui 2>/dev/null; then
    tmux new-session -d -s alarm-tui "cd $PROJECT_DIR && source $ENV_BIN/activate && export PYTHONPATH=$MODULE_DIR && python -m alarm_tui run"
fi

tmux attach-session -t alarm-tui
