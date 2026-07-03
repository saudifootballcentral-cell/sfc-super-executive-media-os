#!/usr/bin/env python3
"""hero_image3d.py <Name> <image_path> — Meshy image-to-3d from key art,
poll, download GLB, QA renders (Creative Director directive: art drives
the mesh)."""
import base64, json, os, sys, time, urllib.request

API = "https://api.meshy.ai/openapi"
KEY = os.environ["MESHY_API_KEY"]
OUT = "projects/moments/meshy"

def req(method, path, body=None):
    r = urllib.request.Request(API + path,
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())

name, img_path = sys.argv[1], sys.argv[2]
with open(img_path, "rb") as f:
    uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()
task = req("POST", "/v1/image-to-3d", {
    "image_url": uri, "enable_pbr": True, "should_remesh": True,
    "should_texture": True, "topology": "triangle", "target_polycount": 15000})
tid = task["result"]
print(f"[Meshy] {name} image-to-3d task {tid}", flush=True)
os.system(f"python3 os/engine/memory.py log meshy_history "
          f"'{json.dumps({'name': name + '_img', 'task_id': tid, 'kind': 'image-to-3d', 'status': 'started', 'source': img_path})}' >/dev/null")

t0 = time.time()
while True:
    t = req("GET", f"/v1/image-to-3d/{tid}")
    st = t.get("status")
    print(f"[Meshy] {name} img3d {int(time.time()-t0)}s {st} {t.get('progress','')}%", flush=True)
    if st == "SUCCEEDED": break
    if st in ("FAILED", "CANCELED"): sys.exit(f"[Meshy] {name} img3d {st}: {t.get('task_error')}")
    if time.time() - t0 > 2400: sys.exit("timeout")
    time.sleep(20)

glb = os.path.join(OUT, f"{name}_img.glb")
urllib.request.urlretrieve(t["model_urls"]["glb"], glb)
print(f"[Meshy] downloaded {glb} ({os.path.getsize(glb)//1024} KB)", flush=True)
os.system(f"python3 os/engine/memory.py log meshy_history "
          f"'{json.dumps({'name': name + '_img', 'task_id': tid, 'kind': 'image-to-3d', 'status': 'SUCCEEDED', 'glb': glb})}' >/dev/null")

import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
lo = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
hi = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
h2 = hi - lo or 1
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
mid = lo + h2 / 2
for label, ang in (("front", math.radians(-90)), ("threequarter", math.radians(-45))):
    cam.location = (2.6 * h2 * math.cos(ang), 2.6 * h2 * math.sin(ang), mid + h2 * 0.15)
    d = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(d)
    d.location = (0, 0, mid)
    tr = cam.constraints.new('TRACK_TO'); tr.target = d
    sc.render.filepath = os.path.join(OUT, f"{name}_img_{label}.png")
    bpy.ops.render.render(write_still=True)
    cam.constraints.remove(tr)
print(f"[Meshy] {name} img3d QA renders done", flush=True)
