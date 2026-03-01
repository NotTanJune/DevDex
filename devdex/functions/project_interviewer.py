from __future__ import annotations

from collections import OrderedDict

import questionary
import questionary.prompts.common as _qcommon
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

_orig_create_layout = _qcommon.create_inquirer_layout
_orig_get_choice_tokens = _qcommon.InquirerControl._get_choice_tokens


def _get_choice_tokens_fixed(self):
    tokens = _orig_get_choice_tokens(self)

    result = []
    current_is_pointed = False
    for style, text in tokens:
        if style == "[SetCursorPosition]":
            continue
        if style == "class:pointer":
            current_is_pointed = True
        elif style == "class:text" and text.startswith("   "):
            current_is_pointed = False
        if style == "class:selected":
            style = "class:highlighted" if current_is_pointed else "class:text"
        result.append((style, text))
    return result


_qcommon.InquirerControl._get_choice_tokens = _get_choice_tokens_fixed


def _create_layout_focused(ic, get_prompt_tokens, **kwargs):
    from prompt_toolkit.filters import Always
    from prompt_toolkit.layout.controls import BufferControl

    ic.show_cursor = False

    layout = _orig_create_layout(ic, get_prompt_tokens, **kwargs)

    for win in layout.find_all_windows():
        if isinstance(win.content, _qcommon.InquirerControl):
            win.always_hide_cursor = Always()

    for win in layout.find_all_windows():
        if (
            isinstance(win.content, BufferControl)
            and win.content.buffer.name == "DEFAULT_BUFFER"
        ):
            layout.current_window = win
            break

    return layout


_qcommon.create_inquirer_layout = _create_layout_focused

from devdex.models import (
    AgeRating,
    DeploymentTarget,
    DevDexPipelineState,
    LandingPageChoice,
    MonetizationModel,
    ProjectUnderstanding,
)

console = Console(stderr=True)


_ANSI_COLOR_MAP = {
    "red": "ansired",
    "blue": "ansiblue",
    "yellow": "ansiyellow",
    "magenta": "ansimagenta",
}


def _make_style(border_color: str) -> Style:
    ansi = _ANSI_COLOR_MAP.get(border_color, border_color)
    return Style(
        [
            ("qmark", f"fg:{ansi} bold"),
            ("question", "bold"),
            ("pointer", f"fg:{ansi} bold"),
            ("highlighted", f"bg:{ansi} fg:ansiwhite bold"),
            ("selected", ""),
            ("answer", f"fg:{ansi} bold"),
        ]
    )


def _ask(prompt_obj):
    result = prompt_obj.ask()
    if result is None:
        raise KeyboardInterrupt()
    return result


STEP_LABELS = [
    "Purpose",
    "Audience",
    "Deploy",
    "Monetization",
    "Age",
    "Colors",
    "Landing",
    "Developer",
    "Email",
    "Country",
]


def _render_step_bar(
    current_idx: int, answers: OrderedDict[str, str], rich_primary: str
) -> Text:
    parts = Text()
    parts.append("  ")
    for i, label in enumerate(STEP_LABELS):
        if i > 0:
            parts.append(" · ", style="dim")
        if label in answers:
            parts.append("✓ ", style=rich_primary)
            parts.append(label, style=rich_primary)
        elif i == current_idx:
            parts.append("■ ", style=f"bold {rich_primary}")
            parts.append(label, style=f"bold {rich_primary}")
        else:
            parts.append("□ ", style="dim")
            parts.append(label, style="dim")
    return parts


def _ask_purpose(pu: ProjectUnderstanding, style: Style) -> str:
    noun = "project" if pu.deployment_target == DeploymentTarget.WEB_HOSTING else "app"
    console.print(f"  [dim]A brief one-liner describing what your {noun} does.[/]")
    val = _ask(
        questionary.text(
            f"What does your {noun} do?",
            default=pu.app_purpose or "",
            style=style,
        )
    )
    pu.app_purpose = val or ""
    return pu.app_purpose or "(skipped)"


def _ask_audience(pu: ProjectUnderstanding, style: Style) -> str:
    noun = "website" if pu.deployment_target == DeploymentTarget.WEB_HOSTING else "app"
    console.print(
        f"  [dim]Who is this {noun} built for? e.g. students, fitness enthusiasts.[/]"
    )
    val = _ask(
        questionary.text(
            "Target audience?",
            default=pu.target_audience or "General consumers",
            style=style,
        )
    )
    pu.target_audience = val or "General consumers"
    return pu.target_audience


def _ask_deploy(pu: ProjectUnderstanding, style: Style) -> str:
    console.print("  [dim]Choose how you want to distribute your app.[/]")
    choice = _ask(
        questionary.select(
            "Where will you deploy?",
            choices=[
                questionary.Choice(
                    "App Store — Full public release", value="app_store"
                ),
                questionary.Choice(
                    "TestFlight — Beta testing only", value="testflight"
                ),
                questionary.Choice(
                    "Web hosting — Deploy to the web", value="web_hosting"
                ),
                questionary.Choice(
                    "Enterprise — Internal distribution", value="enterprise"
                ),
            ],
            default=pu.deployment_target.value,
            style=style,
        )
    )
    pu.deployment_target = DeploymentTarget(choice)
    return pu.deployment_target.value.replace("_", " ").title()


def _ask_monetization(pu: ProjectUnderstanding, style: Style) -> str:
    console.print("  [dim]How will your app make money (if at all)?[/]")
    choice = _ask(
        questionary.select(
            "Monetization model?",
            choices=[
                questionary.Choice("Free — No charges", value="free"),
                questionary.Choice("Paid — One-time purchase", value="paid"),
                questionary.Choice(
                    "Freemium — Free + premium features", value="freemium"
                ),
                questionary.Choice(
                    "Subscription — Recurring payments", value="subscription"
                ),
                questionary.Choice("Ad-supported — Revenue from ads", value="ads"),
                questionary.Choice("None — Hobby or internal project", value="none"),
            ],
            default=pu.monetization.value,
            style=style,
        )
    )
    pu.monetization = MonetizationModel(choice)
    return pu.monetization.value.replace("_", " ").title()


def _ask_age(pu: ProjectUnderstanding, style: Style) -> str:
    console.print("  [dim]App Store age rating for content suitability.[/]")
    choice = _ask(
        questionary.select(
            "Age rating?",
            choices=[
                questionary.Choice("4+ — No objectionable content", value="4+"),
                questionary.Choice("9+ — Mild cartoon violence", value="9+"),
                questionary.Choice("12+ — Infrequent mature themes", value="12+"),
                questionary.Choice("17+ — Frequent mature content", value="17+"),
            ],
            default=pu.age_rating.value,
            style=style,
        )
    )
    pu.age_rating = AgeRating(choice)
    return pu.age_rating.value


def _ask_colors(pu: ProjectUnderstanding, style: Style) -> str:
    if pu.color_theme:
        theme_display = ", ".join(f"{k}: {v}" for k, v in pu.color_theme.items())
        console.print(f"  [dim]Detected from your project: {theme_display}[/]")
        keep = _ask(
            questionary.confirm(
                "Use detected colors for the landing page?",
                default=True,
                style=style,
            )
        )
        if keep:
            return theme_display
    else:
        console.print(
            "  [dim]Optional hex colors for your landing page. Leave blank to auto-generate.[/]"
        )

    primary = _ask(
        questionary.text(
            "Primary brand color (hex, e.g. #FF5722)?",
            default=pu.color_theme.get("primary", ""),
            style=style,
        )
    )
    if primary:
        pu.color_theme["primary"] = primary
    secondary = _ask(
        questionary.text(
            "Secondary brand color (hex)?",
            default=pu.color_theme.get("secondary", ""),
            style=style,
        )
    )
    if secondary:
        pu.color_theme["secondary"] = secondary

    if pu.color_theme:
        return ", ".join(f"{k}: {v}" for k, v in pu.color_theme.items())
    return "auto-generate"


def _ask_landing(pu: ProjectUnderstanding, style: Style) -> str:
    console.print("  [dim]Generate a landing page for your app, or skip.[/]")
    choice = _ask(
        questionary.select(
            "Landing page?",
            choices=[
                questionary.Choice(
                    "Prompt only — Paste into Le Chat / v0 / Bolt", value="prompt"
                ),
                questionary.Choice(
                    "Generate HTML — LLM creates the page directly", value="html"
                ),
                questionary.Choice("Skip — No landing page", value="no"),
            ],
            default=pu.landing_page.value,
            style=style,
        )
    )
    pu.landing_page = LandingPageChoice(choice)
    labels = {"prompt": "Prompt only", "html": "Generate HTML", "no": "Skip"}
    return labels.get(choice, choice)


def _ask_dev_name(pu: ProjectUnderstanding, style: Style) -> str:
    console.print("  [dim]Used in legal documents (privacy policy, ToS).[/]")
    val = _ask(
        questionary.text(
            "Developer / company name?",
            default=pu.developer_name or "",
            style=style,
        )
    )
    pu.developer_name = val or ""
    return pu.developer_name or "(skipped)"


def _ask_email(pu: ProjectUnderstanding, style: Style) -> str:
    if pu.deployment_target == DeploymentTarget.WEB_HOSTING:
        console.print("  [dim]Contact email for the privacy policy.[/]")
    else:
        console.print(
            "  [dim]Contact email for the privacy policy and App Store listing.[/]"
        )
    val = _ask(
        questionary.text(
            "Contact email?",
            default=pu.developer_email or "",
            style=style,
        )
    )
    pu.developer_email = val or ""
    return pu.developer_email or "(skipped)"


def _ask_country(pu: ProjectUnderstanding, style: Style) -> str:
    console.print("  [dim]Determines legal jurisdiction for your Terms of Service.[/]")
    val = _ask(
        questionary.text(
            "Country?",
            default=(
                pu.developer_country if pu.developer_country != "United States" else ""
            ),
            style=style,
        )
    )
    pu.developer_country = val or "United States"
    return pu.developer_country


def _auto_fill_from_scan(pu: ProjectUnderstanding) -> dict[str, str]:
    from devdex.models import Platform

    auto: dict[str, str] = {}

    sdk_names = {s.name for s in pu.sdks}
    sdk_categories = {s.category for s in pu.sdks}

    if "ads" in sdk_categories:
        pu.monetization = MonetizationModel.ADS
        auto["Monetization"] = "Ad-supported (detected)"
    elif "RevenueCat" in sdk_names:
        pu.monetization = MonetizationModel.SUBSCRIPTION
        auto["Monetization"] = "Subscription (detected)"
    elif pu.has_in_app_purchases:
        pu.monetization = MonetizationModel.FREEMIUM
        auto["Monetization"] = "Freemium (detected)"
    elif "Stripe" in sdk_names or "Stripe.js" in sdk_names:
        pu.monetization = MonetizationModel.PAID
        auto["Monetization"] = "Paid (detected)"

    if pu.platform == Platform.IOS:
        pu.deployment_target = DeploymentTarget.APP_STORE
        auto["Deploy"] = "App Store (detected)"
    elif pu.platform == Platform.WEB:
        pu.deployment_target = DeploymentTarget.WEB_HOSTING
        auto["Deploy"] = "Web Hosting (detected)"

    if pu.platform == Platform.WEB or pu.deployment_target == DeploymentTarget.WEB_HOSTING:
        pu.age_rating = AgeRating.FOUR_PLUS
        auto["Age"] = "N/A (web project)"
        pu.landing_page = LandingPageChoice.NO
        auto["Landing"] = "N/A (already a website)"

    if pu.color_theme:
        theme_display = ", ".join(f"{k}: {v}" for k, v in pu.color_theme.items())
        auto["Colors"] = f"{theme_display} (detected)"

    return auto


STEPS: list[tuple[str, object]] = [
    ("Purpose", _ask_purpose),
    ("Audience", _ask_audience),
    ("Deploy", _ask_deploy),
    ("Monetization", _ask_monetization),
    ("Age", _ask_age),
    ("Colors", _ask_colors),
    ("Landing", _ask_landing),
    ("Developer", _ask_dev_name),
    ("Email", _ask_email),
    ("Country", _ask_country),
]

STEP_DESCRIPTIONS = {
    "Purpose": "What the app does",
    "Audience": "Target users",
    "Deploy": "Distribution method",
    "Monetization": "Revenue model",
    "Age": "Content rating",
    "Colors": "Brand colors",
    "Landing": "Landing page option",
    "Developer": "Developer or company",
    "Email": "Contact address",
    "Country": "Legal jurisdiction",
}


def _show_summary(answers: OrderedDict[str, str], border_style: str, pu: ProjectUnderstanding | None = None):
    is_web = pu and pu.deployment_target == DeploymentTarget.WEB_HOSTING
    lines = []
    for label, value in answers.items():
        desc = STEP_DESCRIPTIONS.get(label, "")
        if label == "Purpose" and is_web:
            desc = "What the project does"
        lines.append(f"  [bold]{label}[/]  [dim]{desc}[/]")
        lines.append(f"    {value}")
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    console.print()
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold]Summary[/]",
            border_style=border_style,
            expand=True,
            padding=(1, 2),
        )
    )


def run_interview_cli(state: DevDexPipelineState) -> DevDexPipelineState:
    from devdex.cli import get_session_theme

    theme = get_session_theme()
    border = theme["border"]
    style = _make_style(border)

    pu = state.understanding
    answers: OrderedDict[str, str] = OrderedDict()

    auto_answers = _auto_fill_from_scan(pu)
    if auto_answers:
        answers.update(auto_answers)
        detail_lines = [f"  {k} → {v}" for k, v in auto_answers.items()]
        console.print()
        console.print(
            Panel(
                "\n".join(detail_lines),
                title="[bold]Auto-detected from scan[/]",
                border_style=border,
                expand=False,
                padding=(0, 1),
            )
        )

    console.print(f"\n[{theme['accent']}]--- Project Questionnaire ---[/]")
    console.print("[dim]Ctrl+C to quit.[/]\n")

    for i, (label, ask_fn) in enumerate(STEPS):
        if label in answers:
            continue

        console.print()
        console.print(_render_step_bar(i, answers, border))
        console.print()

        display = ask_fn(pu, style)
        answers[label] = display

    while True:
        _show_summary(answers, border, pu)

        action = _ask(
            questionary.select(
                "Ready?",
                choices=[
                    questionary.Choice("Looks good, generate!", value="submit"),
                    questionary.Choice("Edit a field", value="edit"),
                ],
                default="submit",
                style=style,
            )
        )

        if action == "submit":
            break

        field = _ask(
            questionary.select(
                "Which field to edit?",
                choices=[questionary.Choice(lbl, value=lbl) for lbl in answers],
                style=style,
            )
        )
        for idx, (lbl, fn) in enumerate(STEPS):
            if lbl == field:
                console.print()
                console.print(_render_step_bar(idx, answers, border))
                console.print()
                answers[lbl] = fn(pu, style)
                break

    state.interview_complete = True
    console.print(f"\n[{theme['accent']}]Questionnaire complete![/]\n")
    return state
