using System.Collections.Generic;
using UnityEngine;
using Moments.Core;

namespace Moments.Minigames.PolarPush
{
    /// Hazard scheduler implementing the telegraph standard (bible §7):
    /// phone vibration + TV warning, exactly 2 seconds, then the event.
    /// Slice ships one hazard: Blizzard Gust. Alpha adds Orca Breach etc.
    /// by extending the same Arm/Tick contract.
    public sealed class ArenaHazardSystem : MonoBehaviour
    {
        [Header("Schedule")]
        public float firstHazardAt = 35f;
        public float hazardEverySeconds = 25f;
        public float telegraphSeconds = 2f;    // the standard — do not change per hazard

        [Header("Blizzard Gust")]
        public float gustForce = 7f;
        public float gustSeconds = 3f;

        enum HState { Idle, Telegraph, Active }
        HState state = HState.Idle;
        float clock, stateT, nextAt;
        Vector3 gustDir;
        System.Random rng;

        public void Arm(int seed)
        {
            rng = new System.Random(seed * 7919);
            clock = 0; stateT = 0; state = HState.Idle;
            nextAt = firstHazardAt;
        }

        public void Tick(float dt, IEnumerable<HeroController> heroes)
        {
            clock += dt; stateT += dt;
            switch (state)
            {
                case HState.Idle:
                    if (clock >= nextAt)
                    {
                        float a = (float)(rng.NextDouble() * Mathf.PI * 2);
                        gustDir = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                        SetState(HState.Telegraph);
                        ControllerGateway.Instance.AssignLayout("show_hazard_warning",
                            promptsAr: "عاصفة قادمة!", promptsEn: "Blizzard incoming!");
                        // HUDManager.ShowHazardWarning(gustDir) — TV side of the telegraph
                    }
                    break;

                case HState.Telegraph:
                    if (stateT >= telegraphSeconds) SetState(HState.Active);
                    break;

                case HState.Active:
                    foreach (var h in heroes)
                        if (h.TryGetComponent<Rigidbody>(out var rb))
                            rb.AddForce(gustDir * gustForce, ForceMode.Acceleration);
                    // VFXManager.BlizzardParticles(gustDir) — vfx_polish stage
                    if (stateT >= gustSeconds)
                    {
                        SetState(HState.Idle);
                        nextAt = clock + hazardEverySeconds;
                        ControllerGateway.Instance.AssignLayout("show_joystick");
                    }
                    break;
            }
        }

        void SetState(HState s) { state = s; stateT = 0; }
    }
}
