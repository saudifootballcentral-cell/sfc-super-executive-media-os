# Video Clip Types

## Sport Event Types

| Event | Keyword Triggers | Highlight Score Base | Best Platforms |
|---|---|---|---|
| `goal` | هدف, goal, score, scored | 92 | YouTube Short, TikTok, Instagram |
| `save` | تصدى, إنقاذ, save, saved, goalkeeper | 82 | YouTube Short, Instagram |
| `penalty` | ركلة جزاء, penalty | 85 | YouTube Short, TikTok |
| `red_card` | بطاقة حمراء, red card, طرد | 75 | X (Twitter), YouTube |
| `var_review` | var, مراجعة | 70 | YouTube, X |
| `skill` | مهارة, skill, dribble | 80 | TikTok, Instagram |
| `celebration` | احتفال, celebration | 75 | Instagram, TikTok |
| `controversial` | جدل, controversial | 70 | X (Twitter) |
| `near_miss` | كاد, near miss | 65 | YouTube Short |
| `yellow_card` | بطاقة صفراء, yellow card | 45 | X |
| `injury` | إصابة, injury | 50 | Low priority |
| `substitution` | تبديل, substitution | 40 | Low priority |
| `tactical_moment` | (AI detected) | 60 | YouTube |
| `crowd_reaction` | (AI detected) | 55 | YouTube, TikTok |
| `coach_reaction` | (AI detected) | 50 | YouTube, X |
| `free_kick` | ركلة حرة, free kick | 55 | YouTube Short |
| `corner` | ركنية, corner | 35 | Low priority |

## Interview / Quote Clips

| Type | Description | Clip Source |
|---|---|---|
| `player_interview` | Player post-match or pre-match interview | `key_quote` clips |
| `coach_interview` | Manager/coach tactical or emotional quotes | `key_quote` clips |
| `press_conference` | Formal press conference Q&A | `key_quote` clips |
| `pundit_analysis` | Studio analysis and commentary | `key_quote` clips |

Quote clips are extracted from `KeyQuote` objects with `importance_score >= 70`.

---

## Platform Clip Specifications

| Platform | Aspect Ratio | Max Duration | Format |
|---|---|---|---|
| YouTube Short | 9:16 | 60s | MP4 |
| Instagram Reel | 9:16 | 90s | MP4 |
| TikTok | 9:16 | 180s | MP4 |
| X Video | 16:9 | 140s | MP4 |
| YouTube Video | 16:9 | No limit | MP4 |

---

## Clip Scoring Weights

```
overall_score = (
    viral_potential  × 0.35
    + audience_appeal × 0.25
    + brand_alignment × 0.25
    + technical_quality × 0.15
)
```

Clips with `overall_score < 70` are rejected by governance quality gate.
Controversial clips have reduced brand alignment (base 62 vs 82).

---

## Learning Loop Weight Adjustment

After clips are published and engagement data is recorded, the `ClipLearningLoop`
adjusts detection weights ±5% based on engagement vs. average:

```python
loop = get_clip_learning_loop()
loop.record_performance(
    clip_id="clip-uuid",
    platform="youtube_short",
    views=150000,
    likes=8000,
    shares=3000,
    comments=500,
)
report = await loop.generate_report()
print(report.weight_adjustments)  # {"goal": 1.05, "save": 0.98}
```
