from __future__ import annotations

import asyncio
import json
import random
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from devdex import __version__
from devdex.config import DevDexConfig
from devdex.models import (
    DeploymentTarget,
    DevDexPipelineState,
    GeneratedArtifact,
    GenerationResult,
    LandingPageChoice,
)

_hidden_commands: dict[str, callable] = {}
_event_hooks: dict[str, list[callable]] = {}


def register_hidden_command(name: str):
    def decorator(fn):
        _hidden_commands[name] = fn
        return fn

    return decorator


def on_event(event_name: str):
    def decorator(fn):
        _event_hooks.setdefault(event_name, []).append(fn)
        return fn

    return decorator


def emit_event(event_name: str, **kwargs):
    for hook in _event_hooks.get(event_name, []):
        try:
            hook(**kwargs)
        except Exception:
            pass


console = Console(stderr=True)
stdout_console = Console()


def _flush_stdin() -> None:
    try:
        import termios

        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except (ImportError, termios.error, OSError, ValueError):
        pass

app = typer.Typer(
    name="devdex",
    help="DevDex — Scan your codebase, generate your launch kit.",
    no_args_is_help=True,
)

LOGOS = {
    "pokeball": (
        "      [color(196)]████████████[/]      \n"
        "   [color(196)]██████████████████[/]   \n"
        " [color(196)]██████████████████████[/] \n"
        " [color(196)]████████[/][color(235)]██████[/][color(196)]████████[/] \n"
        " [color(235)]████████[/][color(231)]██████[/][color(235)]████████[/] \n"
        " [color(231)]████████[/][color(235)]██████[/][color(231)]████████[/] \n"
        "   [color(231)]██████████████████[/]   \n"
        "      [color(231)]████████████[/]      "
    ),
    "greatball": (
        "      [color(33)]████████████[/]      \n"
        "   [color(196)]███[/][color(33)]████████████[/][color(196)]███[/]   \n"
        " [color(196)]█████[/][color(33)]████████████[/][color(196)]█████[/] \n"
        " [color(33)]███████[/][color(235)]████████[/][color(33)]███████[/] \n"
        " [color(235)]████████[/][color(231)]██████[/][color(235)]████████[/] \n"
        " [color(231)]████████[/][color(235)]██████[/][color(231)]████████[/] \n"
        "   [color(231)]██████████████████[/]   \n"
        "      [color(231)]████████████[/]      "
    ),
    "ultraball": (
        "      [color(235)]████████████[/]      \n"
        "   [color(220)]███[/][color(235)]████████████[/][color(220)]███[/]   \n"
        " [color(220)]█████[/][color(235)]████████████[/][color(220)]█████[/] \n"
        " [color(220)]███████[/][color(235)]████████[/][color(220)]███████[/] \n"
        " [color(235)]████████[/][color(231)]██████[/][color(235)]████████[/] \n"
        " [color(231)]████████[/][color(235)]██████[/][color(231)]████████[/] \n"
        "   [color(231)]██████████████████[/]   \n"
        "      [color(231)]████████████[/]      "
    ),
    "masterball": (
        "      [color(93)]████████████[/]      \n"
        "   [color(206)]██[/][color(93)]█[/][color(231)]█[/][color(93)]██[/][color(231)]█[/][color(93)]████[/][color(231)]█[/][color(93)]██[/][color(231)]█[/][color(93)]█[/][color(206)]██[/]   \n"
        " [color(206)]███[/][color(93)]███[/][color(231)]█[/][color(93)]██[/][color(231)]█[/][color(93)]██[/][color(231)]█[/][color(93)]██[/][color(231)]█[/][color(93)]███[/][color(206)]███[/] \n"
        " [color(206)]███[/][color(93)]████[/][color(235)]████████[/][color(93)]████[/][color(206)]███[/] \n"
        " [color(235)]████████[/][color(231)]██████[/][color(235)]████████[/] \n"
        " [color(231)]████████[/][color(235)]██████[/][color(231)]████████[/] \n"
        "   [color(231)]██████████████████[/]   \n"
        "      [color(231)]████████████[/]      "
    ),
}

LOGOS_COMPACT = {
    "pokeball": (
        "   [color(196)]████████[/]   \n"
        " [color(196)]████[/][color(235)]████[/][color(196)]████[/] \n"
        " [color(235)]████[/][color(231)]████[/][color(235)]████[/] \n"
        " [color(231)]████[/][color(235)]████[/][color(231)]████[/] \n"
        "   [color(231)]████████[/]   "
    ),
    "greatball": (
        "   [color(33)]████████[/]   \n"
        " [color(196)]██[/][color(33)]████████[/][color(196)]██[/] \n"
        " [color(235)]████[/][color(231)]████[/][color(235)]████[/] \n"
        " [color(231)]████[/][color(235)]████[/][color(231)]████[/] \n"
        "   [color(231)]████████[/]   "
    ),
    "ultraball": (
        "   [color(235)]████████[/]   \n"
        " [color(220)]██[/][color(235)]████████[/][color(220)]██[/] \n"
        " [color(235)]████[/][color(231)]████[/][color(235)]████[/] \n"
        " [color(231)]████[/][color(235)]████[/][color(231)]████[/] \n"
        "   [color(231)]████████[/]   "
    ),
    "masterball": (
        "   [color(93)]████████[/]   \n"
        " [color(206)]██[/][color(93)]██[/][color(231)]█[/][color(93)]██[/][color(231)]█[/][color(93)]██[/][color(206)]██[/] \n"
        " [color(235)]████[/][color(231)]████[/][color(235)]████[/] \n"
        " [color(231)]████[/][color(235)]████[/][color(231)]████[/] \n"
        "   [color(231)]████████[/]   "
    ),
}

LOGO_FOOTER = "[bold yellow]DevDéx[/] [dim]v{ver}[/]\n[bold green]Gotta Ship 'Em All![/]"

_LOGO_FULL_MIN_WIDTH = 70
_LOGO_COMPACT_MIN_WIDTH = 56


def _get_logo_for_width(ball_name: str, term_width: int) -> str | None:
    if term_width >= _LOGO_FULL_MIN_WIDTH:
        return LOGOS.get(ball_name, LOGOS["pokeball"])
    elif term_width >= _LOGO_COMPACT_MIN_WIDTH:
        return LOGOS_COMPACT.get(ball_name, LOGOS_COMPACT["pokeball"])
    return None


def _get_footer_for_width(term_width: int) -> str | None:
    if term_width >= _LOGO_FULL_MIN_WIDTH:
        return "panel"
    elif term_width >= _LOGO_COMPACT_MIN_WIDTH:
        return "line"
    return None

BALL_THEMES = {
    "pokeball":   {"rich": "#ff5555", "accent": "bold red",     "hex": "#ff5555", "border": "red"},
    "greatball":  {"rich": "#55aaff", "accent": "bold blue",    "hex": "#55aaff", "border": "blue"},
    "ultraball":  {"rich": "#ffdd55", "accent": "bold yellow",  "hex": "#ffdd55", "border": "yellow"},
    "masterball": {"rich": "#ff55ff", "accent": "bold magenta", "hex": "#ff55ff", "border": "magenta"},
}

_session_theme: dict[str, str] = BALL_THEMES["pokeball"]


def get_session_theme() -> dict[str, str]:
    return _session_theme


_session_logo: str = ""


def _show_logo():
    global _session_theme, _session_logo
    name = random.choice(list(LOGOS.keys()))
    _session_logo = name
    _session_theme = BALL_THEMES[name]


class _ProgressDisplay:

    def __init__(self, task_names: list[str]):
        self._names = task_names
        self._status: dict[str, str] = {n: "pending" for n in task_names}
        self._errors: dict[str, str] = {}
        self._spinners: dict[str, Spinner] = {
            n: Spinner("dots", text=Text.from_markup(f"  {n}..."))
            for n in task_names
        }

    def set_running(self, name: str):
        self._status[name] = "running"

    def set_done(self, name: str):
        self._status[name] = "done"

    def set_failed(self, name: str, error: str):
        self._status[name] = "failed"
        self._errors[name] = error[:60]

    def __rich_console__(self, console, options):
        theme = get_session_theme()
        primary = theme["rich"]
        for name in self._names:
            s = self._status[name]
            if s == "done":
                yield Text.from_markup(f"  [{primary}]●[/] {name}")
            elif s == "failed":
                yield Text.from_markup(
                    f"  [red]✗[/] {name} — {self._errors.get(name, 'error')}"
                )
            elif s == "running":
                yield self._spinners[name]
            else:
                yield Text.from_markup(f"  [dim]○[/] [dim]{name}[/]")


async def _generate_single(
    name: str,
    gen_fn,
    state: DevDexPipelineState,
    client,
    model: str,
    progress: _ProgressDisplay,
    live: Live,
    improvement_context: str = "",
) -> GeneratedArtifact:
    progress.set_running(name)
    live.refresh()
    artifact = await gen_fn(state, client, model, improvement_context=improvement_context)
    if artifact.success:
        progress.set_done(name)
    else:
        progress.set_failed(name, artifact.error)
    live.refresh()
    return artifact


async def _run_generation(
    state: DevDexPipelineState,
    cfg: DevDexConfig,
    landing_mode: LandingPageChoice = LandingPageChoice.PROMPT,
    improvement_context: str = "",
) -> list[GeneratedArtifact]:
    from openai import AsyncOpenAI

    from devdex.functions.appstore_gen import generate_appstore
    from devdex.functions.checklist_gen import generate_checklist
    from devdex.functions.landing_page_gen import generate_landing_page
    from devdex.functions.landing_page_html_gen import generate_landing_page_html
    from devdex.functions.privacy_policy_gen import generate_privacy_policy
    from devdex.functions.tos_gen import generate_tos

    models = cfg.models

    gen_model = cfg.finetuned_model_id or models["mistral_large"]

    client = AsyncOpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
    )

    is_web = state.understanding.deployment_target == DeploymentTarget.WEB_HOSTING

    tasks = [
        ("Privacy Policy", generate_privacy_policy, gen_model),
        ("Terms of Service", generate_tos, gen_model),
        ("Deployment Checklist", generate_checklist, models["ministral"]),
    ]

    if not is_web:
        tasks.insert(2, ("App Store Description", generate_appstore, gen_model))

    if landing_mode == LandingPageChoice.PROMPT:
        tasks.append(
            ("Landing Page Prompt", generate_landing_page, models["mistral_large"])
        )
    elif landing_mode == LandingPageChoice.HTML:
        tasks.append(
            ("Landing Page HTML", generate_landing_page_html, models["mistral_large"])
        )

    task_names = [name for name, _, _ in tasks]
    progress = _ProgressDisplay(task_names)

    with Live(progress, console=console, refresh_per_second=10) as live:
        coroutines = [
            _generate_single(
                name, fn, state, client, model, progress, live,
                improvement_context=improvement_context,
            )
            for name, fn, model in tasks
        ]
        artifacts = await asyncio.gather(*coroutines, return_exceptions=True)

    results: list[GeneratedArtifact] = []
    for i, artifact in enumerate(artifacts):
        if isinstance(artifact, Exception):
            results.append(
                GeneratedArtifact(
                    artifact_type=tasks[i][0].lower().replace(" ", "_"),
                    error=str(artifact),
                )
            )
        else:
            results.append(artifact)

    return results


@app.command()
def scan(
    path: Annotated[
        Path,
        typer.Argument(help="Path to the project to scan", exists=True),
    ] = Path("."),
    skip_interview: Annotated[
        bool, typer.Option("--skip-interview", help="Skip interactive interview")
    ] = False,
    no_branch: Annotated[
        bool, typer.Option("--no-branch", help="Don't create a git branch")
    ] = False,
    output: Annotated[
        Optional[Path], typer.Option("--output", "-o", help="Output directory")
    ] = None,
    branch: Annotated[
        Optional[str],
        typer.Option("--branch", "-b", help="Branch name for generated files"),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output machine-readable JSON to stdout")
    ] = False,
    no_telemetry: Annotated[
        bool, typer.Option("--no-telemetry", help="Disable anonymous feedback telemetry")
    ] = False,
):
    _show_logo()

    cfg = DevDexConfig.load()
    if no_telemetry:
        cfg.telemetry_enabled = False
    cfg.ensure_api_key()

    run_id = str(uuid.uuid4())

    if sys.stdin.isatty() and not json_output:
        from devdex.functions.deployment_guide import (
            _load_checklist_progress,
            run_deployment_guide,
        )

        project_key = str(path.resolve())
        loaded = _load_checklist_progress(project_key)
        if loaded:
            saved_states, saved_content, saved_theme_name = loaded
            completed_count = sum(1 for v in saved_states.values() if v)
            total_count = len(saved_states)

            console.print(
                f"\n[bold cyan]Found saved checklist progress "
                f"({completed_count}/{total_count} items completed).[/]"
            )
            _flush_stdin()
            try:
                answer = input("Resume walkthrough? [Y/n] ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Interrupted — exiting DevDex.[/]")
                raise typer.Exit(1)

            if answer in ("", "y", "yes"):
                theme = BALL_THEMES.get(saved_theme_name, get_session_theme())
                output_dir = output or (path.resolve() / "devdex-output")
                output_dir = Path(output_dir)
                run_deployment_guide(
                    saved_content, theme, output_dir,
                    project_path=project_key,
                    skip_resume_check=True,
                    initial_states=saved_states,
                    theme_name=saved_theme_name,
                )
                _flush_stdin()
                try:
                    _collect_feedback(output_dir, cfg)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Skipped feedback.[/]")
                return
            from devdex.functions.deployment_guide import _clear_checklist_progress
            _clear_checklist_progress(project_key)

    try:
        import io as _weave_io
        import warnings as _weave_warnings

        _old_stderr = sys.stderr
        sys.stderr = _weave_io.StringIO()
        try:
            with _weave_warnings.catch_warnings():
                _weave_warnings.simplefilter("ignore")
                import weave
                weave.init("devdex-generation")
        finally:
            sys.stderr = _old_stderr
    except Exception:
        pass

    emit_event("scan_start", path=str(path))

    from devdex.functions.codebase_scanner import run_scan

    with console.status("[bold cyan]Scanning codebase...[/]"):
        state = run_scan(str(path.resolve()))

    pu = state.understanding

    _print_scan_summary(pu)

    emit_event("scan_complete", state=state)

    if not skip_interview and sys.stdin.isatty():
        from devdex.functions.project_interviewer import run_interview_cli

        try:
            state = run_interview_cli(state)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted — exiting DevDex.[/]")
            raise typer.Exit(1)
        emit_event("interview_complete", state=state)
    else:
        state.interview_complete = True
        if not pu.app_purpose:
            pu.app_purpose = f"A {pu.platform.value} application"

    theme = get_session_theme()

    console.print(f"\n[{theme['accent']}]--- Generating Launch Kit ---[/]")
    console.print("[dim]This can take a while...[/]\n")

    from devdex.functions.feedback_loop import (
        build_improvement_context,
        display_feedback_summary,
        load_past_feedback,
    )

    with console.status("[bold cyan]Loading past feedback...[/]"):
        past_feedback = load_past_feedback(wandb_api_key=cfg.wandb_api_key or "")
        improvement_context = build_improvement_context(past_feedback)

    display_feedback_summary(past_feedback, theme)

    start_time = time.time()

    artifacts = asyncio.run(
        _run_generation(state, cfg, pu.landing_page, improvement_context=improvement_context)
    )

    elapsed = time.time() - start_time
    state.generation_complete = True
    emit_event("generation_complete", state=state)

    output_dir = output or (path.resolve() / "devdex-output")
    output_dir = Path(output_dir)

    result = GenerationResult(
        artifacts=artifacts,
        output_dir=str(output_dir),
        total_time_seconds=round(elapsed, 2),
    )

    _write_artifacts(output_dir, result)

    if cfg.supabase_url and cfg.supabase_key:
        try:
            from devdex.functions.vector_store import VectorStore

            vs = VectorStore(cfg.supabase_url, cfg.supabase_key, cfg.mistral_embed_api_key)
            for a in artifacts:
                if a.success and a.system_prompt and a.user_prompt:
                    vs.store_artifact({
                        "artifact_type": a.artifact_type,
                        "system_prompt": a.system_prompt,
                        "user_prompt": a.user_prompt,
                        "generated_content": a.content,
                        "model_used": a.model_used,
                        "run_id": run_id,
                    })
        except Exception:
            pass

    if cfg.telemetry_enabled and cfg.telemetry_url:
        try:
            from devdex.functions.feedback_loop import send_central_artifacts

            artifact_data = [
                {
                    "artifact_type": a.artifact_type,
                    "system_prompt": a.system_prompt,
                    "user_prompt": a.user_prompt,
                    "generated_content": a.content,
                    "model_used": a.model_used,
                }
                for a in artifacts
                if a.success and a.system_prompt and a.user_prompt
            ]
            if artifact_data:
                send_central_artifacts(artifact_data, cfg.telemetry_url, __version__, run_id=run_id)
        except Exception:
            pass

    if not no_branch:
        branch_name = (
            branch or f"devdex/launch-kit-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        result.branch_name = branch_name
        _create_git_branch(path.resolve(), output_dir, branch_name)

    _print_generation_summary(result, json_output)

    if sys.stdin.isatty() and not json_output:
        checklist_artifact = next(
            (a for a in artifacts if a.artifact_type == "deployment_checklist" and a.success),
            None,
        )
        if checklist_artifact:
            try:
                import questionary as _q
                _flush_stdin()
                walk = _q.confirm(
                    "Would you like to walk through the deployment checklist?",
                    default=False,
                ).ask()
                if walk:
                    from devdex.functions.deployment_guide import run_deployment_guide
                    run_deployment_guide(
                        checklist_artifact.content, theme, output_dir,
                        project_path=str(path.resolve()),
                        theme_name=_session_logo,
                    )
            except KeyboardInterrupt:
                console.print("\n[yellow]Skipped deployment walkthrough.[/]")

    if sys.stdin.isatty() and not json_output:
        _flush_stdin()
        try:
            _collect_feedback(output_dir, cfg, run_id=run_id)
        except KeyboardInterrupt:
            console.print("\n[yellow]Skipped feedback.[/]")


def _print_scan_summary(pu):
    import io as _io

    from rich.console import Console as _Console

    theme = get_session_theme()
    term_width = console.width or 100

    scan_table = Table(
        title="Scan Results", show_header=False, border_style=theme["border"],
    )
    scan_table.add_column("Field", style="bold")
    scan_table.add_column("Value")

    scan_table.add_row("Project", pu.display_name)
    scan_table.add_row("Platform", pu.platform.value)
    scan_table.add_row("Languages", ", ".join(pu.languages) or "Unknown")
    scan_table.add_row("Frameworks", ", ".join(pu.frameworks) or "None detected")
    scan_table.add_row("SDKs", ", ".join(pu.sdk_names) or "None detected")
    scan_table.add_row("Bundle ID", pu.bundle_id or "Not found")
    scan_table.add_row("Data Types", ", ".join(pu.all_data_types) or "None detected")
    scan_table.add_row(
        "Auth Methods", ", ".join(a.method for a in pu.auth_methods) or "None"
    )
    scan_table.add_row("In-App Purchases", "Yes" if pu.has_in_app_purchases else "No")

    if pu.color_theme:
        theme_str = ", ".join(f"{k}: {v}" for k, v in pu.color_theme.items())
        scan_table.add_row("Color Theme", Text(theme_str))
    else:
        scan_table.add_row("Color Theme", "None detected")

    logo_markup = _get_logo_for_width(_session_logo, term_width)

    if logo_markup is None:
        console.print()
        console.print(scan_table)
        return

    footer_markup = LOGO_FOOTER.format(ver=__version__)

    import re as _re
    _ansi_re = _re.compile(r"\x1b\[[0-9;]*m")

    def _visible_len(s: str) -> int:
        return len(_ansi_re.sub("", s))

    buf_left = _io.StringIO()
    c_left = _Console(file=buf_left, force_terminal=True, width=200, stderr=False)
    c_left.print(Text.from_markup(logo_markup))

    footer_mode = _get_footer_for_width(term_width)
    if footer_mode == "panel":
        c_left.print(Panel(Text.from_markup(footer_markup), border_style="dim", expand=False))
    elif footer_mode == "line":
        c_left.print(Text.from_markup(f"[bold yellow]DevDéx[/] [dim]v{__version__}[/]"))

    left_lines = buf_left.getvalue().rstrip("\n").split("\n")

    left_width = max((_visible_len(l) for l in left_lines), default=0)

    buf_right = _io.StringIO()
    right_width = max(40, term_width - left_width - 4)
    c_right = _Console(file=buf_right, force_terminal=True, width=right_width, stderr=False)
    c_right.print(scan_table)
    right_lines = buf_right.getvalue().rstrip("\n").split("\n")

    left_height = len(left_lines)
    right_height = len(right_lines)
    top_pad = max(0, (right_height - left_height) // 2)

    padded_left = [""] * top_pad + left_lines
    while len(padded_left) < len(right_lines):
        padded_left.append("")
    while len(right_lines) < len(padded_left):
        right_lines.append("")

    gap = "  "

    console.print()
    for ll, rl in zip(padded_left, right_lines):
        pad_needed = left_width - _visible_len(ll)
        line = ll + " " * pad_needed + gap + rl
        sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _write_artifacts(output_dir: Path, result: GenerationResult):
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "total_time_seconds": result.total_time_seconds,
        "artifacts": [],
    }

    for artifact in result.artifacts:
        if not artifact.success:
            manifest["artifacts"].append(
                {
                    "type": artifact.artifact_type,
                    "status": "failed",
                    "error": artifact.error,
                }
            )
            continue

        file_path = output_dir / artifact.file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(artifact.content)

        extra_files_list = []
        for extra_path, extra_content in artifact.extra_files.items():
            ep = output_dir / extra_path
            ep.parent.mkdir(parents=True, exist_ok=True)
            ep.write_text(extra_content)
            extra_files_list.append(str(extra_path))

        manifest["artifacts"].append(
            {
                "type": artifact.artifact_type,
                "status": "success",
                "file": str(artifact.file_path),
                "format": artifact.format,
                "model": artifact.model_used,
                **({"extra_files": extra_files_list} if extra_files_list else {}),
            }
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))


def _create_git_branch(project_path: Path, output_dir: Path, branch_name: str):
    try:
        import git

        try:
            repo = git.Repo(project_path)
        except git.InvalidGitRepositoryError:
            console.print("[dim]Not a git repo — skipping branch creation.[/]")
            return

        try:
            repo.head.commit
        except ValueError:
            console.print(
                "[dim]No commits yet — skipping branch creation. "
                "Run 'git add . && git commit' first.[/]"
            )
            return

        current = repo.active_branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()

        repo.index.add([str(p) for p in output_dir.rglob("*") if p.is_file()])
        repo.index.commit(
            f"feat: add DevDex launch kit\n\nGenerated by DevDex v{__version__}"
        )

        current.checkout()

        console.print(f"\n[bold green]Created branch:[/] {branch_name}")
        console.print(f"[dim]Run: git checkout {branch_name}[/]")

    except Exception as e:
        console.print(f"[yellow]Git branch creation failed: {e}[/]")


def _print_generation_summary(result: GenerationResult, json_output: bool):
    if json_output:
        manifest_path = Path(result.output_dir) / "manifest.json"
        if manifest_path.exists():
            stdout_console.print(manifest_path.read_text())
        return

    console.print()
    panel_lines = []
    for a in result.artifacts:
        if a.success:
            panel_lines.append(f"[green]  {a.artifact_type}: {a.file_path}[/]")
        else:
            panel_lines.append(f"[red]  {a.artifact_type}: FAILED — {a.error[:50]}[/]")

    panel_lines.append(f"\n[dim]  Output: {result.output_dir}[/]")
    panel_lines.append(f"[dim]  Time: {result.total_time_seconds}s[/]")

    if result.branch_name:
        panel_lines.append(f"[dim]  Branch: {result.branch_name}[/]")

    theme = get_session_theme()
    console.print(
        Panel(
            "\n".join(panel_lines),
            title=f"[{theme['accent']}]Launch Kit Generated[/]",
            border_style=theme["border"],
        )
    )


def _render_feedback_step_bar(
    current_idx: int, total: int, artifact_names: list[str], theme: dict
) -> None:
    border = theme["border"]
    term_width = console.width or 80
    indent = "  "

    line = Text(indent)
    col = len(indent)

    for i, name in enumerate(artifact_names):
        label = name.replace("_", " ").title()

        chunk = Text()
        if i > 0:
            chunk.append(" · ", style="dim")
        if i < current_idx:
            chunk.append("✓ ", style=border)
            chunk.append(label, style=border)
        elif i == current_idx:
            chunk.append("■ ", style=f"bold {border}")
            chunk.append(label, style=f"bold {border}")
        else:
            chunk.append("□ ", style="dim")
            chunk.append(label, style="dim")

        chunk_len = len(chunk.plain)

        if col + chunk_len > term_width and col > len(indent):
            console.print(line)
            line = Text(indent)
            col = len(indent)
            if i > 0:
                chunk = Text()
                if i < current_idx:
                    chunk.append("✓ ", style=border)
                    chunk.append(label, style=border)
                elif i == current_idx:
                    chunk.append("■ ", style=f"bold {border}")
                    chunk.append(label, style=f"bold {border}")
                else:
                    chunk.append("□ ", style="dim")
                    chunk.append(label, style="dim")
                chunk_len = len(chunk.plain)

        line.append_text(chunk)
        col += chunk_len

    console.print(line)


def _submit_feedback(
    ratings: list[dict], output_dir: Path, cfg: DevDexConfig, run_id: str = ""
) -> None:
    import io as _io
    import warnings

    from devdex.functions.feedback_loop import save_feedback_to_history

    if not ratings:
        return

    if cfg.wandb_api_key:
        import threading

        _wandb_api_key = cfg.wandb_api_key

        def _wandb_log():
            try:
                import io as _thread_io
                import logging as _logging
                import os as _os

                _os.environ["WANDB_SILENT"] = "true"
                import wandb

                _old_stdout, _old_stderr = sys.stdout, sys.stderr
                sys.stdout = sys.stderr = _thread_io.StringIO()
                _logging.getLogger("wandb").setLevel(_logging.CRITICAL)
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        wandb.login(key=_wandb_api_key)
                        run = wandb.init(
                            project="devdex-feedback",
                            settings=wandb.Settings(
                                silent=True, console="off", quiet=True,
                                _disable_stats=True, init_timeout=5,
                            ),
                        )
                        for r in ratings:
                            wandb.log(r)
                        run.finish(quiet=True)
                finally:
                    sys.stdout, sys.stderr = _old_stdout, _old_stderr
            except Exception:
                pass

        t = threading.Thread(target=_wandb_log, daemon=True)
        t.start()
        with console.status("[bold cyan]Submitting your feedback...[/]"):
            t.join(timeout=8)

        if not t.is_alive():
            console.print("[green]Thank you! Your feedback helps improve DevDex for everyone.[/]")
        else:
            console.print("[green]Feedback saved locally. Sync will complete in background.[/]")

    if cfg.telemetry_enabled and cfg.telemetry_url:
        try:
            from devdex.functions.feedback_loop import send_central_telemetry

            send_central_telemetry(ratings, cfg.telemetry_url, __version__, run_id=run_id)
        except Exception:
            pass

    feedback_path = output_dir / "feedback.json"
    feedback_path.write_text(json.dumps(ratings, indent=2))
    console.print(f"[dim]Feedback saved to {feedback_path}[/]")

    save_feedback_to_history(ratings)

    if cfg.supabase_url and cfg.supabase_key:
        try:
            from devdex.functions.feedback_loop import store_feedback_to_vector_store

            store_feedback_to_vector_store(
                ratings,
                supabase_url=cfg.supabase_url,
                supabase_key=cfg.supabase_key,
                mistral_api_key=cfg.mistral_embed_api_key,
                run_id=run_id,
            )
        except Exception:
            pass


def _collect_feedback(output_dir: Path, cfg: DevDexConfig, run_id: str = "") -> None:
    import questionary

    from devdex.functions.feedback_loop import classify_feedback_to_artifacts

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())
    successful = [a for a in manifest.get("artifacts", []) if a["status"] == "success"]
    if not successful:
        return

    want = questionary.confirm(
        "Would you like to rate the generated artifacts?",
        default=False,
    ).ask()
    if not want:
        return

    theme = get_session_theme()
    artifact_names = [a["type"] for a in successful]
    ratings: list[dict] = []

    try:
        for idx, a in enumerate(successful):
            console.print()
            _render_feedback_step_bar(idx, len(successful), artifact_names, theme)
            console.print()
            console.print(f"  [bold]{a['type'].replace('_', ' ').title()}[/] [dim]({a['file']})[/]")

            while True:
                raw = questionary.text(
                    "  Rate (1-5, Enter to skip):",
                ).ask()
                if raw is None:
                    raise KeyboardInterrupt()
                raw = raw.strip()
                if raw == "":
                    break
                if raw in ("1", "2", "3", "4", "5"):
                    ratings.append({
                        "artifact_type": a["type"],
                        "user_rating": int(raw),
                        "had_edits": False,
                        "edit_description": "",
                    })
                    break
                console.print("  [dim]Please enter 1-5 or press Enter to skip.[/]")

        console.print()
        _render_feedback_step_bar(len(successful), len(successful), artifact_names, theme)
        console.print()

        if not ratings:
            console.print("[dim]No ratings provided.[/]")
            return

        had_changes = questionary.confirm(
            "Is there anything you had to change?",
            default=False,
        ).ask()
        if had_changes is None:
            raise KeyboardInterrupt()

        if had_changes:
            edit_text = questionary.text("What did you change?").ask()
            if edit_text is None:
                raise KeyboardInterrupt()

            if edit_text.strip():
                rated_types = [r["artifact_type"] for r in ratings]
                matched = classify_feedback_to_artifacts(edit_text, rated_types)

                for r in ratings:
                    if r["artifact_type"] in matched:
                        r["had_edits"] = True
                        r["edit_description"] = edit_text.strip()

        _submit_feedback(ratings, output_dir, cfg, run_id=run_id)

    except KeyboardInterrupt:
        if ratings:
            console.print("\n[yellow]Interrupted — submitting partial feedback.[/]")
            _submit_feedback(ratings, output_dir, cfg, run_id=run_id)
        else:
            console.print("\n[yellow]Feedback skipped.[/]")


@app.command(hidden=True)
def logo(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Logo variant: pokeball, greatball, ultraball, masterball"),
    ] = None,
):
    term_width = console.width or 100

    def _print_logo_and_footer(ball_name: str) -> None:
        art = _get_logo_for_width(ball_name, term_width)
        if art is None:
            console.print(f"[bold yellow]DevDéx[/] [dim]v{__version__}[/]")
            return
        console.print(art)
        footer_mode = _get_footer_for_width(term_width)
        if footer_mode == "panel":
            console.print(Panel(LOGO_FOOTER.format(ver=__version__), border_style="dim", expand=False))
        elif footer_mode == "line":
            console.print(f"[bold yellow]DevDéx[/] [dim]v{__version__}[/]")

    if name and name in LOGOS:
        _print_logo_and_footer(name)
    elif name == "all":
        for n in LOGOS:
            console.print(f"[dim]--- {n} ---[/]")
            _print_logo_and_footer(n)
    else:
        _show_logo()
        _print_logo_and_footer(_session_logo)


config_app = typer.Typer(help="Manage DevDex configuration.")
app.add_typer(config_app, name="config")


@config_app.command("set")
def config_set(
    key: Annotated[
        str,
        typer.Argument(help="Config key (api_key, base_url, provider, wandb_api_key)"),
    ],
    value: Annotated[str, typer.Argument(help="Config value")],
):
    cfg = DevDexConfig.load()
    valid_keys = {
        "api_key", "base_url", "provider", "wandb_api_key", "nvidia_api_key",
        "supabase_url", "supabase_key", "mistral_embed_api_key", "finetuned_model_id",
    }
    if key not in valid_keys:
        console.print(f"[red]Unknown key: {key}[/]")
        console.print(f"[dim]Valid keys: {', '.join(sorted(valid_keys))}[/]")
        raise typer.Exit(1)

    setattr(cfg, key, value)
    cfg.save()
    console.print(f"[green]Saved {key}[/]")


@config_app.command("show")
def config_show():
    cfg = DevDexConfig.load()
    table = Table(title="DevDex Config", show_header=True, border_style="cyan")
    table.add_column("Key")
    table.add_column("Value")

    key_display = f"{cfg.api_key[:12]}..." if cfg.api_key else "[red]Not set[/]"
    wandb_display = (
        f"{cfg.wandb_api_key[:10]}..." if cfg.wandb_api_key else "[dim]Not set[/]"
    )

    supabase_display = (
        f"{cfg.supabase_url[:30]}..." if cfg.supabase_url else "[dim]Not set[/]"
    )
    finetuned_display = cfg.finetuned_model_id or "[dim]Not set[/]"

    table.add_row("provider", cfg.provider or "nvidia (default)")
    table.add_row("base_url", cfg.base_url or "[dim]auto[/]")
    table.add_row("api_key", key_display)
    table.add_row("wandb_api_key", wandb_display)
    table.add_row("supabase_url", supabase_display)
    table.add_row("supabase_key", f"{cfg.supabase_key[:10]}..." if cfg.supabase_key else "[dim]Not set[/]")
    table.add_row("finetuned_model_id", finetuned_display)
    console.print(table)


@app.command()
def review(
    artifact: Annotated[
        Optional[str], typer.Argument(help="Artifact path to open")
    ] = None,
    output: Annotated[
        Optional[Path], typer.Option("--output", "-o", help="Output directory")
    ] = None,
):
    output_dir = output or Path("devdex-output")

    if artifact:
        target = output_dir / artifact
        if not target.exists():
            console.print(f"[red]File not found: {target}[/]")
            raise typer.Exit(1)
        subprocess.run(["open", str(target)])
        return

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        console.print("[red]No manifest found. Run 'devdex scan' first.[/]")
        raise typer.Exit(1)

    manifest = json.loads(manifest_path.read_text())
    console.print("\n[bold cyan]Generated Artifacts:[/]\n")
    for a in manifest.get("artifacts", []):
        if a["status"] == "success":
            console.print(f"  [green]{a['type']}[/]: {a['file']}")
        else:
            console.print(f"  [red]{a['type']}[/]: FAILED")


@app.command(hidden=True)
def feedback(
    output: Annotated[
        Optional[Path], typer.Option("--output", "-o", help="Output directory")
    ] = None,
    no_telemetry: Annotated[
        bool, typer.Option("--no-telemetry", help="Disable anonymous feedback telemetry")
    ] = False,
):
    _show_logo()
    term_width = console.width or 100
    art = _get_logo_for_width(_session_logo, term_width)
    if art:
        console.print(art)
        footer_mode = _get_footer_for_width(term_width)
        if footer_mode == "panel":
            console.print(Panel(LOGO_FOOTER.format(ver=__version__), border_style="dim", expand=False))
        elif footer_mode == "line":
            console.print(f"[bold yellow]DevDéx[/] [dim]v{__version__}[/]")
    output_dir = output or Path("devdex-output")
    cfg = DevDexConfig.load()
    if no_telemetry:
        cfg.telemetry_enabled = False
    try:
        _collect_feedback(output_dir, cfg)
    except KeyboardInterrupt:
        console.print("\n[yellow]Feedback skipped.[/]")


@app.command(hidden=True)
def finetune(
    base_model: Annotated[
        str,
        typer.Option("--base-model", "-m", help="Base model to fine-tune"),
    ] = "",
    mlx: Annotated[
        bool, typer.Option("--mlx", help="Use MLX LoRA fine-tuning (Apple Silicon)")
    ] = False,
    unsloth: Annotated[
        bool, typer.Option("--unsloth", help="Use Unsloth fine-tuning (2-5x faster, recommended)")
    ] = False,
    local: Annotated[
        bool, typer.Option("--local", help="Use local TRL fine-tuning (requires CUDA/MPS + PyTorch)")
    ] = False,
    iters: Annotated[
        int, typer.Option("--iters", help="Training iterations (MLX mode)")
    ] = 100,
    min_rating: Annotated[
        int, typer.Option("--min-rating", help="Minimum rating for training data")
    ] = 4,
    min_samples: Annotated[
        int, typer.Option("--min-samples", help="Minimum training samples required")
    ] = 50,
    dev: Annotated[
        bool, typer.Option("--dev", help="Dev mode: allow min_samples=1 for testing the flow")
    ] = False,
):
    if dev:
        min_samples = 1
        console.print("[yellow]Dev mode: min_samples set to 1[/]")

    cfg = DevDexConfig.load()

    if not cfg.supabase_url or not cfg.supabase_key:
        console.print("[red]Supabase not configured. Set DEVDEX_SUPABASE_URL and DEVDEX_SUPABASE_KEY.[/]")
        raise typer.Exit(1)

    import os
    mistral_key = os.environ.get("MISTRAL_API_KEY", "") or cfg.mistral_embed_api_key or cfg.api_key

    from devdex.functions.finetune_pipeline import export_training_data

    with console.status("[bold cyan]Exporting training data from Supabase...[/]"):
        try:
            data_path, val_path = export_training_data(
                cfg.supabase_url, cfg.supabase_key, mistral_key or "",
                min_rating=min_rating, min_samples=min_samples,
            )
        except ValueError as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(1)

    train_count = sum(1 for _ in open(data_path))
    val_count = sum(1 for _ in open(val_path)) if val_path else 0
    console.print(f"[green]Training data: {train_count} samples → {data_path}[/]")
    if val_path:
        console.print(f"[green]Validation data: {val_count} samples → {val_path}[/]")
    console.print(f"[dim]Min rating filter: {min_rating}+[/]")

    if mlx:
        mlx_model = base_model or "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
        console.print(f"\n[bold cyan]{'='*50}[/]")
        console.print(f"[bold cyan]  MLX LoRA Fine-Tuning[/]")
        console.print(f"[bold cyan]{'='*50}[/]")
        console.print(f"  [dim]Base model:[/]  {mlx_model}")
        console.print(f"  [dim]Iterations:[/]  {iters}")
        console.print(f"  [dim]Batch size:[/]  1")
        console.print(f"  [dim]LoRA layers:[/] 4")
        console.print(f"  [dim]Train set:[/]   {train_count} samples")
        console.print(f"  [dim]Valid set:[/]   {val_count} samples")
        console.print(f"[bold cyan]{'='*50}[/]\n")

        try:
            from devdex.functions.finetune_pipeline import run_mlx_finetune
        except ImportError:
            console.print(
                "[red]MLX fine-tuning requires mlx-lm.[/]\n"
                '[dim]Install with: uv pip install "devdex[pipeline-mlx]"[/]'
            )
            raise typer.Exit(1)

        try:
            adapter_path = run_mlx_finetune(
                data_path,
                validation_data_path=val_path,
                base_model=mlx_model,
                iters=iters,
                wandb_api_key=cfg.wandb_api_key or "",
            )
        except Exception as e:
            console.print(f"[red]MLX fine-tuning failed: {e}[/]")
            raise typer.Exit(1)

        console.print(f"\n[bold green]Fine-tuning complete![/]")
        console.print(f"[green]Adapters saved to: {adapter_path}[/]")

        cfg.finetuned_model_id = f"mlx:{mlx_model}:{adapter_path}"
        cfg.save()
        console.print(f"[green]Saved adapter path to config[/]")

        if cfg.wandb_api_key:
            from devdex.functions.finetune_pipeline import register_model_version
            with console.status("[bold cyan]Registering model in W&B...[/]"):
                register_model_version(
                    model_id=f"mlx-lora:{adapter_path}",
                    job_id="local-mlx",
                    wandb_api_key=cfg.wandb_api_key,
                    base_model=mlx_model,
                )
            console.print("[green]Model registered in W&B model registry[/]")

        console.print(f"\n[bold cyan]Testing fine-tuned model...[/]")
        try:
            from devdex.functions.finetune_pipeline import mlx_generate
            test_output = mlx_generate(
                base_model=mlx_model,
                adapter_path=adapter_path,
                system_prompt="You are a legal expert that generates privacy policies for apps.",
                user_prompt="Generate a brief privacy policy summary for a fitness tracking app.",
                max_tokens=256,
            )
            console.print(f"\n[dim]Sample generation with fine-tuned model:[/]")
            console.print(test_output[:500])
        except Exception as e:
            console.print(f"[yellow]Test generation failed (non-critical): {e}[/]")

        return

    if unsloth:
        unsloth_model = base_model or "unsloth/mistral-7b-instruct-v0.3-bnb-4bit"
        console.print(f"\n[bold cyan]{'='*50}[/]")
        console.print(f"[bold cyan]  Unsloth LoRA Fine-Tuning[/]")
        console.print(f"[bold cyan]{'='*50}[/]")
        console.print(f"  [dim]Base model:[/]  {unsloth_model}")
        console.print(f"  [dim]Max steps:[/]   {iters}")
        console.print(f"  [dim]Train set:[/]   {train_count} samples")
        console.print(f"  [dim]Valid set:[/]   {val_count} samples")
        console.print(f"[bold cyan]{'='*50}[/]\n")

        try:
            from devdex.functions.finetune_pipeline import run_unsloth_finetune
        except ImportError:
            console.print(
                "[red]Unsloth fine-tuning requires unsloth.[/]\n"
                '[dim]Install with: uv pip install "devdex[pipeline-unsloth]"[/]'
            )
            raise typer.Exit(1)

        try:
            output_path = run_unsloth_finetune(
                data_path,
                base_model=unsloth_model,
                max_steps=iters,
                wandb_api_key=cfg.wandb_api_key or "",
            )
        except Exception as e:
            console.print(f"[red]Unsloth fine-tuning failed: {e}[/]")
            raise typer.Exit(1)

        console.print(f"\n[bold green]Fine-tuning complete![/]")
        console.print(f"[green]Model saved to: {output_path}[/]")

        cfg.finetuned_model_id = f"unsloth:{output_path}"
        cfg.save()
        console.print(f"[green]Saved model path to config[/]")

        if cfg.wandb_api_key:
            from devdex.functions.finetune_pipeline import register_model_version
            with console.status("[bold cyan]Registering model in W&B...[/]"):
                register_model_version(
                    model_id=f"unsloth-lora:{output_path}",
                    job_id="local-unsloth",
                    wandb_api_key=cfg.wandb_api_key,
                    base_model=unsloth_model,
                    training_samples=train_count,
                )
            console.print("[green]Model registered in W&B model registry[/]")
        return

    if local:
        from devdex.functions.finetune_pipeline import run_local_finetune
        trl_model = base_model or "mistralai/Ministral-8B-Instruct-2410"
        with console.status("[bold cyan]Running local fine-tuning (this may take a while)...[/]"):
            try:
                output_dir = run_local_finetune(data_path, base_model=trl_model)
                console.print(f"[green]Fine-tuned model saved to {output_dir}[/]")
            except ImportError:
                console.print(
                    "[red]Local fine-tuning requires: trl, peft, transformers, datasets, torch[/]\n"
                    "[dim]Install with: uv pip install 'devdex[pipeline-local]'[/]"
                )
                raise typer.Exit(1)
        return

    api_model = base_model or "open-mistral-nemo"

    if not mistral_key:
        console.print(
            "[red]No Mistral API key found.[/]\n"
            "[dim]Fine-tuning requires a key from console.mistral.ai (not NVIDIA NIM).[/]\n"
            "[dim]Set it via: export MISTRAL_API_KEY=your-key[/]"
        )
        raise typer.Exit(1)

    if mistral_key.startswith("nvapi-"):
        console.print(
            "[yellow]Warning: Your MISTRAL_API_KEY looks like an NVIDIA NIM key (nvapi-...).[/]\n"
            "[yellow]Fine-tuning requires a Mistral Platform key from console.mistral.ai.[/]"
        )

    from devdex.functions.finetune_pipeline import (
        poll_job_status,
        register_model_version,
        run_finetune,
    )

    with console.status("[bold cyan]Uploading data and creating fine-tuning job...[/]"):
        try:
            result = run_finetune(
                data_path,
                validation_data_path=val_path,
                base_model=api_model,
                mistral_api_key=mistral_key,
                wandb_api_key=cfg.wandb_api_key or "",
            )
        except Exception as e:
            console.print(f"[red]Fine-tuning job creation failed: {e}[/]")
            raise typer.Exit(1)

    console.print(f"[green]Fine-tuning job created: {result['job_id']}[/]")

    with console.status("[bold cyan]Waiting for fine-tuning to complete...[/]"):
        try:
            final = poll_job_status(mistral_key, result["job_id"])
        except (TimeoutError, RuntimeError) as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(1)

    model_id = final["fine_tuned_model"]
    console.print(f"[bold green]Fine-tuning complete! Model: {model_id}[/]")

    cfg.finetuned_model_id = model_id
    cfg.save()
    console.print(f"[green]Saved finetuned_model_id to config[/]")

    if cfg.wandb_api_key:
        with console.status("[bold cyan]Registering model in W&B...[/]"):
            register_model_version(
                model_id, result["job_id"],
                wandb_api_key=cfg.wandb_api_key,
                base_model=api_model,
            )
        console.print("[green]Model registered in W&B model registry[/]")


def _version_callback(value: bool):
    if value:
        print(f"DevDex v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=_version_callback, is_eager=True),
    ] = None,
):
    pass
