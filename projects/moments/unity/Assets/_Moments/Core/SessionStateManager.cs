using System;
using UnityEngine;

namespace Moments.Core
{
    public enum Phase { Attract, Lobby, MiniGameLoad, MiniGame, Results, Podium }

    /// Single source of truth for the session. Nothing changes phase except
    /// through Advance()/SetPhase(); everything else subscribes.
    public sealed class SessionStateManager : MonoBehaviour
    {
        public static SessionStateManager Instance { get; private set; }

        public Phase CurrentPhase { get; private set; } = Phase.Attract;
        public event Action<Phase, Phase> OnPhaseChanged;   // (from, to)

        [Header("Session settings")]
        public int roundsPerSession = 1;                    // slice: 1 (Polar Push)
        public int roundsPlayed;

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        public void SetPhase(Phase next)
        {
            if (next == CurrentPhase) return;
            if (!IsLegalTransition(CurrentPhase, next))
            {
                Debug.LogError($"[Session] illegal transition {CurrentPhase} -> {next}");
                return;
            }
            var prev = CurrentPhase;
            CurrentPhase = next;
            Debug.Log($"[Session] {prev} -> {next}");
            OnPhaseChanged?.Invoke(prev, next);
        }

        static bool IsLegalTransition(Phase from, Phase to) => (from, to) switch
        {
            (Phase.Attract, Phase.Lobby) => true,
            (Phase.Lobby, Phase.MiniGameLoad) => true,
            (Phase.MiniGameLoad, Phase.MiniGame) => true,
            (Phase.MiniGame, Phase.Results) => true,
            (Phase.Results, Phase.MiniGameLoad) => true,   // next round
            (Phase.Results, Phase.Podium) => true,          // session end
            (Phase.Podium, Phase.Lobby) => true,            // rematch
            (Phase.Podium, Phase.Attract) => true,          // back to attract
            (_, Phase.Attract) => true,                     // hard reset always legal
            _ => false,
        };

        /// Round finished: Results -> next round or Podium.
        public void OnRoundComplete()
        {
            roundsPlayed++;
            SetPhase(Phase.Results);
        }

        public void AdvanceFromResults()
            => SetPhase(roundsPlayed >= roundsPerSession ? Phase.Podium : Phase.MiniGameLoad);
    }
}
