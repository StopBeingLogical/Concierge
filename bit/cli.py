"""Command-line interface for bit."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bit.workspace import Workspace, WorkspaceConfig
from bit.modes import (
    MODE_CATALOG,
    SessionManager,
    get_mode,
    list_modes,
    validate_mode,
)
from bit.intent import Intent, IntentSynthesizer, IntentManager

app = typer.Typer(help="bit: Personal AI orchestration shell")
console = Console()

# Global state
_active_workspace: Optional[Workspace] = None


def get_workspace() -> Workspace:
    """Get active workspace or raise error."""
    global _active_workspace
    if _active_workspace is None:
        raise typer.BadParameter("No workspace active. Use 'bit ws open' first.")
    return _active_workspace


@app.command()
def init(
    path: str = typer.Argument(
        ".",
        help="Path to create workspace (default: current directory)"
    )
) -> None:
    """Initialize a new bit workspace.

    Creates workspace structure:
    - context/       (session state)
    - jobs/          (job specs + plans)
    - artifacts/     (outputs + logs)
    - logs/          (event log)
    - cache/         (determinism cache)
    - scratch/       (temporary files)
    """
    workspace_path = Path(path).absolute()

    console.print(f"[bold]Initializing workspace[/bold] at {workspace_path}")

    try:
        ws = Workspace(str(workspace_path))
        config = ws.initialize()

        console.print("[green]✓[/green] Workspace initialized")
        console.print(f"[dim]Path:[/dim] {config.workspace_path}")
        console.print(f"[dim]Created:[/dim] {config.created_at}")

        sys.exit(0)

    except FileExistsError as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(2)


@app.command()
def ws(
    action: str = typer.Argument(
        ...,
        help="Action: open, validate, show"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (for 'open' action)"
    )
) -> None:
    """Manage workspace.

    Actions:
    - open: Set active workspace
    - validate: Check workspace structure
    - show: Display active workspace info
    """
    global _active_workspace

    if action == "open":
        if not path:
            raise typer.BadParameter("--path required for 'open' action")

        workspace_path = Path(path).absolute()

        try:
            ws = Workspace(str(workspace_path))
            ws.validate()
            _active_workspace = ws

            config = ws.load_config()
            console.print(f"[green]✓[/green] Workspace opened: {workspace_path}")
            console.print(f"[dim]Created:[/dim] {config.created_at}")

            sys.exit(0)

        except FileNotFoundError as e:
            console.print(f"[red]✗[/red] {e}")
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]✗[/red] Validation failed: {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(2)

    elif action == "validate":
        if not path:
            raise typer.BadParameter("--path required for 'validate' action")

        workspace_path = Path(path).absolute()

        try:
            ws = Workspace(str(workspace_path))
            ws.validate()
            console.print(f"[green]✓[/green] Workspace valid: {workspace_path}")
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Validation failed: {e}")
            sys.exit(1)

    elif action == "show":
        try:
            ws = get_workspace()
            config = ws.load_config()

            table = Table(title="Active Workspace")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Path", config.workspace_path)
            table.add_row("Created", config.created_at)
            table.add_row("Version", config.version)

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] {e}")
            sys.exit(1)

    else:
        raise typer.BadParameter(f"Unknown action: {action}")


@app.command()
def mode(
    action: str = typer.Argument(
        ...,
        help="Action: list, set, show"
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        help="Mode name (for 'set' action)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (required for set/show)"
    )
) -> None:
    """Manage reasoning bias modes.

    Actions:
    - list: Show all available modes
    - set: Set active mode for workspace
    - show: Display current mode for workspace

    Modes are reasoning bias hints that don't affect job schema.
    """
    if action == "list":
        table = Table(title="Available Modes")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Bias", style="dim")

        for mode_spec in list_modes():
            table.add_row(mode_spec.name, mode_spec.description, mode_spec.bias)

        console.print(table)
        sys.exit(0)

    elif action == "set":
        if not path:
            raise typer.BadParameter("--path required for 'set' action")
        if not name:
            raise typer.BadParameter("--name required for 'set' action")

        workspace_path = Path(path).absolute()

        try:
            # Validate workspace exists
            ws = Workspace(str(workspace_path))
            ws.validate()

            # Set mode
            session = SessionManager(str(workspace_path))
            state = session.set_mode(name)

            mode_spec = get_mode(name)
            console.print(f"[green]✓[/green] Mode set to [cyan]{name}[/cyan]")
            console.print(f"[dim]Bias:[/dim] {mode_spec.bias}")
            sys.exit(0)

        except ValueError as e:
            console.print(f"[red]✗[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(2)

    elif action == "show":
        if not path:
            raise typer.BadParameter("--path required for 'show' action")

        workspace_path = Path(path).absolute()

        try:
            # Validate workspace exists
            ws = Workspace(str(workspace_path))
            ws.validate()

            # Get current mode
            session = SessionManager(str(workspace_path))
            state = session.load()
            mode_spec = get_mode(state.active_mode)

            table = Table(title="Current Mode")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Mode", state.active_mode)
            table.add_row("Description", mode_spec.description if mode_spec else "Unknown")
            table.add_row("Bias", mode_spec.bias if mode_spec else "Unknown")
            if state.updated_at:
                table.add_row("Updated", state.updated_at)

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    else:
        raise typer.BadParameter(f"Unknown action: {action}")


@app.command()
def intent(
    action: str = typer.Argument(
        ...,
        help="Action: synth, show, list, verify"
    ),
    text: Optional[str] = typer.Option(
        None,
        "--text",
        help="Intent text (for 'synth' action)"
    ),
    hash_value: Optional[str] = typer.Option(
        None,
        "--hash",
        help="Intent hash (for 'show' and 'verify' actions)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional, uses active workspace if not provided)"
    )
) -> None:
    """Manage intent artifacts.

    Actions:
    - synth: Synthesize intent from text
    - show: Display intent by hash
    - list: List all intents
    - verify: Verify intent hash integrity
    """
    # Get workspace
    try:
        if path:
            ws_path = Path(path).absolute()
            ws = Workspace(str(ws_path))
            ws.validate()
        else:
            ws = get_workspace()
            ws_path = ws.path
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)

    if action == "synth":
        if not text:
            raise typer.BadParameter("--text required for 'synth' action")

        try:
            # Get current mode
            session = SessionManager(str(ws_path))
            mode = session.get_mode()

            # Synthesize intent
            intent_obj = IntentSynthesizer.synthesize(text, mode)

            # Save intent
            manager = IntentManager(str(ws_path))
            intent_path = manager.save(intent_obj)

            console.print(f"[green]✓[/green] Intent synthesized")
            console.print(f"[dim]Hash:[/dim] {intent_obj.intent_hash}")
            console.print(f"[dim]ID:[/dim] {intent_obj.intent_id}")
            console.print(f"[dim]Mode:[/dim] {intent_obj.mode}")
            console.print(f"[dim]Distilled:[/dim] {intent_obj.distilled_intent}")
            console.print(f"[dim]Success:[/dim] {intent_obj.success_criteria}")
            if intent_obj.constraints:
                console.print(f"[dim]Constraints:[/dim] {', '.join(intent_obj.constraints)}")

            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(2)

    elif action == "show":
        if not hash_value:
            raise typer.BadParameter("--hash required for 'show' action")

        try:
            manager = IntentManager(str(ws_path))
            intent_obj = manager.load(hash_value)

            if not intent_obj:
                console.print(f"[red]✗[/red] Intent not found: {hash_value}")
                sys.exit(1)

            table = Table(title=f"Intent {intent_obj.intent_hash[:16]}")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Hash", intent_obj.intent_hash)
            table.add_row("ID", intent_obj.intent_id)
            table.add_row("Mode", intent_obj.mode)
            table.add_row("Distilled", intent_obj.distilled_intent)
            table.add_row("Success Criteria", intent_obj.success_criteria)
            table.add_row("Constraints", ", ".join(intent_obj.constraints) if intent_obj.constraints else "(none)")
            table.add_row("Created", intent_obj.created_at)

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    elif action == "list":
        try:
            manager = IntentManager(str(ws_path))
            intents = manager.list_intents()

            if not intents:
                console.print("[dim]No intents found[/dim]")
                sys.exit(0)

            table = Table(title="Intents")
            table.add_column("Hash (first 16)", style="cyan")
            table.add_column("Distilled Intent", style="white")
            table.add_column("Mode", style="dim")
            table.add_column("Created", style="dim")

            for intent_obj in intents:
                table.add_row(
                    intent_obj.intent_hash[:16],
                    intent_obj.distilled_intent,
                    intent_obj.mode,
                    intent_obj.created_at,
                )

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    elif action == "verify":
        if not hash_value:
            raise typer.BadParameter("--hash required for 'verify' action")

        try:
            manager = IntentManager(str(ws_path))
            intent_obj = manager.load(hash_value)

            if not intent_obj:
                console.print(f"[red]✗[/red] Intent not found: {hash_value}")
                sys.exit(1)

            is_valid = manager.verify_hash(intent_obj)

            if is_valid:
                console.print(f"[green]✓[/green] Hash is valid")
                sys.exit(0)
            else:
                console.print(f"[red]✗[/red] Hash verification failed!")
                console.print(f"[dim]Expected:[/dim] {intent_obj.intent_hash}")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    else:
        raise typer.BadParameter(f"Unknown action: {action}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
