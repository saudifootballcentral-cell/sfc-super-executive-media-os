#!/usr/bin/env python3
"""hero_refine.py <HeroName> <preview_task_id> — pay for Meshy refine
(textures/PBR) after Creative Director approval, download textured GLB,
render textured QA views."""
import json, os, sys, time, urllib.request

API = "https://api.meshy.ai/openapi"
KEY = os.environ["MESHY_API_KEY"]
OUT = "projects/moments/meshy"

def req(method, path, body=None):
    r = urllib.request.Request(API + path,
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read())

name, prev_id = sys.argv[1], sys.argv[2]
task = req("POST", "/v2/text-to-3d", {"mode": "refine", "preview_task_id": prev_id, "enable_pbr": True})
tid = task["result"]
print(f"[Meshy] {name} refine task {tid}", flush=True)
os.system(f"python3 os/engine/memory.py log meshy_history "
          f"'{json.dumps({'name': name, 'task_id': tid, 'kind': 'text-to-3d-refine', 'status': 'started', 'preview_task': prev_id})}' >/dev/null")

t0 = time.time()
while True:
    t = req("GET", f"/v2/text-to-3d/{tid}")
    st = t.get("status")
    print(f"[Meshy] {name} refine {int(time.time()-t0)}s {st} {t.get('progress','')}%", flush=True)
    if st == "SUCCEEDED": break
    if st in ("FAILED", "CANCELED"): sys.exit(f"[Meshy] {name} refine {st}: {t.get('task_error')}")
    if time.time() - t0 > 2400: sys.exit(f"[Meshy] {name} refine timeout")
    time.sleep(20)

glb = os.path.join(OUT, f"{name}.glb")
urllib.request.urlretrieve(t["model_urls"]["glb"], glb)
print(f"[Meshy] downloaded {glb} ({os.path.getsize(glb)//1024} KB)", flush=True)
os.system(f"python3 os/engine/memory.py log meshy_history "
          f"'{json.dumps({'name': name, 'task_id': tid, 'kind': 'text-to-3d-refine', 'status': 'SUCCEEDED', 'glb': glb})}' >/dev/null")

import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
lo = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
hi = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
h = hi - lo or 1
cam_d = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cam_d)
bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam
sun_d = bpy.data.lights.new("s", 'SUN'); sun_d.energy = 3
sun = bpy.data.objects.new("s", sun_d); bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), 0, math.radians(30))
w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.85, .88, .92, 1)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 768
mid = lo + h / 2
for label, ang in (("front", math.radians(-90)), ("threequarter", math.radians(-45))):
    cam.location = (2.6 * h * math.cos(ang), 2.6 * h * math.sin(ang), mid + h * 0.15)
    d = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(d)
    d.location = (0, 0, mid)
    tr = cam.constraints.new('TRACK_TO'); tr.target = d
    sc.render.filepath = os.path.join(OUT, f"{name}_refined_{label}.png")
    bpy.ops.render.render(write_still=True)
    cam.constraints.remove(tr)
print(f"[Meshy] {name} textured QA renders done", flush=True)
