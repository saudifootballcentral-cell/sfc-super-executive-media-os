#!/usr/bin/env python3
"""
arena_rim.py — Polar Push arena rim: visible snow-bank ring + _COL_ wall.

The rim rings the tile platform (platform radius ~9 m for a 5-ring hex grid).
Visible mesh: low-poly banked ring. Collider: simple cylinder wall named
ArenaRim_COL — SirajAssetPostprocessor turns any *_COL_* mesh into a
MeshCollider and hides its renderer.

Budget: 2000 tris total. Pivot at arena center, Y-up for Unity.
Run:  blender -b -P arena_rim.py -- ArenaRim   |   python3 arena_rim.py
"""
import math
import os
import random
import sys

import bpy

R_IN, R_OUT, H, SEG = 9.0, 10.4, 1.1, 48


def _args():
    av = sys.argv
    return av[av.index("--") + 1:] if "--" in av else av[1:]


def ring(name, r_in, r_out, h, seg, jitter=0.0, seed=5):
    rng = random.Random(seed)
    verts, faces = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        j = 1.0 + (rng.uniform(-jitter, jitter) if jitter else 0.0)
        verts += [
            (r_in * math.cos(a), r_in * math.sin(a), 0.0),                    # 0 inner base
            (r_in * math.cos(a) * 1.02, r_in * math.sin(a) * 1.02, h * 0.85 * j),  # 1 inner top
            (r_out * math.cos(a) * j, r_out * math.sin(a) * j, h * j),        # 2 crest
            (r_out * math.cos(a) * 1.08, r_out * math.sin(a) * 1.08, 0.0),    # 3 outer base
        ]
    n = 4
    for i in range(seg):
        k, m = i * n, ((i + 1) % seg) * n
        for a, b in ((0, 1), (1, 2), (2, 3)):
            faces.append([k + a, m + a, m + b, k + b])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def wall(name, r, h, seg):
    verts, faces = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        verts += [(r * math.cos(a), r * math.sin(a), -0.5),
                  (r * math.cos(a), r * math.sin(a), h)]
    for i in range(seg):
        k, m = i * 2, ((i + 1) % seg) * 2
        faces.append([k, m, m + 1, k + 1])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def tri_count(objs):
    total = 0
    for o in objs:
        o.data.calc_loop_triangles()
        total += len(o.data.loop_triangles)
    return total


if __name__ == "__main__":
    name = (_args() or ["ArenaRim"])[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    visible = ring(name, R_IN, R_OUT, H, SEG, jitter=0.06)
    col = wall(f"{name}_COL_", R_IN + 0.1, H * 2.0, 24)
    col.parent = visible
    n = tri_count([visible, col])
    assert n <= 2000, f"{n} tris exceeds budget 2000"
    exports = os.environ.get("SIRAJ_EXPORTS", os.path.expanduser("~/blender/exports"))
    os.makedirs(exports, exist_ok=True)
    for o in (visible, col):
        o.select_set(True)
    bpy.context.view_layer.objects.active = visible
    path = os.path.join(exports, f"{name}_COL.fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True,
                             axis_forward='-Z', axis_up='Y',
                             apply_scale_options='FBX_SCALE_ALL',
                             add_leaf_bones=False)
    print(f"[Siraj] exported {path} ({n} tris)")
