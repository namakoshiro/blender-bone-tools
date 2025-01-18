"""
A blender add-on for one-click to rename all physical bones

Features:
- Rename all physical bones (skirt, hair, etc.)

Version: 1.0.0
Created: 2025/1/16
Last Updated: 2025/1/18
Support Blender Version: 2.80 → 4.3

GPL License
Blender Add-on | Bone Tools

Copyright (C) 2025 namakoshiro

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

bl_info = {
    "name": "Bone Tools",
    "author": "namakoshiro",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bone",
    "description": "A blender add-on for one-click to rename all physical bones",
    "warning": "",
    "wiki_url": "https://github.com/namakoshiro/blender-bone-tools",
    "doc_url": "https://github.com/namakoshiro/blender-bone-tools",
    "category": "Rigging",
    "support": "COMMUNITY"
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty

class BoneToolsProperties(PropertyGroup):
    """Properties for Bone Tools
    
    This class stores properties that can be accessed globally
    across the add-on.
    """
    prefix: StringProperty(
        name="Prefix",
        description="Prefix for bone names",
        default="Bone",
    )

class VIEW3D_PT_bone_tools(Panel):
    """Panel for Bone Tools
    
    This panel provides quick access to bone manipulation tools
    in the 3D View's sidebar. It is visible when an armature object
    is selected.
    """
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bone"
    bl_label = "Bone Tools"
    
    @classmethod
    def poll(cls, context):
        # Show panel when an armature is selected
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    
    def draw(self, context):
        """Draw the panel layout"""
        layout = self.layout
        
        # Mode warning at top (only show when not in Edit Mode)
        if context.mode != 'EDIT_ARMATURE':
            box = layout.box()
            row = box.row()
            row.alert = True
            row.label(text="Edit Mode Only", icon='ERROR')
            layout.separator()
        
        # Step 1: Prefix input
        box = layout.box()
        box.label(text="Step 1: Enter Bone Prefix")
        box.prop(context.scene.bone_tools, "prefix", text="")
        
        # Step 2: Selection instruction
        box = layout.box()
        box.label(text="Step 2: Select All Bones")
        row = box.row()
        row.scale_y = 0.7
        row.label(text="Don't select the root bone", icon='LIGHT')
        
        # Step 3: Rename buttons
        box = layout.box()
        box.label(text="Step 3: Rename Bones")
        row = box.row()
        row.scale_y = 1.5
        row.operator("bone.rename_hair_chain", text="Click this Button")
        # Test button (hidden)
        # row = box.row()
        # row.scale_y = 1.5
        # row.operator("bone.rename_test", text="Test")
        
        # Add version information
        layout.separator()
        box = layout.box()
        col = box.column()
        col.scale_y = 0.8
        col.label(text="Version: 1.0.0")
        col.label(text="Last Updated: 2025/1/18")
        col.label(text="Blender: 2.80 → 4.3")

class BONE_OT_rename_hair_chain(Operator):
    """Rename bone chains with simple numeric system
    
    This operator renames selected bone chains using the following pattern:
    - Format: Prefix_n_n_n
    - First n: Main chain number (1-n for parallel chains)
    - Second n: Chain ID (1 for main chain, 2+ for sub-chains in order of appearance)
    - Third n: Bone position in its chain
    
    Examples:
    - Prefix_1_1_1: First bone of main chain 1
    - Prefix_1_1_2: Second bone of main chain 1
    - Prefix_1_2_1: First bone of first sub-chain in main chain 1
    - Prefix_2_1_1: First bone of main chain 2
    """
    bl_idname = "bone.rename_hair_chain"
    bl_label = "Rename Bone Chain"
    bl_description = "Rename selected bone chains with simple numeric system"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if the operator can be called
        
        This operator can only be used in Edit Mode with bones selected.
        
        Args:
            context: Blender context
            
        Returns:
            bool: True if operator can be called
        """
        # Only allow in Edit Mode
        if context.mode != 'EDIT_ARMATURE':
            return False
        
        # Check if we have selected bones
        return bool(context.selected_editable_bones)
    
    def get_chain_name(self, prefix, main_chain_num, chain_id, bone_num):
        """Generate the name for a bone in the chain
        
        Args:
            prefix: The name prefix (can be empty)
            main_chain_num: The main chain number (1-n)
            chain_id: The chain ID (1 for main, 2+ for sub-chains)
            bone_num: The bone's position in its chain
            
        Returns:
            str: The new name for the bone
        """
        if prefix:
            return f"{prefix}_{main_chain_num}_{chain_id}_{bone_num}"
        return f"_{main_chain_num}_{chain_id}_{bone_num}"
    
    def process_bone_chain(self, bone, prefix, main_chain_num, chain_id, bone_num, next_chain_id):
        """Process a chain of bones for renaming
        
        This function recursively processes a bone chain:
        - Renames the current bone
        - First child continues the current chain
        - Other children start new chains
        
        Args:
            bone: The bone to process
            prefix: The name prefix
            main_chain_num: Current main chain number
            chain_id: Current chain ID
            bone_num: Current bone number in chain
            next_chain_id: Next available chain ID for new branches
            
        Returns:
            int: The next available chain ID after processing this chain
        """
        # Rename current bone
        bone.name = self.get_chain_name(prefix, main_chain_num, chain_id, bone_num)
        
        # Get children that are in the selection
        children = [b for b in bone.children if b in self.selected_bones]
        
        if not children:
            return next_chain_id
            
        # First child continues current chain
        current_next_chain_id = self.process_bone_chain(
            children[0], prefix, main_chain_num, chain_id, bone_num + 1, next_chain_id
        )
        
        # Other children start new chains
        for child in children[1:]:
            current_next_chain_id = self.process_bone_chain(
                child, prefix, main_chain_num, current_next_chain_id, 1, current_next_chain_id + 1
            )
        
        return current_next_chain_id
    
    def execute(self, context):
        """Execute the operator
        
        This function:
        - Gets the prefix from properties
        - Gets selected bones
        - Finds root bones
        - Processes each root bone as a separate main chain
        
        Args:
            context: Blender context
            
        Returns:
            set: {'FINISHED'} if successful, {'CANCELLED'} if failed
        """
        try:
            # Get prefix from properties (can be empty)
            prefix = context.scene.bone_tools.prefix
            
            # Get selected bones
            self.selected_bones = context.selected_editable_bones
            if not self.selected_bones:
                self.report({'ERROR'}, "No bones selected")
                return {'CANCELLED'}
            
            # Find root bones (bones without parents or with unselected parents)
            root_bones = [b for b in self.selected_bones if not b.parent or b.parent not in self.selected_bones]
            if not root_bones:
                self.report({'ERROR'}, "No root bones found in selection")
                return {'CANCELLED'}
            
            # Process each root bone as a separate main chain
            for i, root in enumerate(root_bones, 1):
                self.process_bone_chain(root, prefix, i, 1, 1, 2)
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename bones: {str(e)}")
            return {'CANCELLED'}

class BONE_OT_rename_test(Operator):
    """Test operator to rename bones with only prefix
    
    This operator renames selected bones using only the prefix,
    without any additional numbering.
    """
    bl_idname = "bone.rename_test"
    bl_label = "Rename Test"
    bl_description = "Rename selected bones with prefix only (for testing)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if the operator can be called"""
        if context.mode != 'EDIT_ARMATURE':
            return False
        return bool(context.selected_editable_bones)
    
    def execute(self, context):
        """Execute the operator"""
        try:
            prefix = context.scene.bone_tools.prefix
            if not prefix:
                self.report({'ERROR'}, "Please enter a prefix")
                return {'CANCELLED'}
                
            selected_bones = context.selected_editable_bones
            if not selected_bones:
                self.report({'ERROR'}, "No bones selected")
                return {'CANCELLED'}
            
            # Rename all selected bones with just the prefix
            for bone in selected_bones:
                bone.name = prefix
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename bones: {str(e)}")
            return {'CANCELLED'}

def register():
    """Register all classes"""
    bpy.utils.register_class(BoneToolsProperties)
    bpy.utils.register_class(BONE_OT_rename_hair_chain)
    bpy.utils.register_class(BONE_OT_rename_test)
    bpy.utils.register_class(VIEW3D_PT_bone_tools)
    bpy.types.Scene.bone_tools = bpy.props.PointerProperty(type=BoneToolsProperties)

def unregister():
    """Unregister all classes"""
    bpy.utils.unregister_class(VIEW3D_PT_bone_tools)
    bpy.utils.unregister_class(BONE_OT_rename_test)
    bpy.utils.unregister_class(BONE_OT_rename_hair_chain)
    bpy.utils.unregister_class(BoneToolsProperties)
    del bpy.types.Scene.bone_tools

if __name__ == "__main__":
    register()