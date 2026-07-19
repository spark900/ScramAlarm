"""alarm-tui: the interactive Textual application."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Set

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from . import storage
from .audio import AlarmPlayer
from .security import InterruptShield, code_length_after_snoozes, generate_dismissal_code
from .timeparse import TimeParseError, parse_alarm_time

# Alternating (foreground, background) pairs for the fail-safe visual flash.
# High-contrast and deliberately jarring so the alarm is noticeable even
# with system audio muted.
FLASH_PALETTES = [
    ("white", "red"),
    ("black", "yellow"),
    ("white", "magenta"),
    ("black", "cyan"),
]

SNOOZE_MINUTES = 5


class RingingScreen(Screen):
    """Full-screen alarm prompt. The only way out is the correct code."""

    # Deliberately no key bindings here: nothing on this screen should be
    # able to pop it except a correct code submission.
    BINDINGS = []

    def __init__(self, alarm: storage.Alarm) -> None:
        super().__init__()
        self.alarm = alarm
        self.snooze_count = alarm.snooze_count
        self.code = generate_dismissal_code(code_length_after_snoozes(self.snooze_count))
        self.player = AlarmPlayer()
        self._flash_index = 0
        self._flash_timer: Optional[Timer] = None
        self._shield = InterruptShield()

    def compose(self) -> ComposeResult:
        with Vertical(id="ringing-root"):
            yield Static("ALARM", id="ringing-title")
            yield Label(f"[b]{self.alarm.label}[/b]", id="ringing-label")
            yield Label("Type the code below exactly to dismiss:", id="ringing-instructions")
            yield Static(self.code, id="ringing-code")
            yield Input(placeholder="Type the code here...", id="ringing-input")
            with Horizontal(id="ringing-buttons"):
                yield Button(
                    f"Snooze {SNOOZE_MINUTES} min  (next code will be +5 chars longer)",
                    id="snooze-btn",
                    variant="warning",
                )
            yield Label("", id="ringing-feedback")
            if not self.player.audio_available:
                yield Label(
                    "[dim]Audio backend unavailable -- relying on the visual flash only.[/dim]",
                    id="ringing-audio-warning",
                )

    def on_mount(self) -> None:
        self._shield.__enter__()
        self.player.start()
        self._flash_timer = self.set_interval(0.4, self._flash_step)
        self.query_one("#ringing-input", Input).focus()

    def on_unmount(self) -> None:
        self._shield.__exit__()
        self.player.stop()
        if self._flash_timer is not None:
            self._flash_timer.stop()

    def _flash_step(self) -> None:
        fg, bg = FLASH_PALETTES[self._flash_index % len(FLASH_PALETTES)]
        self._flash_index += 1
        root = self.query_one("#ringing-root")
        root.styles.background = bg
        root.styles.color = fg

    @on(Input.Submitted, "#ringing-input")
    def _check_code(self, event: Input.Submitted) -> None:
        attempt = event.value
        feedback = self.query_one("#ringing-feedback", Label)
        if attempt == self.code:
            self.player.stop()
            app: AlarmTUIApp = self.app  # type: ignore[assignment]
            app.pop_screen()
            app.mark_alarm_dismissed(self.alarm)
        else:
            feedback.update("[red]Incorrect. Keep trying.[/red]")
            self.query_one("#ringing-input", Input).value = ""

    @on(Button.Pressed, "#snooze-btn")
    def _snooze(self) -> None:
        self.player.stop()
        app: AlarmTUIApp = self.app  # type: ignore[assignment]
        app.pop_screen()
        app.snooze_alarm(self.alarm)

    def key_ctrl_c(self) -> None:
        # Belt-and-braces: even if the OS-level signal shield were somehow
        # bypassed, Textual's own key event for Ctrl+C is swallowed here.
        pass


class MainScreen(Screen):
    BINDINGS = [
        ("a", "add_alarm", "Add alarm"),
        ("d", "delete_alarm", "Delete selected"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield DataTable(id="alarm-table")
            with Horizontal(id="add-row"):
                yield Input(placeholder="+30m, 07:30, or 2026-07-20 07:30", id="time-input")
                yield Input(placeholder="Label (optional)", id="label-input")
                yield Button("Add Alarm", id="add-btn", variant="success")
            yield Label("", id="status-label")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#alarm-table", DataTable)
        table.add_columns("Label", "Triggers At", "Status")
        table.cursor_type = "row"
        self.refresh_table()
        app: AlarmTUIApp = self.app  # type: ignore[assignment]
        self.set_interval(1.0, app.check_alarms)

    def refresh_table(self) -> None:
        table = self.query_one("#alarm-table", DataTable)
        table.clear()
        app: AlarmTUIApp = self.app  # type: ignore[assignment]
        for alarm in sorted(app.alarms, key=lambda a: a.trigger_at):
            status = "active" if alarm.active else "done"
            table.add_row(
                alarm.label,
                alarm.trigger_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                status,
                key=alarm.id,
            )

    @on(Button.Pressed, "#add-btn")
    def _add_from_button(self) -> None:
        self.action_add_alarm()

    def action_add_alarm(self) -> None:
        time_input = self.query_one("#time-input", Input)
        label_input = self.query_one("#label-input", Input)
        status = self.query_one("#status-label", Label)
        app: AlarmTUIApp = self.app  # type: ignore[assignment]
        try:
            when = parse_alarm_time(time_input.value)
        except TimeParseError as exc:
            status.update(f"[red]{exc}[/red]")
            return
        alarm = storage.new_alarm(label_input.value, when)
        app.alarms.append(alarm)
        storage.save_alarms(app.alarms)
        time_input.value = ""
        label_input.value = ""
        status.update(f"[green]Added '{alarm.label}' for {when.strftime('%Y-%m-%d %H:%M:%S')}[/green]")
        self.refresh_table()

    def action_delete_alarm(self) -> None:
        table = self.query_one("#alarm-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return
        app: AlarmTUIApp = self.app  # type: ignore[assignment]
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except Exception:
            return
        alarm_id = row_key.value
        app.alarms = [a for a in app.alarms if a.id != alarm_id]
        storage.save_alarms(app.alarms)
        self.refresh_table()

    def action_quit(self) -> None:
        self.app.exit()


class AlarmTUIApp(App):
    CSS = """
    #ringing-root {
        align: center middle;
        height: 100%;
        width: 100%;
    }
    #ringing-title {
        text-style: bold;
        content-align: center middle;
        width: 100%;
        margin-bottom: 1;
        text-align: center;
    }
    #ringing-label, #ringing-instructions {
        content-align: center middle;
        width: 100%;
        text-align: center;
    }
    #ringing-code {
        text-style: bold;
        border: heavy white;
        padding: 1 2;
        margin: 1 0;
        content-align: center middle;
        width: auto;
    }
    #ringing-input {
        width: 60%;
    }
    #ringing-feedback {
        width: 100%;
        text-align: center;
    }
    #add-row {
        height: 3;
    }
    #time-input {
        width: 40%;
    }
    #label-input {
        width: 40%;
    }
    """

    TITLE = "alarm-tui"

    def __init__(self) -> None:
        super().__init__()
        self.alarms: List[storage.Alarm] = storage.load_alarms()
        self._ringing_ids: Set[str] = set()

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def check_alarms(self) -> None:
        now = datetime.now()
        for alarm in self.alarms:
            if not alarm.active or alarm.id in self._ringing_ids:
                continue
            if alarm.trigger_datetime <= now:
                self._ringing_ids.add(alarm.id)
                self.push_screen(RingingScreen(alarm))

    def mark_alarm_dismissed(self, alarm: storage.Alarm) -> None:
        alarm.active = False
        self._ringing_ids.discard(alarm.id)
        storage.save_alarms(self.alarms)
        if isinstance(self.screen, MainScreen):
            self.screen.refresh_table()
        self.bell()

    def snooze_alarm(self, alarm: storage.Alarm) -> None:
        alarm.snooze_count += 1
        alarm.trigger_at = (datetime.now() + timedelta(minutes=SNOOZE_MINUTES)).isoformat()
        self._ringing_ids.discard(alarm.id)
        storage.save_alarms(self.alarms)
        if isinstance(self.screen, MainScreen):
            self.screen.refresh_table()


def run() -> None:
    AlarmTUIApp().run()
