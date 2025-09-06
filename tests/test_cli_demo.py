#!/usr/bin/env python3
"""Smoke tests for the CLI demo parser and dispatch.

Directly calls examples.cli_demo.cli.main with simple, safe subcommands
that do not depend on external services: transforms, presets, status, quick-ref,
and validate with a trivial prompt.
"""

from examples.cli_demo import cli as demo_cli


def test_cli_transforms():
    assert demo_cli.main(["transforms"]) == 0


def test_cli_presets():
    assert demo_cli.main(["presets"]) == 0


def test_cli_status():
    assert demo_cli.main(["status"]) == 0


def test_cli_quick_ref():
    assert demo_cli.main(["quick-ref"]) == 0


def test_cli_validate():
    assert demo_cli.main(["validate", "--prompt", "add blur"]) == 0
