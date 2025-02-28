import bpy
import os
import json
import numpy as np
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, BoolProperty
from mathutils import Vector, Color
from bpy_extras.io_utils import ImportHelper, ExportHelper
from ..utils.rainbow import draw_rainbow_weights, update_rainbow_weights_display, rainbow_weights_depsgraph_update

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
            
            # Prepare vertex groups
            existing_groups = {group.name: group for group in obj.vertex_groups}
            original_order = [group.name for group in obj.vertex_groups]
            
            # Create missing vertex groups
            for group_name in import_data["vertex_groups"]:
                if group_name not in existing_groups:
                    obj.vertex_groups.new(name=group_name)
            
            # Process vertices
            if selected_only:
                vertices = [v for v in obj.data.vertices if v.select]
            else:
                vertices = obj.data.vertices
            
            for vertex in vertices:
                vertex_global = world_matrix @ vertex.co
                
                # Find closest vertex in source data
                min_dist = float('inf')
                closest_data = None
                
                for data in vertex_data:
                    source_pos = Vector(data["coord"])
                    dist = (source_pos - vertex_global).length
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_data = data
                
                # Apply weights
                if closest_data:
                    for group in obj.vertex_groups:
                        group.remove([vertex.index])
                    
                    for weight_info in closest_data["weights"]:
                        bone_name = weight_info["bone"]
                        group = obj.vertex_groups[bone_name]
                        group.add([vertex.index], weight_info["weight"], 'REPLACE')
            
            # Restore original vertex group order
            bpy.ops.object.mode_set(mode='OBJECT')
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

# Register
def register():
    bpy.utils.register_class(WEIGHT_OT_export_weights)
    bpy.utils.register_class(WEIGHT_OT_import_weights)
    
    # Register depsgraph update handler from rainbow module
    from ..utils.rainbow import register as register_rainbow
    register_rainbow()

# Unregister
def unregister():
    # Unregister rainbow module
    from ..utils.rainbow import unregister as unregister_rainbow
    unregister_rainbow()
    
    bpy.utils.unregister_class(WEIGHT_OT_import_weights)
    bpy.utils.unregister_class(WEIGHT_OT_export_weights)

if __name__ == "__main__":
    register()