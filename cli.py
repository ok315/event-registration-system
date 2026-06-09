"""
cli.py — Interactive terminal menu using the Rich library.

WHAT IS Rich?
  Rich is a Python library for beautiful terminal output.
  It gives you colored text, tables, panels, progress bars, and more.
  pip install rich

HOW TO RUN:
    python cli.py
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.text import Text
from rich import box
from datetime import date
import service

console = Console()


# ── Styling helpers ────────────────────────────────────────────────────────

def success(msg: str):
    console.print(f"\n  ✅ [bold green]{msg}[/bold green]")

def error(msg: str):
    console.print(f"\n  ❌ [bold red]{msg}[/bold red]")

def info(msg: str):
    console.print(f"\n  ℹ️  [bold cyan]{msg}[/bold cyan]")

def divider():
    console.print()


# ═══════════════════════════════════════════════════════════════════════════
# SCREENS
# ═══════════════════════════════════════════════════════════════════════════

def screen_create_event():
    """Walk the user through creating a new event."""
    console.print(Panel("[bold]Create New Event[/bold]", style="blue"))

    name = Prompt.ask("  Event name")
    seats_str = Prompt.ask("  Total seats")
    event_date = Prompt.ask("  Event date (YYYY-MM-DD)")

    result = service.create_event(name, seats_str, event_date)

    if result["success"]:
        evt = result["event"]
        success(f"Event created! ID: [yellow]{evt['id']}[/yellow]")
        console.print(f"     Name  : {evt['name']}")
        console.print(f"     Seats : {evt['total_seats']}")
        console.print(f"     Date  : {evt['date']}")
    else:
        error(result["error"])


def screen_list_events():
    """Display all events in a rich table."""
    console.print(Panel("[bold]All Events[/bold]", style="blue"))

    upcoming_filter = Confirm.ask("  Show upcoming events only?", default=False)
    result = service.list_events(sort_by_date=True, upcoming_only=upcoming_filter)

    events = result["events"]
    if not events:
        info("No events found.")
        return

    table = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=True)
    table.add_column("ID",         style="yellow",     no_wrap=True)
    table.add_column("Name",       style="white",      min_width=20)
    table.add_column("Date",       style="magenta")
    table.add_column("Seats",      justify="center")
    table.add_column("Available",  justify="center")
    table.add_column("Status",     justify="center")

    today = date.today().isoformat()

    for evt in events:
        avail = evt["available_seats"]
        total = evt["total_seats"]

        # Color code availability
        if avail == 0:
            avail_display = "[bold red]FULL[/bold red]"
            status        = "[red]Full[/red]"
        elif avail <= total * 0.2:          # Less than 20% seats left
            avail_display = f"[yellow]{avail}[/yellow]"
            status        = "[yellow]Almost Full[/yellow]"
        else:
            avail_display = f"[green]{avail}[/green]"
            status        = "[green]Open[/green]"

        # Dim past events
        name_display = evt["name"] if evt["date"] >= today else f"[dim]{evt['name']}[/dim]"

        table.add_row(
            evt["id"],
            name_display,
            evt["date"],
            str(total),
            avail_display,
            status,
        )

    divider()
    console.print(table)
    info(f"Showing {result['count']} event(s).")


def screen_register_user():
    """Register a user for an event."""
    console.print(Panel("[bold]Register for Event[/bold]", style="blue"))

    # Show events first so user can pick
    events_result = service.list_events(sort_by_date=True, upcoming_only=True)
    if not events_result["events"]:
        info("No upcoming events to register for.")
        return

    # Quick list of upcoming events
    console.print("\n  Upcoming events:")
    for evt in events_result["events"]:
        avail = evt["available_seats"]
        status = "[red]FULL[/red]" if avail == 0 else f"[green]{avail} seats[/green]"
        console.print(f"    [yellow]{evt['id']}[/yellow]  {evt['name']}  ({evt['date']})  {status}")

    divider()
    event_id  = Prompt.ask("  Event ID")
    user_name = Prompt.ask("  Your name")

    result = service.register_user(user_name, event_id)

    if result["success"]:
        reg = result["registration"]
        success(f"Registered! Registration ID: [yellow]{reg['id']}[/yellow]")
        console.print(f"     User      : {reg['user_name']}")
        console.print(f"     Registered: {reg['registered_at']}")
    else:
        error(result["error"])


def screen_cancel_registration():
    """Cancel a registration."""
    console.print(Panel("[bold]Cancel Registration[/bold]", style="blue"))

    event_id = Prompt.ask("  Event ID (to see registrations)")
    regs_result = service.list_registrations(event_id)

    if not regs_result["success"]:
        error(regs_result["error"])
        return

    regs = regs_result["registrations"]
    if not regs:
        info("No active registrations for this event.")
        return

    # Show registrations
    table = Table(box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Registration ID", style="yellow")
    table.add_column("User",           style="white")
    table.add_column("Registered At",  style="dim")

    for reg in regs:
        table.add_row(reg["id"], reg["user_name"], reg["registered_at"])

    divider()
    console.print(table)

    reg_id = Prompt.ask("  Registration ID to cancel")
    confirm = Confirm.ask(f"  Are you sure you want to cancel registration [yellow]{reg_id}[/yellow]?")

    if not confirm:
        info("Cancellation aborted.")
        return

    result = service.cancel_registration(reg_id)
    if result["success"]:
        success(result["message"])
    else:
        error(result["error"])


def screen_view_registrations():
    """View all registrations for an event."""
    console.print(Panel("[bold]View Registrations[/bold]", style="blue"))
    event_id = Prompt.ask("  Event ID")

    event_result = service.get_event(event_id)
    if not event_result["success"]:
        error(event_result["error"])
        return

    regs_result = service.list_registrations(event_id)
    if not regs_result["success"]:
        error(regs_result["error"])
        return

    evt  = event_result["event"]
    regs = regs_result["registrations"]

    console.print(f"\n  Event : [bold]{evt['name']}[/bold]")
    console.print(f"  Date  : {evt['date']}")
    console.print(f"  Seats : {evt['available_seats']} available / {evt['total_seats']} total")

    if not regs:
        info("No registrations yet.")
        return

    table = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=True)
    table.add_column("#",              style="dim",    width=4)
    table.add_column("Registration ID", style="yellow", no_wrap=True)
    table.add_column("User",            style="white")
    table.add_column("Registered At",   style="dim")

    for i, reg in enumerate(regs, 1):
        table.add_row(str(i), reg["id"], reg["user_name"], reg["registered_at"])

    divider()
    console.print(table)
    info(f"{regs_result['count']} active registration(s).")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════

MENU_OPTIONS = {
    "1": ("Create Event",               screen_create_event),
    "2": ("View All Events",            screen_list_events),
    "3": ("Register for Event",         screen_register_user),
    "4": ("View Event Registrations",   screen_view_registrations),
    "5": ("Cancel Registration",        screen_cancel_registration),
    "6": ("Exit",                       None),
}


def main():
    while True:
        console.clear()
        console.print(Panel(
            Text("🎫  Event Registration System", justify="center", style="bold white"),
            style="bold blue",
            padding=(1, 4),
        ))

        for key, (label, _) in MENU_OPTIONS.items():
            icon = "🚪" if key == "6" else "  "
            console.print(f"    [bold cyan]{key}[/bold cyan]  {icon} {label}")

        divider()
        choice = Prompt.ask("  Choose an option", choices=list(MENU_OPTIONS.keys()))

        if choice == "6":
            console.print("\n  Goodbye! 👋\n")
            break

        _, action = MENU_OPTIONS[choice]
        console.clear()
        action()

        divider()
        Prompt.ask("  Press Enter to return to menu", default="")


if __name__ == "__main__":
    main()
