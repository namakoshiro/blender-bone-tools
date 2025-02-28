# Explanation of the hierarchical naming system
# Format: Prefix_n_n_n
# First n: Main chain ID (Main chains are parallel to each other)
# Second n: Sub-chain ID (Sub-chains are branches from main chains)
# Third n: Bone ID

import bpy
from bpy.types import Operator

class BONE_OT_rename_hair_chain(Operator):
    bl_idname = "bone.rename_hair_chain"
    bl_label = "Rename Bone Chain"
    bl_description = "Rename selected bone chains with a hierarchy numbering system"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # Check if object is armature
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    
    def get_chain_name(self, prefix, main_chain_num, chain_id, bone_num):
        # Generate bone name with or without prefix
        if prefix:
            return f"{prefix}_{main_chain_num}_{chain_id}_{bone_num}"
        return f"_{main_chain_num}_{chain_id}_{bone_num}"
    
    def process_bone_chain(self, bone, prefix, main_chain_num, chain_id, bone_num, next_chain_id):
        # Rename current bone
        bone.name = self.get_chain_name(prefix, main_chain_num, chain_id, bone_num)
        
        # Get selected children
        children = [b for b in bone.children if b in self.selected_bones]
        
        if not children:
            return next_chain_id
        
        # Process direct child in same chain    
        current_next_chain_id = self.process_bone_chain(
            children[0], prefix, main_chain_num, chain_id, bone_num + 1, next_chain_id
        )
        
        # Process other children as new sub-chains
        for child in children[1:]:
            current_next_chain_id = self.process_bone_chain(
                child, prefix, main_chain_num, current_next_chain_id, 1, current_next_chain_id + 1
            )
        
        return current_next_chain_id
    
    def execute(self, context):
        try:
            # Get prefix from properties
            prefix = context.scene.bone_tools.prefix
            
            # Get selected bones
            self.selected_bones = context.selected_editable_bones
            if not self.selected_bones:
                self.report({'ERROR'}, "No bones selected")
                return {'CANCELLED'}
            
            # Find root bones
            root_bones = [b for b in self.selected_bones if not b.parent or b.parent not in self.selected_bones]
            if not root_bones:
                self.report({'ERROR'}, "No root bones found in selection")
                return {'CANCELLED'}
            
            # Process each root bone as start of new chain
            for i, root in enumerate(root_bones, 1):
                self.process_bone_chain(root, prefix, i, 1, 1, 2)
            
            return {'FINISHED'}
        
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename: {str(e)}")
            return {'CANCELLED'}

# Register
def register():
    bpy.utils.register_class(BONE_OT_rename_hair_chain)

# Unregister
def unregister():
    bpy.utils.unregister_class(BONE_OT_rename_hair_chain)