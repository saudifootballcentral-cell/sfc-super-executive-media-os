# Pipeline — Publishing / Delivery

Stage: `publishing` · Owner: producer

## Deliverables
1. Build artifact (from the build pipeline).
2. README: how to run, how to extend, asset inventory, known issues.
3. Updated `workspace/SIRAJ_SYSTEMS.md` project section.
4. Credits report: total Meshy spend vs. the plan's budget.
5. If Unity Cloud is active: `ugs_deploy.sh` for live-service config the GDD explicitly
   requires; cloud-build results land in memory via `cloud_build_hooks/post-build.sh`.

## Gate
Creative Director sign-off — explicit words, recorded in the gate note. This is the only
gate that cannot pass on technical evidence alone.
