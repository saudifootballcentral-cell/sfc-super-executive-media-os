"""Verify Buffer API authentication using BUFFER_ACCESS_TOKEN env var.

Tries GraphQL first (for Buffer API Keys), falls back to REST (for OAuth tokens).

Usage:
    BUFFER_ACCESS_TOKEN="<token>" python scripts/verify_buffer_auth.py
"""

from __future__ import annotations

import asyncio
import os
import sys


def _force_live_mode() -> None:
    os.environ["LIVE_PUBLISHING_ENABLED"] = "true"


def _check_token() -> str:
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        print("ERROR: BUFFER_ACCESS_TOKEN is not set.")
        sys.exit(1)
    masked = token[:6] + "..." + token[-4:]
    print(f"Token found:  {masked}")
    return token


async def _verify() -> None:
    from sfc.connectors.buffer.api_client import BufferAPIClient
    from sfc.connectors.buffer.auth import BufferAuth
    from sfc.connectors.buffer.graphql_client import BufferGraphQLClient, get_buffer_graphql_client
    from sfc.connectors.buffer.profiles import BufferProfileManager

    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    is_api_key = BufferGraphQLClient.is_api_key(token)
    print(f"Token type:   {'API Key (GraphQL)' if is_api_key else 'OAuth token (REST)'}")
    print(f"Live mode:    True")
    print()

    rest_client = BufferAPIClient()
    gql_client = get_buffer_graphql_client()
    auth = BufferAuth(client=rest_client, graphql_client=gql_client)
    profile_mgr = BufferProfileManager(client=rest_client, graphql_client=gql_client)

    # ------------------------------------------------------------------
    # 1. Try GraphQL validation directly (most informative for API Keys)
    # ------------------------------------------------------------------
    print("=== GraphQL Validation ===")
    gql_user = await gql_client.validate()
    if gql_user and not gql_user.raw.get("dry_run"):
        print(f"OK  — GraphQL accepted token")
        print(f"      User ID:  {gql_user.user_id}")
        print(f"      Name:     {gql_user.name}")
        print(f"      Email:    {gql_user.email}")
        print(f"      Timezone: {gql_user.timezone}")
    else:
        print("     GraphQL validation did not return user data — trying REST...")

    # ------------------------------------------------------------------
    # 2. Unified auth (GraphQL → REST fallback)
    # ------------------------------------------------------------------
    print()
    print("=== Auth Validation (with fallback) ===")
    valid = await auth.validate_token()
    if not valid:
        print("FAIL: Token rejected by both GraphQL and REST APIs.")
        sys.exit(1)

    user = await auth.get_user()
    if user:
        print(f"OK  — api_mode: {user.api_mode}")
        if not user.raw.get("dry_run"):
            print(f"      User:     {user.name}")
            print(f"      Email:    {user.email}")
            print(f"      Plan:     {user.plan}")
            print(f"      Timezone: {user.timezone}")
            print(f"      User ID:  {user.user_id}")
    else:
        print("OK  — Token validated (user details unavailable)")

    # ------------------------------------------------------------------
    # 3. Health check
    # ------------------------------------------------------------------
    print()
    print("=== Health Check ===")
    health = await auth.health_check()
    for k, v in health.items():
        print(f"  {k}: {v}")

    # ------------------------------------------------------------------
    # 4. Connected channels / profiles
    # ------------------------------------------------------------------
    print()
    print("=== Connected Channels / Profiles ===")
    profiles = await profile_mgr.get_profiles(force_refresh=True)
    if not profiles:
        print("  (no channels found)")
    for p in profiles:
        print(f"  [{p.platform_key:12s}] {p.formatted_username:25s}  id={p.profile_id}  source={p.source}")

    print()
    print("Buffer authentication verified successfully.")


def main() -> None:
    _force_live_mode()
    _check_token()
    asyncio.run(_verify())


if __name__ == "__main__":
    main()
