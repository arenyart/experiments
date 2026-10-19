# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a high-contrast test card, run the Scanimate filter, write a still.

Run from the repository root with Blender 5.x:

    blender --background --factory-startup --python scripts/render_demo.py

Writes demo/scanimate-still.png using the Classic Logo preset.
"""

import array
import math
import sys
import zipfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "demo" / "scanimate-still.png"
CARD_PATH = Path("/tmp/scanimate-card.png")
WIDTH = 1280
HEIGHT = 720


def install_addon():
    zpath = Path("/tmp/scanimate-addon.zip")
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "scanimate").rglob("*.py")):
            archive.write(path, path.relative_to(ROOT).as_posix())
    bpy.ops.preferences.addon_install(overwrite=True, filepath=str(zpath))
    bpy.ops.preferences.addon_enable(module="scanimate")
    addon = bpy.context.preferences.addons.get("scanimate")
    if addon is None:
        raise RuntimeError("Scanimate addon failed to enable")
    import scanimate

    # register() runs while bpy.data is restricted, so build the group now.
    scanimate.ensure_group()
    print(f"enabled {scanimate.__file__}")


def smoothstep(edge0, edge1, value):
    span = edge1 - edge0
    if span == 0.0:
        return 0.0
    t = (value - edge0) / span
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return t * t * (3.0 - 2.0 * t)


def sd_annulus(x, y, cx, cy, radius, thickness):
    return abs(math.hypot(x - cx, y - cy) - radius) - thickness * 0.5


def sd_diamond(x, y, cx, cy, radius):
    return abs(x - cx) + abs(y - cy) - radius


def sd_box(x, y, cx, cy, half_x, half_y):
    dx = abs(x - cx) - half_x
    dy = abs(y - cy) - half_y
    return math.hypot(max(dx, 0.0), max(dy, 0.0)) + min(max(dx, dy), 0.0)


def build_test_card():
    """White geometric logo on black, with a soft edge so the neon ramp has a fringe."""
    pixels = array.array("f", [0.0]) * (WIDTH * HEIGHT * 4)
    ring_x = WIDTH * 0.5
    ring_y = HEIGHT * 0.56
    index = 0
    for y in range(HEIGHT):
        for x in range(WIDTH):
            distance = min(
                sd_annulus(x, y, ring_x, ring_y, 150.0, 52.0),
                sd_diamond(x, y, ring_x, ring_y, 78.0),
                sd_box(x, y, ring_x, 188.0, 250.0, 16.0),
                sd_box(x, y, ring_x, 136.0, 168.0, 12.0),
            )
            # Outside the shape is 0. Deep inside climbs to 1, so edges
            # travel the neon ramp and the core goes white-hot.
            mask = smoothstep(8.0, -36.0, distance)
            pixels[index] = mask
            pixels[index + 1] = mask
            pixels[index + 2] = mask
            pixels[index + 3] = 1.0
            index += 4

    image = bpy.data.images.new("Scanimate Test Card", WIDTH, HEIGHT, alpha=True)
    image.colorspace_settings.name = "sRGB"
    image.file_format = "PNG"
    # Assign the path before the pixels. Pointing a new image at an existing
    # file reloads it, and save() before update() writes an empty buffer.
    image.filepath_raw = str(CARD_PATH)
    image.pixels.foreach_set(pixels)
    image.update()
    image.save()
    center = (int(ring_y) * WIDTH + int(ring_x)) * 4
    print(f"wrote test card {CARD_PATH} center={tuple(round(v, 3) for v in image.pixels[center:center + 4])}")
    return image


def assert_group(tree):
    sockets = [
        item.name
        for item in tree.interface.items_tree
        if item.item_type == "SOCKET" and item.in_out == "INPUT"
    ]
    expected = [
        "Image",
        "Amplitude",
        "Frequency",
        "Phase",
        "Speed",
        "Squeeze X",
        "Squeeze Y",
        "Jitter",
        "Echo Count",
        "Echo Offset X",
        "Echo Offset Y",
        "Echo Decay",
        "Hue Offset",
        "Hue Speed",
        "Glow",
    ]
    missing = [name for name in expected if name not in sockets]
    if missing:
        raise RuntimeError(f"Scanimate group is missing inputs: {missing}; has {sockets}")
    counts = {}
    for node in tree.nodes:
        counts[node.bl_idname] = counts.get(node.bl_idname, 0) + 1
    requirements = {
        "CompositorNodeImageCoordinates": 1,
        "CompositorNodeMapUV": 1,
        "CompositorNodeSceneTime": 1,
        "CompositorNodeTranslate": 4,
        "ShaderNodeValToRGB": 1,
        "CompositorNodeHueSat": 1,
        "CompositorNodeBlur": 2,
    }
    for idname, count in requirements.items():
        if counts.get(idname, 0) < count:
            raise RuntimeError(f"expected at least {count} {idname}, found {counts.get(idname, 0)}")
    print(f"Scanimate group ok, {len(tree.nodes)} nodes, inputs: {', '.join(sockets)}")


def build_compositor(card):
    from scanimate.group import GROUP_NAME, apply_preset

    scan = bpy.data.node_groups[GROUP_NAME]
    assert_group(scan)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    if hasattr(scene.render, "resolution_percentage"):
        scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 15
    scene.render.filepath = str(OUT_PATH)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_set(10)

    world = scene.world
    if world and world.node_tree:
        for node in world.node_tree.nodes:
            if node.type == "BACKGROUND":
                node.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
                node.inputs[1].default_value = 1.0

    comp = bpy.data.node_groups.new("Scanimate Demo", "CompositorNodeTree")
    comp.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = comp

    image_node = comp.nodes.new("CompositorNodeImage")
    image_node.image = card
    image_node.location = (-500, 0)

    group = comp.nodes.new("CompositorNodeGroup")
    group.node_tree = scan
    group.location = (-80, 0)
    group.width = 280
    apply_preset(group, "CLASSIC_LOGO")

    output = comp.nodes.new("NodeGroupOutput")
    output.location = (360, 0)
    comp.links.new(image_node.outputs["Image"], group.inputs["Image"])
    comp.links.new(group.outputs["Image"], output.inputs["Image"])
    print("wired Image -> Scanimate -> Group Output, preset Classic Logo, frame", scene.frame_current)


def render_still():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    engines = ("BLENDER_WORKBENCH", "BLENDER_EEVEE", "CYCLES")
    last_error = None
    for engine in engines:
        bpy.context.scene.render.engine = engine
        if engine == "CYCLES":
            bpy.context.scene.cycles.device = "CPU"
            bpy.context.scene.cycles.samples = 1
        try:
            bpy.ops.render.render(write_still=True)
            print(f"rendered with {engine}")
            return
        except Exception as exc:
            last_error = exc
            print(f"{engine} render failed: {exc}")
    raise RuntimeError(f"compositor render failed: {last_error}")


def analyze_still():
    if not OUT_PATH.is_file() or OUT_PATH.stat().st_size < 8000:
        raise RuntimeError(f"filtered still was not written: {OUT_PATH}")
    image = bpy.data.images.load(str(OUT_PATH))
    width, height = image.size
    pixels = list(image.pixels)
    count = width * height
    lit = 0
    colorful = 0
    sum_r = sum_g = sum_b = 0.0
    for index in range(0, len(pixels), 4):
        red, green, blue = pixels[index], pixels[index + 1], pixels[index + 2]
        sum_r += red
        sum_g += green
        sum_b += blue
        peak = red if red > green else green
        if blue > peak:
            peak = blue
        floor = red if red < green else green
        if blue < floor:
            floor = blue
        if peak > 0.08:
            lit += 1
            if peak - floor > 0.12 and peak > 0.15:
                colorful += 1
    corner = max(pixels[0], pixels[1], pixels[2])
    center_index = ((height // 2) * width + (width // 2)) * 4
    center = pixels[center_index:center_index + 3]
    print(
        f"still {width}x{height} bytes={OUT_PATH.stat().st_size} "
        f"lit={lit} colorful={colorful} "
        f"mean=({sum_r / count:.4f}, {sum_g / count:.4f}, {sum_b / count:.4f}) "
        f"corner={corner:.4f} center={tuple(round(c, 3) for c in center)}"
    )
    if lit < 2000 or colorful < 800:
        raise RuntimeError("filtered still does not show the neon Scanimate image")
    if corner > 0.08:
        raise RuntimeError("background is not black; the filter did not hold the scan on black")
    print(f"wrote {OUT_PATH}")


def main():
    install_addon()
    card = build_test_card()
    build_compositor(card)
    render_still()
    analyze_still()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
