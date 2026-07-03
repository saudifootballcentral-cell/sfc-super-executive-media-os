using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Moments.Minigames.PolarPush
{
    public enum TileState { Solid, Cracked, Breaking, Gone }

    /// Owns the hex tile platform: builds the grid from the three tile
    /// prefabs (IceTile_Solid/Cracked/Breaking from the Blender pipeline),
    /// collapses the outer rings over time with a Fisher-Yates shuffle
    /// (GDD-specified), and answers spatial queries for bots and Final Duel.
    public sealed class IcePlatformManager : MonoBehaviour
    {
        [Header("Prefabs (from siraj-build.sh imports)")]
        public GameObject solidPrefab;
        public GameObject crackedPrefab;
        public GameObject breakingPrefab;

        [Header("Layout — must match tasks/ice_tiles.py dims")]
        public int rings = 4;                 // 61 tiles
        public float hexRadius = 1.0f;

        [Header("Collapse pacing")]
        public float firstCollapseAt = 20f;   // seconds into Playing
        public float secondsPerTile = 1.2f;
        public float crackWarnSeconds = 2f;   // Solid->Cracked->Breaking telegraph
        public int finalDuelKeepRing = 1;     // rings kept when Final Duel fires

        sealed class Tile
        {
            public Vector2Int ax;             // axial coords (q, r)
            public int ring;
            public TileState state;
            public GameObject go;
            public Vector3 pos;
        }

        readonly Dictionary<Vector2Int, Tile> tiles = new();
        readonly Queue<Tile> collapseQueue = new();
        float clock, nextCollapse;
        bool collapsing;

        public event Action<Vector3> OnTileDropped;

        public void Build(int seed)
        {
            foreach (var t in tiles.Values) if (t.go) Destroy(t.go);
            tiles.Clear(); collapseQueue.Clear();
            clock = 0; collapsing = false;

            for (int q = -rings; q <= rings; q++)
                for (int r = Mathf.Max(-rings, -q - rings); r <= Mathf.Min(rings, -q + rings); r++)
                {
                    int ring = Mathf.Max(Mathf.Abs(q), Mathf.Abs(r), Mathf.Abs(-q - r));
                    var pos = new Vector3(hexRadius * 1.5f * q, 0f,
                                          hexRadius * Mathf.Sqrt(3f) * (r + q / 2f));
                    var t = new Tile { ax = new Vector2Int(q, r), ring = ring, state = TileState.Solid, pos = pos };
                    t.go = Instantiate(solidPrefab, pos, Quaternion.identity, transform);
                    tiles[t.ax] = t;
                }

            // Fisher-Yates per ring, outermost rings first (GDD)
            var rng = new System.Random(seed);
            for (int ring = rings; ring >= 1; ring--)
            {
                var ringTiles = tiles.Values.Where(t => t.ring == ring).ToArray();
                for (int i = ringTiles.Length - 1; i > 0; i--)
                {
                    int j = rng.Next(i + 1);
                    (ringTiles[i], ringTiles[j]) = (ringTiles[j], ringTiles[i]);
                }
                foreach (var t in ringTiles) collapseQueue.Enqueue(t);
            }
            nextCollapse = firstCollapseAt;
        }

        public void Tick(float dt)
        {
            clock += dt;
            if (clock >= nextCollapse && collapseQueue.Count > 0)
            {
                nextCollapse = clock + secondsPerTile;
                StartCoroutine(Collapse(collapseQueue.Dequeue()));
            }
        }

        System.Collections.IEnumerator Collapse(Tile t)
        {
            if (t.state != TileState.Solid) yield break;
            Swap(t, crackedPrefab, TileState.Cracked);
            yield return new WaitForSeconds(crackWarnSeconds);
            Swap(t, breakingPrefab, TileState.Breaking);
            yield return new WaitForSeconds(crackWarnSeconds * 0.5f);
            Destroy(t.go);
            t.go = null; t.state = TileState.Gone;
            OnTileDropped?.Invoke(t.pos);
        }

        void Swap(Tile t, GameObject prefab, TileState s)
        {
            if (t.go) Destroy(t.go);
            t.go = Instantiate(prefab, t.pos, Quaternion.identity, transform);
            t.state = s;
        }

        /// Final Duel: everything outside keepRing drops fast.
        public void ShrinkToCenter()
        {
            foreach (var t in tiles.Values.Where(t => t.ring > finalDuelKeepRing && t.state != TileState.Gone))
                StartCoroutine(Collapse(t));
            collapseQueue.Clear();
        }

        // ---- spatial queries -------------------------------------------------

        public TileState StateAt(Vector3 world)
        {
            var t = Nearest(world);
            return t == null || Vector3.Distance(world, t.pos) > hexRadius ? TileState.Gone : t.state;
        }

        public Vector3? NearestSafePoint(Vector3 world)
        {
            var safe = tiles.Values.Where(t => t.state == TileState.Solid).ToList();
            if (safe.Count == 0) return null;
            return safe.OrderBy(t => (t.pos - world).sqrMagnitude).First().pos;
        }

        Tile Nearest(Vector3 world)
        {
            Tile best = null; float bd = float.MaxValue;
            foreach (var t in tiles.Values)
            {
                if (t.state == TileState.Gone) continue;
                float d = (t.pos - world).sqrMagnitude;
                if (d < bd) { bd = d; best = t; }
            }
            return best;
        }
    }
}
