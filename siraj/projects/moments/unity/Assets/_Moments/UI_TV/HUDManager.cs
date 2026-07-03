using UnityEngine;
using UnityEngine.UI;
using Moments.Core;
using Moments.Minigames;

namespace Moments.UI_TV
{
    /// TV HUD binding layer: round timer, player score cards, hazard warning
    /// banner. Reads game state via events — never polls scene objects for
    /// truth (ui_ux law). Visual layout is authored in the scene_assembly
    /// stage; this class only feeds it.
    public sealed class HUDManager : MonoBehaviour
    {
        [Header("Bindings (wired in TV_Play scene)")]
        public Text timerText;                  // large center-top countdown
        public Text hazardBannerAr;             // telegraph standard, Arabic
        public Text hazardBannerEn;             // telegraph standard, English
        public Transform playerCardRow;         // horizontal card container

        MiniGameBase game;

        void Start()
        {
            game = FindAnyObjectByType<MiniGameBase>();
            PlayerRegistry.Instance.OnSlotChanged += RefreshCard;
            HideHazardWarning();
        }

        void OnDestroy()
        {
            if (PlayerRegistry.Instance != null)
                PlayerRegistry.Instance.OnSlotChanged -= RefreshCard;
        }

        void Update()
        {
            if (game == null || timerText == null) return;
            int s = Mathf.Max(0, Mathf.CeilToInt(game.TimeLeft));
            timerText.text = $"{s / 60}:{s % 60:00}";
            timerText.color = s <= 10 ? Color.red : Color.white;   // "final seconds" read
        }

        public void ShowHazardWarning(string ar, string en)
        {
            if (hazardBannerAr) { hazardBannerAr.text = ar; hazardBannerAr.enabled = true; }
            if (hazardBannerEn) { hazardBannerEn.text = en; hazardBannerEn.enabled = true; }
        }

        public void HideHazardWarning()
        {
            if (hazardBannerAr) hazardBannerAr.enabled = false;
            if (hazardBannerEn) hazardBannerEn.enabled = false;
        }

        void RefreshCard(PlayerSlot slot)
        {
            // scene_assembly stage instantiates one card prefab per slot under
            // playerCardRow and binds nickname/portrait/score/ready ring here.
            Debug.Log($"[HUD] card {slot.slot}: {slot.nickname} {slot.heroId} {slot.score}pts {slot.state}");
        }
    }
}
