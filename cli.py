"""
MindMate AI — Interactive CLI

Run:  python cli.py
      python cli.py --model mistral
      python cli.py --session <existing_session_id>
"""
from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from orchestrator import orchestrator
from emotion_detector import EmotionResult

app_cli = typer.Typer(add_completion=False)
console = Console()

BANNER = """
███╗   ███╗██╗███╗   ██╗██████╗ ███╗   ███╗ █████╗ ████████╗███████╗
████╗ ████║██║████╗  ██║██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║██║██╔██╗ ██║██║  ██║██╔████╔██║███████║   ██║   █████╗  
██║╚██╔╝██║██║██║╚██╗██║██║  ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║██║██║ ╚████║██████╔╝██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
                        AI Mental Health Companion for Students
"""

RISK_COLOURS = {"Low": "green", "Medium": "yellow", "High": "red"}
EMOTION_EMOJI = {
    "joy": "😊", "sadness": "😢", "anger": "😠", "fear": "😨",
    "disgust": "😣", "surprise": "😮", "neutral": "😐",
}


def _emotion_badge(emotion: EmotionResult) -> Text:
    emoji = EMOTION_EMOJI.get(emotion.primary_emotion, "🧠")
    colour = RISK_COLOURS.get(emotion.risk_level, "white")
    t = Text()
    t.append(f"{emoji} {emotion.primary_emotion.title()} ", style="bold")
    t.append(f"| Intensity {emotion.intensity}/10 ", style="white")
    t.append(f"| {emotion.risk_level} Risk", style=f"bold {colour}")
    if emotion.is_crisis:
        t.append(" ⚠ CRISIS", style="bold red blink")
    return t


@app_cli.command()
def run(
    model: str = typer.Option(None, "--model", "-m", help="Override Ollama model (e.g. mistral)"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Resume an existing session ID"),
    no_physical: bool = typer.Option(False, "--no-physical", help="Disable physical activity suggestions"),
    low_mobility: bool = typer.Option(False, "--low-mobility", help="Only suggest low-mobility activities"),
    indoor: bool = typer.Option(False, "--indoor", help="Only suggest indoor activities"),
    outdoor: bool = typer.Option(False, "--outdoor", help="Only suggest outdoor activities"),
):
    """Start an interactive MindMate AI session."""
    import config
    if model:
        config.OLLAMA_MODEL = model
        config.settings.ollama_model = model

    console.print(BANNER, style="bold cyan")
    console.print(
        Panel(
            "[bold]Welcome to MindMate AI[/bold] — your mental health companion.\n"
            "Type your message and press Enter. Type [bold yellow]quit[/bold yellow] or [bold yellow]exit[/bold yellow] to end.",
            border_style="cyan",
        )
    )

    environment = "indoor" if indoor else ("outdoor" if outdoor else None)
    current_session_id: Optional[str] = session

    while True:
        try:
            console.print()
            user_input = console.input("[bold green]You[/bold green]: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[italic]Take care of yourself. Goodbye! 💛[/italic]")
            sys.exit(0)

        if user_input.lower() in ("quit", "exit", "bye", "goodbye"):
            console.print("\n[italic]Take care of yourself. Goodbye! 💛[/italic]")
            break

        if not user_input:
            continue

        with console.status("[dim]MindMate is thinking...[/dim]", spinner="dots"):
            result = orchestrator.chat(
                user_message=user_input,
                session_id=current_session_id,
                include_physical=not no_physical,
                environment=environment,
                low_mobility=low_mobility,
            )

        current_session_id = result.session_id

        # ── Emotion badge ──────────────────────────────────────────────────
        console.print(_emotion_badge(result.emotion))

        # ── Response ────────────────────────────────────────────────────────
        console.print(
            Panel(
                Markdown(result.assistant_response),
                title="[bold blue]MindMate AI[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )
        )

        # ── Session ID (first turn) ─────────────────────────────────────────
        if not session:
            console.print(
                f"[dim]Session: {result.session_id}  "
                f"(use --session {result.session_id} to resume)[/dim]"
            )
            session = result.session_id  # suppress on subsequent turns


if __name__ == "__main__":
    app_cli()
