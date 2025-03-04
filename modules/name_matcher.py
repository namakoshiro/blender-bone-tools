import bpy
from bpy.types import Operator
from bpy.props import EnumProperty
import os
import subprocess
import platform
from .. import get_preset_items, load_presets, get_preset_path

# Show warning dialog before opening presets file
class ARMATURE_OT_show_presets_warning(Operator):
    bl_idname = "armature.show_presets_warning"
    bl_label = "WARNING"
    bl_description = "Show warning before opening presets file"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def invoke(self, context, event):
        # Show dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=270)
    
    def draw(self, context):
        # Draw dialog content
        layout = self.layout
        layout.label(text="This presets file will be overwritten when updating")
        layout.label(text="Please remember to make a backup", icon='ERROR')
    
    def execute(self, context):
        # Open the presets file after user confirms
        preset_path = get_preset_path()
        
        if not os.path.exists(preset_path):
            self.report({'ERROR'}, "presets.json file not found")
            return {'CANCELLED'}
        
        try:
            if platform.system() == "Windows":
                os.startfile(preset_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", preset_path])
            else:
                subprocess.call(["xdg-open", preset_path])
            
            self.report({'INFO'}, f"Opened {preset_path}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open file: {str(e)}")
            return {'CANCELLED'}
    
    def cancel(self, context):
        # User cancelled the operation
        return {'CANCELLED'}

# Edit presets.json file in text editor
class ARMATURE_OT_open_presets_file(Operator):
    bl_idname = "armature.open_presets_file"
    bl_label = "Edit Presets"
    bl_description = "Open presets.json file in text editor"
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        # Instead of opening the file directly, show warning dialog first
        bpy.ops.armature.show_presets_warning('INVOKE_DEFAULT')
        return {'FINISHED'}

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
    bpy.utils.register_class(ARMATURE_OT_show_presets_warning)
    bpy.utils.register_class(ARMATURE_OT_open_presets_file)

# Unregister
def unregister():
    bpy.utils.unregister_class(ARMATURE_OT_open_presets_file)
    bpy.utils.unregister_class(ARMATURE_OT_show_presets_warning)
    bpy.utils.unregister_class(ARMATURE_OT_convert_names) 