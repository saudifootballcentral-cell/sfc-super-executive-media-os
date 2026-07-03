#!/usr/bin/env python3
"""hero_preview.py <HeroName> — fire a Meshy text-to-3d PREVIEW (cheap),
poll, download GLB, render QA views via bpy. Refine is a separate,
deliberate step after visual approval (credits law)."""
import json, os, sys, time, urllib.request

API = "https://api.meshy.ai/openapi"
KEY = os.environ["MESHY_API_KEY"]
OUT = "projects/moments/meshy"

STYLE = ("low poly, game asset, clean topology, T-pose, symmetrical, "
         "stylized toy-like 3D chibi proportions with oversized head, "
         "vibrant saturated colors, premium party-game character")
PROMPTS = {
  "Byte":  "chibi arcade tech kid, round black helmet with glowing LED pixel smiley-face visor, spiky teal hair, black hoodie with neon blue glowing trim, chunky sneakers, fingerless gloves, " + STYLE,
  "Nova":  "chibi girl star hunter, bright pink ponytail, star-emblem goggles on forehead, white and black sporty jacket with gold star badge, black leggings, energetic heroine, " + STYLE,
  "Orbit": "chibi mini astronaut robot, round black glass dome visor with glowing green eyes, white and black space suit with toxic green accents, small backpack thrusters, " + STYLE,
  "Pop":   "chibi girl chaos maker, blue twin-tail hair, pink cap with smiley badge, pink jacket, blowing bubblegum, roller-skater vibe, knee pads, " + STYLE,
}

def req(method, path, body=None):
    r = urllib.request.Request(API + path,
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read())

name = sys.argv[1]
task = req("POST", "/v2/text-to-3d", {
    "mode": "preview", "prompt": PROMPTS[name], "art_style": "realistic",
    "should_remesh": True, "topology": "triangle", "target_polycount": 15000})
tid = task["result"]
print(f"[Meshy] {name} preview task {tid}", flush=True)
os.system(f"python3 os/engine/memory.py log meshy_history "
          f"'{json.dumps({'name': name, 'task_id': tid, 'kind': 'text-to-3d-preview', 'status': 'started'})}' >/dev/null")

t0 = time.time()
while True:
    t = req("GET", f"/v2/text-to-3d/{tid}")
    st = t.get("status")
    print(f"[Meshy] {name} {int(time.time()-t0)}s {st} {t.get('progress','')}%", flush=True)
    if st == "SUCCEEDED": break
    if st in ("FAILED", "CANCELED"): sys.exit(f"[Meshy] {name} {st}: {t.get('task_error')}")
    if time.time() - t0 > 1500: sys.exit(f"[Meshy] {name} timeout")
    time.sleep(15)

glb = os.path.join(OUT, f"{name}_preview.glb")
urllib.request.urlretrieve(t["model_urls"]["glb"], glb)
print(f"[Meshy] downloaded {glb} ({os.path.getsize(glb)//1024} KB)", flush=True)
os.system(f"python3 os/engine/memory.py log meshy_history "
          f"'{json.dumps({'name': name, 'task_id': tid, 'kind': 'text-to-3d-preview', 'status': 'SUCCEEDED', 'glb': glb})}' >/dev/null")

# QA renders: front + three-quarter
import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
lo = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
hi = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
h = hi - lo or 1
cam_d = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cam_d)
bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam
sun_d = bpy.data.lights.new("s", 'SUN'); sun_d.energy = 4
sun = bpy.data.objects.new("s", sun_d); bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), 0, math.radians(30))
w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.85, .88, .92, 1)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 768
mid = lo + h / 2
for label, ang in (("front", math.radians(-90)), ("threequarter", math.radians(-45))):
    cam.location = (2.6 * h * math.cos(ang), 2.6 * h * math.sin(ang), mid + h * 0.15)
    d = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(d)
    d.location = (0, 0, mid)
    tr = cam.constraints.new('TRACK_TO'); tr.target = d
    sc.render.filepath = os.path.join(OUT, f"{name}_preview_{label}.png")
    bpy.ops.render.render(write_still=True)
    cam.constraints.remove(tr)
print(f"[Meshy] {name} QA renders done", flush=True)
