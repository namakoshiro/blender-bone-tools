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
            row.operator("bone.rename_hair_chain", text="Rename")
        
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
            
            # Click the button
            row = box.row()
            row.scale_y = 1
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.operator("armature.convert_names", text="Convert")
        
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
            col.operator("weight.export_weights", text="Export")
            
            # Import button
            col = split.column(align=True)
            col.scale_y = 1
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.import_weights", text="Import")
            
            # Import to selected vertices only
            row = box.row()
            row.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            row.prop(props, "selected_only")
        
        layout.separator()
        
        # Update from online
        box = layout.box()
        row = box.row()
        row.scale_y = 1
        row.operator("bone.update_from_online", text="Update from Online", icon='URL')
        
        # Update from local
        row = box.row()
        row.scale_y = 1
        row.operator("bone.update_from_local", text="Update from Local", icon='PACKAGE')

        # Version Info
        col = box.column()
        col.label(text="Version: 1.2.0")
        col.label(text="Last Updated: 2025/2/28")

# Register
def register():
    bpy.utils.register_class(VIEW3D_PT_bone_tools)

# Unregister
def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_bone_tools)