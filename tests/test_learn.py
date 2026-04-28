"""Tests for the learn module (Task 6.4)."""
from __future__ import annotations

import os
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend-pro-max", "scripts"))

import learn


# ── Card generation ──────────────────────────────────────────────────────
def test_generate_cards_all():
    """generate_cards() returns cards from all domains."""
    cards = learn.generate_cards()
    assert len(cards) > 0
    domains = {c.domain for c in cards}
    assert len(domains) > 5


def test_generate_cards_domain_filter():
    """generate_cards(domain=X) returns only that domain."""
    cards = learn.generate_cards(domain="cache")
    assert len(cards) > 0
    assert all(c.domain == "cache" for c in cards)


def test_card_has_question_and_answer():
    """Every card has non-empty question and answer."""
    for card in learn.generate_cards(domain="messaging"):
        assert card.question, f"Card {card.id} has empty question"
        assert card.answer, f"Card {card.id} has empty answer"


def test_card_ids_unique():
    """Card IDs are unique."""
    cards = learn.generate_cards()
    ids = [c.id for c in cards]
    assert len(ids) == len(set(ids))


# ── SM-2 algorithm ──────────────────────────────────────────────────────
def test_sm2_rating_5():
    """Perfect rating increases interval and keeps high EF."""
    card = learn.Card(id="test.a", domain="test", question="Q", answer="A")
    learn.sm2_schedule(card, 5)
    assert card.interval == 1
    assert card.repetitions == 1
    assert card.easiness >= 2.5
    assert card.next_review  # non-empty

    learn.sm2_schedule(card, 5)
    assert card.interval == 6
    assert card.repetitions == 2


def test_sm2_rating_1_resets():
    """Failed rating resets repetitions."""
    card = learn.Card(id="test.b", domain="test", question="Q", answer="A",
                      repetitions=3, interval=15, easiness=2.5)
    learn.sm2_schedule(card, 1)
    assert card.repetitions == 0
    assert card.interval == 1


def test_sm2_easiness_never_below_1_3():
    """EF never drops below 1.3."""
    card = learn.Card(id="test.c", domain="test", question="Q", answer="A", easiness=1.4)
    for _ in range(10):
        learn.sm2_schedule(card, 1)
    assert card.easiness >= 1.3


def test_sm2_rating_clamped():
    """Ratings outside 1-5 are clamped."""
    card = learn.Card(id="test.d", domain="test", question="Q", answer="A")
    learn.sm2_schedule(card, 0)
    assert card.last_rating == 1
    card2 = learn.Card(id="test.e", domain="test", question="Q", answer="A")
    learn.sm2_schedule(card2, 10)
    assert card2.last_rating == 5


def test_sm2_interval_growth():
    """Repeated perfect ratings grow the interval."""
    card = learn.Card(id="test.f", domain="test", question="Q", answer="A")
    intervals = []
    for _ in range(5):
        learn.sm2_schedule(card, 4)
        intervals.append(card.interval)
    # Intervals should be non-decreasing
    assert intervals == sorted(intervals)
    assert intervals[-1] > intervals[0]


# ── State persistence ────────────────────────────────────────────────────
def test_load_state_empty():
    """Loading state when no file exists returns empty state."""
    with mock.patch.object(learn, "STATE_FILE", learn.Path(tempfile.mktemp())):
        state = learn.load_state()
        assert state["version"] == 1
        assert state["cards"] == {}


def test_save_and_load_state():
    """State round-trips through save/load."""
    tmp = tempfile.mktemp(suffix=".json")
    tmp_path = learn.Path(tmp)
    with mock.patch.object(learn, "STATE_FILE", tmp_path), \
         mock.patch.object(learn, "STATE_DIR", tmp_path.parent):
        state = {"version": 1, "cards": {"test.a": {"easiness": 2.6, "interval": 6,
                 "repetitions": 2, "next_review": "2026-01-01", "last_rating": 4, "domain": "test"}}}
        learn.save_state(state)
        loaded = learn.load_state()
        assert loaded["cards"]["test.a"]["easiness"] == 2.6


def test_reset_state():
    """reset_state removes the state file."""
    tmp = tempfile.mktemp(suffix=".json")
    tmp_path = learn.Path(tmp)
    tmp_path.write_text("{}")
    with mock.patch.object(learn, "STATE_FILE", tmp_path):
        learn.reset_state()
        assert not tmp_path.exists()


# ── Due card selection ───────────────────────────────────────────────────
def test_get_due_cards_new():
    """New cards (not in state) are returned."""
    cards = learn.generate_cards(domain="cache")
    state = {"version": 1, "cards": {}}
    due = learn.get_due_cards(state, cards, daily=3, domain="cache")
    assert len(due) == 3


def test_get_due_cards_respects_daily():
    """Daily limit is respected."""
    cards = learn.generate_cards()
    state = {"version": 1, "cards": {}}
    due = learn.get_due_cards(state, cards, daily=2)
    assert len(due) == 2


def test_get_due_cards_skips_future():
    """Cards scheduled for the future are not returned."""
    cards = [learn.Card(id="test.a", domain="test", question="Q", answer="A")]
    state = {"version": 1, "cards": {
        "test.a": {"easiness": 2.5, "interval": 30, "repetitions": 3,
                   "next_review": "2099-01-01", "last_rating": 4, "domain": "test"}
    }}
    due = learn.get_due_cards(state, cards, daily=5)
    assert len(due) == 0


# ── Stats ────────────────────────────────────────────────────────────────
def test_show_stats_empty():
    state = {"version": 1, "cards": {}}
    output = learn.show_stats(state)
    assert "No learning history" in output


def test_show_stats_with_data():
    state = {"version": 1, "cards": {
        "cache.redis": {"domain": "cache", "easiness": 2.7, "interval": 30,
                        "repetitions": 6, "next_review": "2026-05-01", "last_rating": 5},
        "cache.memcached": {"domain": "cache", "easiness": 2.0, "interval": 1,
                            "repetitions": 1, "next_review": "2026-04-28", "last_rating": 3},
    }}
    output = learn.show_stats(state)
    assert "Total cards seen: 2" in output
    assert "Mastered" in output
    assert "cache" in output
