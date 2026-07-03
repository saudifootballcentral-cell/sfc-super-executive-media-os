using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Moments.Core
{
    public enum SlotState { Empty, Joining, Ready, Playing, DisconnectedGrace, Bot }

    [Serializable]
    public sealed class PlayerSlot
    {
        public int slot;                  // 0..7
        public string playerId;           // stable per device (reconnect key)
        public string nickname;
        public string heroId;             // CharacterDefinition.heroId
        public SlotState state;
        public bool isBot;
        public int score;                 // cumulative session points
        public float graceUntil;          // Time.unscaledTime deadline while disconnected
        public Color color = Color.white; // hero color, stamps HUD + phone frame
    }

    /// Owns the 8 slots. The ONLY writer of slot state. Iterate via Snapshot()
    /// (copies — GDD law: no ConcurrentModification during join/leave storms).
    public sealed class PlayerRegistry : MonoBehaviour
    {
        public static PlayerRegistry Instance { get; private set; }

        public const int MaxPlayers = 8;
        public const float ReconnectGraceSeconds = 10f;
        public int botsFillTo = 4;        // spec: botsFillTo

        readonly PlayerSlot[] slots = new PlayerSlot[MaxPlayers];
        public event Action<PlayerSlot> OnSlotChanged;

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
            for (int i = 0; i < MaxPlayers; i++) slots[i] = new PlayerSlot { slot = i, state = SlotState.Empty };
        }

        public List<PlayerSlot> Snapshot() => slots.Select(s => s).Where(s => s.state != SlotState.Empty).ToList();
        public PlayerSlot Get(int slot) => slots[slot];

        public PlayerSlot Join(string playerId, string nickname)
        {
            // reconnect path: same playerId within grace reclaims slot + hero + score
            var back = slots.FirstOrDefault(s => s.playerId == playerId && s.state == SlotState.DisconnectedGrace);
            if (back != null) { back.state = SlotState.Joining; Changed(back); return back; }

            var free = slots.FirstOrDefault(s => s.state == SlotState.Empty)
                       ?? slots.FirstOrDefault(s => s.isBot);       // humans evict bots
            if (free == null) return null;                          // room full
            if (free.isBot) free.score = 0;                         // bot's points don't transfer
            free.playerId = playerId; free.nickname = nickname;
            free.isBot = false; free.heroId = null;
            free.state = SlotState.Joining;
            Changed(free);
            return free;
        }

        public bool LockHero(int slot, string heroId, bool allowDuplicates = false)
        {
            if (!allowDuplicates && slots.Any(s => s.heroId == heroId && s.slot != slot && s.state != SlotState.Empty))
                return false;
            slots[slot].heroId = heroId;
            Changed(slots[slot]);
            return true;
        }

        public void SetReady(int slot, bool ready)
        {
            slots[slot].state = ready ? SlotState.Ready : SlotState.Joining;
            Changed(slots[slot]);
        }

        public bool AllHumansReady()
        {
            var humans = slots.Where(s => !s.isBot && s.state != SlotState.Empty && s.state != SlotState.DisconnectedGrace).ToList();
            return humans.Count > 0 && humans.All(s => s.state == SlotState.Ready);
        }

        /// Transport says a phone dropped: start grace; bot takes over when it expires (polled by Tick).
        public void OnDisconnected(string playerId)
        {
            var s = slots.FirstOrDefault(x => x.playerId == playerId);
            if (s == null) return;
            s.state = SlotState.DisconnectedGrace;
            s.graceUntil = Time.unscaledTime + ReconnectGraceSeconds;
            Changed(s);
        }

        void Update()
        {
            foreach (var s in slots)
                if (s.state == SlotState.DisconnectedGrace && Time.unscaledTime > s.graceUntil)
                { s.isBot = true; s.state = SlotState.Bot; Changed(s); }   // AI takeover, slot kept
        }

        /// Called on match start: pad with bots up to botsFillTo.
        public void FillWithBots(System.Func<int, string> pickHero)
        {
            int active = slots.Count(s => s.state != SlotState.Empty);
            for (int i = 0; active < botsFillTo && i < MaxPlayers; i++)
            {
                var s = slots[i];
                if (s.state != SlotState.Empty) continue;
                s.isBot = true; s.state = SlotState.Bot;
                s.playerId = $"bot-{i}"; s.nickname = $"BOT {i + 1}";
                s.heroId = pickHero(i);
                Changed(s); active++;
            }
        }

        public void AddScore(int slot, int points) { slots[slot].score += points; Changed(slots[slot]); }

        void Changed(PlayerSlot s) => OnSlotChanged?.Invoke(s);
    }
}
