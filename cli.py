"""Command-line entry point for alarm-tui."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from . import storage
from .timeparse import TimeParseError, parse_alarm_time


def _cmd_run(_args: argparse.Namespace) -> int:
    from .app import AlarmTUIApp  # deferred: keeps `alarm-tui list` fast & Textual-free

    AlarmTUIApp().run()
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    try:
        when = parse_alarm_time(args.time)
    except TimeParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    alarms = storage.load_alarms()
    alarm = storage.new_alarm(args.label or "Alarm", when)
    alarms.append(alarm)
    storage.save_alarms(alarms)
    print(f"Added alarm '{alarm.label}' for {when.strftime('%Y-%m-%d %H:%M:%S')} (id {alarm.id})")
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    alarms = storage.load_alarms()
    if not alarms:
        print("No alarms scheduled.")
        return 0
    now = datetime.now()
    for alarm in sorted(alarms, key=lambda a: a.trigger_at):
        status = "active" if alarm.active else "done"
        marker = "!" if alarm.active and alarm.trigger_datetime <= now else " "
        print(f"[{marker}] {alarm.id}  {alarm.trigger_at}  {status:8s}  {alarm.label}")
    return 0


def _cmd_clear(args: argparse.Namespace) -> int:
    alarms = storage.load_alarms()
    if args.all:
        storage.save_alarms([])
        print("Cleared all alarms.")
        return 0
    remaining = [a for a in alarms if a.active]
    storage.save_alarms(remaining)
    print(f"Removed {len(alarms) - len(remaining)} finished alarm(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alarm-tui", description="A minimal terminal alarm clock for Arch Linux."
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Launch the interactive TUI (default).")
    run_parser.set_defaults(func=_cmd_run)

    add_parser = subparsers.add_parser("add", help="Add an alarm without opening the TUI.")
    add_parser.add_argument("time", help="+30m, 07:30, or 2026-07-20 07:30")
    add_parser.add_argument("label", nargs="?", default="", help="Optional label")
    add_parser.set_defaults(func=_cmd_add)

    list_parser = subparsers.add_parser("list", help="List all stored alarms.")
    list_parser.set_defaults(func=_cmd_list)

    clear_parser = subparsers.add_parser("clear", help="Remove finished alarms.")
    clear_parser.add_argument("--all", action="store_true", help="Remove every alarm, including active ones.")
    clear_parser.set_defaults(func=_cmd_clear)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        return _cmd_run(args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
