// SirajAssetPostprocessor.cs — auto-configures imports for the Siraj pipeline.
// Assets/Characters/*  -> Humanoid rig (Mecanim auto-map from bone names)
// Assets/Models/*      -> Generic rig; "_COL_" in mesh name -> MeshCollider
// Meshy FBX imports    -> extract embedded textures + materials once.
using UnityEditor;
using UnityEngine;

public class SirajAssetPostprocessor : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        var mi = (ModelImporter)assetImporter;
        mi.globalScale = 1f;
        mi.importCameras = false;
        mi.importLights = false;

        if (assetPath.Contains("Assets/Characters/"))
        {
            mi.animationType = ModelImporterAnimationType.Human;
            mi.autoGenerateAvatarMappingIfUnspecified = true;
        }
        else if (assetPath.Contains("Assets/Models/"))
        {
            mi.animationType = ModelImporterAnimationType.Generic;
        }

        // Meshy exports embed textures in the FBX — extract them once.
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        mi.ExtractTextures(System.IO.Path.GetDirectoryName(assetPath));
    }

    void OnPostprocessGameObjectWithUserProperties(
        GameObject go, string[] names, object[] values) { }

    void OnPostprocessModel(GameObject g)
    {
        foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            if (mf.name.Contains("_COL_"))
            {
                var mc = mf.gameObject.AddComponent<MeshCollider>();
                mc.sharedMesh = mf.sharedMesh;
                mf.GetComponent<MeshRenderer>().enabled = false;
            }
        Debug.Log($"[Siraj] imported {assetPath}");
    }
}
