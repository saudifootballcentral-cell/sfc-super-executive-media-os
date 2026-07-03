using System;
using System.Collections.Generic;
using UnityEngine;
using Moments.Core;

namespace Moments.Minigames
{
    public enum RoundState { Setup, Countdown, Playing, RoundEnd }

    /// Contract every mini-game inherits (bible: MiniGameBase). Owns the
    /// inner round state machine (Setup → Countdown → Playing → RoundEnd),
    /// the round timer, and placement scoring. Subclasses implement the verbs.
    public abstract class MiniGameBase : MonoBehaviour
    {
        [Header("Round")]
        public float roundSeconds = 120f;
        public float countdownSeconds = 3f;

        public RoundState State { get; private set; } = RoundState.Setup;
        public float TimeLeft { get; private set; }
        public event Action<RoundState> OnStateChanged;

        protected readonly List<int> eliminationOrder = new();   // slots, first out first
        float stateT;
        float snapshotT;

        protected abstract string ControllerLayout { get; }      // e.g. "show_joystick"
        protected abstract void OnSetup(List<PlayerSlot> players);
        protected abstract void OnPlayingTick();
        protected abstract bool WinConditionMet();

        public void Begin()
        {
            var players = PlayerRegistry.Instance.Snapshot();
            PlayerRegistry.Instance.FillWithBots(i => DefaultBotHero(i));
            players = PlayerRegistry.Instance.Snapshot();
            eliminationOrder.Clear();
            TimeLeft = roundSeconds;
            OnSetup(players);
            ControllerGateway.Instance.AssignLayout(ControllerLayout);
            SetState(RoundState.Countdown);
        }

        protected virtual string DefaultBotHero(int i)
            => new[] { "byte", "nova", "orbit", "pop" }[i % 4];

        void Update()
        {
            stateT += Time.deltaTime;
            switch (State)
            {
                case RoundState.Countdown:
                    if (stateT >= countdownSeconds) SetState(RoundState.Playing);
                    break;
                case RoundState.Playing:
                    TimeLeft -= Time.deltaTime;
                    OnPlayingTick();
                    ThrottledSnapshot();
                    if (WinConditionMet() || TimeLeft <= 0f) EndRound();
                    break;
            }
        }

        void ThrottledSnapshot()   // 1 Hz, never per-frame (GDD network law)
        {
            snapshotT += Time.deltaTime;
            if (snapshotT < 1f) return;
            snapshotT = 0f;
            FindAnyObjectByType<Core.Net.MomentsWebSocketServer>()
                ?.BroadcastSnapshot(Mathf.CeilToInt(TimeLeft));
        }

        protected void Eliminate(int slot)
        {
            if (eliminationOrder.Contains(slot)) return;
            eliminationOrder.Add(slot);
            OnEliminated(slot);
        }
        protected virtual void OnEliminated(int slot) { }
        protected bool IsEliminated(int slot) => eliminationOrder.Contains(slot);

        void EndRound()
        {
            SetState(RoundState.RoundEnd);
            AwardPlacementPoints();
            SessionStateManager.Instance.OnRoundComplete();
        }

        /// Survivors rank above the eliminated; later eliminations rank higher.
        protected virtual void AwardPlacementPoints()
        {
            var players = PlayerRegistry.Instance.Snapshot();
            var ranked = new List<int>();
            foreach (var p in players) if (!IsEliminated(p.slot)) ranked.Add(p.slot);
            for (int i = eliminationOrder.Count - 1; i >= 0; i--) ranked.Add(eliminationOrder[i]);
            int[] points = { 100, 70, 50, 35, 25, 15, 10, 5 };
            for (int i = 0; i < ranked.Count && i < points.Length; i++)
                PlayerRegistry.Instance.AddScore(ranked[i], points[i]);
        }

        protected void SetState(RoundState s)
        {
            if (s == State) return;
            State = s; stateT = 0f;
            Debug.Log($"[Round] -> {s}");
            OnStateChanged?.Invoke(s);
        }
    }
}
