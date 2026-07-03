#!/usr/bin/env python3
"""
meshy_client.py — Siraj's Meshy AI client (text-to-3D, image-to-3D, retexture).

Usage:
  export MESHY_API_KEY=msy_xxx   (or put it in /home/mulerun/.env)

  # Text -> 3D (preview + refine + download GLB)
  python3 meshy_client.py text "a stylized low-poly pirate cannon" \
      --name Cannon --style sculpture --polys 15000

  # Image -> 3D
  python3 meshy_client.py image /path/to/concept.png --name HeroConcept

  # Retexture an existing Meshy task or model URL
  python3 meshy_client.py retexture --task-id 0189... \
      --prompt "weathered bronze with gold trim" --name Cannon_Bronze

Output: GLB saved to /home/mulerun/meshy/downloads/<Name>.glb
Then hand off to Blender:  siraj-build.sh --meshy <Name>.glb <Name> <Category> [--rig]
"""
import argparse, base64, json, os, sys, time, urllib.request

API = "https://api.meshy.ai/openapi"
DOWNLOADS = os.path.expanduser("~/meshy/downloads")

def _key():
    k = os.environ.get("MESHY_API_KEY")
    if not k:
        env = os.path.expanduser("~/.env")
        if os.path.exists(env):
            for line in open(env):
                if line.startswith("MESHY_API_KEY="):
                    k = line.split("=", 1)[1].strip()
    if not k:
        sys.exit("MESHY_API_KEY not set (env var or ~/.env)")
    return k

def _req(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={"Authorization": f"Bearer {_key()}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def _poll(path, task_id, every=10, timeout=1800):
    """Poll a task until SUCCEEDED. Returns the final task object."""
    t0 = time.time()
    while True:
        task = _req("GET", f"{path}/{task_id}")
        st = task.get("status")
        print(f"  [{int(time.time()-t0):>4}s] {st} {task.get('progress', '')}%",
              flush=True)
        if st == "SUCCEEDED":
            return task
        if st in ("FAILED", "CANCELED"):
            sys.exit(f"Meshy task {st}: {task.get('task_error')}")
        if time.time() - t0 > timeout:
            sys.exit("Meshy task timed out")
        time.sleep(every)

def _download(task, name):
    os.makedirs(DOWNLOADS, exist_ok=True)
    url = task["model_urls"].get("glb") or task["model_urls"].get("fbx")
    out = os.path.join(DOWNLOADS, f"{name}.glb")
    print(f"  downloading -> {out}")
    urllib.request.urlretrieve(url, out)
    print(f"DONE {out}")
    return out

def text_to_3d(prompt, name, style="sculpture", polys=15000, pbr=True):
    print("[1/2] preview...")
    prev = _req("POST", "/v2/text-to-3d", {
        "mode": "preview", "prompt": prompt, "art_style": style,
        "should_remesh": True, "topology": "triangle",
        "target_polycount": polys})
    prev_task = _poll("/v2/text-to-3d", prev["result"])
    print("[2/2] refine (textures)...")
    ref = _req("POST", "/v2/text-to-3d", {
        "mode": "refine", "preview_task_id": prev_task["id"],
        "enable_pbr": pbr})
    return _download(_poll("/v2/text-to-3d", ref["result"]), name)

def image_to_3d(image_path, name, polys=15000):
    with open(image_path, "rb") as f:
        data_uri = ("data:image/png;base64,"
                    + base64.b64encode(f.read()).decode())
    t = _req("POST", "/v1/image-to-3d", {
        "image_url": data_uri, "enable_pbr": True,
        "should_remesh": True, "target_polycount": polys})
    return _download(_poll("/v1/image-to-3d", t["result"]), name)

def retexture(name, prompt, task_id=None, model_url=None):
    body = {"text_style_prompt": prompt, "enable_pbr": True}
    if task_id:   body["input_task_id"] = task_id
    if model_url: body["model_url"] = model_url
    t = _req("POST", "/v1/retexture", body)
    return _download(_poll("/v1/retexture", t["result"]), name)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("text")
    t.add_argument("prompt"); t.add_argument("--name", required=True)
    t.add_argument("--style", default="sculpture",
                   choices=["realistic", "sculpture"])
    t.add_argument("--polys", type=int, default=15000)
    t.add_argument("--no-pbr", action="store_true")

    i = sub.add_parser("image")
    i.add_argument("image"); i.add_argument("--name", required=True)
    i.add_argument("--polys", type=int, default=15000)

    r = sub.add_parser("retexture")
    r.add_argument("--name", required=True); r.add_argument("--prompt", required=True)
    r.add_argument("--task-id"); r.add_argument("--model-url")

    a = p.parse_args()
    if a.cmd == "text":
        text_to_3d(a.prompt, a.name, a.style, a.polys, not a.no_pbr)
    elif a.cmd == "image":
        image_to_3d(a.image, a.name, a.polys)
    else:
        retexture(a.name, a.prompt, a.task_id, a.model_url)
