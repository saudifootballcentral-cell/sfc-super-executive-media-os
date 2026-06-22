# Video Clip Governance

## Overview

Every clip package passes through `ClipGovernanceLayer.review()` before
publishing. No clip can bypass governance. Governance checks four gates in order:

1. Rights gate
2. Brand safety check
3. Content policy check
4. Quality gate

---

## Rights Gate

| `rights_status` | Governance Status | Publishing |
|---|---|---|
| `restricted` | `RIGHTS_BLOCKED` | Blocked — hard stop |
| `unknown` | `NEEDS_MANUAL_REVIEW` | Blocked — pending operator approval |
| `owned` | Continues to next check | Allowed if all gates pass |
| `licensed` | Continues to next check | Allowed if all gates pass |
| `public_source` | Continues to next check | Allowed if all gates pass |

`rights_status = restricted` is a hard block at the **ingestion** stage.
The pipeline terminates immediately; no analysis or clipping occurs.

`rights_status = unknown` allows internal analysis and clipping but blocks
publishing until an operator updates the rights status to `owned`,
`licensed`, or `public_source`.

---

## Brand Safety Check

The `ClipGovernanceLayer` scans package title and description for brand-unsafe
keywords. If any are found:

- `brand_safe = False`
- Issue added to `ClipGovernanceResult.issues`
- Package receives `REJECTED` status (unless rights are also unknown,
  in which case `NEEDS_MANUAL_REVIEW`)

Default unsafe keywords: violence, explicit, adult, hate, discrimination,
عنف, محتوى بالغ.

---

## Content Policy Gate

Minimum requirements for a clip package:

- `title` must not be empty
- `variants` must not be empty (at least one platform variant)

Failure here results in `content_policy_compliant = False` and rejection.

---

## Quality Gate

`quality_score >= VIDEO_CLIP_QUALITY_THRESHOLD` (default 70.0).

Quality score is computed by `ClipScoringEngine` as a weighted average of:
- Viral potential (35%)
- Audience appeal (25%)
- Brand alignment (25%)
- Technical quality (15%)

Clips below the threshold receive `quality_gate_passed = False` and are rejected.

---

## Governance Status Flow

```
PENDING
  │
  ├─ rights = RESTRICTED → RIGHTS_BLOCKED (terminal, no publish)
  │
  ├─ any check fails + rights unknown → NEEDS_MANUAL_REVIEW (blocked)
  │
  ├─ brand unsafe OR policy fail OR quality fail → REJECTED (blocked)
  │
  └─ all checks pass → APPROVED (cleared for publishing)
```

---

## cleared_for_publishing

`ClipGovernanceResult.cleared_for_publishing` is `True` only when:

```python
status in (APPROVED, NEEDS_MANUAL_REVIEW)
AND rights_verified = True
AND brand_safe = True
AND content_policy_compliant = True
```

Note: `NEEDS_MANUAL_REVIEW` sets `cleared_for_publishing = False` because
`rights_verified = False`.

Only `APPROVED` with all flags `True` clears a clip for publishing.
