import shay_cli.kanban_db as kb


def test_extract_task_gate_with_fenced_block():
    task_body = """
    Some introductory text.

    ```gate
    command 1 --arg1
    command 2 "with spaces"
    # a comment line
    command 3
    ```

    More text after the gate.
    """
    expected_command = 'command 1 --arg1 && command 2 "with spaces" && command 3'
    assert kb._extract_task_gate(task_body) == expected_command

def test_extract_task_gate_no_fenced_block_returns_none():
    task_body = """
    This task has no special gate block.
    It's just prose and instructions.
    """
    assert kb._extract_task_gate(task_body) is None

def test_extract_task_gate_empty_fenced_block_returns_none():
    task_body = """
    A gate block, but empty.
    ```gate
    ```
    """
    assert kb._extract_task_gate(task_body) is None

def test_extract_task_gate_with_empty_lines_in_block():
    task_body = """
    ```gate
    cmd1

    cmd2
    ```
    """
    expected_command = "cmd1 && cmd2"
    assert kb._extract_task_gate(task_body) == expected_command

def test_extract_task_gate_mixed_content_before_and_after_gate():
    task_body = """
    Pre-gate info.
    ```gate
    first command
    second command
    ```
    Post-gate info.
    """
    expected_command = "first command && second command"
    assert kb._extract_task_gate(task_body) == expected_command


def test_extract_task_gate_prose_only_returns_none_no_false_red():
    """Prose that looks like instructions must NEVER be returned as a
    shell command. Without a ```gate fence the gate is 'unknown' (None),
    so the reconciler skips it rather than running prose and getting a
    false red."""
    task_body = """
    Run the test suite and make sure everything passes.
    Then commit your work. Verify the import is clean.
    pytest tests/   # this sentence is prose, not a gate command
    """
    assert kb._extract_task_gate(task_body) is None


def test_extract_task_gate_fenced_returns_commands():
    """A ```gate fence yields the joined command list, comments dropped."""
    task_body = """
    ```gate
    # verify import
    python -c "import shay_cli.kanban_db"
    pytest tests/shay_cli -q
    ```
    """
    expected = 'python -c "import shay_cli.kanban_db" && pytest tests/shay_cli -q'
    assert kb._extract_task_gate(task_body) == expected
