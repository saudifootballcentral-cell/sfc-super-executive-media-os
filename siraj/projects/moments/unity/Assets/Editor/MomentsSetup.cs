// MomentsSetup.cs — one-click bootstrap for the Moments vertical slice.
// Run the menu items IN ORDER on the Unity machine (or via MCP execute_menu):
//   Siraj/Moments/1 Verify Imports
//   Siraj/Moments/2 Create Character Definitions
//   Siraj/Moments/3 Build Boot Scene
//   Siraj/Moments/4 Build PolarPush Scene
// Each step logs [Siraj] lines — the stage-10/12 gate evidence.
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Moments.Core;
using Moments.Core.Net;
using Moments.Characters;
using Moments.Minigames.PolarPush;
using Moments.UI_TV;

public static class MomentsSetup
{
    // heroId, EN, AR, fantasy EN, color hex (GDD v1 canon)
    static readonly string[,] Heroes = {
        {"byte",    "Byte",    "بايت",    "The Digital Daredevil", "#00BFFF"},
        {"nova",    "Nova",    "نوفا",    "The Starhunter",        "#FFD700"},
        {"orbit",   "Orbit",   "أوربِت",  "The Gravity Ace",       "#00BFBF"},
        {"pop",     "Pop",     "بوب",     "The Chaos Maker",       "#FF3399"},
        {"striker", "Striker", "سترايكر", "The Lightning Athlete", "#99FF00"},
        {"sizzle",  "Sizzle",  "سيزل",    "The Fiery Blaze",       "#FF6600"},
        {"shade",   "Shade",   "شيد",     "The Shadow Ninja",      "#8000CC"},
        {"dusty",   "Dusty",   "داستي",   "The Earth Adventurer",  "#996633"},
    };

    static readonly string[] ArenaAssets = {
        "IceTile_Solid", "IceTile_Cracked", "IceTile_Breaking",
        "ArenaRim_COL", "Iceberg_A", "Iceberg_B" };

    [MenuItem("Siraj/Moments/1 Verify Imports")]
    public static void VerifyImports()
    {
        int ok = 0, bad = 0;
        foreach (var (path, humanoid) in AllAssets())
        {
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (go == null) { Debug.LogError($"[Siraj] MISSING {path}"); bad++; continue; }
            if (humanoid)
            {
                var mi = (ModelImporter)AssetImporter.GetAtPath(path);
                if (mi.animationType != ModelImporterAnimationType.Human)
                { Debug.LogError($"[Siraj] NOT HUMANOID {path}"); bad++; continue; }
            }
            ok++;
        }
        Debug.Log($"[Siraj] import verification: {ok} ok, {bad} bad — " +
                  (bad == 0 ? "GATE unity_import EVIDENCE: PASS" : "fix before gate"));
    }

    static System.Collections.Generic.IEnumerable<(string, bool)> AllAssets()
    {
        for (int i = 0; i < Heroes.GetLength(0); i++)
            yield return ($"Assets/Characters/{Heroes[i, 1]}.fbx", true);
        yield return ("Assets/Characters/HeroAnimationSet.fbx", true);
        foreach (var a in ArenaAssets)
            yield return ($"Assets/Models/Moments/{a}.fbx", false);
    }

    [MenuItem("Siraj/Moments/2 Create Character Definitions")]
    public static void CreateDefinitions()
    {
        const string dir = "Assets/_Moments/Characters/Definitions";
        Directory.CreateDirectory(dir);
        for (int i = 0; i < Heroes.GetLength(0); i++)
        {
            var def = ScriptableObject.CreateInstance<CharacterDefinition>();
            def.heroId = Heroes[i, 0];
            def.displayNameEn = Heroes[i, 1];
            def.displayNameAr = Heroes[i, 2];
            def.fantasyEn = Heroes[i, 3];
            ColorUtility.TryParseHtmlString(Heroes[i, 4], out var c);
            def.color = c;
            def.prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                $"Assets/Characters/{Heroes[i, 1]}.fbx");
            def.stats = CharacterStats.Identical;   // CD ruling: fair slice
            AssetDatabase.CreateAsset(def, $"{dir}/Hero_{Heroes[i, 1]}.asset");
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"[Siraj] created {Heroes.GetLength(0)} CharacterDefinitions in {dir}");
    }

    [MenuItem("Siraj/Moments/3 Build Boot Scene")]
    public static void BuildBootScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,
                                                NewSceneMode.Single);
        var core = new GameObject("MomentsCore");
        core.AddComponent<SessionStateManager>();
        core.AddComponent<PlayerRegistry>();
        core.AddComponent<ControllerGateway>();
        var net = new GameObject("Net");
        var ws = net.AddComponent<MomentsWebSocketServer>();
        ws.roomToken = System.Guid.NewGuid().ToString("N").Substring(0, 8);
        net.AddComponent<PhoneControllerServer>();
        Directory.CreateDirectory("Assets/_Moments/Scenes");
        EditorSceneManager.SaveScene(scene, "Assets/_Moments/Scenes/TV_Boot.unity");
        AddToBuild("Assets/_Moments/Scenes/TV_Boot.unity");
        Debug.Log("[Siraj] TV_Boot scene built (managers + dual servers)");
    }

    [MenuItem("Siraj/Moments/4 Build PolarPush Scene")]
    public static void BuildPolarPushScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,
                                                NewSceneMode.Single);
        // lighting per TECH_SPEC: 1 directional + gradient ambient, no bakes
        var sun = new GameObject("Sun").AddComponent<Light>();
        sun.type = LightType.Directional;
        sun.transform.rotation = Quaternion.Euler(45, -25, 0);
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(.55f, .75f, .95f);
        RenderSettings.ambientEquatorColor = new Color(.35f, .45f, .6f);
        RenderSettings.ambientGroundColor = new Color(.1f, .15f, .25f);

        var cam = new GameObject("ArenaCamera").AddComponent<Camera>();
        cam.transform.position = new Vector3(0, 15, -21);
        cam.transform.rotation = Quaternion.Euler(36, 0, 0);
        cam.tag = "MainCamera";

        var game = new GameObject("PolarPushGame");
        var platform = game.AddComponent<IcePlatformManager>();
        platform.solidPrefab = Prefab("Assets/Models/Moments/IceTile_Solid.fbx");
        platform.crackedPrefab = Prefab("Assets/Models/Moments/IceTile_Cracked.fbx");
        platform.breakingPrefab = Prefab("Assets/Models/Moments/IceTile_Breaking.fbx");
        var hazards = game.AddComponent<ArenaHazardSystem>();
        var pp = game.AddComponent<PolarPushGame>();
        pp.platform = platform;
        pp.hazards = hazards;
        pp.roster = LoadDefinitions();
        game.AddComponent<HUDManager>();

        SirajBridge.PlaceInActiveScene("Assets/Models/Moments/ArenaRim_COL.fbx", Vector3.zero);
        SirajBridge.PlaceInActiveScene("Assets/Models/Moments/Iceberg_A.fbx", new Vector3(14, -.45f, 7));
        SirajBridge.PlaceInActiveScene("Assets/Models/Moments/Iceberg_B.fbx", new Vector3(-13, -.45f, -9));

        EditorSceneManager.SaveScene(scene, "Assets/_Moments/Scenes/TV_Play_PolarPush.unity");
        AddToBuild("Assets/_Moments/Scenes/TV_Play_PolarPush.unity");
        Debug.Log("[Siraj] TV_Play_PolarPush scene built — enter Play Mode: " +
                  "game.Begin() spawns bots and the round runs (gate gameplay_systems evidence)");
    }

    static GameObject Prefab(string fbx)
    {
        var p = SirajBridge.MakePrefab(fbx);
        return AssetDatabase.LoadAssetAtPath<GameObject>(p);
    }

    static CharacterDefinition[] LoadDefinitions()
    {
        var guids = AssetDatabase.FindAssets("t:CharacterDefinition",
            new[] { "Assets/_Moments/Characters/Definitions" });
        var defs = new CharacterDefinition[guids.Length];
        for (int i = 0; i < guids.Length; i++)
            defs[i] = AssetDatabase.LoadAssetAtPath<CharacterDefinition>(
                AssetDatabase.GUIDToAssetPath(guids[i]));
        return defs;
    }

    static void AddToBuild(string scenePath)
    {
        var scenes = new System.Collections.Generic.List<EditorBuildSettingsScene>(
            EditorBuildSettings.scenes);
        if (scenes.FindIndex(s => s.path == scenePath) < 0)
        {
            scenes.Add(new EditorBuildSettingsScene(scenePath, true));
            EditorBuildSettings.scenes = scenes.ToArray();
        }
    }
}
