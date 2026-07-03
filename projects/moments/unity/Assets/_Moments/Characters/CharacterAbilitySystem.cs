using UnityEngine;

namespace Moments.Characters
{
    /// The ability hook layer. Slice ruling: hooks exist, numbers identical.
    /// Core Alpha flips `abilitiesEnabled` (host toggle) and per-hero stats
    /// from CharacterDefinition start to matter. Gameplay code MUST read all
    /// multipliers through this class — never from the definition directly —
    /// so the toggle is one switch, not a refactor.
    public sealed class CharacterAbilitySystem : MonoBehaviour
    {
        public static bool abilitiesEnabled = false;   // host setting; slice: false

        public CharacterDefinition definition;

        public float Speed(float baseValue)
            => baseValue * (abilitiesEnabled ? definition.stats.speedMult : 1f);
        public float PushForce(float baseValue)
            => baseValue * (abilitiesEnabled ? definition.stats.pushForceMult : 1f);
        public float KnockbackTaken(float baseValue)
            => baseValue / (abilitiesEnabled ? definition.stats.knockbackResistMult : 1f);
        public float Cooldown(float baseValue)
            => baseValue * (abilitiesEnabled ? definition.stats.cooldownMult : 1f);

        // Alpha: dash variants / weapon / special slots land here behind the
        // same toggle. Slice ships the universal dash only (HeroController).
    }
}
