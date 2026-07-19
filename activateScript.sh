#!/bin/bash
PROJECT_DIR="/home/artem/Projects/ScramAlarm"
ENV_BIN="$PROJECT_DIR/.wak-env/bin"

# If executing a management subcommand, talk directly to the shared JSON storage
if [[ "$1" == "add" || "$1" == "list" || "$1" == "clear" ]]; then
    cd "$PROJECT_DIR"
    source "$ENV_BIN/activate"
    PYTHONPATH=. python -m alarm_tui "$@"
    deactivate
    exit 0
fi

# Pass standard audio/display access tokens to the environment inside tmux
export XDG_RUNTIME_DIR="/run/user/1000"
export ALSA_CARD="default"

# Ensure the core application instance is safely isolated inside a persistent background session
if ! tmux has-session -t alarm_tui 2>/dev/null; then
    tmux new-session -d -s alarm_tui "cd $PROJECT_DIR && source $ENV_BIN/activate && export PYTHONPATH=. && python -m alarm_tui run"
fi

# Attach the current terminal interface directly to the engine
tmux attach-session -t alarm_tui
