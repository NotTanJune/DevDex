from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

console = Console(stderr=True)


@dataclass
class ChecklistItem:
    text: str
    is_gotcha: bool = False
    sub_items: list[str] = field(default_factory=list)
    code_blocks: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ChecklistSection:
    title: str
    level: int = 2
    difficulty: str = ""
    items: list[ChecklistItem] = field(default_factory=list)
    subsections: list[ChecklistSection] = field(default_factory=list)

_GOTCHA_RE = re.compile(r"\*\*Gotcha:?\*\*", re.IGNORECASE)
_DIFFICULTY_RE = re.compile(
    r"\(?(easy|medium|hard|difficult|simple|advanced)\)?",
    re.IGNORECASE,
)


def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(\S.+?\S)_', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


def _parse_checklist(content: str) -> list[ChecklistSection]:
    sections: list[ChecklistSection] = []
    current_h2: ChecklistSection | None = None
    current_section: ChecklistSection | None = None
    current_item: ChecklistItem | None = None

    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []

    for line in content.splitlines():
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line.strip().removeprefix("```").strip()
                code_lines = []
            else:
                in_code_block = False
                if current_item is not None:
                    current_item.code_blocks.append(
                        (code_lang or "text", "\n".join(code_lines))
                    )
                code_lang = ""
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            if current_h2 is not None:
                _finalize_section(current_h2, current_section, sections)
            raw_title = h2_match.group(1).strip()
            difficulty = _extract_difficulty(raw_title)
            title = _strip_markdown(raw_title)
            current_h2 = ChecklistSection(title=title, level=2, difficulty=difficulty)
            current_section = current_h2
            current_item = None
            continue

        h3_match = re.match(r"^###\s+(.+)$", line)
        if h3_match:
            raw_title = h3_match.group(1).strip()
            difficulty = _extract_difficulty(raw_title)
            title = _strip_markdown(raw_title)
            sub = ChecklistSection(title=title, level=3, difficulty=difficulty)
            if current_h2 is not None:
                current_h2.subsections.append(sub)
            current_section = sub
            current_item = None
            continue

        item_match = re.match(r"^[-*]\s+\[[ x]\]\s+(.+)$", line)
        if item_match and current_section is not None:
            raw_text = item_match.group(1).strip()
            is_gotcha = bool(_GOTCHA_RE.search(raw_text))
            text = _strip_markdown(raw_text)
            current_item = ChecklistItem(text=text, is_gotcha=is_gotcha)
            current_section.items.append(current_item)
            continue

        sub_match = re.match(r"^\s{2,}[-*]\s+(.+)$", line)
        if sub_match and current_item is not None:
            current_item.sub_items.append(_strip_markdown(sub_match.group(1).strip()))
            continue

    if current_h2 is not None:
        _finalize_section(current_h2, current_section, sections)

    return sections


def _finalize_section(
    h2: ChecklistSection,
    current_section: ChecklistSection | None,
    sections: list[ChecklistSection],
) -> None:
    has_items = bool(h2.items) or any(s.items for s in h2.subsections)
    if has_items:
        sections.append(h2)


def _extract_difficulty(title: str) -> str:
    m = _DIFFICULTY_RE.search(title)
    if m:
        raw = m.group(1).lower()
        mapping = {"simple": "easy", "difficult": "hard", "advanced": "hard"}
        return mapping.get(raw, raw)
    return ""


_DIFFICULTY_STYLES = {
    "easy": ("green", "Easy"),
    "medium": ("yellow", "Medium"),
    "hard": ("red", "Hard"),
}


def _render_section_header(
    section: ChecklistSection, idx: int, total: int, theme: dict
) -> None:
    title_text = Text()
    title_text.append(f"[{idx + 1}/{total}] ", style="bold")
    title_text.append(section.title, style="bold")

    if section.difficulty and section.difficulty in _DIFFICULTY_STYLES:
        color, label = _DIFFICULTY_STYLES[section.difficulty]
        title_text.append(f"  [{label}]", style=f"bold {color}")

    console.print(Panel(
        title_text,
        border_style=theme["border"],
        padding=(0, 1),
    ))


def _render_item_context(item: ChecklistItem, theme: dict) -> None:
    for sub in item.sub_items:
        console.print(f"    [dim]- {sub}[/]")

    for lang, code in item.code_blocks:
        console.print()
        console.print(Syntax(code, lang, theme="monokai", padding=1))
        console.print()


def _render_gotcha_item(item: ChecklistItem) -> None:
    console.print(Panel(
        f"[bold]{item.text}[/]",
        border_style="yellow",
        title="[yellow bold]Gotcha[/]",
        padding=(0, 1),
    ))


def _count_items(sections: list[ChecklistSection]) -> int:
    total = 0
    for s in sections:
        total += len(s.items)
        for sub in s.subsections:
            total += len(sub.items)
    return total


CHECKLIST_HISTORY_PATH = Path.home() / ".devdex" / "checklist_history.json"


def _save_checklist_progress(
    project_path: str,
    checklist_content: str,
    item_states: dict[str, bool],
    theme_name: str = "",
) -> None:
    all_data: dict = {}
    if CHECKLIST_HISTORY_PATH.exists():
        try:
            all_data = json.loads(CHECKLIST_HISTORY_PATH.read_text())
        except Exception:
            all_data = {}

    all_data[project_path] = {
        "checklist_content": checklist_content,
        "items": item_states,
        "theme_name": theme_name,
        "timestamp": datetime.now().isoformat(),
    }

    CHECKLIST_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKLIST_HISTORY_PATH.write_text(json.dumps(all_data, indent=2))


def _load_checklist_progress(
    project_path: str,
) -> tuple[dict[str, bool], str, str] | None:
    if not CHECKLIST_HISTORY_PATH.exists():
        return None
    try:
        all_data = json.loads(CHECKLIST_HISTORY_PATH.read_text())
    except Exception:
        return None

    entry = all_data.get(project_path)
    if not entry:
        return None

    items = entry.get("items", {})
    content = entry.get("checklist_content", "")
    if not items or not content:
        return None

    theme_name = entry.get("theme_name", "")
    return items, content, theme_name


def _clear_checklist_progress(project_path: str) -> None:
    if not CHECKLIST_HISTORY_PATH.exists():
        return
    try:
        all_data = json.loads(CHECKLIST_HISTORY_PATH.read_text())
    except Exception:
        return

    if project_path in all_data:
        del all_data[project_path]
        if all_data:
            CHECKLIST_HISTORY_PATH.write_text(json.dumps(all_data, indent=2))
        else:
            CHECKLIST_HISTORY_PATH.unlink(missing_ok=True)


def run_deployment_guide(
    checklist_content: str,
    theme: dict,
    output_dir: Path | None = None,
    project_path: str | None = None,
    skip_resume_check: bool = False,
    initial_states: dict[str, bool] | None = None,
    theme_name: str = "",
) -> None:
    from questionary import Style

    saved_states: dict[str, bool] | None = None
    resume_mode = False

    if initial_states is not None:
        saved_states = initial_states
        resume_mode = True
    elif project_path and not skip_resume_check:
        loaded = _load_checklist_progress(project_path)
        if loaded:
            saved_states, saved_content, loaded_theme_name = loaded
            completed_count = sum(1 for v in saved_states.values() if v)
            resume = questionary.confirm(
                f"Found saved progress ({completed_count} items completed). Resume?",
                default=True,
            ).ask()
            if resume is None:
                return
            if resume:
                resume_mode = True
                checklist_content = saved_content
                if not theme_name:
                    theme_name = loaded_theme_name
            else:
                saved_states = None
                _clear_checklist_progress(project_path)

    sections = _parse_checklist(checklist_content)
    if not sections:
        console.print("[yellow]Could not parse checklist sections.[/]")
        return

    ansi_map = {"red": "ansired", "blue": "ansiblue", "yellow": "ansiyellow", "magenta": "ansimagenta"}
    ansi = ansi_map.get(theme["border"], theme["border"])
    style = Style([
        ("qmark", f"fg:{ansi} bold"),
        ("question", "bold"),
        ("pointer", f"fg:{ansi} bold"),
        ("highlighted", f"bg:{ansi} fg:ansiwhite bold"),
        ("answer", f"fg:{ansi} bold"),
    ])

    total_items = _count_items(sections)
    completed_items = 0
    skipped_items = 0
    results: list[dict] = []
    item_states: dict[str, bool] = {}

    console.print(f"\n[{theme['accent']}]--- Deployment Walkthrough ---[/]")
    if resume_mode:
        resumed_count = sum(1 for v in saved_states.values() if v)
        console.print(f"[dim]{len(sections)} sections, {total_items} items total. Resuming ({resumed_count} already completed). Ctrl+C to pause.[/]\n")
    else:
        console.print(f"[dim]{len(sections)} sections, {total_items} items total. Ctrl+C to pause.[/]\n")

    def _walk_items(
        items: list[ChecklistItem],
    ) -> tuple[int, int]:
        nonlocal completed_items, skipped_items
        done = 0
        skipped = 0

        for item in items:
            if resume_mode and saved_states and saved_states.get(item.text) is True:
                console.print(f"  [dim green]  {item.text}[/]")
                completed_items += 1
                done += 1
                item_states[item.text] = True
                continue

            if item.is_gotcha:
                _render_gotcha_item(item)
            else:
                console.print()

            _render_item_context(item, theme)

            answer = questionary.confirm(
                f"  {item.text}",
                default=False,
                style=style,
            ).ask()

            if answer is None:
                raise KeyboardInterrupt()

            if answer:
                completed_items += 1
                done += 1
                item_states[item.text] = True
            else:
                skipped_items += 1
                skipped += 1
                item_states[item.text] = False

        return done, skipped

    interrupted = False
    try:
        for sec_idx, section in enumerate(sections):
            _render_section_header(section, sec_idx, len(sections), theme)

            section_done, section_skipped = _walk_items(section.items)

            for sub in section.subsections:
                if sub.items:
                    console.print()
                    header = Text()
                    header.append(f"    {sub.title}", style=f"bold {theme['border']}")
                    if sub.difficulty and sub.difficulty in _DIFFICULTY_STYLES:
                        color, label = _DIFFICULTY_STYLES[sub.difficulty]
                        header.append(f"  [{label}]", style=f"bold {color}")
                    console.print(header)

                    sub_done, sub_skipped = _walk_items(sub.items)
                    section_done += sub_done
                    section_skipped += sub_skipped

                    sub_total = len(sub.items)
                    sub_pct = (sub_done / sub_total * 100) if sub_total else 0
                    console.print(f"    [dim]{sub_done}/{sub_total} done ({sub_pct:.0f}%)[/]")

            total_section = len(section.items) + sum(
                len(s.items) for s in section.subsections
            )
            results.append({
                "section": section.title,
                "total": total_section,
                "completed": section_done,
                "skipped": section_skipped,
            })

            pct = (section_done / total_section * 100) if total_section else 0
            console.print(
                f"  [dim]{section_done}/{total_section} done ({pct:.0f}%)[/]"
            )

            section_all_auto = (
                resume_mode
                and section_skipped == 0
                and section_done == total_section
                and all(
                    saved_states.get(item.text) is True
                    for item in section.items
                )
                and all(
                    saved_states.get(item.text) is True
                    for sub in section.subsections
                    for item in sub.items
                )
            )
            if sec_idx < len(sections) - 1 and not section_all_auto:
                cont = questionary.confirm(
                    "Continue to next section?",
                    default=True,
                    style=style,
                ).ask()
                if cont is None:
                    raise KeyboardInterrupt()
                if not cont:
                    if project_path:
                        _save_checklist_progress(project_path, checklist_content, item_states, theme_name=theme_name)
                        console.print("\n[cyan]Progress saved. Run 'devdex scan' again to resume.[/]")
                    break

    except KeyboardInterrupt:
        interrupted = True
        console.print("\n[yellow]Walkthrough paused.[/]")
        if project_path:
            _save_checklist_progress(project_path, checklist_content, item_states, theme_name=theme_name)
            console.print("[cyan]Progress saved. Run 'devdex scan' again to resume.[/]")

    console.print()
    summary_lines = []
    for r in results:
        status = (
            "[green]complete[/]"
            if r["completed"] == r["total"]
            else f"[yellow]{r['completed']}/{r['total']}[/]"
        )
        summary_lines.append(f"  {r['section']}: {status}")

    summary_lines.append(
        f"\n  [bold]Total: {completed_items}/{total_items} completed, "
        f"{skipped_items} skipped[/]"
    )

    console.print(Panel(
        "\n".join(summary_lines),
        title=f"[{theme['accent']}]Deployment Progress[/]",
        border_style=theme["border"],
    ))

    if output_dir:
        progress_path = output_dir / "deployment-progress.json"
        progress_path.write_text(json.dumps({
            "sections": results,
            "total_items": total_items,
            "completed": completed_items,
            "skipped": skipped_items,
        }, indent=2))
        console.print(f"[dim]Progress saved to {progress_path}[/]")

    all_addressed = (completed_items + skipped_items) == total_items
    if not interrupted and all_addressed and project_path:
        _clear_checklist_progress(project_path)
        console.print("[dim]Checklist complete — saved progress cleared.[/]")
    elif not interrupted and not all_addressed and project_path:
        _save_checklist_progress(project_path, checklist_content, item_states, theme_name=theme_name)
