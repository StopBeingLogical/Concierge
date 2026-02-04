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
from bit.job import Job, JobManager
from bit.packages import TaskPackage
from bit.registry import PackageRegistry
from bit.planner import Planner
from bit.plan import PlanManager
from bit.approval import Approval
from bit.router import Router
from bit.logs import LogReader

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


@app.command()
def job(
    action: str = typer.Argument(
        ...,
        help="Action: from-intent, show, list, validate"
    ),
    intent_id: Optional[str] = typer.Option(
        None,
        "--intent-id",
        help="Intent ID or hash (for 'from-intent' action)"
    ),
    job_id: Optional[str] = typer.Option(
        None,
        "--job-id",
        help="Job ID (for 'show' and 'validate' actions)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional, uses active workspace if not provided)"
    )
) -> None:
    """Manage job specifications.

    Actions:
    - from-intent: Create job from intent
    - show: Display job by ID
    - list: List all jobs
    - validate: Verify job integrity
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

    if action == "from-intent":
        if not intent_id:
            raise typer.BadParameter("--intent-id required for 'from-intent' action")

        try:
            # Load intent
            intent_manager = IntentManager(str(ws_path))
            intent_obj = intent_manager.load(intent_id)

            if not intent_obj:
                console.print(f"[red]✗[/red] Intent not found: {intent_id}")
                sys.exit(1)

            # Verify intent hash
            if not intent_manager.verify_hash(intent_obj):
                console.print(f"[red]✗[/red] Intent hash verification failed!")
                sys.exit(1)

            # Get current mode
            session = SessionManager(str(ws_path))
            mode = session.get_mode()

            # Create job
            job_manager = JobManager(str(ws_path))
            job_obj = job_manager.create_from_intent(intent_obj, mode)

            # Save job
            job_path = job_manager.save(job_obj)

            console.print(f"[green]✓[/green] Job created")
            console.print(f"[dim]Job ID:[/dim] {job_obj.job_id}")
            console.print(f"[dim]Status:[/dim] {job_obj.status.value}")
            console.print(f"[dim]Intent Ref:[/dim] {job_obj.intent_ref}")
            console.print(f"[dim]Mode:[/dim] {job_obj.mode_used}")
            console.print(f"[dim]File:[/dim] {job_path}")

            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(2)

    elif action == "show":
        if not job_id:
            raise typer.BadParameter("--job-id required for 'show' action")

        try:
            job_manager = JobManager(str(ws_path))
            job_obj = job_manager.load(job_id)

            if not job_obj:
                console.print(f"[red]✗[/red] Job not found: {job_id}")
                sys.exit(1)

            table = Table(title=f"Job {job_obj.job_id}")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Job ID", job_obj.job_id)
            table.add_row("Status", job_obj.status.value)
            table.add_row("Created", job_obj.created_at)
            table.add_row("Mode", job_obj.mode_used)
            table.add_row("Intent Ref", job_obj.intent_ref)
            table.add_row("Intent Hash", job_obj.intent_hash[:16])
            table.add_row("Job Spec Hash", job_obj.job_spec_hash[:16])
            table.add_row("Title", job_obj.job_spec.title)
            table.add_row("Intent", job_obj.job_spec.intent)
            table.add_row("Success Criteria", ", ".join(job_obj.job_spec.success_criteria) if job_obj.job_spec.success_criteria else "(none)")
            table.add_row("Constraints", ", ".join(job_obj.job_spec.constraints) if job_obj.job_spec.constraints else "(none)")

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    elif action == "list":
        try:
            job_manager = JobManager(str(ws_path))
            jobs = job_manager.list_jobs()

            if not jobs:
                console.print("[dim]No jobs found[/dim]")
                sys.exit(0)

            table = Table(title="Jobs")
            table.add_column("Job ID", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Title", style="white")
            table.add_column("Mode", style="dim")
            table.add_column("Created", style="dim")

            for job_obj in jobs:
                table.add_row(
                    job_obj.job_id,
                    job_obj.status.value,
                    job_obj.job_spec.title,
                    job_obj.mode_used,
                    job_obj.created_at,
                )

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    elif action == "validate":
        if not job_id:
            raise typer.BadParameter("--job-id required for 'validate' action")

        try:
            job_manager = JobManager(str(ws_path))
            job_obj = job_manager.load(job_id)

            if not job_obj:
                console.print(f"[red]✗[/red] Job not found: {job_id}")
                sys.exit(1)

            # Verify job spec hash
            spec_valid = job_manager.verify_job_spec_hash(job_obj)
            intent_valid = job_manager.verify_intent_hash(job_obj)

            console.print(f"[bold]Job Validation: {job_id}[/bold]")

            if spec_valid:
                console.print(f"[green]✓[/green] Job spec hash is valid")
            else:
                console.print(f"[red]✗[/red] Job spec hash is invalid!")

            if intent_valid:
                console.print(f"[green]✓[/green] Intent hash is valid")
            else:
                console.print(f"[red]✗[/red] Intent hash is invalid!")

            if spec_valid and intent_valid:
                sys.exit(0)
            else:
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    else:
        raise typer.BadParameter(f"Unknown action: {action}")


@app.command()
def package(
    action: str = typer.Argument(
        ...,
        help="Action: list, show, validate"
    ),
    package_id: Optional[str] = typer.Option(
        None,
        "--package-id",
        help="Package ID (for 'show' and 'validate' actions)"
    ),
    version: Optional[str] = typer.Option(
        None,
        "--version",
        help="Package version (for 'show' and 'validate' actions, defaults to latest)"
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        help="Filter by category (for 'list' action)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional, uses active workspace if not provided)"
    )
) -> None:
    """Manage task packages.

    Actions:
    - list: Show all packages (optionally filtered by category)
    - show: Display package details by ID and version
    - validate: Verify package integrity
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

    if action == "list":
        try:
            registry = PackageRegistry(str(ws_path))
            packages = registry.list_packages(category)

            if not packages:
                if category:
                    console.print(f"[dim]No packages found in category: {category}[/dim]")
                else:
                    console.print("[dim]No packages found[/dim]")
                sys.exit(0)

            table = Table(title="Task Packages")
            table.add_column("Package ID", style="cyan")
            table.add_column("Version", style="white")
            table.add_column("Title", style="white")
            table.add_column("Category", style="dim")

            for pkg in sorted(packages, key=lambda p: (p.intent.category, p.package_id)):
                table.add_row(
                    pkg.package_id,
                    pkg.version,
                    pkg.title,
                    pkg.intent.category,
                )

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(2)

    elif action == "show":
        if not package_id:
            raise typer.BadParameter("--package-id required for 'show' action")

        try:
            registry = PackageRegistry(str(ws_path))

            # If no version specified, try to find any version
            if not version:
                packages = registry.list_packages()
                matching = [p for p in packages if p.package_id == package_id]
                if matching:
                    # Use first (most recent) version
                    pkg = matching[0]
                    version = pkg.version
                else:
                    console.print(f"[red]✗[/red] Package not found: {package_id}")
                    sys.exit(1)
            else:
                pkg = registry.get_package(package_id, version)
                if not pkg:
                    console.print(f"[red]✗[/red] Package not found: {package_id} v{version}")
                    sys.exit(1)

            if not pkg:
                pkg = registry.get_package(package_id, version)
                if not pkg:
                    console.print(f"[red]✗[/red] Package not found: {package_id}")
                    sys.exit(1)

            table = Table(title=f"Package {pkg.package_id} v{pkg.version}")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Package ID", pkg.package_id)
            table.add_row("Version", pkg.version)
            table.add_row("Title", pkg.title)
            table.add_row("Description", pkg.description)
            table.add_row("Category", pkg.intent.category)
            table.add_row("Verbs", ", ".join(pkg.intent.verbs) if pkg.intent.verbs else "(none)")
            table.add_row("Entities", ", ".join(pkg.intent.entities) if pkg.intent.entities else "(none)")
            table.add_row("Pipeline Steps", str(len(pkg.pipeline.steps)))
            table.add_row("Approval Required", str(pkg.approval.required))
            table.add_row("Verification Required", str(pkg.verification.required))

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    elif action == "validate":
        if not package_id:
            raise typer.BadParameter("--package-id required for 'validate' action")

        try:
            registry = PackageRegistry(str(ws_path))

            # If no version specified, find any version
            if not version:
                packages = registry.list_packages()
                matching = [p for p in packages if p.package_id == package_id]
                if matching:
                    pkg = matching[0]
                    version = pkg.version
                else:
                    console.print(f"[red]✗[/red] Package not found: {package_id}")
                    sys.exit(1)
            else:
                pkg = registry.get_package(package_id, version)
                if not pkg:
                    console.print(f"[red]✗[/red] Package not found: {package_id} v{version}")
                    sys.exit(1)

            if not pkg:
                pkg = registry.get_package(package_id, version)
                if not pkg:
                    console.print(f"[red]✗[/red] Package not found: {package_id}")
                    sys.exit(1)

            errors = registry.validate_package(pkg)

            console.print(f"[bold]Package Validation: {pkg.package_id} v{pkg.version}[/bold]")

            if not errors:
                console.print(f"[green]✓[/green] Package is valid")
                sys.exit(0)
            else:
                console.print(f"[red]✗[/red] Package validation failed:")
                for error in errors:
                    console.print(f"  - {error}")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    else:
        raise typer.BadParameter(f"Unknown action: {action}")


@app.command()
def plan(
    action: str = typer.Argument(
        ...,
        help="Action: generate, show, list"
    ),
    job_id: Optional[str] = typer.Option(
        None,
        "--job-id",
        help="Job ID (for 'generate', 'show', and 'list' actions)"
    ),
    plan_id: Optional[str] = typer.Option(
        None,
        "--plan-id",
        help="Plan ID (for 'show' action)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional, uses active workspace if not provided)"
    )
) -> None:
    """Manage execution plans.

    Actions:
    - generate: Generate plan from job spec
    - show: Display plan details
    - list: List all plans for a job
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

    if action == "generate":
        if not job_id:
            raise typer.BadParameter("--job-id required for 'generate' action")

        try:
            # Load job
            job_manager = JobManager(str(ws_path))
            job_obj = job_manager.load(job_id)

            if not job_obj:
                console.print(f"[red]✗[/red] Job not found: {job_id}")
                sys.exit(1)

            # Initialize planner
            registry = PackageRegistry(str(ws_path))
            planner = Planner(registry)

            # Try to match package
            match_result = planner.match_package(job_obj.job_spec)

            if not match_result:
                console.print(f"[red]✗[/red] No matching package found for job")
                sys.exit(1)

            package, confidence = match_result

            # Generate plan
            execution_plan = planner.generate_plan(job_obj, package, confidence)

            # Save plan
            plan_manager = PlanManager(str(ws_path))
            plan_path = plan_manager.save(execution_plan)

            console.print(f"[green]✓[/green] Plan generated")
            console.print(f"[dim]Plan ID:[/dim] {execution_plan.plan_id}")
            console.print(f"[dim]Package:[/dim] {package.package_id} v{package.version}")
            console.print(f"[dim]Confidence:[/dim] {confidence:.2%}")
            console.print(f"[dim]Pipeline Steps:[/dim] {len(execution_plan.pipeline.steps)}")
            console.print(f"[dim]File:[/dim] {plan_path}")

            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(2)

    elif action == "show":
        if not job_id or not plan_id:
            raise typer.BadParameter("--job-id and --plan-id required for 'show' action")

        try:
            plan_manager = PlanManager(str(ws_path))
            execution_plan = plan_manager.load(job_id, plan_id)

            if not execution_plan:
                console.print(f"[red]✗[/red] Plan not found: {plan_id}")
                sys.exit(1)

            table = Table(title=f"Plan {execution_plan.plan_id}")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Plan ID", execution_plan.plan_id)
            table.add_row("Job ID", execution_plan.job_id)
            table.add_row("Package", f"{execution_plan.package_id} v{execution_plan.package_version}")
            table.add_row("Confidence", f"{execution_plan.matched_confidence:.2%}")
            table.add_row("Created", execution_plan.created_at)
            table.add_row("Pipeline Steps", str(len(execution_plan.pipeline.steps)))
            table.add_row("CPU Cores", str(execution_plan.resources.total_cpu_cores))
            table.add_row("Memory (MB)", str(execution_plan.resources.total_memory_mb))

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    elif action == "list":
        if not job_id:
            raise typer.BadParameter("--job-id required for 'list' action")

        try:
            plan_manager = PlanManager(str(ws_path))
            plans = plan_manager.list_plans(job_id)

            if not plans:
                console.print(f"[dim]No plans found for job: {job_id}[/dim]")
                sys.exit(0)

            table = Table(title=f"Plans for Job {job_id}")
            table.add_column("Plan ID", style="cyan")
            table.add_column("Package", style="white")
            table.add_column("Confidence", style="white")
            table.add_column("Created", style="dim")

            for p in plans:
                table.add_row(
                    p.plan_id,
                    f"{p.package_id} v{p.package_version}",
                    f"{p.matched_confidence:.2%}",
                    p.created_at,
                )

            console.print(table)
            sys.exit(0)

        except Exception as e:
            console.print(f"[red]✗[/red] Error: {e}")
            sys.exit(1)

    else:
        raise typer.BadParameter(f"Unknown action: {action}")


@app.command()
def approve(
    job_id: str = typer.Argument(
        ...,
        help="Job ID to approve"
    ),
    plan_id: Optional[str] = typer.Option(
        None,
        "--plan-id",
        help="Plan ID to approve (uses latest if not specified)"
    ),
    note: Optional[str] = typer.Option(
        None,
        "--note",
        help="Approval note"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional)"
    )
) -> None:
    """Approve a job for execution.

    Job must be in PLANNED status and have an associated plan.
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

    try:
        # Load job
        job_manager = JobManager(str(ws_path))
        job_obj = job_manager.load(job_id)

        if not job_obj:
            console.print(f"[red]✗[/red] Job not found: {job_id}")
            sys.exit(1)

        # Get plan ID
        if not plan_id:
            plan_manager = PlanManager(str(ws_path))
            latest_plan = plan_manager.get_latest_plan(job_id)

            if not latest_plan:
                console.print(f"[red]✗[/red] No plan found for job. Use 'bit plan generate' first.")
                sys.exit(1)

            plan_id = latest_plan.plan_id

        # Transition to PLANNED if still DRAFT
        if job_obj.status == JobStatus.DRAFT:
            job_obj = job_manager.transition_to_planned(job_obj)

        # Approve job
        if job_obj.status != JobStatus.PLANNED:
            console.print(f"[red]✗[/red] Job must be in PLANNED status to approve. Current: {job_obj.status.value}")
            sys.exit(1)

        job_obj = job_manager.approve_job(job_obj, plan_id, approver="user", note=note)
        job_manager.save(job_obj)

        console.print(f"[green]✓[/green] Job approved")
        console.print(f"[dim]Job ID:[/dim] {job_obj.job_id}")
        console.print(f"[dim]Plan ID:[/dim] {plan_id}")
        console.print(f"[dim]Status:[/dim] {job_obj.status.value}")
        if note:
            console.print(f"[dim]Note:[/dim] {note}")

        sys.exit(0)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(2)


@app.command()
def deny(
    job_id: str = typer.Argument(
        ...,
        help="Job ID to deny"
    ),
    plan_id: Optional[str] = typer.Option(
        None,
        "--plan-id",
        help="Plan ID to deny (uses latest if not specified)"
    ),
    reason: Optional[str] = typer.Option(
        None,
        "--reason",
        help="Denial reason"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional)"
    )
) -> None:
    """Deny a job plan.

    Job must be in PLANNED status. Denial keeps job in PLANNED so different plan can be tried.
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

    try:
        # Load job
        job_manager = JobManager(str(ws_path))
        job_obj = job_manager.load(job_id)

        if not job_obj:
            console.print(f"[red]✗[/red] Job not found: {job_id}")
            sys.exit(1)

        # Get plan ID
        if not plan_id:
            plan_manager = PlanManager(str(ws_path))
            latest_plan = plan_manager.get_latest_plan(job_id)

            if not latest_plan:
                console.print(f"[red]✗[/red] No plan found for job.")
                sys.exit(1)

            plan_id = latest_plan.plan_id

        # Deny job
        if job_obj.status != JobStatus.PLANNED:
            console.print(f"[red]✗[/red] Job must be in PLANNED status to deny. Current: {job_obj.status.value}")
            sys.exit(1)

        job_obj = job_manager.deny_job(job_obj, plan_id, approver="user", reason=reason)
        job_manager.save(job_obj)

        console.print(f"[green]✓[/green] Job plan denied")
        console.print(f"[dim]Job ID:[/dim] {job_obj.job_id}")
        console.print(f"[dim]Plan ID:[/dim] {plan_id}")
        console.print(f"[dim]Status:[/dim] {job_obj.status.value}")
        if reason:
            console.print(f"[dim]Reason:[/dim] {reason}")
        console.print("[dim]Job remains in PLANNED status. You can generate a new plan and approve it.[/dim]")

        sys.exit(0)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(2)


@app.command()
def run(
    job_id: str = typer.Argument(
        ...,
        help="Job ID to execute"
    ),
    plan_id: Optional[str] = typer.Option(
        None,
        "--plan-id",
        help="Plan ID to execute (uses latest if not specified)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional)"
    )
) -> None:
    """Execute an approved job.

    Job must be in APPROVED status. Transitions to RUNNING and executes plan.
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

    try:
        # Load job
        job_manager = JobManager(str(ws_path))
        job_obj = job_manager.load(job_id)

        if not job_obj:
            console.print(f"[red]✗[/red] Job not found: {job_id}")
            sys.exit(1)

        # Check status
        if job_obj.status != JobStatus.APPROVED:
            console.print(f"[red]✗[/red] Job must be APPROVED to run. Current: {job_obj.status.value}")
            sys.exit(1)

        # Get plan
        if not plan_id:
            plan_manager = PlanManager(str(ws_path))
            latest_plan = plan_manager.get_latest_plan(job_id)

            if not latest_plan:
                console.print(f"[red]✗[/red] No approved plan found for job.")
                sys.exit(1)

            plan_id = latest_plan.plan_id
        else:
            plan_manager = PlanManager(str(ws_path))
            latest_plan = plan_manager.load(job_id, plan_id)
            if not latest_plan:
                console.print(f"[red]✗[/red] Plan not found: {plan_id}")
                sys.exit(1)

        # Transition to RUNNING
        job_obj = job_manager.transition_to_running(job_obj)
        job_manager.save(job_obj)

        console.print(f"[bold]Executing job[/bold] {job_obj.job_id}")
        console.print(f"[dim]Plan:[/dim] {latest_plan.plan_id}")
        console.print(f"[dim]Pipeline Steps:[/dim] {len(latest_plan.pipeline.steps)}")

        # Execute plan
        router = Router(str(ws_path))
        success, run_record = router.execute_plan(latest_plan)

        if success:
            # Transition to COMPLETED
            job_obj = job_manager.complete_job(job_obj)
            job_manager.save(job_obj)

            console.print(f"[green]✓[/green] Job completed successfully")
            console.print(f"[dim]Run ID:[/dim] {run_record.run_id}")
            console.print(f"[dim]Duration:[/dim] {run_record.completed_at}")

            sys.exit(0)
        else:
            # Transition to FAILED
            job_obj = job_manager.fail_job(job_obj)
            job_manager.save(job_obj)

            console.print(f"[red]✗[/red] Job execution failed")
            console.print(f"[dim]Run ID:[/dim] {run_record.run_id}")

            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(2)


@app.command()
def status(
    job_id: str = typer.Argument(
        ...,
        help="Job ID to check status"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional)"
    )
) -> None:
    """Show job status and execution state."""
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

    try:
        log_reader = LogReader(str(ws_path))
        status_info = log_reader.get_job_status(job_id)

        if "error" in status_info:
            console.print(f"[red]✗[/red] {status_info['error']}")
            sys.exit(1)

        table = Table(title=f"Job Status: {job_id}")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Status", status_info["status"])
        table.add_row("Title", status_info.get("title", "N/A"))
        table.add_row("Intent", status_info.get("intent", "N/A")[:80])
        table.add_row("Created", status_info.get("created_at", "N/A"))

        if "current_step" in status_info:
            table.add_row("Current Step", status_info["current_step"])

        if "total_events" in status_info:
            table.add_row("Total Events", str(status_info["total_events"]))

        if "latest_event" in status_info:
            table.add_row("Latest Event", status_info["latest_event"])

        console.print(table)
        sys.exit(0)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


@app.command()
def tail(
    job_id: str = typer.Argument(
        ...,
        help="Job ID to tail logs for"
    ),
    n: int = typer.Option(
        10,
        "--lines",
        help="Number of events to show (default: 10)"
    ),
    run_id: Optional[str] = typer.Option(
        None,
        "--run-id",
        help="Specific run ID (uses latest if not specified)"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional)"
    )
) -> None:
    """Tail job execution logs."""
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

    try:
        log_reader = LogReader(str(ws_path))

        if run_id:
            log = log_reader.get_run_log(job_id, run_id)
        else:
            log = log_reader.get_latest_run_log(job_id)

        if not log:
            console.print(f"[red]✗[/red] No logs found for job: {job_id}")
            sys.exit(1)

        events = log.tail(n)

        if not events:
            console.print("[dim]No events found[/dim]")
            sys.exit(0)

        console.print(f"[bold]Last {len(events)} events[/bold]")
        for event in events:
            console.print(log_reader._format_event(event))

        sys.exit(0)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


@app.command()
def artifacts(
    job_id: str = typer.Argument(
        ...,
        help="Job ID to list artifacts for"
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Workspace path (optional)"
    )
) -> None:
    """List artifacts produced by a job."""
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

    try:
        log_reader = LogReader(str(ws_path))
        artifacts_list = log_reader.get_job_artifacts(job_id)

        if not artifacts_list:
            console.print(f"[dim]No artifacts found for job: {job_id}[/dim]")
            sys.exit(0)

        table = Table(title=f"Artifacts for Job {job_id}")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("Size (bytes)", style="dim")
        table.add_column("Modified", style="dim")

        for artifact in artifacts_list:
            table.add_row(
                artifact["name"],
                artifact["path"],
                str(artifact["size"]),
                artifact["modified"],
            )

        console.print(table)
        sys.exit(0)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
