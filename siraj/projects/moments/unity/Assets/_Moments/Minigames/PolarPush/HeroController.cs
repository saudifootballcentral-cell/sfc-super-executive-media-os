using UnityEngine;
using Moments.Core;
using Moments.Characters;

namespace Moments.Minigames.PolarPush
{
    /// Physics-driven hero on ice. Reads intent from ControllerGateway
    /// (phone or bot — identical), applies slippery movement, body pushing
    /// and the universal dash. All numbers route through
    /// CharacterAbilitySystem so the Alpha ability toggle costs nothing.
    [RequireComponent(typeof(Rigidbody), typeof(CharacterAbilitySystem))]
    public sealed class HeroController : MonoBehaviour
    {
        [Header("Ice feel")]
        public float moveForce = 28f;
        public float maxSpeed = 6.5f;
        public float iceDrag = 0.35f;          // low = slippery

        [Header("Push & dash (universal in slice)")]
        public float bodyPushForce = 6f;
        public float dashImpulse = 9f;
        public float dashCooldown = 1.5f;      // spec: heroStats.dash.cooldownSeconds

        public int Slot { get; private set; }
        public float DashReadyIn { get; private set; }

        Rigidbody rb;
        CharacterAbilitySystem abilities;
        bool dashHeld;

        public void Init(int slot, CharacterDefinition def)
        {
            Slot = slot;
            abilities = GetComponent<CharacterAbilitySystem>();
            abilities.definition = def;
            rb = GetComponent<Rigidbody>();
            rb.linearDamping = iceDrag;
            rb.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;
        }

        void FixedUpdate()
        {
            var input = ControllerGateway.Instance.GetInput(Slot);
            var move = Vector3.ClampMagnitude(new Vector3(input.moveX, 0, input.moveY), 1f);

            rb.AddForce(move * abilities.Speed(moveForce), ForceMode.Force);
            var flat = new Vector3(rb.linearVelocity.x, 0, rb.linearVelocity.z);
            float cap = abilities.Speed(maxSpeed);
            if (flat.magnitude > cap)
            {
                var capped = flat.normalized * cap;
                rb.linearVelocity = new Vector3(capped.x, rb.linearVelocity.y, capped.z);
            }
            if (move.sqrMagnitude > 0.01f)
                rb.MoveRotation(Quaternion.Slerp(rb.rotation,
                    Quaternion.LookRotation(move), 0.2f));

            DashReadyIn = Mathf.Max(0f, DashReadyIn - Time.fixedDeltaTime);
            if (input.dash && !dashHeld && DashReadyIn <= 0f)
            {
                var dir = move.sqrMagnitude > 0.01f ? move.normalized : transform.forward;
                rb.AddForce(dir * dashImpulse, ForceMode.VelocityChange);
                DashReadyIn = abilities.Cooldown(dashCooldown);
                // VFXManager.DashTrail(Slot) — hero-colored, wired in vfx_polish stage
            }
            dashHeld = input.dash;
            ControllerGateway.Instance.MarkProcessed(Slot);
        }

        void OnCollisionEnter(Collision c)
        {
            var other = c.rigidbody ? c.rigidbody.GetComponent<HeroController>() : null;
            if (other == null) return;
            var dir = (other.transform.position - transform.position).normalized;
            float speed = Vector3.Dot(rb.linearVelocity, dir);
            if (speed <= 0.5f) return;
            float force = other.abilities.KnockbackTaken(
                abilities.PushForce(bodyPushForce) * Mathf.Clamp01(speed / maxSpeed));
            c.rigidbody.AddForce(dir * force, ForceMode.VelocityChange);
            // VFXManager.HitSpark(c.GetContact(0).point) — vfx_polish stage
        }
    }
}
