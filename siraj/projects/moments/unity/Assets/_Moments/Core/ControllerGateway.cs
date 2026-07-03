using System;
using System.Collections.Generic;
using UnityEngine;

namespace Moments.Core
{
    /// One frame of intent from a controller (phone or bot). Phones send this
    /// as JSON over WebSocket; bots write it directly. Host-authoritative:
    /// this is INTENT only — consequences are resolved by gameplay systems.
    [Serializable]
    public struct PlayerInput
    {
        public int seq;          // client inputSequence for prediction acks
        public float moveX;      // -1..1
        public float moveY;      // -1..1
        public bool dash;
    }

    /// Normalizes all input sources behind one API and pushes UI layout
    /// commands back to phones. Gameplay reads GetInput(slot); it never
    /// talks to the transport directly.
    public sealed class ControllerGateway : MonoBehaviour
    {
        public static ControllerGateway Instance { get; private set; }

        readonly PlayerInput[] latest = new PlayerInput[PlayerRegistry.MaxPlayers];
        readonly int[] lastProcessedSeq = new int[PlayerRegistry.MaxPlayers];

        public event Action<int, string> OnUICommand;   // (slot, layoutJson) -> transport

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        /// Transport/bot layer feeds intent here. Clamped defensively — the
        /// host never trusts client magnitudes.
        public void SubmitInput(int slot, PlayerInput input)
        {
            input.moveX = Mathf.Clamp(input.moveX, -1f, 1f);
            input.moveY = Mathf.Clamp(input.moveY, -1f, 1f);
            if (input.seq >= latest[slot].seq || latest[slot].seq - input.seq > 1000)
                latest[slot] = input;
        }

        public PlayerInput GetInput(int slot) => latest[slot];

        /// Gameplay marks an input consumed so snapshots can ack it
        /// (client-side prediction contract: lastProcessedInputSequence).
        public void MarkProcessed(int slot) => lastProcessedSeq[slot] = latest[slot].seq;
        public int LastProcessedSeq(int slot) => lastProcessedSeq[slot];

        public void ClearAll()
        {
            for (int i = 0; i < latest.Length; i++) { latest[i] = default; lastProcessedSeq[i] = 0; }
        }

        /// Swap every phone to a mini-game layout (e.g. "show_joystick").
        public void AssignLayout(string layout, string promptsAr = "", string promptsEn = "")
        {
            string json = JsonUtility.ToJson(new UICommand { cmd = layout, ar = promptsAr, en = promptsEn });
            foreach (var s in PlayerRegistry.Instance.Snapshot())
                if (!s.isBot) OnUICommand?.Invoke(s.slot, json);
        }

        [Serializable] struct UICommand { public string cmd; public string ar; public string en; }
    }
}
