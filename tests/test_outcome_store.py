"""Tests for the outcome store and Jaccard similarity helper."""

from __future__ import annotations

import pytest

from app.reasoning.outcome_store import OutcomeRecord, OutcomeStore, _jaccard_similarity


class TestJaccardSimilarity:
    """Unit tests for the _jaccard_similarity helper."""

    def test_identical_texts_returns_one(self) -> None:
        assert _jaccard_similarity("saas subscription", "saas subscription") == 1.0

    def test_empty_texts_returns_zero(self) -> None:
        assert _jaccard_similarity("", "") == 0.0

    def test_one_empty_text_returns_zero(self) -> None:
        assert _jaccard_similarity("hello world", "") == 0.0
        assert _jaccard_similarity("", "hello world") == 0.0

    def test_no_overlap_returns_zero(self) -> None:
        assert _jaccard_similarity("apple banana cherry", "date elderberry fig") == 0.0

    def test_partial_overlap_between_zero_and_one(self) -> None:
        sim = _jaccard_similarity("saas subscription developer", "saas platform user")
        assert 0.0 < sim < 1.0

    def test_symmetry(self) -> None:
        a = "recurring revenue saas billing subscription"
        b = "saas billing tool for developers"
        assert _jaccard_similarity(a, b) == _jaccard_similarity(b, a)

    def test_single_shared_word(self) -> None:
        sim = _jaccard_similarity("saas tool alpha", "saas widget beta")
        assert sim > 0.0

    def test_punctuation_stripped(self) -> None:
        # Commas and periods should not prevent word matching.
        sim_plain = _jaccard_similarity("saas tool", "saas tool")
        sim_punct = _jaccard_similarity("saas, tool.", "saas tool")
        assert sim_plain == sim_punct == 1.0

    def test_case_insensitive(self) -> None:
        assert _jaccard_similarity("SaaS SUBSCRIPTION", "saas subscription") == 1.0


class TestOutcomeRecord:
    """Unit tests for the OutcomeRecord model."""

    def test_defaults_are_sensible(self) -> None:
        record = OutcomeRecord(idea_id="x", idea_text="test idea", outcome_score=0.7)
        assert record.revenue_usd == 0.0
        assert record.conversions == 0
        assert record.views == 0
        assert record.churn30d == 0.0
        assert record.source == "unknown"
        assert record.captured_at  # non-empty timestamp

    def test_outcome_score_bounds(self) -> None:
        with pytest.raises(Exception):
            OutcomeRecord(idea_id="x", idea_text="test", outcome_score=1.5)
        with pytest.raises(Exception):
            OutcomeRecord(idea_id="x", idea_text="test", outcome_score=-0.1)


class TestOutcomeStore:
    """Unit tests for the OutcomeStore."""

    def test_empty_store_record_count(self) -> None:
        store = OutcomeStore()
        assert store.record_count() == 0

    def test_add_record_increments_count(self) -> None:
        store = OutcomeStore()
        store.add_record(OutcomeRecord(idea_id="a", idea_text="saas billing", outcome_score=0.8))
        assert store.record_count() == 1

    def test_add_multiple_records(self) -> None:
        store = OutcomeStore()
        for i in range(5):
            store.add_record(
                OutcomeRecord(idea_id=str(i), idea_text=f"idea {i}", outcome_score=0.5),
            )
        assert store.record_count() == 5

    def test_find_similar_empty_store_returns_empty(self) -> None:
        store = OutcomeStore()
        assert store.find_similar("any text", top_k=5) == []

    def test_find_similar_empty_query_returns_empty(self) -> None:
        store = OutcomeStore()
        store.add_record(OutcomeRecord(idea_id="a", idea_text="something", outcome_score=0.5))
        assert store.find_similar("", top_k=5) == []

    def test_find_similar_returns_most_similar_first(self) -> None:
        store = OutcomeStore()
        store.add_record(
            OutcomeRecord(idea_id="close", idea_text="saas subscription billing platform", outcome_score=0.9),
        )
        store.add_record(
            OutcomeRecord(idea_id="far", idea_text="blockchain nft gaming metaverse", outcome_score=0.2),
        )
        results = store.find_similar("saas subscription revenue", top_k=5, min_similarity=0.0)
        assert len(results) >= 1
        assert results[0].record.idea_id == "close"

    def test_find_similar_top_k_limits_results(self) -> None:
        store = OutcomeStore()
        for i in range(10):
            store.add_record(
                OutcomeRecord(idea_id=str(i), idea_text=f"saas subscription idea {i}", outcome_score=0.5),
            )
        results = store.find_similar("saas subscription", top_k=3)
        assert len(results) <= 3

    def test_find_similar_min_similarity_filters_results(self) -> None:
        store = OutcomeStore()
        store.add_record(
            OutcomeRecord(idea_id="a", idea_text="horses hay barn farm rural", outcome_score=0.8),
        )
        results = store.find_similar("saas subscription software startup", top_k=5, min_similarity=0.5)
        assert results == []

    def test_find_similar_similarity_values_in_range(self) -> None:
        store = OutcomeStore()
        store.add_record(
            OutcomeRecord(idea_id="a", idea_text="saas subscription billing", outcome_score=0.7),
        )
        results = store.find_similar("saas subscription platform", top_k=5, min_similarity=0.0)
        for r in results:
            assert 0.0 <= r.similarity <= 1.0

    def test_reset_clears_all_records(self) -> None:
        store = OutcomeStore()
        store.add_record(OutcomeRecord(idea_id="a", idea_text="test", outcome_score=0.5))
        store.reset()
        assert store.record_count() == 0
        assert store.find_similar("test") == []

    def test_results_sorted_by_similarity_descending(self) -> None:
        store = OutcomeStore()
        # "saas billing" has more overlap with query "saas billing recurring"
        store.add_record(
            OutcomeRecord(idea_id="high", idea_text="saas billing recurring", outcome_score=0.8),
        )
        store.add_record(
            OutcomeRecord(idea_id="low", idea_text="marketplace directory listing", outcome_score=0.6),
        )
        results = store.find_similar("saas billing recurring platform", top_k=5, min_similarity=0.0)
        sims = [r.similarity for r in results]
        assert sims == sorted(sims, reverse=True)
