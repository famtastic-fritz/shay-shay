"""Tests for the advisory Run Model router (shay_cli/run_router.py).

These assert that the routing rules encoded in run-policy.yaml DRIVE the
router's picks — orchestrator by item-count + swarm keyword, executor by
task-kind — exactly as the RUN-MODEL spec requires.
"""

from shay_cli import run_router


def test_policy_loads_and_is_advisory():
    policy = run_router.load_policy()
    assert policy["mode"] == "advisory"
    assert "orchestrators" in policy
    assert "executors" in policy
    assert "routing" in policy


def test_single_item_is_interactive():
    plan = run_router.select_run("fix the login bug")
    assert plan.item_count == 1
    assert plan.orchestrator == "interactive"
    assert plan.parallel is False


def test_n_items_default_is_ralph_sequential():
    plan = run_router.select_run("build these 10 screens")
    assert plan.item_count == 10
    assert plan.orchestrator == "ralph"
    assert plan.parallel is False


def test_n_items_with_swarm_is_swarm_parallel():
    plan = run_router.select_run("swarm 10 research tasks")
    assert plan.item_count == 10
    assert plan.orchestrator == "swarm"
    assert plan.parallel is True


def test_code_kind_routes_to_claude_cli():
    plan = run_router.select_run("build these 10 screens")
    assert all(ip.executor == "claude-cli" for ip in plan.items)
    assert all(ip.kind == "code" for ip in plan.items)


def test_research_kind_routes_to_gemini_cli():
    plan = run_router.select_run("swarm 10 research tasks")
    assert all(ip.executor == "gemini-cli" for ip in plan.items)
    assert all(ip.kind == "research" for ip in plan.items)


def test_doc_kind_routes_to_native():
    plan = run_router.select_run("update these 3 docs")
    assert plan.orchestrator == "ralph"
    assert all(ip.executor == "native" for ip in plan.items)


def test_explicit_items_override_count_inference():
    items = ["build the navbar", "research competitor pricing", "fix typo in readme"]
    plan = run_router.select_run("do this backlog", items=items)
    assert plan.item_count == 3
    assert plan.orchestrator == "ralph"  # no swarm keyword
    execs = [ip.executor for ip in plan.items]
    assert execs == ["claude-cli", "gemini-cli", "native"]


def test_swarm_with_explicit_mixed_items_is_parallel():
    items = ["research A", "research B"]
    plan = run_router.select_run("swarm these", items=items)
    assert plan.orchestrator == "swarm"
    assert plan.parallel is True
    assert all(ip.executor == "gemini-cli" for ip in plan.items)


def test_collision_warning_on_duplicate_targets_under_swarm():
    items = ["edit config.yaml", "edit config.yaml"]
    plan = run_router.select_run("swarm these edits", items=items)
    assert plan.orchestrator == "swarm"
    assert plan.collision_warning is not None
    assert "serial" in plan.collision_warning.lower()


def test_research_keyword_beats_code_keyword():
    # "research the API" contains "api" (code) but research must win.
    plan = run_router.select_run("research the api endpoints")
    assert plan.items[0].kind == "research"
    assert plan.items[0].executor == "gemini-cli"


def test_as_dict_is_serializable():
    import json

    plan = run_router.select_run("build these 10 screens")
    blob = json.dumps(plan.as_dict())
    assert "ralph" in blob
    assert "claude-cli" in blob


def test_render_plan_contains_key_facts():
    plan = run_router.select_run("swarm 10 research tasks")
    text = run_router.render_plan(plan, policy_src="x.yaml")
    assert "swarm" in text
    assert "gemini-cli" in text
    assert "parallel" in text
    assert "x.yaml" in text
