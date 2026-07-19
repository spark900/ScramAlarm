#!/bin/bash
# Activate your custom environment
source ~/ScramAlarm/.wake-env/bin/activate

# Run the app, passing any arguments along (like 'add +30m')
python -m alarm_tui "$@"

# Deactivate the environment cleanly when done
deactivate