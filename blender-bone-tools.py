"""
A blender add-on to easily rename bones and transfer weights.

Features:
- Rename all physical bones (skirt, hair, etc.) with smart numbering system
- Convert bone names between different naming conventions using presets
- Export and import vertex weights as JSON file with global coordinates

Version: 1.1.0
Created: 2025/1/16
Last Updated: 2025/2/25
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
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bone",
    "description": "A blender add-on to easily rename bones and transfer weights.",
    "warning": "",
    "wiki_url": "https://github.com/namakoshiro/blender-bone-tools",
    "doc_url": "https://github.com/namakoshiro/blender-bone-tools",
    "category": "Rigging",
    "support": "COMMUNITY"
}

import bpy
import json
import os
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, EnumProperty, BoolProperty, FloatProperty
from mathutils import Vector
from bpy_extras.io_utils import ImportHelper, ExportHelper

def get_preset_path():
    """Get the path to the naming preset file.
    
    The preset file contains bone name mappings between different naming conventions.
    It should be located in the same directory as this script.
    
    Returns:
        str: Full path to the preset file
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "presets.json")

def load_presets():
    """Load naming presets from the JSON file.
    
    The preset file contains mappings between different naming conventions.
    Each preset defines how bone names should be converted.
    
    Returns:
        dict: Preset data containing name mappings if successful, empty dict if failed
    """
    try:
        with open(get_preset_path(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load presets: {str(e)}")
        return {}

def get_preset_items(self, context):
    """Get preset items for the naming convention dropdown.
    
    This function loads the presets and formats them for use in the UI.
    Each preset contains a name and description that will be shown in the dropdown.
    
    Returns:
        list: List of tuples formatted as (identifier, name, description)
    """
    presets = load_presets()
    items = []
    for key, preset in presets.items():
        items.append((
            key,  # identifier
            preset["name"],  # name
            preset["description"]  # description
        ))
    return items if items else [('NONE', "No Presets", "No naming presets found")]

class BoneToolsProperties(PropertyGroup):
    """Properties for the Bone Tools add-on.
    
    This class defines all the properties used by the add-on:
    - UI state properties for collapsible sections
    - Input properties for bone renaming
    - Selection properties for name conversion
    - Options for weight transfer
    """
    # Collapsible group properties
    show_physbone: BoolProperty(
        name="Show Physbone Renamer",
        description="Show or hide the Physbone Renamer group",
        default=True
    )
    show_matcher: BoolProperty(
        name="Show Name Matcher",
        description="Show or hide the Name Matcher group",
        default=True
    )
    show_weights: BoolProperty(
        name="Show Weight Transfer",
        description="Show or hide the Weight Transfer group",
        default=True
    )
    
    # Physbone Renamer properties
    prefix: StringProperty(
        name="Prefix",
        description="Prefix for bone names",
        default="",
    )
    
    # Name Matcher properties
    source_preset: EnumProperty(
        name="Source Convention",
        description="Source naming convention",
        items=get_preset_items
    )
    target_preset: EnumProperty(
        name="Target Convention",
        description="Target naming convention",
        items=get_preset_items
    )
    
    # Weight Transfer properties
    selected_only: BoolProperty(
        name="Import to Selected Vertices",
        description="Import weights to selected vertices only.\nYou can select vertices in Edit Mode and then switch back to Object Mode or Weight Paint Mode",
        default=False
    )

class VIEW3D_PT_bone_tools(Panel):
    """Main panel for Bone Tools in the 3D View sidebar.
    
    This panel contains three main sections:
    1. Physbone Renamer: Rename physical bone chains with smart numbering
    2. Bodybone Name Matcher: Convert bone names between different conventions
    3. Weight Transfer: Export and import vertex weights
    
    The panel is only shown when an armature or mesh is selected.
    Each section can be collapsed to save space.
    """
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bone"
    bl_label = "Bone Tools"
    
    @classmethod
    def poll(cls, context):
        # Show panel when an armature or mesh is selected
        obj = context.active_object
        return obj and obj.type in {'ARMATURE', 'MESH'}
    
    def draw(self, context):
        """Draw the panel layout.
        
        This function creates the UI layout with three collapsible sections.
        Each section is enabled/disabled based on the current context:
        - Armature operations require Edit Mode
        - Weight operations require Object/Weight Paint mode
        
        Args:
            context: Blender context containing the current state
        """
        layout = self.layout
        
        obj = context.active_object
        props = context.scene.bone_tools
        
        # Physbone Renamer
        box = layout.box()
        row = box.row()
        row.prop(props, "show_physbone", text="Physbone Renamer", icon='TRIA_DOWN' if props.show_physbone else 'TRIA_RIGHT', emboss=False)
        if props.show_physbone:
            # Show error if armature is selected but not in Edit Mode
            if obj and obj.type == 'ARMATURE' and context.mode != 'EDIT_ARMATURE':
                row = box.row()
                row.alert = True
                row.label(text="Run in Edit Mode", icon='ERROR')
            
            # Prefix input in one row
            row = box.row(align=True)
            row.label(text="Enter Bone Prefix")
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.prop(props, "prefix", text="")
            
            # Selection instruction
            row = box.row()
            row.label(text="Select Physbones Except Root")
            
            # Rename button
            row = box.row()
            row.scale_y = 1.2
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.operator("bone.rename_hair_chain", text="Smart Rename")
        
        # Bodybone Name Matcher
        box = layout.box()
        row = box.row()
        row.prop(props, "show_matcher", text="Bodybone Name Matcher", icon='TRIA_DOWN' if props.show_matcher else 'TRIA_RIGHT', emboss=False)
        if props.show_matcher:
            # Show error if armature is selected but not in Edit Mode
            if obj and obj.type == 'ARMATURE' and context.mode != 'EDIT_ARMATURE':
                row = box.row()
                row.alert = True
                row.label(text="Run in Edit Mode", icon='ERROR')
            
            # Source preset in one row
            row = box.row(align=True)
            row.label(text="Source")
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.prop(props, "source_preset", text="")
            
            # Target preset in one row
            row = box.row(align=True)
            row.label(text="Target")
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.prop(props, "target_preset", text="")
            
            # Convert button
            row = box.row()
            row.scale_y = 1.2
            row.enabled = obj and obj.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'
            row.operator("armature.convert_names", text="Convert")
        
        # Weight Transfer
        box = layout.box()
        row = box.row()
        row.prop(props, "show_weights", text="Weight Transfer", icon='TRIA_DOWN' if props.show_weights else 'TRIA_RIGHT', emboss=False)
        if props.show_weights:
            # Only show error if a mesh is selected but in wrong mode
            if obj and obj.type == 'MESH' and context.mode not in {'OBJECT', 'PAINT_WEIGHT'}:
                row = box.row()
                row.alert = True
                row.label(text="Press Button in Object/Weight Mode", icon='ERROR')
            
            # Export/Import buttons in one row
            row = box.row(align=True)
            split = row.split(factor=0.5, align=True)
            col = split.column(align=True)
            col.scale_y = 1.2
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.export_weights", text="Export")
            
            col = split.column(align=True)
            col.scale_y = 1.2
            col.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            col.operator("weight.import_weights", text="Import")
            
            row = box.row()
            row.enabled = obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'PAINT_WEIGHT'}
            row.prop(props, "selected_only")
        
        # Version information at bottom
        layout.separator()
        box = layout.box()
        col = box.column()
        col.scale_y = 0.8
        col.label(text="Version: 1.1.0")
        col.label(text="Last Updated: 2025/2/25")
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
        
        Args:
            context: Blender context
            
        Returns:
            bool: True if operator can be called
        """
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    
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
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    
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

class ARMATURE_OT_convert_names(Operator):
    """Convert names between different naming conventions
    
    This operator converts names from source convention to target convention
    using the preset mapping rules.
    """
    bl_idname = "armature.convert_names"
    bl_label = "Convert Names"
    bl_description = "Convert names between different naming conventions"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if the operator can be called
        
        Args:
            context: Blender context
            
        Returns:
            bool: True if operator can be called
        """
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    
    def execute(self, context):
        """Execute the operator
        
        This function:
        - Loads source and target presets
        - Creates name mapping dictionary
        - Renames all matching bones according to mapping
        
        Args:
            context: Blender context
            
        Returns:
            set: {'FINISHED'} if successful, {'CANCELLED'} if failed
        """
        try:
            # Get properties
            props = context.scene.bone_tools
            if props.source_preset == props.target_preset:
                self.report({'WARNING'}, "Source and target conventions are the same")
                return {'CANCELLED'}
            
            # Load presets
            presets = load_presets()
            if not presets:
                self.report({'ERROR'}, "Failed to load naming presets")
                return {'CANCELLED'}
            
            source_preset = presets.get(props.source_preset)
            target_preset = presets.get(props.target_preset)
            
            if not source_preset or not target_preset:
                self.report({'ERROR'}, "Invalid preset selection")
                return {'CANCELLED'}
            
            # Create name mapping
            name_mapping = {}
            for standard_name, source_name in source_preset["bones"].items():
                target_name = target_preset["bones"].get(standard_name)
                if target_name:
                    name_mapping[source_name] = target_name
            
            # Get armature
            obj = context.active_object
            armature = obj.data
            
            # Rename all matching bones (not just selected ones)
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
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to convert names: {str(e)}")
            return {'CANCELLED'}

class WEIGHT_OT_export_weights(Operator, ExportHelper):
    """Export vertex weights to file
    
    This operator exports vertex weights data including:
    - Global vertex coordinates
    - Associated bone names and their order
    - Weight values for each bone
    
    The data is saved in JSON format for easy reading and editing.
    """
    bl_idname = "weight.export_weights"
    bl_label = "Export Weights"
    bl_description = "Export vertex weights to file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    
    def invoke(self, context, event):
        """Set default filename to object name"""
        if not self.filepath and context.active_object:
            self.filepath = context.active_object.name + self.filename_ext
        return super().invoke(context, event)
    
    @classmethod
    def poll(cls, context):
        """Check if the operator can be called
        
        This operator can be used in Object Mode and Weight Paint Mode
        with a mesh selected.
        
        Args:
            context: Blender context
            
        Returns:
            bool: True if operator can be called
        """
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'OBJECT', 'PAINT_WEIGHT'}
    
    def execute(self, context):
        try:
            obj = context.active_object
            world_matrix = obj.matrix_world
            
            # Prepare data structure with vertex groups order
            export_data = {
                "vertex_groups": [group.name for group in obj.vertex_groups],
                "vertices": []
            }
            
            # Process each vertex
            for vertex in obj.data.vertices:
                # Get global coordinates
                global_coord = world_matrix @ vertex.co
                
                # Get non-zero weights
                weights = []
                for group in obj.vertex_groups:
                    try:
                        weight = group.weight(vertex.index)
                        if weight > 0:  # Only store non-zero weights
                            weights.append({
                                "bone": group.name,
                                "weight": weight
                            })
                    except RuntimeError:
                        continue
                
                # Save vertex data if it has any weights
                if weights:
                    vertex_data = {
                        "coord": [global_coord.x, global_coord.y, global_coord.z],
                        "weights": weights
                    }
                    export_data["vertices"].append(vertex_data)
            
            # Save to file
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            self.report({'INFO'}, f"Successfully exported weights to {self.filepath}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export weights: {str(e)}")
            return {'CANCELLED'}

class WEIGHT_OT_import_weights(Operator, ImportHelper):
    """Import vertex weights from file
    
    This operator imports vertex weights data and applies it to the mesh:
    - Can import to all vertices or selected vertices
    - Matches vertices based on global coordinates
    - Creates vertex groups if they don't exist
    - Assigns weights to matched vertices
    """
    bl_idname = "weight.import_weights"
    bl_label = "Import Weights"
    bl_description = "Import vertex weights from file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'OBJECT', 'PAINT_WEIGHT'}
    
    def execute(self, context):
        try:
            # Store current mode
            current_mode = context.mode
            
            # Get import options
            props = context.scene.bone_tools
            selected_only = props.selected_only
            
            # Check if vertices are selected when needed
            if selected_only and not any(v.select for v in context.active_object.data.vertices):
                self.report({'ERROR'}, "Please select vertices in Edit Mode first")
                return {'CANCELLED'}
            
            # Load and validate weight data
            with open(self.filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate data format
            if not isinstance(import_data, dict):
                self.report({'ERROR'}, "Invalid weight file format")
                return {'CANCELLED'}
            
            if "vertex_groups" not in import_data or "vertices" not in import_data:
                self.report({'ERROR'}, "Invalid weight file format")
                return {'CANCELLED'}
            
            vertex_data = import_data["vertices"]
            if not vertex_data:
                self.report({'ERROR'}, "Weight file is empty")
                return {'CANCELLED'}
            
            obj = context.active_object
            world_matrix = obj.matrix_world
            
            # Store existing vertex groups and their order
            existing_groups = {group.name: group for group in obj.vertex_groups}
            original_order = [group.name for group in obj.vertex_groups]
            
            # Create new vertex groups at the end
            for group_name in import_data["vertex_groups"]:
                if group_name not in existing_groups:
                    obj.vertex_groups.new(name=group_name)
            
            # Get vertices to process
            if selected_only:
                vertices = [v for v in obj.data.vertices if v.select]
            else:
                vertices = obj.data.vertices
            
            # Process vertices
            for vertex in vertices:
                # Get vertex global position
                vertex_global = world_matrix @ vertex.co
                
                # Find closest source vertex
                min_dist = float('inf')
                closest_data = None
                
                for data in vertex_data:
                    source_pos = Vector(data["coord"])
                    dist = (source_pos - vertex_global).length
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_data = data
                
                if closest_data:
                    # Remove vertex from all groups first
                    for group in obj.vertex_groups:
                        group.remove([vertex.index])
                    
                    # Apply weights
                    for weight_info in closest_data["weights"]:
                        bone_name = weight_info["bone"]
                        group = obj.vertex_groups[bone_name]
                        group.add([vertex.index], weight_info["weight"], 'REPLACE')
            
            # Restore original order for existing groups
            bpy.ops.object.mode_set(mode='OBJECT')  # Ensure we're in Object Mode
            for i, group_name in enumerate(original_order):
                group = obj.vertex_groups[group_name]
                while group.index > i:
                    obj.vertex_groups.active_index = group.index
                    bpy.ops.object.vertex_group_move(direction='UP')
            
            # Restore original mode
            if current_mode == 'PAINT_WEIGHT':
                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            
            self.report({'INFO'}, f"Successfully imported weights from {self.filepath}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import weights: {str(e)}")
            return {'CANCELLED'}

def register():
    """Register all classes"""
    # 1. Register property group first
    bpy.utils.register_class(BoneToolsProperties)
    bpy.types.Scene.bone_tools = bpy.props.PointerProperty(type=BoneToolsProperties)
    
    # 2. Register operators
    bpy.utils.register_class(BONE_OT_rename_hair_chain)
    bpy.utils.register_class(BONE_OT_rename_test)
    bpy.utils.register_class(ARMATURE_OT_convert_names)
    bpy.utils.register_class(WEIGHT_OT_export_weights)
    bpy.utils.register_class(WEIGHT_OT_import_weights)
    
    # 3. Register panel last
    bpy.utils.register_class(VIEW3D_PT_bone_tools)

def unregister():
    """Unregister all classes"""
    # 1. Unregister panel first
    bpy.utils.unregister_class(VIEW3D_PT_bone_tools)
    
    # 2. Unregister operators
    bpy.utils.unregister_class(WEIGHT_OT_import_weights)
    bpy.utils.unregister_class(WEIGHT_OT_export_weights)
    bpy.utils.unregister_class(ARMATURE_OT_convert_names)
    bpy.utils.unregister_class(BONE_OT_rename_test)
    bpy.utils.unregister_class(BONE_OT_rename_hair_chain)
    
    # 3. Unregister property group last
    del bpy.types.Scene.bone_tools
    bpy.utils.unregister_class(BoneToolsProperties)

if __name__ == "__main__":
    register()
