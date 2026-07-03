using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Moments.Core;

namespace Moments.UI_TV
{
    [System.Serializable]
    public struct Standing
    {
        public int slot;
        public string nickname;
        public string heroId;
        public int score;
        public int place;        // 1-based
        public string medal;     // "gold" | "silver" | "bronze" | ""
    }

    /// Turns PlayerRegistry scores into ranked standings for TV_Results and
    /// the TV_Finale podium. Pure data — presentation binds to this.
    public static class ResultsAggregator
    {
        public static List<Standing> Standings()
        {
            var ranked = PlayerRegistry.Instance.Snapshot()
                .OrderByDescending(p => p.score).ToList();
            var outp = new List<Standing>();
            string[] medals = { "gold", "silver", "bronze" };
            for (int i = 0; i < ranked.Count; i++)
                outp.Add(new Standing
                {
                    slot = ranked[i].slot,
                    nickname = ranked[i].nickname,
                    heroId = ranked[i].heroId,
                    score = ranked[i].score,
                    place = i + 1,
                    medal = i < 3 ? medals[i] : "",
                });
            return outp;
        }

        public static Standing Champion() => Standings().First();
    }
}
