#!/bin/bash
PROJECT_DIR="/home/artem/Projects/ScramAlarm"
ENV_BIN="$PROJECT_DIR/.wak-env/bin"

# If executing a CLI action (add, list, clear), talk to the storage from the project root
if [[ "$1" == "add" || "$1" == "list" || "$1" == "clear" ]]; then
    cd "$PROJECT_DIR"
    source "$ENV_BIN/activate"
    export PYTHONPATH="$PROJECT_DIR"
    python -m alarm_tui "$@"
    deactivate
    exit 0
fi

# Ensure audio and window display variables pass cleanly
export XDG_RUNTIME_DIR="/run/user/1000"
export ALSA_CARD="default"

# Force the core background engine to start using the project root as PYTHONPATH
if ! tmux has-session -t alarm_tui 2>/dev/null; then
    tmux new-session -d -s alarm_tui "cd $PROJECT_DIR && source $ENV_BIN/activate && export PYTHONPATH=$PROJECT_DIR && python -m alarm_tui run"
fi

# Securely attach Konsole to the active engine
tmux attach-session -t alarm_tui
