bl_info = {
    "name": "Bone Tools",
    "author": "namakoshiro",
    "version": (1, 3, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bone",
    "description": "This is a Blender addon to manage bones and weights",
    "warning": "",
    "wiki_url": "https://github.com/namakoshiro/blender-bone-tools",
    "doc_url": "https://github.com/namakoshiro/blender-bone-tools",
    "category": "Rigging",
    "support": "COMMUNITY"
}

import bpy
import os
import json

from bpy.types import PropertyGroup
from bpy.props import StringProperty, EnumProperty, BoolProperty

# Naming convention presets loader
def get_preset_path():
    # Get path to presets.json
    addon_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(addon_dir, "presets.json")

def load_presets():
    try:
        # Load presets data
        with open(get_preset_path(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def get_preset_items(self, context):
    # Get preset items for EnumProperty
    presets = load_presets()
    items = [(key, preset["name"], preset["description"]) for key, preset in presets.items()]
    return items if items else [('NONE', "No Presets", "No naming presets found")]

# Make these functions available for other modules
__all__ = ['get_preset_path', 'load_presets', 'get_preset_items']

# Import from ui directory
from .ui import panels

# Import from modules directory
from .modules import physbone_renamer
from .modules import name_matcher
from .modules import weight_transfer

# Import from utils directory
from .utils import install
from .utils import update

class BoneToolsProperties(PropertyGroup):
    # Show or hide the sections
    show_physbone: BoolProperty(
        name="Show Physbone Renamer",
        description="Show/hide the Physbone Renamer section",
        default=True
    )
    show_matcher: BoolProperty(
        name="Show Bodybone Name Matcher",
        description="Show/hide the Name Matcher section",
        default=True
    )
    show_weights: BoolProperty(
        name="Show Weight Transfer",
        description="Show/hide the Weight Transfer section",
        default=True
    )
    
    # Physbone Renamer section
    prefix: StringProperty(
        name="Prefix",
        description="Enter a prefix for the names",
        default=""
    )
    
    # Name Matcher section
    source_preset: EnumProperty(
        name="Source",
        description="Select a source naming convention",
        items=get_preset_items
    )
    target_preset: EnumProperty(
        name="Target",
        description="Select a target naming convention",
        items=get_preset_items
    )
    
    # Weight Transfer section
    selected_only: BoolProperty(
        name="Import to Selected Vertices",
        description="Import weights to selected vertices only",
        default=False
    )

# Register
def register():
    bpy.utils.register_class(BoneToolsProperties)
    bpy.types.Scene.bone_tools = bpy.props.PointerProperty(type=BoneToolsProperties)
    
    physbone_renamer.register()
    name_matcher.register()
    weight_transfer.register()
    panels.register()
    install.register()
    update.register()

# Unregister
def unregister():
    update.unregister()
    install.unregister()
    panels.unregister()
    weight_transfer.unregister()
    name_matcher.unregister()
    physbone_renamer.unregister()
    
    del bpy.types.Scene.bone_tools
    bpy.utils.unregister_class(BoneToolsProperties)

if __name__ == "__main__":
    register() 