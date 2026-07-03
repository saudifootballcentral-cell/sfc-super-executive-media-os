#!/usr/bin/env python3
"""
animation_library.py — the shared Moments animation set (11 clips) authored
procedurally on the SAME Mecanim skeleton meshy_refine.py builds, so every
clip retargets to every hero via Unity Humanoid.

Clips (per GameSpecs + Pop master bible):
  idle · ready · celebrate · lose · point · laugh · clap · shocked
  · dance · intro_pose · podium_pose

Output: $SIRAJ_EXPORTS/HeroAnimationSet.fbx (armature + all actions)
Run:  python3 animation_library.py   |   blender -b -P animation_library.py
"""
import math
import os
import sys

import bpy
from mathutils import Euler

H = 1.0        # canonical rig height; Humanoid retarget normalizes
FPS = 24


def build_rig():
    """Identical bone layout/names to meshy_refine.py."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "HeroAnimationSet"
    eb = arm.data.edit_bones
    eb.remove(eb[0])

    def bone(name, head, tail, parent=None):
        b = eb.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = eb[parent]
        return b

    bone("Hips",  (0, 0, .50 * H), (0, 0, .58 * H))
    bone("Spine", (0, 0, .58 * H), (0, 0, .70 * H), "Hips")
    bone("Chest", (0, 0, .70 * H), (0, 0, .82 * H), "Spine")
    bone("Neck",  (0, 0, .82 * H), (0, 0, .88 * H), "Chest")
    bone("Head",  (0, 0, .88 * H), (0, 0, 1.0 * H), "Neck")
    for side, s in (("Left", 1), ("Right", -1)):
        bone(f"{side}Shoulder", (s * .05 * H, 0, .80 * H), (s * .10 * H, 0, .80 * H), "Chest")
        bone(f"{side}UpperArm", (s * .10 * H, 0, .80 * H), (s * .25 * H, 0, .80 * H), f"{side}Shoulder")
        bone(f"{side}LowerArm", (s * .25 * H, 0, .80 * H), (s * .40 * H, 0, .80 * H), f"{side}UpperArm")
        bone(f"{side}Hand",     (s * .40 * H, 0, .80 * H), (s * .46 * H, 0, .80 * H), f"{side}LowerArm")
        bone(f"{side}UpperLeg", (s * .08 * H, 0, .50 * H), (s * .08 * H, 0, .28 * H), "Hips")
        bone(f"{side}LowerLeg", (s * .08 * H, 0, .28 * H), (s * .08 * H, 0, .06 * H), f"{side}UpperLeg")
        bone(f"{side}Foot",     (s * .08 * H, 0, .06 * H), (s * .08 * H, -.10 * H, .02 * H), f"{side}LowerLeg")
    bpy.ops.object.mode_set(mode="POSE")
    return arm


DEG = math.radians


def key(arm, frame, poses, loc_hips_z=None):
    """poses: {bone: (rx, ry, rz) degrees}. Keys rotation (+ optional hips lift)."""
    for name, (rx, ry, rz) in poses.items():
        pb = arm.pose.bones[name]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = Euler((DEG(rx), DEG(ry), DEG(rz)))
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc_hips_z is not None:
        pb = arm.pose.bones["Hips"]
        pb.location.z = loc_hips_z
        pb.keyframe_insert("location", frame=frame)


REST = {b: (0, 0, 0) for b in
        ["Hips", "Spine", "Chest", "Neck", "Head",
         "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
         "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
         "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
         "RightUpperLeg", "RightLowerLeg", "RightFoot"]}


def clip(arm, name, length, keyframes):
    """keyframes: list of (frame, poses_dict, hips_z|None)."""
    action = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = action
    for f, poses, hz in keyframes:
        full = dict(REST)
        full.update(poses)
        key(arm, f, full, hz)
    action.use_fake_user = True      # keep all actions for export
    action.frame_range
    return action


def build_clips(arm):
    arms_down = {"LeftUpperArm": (0, 0, 65), "RightUpperArm": (0, 0, -65)}   # relaxed A-pose
    arms_up = {"LeftUpperArm": (0, 0, -140), "RightUpperArm": (0, 0, 140)}

    def merged(*ds):
        out = {}
        for d in ds:
            out.update(d)
        return out

    # idle — breathing sway, 60f loop
    clip(arm, "idle", 60, [
        (1,  merged(arms_down, {"Spine": (2, 0, 0), "Head": (-2, 0, 0)}), 0.0),
        (30, merged(arms_down, {"Spine": (-1, 0, 2), "Head": (2, 0, -2),
                                "LeftUpperArm": (0, 0, 62), "RightUpperArm": (0, 0, -68)}), 0.01),
        (60, merged(arms_down, {"Spine": (2, 0, 0), "Head": (-2, 0, 0)}), 0.0),
    ])
    # ready — fists up fight stance
    clip(arm, "ready", 30, [
        (1,  arms_down, 0.0),
        (15, {"LeftUpperArm": (0, -40, 30), "LeftLowerArm": (0, 0, 100),
              "RightUpperArm": (0, 40, -30), "RightLowerArm": (0, 0, -100),
              "Spine": (8, 0, 0), "Hips": (5, 0, 0)}, -0.03),
        (30, {"LeftUpperArm": (0, -40, 28), "LeftLowerArm": (0, 0, 102),
              "RightUpperArm": (0, 40, -28), "RightLowerArm": (0, 0, -102),
              "Spine": (8, 0, 0), "Hips": (5, 0, 0)}, -0.03),
    ])
    # celebrate — jumping V arms
    clip(arm, "celebrate", 40, [
        (1,  arms_down, 0.0),
        (10, arms_up, 0.06),
        (20, merged(arms_up, {"Spine": (-6, 0, 0)}), -0.02),
        (30, arms_up, 0.06),
        (40, arms_down, 0.0),
    ])
    # lose — slump
    clip(arm, "lose", 40, [
        (1,  arms_down, 0.0),
        (25, {"Spine": (28, 0, 0), "Neck": (18, 0, 0), "Head": (14, 0, 0),
              "LeftUpperArm": (0, 0, 75), "RightUpperArm": (0, 0, -75)}, -0.05),
        (40, {"Spine": (26, 0, 0), "Neck": (18, 0, 0), "Head": (14, 0, 0),
              "LeftUpperArm": (0, 0, 75), "RightUpperArm": (0, 0, -75)}, -0.05),
    ])
    # point — right arm forward
    clip(arm, "point", 30, [
        (1,  arms_down, 0.0),
        (12, {"RightUpperArm": (-80, 0, -10), "RightLowerArm": (-10, 0, 0),
              "LeftUpperArm": (0, 0, 65), "Chest": (0, 0, -8)}, 0.0),
        (30, {"RightUpperArm": (-80, 0, -10), "RightLowerArm": (-10, 0, 0),
              "LeftUpperArm": (0, 0, 65), "Chest": (0, 0, -8)}, 0.0),
    ])
    # laugh — torso bounce
    clip(arm, "laugh", 30, [
        (1,  merged(arms_down, {"Spine": (-6, 0, 0), "Head": (-10, 0, 0)}), 0.0),
        (8,  merged(arms_down, {"Spine": (4, 0, 0), "Head": (6, 0, 0)}), -0.02),
        (15, merged(arms_down, {"Spine": (-6, 0, 0), "Head": (-10, 0, 0)}), 0.0),
        (22, merged(arms_down, {"Spine": (4, 0, 0), "Head": (6, 0, 0)}), -0.02),
        (30, merged(arms_down, {"Spine": (-2, 0, 0), "Head": (-4, 0, 0)}), 0.0),
    ])
    # clap
    hands_apart = {"LeftUpperArm": (0, -30, 20), "LeftLowerArm": (0, 0, 70),
                   "RightUpperArm": (0, 30, -20), "RightLowerArm": (0, 0, -70)}
    hands_meet = {"LeftUpperArm": (0, -30, -5), "LeftLowerArm": (0, 0, 95),
                  "RightUpperArm": (0, 30, 5), "RightLowerArm": (0, 0, -95)}
    clip(arm, "clap", 40, [
        (1, hands_apart, 0.0), (8, hands_meet, 0.0), (16, hands_apart, 0.0),
        (24, hands_meet, 0.0), (32, hands_apart, 0.0), (40, hands_meet, 0.0),
    ])
    # shocked — recoil
    clip(arm, "shocked", 20, [
        (1,  arms_down, 0.0),
        (6,  {"Spine": (-14, 0, 0), "Head": (-12, 0, 0),
              "LeftUpperArm": (0, 0, -30), "LeftLowerArm": (0, 0, 60),
              "RightUpperArm": (0, 0, 30), "RightLowerArm": (0, 0, -60)}, 0.03),
        (20, {"Spine": (-10, 0, 0), "Head": (-8, 0, 0),
              "LeftUpperArm": (0, 0, -25), "LeftLowerArm": (0, 0, 55),
              "RightUpperArm": (0, 0, 25), "RightLowerArm": (0, 0, -55)}, 0.02),
    ])
    # dance — hip sway loop
    clip(arm, "dance", 60, [
        (1,  {"Hips": (0, 0, 10), "Chest": (0, 0, -12),
              "LeftUpperArm": (0, 0, -60), "RightUpperArm": (0, 0, -70)}, -0.02),
        (15, {"Hips": (0, 0, -10), "Chest": (0, 0, 12),
              "LeftUpperArm": (0, 0, 70), "RightUpperArm": (0, 0, 60)}, 0.01),
        (30, {"Hips": (0, 0, 10), "Chest": (0, 0, -12),
              "LeftUpperArm": (0, 0, -60), "RightUpperArm": (0, 0, -70)}, -0.02),
        (45, {"Hips": (0, 0, -10), "Chest": (0, 0, 12),
              "LeftUpperArm": (0, 0, 70), "RightUpperArm": (0, 0, 60)}, 0.01),
        (60, {"Hips": (0, 0, 10), "Chest": (0, 0, -12),
              "LeftUpperArm": (0, 0, -60), "RightUpperArm": (0, 0, -70)}, -0.02),
    ])
    # intro_pose — heroic hold
    clip(arm, "intro_pose", 10, [
        (1, {"Chest": (-6, 0, 15), "Head": (0, 0, -12),
             "LeftUpperArm": (0, 0, 55), "RightUpperArm": (0, -30, -35),
             "RightLowerArm": (0, 0, -80)}, 0.0),
        (10, {"Chest": (-6, 0, 15), "Head": (0, 0, -12),
              "LeftUpperArm": (0, 0, 55), "RightUpperArm": (0, -30, -35),
              "RightLowerArm": (0, 0, -80)}, 0.0),
    ])
    # podium_pose — champion V
    clip(arm, "podium_pose", 10, [
        (1,  merged(arms_up, {"Chest": (-8, 0, 0), "Head": (-6, 0, 0)}), 0.0),
        (10, merged(arms_up, {"Chest": (-8, 0, 0), "Head": (-6, 0, 0)}), 0.0),
    ])


if __name__ == "__main__":
    arm = build_rig()
    build_clips(arm)
    bpy.ops.object.mode_set(mode="OBJECT")
    exports = os.environ.get("SIRAJ_EXPORTS", os.path.expanduser("~/blender/exports"))
    os.makedirs(exports, exist_ok=True)
    out = os.path.join(exports, "HeroAnimationSet.fbx")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True,
        axis_forward='-Z', axis_up='Y', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_bones=True)
    n = len([a for a in bpy.data.actions])
    print(f"[Siraj] exported {out} with {n} clips")
