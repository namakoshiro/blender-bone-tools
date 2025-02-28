import bpy
from bpy.types import Operator
from bpy.props import EnumProperty
from .. import get_preset_items, load_presets

class ARMATURE_OT_convert_names(Operator):
    bl_idname = "armature.convert_names"
    bl_label = "Convert Names"
    bl_description = "Convert bone naming conventions"
    bl_options = {'REGISTER', 'UNDO'}
    
    source_preset: EnumProperty(
        name="Source",
        description="Source naming convention",
        items=get_preset_items
    )
    
    target_preset: EnumProperty(
        name="Target",
        description="Target naming convention",
        items=get_preset_items
    )
    
    @classmethod
    def poll(cls, context):
        # Check if object is armature
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    
    def execute(self, context):
        props = context.scene.bone_tools
        if props.source_preset == props.target_preset:
            self.report({'WARNING'}, "Source and target are the same")
            return {'CANCELLED'}
        
        # Load preset data
        presets = load_presets()
        if not presets:
            self.report({'ERROR'}, "Failed to load presets")
            return {'CANCELLED'}
        
        source_preset = presets.get(props.source_preset)
        target_preset = presets.get(props.target_preset)
        
        if not source_preset or not target_preset:
            self.report({'ERROR'}, "Invalid preset selection")
            return {'CANCELLED'}
        
        # Create name mapping dictionary
        name_mapping = {}
        for standard_name, source_name in source_preset["bones"].items():
            target_name = target_preset["bones"].get(standard_name)
            if target_name:
                name_mapping[source_name] = target_name
        
        armature = context.active_object.data
        
        # Rename bones
        renamed_count = 0
        for bone in armature.edit_bones:
            if bone.name in name_mapping:
                bone.name = name_mapping[bone.name]
                renamed_count += 1
        
        if renamed_count == 0:
            self.report({'INFO'}, "No matching bones found")
        else:
            self.report({'INFO'}, f"Successfully renamed {renamed_count} bones")
        return {'FINISHED'}

# Register
def register():
    bpy.utils.register_class(ARMATURE_OT_convert_names)

# Unregister
def unregister():
    bpy.utils.unregister_class(ARMATURE_OT_convert_names) 