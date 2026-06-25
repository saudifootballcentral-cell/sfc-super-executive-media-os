"""Live Connectivity Validation — SFC Super Executive Media OS.

Verifies all external connectors are reachable and credentials are valid.
Runs read-only checks ONLY. LIVE_PUBLISHING_ENABLED must remain false.

Usage:
    python scripts/live_connectivity_check.py

Exit codes:
    0 — all configured connectors pass (READY FOR CONTROLLED GO-LIVE)
    1 — one or more connector failures detected
    2 — import / runtime error (environment problem)
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

# Ensure src/ is importable when run directly
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
if os.path.join(_repo_root, "src") not in sys.path:
    sys.path.insert(0, os.path.join(_repo_root, "src"))

# ---------------------------------------------------------------------------
# Status tracking
# ---------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"  # credential not configured in this environment


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | FAIL | SKIP
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# 1. Anthropic connectivity
# ---------------------------------------------------------------------------

async def check_anthropic() -> CheckResult:
    """GET /v1/models — proves API key is valid; zero token consumption."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return CheckResult(
            name="Anthropic API",
            status=SKIP,
            detail="ANTHROPIC_API_KEY not configured",
        )

    try:
        import httpx
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.anthropic.com/v1/models", headers=headers)
        latency_ms = (time.monotonic() - t0) * 1000

        if resp.status_code == 200:
            body = resp.json()
            models = [m["id"] for m in body.get("data", [])[:5]]
            return CheckResult(
                name="Anthropic API",
                status=PASS,
                detail=f"HTTP 200 — {len(body.get('data', []))} models available",
                data={"sample_models": models},
                latency_ms=latency_ms,
            )
        else:
            return CheckResult(
                name="Anthropic API",
                status=FAIL,
                detail=f"HTTP {resp.status_code}: {resp.text[:200]}",
                latency_ms=latency_ms,
            )
    except Exception as exc:
        return CheckResult(
            name="Anthropic API",
            status=FAIL,
            detail=f"Connection error: {exc}",
        )


# ---------------------------------------------------------------------------
# 2. Buffer authentication (direct HTTP, read-only, no publishing)
# ---------------------------------------------------------------------------

_BUFFER_GQL_URL = "https://api.buffer.com"
_BUFFER_REST_BASE = "https://api.bufferapp.com/1"

_QUERY_WHOAMI = """
query SFCLiveCheck {
  account {
    id
    name
    email
    timezone
    channels {
      id
      service
      name
      handle
      avatar
    }
  }
}
"""

_QUERY_WHOAMI_ALT = """
query SFCLiveCheckAlt {
  currentUser {
    id
    name
    email
    timezone
  }
}
"""


def _is_api_key(token: str) -> bool:
    """Buffer API Keys contain hyphens; OAuth tokens do not."""
    return bool(token) and "-" in token


async def _buffer_graphql_whoami(token: str) -> tuple[bool, dict[str, Any], str]:
    """Direct GraphQL call to Buffer. Returns (success, data, error_msg)."""
    import httpx
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"query": _QUERY_WHOAMI}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(_BUFFER_GQL_URL, json=body, headers=headers)
        if resp.status_code in (401, 403):
            return False, {}, f"Auth rejected (HTTP {resp.status_code})"
        if resp.status_code != 200:
            return False, {}, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        if data.get("errors"):
            msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
            return False, {}, f"GraphQL errors: {msgs}"
        payload = data.get("data", {})
        account = payload.get("account") or {}
        if not account:
            # Try alt query
            alt_body = {"query": _QUERY_WHOAMI_ALT}
            async with httpx.AsyncClient(timeout=20.0) as client:
                alt_resp = await client.post(_BUFFER_GQL_URL, json=alt_body, headers=headers)
            if alt_resp.status_code == 200:
                alt_data = alt_resp.json().get("data", {})
                account = alt_data.get("currentUser", {})
        return True, account, ""
    except Exception as exc:
        return False, {}, str(exc)


async def _buffer_rest_whoami(token: str) -> tuple[bool, dict[str, Any], str]:
    """Direct REST call to Buffer v1. Returns (success, data, error_msg)."""
    import httpx
    url = f"{_BUFFER_REST_BASE}/user.json"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params={"access_token": token})
        if resp.status_code in (401, 403):
            return False, {}, f"Auth rejected (HTTP {resp.status_code})"
        if resp.status_code != 200:
            return False, {}, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        if data.get("error"):
            return False, {}, f"API error: {data['error']}"
        return True, data, ""
    except Exception as exc:
        return False, {}, str(exc)


async def check_buffer_auth() -> CheckResult:
    """Validate Buffer token via GraphQL (API Key) or REST (OAuth), read-only."""
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        return CheckResult(
            name="Buffer Authentication",
            status=SKIP,
            detail="BUFFER_ACCESS_TOKEN not configured",
        )

    t0 = time.monotonic()
    token_type = "API Key (GraphQL)" if _is_api_key(token) else "OAuth (REST)"

    if _is_api_key(token):
        ok, data, err = await _buffer_graphql_whoami(token)
        if not ok:
            # Fall back to REST
            ok, data, err = await _buffer_rest_whoami(token)
    else:
        ok, data, err = await _buffer_rest_whoami(token)
        if not ok:
            ok, data, err = await _buffer_graphql_whoami(token)

    latency_ms = (time.monotonic() - t0) * 1000

    if ok:
        user_name = data.get("name", data.get("id", "unknown"))
        user_email = data.get("email", "")
        return CheckResult(
            name="Buffer Authentication",
            status=PASS,
            detail=f"Token accepted — user: {user_name} ({user_email}) via {token_type}",
            data={"user_name": user_name, "user_email": user_email, "token_type": token_type},
            latency_ms=latency_ms,
        )
    else:
        return CheckResult(
            name="Buffer Authentication",
            status=FAIL,
            detail=f"Token validation failed ({token_type}): {err}",
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# 3. Buffer channel discovery
# ---------------------------------------------------------------------------

_GQL_SERVICE_DISPLAY = {
    "twitter": "X (Twitter)",
    "x": "X (Twitter)",
    "youtube": "YouTube",
    "instagram": "Instagram",
    "instagramBusiness": "Instagram Business",
    "instagramPersonal": "Instagram Personal",
    "facebook": "Facebook",
    "facebookPage": "Facebook Page",
    "tiktok": "TikTok",
    "tikTok": "TikTok",
    "linkedin": "LinkedIn",
    "linkedIn": "LinkedIn",
    "threads": "Threads",
}


async def check_buffer_channels() -> CheckResult:
    """Discover connected Buffer channels via GraphQL whoami (read-only)."""
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        return CheckResult(
            name="Buffer Channels",
            status=SKIP,
            detail="BUFFER_ACCESS_TOKEN not configured — channel discovery skipped",
        )

    t0 = time.monotonic()
    ok, account, err = await _buffer_graphql_whoami(token)
    latency_ms = (time.monotonic() - t0) * 1000

    if not ok:
        return CheckResult(
            name="Buffer Channels",
            status=FAIL,
            detail=f"Channel discovery failed: {err}",
            latency_ms=latency_ms,
        )

    channels = account.get("channels", [])
    if not channels:
        return CheckResult(
            name="Buffer Channels",
            status=PASS,
            detail="Account authenticated but no channels connected (or REST-only token)",
            data={"channel_count": 0, "channels": []},
            latency_ms=latency_ms,
        )

    channel_list = []
    for ch in channels:
        service = ch.get("service", "")
        display = _GQL_SERVICE_DISPLAY.get(service, service)
        handle = ch.get("handle") or ch.get("name", "")
        channel_list.append({
            "platform": display,
            "handle": handle,
            "id": ch.get("id", ""),
        })

    platforms = [c["platform"] for c in channel_list]
    return CheckResult(
        name="Buffer Channels",
        status=PASS,
        detail=f"{len(channel_list)} channel(s) discovered: {', '.join(platforms)}",
        data={"channel_count": len(channel_list), "channels": channel_list},
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# 4. X profile verification
# ---------------------------------------------------------------------------

async def check_x_profile(buffer_channels_data: dict[str, Any]) -> CheckResult:
    """Confirm X profile from Buffer channel data or X env vars."""
    x_api_key = os.environ.get("X_API_KEY", "")
    x_profile_id = os.environ.get("BUFFER_X_PROFILE_ID", "")

    channels = buffer_channels_data.get("channels", [])
    x_channels = [
        c for c in channels
        if c.get("platform", "").lower() in ("x (twitter)", "x", "twitter")
    ]

    if x_channels:
        handles = [c["handle"] for c in x_channels]
        return CheckResult(
            name="X (Twitter) Profile",
            status=PASS,
            detail=f"X account(s) connected via Buffer: {', '.join(handles)}",
            data={"handles": handles, "source": "buffer_graphql"},
        )
    elif x_profile_id:
        return CheckResult(
            name="X (Twitter) Profile",
            status=PASS,
            detail=f"X profile configured via BUFFER_X_PROFILE_ID: {x_profile_id}",
            data={"profile_id": x_profile_id, "source": "env_override"},
        )
    elif x_api_key:
        return CheckResult(
            name="X (Twitter) Profile",
            status=PASS,
            detail="X_API_KEY present — direct X API authentication available",
            data={"source": "x_api_key"},
        )
    else:
        return CheckResult(
            name="X (Twitter) Profile",
            status=SKIP,
            detail="X not configured (no Buffer X channel, BUFFER_X_PROFILE_ID, or X_API_KEY)",
        )


# ---------------------------------------------------------------------------
# 5. YouTube profile verification
# ---------------------------------------------------------------------------

async def check_youtube_profile(buffer_channels_data: dict[str, Any]) -> CheckResult:
    """Confirm YouTube profile from Buffer channel data or YouTube env vars."""
    yt_client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    yt_profile_id = os.environ.get("BUFFER_YOUTUBE_PROFILE_ID", "")

    channels = buffer_channels_data.get("channels", [])
    yt_channels = [c for c in channels if "youtube" in c.get("platform", "").lower()]

    if yt_channels:
        names = [c["handle"] for c in yt_channels]
        return CheckResult(
            name="YouTube Profile",
            status=PASS,
            detail=f"YouTube channel(s) connected via Buffer: {', '.join(names)}",
            data={"names": names, "source": "buffer_graphql"},
        )
    elif yt_profile_id:
        return CheckResult(
            name="YouTube Profile",
            status=PASS,
            detail=f"YouTube profile configured via BUFFER_YOUTUBE_PROFILE_ID: {yt_profile_id}",
            data={"profile_id": yt_profile_id, "source": "env_override"},
        )
    elif yt_client_id:
        return CheckResult(
            name="YouTube Profile",
            status=PASS,
            detail="YOUTUBE_CLIENT_ID present — YouTube OAuth available",
            data={"source": "youtube_oauth"},
        )
    else:
        return CheckResult(
            name="YouTube Profile",
            status=SKIP,
            detail="YouTube not configured (no Buffer YouTube channel, BUFFER_YOUTUBE_PROFILE_ID, or YOUTUBE_CLIENT_ID)",
        )


# ---------------------------------------------------------------------------
# 6. Connector class initialization check
# ---------------------------------------------------------------------------

async def check_connector_init() -> CheckResult:
    """Verify all publishing connector service classes initialize without error."""
    failures: list[str] = []
    successes: list[str] = []

    connectors_to_check = [
        ("Buffer API Client", "sfc.connectors.buffer.api_client", "get_buffer_api_client"),
        ("Buffer GraphQL Client", "sfc.connectors.buffer.graphql_client", "get_buffer_graphql_client"),
        ("Buffer Auth", "sfc.connectors.buffer.auth", "get_buffer_auth"),
        ("Buffer Profile Manager", "sfc.connectors.buffer.profiles", "get_buffer_profile_manager"),
        ("Buffer Publisher", "sfc.connectors.buffer.publisher", "get_buffer_publisher"),
        ("X Service", "sfc.connectors.x.service", "get_x_service"),
        ("YouTube Service", "sfc.connectors.youtube.service", "get_youtube_service"),
    ]

    for display_name, module_path, factory_fn in connectors_to_check:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            factory = getattr(mod, factory_fn)
            instance = factory()
            if instance is not None:
                successes.append(display_name)
            else:
                failures.append(f"{display_name}: factory returned None")
        except Exception as exc:
            failures.append(f"{display_name}: {exc}")

    if failures:
        return CheckResult(
            name="Connector Initialization",
            status=FAIL,
            detail=f"{len(failures)} connector(s) failed to initialize",
            data={"failures": failures, "successes": successes},
        )
    return CheckResult(
        name="Connector Initialization",
        status=PASS,
        detail=f"All {len(successes)} connector service classes initialized successfully",
        data={"connectors": successes},
    )


# ---------------------------------------------------------------------------
# 7. Graph node connector check
# ---------------------------------------------------------------------------

async def check_graph_connector_nodes() -> CheckResult:
    """Verify the LangGraph connector nodes can be imported."""
    failures: list[str] = []
    successes: list[str] = []

    nodes_to_check = [
        ("Buffer Connector Node", "sfc.graph.nodes.buffer_connector_node"),
        ("X Connector Node", "sfc.graph.nodes.x_connector_node"),
        ("YouTube Connector Node", "sfc.graph.nodes.youtube_connector_node"),
    ]

    for display_name, module_path in nodes_to_check:
        try:
            import importlib
            importlib.import_module(module_path)
            successes.append(display_name)
        except Exception as exc:
            failures.append(f"{display_name}: {exc}")

    if failures:
        return CheckResult(
            name="Graph Connector Nodes",
            status=FAIL,
            detail=f"{len(failures)} node module(s) failed to import",
            data={"failures": failures, "successes": successes},
        )
    return CheckResult(
        name="Graph Connector Nodes",
        status=PASS,
        detail=f"All {len(successes)} connector graph nodes imported successfully",
        data={"nodes": successes},
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _status_icon(status: str) -> str:
    return {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status, "[????]")


def print_report(results: list[CheckResult]) -> bool:
    """Print the Live Connectivity Report. Returns True if go-live ready."""
    width = 70
    line = "=" * width

    print()
    print(line)
    print("  SFC SUPER EXECUTIVE MEDIA OS — LIVE CONNECTIVITY REPORT")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(line)
    print()

    passes = [r for r in results if r.status == PASS]
    fails  = [r for r in results if r.status == FAIL]
    skips  = [r for r in results if r.status == SKIP]

    for result in results:
        icon = _status_icon(result.status)
        latency = f"  [{result.latency_ms:.0f}ms]" if result.latency_ms > 0 else ""
        print(f"  {icon}  {result.name}{latency}")
        print(f"         {result.detail}")

        if result.status == PASS and result.data:
            if "channels" in result.data and result.data["channels"]:
                for ch in result.data["channels"]:
                    print(f"           • {ch['platform']}: {ch['handle']}")
            elif "sample_models" in result.data:
                print(f"           Sample models: {', '.join(result.data['sample_models'][:3])}")
            elif "connectors" in result.data:
                for c in result.data["connectors"]:
                    print(f"           • {c}")
            elif "nodes" in result.data:
                for n in result.data["nodes"]:
                    print(f"           • {n}")
        elif result.status == FAIL and result.data.get("failures"):
            for f in result.data["failures"]:
                print(f"           ! {f}")
        print()

    print(line)
    print(f"  SUMMARY:  {len(passes)} PASS  |  {len(fails)} FAIL  |  {len(skips)} SKIP")
    print()

    # Publishing safety confirmation
    live_flag = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower()
    safety_icon = "[PASS]" if live_flag != "true" else "[FAIL]"
    print(f"  {safety_icon}  Publishing safety: LIVE_PUBLISHING_ENABLED={live_flag}")
    print()
    print(line)

    # Go-live determination: FAIL blocks; SKIP is acceptable (not configured here)
    go_live_ready = len(fails) == 0 and live_flag != "true"

    if go_live_ready:
        configured_pass = len(passes)
        skipped = len(skips)
        if configured_pass == 0 and skipped > 0:
            print()
            print("  NOTE: No credentials are configured in this environment.")
            print("        All checks were SKIP (not FAIL).")
            print("        Configure credentials in Railway to complete live validation.")
            print()
            print("  ENVIRONMENT STATUS: CREDENTIALS NOT CONFIGURED")
        else:
            print()
            print("  *** READY FOR CONTROLLED GO-LIVE ***")
            print()
            print("  All configured connectors passed validation.")
            if skipped > 0:
                print(f"  ({skipped} platform(s) not configured — add credentials to enable)")
    else:
        print()
        print("  *** NOT READY — RESOLVE FAILURES BEFORE GO-LIVE ***")
        print()
        for r in fails:
            print(f"    • {r.name}: {r.detail}")

    print()
    print(line)
    print()

    return go_live_ready


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_all_checks() -> list[CheckResult]:
    """Run all connectivity checks and return results."""
    results: list[CheckResult] = []

    # Anthropic
    r = await check_anthropic()
    results.append(r)

    # Buffer auth (needed before channel discovery)
    r_auth = await check_buffer_auth()
    results.append(r_auth)

    # Buffer channels
    r_channels = await check_buffer_channels()
    results.append(r_channels)
    channels_data = r_channels.data if r_channels.status == PASS else {}

    # Platform profiles
    results.append(await check_x_profile(channels_data))
    results.append(await check_youtube_profile(channels_data))

    # Connector init
    results.append(await check_connector_init())
    results.append(await check_graph_connector_nodes())

    return results


def main() -> int:
    try:
        results = asyncio.run(run_all_checks())
        ready = print_report(results)
        return 0 if ready else 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 2
    except Exception as exc:
        print(f"\n[ERROR] Live connectivity check failed with unexpected error: {exc}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
