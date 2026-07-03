using UnityEngine;

namespace Moments.Characters
{
    /// Data-driven hero. One asset per hero (bible: CharacterDefinition SO).
    /// Slice roster: byte, nova, orbit, pop.
    [CreateAssetMenu(menuName = "Moments/Character Definition", fileName = "Hero_")]
    public sealed class CharacterDefinition : ScriptableObject
    {
        [Header("Identity")]
        public string heroId;                 // "byte" — stable key used by phones
        public string displayNameEn;
        public string displayNameAr;
        [TextArea] public string fantasyEn;   // one-line fantasy for the carousel
        [TextArea] public string fantasyAr;
        public Color color = Color.white;     // stamps HUD, trail, phone frame

        [Header("Presentation")]
        public Sprite portrait;
        public GameObject prefab;             // rigged, 15k budget, from the triangle
        public string[] emoteClips;           // shared vocabulary across the roster

        [Header("Abilities — DORMANT IN SLICE (Creative Director ruling 2026-07-03)")]
        public CharacterStats stats = CharacterStats.Identical;
    }

    [System.Serializable]
    public struct CharacterStats
    {
        [Tooltip("All 1.0 in the slice — fair heroes. Alpha flips the host toggle.")]
        public float speedMult;
        public float pushForceMult;
        public float knockbackResistMult;
        public float cooldownMult;

        public static CharacterStats Identical => new CharacterStats
        { speedMult = 1f, pushForceMult = 1f, knockbackResistMult = 1f, cooldownMult = 1f };
    }
}
