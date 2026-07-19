#!/bin/bash
PROJECT_DIR="/home/artem/projects/ScramAlarm"
ENV_BIN="$PROJECT_DIR/.wake-env/bin"

# If the user is adding, listing, or clearing alarms, handle it directly via the CLI
if [[ "$1" == "add" || "$1" == "list" || "$1" == "clear" ]]; then
    cd "$PROJECT_DIR"
    source "$ENV_BIN/activate"
    PYTHONPATH=. python -m alarm_tui "$@"
    deactivate
    exit 0
fi

# Otherwise, the user wants to view the application interface.
# We force it to run inside tmux so it never dies if a window is closed.
if ! tmux has-session -t alarm-tui 2>/dev/null; then
    tmux new-session -d -s alarm-tui "cd $PROJECT_DIR && source $ENV_BIN/activate && PYTHONPATH=. python -m alarm_tui"
fi

# Attach to the running session
tmux attach-t alarm-tui
