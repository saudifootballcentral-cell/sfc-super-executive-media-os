using UnityEngine;
using Moments.Core;

namespace Moments.Minigames.PolarPush
{
    /// Normal-difficulty bot. THE LAW: bots drive the exact same input API
    /// as phones (ControllerGateway.SubmitInput) — gameplay cannot tell the
    /// difference, which is what makes them valid for soak tests and
    /// disconnect takeover.
    ///
    /// Behavior: stay near safe ice, drift toward the nearest rival when
    /// confident, dash-push when lined up, fight the blizzard drift.
    public sealed class BotController : MonoBehaviour
    {
        public float thinkEverySeconds = 0.15f;   // human-ish reaction cadence
        public float aggroRange = 4f;
        public float dashRange = 1.8f;

        int slot, seq;
        IcePlatformManager platform;
        PolarPushGame game;
        float thinkT;
        Vector3 target;

        public void Init(int slot, IcePlatformManager platform, PolarPushGame game)
        {
            this.slot = slot; this.platform = platform; this.game = game;
        }

        void Update()
        {
            thinkT -= Time.deltaTime;
            if (thinkT > 0) return;
            thinkT = thinkEverySeconds;

            var pos = transform.position;
            bool dash = false;

            // survival first: on cracked/missing ice -> run to safety
            if (platform.StateAt(pos) != TileState.Solid)
            {
                var safe = platform.NearestSafePoint(pos);
                target = safe ?? Vector3.zero;
            }
            else
            {
                // hunt: nearest living rival inside aggro range, else drift center
                HeroController prey = null; float best = aggroRange * aggroRange;
                foreach (var h in FindObjectsByType<HeroController>(FindObjectsSortMode.None))
                {
                    if (h.Slot == slot) continue;
                    float d = (h.transform.position - pos).sqrMagnitude;
                    if (d < best) { best = d; prey = h; }
                }
                if (prey != null)
                {
                    // push them OUTWARD: aim through the rival away from center
                    var through = (prey.transform.position - pos).normalized;
                    bool outward = Vector3.Dot(through, prey.transform.position.normalized) > 0.2f;
                    target = prey.transform.position + through * 0.5f;
                    dash = outward && best < dashRange * dashRange;
                }
                else target = Vector3.zero;                       // idle toward center
            }

            var move = target - pos; move.y = 0;
            if (move.magnitude > 0.2f) move.Normalize(); else move = Vector3.zero;

            ControllerGateway.Instance.SubmitInput(slot, new PlayerInput
            { seq = ++seq, moveX = move.x, moveY = move.z, dash = dash });
        }
    }
}
