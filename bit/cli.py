"""Command-line interface for bit."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bit.workspace import Workspace, WorkspaceConfig

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


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
