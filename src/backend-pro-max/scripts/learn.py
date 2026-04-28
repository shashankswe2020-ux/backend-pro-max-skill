#!/usr/bin/env python3
"""
Backend Pro Max Learn — spaced-repetition flashcards from the KB.

Uses the SM-2 algorithm for scheduling. State persists in
~/.backendpro/learn.json. Pure standard-library.

Public API:
    generate_cards(domain=None) -> list[Card]
    sm2_schedule(card, rating) -> Card  (mutates and returns)
    get_due_cards(state, daily=5, domain=None) -> list[Card]
    run_session(domain=None, daily=5)
    show_stats(state) -> str
    reset_state()
    load_state() -> dict
    save_state(state)
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from .core import CSV_CONFIG
except ImportError:
    from core import CSV_CONFIG  # type: ignore[no-redef]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_DIR = Path.home() / ".backendpro"
STATE_FILE = STATE_DIR / "learn.json"

# Schema version for forward compatibility
_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Card model
# ---------------------------------------------------------------------------

@dataclass
class Card:
    id: str           # domain.slug
    domain: str
    question: str
    answer: str
    # SM-2 fields
    easiness: float = 2.5
    interval: int = 1       # days
    repetitions: int = 0
    next_review: str = ""   # ISO date string
    last_rating: int = 0


# ---------------------------------------------------------------------------
# Card generation from KB
# ---------------------------------------------------------------------------

def _name_col(cfg: dict) -> str:
    out = cfg.get("output_cols", [])
    for c in ("Name", "Topic", "Service", "Category", "Guideline"):
        if c in out:
            return c
    return out[0] if out else "Name"


def _slugify(text: str) -> str:
    import re
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[\s_]+", "-", s).strip("-")


def _make_question(name: str, row: dict, domain: str) -> str:
    """Generate a question from a KB row."""
    templates = [
        f"What is **{name}** and when would you use it?",
        f"Describe **{name}** — what problem does it solve?",
        f"What are the key trade-offs of **{name}**?",
    ]
    # Pick deterministically based on name hash
    return templates[hash(name) % len(templates)]


def _make_answer(name: str, row: dict, name_col: str) -> str:
    """Generate an answer from KB row fields."""
    parts = [f"**{name}**"]
    # Include the most informative fields
    answer_fields = [
        "Use Case", "Problem", "Solution", "Strengths", "Weaknesses",
        "When to Use", "When NOT to Use", "Trade-offs", "Mitigation",
        "Fix", "Description", "Category",
    ]
    for f in answer_fields:
        if f in row and row[f].strip():
            parts.append(f"**{f}:** {row[f].strip()}")
    if not parts[1:]:
        # Fallback: use all non-empty fields
        for k, v in row.items():
            if k != name_col and v.strip() and k not in ("Keywords", "Source URL", "Source Type", "Last Updated"):
                parts.append(f"**{k}:** {v.strip()}")
                if len(parts) >= 4:
                    break
    return "\n".join(parts)


def generate_cards(domain: str | None = None) -> list[Card]:
    """Generate flashcards from the KB."""
    cards = []
    seen_ids: set = set()
    configs = CSV_CONFIG
    if domain:
        configs = {k: v for k, v in configs.items() if k == domain}

    for dom, cfg in sorted(configs.items()):
        filepath = DATA_DIR / cfg["file"]
        if not filepath.exists():
            continue
        name_col = _name_col(cfg)
        with open(filepath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                name = row.get(name_col, "").strip()
                if not name:
                    continue
                base_id = f"{dom}.{_slugify(name)}"
                card_id = base_id
                counter = 2
                while card_id in seen_ids:
                    card_id = f"{base_id}-{counter}"
                    counter += 1
                seen_ids.add(card_id)
                cards.append(Card(
                    id=card_id,
                    domain=dom,
                    question=_make_question(name, row, dom),
                    answer=_make_answer(name, row, name_col),
                ))
    return cards


# ---------------------------------------------------------------------------
# SM-2 Algorithm
# ---------------------------------------------------------------------------

def sm2_schedule(card: Card, rating: int) -> Card:
    """
    Apply SM-2 algorithm. Rating: 1-5 (1=blackout, 5=perfect).

    SM-2 reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
    """
    rating = max(1, min(5, rating))
    card.last_rating = rating

    if rating < 3:
        # Failed — reset repetitions
        card.repetitions = 0
        card.interval = 1
    else:
        if card.repetitions == 0:
            card.interval = 1
        elif card.repetitions == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.easiness)

        card.repetitions += 1

    # Update easiness factor (never below 1.3)
    card.easiness = max(1.3, card.easiness + 0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))

    # Set next review date
    today = datetime.now().date()
    card.next_review = (today + timedelta(days=card.interval)).isoformat()

    return card


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def load_state() -> dict[str, Any]:
    """Load learn state from disk."""
    if not STATE_FILE.exists():
        return {"version": _SCHEMA_VERSION, "cards": {}}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version", 0) != _SCHEMA_VERSION:
            return {"version": _SCHEMA_VERSION, "cards": {}}
        return data
    except (json.JSONDecodeError, KeyError):
        return {"version": _SCHEMA_VERSION, "cards": {}}


def save_state(state: dict[str, Any]):
    """Atomically save state to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp.replace(STATE_FILE)


def reset_state():
    """Delete learn state."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ---------------------------------------------------------------------------
# Session logic
# ---------------------------------------------------------------------------

def get_due_cards(
    state: dict[str, Any],
    all_cards: list[Card],
    daily: int = 5,
    domain: str | None = None,
) -> list[Card]:
    """Get cards due for review today, up to daily limit."""
    today = datetime.now().date().isoformat()
    saved = state.get("cards", {})

    due = []
    new = []

    for card in all_cards:
        if domain and card.domain != domain:
            continue

        if card.id in saved:
            # Restore SM-2 state
            s = saved[card.id]
            card.easiness = s.get("easiness", 2.5)
            card.interval = s.get("interval", 1)
            card.repetitions = s.get("repetitions", 0)
            card.next_review = s.get("next_review", "")
            card.last_rating = s.get("last_rating", 0)

            if card.next_review <= today:
                due.append(card)
        else:
            new.append(card)

    # Prioritize due cards, then new cards
    random.shuffle(new)
    result = due + new
    return result[:daily]


def show_stats(state: dict[str, Any]) -> str:
    """Show learning progress stats."""
    cards = state.get("cards", {})
    if not cards:
        return "No learning history. Run `backendpro learn` to start."

    today = datetime.now().date().isoformat()
    total = len(cards)
    due = sum(1 for c in cards.values() if c.get("next_review", "") <= today)
    mastered = sum(1 for c in cards.values() if c.get("repetitions", 0) >= 5 and c.get("easiness", 2.5) >= 2.5)

    lines = [
        "📊 **Learning Stats**",
        f"  Total cards seen: {total}",
        f"  Due today: {due}",
        f"  Mastered (5+ reps, EF≥2.5): {mastered}",
        f"  In progress: {total - mastered}",
    ]

    # Per-domain breakdown
    domains: dict[str, int] = {}
    for c in cards.values():
        dom = c.get("domain", "unknown")
        domains[dom] = domains.get(dom, 0) + 1
    if domains:
        lines.append("\n  **By domain:**")
        for dom in sorted(domains):
            lines.append(f"    {dom}: {domains[dom]} cards")

    return "\n".join(lines)


def run_session(domain: str | None = None, daily: int = 5):
    """Run an interactive flashcard session."""
    all_cards = generate_cards(domain)
    if not all_cards:
        print("No cards available for the selected domain.")
        return

    state = load_state()
    due = get_due_cards(state, all_cards, daily, domain)

    if not due:
        print("🎉 No cards due today! Check back tomorrow or add --reset to start over.")
        return

    print(f"\n🧠 Backend Pro Max — Learn Mode ({len(due)} cards)\n")

    for i, card in enumerate(due, 1):
        print(f"─── Card {i}/{len(due)} [{card.domain}] ───")
        print(f"\n❓ {card.question}\n")
        input("  [Press Enter to reveal answer]")
        print(f"\n💡 {card.answer}\n")

        while True:
            try:
                rating_str = input("  Rate yourself (1=blackout, 2=wrong, 3=hard, 4=good, 5=perfect): ").strip()
                rating = int(rating_str)
                if 1 <= rating <= 5:
                    break
            except (ValueError, EOFError):
                pass
            print("  Please enter 1-5.")

        sm2_schedule(card, rating)

        # Save card state
        state.setdefault("cards", {})[card.id] = {
            "domain": card.domain,
            "easiness": card.easiness,
            "interval": card.interval,
            "repetitions": card.repetitions,
            "next_review": card.next_review,
            "last_rating": card.last_rating,
        }

    save_state(state)
    print(f"\n✅ Session complete! {len(due)} cards reviewed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list | None = None):
    """CLI: backendpro learn [--domain D] [--daily N] [--stats] [--reset]"""
    parser = argparse.ArgumentParser(prog="backendpro learn", description="Spaced-repetition flashcards from the KB.")
    parser.add_argument("--domain", "-d", default=None, help="Filter to a specific domain")
    parser.add_argument("--daily", "-n", type=int, default=5, help="Cards per session (default 5)")
    parser.add_argument("--stats", action="store_true", help="Show learning stats")
    parser.add_argument("--reset", action="store_true", help="Reset all learning state")
    args = parser.parse_args(argv)

    if args.reset:
        reset_state()
        print("🗑️  Learning state reset.")
        return

    if args.stats:
        state = load_state()
        print(show_stats(state))
        return

    run_session(domain=args.domain, daily=args.daily)


if __name__ == "__main__":
    main()
