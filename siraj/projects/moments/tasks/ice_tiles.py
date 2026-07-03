#!/usr/bin/env python3
"""
ice_tiles.py — Polar Push ice tiles (3 damage states), procedural.

Spec: GameSpecs/Moments_VerticalSlice.json — exact dims, budgets 400/600/800 tris.
Hex tile: flat-top hexagon, circumradius 1.0 m, thickness 0.4 m, pivot at
top-center (tiles sit flush; IcePlatformManager drops them by Y).

Run (either mode):
  blender -b -P ice_tiles.py -- IceTile_Solid
  python3  ice_tiles.py IceTile_Solid          (bpy-as-module)
Exports: $SIRAJ_EXPORTS/<Name>.fbx  (default ~/blender/exports)
"""
import math
import os
import random
import sys

import bpy

R = 1.0          # hex circumradius (m)
T = 0.4          # thickness (m)


def _args():
    av = sys.argv
    return av[av.index("--") + 1:] if "--" in av else av[1:]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def hex_prism(name, r=R, t=T):
    verts, faces = [], []
    top = [(r * math.cos(a), r * math.sin(a), 0.0)
           for a in (math.radians(60 * i) for i in range(6))]
    bot = [(x, y, -t) for x, y, _ in top]
    verts = top + bot
    faces.append([0, 1, 2, 3, 4, 5])                      # top
    faces.append([11, 10, 9, 8, 7, 6])                    # bottom
    for i in range(6):
        j = (i + 1) % 6
        faces.append([i, 6 + i, 6 + j, j])                # sides
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def crack_top(obj, seed, levels, jitter, gap=0.0):
    """Subdivide the top face and jitter it — readable crack/damage look."""
    import bmesh
    rng = random.Random(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    top_faces = [f for f in bm.faces if f.normal.z > 0.5]
    bmesh.ops.subdivide_edges(
        bm, edges=list({e for f in top_faces for e in f.edges}),
        cuts=levels, use_grid_fill=True)
    for v in bm.verts:
        if v.co.z > -0.01 and abs(v.co.x) < R * 0.95 and abs(v.co.y) < R * 0.95:
            v.co.z -= rng.uniform(0.0, jitter)
            v.co.x += rng.uniform(-gap, gap)
            v.co.y += rng.uniform(-gap, gap)
    bm.to_mesh(obj.data)
    bm.free()


def fragments(obj, seed):
    """Breaking state: split into 6 wedges, tilt/sink each — about to drop."""
    import bmesh
    rng = random.Random(seed)
    base = obj.data
    col = bpy.context.collection
    out = []
    for i in range(6):
        a0, a1 = math.radians(60 * i), math.radians(60 * (i + 1))
        verts = [(0, 0, 0),
                 (R * math.cos(a0), R * math.sin(a0), 0),
                 (R * math.cos(a1), R * math.sin(a1), 0)]
        verts += [(x, y, -T) for x, y, _ in verts]
        faces = [[0, 1, 2], [5, 4, 3], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]]
        m = bpy.data.meshes.new(f"frag{i}")
        m.from_pydata(verts, [], faces)
        m.update()
        o = bpy.data.objects.new(f"frag{i}", m)
        col.objects.link(o)
        o.rotation_euler = (rng.uniform(-0.09, 0.09), rng.uniform(-0.09, 0.09), 0)
        o.location.z = -rng.uniform(0.01, 0.06)
        out.append(o)
    bpy.data.objects.remove(obj)
    for o in out:
        o.select_set(True)
    bpy.context.view_layer.objects.active = out[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = base.name
    return joined


def tri_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def export(obj, name):
    exports = os.environ.get("SIRAJ_EXPORTS",
                             os.path.expanduser("~/blender/exports"))
    os.makedirs(exports, exist_ok=True)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(exports, f"{name}.fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True,
                             axis_forward='-Z', axis_up='Y',
                             apply_scale_options='FBX_SCALE_ALL',
                             add_leaf_bones=False)
    print(f"[Siraj] exported {path} ({tri_count(obj)} tris)")
    return path


BUILDERS = {
    "IceTile_Solid":    lambda: hex_prism("IceTile_Solid"),
    "IceTile_Cracked":  lambda: (lambda o: (crack_top(o, 7, 3, 0.05), o)[1])(hex_prism("IceTile_Cracked")),
    "IceTile_Breaking": lambda: fragments(hex_prism("IceTile_Breaking"), 13),
}

BUDGETS = {"IceTile_Solid": 400, "IceTile_Cracked": 600, "IceTile_Breaking": 800}

if __name__ == "__main__":
    names = _args() or list(BUILDERS)
    for name in names:
        if name not in BUILDERS:
            sys.exit(f"unknown tile '{name}' — valid: {', '.join(BUILDERS)}")
        reset()
        obj = BUILDERS[name]()
        obj.name = name
        n = tri_count(obj)
        assert n <= BUDGETS[name], f"{name}: {n} tris exceeds budget {BUDGETS[name]}"
        export(obj, name)
