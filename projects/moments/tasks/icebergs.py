#!/usr/bin/env python3
"""
icebergs.py — background iceberg dressing (Iceberg_A, Iceberg_B).

Displaced low-poly icospheres, stretched and faceted — toy-like per the
style law. No colliders (background dressing outside the rim).
Budget: 1500 tris each. Pivot at waterline (z=0).

Run:  blender -b -P icebergs.py -- Iceberg_A   |   python3 icebergs.py
"""
import os
import random
import sys

import bpy


def _args():
    av = sys.argv
    return av[av.index("--") + 1:] if "--" in av else av[1:]


def iceberg(name, seed, scale=(2.2, 1.7, 2.8)):
    rng = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0)
    obj = bpy.context.active_object
    obj.name = name
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co.x *= scale[0] * (1 + rng.uniform(-0.25, 0.25))
        v.co.y *= scale[1] * (1 + rng.uniform(-0.25, 0.25))
        v.co.z *= scale[2] * (1 + rng.uniform(-0.15, 0.35))
        if v.co.z < -0.4:            # flatten below waterline
            v.co.z = -0.4
    bm.to_mesh(obj.data)
    bm.free()
    # facet + decimate to budget
    mod = obj.modifiers.new("dec", "DECIMATE")
    mod.ratio = 0.55
    bpy.ops.object.modifier_apply(modifier="dec")
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def tri_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


SEEDS = {"Iceberg_A": 21, "Iceberg_B": 42}

if __name__ == "__main__":
    names = _args() or list(SEEDS)
    exports = os.environ.get("SIRAJ_EXPORTS", os.path.expanduser("~/blender/exports"))
    os.makedirs(exports, exist_ok=True)
    for name in names:
        if name not in SEEDS:
            sys.exit(f"unknown iceberg '{name}' — valid: {', '.join(SEEDS)}")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = iceberg(name, SEEDS[name])
        n = tri_count(obj)
        assert n <= 1500, f"{name}: {n} tris exceeds budget 1500"
        for o in bpy.context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(exports, f"{name}.fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True,
                                 axis_forward='-Z', axis_up='Y',
                                 apply_scale_options='FBX_SCALE_ALL',
                                 add_leaf_bones=False)
        print(f"[Siraj] exported {path} ({n} tris)")
