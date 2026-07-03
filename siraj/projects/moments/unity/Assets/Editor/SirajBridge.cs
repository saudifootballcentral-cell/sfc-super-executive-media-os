// SirajBridge.cs — static helpers callable via MCP (execute_menu / run C#).
using UnityEditor;
using UnityEngine;

public static class SirajBridge
{
    // FBX -> prefab in Assets/Prefabs/
    public static string MakePrefab(string fbxPath)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(fbxPath);
        if (src == null) { Debug.LogError($"[Siraj] not found: {fbxPath}"); return null; }
        var inst = (GameObject)PrefabUtility.InstantiatePrefab(src);
        string dir = "Assets/Prefabs";
        if (!AssetDatabase.IsValidFolder(dir)) AssetDatabase.CreateFolder("Assets", "Prefabs");
        string outPath = $"{dir}/{src.name}.prefab";
        PrefabUtility.SaveAsPrefabAsset(inst, outPath);
        Object.DestroyImmediate(inst);
        Debug.Log($"[Siraj] prefab -> {outPath}");
        return outPath;
    }

    public static GameObject PlaceInActiveScene(string assetPath, Vector3 pos)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
        if (src == null) { Debug.LogError($"[Siraj] not found: {assetPath}"); return null; }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(src);
        go.transform.position = pos;
        Debug.Log($"[Siraj] placed {go.name} at {pos}");
        return go;
    }

    // Quick sanity scene: light + camera + ground + the asset in front of camera.
    public static void PreviewAsset(string assetPath)
    {
        var light = new GameObject("Sun").AddComponent<Light>();
        light.type = LightType.Directional;
        light.transform.rotation = Quaternion.Euler(50, -30, 0);

        var cam = new GameObject("PreviewCam").AddComponent<Camera>();
        cam.transform.position = new Vector3(0, 2, -5);
        cam.transform.LookAt(Vector3.up);

        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.transform.localScale = Vector3.one * 3;

        PlaceInActiveScene(assetPath, Vector3.zero);
    }
}
