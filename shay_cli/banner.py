"""Welcome banner, ASCII art, skills summary, and update check for the CLI.

Pure display functions with no ShayCLI state dependency.
"""

import json
import getpass
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from shay_constants import get_shay_home
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prompt_toolkit import print_formatted_text as _pt_print
from prompt_toolkit.formatted_text import ANSI as _PT_ANSI

logger = logging.getLogger(__name__)


# =========================================================================
# ANSI building blocks for conversation display
# =========================================================================

_GOLD = "\033[1;38;2;255;215;0m"  # True-color #FFD700 bold
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RST = "\033[0m"


def cprint(text: str):
    """Print ANSI-colored text through prompt_toolkit's renderer."""
    _pt_print(_PT_ANSI(text))


# =========================================================================
# Skin-aware color helpers
# =========================================================================

def _skin_color(key: str, fallback: str) -> str:
    """Get a color from the active skin, or return fallback."""
    try:
        from shay_cli.skin_engine import get_active_skin
        return get_active_skin().get_color(key, fallback)
    except Exception:
        return fallback


def _skin_branding(key: str, fallback: str) -> str:
    """Get a branding string from the active skin, or return fallback."""
    try:
        from shay_cli.skin_engine import get_active_skin
        return get_active_skin().get_branding(key, fallback)
    except Exception:
        return fallback


# =========================================================================
# ASCII Art & Branding
# =========================================================================

from shay_cli import __version__ as VERSION, __release_date__ as RELEASE_DATE

SHAY_AGENT_LOGO = """[bold #FF3366]███████╗██╗  ██╗ █████╗ ██╗   ██╗       ███████╗██╗  ██╗ █████╗ ██╗   ██╗[/]
[bold #FF3366]██╔════╝██║  ██║██╔══██╗╚██╗ ██╔╝       ██╔════╝██║  ██║██╔══██╗╚██╗ ██╔╝[/]
[#2C5F8D]███████╗███████║███████║ ╚████╔╝ █████╗ ███████╗███████║███████║ ╚████╔╝ [/]
[#2C5F8D]╚════██║██╔══██║██╔══██║  ╚██╔╝  ╚════╝ ╚════██║██╔══██║██╔══██║  ╚██╔╝  [/]
[#FF3366]███████║██║  ██║██║  ██║   ██║          ███████║██║  ██║██║  ██║   ██║   [/]
[#FF3366]╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝          ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   [/]"""

SHAY_CADUCEUS = """[#CD7F32]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠀⣀⣀⠀⢀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#CD7F32]⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣿⣿⣇⠸⣿⣿⠇⣸⣿⣿⣷⣦⣄⡀⠀⠀⠀⠀⠀⠀[/]
[#FFBF00]⠀⢀⣠⣴⣶⠿⠋⣩⡿⣿⡿⠻⣿⡇⢠⡄⢸⣿⠟⢿⣿⢿⣍⠙⠿⣶⣦⣄⡀⠀[/]
[#FFBF00]⠀⠀⠉⠉⠁⠶⠟⠋⠀⠉⠀⢀⣈⣁⡈⢁⣈⣁⡀⠀⠉⠀⠙⠻⠶⠈⠉⠉⠀⠀[/]
[#FFD700]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⡿⠛⢁⡈⠛⢿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#FFD700]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠿⣿⣦⣤⣈⠁⢠⣴⣿⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#FFBF00]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠻⢿⣿⣦⡉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#FFBF00]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢷⣦⣈⠛⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#CD7F32]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣴⠦⠈⠙⠿⣦⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#CD7F32]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣤⡈⠁⢤⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠷⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠑⢶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠁⢰⡆⠈⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠳⠈⣡⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[#B8860B]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]"""


def _git_branch(cwd: str) -> str | None:
    """Return the current git branch for ``cwd``, or ``None`` when unavailable."""
    path = Path(cwd).expanduser()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    branch = (result.stdout or "").strip()
    return branch or None


def _time_of_day_greeting() -> str:
    user = os.environ.get("SHAY_USER_NICKNAME") or os.environ.get("USER") or getpass.getuser() or "there"
    return f"Map Bole, {user}. Let’s move."


def _summarize_local_mailbox() -> dict | None:
    """Return a compact summary of the local mailbox, if present."""
    user = os.environ.get("USER") or getpass.getuser()
    mailbox = Path("/var/mail") / user
    if not mailbox.exists() or not mailbox.is_file():
        return None
    try:
        raw = mailbox.read_text(errors="replace")
    except Exception:
        return None

    chunks = [part for part in raw.split("\nFrom ") if part.strip()]
    if not chunks:
        return None

    latest = chunks[-1]
    subject = ""
    sender = ""
    body_lines: list[str] = []
    in_body = False
    for raw_line in latest.splitlines():
        line = raw_line.rstrip("\n")
        if not in_body:
            if not line.strip():
                in_body = True
                continue
            lowered = line.lower()
            if lowered.startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif lowered.startswith("from:"):
                sender = line.split(":", 1)[1].strip()
        elif line.strip():
            body_lines.append(line.strip())

    preview = next((line for line in body_lines if line), "")
    return {"count": len(chunks), "subject": subject, "sender": sender, "preview": preview}


def _clean_mail_text(value: str, *, limit: int) -> str:
    """Trim noisy cron details from mailbox text for startup display."""
    cleaned = " ".join((value or "").split())
    replacements = [
        ("Cron <", "Cron "),
        (">> ~/.famtastic/logs/cron-analysis.log 2>&1", ""),
        ("/Users/famtasticfritz/.famtastic/logs/cron-analysis.log", "cron-analysis.log"),
        ("No such file or directory", "missing cron-analysis.log"),
    ]
    for needle, repl in replacements:
        cleaned = cleaned.replace(needle, repl)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 3].rstrip() + "..."
    return cleaned


def _build_attention_items() -> list[str]:
    """Collect startup attention items."""
    items: list[str] = []
    mailbox = _summarize_local_mailbox()
    if mailbox:
        count = int(mailbox.get("count") or 0)
        subject = _clean_mail_text(mailbox.get("subject") or "local mailbox activity", limit=56)
        preview = _clean_mail_text(
            mailbox.get("preview") or mailbox.get("sender") or "check local mail",
            limit=64,
        )
        items.append(f"{count} local mail item(s) — {subject}: {preview}")
    return items


def _build_quick_actions() -> list[str]:
    return ["/resume", "/agents", "/model", "/new", "/history", "/help"]


# =========================================================================
# Skills scanning
# =========================================================================

def get_available_skills() -> Dict[str, List[str]]:
    """Return skills grouped by category, filtered by platform and disabled state.

    Delegates to ``_find_all_skills()`` from ``tools/skills_tool`` which already
    handles platform gating (``platforms:`` frontmatter) and respects the
    user's ``skills.disabled`` config list.
    """
    try:
        from tools.skills_tool import _find_all_skills
        all_skills = _find_all_skills()  # already filtered
    except Exception:
        return {}

    skills_by_category: Dict[str, List[str]] = {}
    for skill in all_skills:
        category = skill.get("category") or "general"
        skills_by_category.setdefault(category, []).append(skill["name"])
    return skills_by_category


# =========================================================================
# Update check
# =========================================================================

# Cache update check results for 6 hours to avoid repeated git fetches
_UPDATE_CHECK_CACHE_SECONDS = 6 * 3600

# Sentinel returned when we know an update exists but can't count commits
# (e.g. nix-built shay — no local git history to count against).
UPDATE_AVAILABLE_NO_COUNT = -1

_UPSTREAM_REPO_URL = "https://github.com/NousResearch/shay-shay.git"


def _check_via_rev(local_rev: str) -> Optional[int]:
    """Compare an embedded git revision to upstream main via ls-remote.

    Returns 0 if up-to-date, ``UPDATE_AVAILABLE_NO_COUNT`` if behind,
    or ``None`` on failure.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", _UPSTREAM_REPO_URL, "refs/heads/main"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    upstream_rev = result.stdout.split()[0]
    if not upstream_rev:
        return None
    return 0 if upstream_rev == local_rev else UPDATE_AVAILABLE_NO_COUNT


def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    """Count commits behind origin/main in a local checkout."""
    try:
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            capture_output=True, timeout=10,
            cwd=str(repo_dir),
        )
    except Exception:
        pass  # Offline or timeout — use stale refs, that's fine

    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],
            capture_output=True, text=True, timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def check_for_updates() -> Optional[int]:
    """Check whether a Shay-Shay update is available.

    Two paths: if ``SHAY_REVISION`` is set (nix builds embed it), compare
    it to upstream main via ``git ls-remote``. Otherwise look for a local
    git checkout and count commits behind ``origin/main``.

    Returns the number of commits behind, ``UPDATE_AVAILABLE_NO_COUNT`` (-1)
    if behind but the count is unknown, ``0`` if up-to-date, or ``None`` if
    the check failed or doesn't apply. Cached for 6 hours.
    """
    shay_home = get_shay_home()
    cache_file = shay_home / ".update_check"
    embedded_rev = os.environ.get("SHAY_REVISION") or None

    # Read cache — invalidate if the embedded rev has changed since last check
    now = time.time()
    try:
        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            if (
                now - cached.get("ts", 0) < _UPDATE_CHECK_CACHE_SECONDS
                and cached.get("rev") == embedded_rev
            ):
                return cached.get("behind")
    except Exception:
        pass

    if embedded_rev:
        behind = _check_via_rev(embedded_rev)
    else:
        # Prefer the running code's location over the profile-scoped path.
        # $SHAY_HOME/shay-shay/ may be a stale copy from --clone-all;
        # Path(__file__) always resolves to the actual installed checkout.
        repo_dir = Path(__file__).parent.parent.resolve()
        if not (repo_dir / ".git").exists():
            repo_dir = shay_home / "shay-shay"
        if not (repo_dir / ".git").exists():
            return None
        behind = _check_via_local_git(repo_dir)

    try:
        cache_file.write_text(json.dumps({"ts": now, "behind": behind, "rev": embedded_rev}))
    except Exception:
        pass

    return behind


def _resolve_repo_dir() -> Optional[Path]:
    """Return the active Shay-Shay git checkout, or None if this isn't a git install.

    Prefers the running code's location over the profile-scoped path
    because ``$SHAY_HOME/shay-shay/`` may be a stale copy carried
    over by ``--clone-all``.
    """
    repo_dir = Path(__file__).parent.parent.resolve()
    if not (repo_dir / ".git").exists():
        shay_home = get_shay_home()
        repo_dir = shay_home / "shay-shay"
    return repo_dir if (repo_dir / ".git").exists() else None


def _git_short_hash(repo_dir: Path, rev: str) -> Optional[str]:
    """Resolve a git revision to an 8-character short hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", rev],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_dir),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip()
    return value or None


def get_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]:
    """Return upstream/local git hashes for the startup banner."""
    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        return None

    upstream = _git_short_hash(repo_dir, "origin/main")
    local = _git_short_hash(repo_dir, "HEAD")
    if not upstream or not local:
        return None

    ahead = 0
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            ahead = int((result.stdout or "0").strip() or "0")
    except Exception:
        ahead = 0

    return {"upstream": upstream, "local": local, "ahead": max(ahead, 0)}


_RELEASE_URL_BASE = "https://github.com/NousResearch/shay-shay/releases/tag"
_latest_release_cache: Optional[tuple] = None  # (tag, url) once resolved


def get_latest_release_tag(repo_dir: Optional[Path] = None) -> Optional[tuple]:
    """Return ``(tag, release_url)`` for the latest git tag, or None.

    Local-only — runs ``git describe --tags --abbrev=0`` against the
    Shay-Shay checkout. Cached per-process. Release URL always points at the
    canonical NousResearch/shay-shay repo (forks don't get a link).
    """
    global _latest_release_cache
    if _latest_release_cache is not None:
        return _latest_release_cache or None

    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        _latest_release_cache = ()  # falsy sentinel — skip future lookups
        return None

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=str(repo_dir),
        )
    except Exception:
        _latest_release_cache = ()
        return None

    if result.returncode != 0:
        _latest_release_cache = ()
        return None

    tag = (result.stdout or "").strip()
    if not tag:
        _latest_release_cache = ()
        return None

    url = f"{_RELEASE_URL_BASE}/{tag}"
    _latest_release_cache = (tag, url)
    return _latest_release_cache


def format_banner_version_label() -> str:
    """Return the version label shown in the startup banner title."""
    base = f"Shay-Shay v{VERSION} ({RELEASE_DATE})"
    state = get_git_banner_state()
    if not state:
        return base

    upstream = state["upstream"]
    local = state["local"]
    ahead = int(state.get("ahead") or 0)

    if ahead <= 0 or upstream == local:
        return f"{base} · upstream {upstream}"

    carried_word = "commit" if ahead == 1 else "commits"
    return f"{base} · upstream {upstream} · local {local} (+{ahead} carried {carried_word})"


# =========================================================================
# Non-blocking update check
# =========================================================================

_update_result: Optional[int] = None
_update_check_done = threading.Event()


def prefetch_update_check():
    """Kick off update check in a background daemon thread."""
    def _run():
        global _update_result
        _update_result = check_for_updates()
        _update_check_done.set()
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def get_update_result(timeout: float = 0.5) -> Optional[int]:
    """Get result of prefetched check. Returns None if not ready."""
    _update_check_done.wait(timeout=timeout)
    return _update_result


# =========================================================================
# Welcome banner
# =========================================================================

def _format_context_length(tokens: int) -> str:
    """Format a token count for display (e.g. 128000 → '128K', 1048576 → '1M')."""
    if tokens >= 1_000_000:
        val = tokens / 1_000_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}M"
        return f"{val:.1f}M"
    elif tokens >= 1_000:
        val = tokens / 1_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}K"
        return f"{val:.1f}K"
    return str(tokens)


def _display_toolset_name(toolset_name: str) -> str:
    """Normalize internal/legacy toolset identifiers for banner display."""
    if not toolset_name:
        return "unknown"
    return (
        toolset_name[:-6]
        if toolset_name.endswith("_tools")
        else toolset_name
    )

def build_welcome_banner(console: Console, model: str, cwd: str,
                         tools: List[dict] = None,
                         enabled_toolsets: List[str] = None,
                         session_id: str = None,
                         get_toolset_for_tool=None,
                         context_length: int = None):
    """Build and print the command-center startup banner."""
    tools = tools or []
    enabled_toolsets = enabled_toolsets or []

    layout_table = Table.grid(padding=(0, 2))
    layout_table.add_column("left", justify="center")
    layout_table.add_column("right", justify="left")

    accent = _skin_color("banner_accent", "#FFBF00")
    dim = _skin_color("banner_dim", "#B8860B")
    text = _skin_color("banner_text", "#FFF8DC")
    session_color = _skin_color("session_border", "#8B8682")

    try:
        from shay_cli.skin_engine import get_active_skin
        _bskin = get_active_skin()
        _hero = _bskin.banner_hero if hasattr(_bskin, "banner_hero") and _bskin.banner_hero else SHAY_CADUCEUS
    except Exception:
        _bskin = None
        _hero = SHAY_CADUCEUS

    branch = _git_branch(cwd)
    greeting = _time_of_day_greeting()
    model_short = model.split("/")[-1] if "/" in model else model
    if model_short.endswith(".gguf"):
        model_short = model_short[:-5]
    if len(model_short) > 28:
        model_short = model_short[:25] + "..."

    left_lines = ["", _hero, "", f"[bold {accent}]{greeting}[/]"]
    runtime_line = f"[{text}]Model[/] [dim {dim}]→[/] [{accent}]{model_short}[/]"
    if context_length:
        runtime_line += f" [dim {dim}]·[/] [dim {dim}]{_format_context_length(context_length)} context[/]"
    left_lines.append(runtime_line)
    left_lines.append(f"[{text}]Workspace[/] [dim {dim}]→[/] [dim {dim}]{cwd}[/]")
    if branch:
        left_lines.append(f"[{text}]Branch[/] [dim {dim}]→[/] [{accent}]{branch}[/]")
    if session_id:
        left_lines.append(f"[{text}]Session[/] [dim {dim}]→[/] [dim {session_color}]{session_id}[/]")
    left_content = "\n".join(left_lines)

    skills_by_category = get_available_skills()
    total_skills = sum(len(s) for s in skills_by_category.values())
    toolset_count = len(enabled_toolsets) if enabled_toolsets else 0

    right_lines = [f"[bold {accent}]Mission Control[/]"]
    right_lines.append(f"[{text}]Tools[/] [dim {dim}]→[/] [{accent}]{len(tools)}[/]")
    right_lines.append(f"[{text}]Toolsets[/] [dim {dim}]→[/] [{accent}]{toolset_count}[/]")
    right_lines.append(f"[{text}]Skills[/] [dim {dim}]→[/] [{accent}]{total_skills}[/]")

    try:
        from shay_cli.profiles import get_active_profile_name
        _profile_name = get_active_profile_name()
        if _profile_name and _profile_name != "default":
            right_lines.append(f"[{text}]Profile[/] [dim {dim}]→[/] [{accent}]{_profile_name}[/]")
    except Exception:
        pass

    attention_items = _build_attention_items()
    right_lines.append("")
    right_lines.append(f"[bold {accent}]Live Signal[/]")
    if attention_items:
        for item in attention_items:
            right_lines.append(f"[{text}]•[/] [{text}]{item}[/]")
    else:
        right_lines.append(f"[dim {dim}]No live startup signal.[/]")

    right_lines.append("")
    right_lines.append(f"[bold {accent}]Launch Commands[/]")
    right_lines.append(f"[dim {dim}]{'  '.join(_build_quick_actions())}[/]")

    try:
        behind = get_update_result(timeout=0.5)
        if behind is not None and behind != 0:
            from shay_cli.config import get_managed_update_command, recommended_update_command
            right_lines.append("")
            if behind > 0:
                commits_word = "commit" if behind == 1 else "commits"
                right_lines.append(f"[bold yellow]Update[/] [dim {dim}]→[/] [yellow]{behind} {commits_word} behind[/]")
                right_lines.append(f"[dim {dim}]Run[/] [bold]{recommended_update_command()}[/bold]")
            else:
                managed_cmd = get_managed_update_command()
                right_lines.append("[bold yellow]Update[/] [dim yellow]→[/] [yellow]available[/]")
                if managed_cmd:
                    right_lines.append(f"[dim {dim}]Run[/] [bold]{managed_cmd}[/bold]")
    except Exception:
        pass

    right_content = "\n".join(right_lines)
    layout_table.add_row(left_content, right_content)

    title_color = _skin_color("banner_title", "#FFD700")
    border_color = _skin_color("banner_border", "#CD7F32")
    version_label = format_banner_version_label()
    release_info = get_latest_release_tag()
    if release_info:
        _tag, _url = release_info
        title_markup = f"[bold {title_color}][link={_url}]{version_label}[/link][/]"
    else:
        title_markup = f"[bold {title_color}]{version_label}[/]"
    outer_panel = Panel(
        layout_table,
        title=title_markup,
        border_style=border_color,
        padding=(0, 2),
    )

    console.print()
    term_width = shutil.get_terminal_size().columns
    if term_width >= 95:
        _logo = _bskin.banner_logo if _bskin and hasattr(_bskin, "banner_logo") and _bskin.banner_logo else SHAY_AGENT_LOGO
        console.print(_logo)
        console.print()
    console.print(outer_panel)
