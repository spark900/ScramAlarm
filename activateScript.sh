#!/bin/bash
PROJECT_DIR="/home/artem/Projects/ScramAlarm"
ENV_BIN="$PROJECT_DIR/.wak-env/bin"

# CLI utility shortcuts (add, list, clear)
if [[ "$1" == "add" || "$1" == "list" || "$1" == "clear" ]]; then
    cd "$PROJECT_DIR"
    source "$ENV_BIN/activate"
    export PYTHONPATH="$PROJECT_DIR"
    python -m alarm_tui "$@"
    deactivate
    exit 0
fi

export XDG_RUNTIME_DIR="/run/user/1000"
export ALSA_CARD="default"

# Launch the interactive app inside tmux using the proper directory nesting
if ! tmux has-session -t alarm_tui 2>/dev/null; then
    tmux new-session -d -s alarm_tui "cd $PROJECT_DIR && source $ENV_BIN/activate && export PYTHONPATH=$PROJECT_DIR && python -m alarm_tui run"
fi

tmux attach-session -t alarm_tui
