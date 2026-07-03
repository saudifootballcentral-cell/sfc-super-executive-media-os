# Siraj — Install (on the same VM as Dhai, or fresh)

## 0. Prereqs (already present if Dhai is installed)
- Unity 6 at `/home/mulerun/unity6/Editor/Unity` + licensed project
- Blender 4.4 at `/home/mulerun/blender/blender`
- MCP server on 127.0.0.1:8080, Xvfb :99
- Fresh VM? Run Dhai's INSTALL.md first — Siraj shares that base.

## 1. Copy files
```bash
cp -r home/mulerun/* /home/mulerun/
chmod +x /home/mulerun/siraj-build.sh
mkdir -p /home/mulerun/meshy/downloads
```
Unity editor scripts land in `Assets/Editor/` — Unity recompiles on refresh.

## 2. Meshy API key
Get a key at meshy.ai (Settings → API), then:
```bash
echo 'MESHY_API_KEY=msy_xxxxxxxx' >> /home/mulerun/.env
chmod 600 /home/mulerun/.env
```

## 3. Workspace
Copy `workspace/*.md` into the agent's workspace directory
(same place Dhai's IDENTITY.md lives, or a sibling folder for Siraj).

## 4. Smoke test (uses ~1 Meshy generation)
```bash
cd /home/mulerun
./siraj-build.sh --prompt "simple low poly barrel, game prop" Barrel Models/Test
tail -f unity6/MyGame/../logs/unity.log   # expect: [Siraj] imported ...Barrel.fbx
```

## Troubleshooting
- 404 from Meshy → API version moved; check docs.meshy.ai and update
  paths in `meshy_client.py` (`/v2/text-to-3d` etc.).
- FBX imports tiny/huge → Meshy scale varies; `meshy_refine.py` grounds
  the pivot but not real-world size — pass a scale fix in Blender if needed.
- Unity OOM during import → `DHAI_NOGFX=1 start-dhai.sh restart`, retry refresh.
