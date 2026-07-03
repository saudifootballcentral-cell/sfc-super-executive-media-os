#!/usr/bin/env python3
"""unity_cloud_bridge.py — Siraj's bridge to Unity Cloud Asset Manager.

Purpose: let asset_director check the REAL cloud asset library before
routing any generation — this outranks the local memory/assets.json
registry, since Unity Cloud is the shared source of truth across a team.

## Setup
    pip install --index-url https://unity3ddist.jfrog.io/artifactory/api/pypi/am-pypi-prod-local/simple unity-cloud

Requires Python >= 3.9. Then set in home/mulerun/.env (never print these):
    UNITY_CLOUD_ORG_ID=012345678912
    UNITY_CLOUD_PROJECT_ID=1234abcd-ab12-cd34-ef56-123456abcdef

## Auth — read this before running unattended on a server
The SDK's documented quick-start uses an INTERACTIVE browser login
(unity_cloud.identity.user_login.login()), which is fine to run once from
an interactive terminal but is not obviously suited to unattended/headless
automation. Before wiring this into a fully autonomous pipeline, check
https://docs.unity.com/en-us/cloud/asset-manager/python-sdk for a
service-account (non-interactive) auth mode — this script does NOT assume
one exists, since that isn't confirmed. Run auth() once interactively per
machine; the SDK is expected to persist the session for subsequent calls.

## What's implemented vs. what needs your confirmation
- check_reuse() / get_by_label() / get_asset()  -> uses CONFIRMED SDK calls
  (unity_cloud.assets.get_asset, get_asset_by_label).
- update_metadata()                              -> uses CONFIRMED SDK call
  (unity_cloud.assets.update_asset + AssetUpdate).
- upload_new_asset()                             -> the exact SDK call for
  CREATING a brand-new asset (as opposed to updating one) was not confirmed
  in the docs pulled for this build. This function is intentionally a stub
  that raises NotImplementedError with a pointer to the manage-assets page
  — fill in the real call once you've confirmed it, rather than trust a
  guessed signature.

CLI:
  python3 unity_cloud_bridge.py check-reuse Falcon
  python3 unity_cloud_bridge.py get <asset_id> <asset_version>
"""
import os, sys, json

def _env():
    org = os.environ.get("UNITY_CLOUD_ORG_ID")
    proj = os.environ.get("UNITY_CLOUD_PROJECT_ID")
    if not org or not proj:
        env_path = os.path.expanduser("~/.env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("UNITY_CLOUD_ORG_ID="): org = line.split("=", 1)[1].strip()
                if line.startswith("UNITY_CLOUD_PROJECT_ID="): proj = line.split("=", 1)[1].strip()
    return org, proj

def _sdk():
    try:
        import unity_cloud
    except ImportError:
        sys.exit("Unity Cloud SDK not installed. See module docstring for the pip command.")
    return unity_cloud

def auth():
    """Run once, interactively, per machine. Not suitable for unattended cron use
    until a service-account auth mode is confirmed — see module docstring."""
    uc = _sdk()
    uc.initialize()
    uc.identity.user_login.use()
    state = uc.identity.user_login.get_authentication_state()
    if state != uc.identity.user_login.Authentication_State.LOGGED_IN:
        uc.identity.user_login.login()
    return uc

def get_by_label(asset_id, label, org_id=None, project_id=None):
    uc = _sdk()
    org_id = org_id or _env()[0]; project_id = project_id or _env()[1]
    if not (org_id and project_id):
        sys.exit("UNITY_CLOUD_ORG_ID / UNITY_CLOUD_PROJECT_ID not set")
    return uc.assets.get_asset_by_label(org_id=org_id, project_id=project_id,
                                          asset_id=asset_id, label=label)

def get_asset(asset_id, asset_version, org_id=None, project_id=None):
    uc = _sdk()
    org_id = org_id or _env()[0]; project_id = project_id or _env()[1]
    return uc.assets.get_asset(org_id=org_id, project_id=project_id,
                                 asset_id=asset_id, asset_version=asset_version)

def update_metadata(asset_id, asset_version, name=None, description=None,
                     tags=None, preview_file=None, org_id=None, project_id=None):
    uc = _sdk()
    org_id = org_id or _env()[0]; project_id = project_id or _env()[1]
    upd = uc.assets.AssetUpdate(name=name, description=description,
                                  type=uc.assets.AssetType.MODEL_3D,
                                  tags=tags or [], preview_file=preview_file)
    return uc.assets.update_asset(asset_update=upd, org_id=org_id, project_id=project_id,
                                    asset_id=asset_id, asset_version=asset_version)

def upload_new_asset(*args, **kwargs):
    raise NotImplementedError(
        "The create/upload-new-asset SDK call wasn't confirmed for this build. "
        "Check https://docs.unity.com/en-us/cloud/asset-manager/python-sdk/manage-assets "
        "for the current create-asset function, then implement here — don't guess the "
        "signature. Until then, upload new assets via the Unity Editor Asset Manager "
        "package (com.unity.asset-manager-for-unity) or the web dashboard, and use "
        "get_by_label()/update_metadata() here for everything downstream of that."
    )

def check_reuse(name):
    """Best-effort reuse check by label; returns the asset dict or None.
    Falls back cleanly (returns None) if the SDK/creds aren't configured,
    so callers can always fall through to the local JSON registry."""
    org_id, project_id = _env()
    if not (org_id and project_id):
        return None
    try:
        asset = get_by_label(asset_id=name, label="latest", org_id=org_id, project_id=project_id)
        return asset
    except Exception as e:
        print(f"[unity_cloud_bridge] reuse check failed, falling back to local registry: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "check-reuse":
        result = check_reuse(sys.argv[2])
        print(json.dumps({"found": result is not None, "asset": str(result) if result else None}))
    elif sys.argv[1] == "get":
        print(get_asset(sys.argv[2], sys.argv[3]))
    else:
        sys.exit(__doc__)
