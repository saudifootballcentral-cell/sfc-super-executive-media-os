#!/usr/bin/env python3
"""
asset_router.py — the mandatory routing law for every asset.

Order of consideration (cheapest first — Meshy credits are the Creative
Director's money):

  1. reuse        asset already exists in memory/assets.json or downloads/
  2. retexture    a same-mesh variant of an existing Meshy asset (skins)
  3. procedural   Blender factories — geometric, exact-dims, collider-driven
  4. meshy        organic/complex/hero assets (text-to-3d or image-to-3d)
  5. marketplace  meshy budget exhausted or repeated generation failures
  6. manual       nothing above applies — Creative Director decides

No Meshy generation happens without a routing decision logged in memory
('decisions' store). /siraj-route wraps this engine.

Usage:
  python3 asset_router.py route '<json>'
    fields: name (required), type (character|creature|prop|arena|platform|
            obstacle|weapon|hero_weapon|animation|skin|vehicle|...),
            exact_dims (bool), concept_image (bool), variant_of (name),
            organic (bool), hero (bool), notes
  python3 asset_router.py route '<json>' --log     # also record the decision
"""
import json
import sys

import memory

PROCEDURAL_TYPES = {"arena", "platform", "obstacle", "floor", "wall", "weapon",
                    "animation"}
ORGANIC_TYPES = {"character", "creature", "organic", "hero_weapon", "vehicle"}
POLY_BUDGETS = {"character": 15000, "creature": 15000, "arena": 30000,
                "prop": 8000, "weapon": 8000, "default": 8000}


def _existing_assets():
    return {a.get("name"): a for a in memory.read_store("assets") if a.get("name")}


def _meshy_credits_low():
    for entry in reversed(memory.read_store("credits")):
        if "remaining" in entry:
            try:
                return float(entry["remaining"]) <= float(entry.get("floor", 0))
            except (TypeError, ValueError):
                return False
    return False


def _repeated_failures(name):
    fails = [h for h in memory.read_store("meshy_history")
             if h.get("name") == name and h.get("status") in ("FAILED", "rejected")]
    return len(fails) >= 2


def route(spec: dict) -> dict:
    name = spec.get("name")
    if not name:
        return {"error": "spec needs at least a 'name'"}
    atype = (spec.get("type") or "prop").lower()
    chain = []

    # 1. reuse
    assets = _existing_assets()
    if name in assets:
        return _verdict("reuse", f"'{name}' already exists ({assets[name].get('path', 'memory/assets.json')}) — never regenerate an existing asset", chain, spec)
    chain.append("reuse: no existing asset with this name")

    # 2. retexture
    base = spec.get("variant_of")
    if base or atype == "skin":
        base_asset = assets.get(base) if base else None
        task_id = (base_asset or {}).get("meshy_task_id")
        if task_id:
            return _verdict("retexture",
                            f"same mesh as '{base}' (meshy task {task_id}) — retexture is cheaper than regeneration",
                            chain, spec, extra={"base_task_id": task_id})
        chain.append("retexture: no base Meshy task id found"
                     + (f" for '{base}'" if base else ""))
    else:
        chain.append("retexture: not a variant/skin")

    # 3. procedural
    if spec.get("exact_dims") or atype in PROCEDURAL_TYPES:
        why = ("exact dimensions / collider-driven geometry demand procedural control"
               if spec.get("exact_dims")
               else f"type '{atype}' is geometric/systemic — buildable in Blender in under a minute")
        if atype in ORGANIC_TYPES and not spec.get("exact_dims"):
            chain.append("procedural: organic type, skipping")
        else:
            return _verdict("procedural", why, chain, spec)
    else:
        chain.append("procedural: not geometric/exact-dims")

    # 4. meshy
    if not _meshy_credits_low() and not _repeated_failures(name):
        kind = "image-to-3d" if spec.get("concept_image") else "text-to-3d"
        why = (f"organic/complex form — Meshy {kind} exceeds the procedural sculpting ceiling"
               if atype in ORGANIC_TYPES or spec.get("organic") or spec.get("hero")
               else f"no cheaper route qualified — Meshy {kind} (preview before refine)")
        return _verdict("meshy", why, chain, spec, extra={"meshy_kind": kind})
    chain.append("meshy: credits low or repeated failures for this asset")

    # 5. marketplace
    if _meshy_credits_low() or _repeated_failures(name):
        return _verdict("marketplace",
                        "Meshy unavailable (budget/failures) — source from asset store, license permitting",
                        chain, spec)

    # 6. manual
    return _verdict("manual", "no automated route qualified — Creative Director decides", chain, spec)


def _verdict(route_name, reason, chain, spec, extra=None):
    atype = (spec.get("type") or "prop").lower()
    out = {"route": route_name, "asset": spec.get("name"), "type": atype,
           "reason": reason,
           "poly_budget": POLY_BUDGETS.get(atype, POLY_BUDGETS["default"]),
           "chain": chain}
    if extra:
        out.update(extra)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "route":
        sys.exit(__doc__.strip())
    try:
        spec = json.loads(sys.argv[2])
    except json.JSONDecodeError as e:
        sys.exit(f"invalid JSON: {e}")
    result = route(spec)
    if "--log" in sys.argv[3:] and "error" not in result:
        memory.append("decisions", {"kind": "asset_route", **result})
    print(json.dumps(result, ensure_ascii=False, indent=2))
