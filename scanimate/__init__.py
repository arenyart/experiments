# SPDX-License-Identifier: GPL-2.0-or-later
"""Scanimate — analog scan-conversion video filter for the Blender compositor.

On enable, a compositor node group named Scanimate is registered. Drop it on
an Image or Movie Clip node. Presets live in the Compositor sidebar and in
Add → Scanimate.
"""

import bpy
from bpy.app.handlers import persistent

from .group import (
    GROUP_NAME,
    PRESET_ITEMS,
    apply_preset,
    ensure_group,
    is_scanimate_node,
)

bl_info = {
    "name": "Scanimate",
    "author": "Scanimate",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "Compositor > Add > Scanimate",
    "description": "Analog scan-conversion video filter based on Computer Image Corporation Scanimate",
    "category": "Compositing",
}


def _compositor_space(context):
    space = getattr(context, "space_data", None)
    if space is None or space.type != "NODE_EDITOR":
        return None
    if getattr(space, "tree_type", None) != "CompositorNodeTree":
        return None
    return space


class SCANIMATE_OT_add_node(bpy.types.Operator):
    bl_idname = "scanimate.add_node"
    bl_label = "Scanimate"
    bl_description = "Add a Scanimate scan-conversion filter to the compositor"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(
        name="Preset",
        description="Scanimate look to load into the new node",
        items=PRESET_ITEMS,
        default="CLASSIC_LOGO",
    )

    @classmethod
    def poll(cls, context):
        return _compositor_space(context) is not None

    def execute(self, context):
        space = _compositor_space(context)
        tree = space.edit_tree or space.node_tree
        if tree is None:
            self.report({"WARNING"}, "Open a compositing node tree first")
            return {"CANCELLED"}
        node = tree.nodes.new("CompositorNodeGroup")
        node.node_tree = ensure_group()
        node.label = "Scanimate"
        node.width = 280
        node.location = getattr(space, "cursor_location", (0.0, 0.0))
        apply_preset(node, self.preset)
        for other in tree.nodes:
            other.select = False
        node.select = True
        tree.nodes.active = node
        return {"FINISHED"}


class SCANIMATE_OT_apply_preset(bpy.types.Operator):
    bl_idname = "scanimate.apply_preset"
    bl_label = "Apply Scanimate Preset"
    bl_description = "Set the selected Scanimate node's unlinked inputs to a preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(
        name="Preset",
        description="Scanimate look to apply",
        items=PRESET_ITEMS,
        default="CLASSIC_LOGO",
    )

    @classmethod
    def poll(cls, context):
        return is_scanimate_node(getattr(context, "active_node", None))

    def execute(self, context):
        node = context.active_node
        if not is_scanimate_node(node):
            self.report({"WARNING"}, "Select a Scanimate node")
            return {"CANCELLED"}
        apply_preset(node, self.preset)
        return {"FINISHED"}


class SCANIMATE_PT_presets(bpy.types.Panel):
    bl_label = "Scanimate"
    bl_idname = "SCANIMATE_PT_presets"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Scanimate"

    @classmethod
    def poll(cls, context):
        return _compositor_space(context) is not None

    def draw(self, context):
        layout = self.layout
        layout.label(text="Analog scan-conversion filter")
        node = context.active_node
        if not is_scanimate_node(node):
            layout.label(text="Add the node, then connect an Image or Movie Clip.")
            layout.operator_menu_enum("scanimate.add_node", "preset", text="Add Scanimate")
            return
        layout.label(text="Presets")
        column = layout.column(align=True)
        for key, _label, _description in PRESET_ITEMS:
            operator = column.operator("scanimate.apply_preset", text=_label)
            operator.preset = key


def draw_add_menu(self, context):
    if _compositor_space(context) is None:
        return
    self.layout.operator_menu_enum("scanimate.add_node", "preset", text="Scanimate")


@persistent
def on_load_post(*_args):
    try:
        ensure_group()
    except Exception as exc:
        print(f"Scanimate: could not build the node group ({exc})")


CLASSES = (
    SCANIMATE_OT_add_node,
    SCANIMATE_OT_apply_preset,
    SCANIMATE_PT_presets,
)


def _ensure_when_data_is_ready():
    """Retry until Blender has finished restricting data during addon enable."""
    try:
        ensure_group()
    except Exception as exc:
        print(f"Scanimate: node group not ready yet ({exc})")
        return 0.2
    return None


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_compositor_node_add_all.append(draw_add_menu)
    bpy.types.NODE_MT_group_add.append(draw_add_menu)
    if on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(on_load_post)
    # Enabling an addon runs register() while bpy.data is still restricted.
    # A timer fires on the next event-loop tick in the UI. Background scripts
    # should also call ensure_group() after enable; load_post covers new files.
    try:
        ensure_group()
    except Exception as exc:
        print(f"Scanimate: node group will be created when data is available ({exc})")
        if not bpy.app.timers.is_registered(_ensure_when_data_is_ready):
            bpy.app.timers.register(_ensure_when_data_is_ready, first_interval=0.0, persistent=True)


def unregister():
    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)
    for menu in (bpy.types.NODE_MT_compositor_node_add_all, bpy.types.NODE_MT_group_add):
        try:
            menu.remove(draw_add_menu)
        except ValueError:
            pass
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
