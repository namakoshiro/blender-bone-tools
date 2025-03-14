import bpy
import os
import json
import numpy as np
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, BoolProperty, FloatProperty
from mathutils import Vector, Color, kdtree
from bpy_extras.io_utils import ImportHelper, ExportHelper

class WEIGHT_OT_export_weights(Operator, ExportHelper):
    bl_idname = "weight.export_weights"
    bl_label = "Export Weights"
    bl_description = "Export vertex weights to file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    
    def invoke(self, context, event):
        # Set default filename as the active object name
        if not self.filepath and context.active_object:
            self.filepath = context.active_object.name + self.filename_ext
        return super().invoke(context, event)
    
    @classmethod
    def poll(cls, context):
        # Check if object is mesh and is in Object Mode or Weight Paint Mode
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'OBJECT', 'PAINT_WEIGHT'}
    
    def execute(self, context):
        try:
            obj = context.active_object
            world_matrix = obj.matrix_world
            
            # Prepare export data structure
            export_data = {
                "vertex_groups": [group.name for group in obj.vertex_groups],
                "vertices": []
            }
            
            for vertex in obj.data.vertices:
                global_coord = world_matrix @ vertex.co
                
                # Get vertex weights
                weights = []
                for group in obj.vertex_groups:
                    try:
                        weight = group.weight(vertex.index)
                        if weight > 0:
                            weights.append({
                                "bone": group.name,
                                "weight": weight
                            })
                    except RuntimeError:
                        continue
                
                # Add vertex data if it has weights
                if weights:
                    vertex_data = {
                        "coord": [global_coord.x, global_coord.y, global_coord.z],
                        "weights": weights
                    }
                    export_data["vertices"].append(vertex_data)
            
            # Write to file
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            self.report({'INFO'}, f"Successfully exported weights to {self.filepath}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export weights: {str(e)}")
            return {'CANCELLED'}

class WEIGHT_OT_import_weights(Operator, ImportHelper):
    bl_idname = "weight.import_weights"
    bl_label = "Import Weights"
    bl_description = "Import vertex weights from file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    
    max_distance: FloatProperty(
        name="Max Distance",
        description="Maximum distance to search for matching vertices (0 = unlimited)",
        default=0.0,
        min=0.0,
        soft_max=10.0,
        unit='LENGTH'
    )
    
    @classmethod
    def poll(cls, context):
        # Check if object is mesh and is in Object Mode or Weight Paint Mode
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'OBJECT', 'PAINT_WEIGHT'}
    
    def execute(self, context):
        try:
            current_mode = context.mode
            
            props = context.scene.bone_tools
            selected_only = props.selected_only
            
            # Check if any vertex are selected when selected_only is true
            if selected_only and not any(v.select for v in context.active_object.data.vertices):
                self.report({'ERROR'}, "Please select vertices in Edit Mode first")
                return {'CANCELLED'}
            
            # Load weight data
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
            
            # Store original vertex group order
            original_groups = [group.name for group in obj.vertex_groups]
            
            # Prepare vertex groups
            existing_groups = {group.name: group for group in obj.vertex_groups}
            
            # Create missing vertex groups
            for group_name in import_data["vertex_groups"]:
                if group_name not in existing_groups:
                    obj.vertex_groups.new(name=group_name)
            
            # Build KD-tree for source vertices
            size = len(vertex_data)
            kd = kdtree.KDTree(size)
            
            for i, data in enumerate(vertex_data):
                kd.insert(Vector(data["coord"]), i)
            
            kd.balance()
            
            # Process vertices
            if selected_only:
                vertices = [v for v in obj.data.vertices if v.select]
            else:
                vertices = obj.data.vertices
            
            # Prepare a batch operation for better performance
            weight_operations = []
            
            for vertex in vertices:
                vertex_global = world_matrix @ vertex.co
                
                # Find closest vertex in source data
                if self.max_distance > 0:
                    # Use find_range with distance limit
                    matches = kd.find_range(vertex_global, self.max_distance)
                    if not matches:
                        continue
                    # Get the closest match
                    closest_dist, closest_idx, _ = matches[0]
                else:
                    # Use find_n to get the closest match regardless of distance
                    closest_dist, closest_idx, _ = kd.find(vertex_global)
                
                closest_data = vertex_data[closest_idx]
                
                # Store weight operations for batch processing
                weight_operations.append((vertex.index, closest_data["weights"]))
            
            # Apply weights in batch
            # First, clear weights for affected vertices
            for vertex_idx, _ in weight_operations:
                for group in obj.vertex_groups:
                    group.remove([vertex_idx])
            
            # Then apply new weights
            for vertex_idx, weights in weight_operations:
                for weight_info in weights:
                    bone_name = weight_info["bone"]
                    weight_value = weight_info["weight"]
                    if bone_name in obj.vertex_groups:
                        group = obj.vertex_groups[bone_name]
                        group.add([vertex_idx], weight_value, 'REPLACE')
            
            # Restore original vertex group order
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Get the current order of vertex groups
            current_groups = [group.name for group in obj.vertex_groups]
            
            # Reorder vertex groups to match original order
            for target_idx, group_name in enumerate(original_groups):
                if group_name in current_groups:
                    current_idx = current_groups.index(group_name)
                    if current_idx != target_idx:
                        # Set active index to the current position
                        obj.vertex_groups.active_index = current_idx
                        # Move up or down as needed
                        if current_idx > target_idx:
                            for _ in range(current_idx - target_idx):
                                bpy.ops.object.vertex_group_move(direction='UP')
                        else:
                            for _ in range(target_idx - current_idx):
                                bpy.ops.object.vertex_group_move(direction='DOWN')
                        # Update current groups list after moving
                        current_groups = [group.name for group in obj.vertex_groups]
            
            # Restore original mode
            if current_mode == 'PAINT_WEIGHT':
                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            
            # Select the first vertex group if any exist
            if obj.vertex_groups and len(obj.vertex_groups) > 0:
                obj.vertex_groups.active_index = 0
            
            self.report({'INFO'}, f"Successfully imported weights from {self.filepath}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import weights: {str(e)}")
            return {'CANCELLED'}

class WEIGHT_OT_copy_weights(Operator):
    bl_idname = "weight.copy_weights"
    bl_label = "Copy Weights"
    bl_description = "Copy vertex weights to clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'OBJECT', 'PAINT_WEIGHT'}
    
    def execute(self, context):
        try:
            obj = context.active_object
            world_matrix = obj.matrix_world
            
            # Prepare export data structure
            export_data = {
                "vertex_groups": [group.name for group in obj.vertex_groups],
                "vertices": []
            }
            
            for vertex in obj.data.vertices:
                global_coord = world_matrix @ vertex.co
                
                # Get vertex weights
                weights = []
                for group in obj.vertex_groups:
                    try:
                        weight = group.weight(vertex.index)
                        if weight > 0:
                            weights.append({
                                "bone": group.name,
                                "weight": weight
                            })
                    except RuntimeError:
                        continue
                
                # Add vertex data if it has weights
                if weights:
                    vertex_data = {
                        "coord": [global_coord.x, global_coord.y, global_coord.z],
                        "weights": weights
                    }
                    export_data["vertices"].append(vertex_data)
            
            # Convert to JSON string
            json_str = json.dumps(export_data)
            
            # Check data size
            data_size = len(json_str.encode('utf-8'))
            if data_size > 100 * 1024 * 1024:  # 100MB warning threshold
                self.report({'WARNING'}, f"Large data size ({data_size/1024/1024:.1f}MB). Clipboard transfer may fail.")
            
            # Set clipboard
            context.window_manager.clipboard = json_str
            
            self.report({'INFO'}, f"Successfully copied weights ({len(export_data['vertices'])} vertices)")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to copy weights: {str(e)}")
            return {'CANCELLED'}

class WEIGHT_OT_paste_weights(Operator):
    bl_idname = "weight.paste_weights"
    bl_label = "Paste Weights"
    bl_description = "Paste vertex weights from clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'OBJECT', 'PAINT_WEIGHT'}
    
    def execute(self, context):
        try:
            current_mode = context.mode
            
            props = context.scene.bone_tools
            selected_only = props.selected_only
            
            # Check if any vertex are selected when selected_only is true
            if selected_only and not any(v.select for v in context.active_object.data.vertices):
                self.report({'ERROR'}, "Please select vertices in Edit Mode first")
                return {'CANCELLED'}
            
            # Get clipboard data
            clipboard_data = context.window_manager.clipboard
            if not clipboard_data:
                self.report({'ERROR'}, "No data in clipboard")
                return {'CANCELLED'}
            
            try:
                import_data = json.loads(clipboard_data)
            except json.JSONDecodeError:
                self.report({'ERROR'}, "Invalid JSON data in clipboard")
                return {'CANCELLED'}
            
            # Validate data format
            if not isinstance(import_data, dict):
                self.report({'ERROR'}, "Invalid weight data format")
                return {'CANCELLED'}
            
            if "vertex_groups" not in import_data or "vertices" not in import_data:
                self.report({'ERROR'}, "Invalid weight data format")
                return {'CANCELLED'}
            
            vertex_data = import_data["vertices"]
            if not vertex_data:
                self.report({'ERROR'}, "Weight data is empty")
                return {'CANCELLED'}
            
            obj = context.active_object
            world_matrix = obj.matrix_world
            
            # Store original vertex group order
            original_groups = [group.name for group in obj.vertex_groups]
            
            # Prepare vertex groups
            existing_groups = {group.name: group for group in obj.vertex_groups}
            
            # Create missing vertex groups
            for group_name in import_data["vertex_groups"]:
                if group_name not in existing_groups:
                    obj.vertex_groups.new(name=group_name)
            
            # Build KD-tree for source vertices
            size = len(vertex_data)
            kd = kdtree.KDTree(size)
            
            for i, data in enumerate(vertex_data):
                kd.insert(Vector(data["coord"]), i)
            
            kd.balance()
            
            # Process vertices
            if selected_only:
                vertices = [v for v in obj.data.vertices if v.select]
            else:
                vertices = obj.data.vertices
            
            # Prepare a batch operation for better performance
            weight_operations = []
            
            for vertex in vertices:
                vertex_global = world_matrix @ vertex.co
                
                # Find closest vertex in source data
                closest_dist, closest_idx, _ = kd.find(vertex_global)
                closest_data = vertex_data[closest_idx]
                
                # Store weight operations for batch processing
                weight_operations.append((vertex.index, closest_data["weights"]))
            
            # Apply weights in batch
            # First, clear weights for affected vertices
            for vertex_idx, _ in weight_operations:
                for group in obj.vertex_groups:
                    group.remove([vertex_idx])
            
            # Then apply new weights
            for vertex_idx, weights in weight_operations:
                for weight_info in weights:
                    bone_name = weight_info["bone"]
                    weight_value = weight_info["weight"]
                    if bone_name in obj.vertex_groups:
                        group = obj.vertex_groups[bone_name]
                        group.add([vertex_idx], weight_value, 'REPLACE')
            
            # Restore original vertex group order
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Get the current order of vertex groups
            current_groups = [group.name for group in obj.vertex_groups]
            
            # Reorder vertex groups to match original order
            for target_idx, group_name in enumerate(original_groups):
                if group_name in current_groups:
                    current_idx = current_groups.index(group_name)
                    if current_idx != target_idx:
                        # Set active index to the current position
                        obj.vertex_groups.active_index = current_idx
                        # Move up or down as needed
                        if current_idx > target_idx:
                            for _ in range(current_idx - target_idx):
                                bpy.ops.object.vertex_group_move(direction='UP')
                        else:
                            for _ in range(target_idx - current_idx):
                                bpy.ops.object.vertex_group_move(direction='DOWN')
                        # Update current groups list after moving
                        current_groups = [group.name for group in obj.vertex_groups]
            
            # Restore original mode
            if current_mode == 'PAINT_WEIGHT':
                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            
            # Select the first vertex group if any exist
            if obj.vertex_groups and len(obj.vertex_groups) > 0:
                obj.vertex_groups.active_index = 0
            
            self.report({'INFO'}, f"Successfully pasted weights ({len(vertex_data)} vertices)")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to paste weights: {str(e)}")
            return {'CANCELLED'}

# Register
def register():
    bpy.utils.register_class(WEIGHT_OT_export_weights)
    bpy.utils.register_class(WEIGHT_OT_import_weights)
    bpy.utils.register_class(WEIGHT_OT_copy_weights)
    bpy.utils.register_class(WEIGHT_OT_paste_weights)

# Unregister
def unregister():
    bpy.utils.unregister_class(WEIGHT_OT_paste_weights)
    bpy.utils.unregister_class(WEIGHT_OT_copy_weights)
    bpy.utils.unregister_class(WEIGHT_OT_import_weights)
    bpy.utils.unregister_class(WEIGHT_OT_export_weights)

if __name__ == "__main__":
    register()