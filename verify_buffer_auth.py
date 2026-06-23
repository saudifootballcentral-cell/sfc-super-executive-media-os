"""Verify Buffer API authentication using BUFFER_ACCESS_TOKEN env var.

Usage:
    BUFFER_ACCESS_TOKEN="<token>" python verify_buffer_auth.py
"""

from __future__ import annotations

import asyncio
import os
import sys


def _force_live_mode() -> None:
    """Force live mode so we make real API calls, not dry-run."""
    os.environ["LIVE_PUBLISHING_ENABLED"] = "true"


def _check_token() -> str:
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        print("ERROR: BUFFER_ACCESS_TOKEN is not set.")
        sys.exit(1)
    masked = token[:6] + "..." + token[-4:]
    print(f"Token found: {masked}")
    return token


async def _verify() -> None:
    # Imports after env is set so singletons pick up live mode
    from sfc.connectors.buffer.api_client import BufferAPIClient
    from sfc.connectors.buffer.auth import BufferAuth
    from sfc.connectors.buffer.profiles import BufferProfileManager

    client = BufferAPIClient()
    auth = BufferAuth(client=client)
    profile_mgr = BufferProfileManager(client=client)

    print(f"Live mode:  {client.is_live}")
    print()

    # --- Token validation ---
    print("=== Token Validation ===")
    valid = await auth.validate_token()
    if not valid:
        print("FAIL: Token rejected by Buffer API.")
        sys.exit(1)

    user = await auth.get_user()
    if user:
        print(f"OK  — User:     {user.name}")
        print(f"      Email:    {user.email}")
        print(f"      Plan:     {user.plan}")
        print(f"      Timezone: {user.timezone}")
        print(f"      User ID:  {user.user_id}")
    else:
        print("OK  — Token validated (user details unavailable)")

    # --- Health check ---
    print()
    print("=== Health Check ===")
    health = await auth.health_check()
    for k, v in health.items():
        print(f"  {k}: {v}")

    # --- Connected profiles ---
    print()
    print("=== Connected Profiles ===")
    profiles = await profile_mgr.get_profiles(force_refresh=True)
    if not profiles:
        print("  (no profiles found)")
    for p in profiles:
        print(f"  [{p.platform_key:12s}] {p.formatted_username:25s}  id={p.profile_id}")

    print()
    print("Buffer authentication verified successfully.")


def main() -> None:
    _force_live_mode()
    _check_token()
    asyncio.run(_verify())


if __name__ == "__main__":
    main()
