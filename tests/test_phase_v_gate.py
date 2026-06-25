"""Regression tests: Phase V gate logic.

Tests three invariants:
1. Phase V must not count itself when evaluating prior-phase failures (the
   self-inclusion bug: 'GATE_PRIOR_PHASES_INCOMPLETE: failed phases =
   [Phase V — Controlled Production Activation]').
2. Phase V must PASS when Phases I–IV all pass and Railway has
   LIVE_PUBLISHING_ENABLED=true.
3. When a prior phase fails, Gate 1 must name that phase — never Phase V.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
_MOD_NAME = "production_go_live_testmod"


def _load_go_live() -> Any:
    spec = importlib.util.spec_from_file_location(
        _MOD_NAME,
        _SCRIPTS_DIR / "production_go_live.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Must register in sys.modules BEFORE exec so @dataclass can resolve __module__
    sys.modules[_MOD_NAME] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(_MOD_NAME, None)
        raise
    return mod


# Loaded once — module-level code (diagnostics prints) runs here.
_go_live = _load_go_live()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _passed_phase(mod: Any, name: str) -> Any:
    p = mod.PhaseResult(name=name)
    p.complete(passed=True)
    return p


def _failed_phase(mod: Any, name: str, reason: str = "simulated failure") -> Any:
    p = mod.PhaseResult(name=name)
    p.fail(reason)
    return p


def _four_passed_report(mod: Any) -> Any:
    report = mod.GoLiveReport()
    for name in [
        "Phase I — Production Health Assessment",
        "Phase II — End-to-End Dry Run",
        "Phase III — Publishing Infrastructure",
        "Phase IV — Enterprise Production Audit",
    ]:
        report.phases.append(_passed_phase(mod, name))
    return report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPhaseVGateLogic:
    """Phase V gate checks must evaluate only Phases I–IV."""

    def test_self_inclusion_bug_confirmed_without_fix(self) -> None:
        """Demonstrate the old bug: appending Phase V makes all_phases_passed False."""
        report = _four_passed_report(_go_live)

        # Before Phase V is appended, all phases pass
        assert all(p.passed or p.skipped for p in report.phases)

        # Simulate the old code: append Phase V (not yet passed) BEFORE the check
        v_stub = _go_live.PhaseResult(name="Phase V — Controlled Production Activation")
        report.phases.append(v_stub)

        # This is what the old code checked — it now returns False because of Phase V itself
        assert not all(p.passed or p.skipped for p in report.phases), (
            "Confirmed: including Phase V in the list breaks all_phases_passed"
        )

    def test_phase_v_passes_when_prior_phases_pass_and_railway_authorized(self) -> None:
        """Phase V must PASS when I–IV pass and Railway has LIVE_PUBLISHING_ENABLED=true."""
        report = _four_passed_report(_go_live)

        with (
            patch.object(_go_live, "_RAILWAY_LIVE_IS_TRUE", True),
            patch.object(_go_live, "_RAILWAY_LIVE_VALUE", "true"),
            patch.object(_go_live, "_RAILWAY_LIVE_SOURCE", "Railway Environment"),
            patch.dict(os.environ, {}, clear=False),
        ):
            result = asyncio.run(_go_live.phase_v_activate(report))

        assert result.passed, (
            f"Phase V must pass when I–IV pass and Railway has true. "
            f"Critical failures: {result.critical_failures}"
        )
        assert not result.critical_failures

    def test_phase_v_does_not_include_itself_in_failed_prior_phases(self) -> None:
        """Gate 1 failure message must not contain 'Phase V'."""
        # Phase II failed — only Phase II should appear in the error
        report = _four_passed_report(_go_live)
        report.phases[1] = _failed_phase(_go_live, "Phase II — End-to-End Dry Run")

        with (
            patch.object(_go_live, "_RAILWAY_LIVE_IS_TRUE", True),
            patch.object(_go_live, "_RAILWAY_LIVE_VALUE", "true"),
            patch.object(_go_live, "_RAILWAY_LIVE_SOURCE", "Railway Environment"),
            patch.dict(os.environ, {}, clear=False),
        ):
            result = asyncio.run(_go_live.phase_v_activate(report))

        assert not result.passed
        reason = result.critical_failures[0]
        assert "GATE_PRIOR_PHASES_INCOMPLETE" in reason
        assert "Phase II" in reason, f"Must name Phase II; got: {reason!r}"
        assert "Phase V" not in reason, (
            f"Phase V must NOT appear in failed-phases list; got: {reason!r}"
        )

    def test_gate1_names_specific_failed_phases_not_generic(self) -> None:
        """Gate 1 must name exactly the phases that failed, nothing more."""
        report = _four_passed_report(_go_live)
        report.phases[0] = _failed_phase(_go_live, "Phase I — Production Health Assessment")
        report.phases[2] = _failed_phase(_go_live, "Phase III — Publishing Infrastructure")

        with (
            patch.object(_go_live, "_RAILWAY_LIVE_IS_TRUE", True),
            patch.object(_go_live, "_RAILWAY_LIVE_VALUE", "true"),
            patch.object(_go_live, "_RAILWAY_LIVE_SOURCE", "Railway Environment"),
            patch.dict(os.environ, {}, clear=False),
        ):
            result = asyncio.run(_go_live.phase_v_activate(report))

        assert not result.passed
        reason = result.critical_failures[0]
        assert "Phase I" in reason
        assert "Phase III" in reason
        assert "Phase V" not in reason

    def test_gate3_blocks_when_railway_not_authorized(self) -> None:
        """Gate 3 must block if Railway has LIVE_PUBLISHING_ENABLED != 'true'."""
        report = _four_passed_report(_go_live)

        with (
            patch.object(_go_live, "_RAILWAY_LIVE_IS_TRUE", False),
            patch.object(_go_live, "_RAILWAY_LIVE_VALUE", "false"),
            patch.object(_go_live, "_RAILWAY_LIVE_SOURCE", "Railway Environment"),
            patch.dict(os.environ, {}, clear=False),
        ):
            result = asyncio.run(_go_live.phase_v_activate(report))

        assert not result.passed
        reason = result.critical_failures[0]
        assert "GATE_RAILWAY_ENV_NOT_AUTHORIZED" in reason
        assert "'false'" in reason or "false" in reason

    def test_gate3_blocks_when_railway_var_not_set(self) -> None:
        """Gate 3 must block if LIVE_PUBLISHING_ENABLED was absent from Railway env."""
        report = _four_passed_report(_go_live)

        with (
            patch.object(_go_live, "_RAILWAY_LIVE_IS_TRUE", False),
            patch.object(_go_live, "_RAILWAY_LIVE_VALUE", ""),
            patch.object(_go_live, "_RAILWAY_LIVE_SOURCE", "default (not set in Railway)"),
            patch.dict(os.environ, {}, clear=False),
        ):
            result = asyncio.run(_go_live.phase_v_activate(report))

        assert not result.passed
        reason = result.critical_failures[0]
        assert "GATE_RAILWAY_ENV_NOT_AUTHORIZED" in reason
        assert "not set in Railway" in reason
