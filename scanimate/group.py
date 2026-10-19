# SPDX-License-Identifier: GPL-2.0-or-later
"""Scanimate compositor node group.

Signal chain, in the order an analog scan converter applied it:

1. Deflection — sine bend on X and Y, squeeze/stretch, horizontal scan jitter.
2. Multi-image echoes — two to five copies, offset, with brightness decay.
3. Luminance-to-color — black, magenta, cyan, yellow, white, then a hue offset.
4. CRT glow — two soft blooms added back onto the colored image.
"""

import bpy

GROUP_NAME = "Scanimate"
VERSION = 1

# Classic Logo is also the default socket value, so a newly dropped node
# already has the balanced scan-conversion look.
PRESETS = {
    "CLASSIC_LOGO": {
        "label": "Classic Logo",
        "description": "Gentle living wave, a short echo trail, and the classic neon ramp.",
        "values": {
            "Amplitude": 0.028,
            "Frequency": 1.35,
            "Phase": 0.18,
            "Speed": 0.012,
            "Squeeze X": 1.0,
            "Squeeze Y": 1.06,
            "Echo Count": 3,
            "Echo Offset X": 0.034,
            "Echo Offset Y": -0.026,
            "Echo Decay": 0.48,
            "Hue Offset": 0.0,
            "Hue Speed": 0.0,
            "Glow": 0.7,
            "Jitter": 0.0035,
        },
    },
    "WAVE_FLAG": {
        "label": "Wave Flag",
        "description": "Large sine-wave deflection. Horizontal strokes bend into a flag.",
        "values": {
            "Amplitude": 0.11,
            "Frequency": 2.0,
            "Phase": 0.05,
            "Speed": 0.018,
            "Squeeze X": 1.0,
            "Squeeze Y": 1.0,
            "Echo Count": 2,
            "Echo Offset X": 0.01,
            "Echo Offset Y": -0.006,
            "Echo Decay": 0.3,
            "Hue Offset": 0.0,
            "Hue Speed": 0.0,
            "Glow": 0.45,
            "Jitter": 0.002,
        },
    },
    "MULTI_ECHO": {
        "label": "Multi Echo",
        "description": "Five offset copies with a slow brightness decay.",
        "values": {
            "Amplitude": 0.012,
            "Frequency": 1.0,
            "Phase": 0.0,
            "Speed": 0.006,
            "Squeeze X": 1.0,
            "Squeeze Y": 1.0,
            "Echo Count": 5,
            "Echo Offset X": 0.038,
            "Echo Offset Y": -0.028,
            "Echo Decay": 0.68,
            "Hue Offset": 0.02,
            "Hue Speed": 0.0,
            "Glow": 0.6,
            "Jitter": 0.0025,
        },
    },
    "HUE_CYCLE": {
        "label": "Hue Cycle",
        "description": "The neon ramp rotates through hue while the deflection keeps moving.",
        "values": {
            "Amplitude": 0.04,
            "Frequency": 1.6,
            "Phase": 0.25,
            "Speed": 0.014,
            "Squeeze X": 0.96,
            "Squeeze Y": 1.1,
            "Echo Count": 3,
            "Echo Offset X": 0.03,
            "Echo Offset Y": -0.02,
            "Echo Decay": 0.5,
            "Hue Offset": 0.0,
            "Hue Speed": 0.012,
            "Glow": 0.85,
            "Jitter": 0.004,
        },
    },
}

PRESET_ITEMS = tuple(
    (key, preset["label"], preset["description"]) for key, preset in PRESETS.items()
)

_TAU = 6.283185307179586


def is_scanimate_tree(tree):
    return (
        tree is not None
        and tree.bl_idname == "CompositorNodeTree"
        and tree.get("scanimate_version") is not None
    )


def is_scanimate_node(node):
    return node is not None and is_scanimate_tree(getattr(node, "node_tree", None))


def apply_preset(node, preset_id):
    """Write preset values onto an unlinked Scanimate group node."""
    preset = PRESETS[preset_id]
    for name, value in preset["values"].items():
        sock = node.inputs.get(name)
        if sock is None or sock.is_linked:
            continue
        sock.default_value = value


class _Builder:
    def __init__(self, tree):
        self.tree = tree
        self.columns = {}
        self.max_x = 0

    def slot(self, col, step=120):
        y = self.columns.get(col, 720)
        self.columns[col] = y - step
        x = col * 230
        if x > self.max_x:
            self.max_x = x
        return x, y

    def add(self, idname, x, y, label=None):
        node = self.tree.nodes.new(idname)
        node.location = (x, y)
        if label:
            node.label = label
            node.use_custom_color = True
        if x > self.max_x:
            self.max_x = x
        return node

    def link(self, src, dst):
        self.tree.links.new(src, dst)

    @staticmethod
    def sock(node, identifier, outputs=False):
        coll = node.outputs if outputs else node.inputs
        for socket in coll:
            if socket.identifier == identifier:
                return socket
        raise KeyError(identifier)

    def plug(self, socket, value):
        if isinstance(value, (int, float)):
            socket.default_value = float(value)
        else:
            self.tree.links.new(value, socket)

    def math(self, op, a, b=None, c=None, col=0):
        node = self.add("ShaderNodeMath", *self.slot(col, 90))
        node.operation = op
        self.plug(node.inputs[0], a)
        if b is not None:
            self.plug(node.inputs[1], b)
        if c is not None:
            self.plug(node.inputs[2], c)
        return node.outputs[0]

    def separate(self, image, col):
        node = self.add("CompositorNodeSeparateColor", *self.slot(col, 170))
        node.mode = "RGB"
        self.link(image, node.inputs["Image"])
        return node

    def combine(self, red, green, blue, alpha=1.0, col=0):
        node = self.add("CompositorNodeCombineColor", *self.slot(col, 180))
        self.plug(node.inputs["Red"], red)
        self.plug(node.inputs["Green"], green)
        self.plug(node.inputs["Blue"], blue)
        self.plug(node.inputs["Alpha"], alpha)
        return node.outputs["Image"]

    def scale_rgb(self, image, weight, col):
        sep = self.separate(image, col)
        return self.combine(
            self.math("MULTIPLY", sep.outputs["Red"], weight, col=col + 1),
            self.math("MULTIPLY", sep.outputs["Green"], weight, col=col + 1),
            self.math("MULTIPLY", sep.outputs["Blue"], weight, col=col + 1),
            1.0,
            col=col + 2,
        )

    def add_rgb(self, image_a, image_b, col):
        a = self.separate(image_a, col)
        b = self.separate(image_b, col)
        return self.combine(
            self.math("ADD", a.outputs["Red"], b.outputs["Red"], col=col + 1),
            self.math("ADD", a.outputs["Green"], b.outputs["Green"], col=col + 1),
            self.math("ADD", a.outputs["Blue"], b.outputs["Blue"], col=col + 1),
            1.0,
            col=col + 2,
        )


def _panel(tree, name, description):
    panel = tree.interface.new_panel(name)
    panel.description = description
    return panel


def _float_socket(tree, parent, name, default, min_value, max_value, description, subtype="NONE"):
    sock = tree.interface.new_socket(
        name=name,
        in_out="INPUT",
        socket_type="NodeSocketFloat",
        parent=parent,
    )
    sock.description = description
    sock.subtype = subtype
    sock.min_value = min_value
    sock.max_value = max_value
    sock.default_value = float(default)
    return sock


def _build_interface(tree, defaults):
    image_in = tree.interface.new_socket(name="Image", in_out="INPUT", socket_type="NodeSocketColor")
    image_in.description = "High-contrast artwork or video on black. Connect an Image or Movie Clip."

    deflection = _panel(
        tree,
        "Deflection",
        "Sine-wave bend and squeeze, the Scanimate deflection-coil controls.",
    )
    echoes = _panel(
        tree,
        "Echoes",
        "Offset copies of the scanned image with brightness decay.",
    )
    color = _panel(
        tree,
        "Color",
        "Luminance-to-neon ramp and hue cycle.",
    )
    crt = _panel(tree, "CRT", "Soft glow of the scan-converter display.")

    deflection_specs = (
        ("Amplitude", 0.0, 0.35, "NONE",
         "Peak sine deflection, as a fraction of the image. Higher bends the picture into a flag."),
        ("Frequency", 0.0, 12.0, "NONE",
         "Sine cycles across the frame. About 1–2 is a slow wave; higher is a tighter ripple."),
        ("Phase", -8.0, 8.0, "NONE",
         "Deflection phase in turns. 0 and 1 are the same bend, shifted by a full cycle."),
        ("Speed", -0.25, 0.25, "NONE",
         "Phase advance in turns per frame. Zero holds the wave still."),
        ("Squeeze X", 0.25, 3.0, "NONE",
         "Horizontal deflection gain. 1 is unchanged, higher squeezes the image narrower, lower stretches it."),
        ("Squeeze Y", 0.25, 3.0, "NONE",
         "Vertical deflection gain. 1 is unchanged, higher squeezes the image shorter, lower stretches it."),
        ("Jitter", 0.0, 0.04, "NONE",
         "Horizontal per-scanline jitter, as a fraction of image width."),
    )
    for name, min_value, max_value, subtype, description in deflection_specs:
        _float_socket(tree, deflection, name, defaults[name], min_value, max_value, description, subtype)

    count = tree.interface.new_socket(
        name="Echo Count",
        in_out="INPUT",
        socket_type="NodeSocketInt",
        parent=echoes,
    )
    count.description = "How many images are stacked, including the original. Range is 2–5."
    count.min_value = 2
    count.max_value = 5
    count.default_value = int(defaults["Echo Count"])

    echo_specs = (
        ("Echo Offset X", -0.25, 0.25, "NONE",
         "Horizontal shift of each echo, as a fraction of image width. Positive moves echoes to the right."),
        ("Echo Offset Y", -0.25, 0.25, "NONE",
         "Vertical shift of each echo, as a fraction of image height. Positive moves echoes up."),
        ("Echo Decay", 0.0, 1.0, "FACTOR",
         "Brightness of each successive echo. 0.5 means each copy is half as bright as the one before it."),
    )
    for name, min_value, max_value, subtype, description in echo_specs:
        _float_socket(tree, echoes, name, defaults[name], min_value, max_value, description, subtype)

    color_specs = (
        ("Hue Offset", 0.0, 1.0, "FACTOR",
         "Rotates the neon ramp around the hue circle. 0 keeps black, magenta, cyan, yellow, white."),
        ("Hue Speed", -0.1, 0.1, "NONE",
         "Hue advance in turns per frame. This is what the Hue Cycle preset animates."),
    )
    for name, min_value, max_value, subtype, description in color_specs:
        _float_socket(tree, color, name, defaults[name], min_value, max_value, description, subtype)

    _float_socket(
        tree,
        crt,
        "Glow",
        defaults["Glow"],
        0.0,
        2.0,
        "Soft CRT bloom added back onto the colored image. 0 turns the glow off.",
        "NONE",
    )

    image_out = tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    image_out.description = "Filtered image. Connect this to the compositing Group Output."


def _build_deflection(g, group_in):
    coords = g.add("CompositorNodeImageCoordinates", *g.slot(0, 200), label="Scan coordinates")
    g.link(group_in.outputs["Image"], coords.inputs["Image"])

    norm = g.add("ShaderNodeSeparateXYZ", *g.slot(0, 150))
    g.link(coords.outputs["Normalized"], norm.inputs["Vector"])
    x = norm.outputs["X"]
    y = norm.outputs["Y"]

    pixel = g.add("ShaderNodeSeparateXYZ", *g.slot(0, 150))
    g.link(coords.outputs["Pixel"], pixel.inputs["Vector"])
    scanline = pixel.outputs["Y"]

    clock = g.add("CompositorNodeSceneTime", *g.slot(0, 140), label="Phase clock")
    frame = clock.outputs["Frame"]

    phase_turns = g.math(
        "ADD",
        group_in.outputs["Phase"],
        g.math("MULTIPLY", frame, group_in.outputs["Speed"], col=1),
        col=2,
    )

    # Squeeze is deflection gain. Above 1 the picture shrinks on that axis.
    squeezed_x = g.math(
        "ADD",
        g.math(
            "MULTIPLY",
            g.math("SUBTRACT", x, 0.5, col=1),
            group_in.outputs["Squeeze X"],
            col=2,
        ),
        0.5,
        col=3,
    )
    squeezed_y = g.math(
        "ADD",
        g.math(
            "MULTIPLY",
            g.math("SUBTRACT", y, 0.5, col=1),
            group_in.outputs["Squeeze Y"],
            col=2,
        ),
        0.5,
        col=3,
    )

    # dx varies with Y so vertical strokes snake. dy varies with X so a
    # horizontal bar becomes the wavy flag. The Y oscillator is a quarter
    # turn ahead, the way two deflection oscillators were rarely locked.
    arg_x = g.math(
        "MULTIPLY",
        g.math(
            "ADD",
            g.math("MULTIPLY", group_in.outputs["Frequency"], y, col=2),
            phase_turns,
            col=3,
        ),
        _TAU,
        col=4,
    )
    arg_y = g.math(
        "MULTIPLY",
        g.math(
            "ADD",
            g.math(
                "ADD",
                g.math("MULTIPLY", group_in.outputs["Frequency"], x, col=2),
                phase_turns,
                col=3,
            ),
            0.25,
            col=4,
        ),
        _TAU,
        col=5,
    )
    delta_x = g.math(
        "MULTIPLY",
        group_in.outputs["Amplitude"],
        g.math("SINE", arg_x, col=5),
        col=6,
    )
    delta_y = g.math(
        "MULTIPLY",
        group_in.outputs["Amplitude"],
        g.math("SINE", arg_y, col=5),
        col=6,
    )

    jitter_wave = g.math(
        "SINE",
        g.math(
            "ADD",
            g.math("MULTIPLY", scanline, 91.345, col=2),
            g.math("MULTIPLY", phase_turns, 40.0, col=2),
            col=3,
        ),
        col=4,
    )
    jitter_x = g.math(
        "MULTIPLY",
        g.math("SUBTRACT", g.math("FRACT", g.math("MULTIPLY", jitter_wave, 43758.5453, col=5), col=6), 0.5, col=7),
        group_in.outputs["Jitter"],
        col=8,
    )

    sample_x = g.math("ADD", g.math("ADD", squeezed_x, delta_x, col=7), jitter_x, col=8)
    sample_y = g.math("ADD", squeezed_y, delta_y, col=7)

    uv = g.add("ShaderNodeCombineXYZ", *g.slot(9, 180), label="Deflection UV")
    g.link(sample_x, uv.inputs["X"])
    g.link(sample_y, uv.inputs["Y"])
    uv.inputs["Z"].default_value = 1.0

    sample = g.add("CompositorNodeMapUV", *g.slot(10, 220), label="Deflection sample")
    sample.use_custom_color = True
    sample.color = (0.16, 0.28, 0.48)
    sample.inputs["Interpolation"].default_value = "Bicubic"
    sample.inputs["Extension X"].default_value = "Clip"
    sample.inputs["Extension Y"].default_value = "Clip"
    g.link(group_in.outputs["Image"], sample.inputs["Image"])
    g.link(uv.outputs["Vector"], sample.inputs["UV"])
    return sample.outputs["Image"], frame


def _flatten_over_black(g, image):
    sep = g.separate(image, 11)
    black_mix = g.add("ShaderNodeMix", *g.slot(12, 200), label="Artwork on black")
    black_mix.data_type = "RGBA"
    black_mix.blend_type = "MIX"
    black_mix.inputs[0].default_value = 1.0
    # Factor is the source alpha. Cleared scan areas stay black, not transparent.
    g.link(sep.outputs["Alpha"], g.sock(black_mix, "Factor_Float"))
    g.sock(black_mix, "A_Color").default_value = (0.0, 0.0, 0.0, 1.0)
    g.link(image, g.sock(black_mix, "B_Color"))
    return g.sock(black_mix, "Result_Color", outputs=True)


def _build_echoes(g, image, group_in):
    info = g.add("CompositorNodeImageInfo", *g.slot(11, 180), label="Image size")
    g.link(group_in.outputs["Image"], info.inputs["Image"])
    size = g.add("ShaderNodeSeparateXYZ", *g.slot(11, 150))
    g.link(info.outputs["Dimensions"], size.inputs["Vector"])
    width = size.outputs["X"]
    height = size.outputs["Y"]

    count = group_in.outputs["Echo Count"]
    offset_x = group_in.outputs["Echo Offset X"]
    offset_y = group_in.outputs["Echo Offset Y"]
    decay = group_in.outputs["Echo Decay"]

    # Copies 1..4. Echo Count includes the unshifted original, so count 2 is
    # the original plus one echo and count 5 is the original plus four.
    accumulated = image
    for index in range(1, 5):
        gate = g.math("GREATER_THAN", count, float(index), col=12)
        weight = g.math(
            "MULTIPLY",
            g.math("POWER", decay, float(index), col=12),
            gate,
            col=13,
        )
        shift_x = g.math(
            "MULTIPLY",
            g.math("MULTIPLY", offset_x, width, col=12),
            float(index),
            col=13,
        )
        shift_y = g.math(
            "MULTIPLY",
            g.math("MULTIPLY", offset_y, height, col=12),
            float(index),
            col=13,
        )
        translated = g.add(
            "CompositorNodeTranslate",
            *g.slot(14, 190),
            label=f"Echo {index}",
        )
        translated.inputs["Interpolation"].default_value = "Bilinear"
        translated.inputs["Extension X"].default_value = "Clip"
        translated.inputs["Extension Y"].default_value = "Clip"
        g.link(image, translated.inputs["Image"])
        g.link(shift_x, translated.inputs["X"])
        g.link(shift_y, translated.inputs["Y"])
        scaled = g.scale_rgb(translated.outputs["Image"], weight, 15)
        accumulated = g.add_rgb(accumulated, scaled, 18)
    return accumulated


def _build_neon(g, image, group_in, frame):
    sep = g.separate(image, 21)
    luma = g.math(
        "MULTIPLY_ADD",
        sep.outputs["Red"],
        0.2126,
        g.math(
            "MULTIPLY_ADD",
            sep.outputs["Green"],
            0.7152,
            g.math("MULTIPLY", sep.outputs["Blue"], 0.0722, col=22),
            col=23,
        ),
        col=24,
    )
    clamped = g.add("ShaderNodeClamp", *g.slot(25, 140), label="Luminance")
    clamped.inputs["Min"].default_value = 0.0
    clamped.inputs["Max"].default_value = 1.0
    g.link(luma, clamped.inputs["Value"])

    ramp = g.add("ShaderNodeValToRGB", *g.slot(26, 260), label="Neon ramp")
    ramp.use_custom_color = True
    ramp.color = (0.45, 0.12, 0.32)
    ramp.color_ramp.interpolation = "LINEAR"
    stops = ramp.color_ramp.elements
    stops[0].position = 0.0
    stops[0].color = (0.0, 0.0, 0.0, 1.0)
    stops[1].position = 1.0
    stops[1].color = (1.0, 1.0, 1.0, 1.0)
    for position, color in (
        (0.12, (1.0, 0.0, 1.0, 1.0)),
        (0.42, (0.0, 1.0, 1.0, 1.0)),
        (0.70, (1.0, 1.0, 0.0, 1.0)),
    ):
        element = stops.new(position)
        element.color = color
    g.link(clamped.outputs["Result"], ramp.inputs["Factor"])

    # Hue Saturation's Hue input is neutral at 0.5. One full turn is +1.
    hue_turn = g.math(
        "FRACT",
        g.math(
            "ADD",
            group_in.outputs["Hue Offset"],
            g.math("MULTIPLY", frame, group_in.outputs["Hue Speed"], col=22),
            col=23,
        ),
        col=24,
    )
    hue_value = g.math("ADD", hue_turn, 0.5, col=25)

    hue = g.add("CompositorNodeHueSat", *g.slot(27, 200), label="Hue cycle")
    hue.inputs["Saturation"].default_value = 1.0
    hue.inputs["Value"].default_value = 1.0
    hue.inputs["Factor"].default_value = 1.0
    g.link(ramp.outputs["Color"], hue.inputs["Image"])
    g.link(hue_value, hue.inputs["Hue"])
    return hue.outputs["Image"]


def _blur(g, image, radius, col, label):
    size = g.add("ShaderNodeCombineXYZ", *g.slot(col, 150))
    g.link(radius, size.inputs["X"])
    g.link(radius, size.inputs["Y"])
    size.inputs["Z"].default_value = 0.0
    blur = g.add("CompositorNodeBlur", *g.slot(col + 1, 180), label=label)
    blur.inputs["Type"].default_value = "Gaussian"
    blur.inputs["Separable"].default_value = True
    g.link(image, blur.inputs["Image"])
    g.link(size.outputs["Vector"], blur.inputs["Size"])
    return blur.outputs["Image"]


def _build_glow(g, image, group_in):
    glow = group_in.outputs["Glow"]
    tight_radius = g.math("MAXIMUM", g.math("MULTIPLY", glow, 14.0, col=28), 0.0, col=29)
    wide_radius = g.math("MAXIMUM", g.math("MULTIPLY", glow, 42.0, col=28), 0.0, col=29)
    tight = g.scale_rgb(
        _blur(g, image, tight_radius, 30, "Tight CRT glow"),
        g.math("MULTIPLY", glow, 0.55, col=29),
        32,
    )
    wide = g.scale_rgb(
        _blur(g, image, wide_radius, 30, "Wide CRT glow"),
        g.math("MULTIPLY", glow, 0.28, col=29),
        32,
    )
    return g.add_rgb(g.add_rgb(image, tight, 35), wide, 38)


def build_group(tree):
    defaults = PRESETS["CLASSIC_LOGO"]["values"]
    _build_interface(tree, defaults)

    g = _Builder(tree)
    group_in = g.add("NodeGroupInput", -460, 0, label="Scanimate")
    warped, frame = _build_deflection(g, group_in)
    flat = _flatten_over_black(g, warped)
    echoed = _build_echoes(g, flat, group_in)
    colored = _build_neon(g, echoed, group_in, frame)
    glowed = _build_glow(g, colored, group_in)

    group_out = g.add("NodeGroupOutput", g.max_x + 380, 0, label="Output")
    g.link(glowed, group_out.inputs["Image"])

    tree.description = (
        "Analog scan-conversion filter based on Computer Image Corporation Scanimate. "
        "Deflection warp, multi-image echoes, luminance-to-neon color, and CRT glow."
    )
    tree.color_tag = "FILTER"
    tree.default_group_node_width = 280
    tree.use_fake_user = True
    tree["scanimate_version"] = VERSION


def ensure_group():
    """Create the Scanimate compositor group, or rebuild it when the version changes."""
    tree = bpy.data.node_groups.get(GROUP_NAME)
    if tree is not None and tree.bl_idname != "CompositorNodeTree":
        bpy.data.node_groups.remove(tree)
        tree = None
    if tree is not None and tree.get("scanimate_version") == VERSION:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(GROUP_NAME, "CompositorNodeTree")
    else:
        tree.nodes.clear()
        tree.links.clear()
        tree.interface.clear()
    build_group(tree)
    return tree
