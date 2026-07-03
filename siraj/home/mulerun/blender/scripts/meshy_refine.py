# meshy_refine.py — run inside headless Blender.
# Imports a Meshy GLB, normalizes it for Unity, optionally rigs it with a
# Mecanim-named skeleton (auto weights), and exports FBX with Unity axes.
#
# Called by siraj-build.sh:
#   blender --factory-startup -b -P meshy_refine.py -- \
#       <input.glb> <Name> <polybudget> [--rig]
#
# Output: ~/blender/exports/<Name>.fbx
import bpy, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, NAME = argv[0], argv[1]
POLY_BUDGET = int(argv[2]) if len(argv) > 2 else 15000
RIG = "--rig" in argv
EXPORT_DIR = os.path.expanduser("~/blender/exports")

# ---- clean scene & import -------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("No mesh in GLB")

# Join into one object, apply transforms
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = NAME
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ---- ground the pivot: feet at Z=0, centered on X/Y -----------------------
mn = [min(v[i] for v in obj.bound_box) for i in range(3)]
mx = [max(v[i] for v in obj.bound_box) for i in range(3)]
obj.location = (-(mn[0]+mx[0])/2, -(mn[1]+mx[1])/2, -mn[2])
bpy.ops.object.transform_apply(location=True)

# ---- decimate to poly budget ----------------------------------------------
tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
if tris > POLY_BUDGET:
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = POLY_BUDGET / tris
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"[Siraj] decimated {tris} -> {POLY_BUDGET} tris")

# ---- optional Mecanim rig ---------------------------------------------------
if RIG:
    h = mx[2] - mn[2]  # character height
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = NAME + "_Armature"
    eb = arm.data.edit_bones
    eb.remove(eb[0])

    def bone(name, head, tail, parent=None):
        b = eb.new(name)
        b.head, b.tail = head, tail
        if parent: b.parent = eb[parent]
        return b

    # Minimal Mecanim-mappable humanoid (proportions from mesh height)
    bone("Hips",  (0,0,.50*h), (0,0,.58*h))
    bone("Spine", (0,0,.58*h), (0,0,.70*h), "Hips")
    bone("Chest", (0,0,.70*h), (0,0,.82*h), "Spine")
    bone("Neck",  (0,0,.82*h), (0,0,.88*h), "Chest")
    bone("Head",  (0,0,.88*h), (0,0,1.0*h), "Neck")
    for side, s in (("Left", 1), ("Right", -1)):
        bone(f"{side}Shoulder", (s*.05*h,0,.80*h), (s*.10*h,0,.80*h), "Chest")
        bone(f"{side}UpperArm", (s*.10*h,0,.80*h), (s*.25*h,0,.80*h), f"{side}Shoulder")
        bone(f"{side}LowerArm", (s*.25*h,0,.80*h), (s*.40*h,0,.80*h), f"{side}UpperArm")
        bone(f"{side}Hand",     (s*.40*h,0,.80*h), (s*.46*h,0,.80*h), f"{side}LowerArm")
        bone(f"{side}UpperLeg", (s*.08*h,0,.50*h), (s*.08*h,0,.28*h), "Hips")
        bone(f"{side}LowerLeg", (s*.08*h,0,.28*h), (s*.08*h,0,.06*h), f"{side}UpperLeg")
        bone(f"{side}Foot",     (s*.08*h,0,.06*h), (s*.08*h,-.10*h,.02*h), f"{side}LowerLeg")
    bpy.ops.object.mode_set(mode="OBJECT")

    # Auto weights
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    print("[Siraj] rigged with Mecanim bone names")

# ---- export FBX (Unity axes) ------------------------------------------------
os.makedirs(EXPORT_DIR, exist_ok=True)
out = os.path.join(EXPORT_DIR, NAME + ".fbx")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.fbx(
    filepath=out, use_selection=True,
    axis_forward="-Z", axis_up="Y", global_scale=1.0,
    bake_space_transform=True, add_leaf_bones=False,
    path_mode="COPY", embed_textures=True)
print(f"[Siraj] exported {out}")
