import bpy
from bpy.types import Panel

class VIEW3D_PT_bone_tools(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bone"
    bl_label = "Bone Tools"
    
    @classmethod
    def poll(cls, context):
        # Check if object is armature or mesh
        obj = context.active_object
        return obj and obj.type in {'ARMATURE', 'MESH'}
    
    def draw(self, context):
        layout = self.layout
        
        obj = context.active_object
        props = context.scene.bone_tools
        
        # Physbone Renamer
        box = layout.box()
        row = box.row()
        row.prop(props, "show_physbone", text="Physbone Renamer", 
                icon='TRIA_DOWN' if props.show_physbone else 'TRIA_RIGHT', 
                emboss=False)
        
        if props.show_physbone:
            # Warning if not in Edit Mode
            if obj and obj.type == 'ARMATURE' and context.mode != 'EDIT_ARMATURE':
                row = box.row()
                row.alert = True
                row.label(text="Run in Edit Mode", icon='ERROR')
            
            # Enter a Prefix
            row = box.row(align=True)
            row.label(text="Enter a Prefix")
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.prop(props, "prefix", text="")
            
            # Select bone chains except Root
            row = box.row()
            row.label(text="Select bone chains except Root", icon='LIGHT')
            
            # Click the button
            row = box.row()
            row.scale_y = 1
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.operator("bone.rename_hair_chain", text="Rename", icon='SHADERFX')
        
        # Name Matcher
        box = layout.box()
        row = box.row()
        row.prop(props, "show_matcher", text="Name Matcher", 
                icon='TRIA_DOWN' if props.show_matcher else 'TRIA_RIGHT',
                emboss=False)
        
        if props.show_matcher:
            # Warning if not in Edit Mode
            if obj and obj.type == 'ARMATURE' and context.mode != 'EDIT_ARMATURE':
                row = box.row()
                row.alert = True
                row.label(text="Run in Edit Mode", icon='ERROR')
            
            # Select the source naming convention
            row = box.row(align=True)
            row.label(text="Source")
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.prop(props, "source_preset", text="")
            
            # Select the target naming convention
            row = box.row(align=True)
            row.label(text="Target")
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.prop(props, "target_preset", text="")
            
            # Click the button and Edit Presets
            row = box.row(align=True)
            split = row.split(factor=0.85, align=True)
            col = split.column(align=True)
            col.scale_y = 1
            col.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            col.operator("armature.convert_names", text="Convert", icon='OUTLINER_OB_ARMATURE')
            
            # Edit Presets button (icon only)
            col = split.column(align=True)
            col.scale_y = 1
            col.operator("armature.open_presets_file", text="", icon='TEXT')
        
        # Weight Transfer
        box = layout.box()
        row = box.row()
        row.prop(props, "show_weights", text="Weight Transfer", 
                icon='TRIA_DOWN' if props.show_weights else 'TRIA_RIGHT',
                emboss=False)
        
        if props.show_weights:
            # Warning if not in Object or Weight Paint Mode
            if obj and obj.type == 'MESH' and context.mode not in {'OBJECT', 'PAINT_WEIGHT'}:
                row = box.row()
                row.alert = True
                row.label(text="Press Button in Object/Weight Mode", icon='ERROR')
            
            # Export button
            row = box.row(align=True)
            split = row.split(factor=0.5, align=True)
            col = split.column(align=True)
            col.scale_y = 1
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.export_weights", text="Export", icon='EXPORT')
            
            # Import button
            col = split.column(align=True)
            col.scale_y = 1
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.import_weights", text="Import", icon='IMPORT')
            
            # Copy button
            row = box.row(align=True)
            split = row.split(factor=0.5, align=True)
            col = split.column(align=True)
            col.scale_y = 1
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.copy_weights", text="Copy", icon='COPYDOWN')
            
            # Paste button
            col = split.column(align=True)
            col.scale_y = 1
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.paste_weights", text="Paste", icon='PASTEDOWN')
            
            # Import to selected vertices only
            row = box.row()
            row.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            row.prop(props, "selected_only")
        
        layout.separator()
        box = layout.box()
        row = box.row(align=True)
        split = row.split(factor=0.5, align=True)
        
        # Update button
        col = split.column(align=True)
        col.scale_y = 1
        update_op = col.operator("bone.update_from_online", text="Update", icon='URL')
        
        # Install button
        col = split.column(align=True)
        col.scale_y = 1
        col.operator("bone.update_from_local", text="Install", icon='PACKAGE')

        # Version Info
        col = box.column()
        col.label(text="Version: 1.3.0")
        col.label(text="Last Updated: 2025/3/14")
        if hasattr(bpy.types.Scene, "bone_tools_update_available"):
            if hasattr(bpy.context.scene, "bone_tools_update_check_in_progress") and bpy.context.scene.bone_tools_update_check_in_progress:
                col.label(text="Checking update...")
            elif bpy.types.Scene.bone_tools_update_available:
                new_version = bpy.types.Scene.bone_tools_new_version if hasattr(bpy.types.Scene, "bone_tools_new_version") else ""
                col.label(text=f"New version {new_version} available", icon='FILE_REFRESH')
            else:
                col.label(text="Already latest version", icon='CHECKMARK')
        else:
            col.label(text="")

# Register
def register():
    bpy.utils.register_class(VIEW3D_PT_bone_tools)

# Unregister
def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_bone_tools)