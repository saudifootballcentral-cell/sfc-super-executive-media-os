---
name: siraj-route
description: Route an asset through the mandatory routing law (reuse → retexture → procedural → meshy → marketplace → manual) before any generation.
---

The argument describes the asset. Build the spec JSON and run the router:

```bash
python3 os/engine/asset_router.py route '{"name":"<Name>","type":"<character|prop|arena|weapon|skin|...>","exact_dims":false,"concept_image":false,"variant_of":null}' --log
```

- `--log` records the decision in memory — required before any Meshy spend.
- Report route + reason + poly budget to the Creative Director.
- If the route is `meshy`, remind: preview before refine; prompt must include
  "low poly, game asset, clean topology" (+ "T-pose, symmetrical" for
  characters).
- Never override the router by hand. Disagree? Change the spec fields
  (exact_dims, variant_of, ...) so they tell the truth, and re-run.
