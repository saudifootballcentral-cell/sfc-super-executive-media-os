using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Moments.Core;
using Moments.Characters;

namespace Moments.Minigames.PolarPush
{
    /// The slice mini-game: last hero standing on the collapsing ice.
    /// Composition: IcePlatformManager (tiles), HeroController (per player),
    /// BlizzardGustHazard (via ArenaHazardSystem), Final Duel at 2 alive.
    public sealed class PolarPushGame : MiniGameBase
    {
        [Header("Wiring")]
        public IcePlatformManager platform;
        public ArenaHazardSystem hazards;
        public CharacterDefinition[] roster;      // byte, nova, orbit, pop
        public GameObject heroFallbackPrefab;     // capsule stub until Meshy heroes land

        [Header("Rules")]
        public float fallY = -3f;                 // below this = eliminated
        public int matchSeed = 0;                 // 0 = random; fixed for QA determinism

        readonly Dictionary<int, HeroController> heroes = new();
        bool finalDuelFired;

        protected override string ControllerLayout => "show_joystick";

        protected override void OnSetup(List<PlayerSlot> players)
        {
            int seed = matchSeed != 0 ? matchSeed : Random.Range(1, int.MaxValue);
            platform.Build(seed);
            hazards.Arm(seed);
            finalDuelFired = false;

            foreach (var h in heroes.Values) if (h) Destroy(h.gameObject);
            heroes.Clear();

            // spawn on ring 2, evenly spaced
            int i = 0, n = players.Count;
            foreach (var p in players)
            {
                var def = roster.FirstOrDefault(r => r.heroId == p.heroId) ?? roster[i % roster.Length];
                var prefab = def.prefab != null ? def.prefab : heroFallbackPrefab;
                float a = 2f * Mathf.PI * i / n;
                var pos = new Vector3(Mathf.Cos(a), 0.5f, Mathf.Sin(a)) * (platform.hexRadius * 3f);
                var hero = Instantiate(prefab, pos, Quaternion.LookRotation(-pos)).AddComponent<HeroController>();
                hero.Init(p.slot, def);
                if (p.isBot) hero.gameObject.AddComponent<BotController>().Init(p.slot, platform, this);
                heroes[p.slot] = hero;
                i++;
            }
        }

        protected override void OnPlayingTick()
        {
            platform.Tick(Time.deltaTime);
            hazards.Tick(Time.deltaTime, heroes.Values.Where(h => h != null));

            foreach (var kv in heroes.ToList())
            {
                if (IsEliminated(kv.Key) || kv.Value == null) continue;
                if (kv.Value.transform.position.y < fallY)
                {
                    Eliminate(kv.Key);
                    // AudioManager.Play("elimination"); phone haptic long — vfx/audio stages
                }
            }

            if (!finalDuelFired && Alive() == 2)
            {
                finalDuelFired = true;
                platform.ShrinkToCenter();
                Time.timeScale = 0.4f;                       // slow-mo sting
                Invoke(nameof(RestoreTime), 0.8f);
                // CameraDirector.ZoomFinalDuel() — scene_assembly stage
            }
        }

        void RestoreTime() => Time.timeScale = 1f;

        protected override void OnEliminated(int slot)
        {
            if (heroes.TryGetValue(slot, out var h) && h != null) Destroy(h.gameObject, 1.5f);
            ControllerGateway.Instance.AssignLayout("show_spectator");
        }

        int Alive() => heroes.Keys.Count(s => !IsEliminated(s));

        protected override bool WinConditionMet() => Alive() <= 1;
    }
}
