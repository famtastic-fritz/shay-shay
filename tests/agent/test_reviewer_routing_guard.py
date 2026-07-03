from pathlib import Path

from agent.reviewer_routing_guard import decide_reviewer_route, infer_reviewer_lane


def test_protected_reviewer_lane_denies_unknown_candidate():
    decision = decide_reviewer_route(
        provider="custom:ollama-local",
        model="qwen3:14b",
        goal="Run final blocker adversarial review on this code diff",
        context="code patch",
        summary={},
    )
    assert decision.lane == "adversarial_review"
    assert decision.decision == "deny"


def test_promoted_reviewer_allowed_for_passed_family():
    summary = {
        "candidates": [
            {
                "provider": "openai-codex",
                "model": "gpt-5.5",
                "recommendation": "promote_for_passed_task_families",
                "passed_task_families": ["code_diff_review"],
                "pass_rate": 1.0,
            }
        ]
    }
    decision = decide_reviewer_route(
        provider="openai-codex",
        model="gpt-5.5",
        goal="Run adversarial review on this code diff",
        summary=summary,
    )
    assert decision.decision == "allow"
    assert decision.reason == "reviewer promoted by bakeoff scorecard"


def test_plain_tasks_are_not_review_lanes():
    assert infer_reviewer_lane("Implement the prefetch proof harness") == "non_review"
