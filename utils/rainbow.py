import bpy
import colorsys
from mathutils import Vector, Color

# Global cache to store rainbow weight data for each object
rainbow_cache = {}

def generate_rainbow_colors(count):
    """Generate rainbow colors to ensure good color differentiation."""
    colors = []
    
    if count <= 10:
        # For a small number of bones, use a predefined high-contrast palette
        predefined_colors = [
            (1.0, 0.0, 0.0, 1.0),  # Red
            (0.0, 0.0, 1.0, 1.0),  # Blue
            (0.0, 0.8, 0.0, 1.0),  # Green
            (1.0, 0.7, 0.0, 1.0),  # Orange
            (0.5, 0.0, 0.5, 1.0),  # Purple
            (0.0, 0.8, 0.8, 1.0),  # Cyan
            (1.0, 1.0, 0.0, 1.0),  # Yellow
            (1.0, 0.0, 1.0, 1.0),  # Magenta
            (0.5, 0.5, 0.0, 1.0),  # Olive
            (0.0, 0.5, 0.5, 1.0),  # Teal
        ]
        return predefined_colors[:count]
    
    # For a large number of bones, use a non-linear distribution of hues
    # Use the golden ratio to create more dispersed hues
    golden_ratio_conjugate = 0.618033988749895
    h = 0.5  # Starting hue
    
    for i in range(count):
        # Generate dispersed hues using the golden ratio
        h = (h + golden_ratio_conjugate) % 1.0
        # Add some randomness to increase diversity while maintaining consistency
        seed_value = (i * 0.317 + 0.123) % 1.0
        h = (h + seed_value * 0.1) % 1.0
        
        # Use higher saturation and brightness to enhance distinguishability
        s = 0.95
        v = 0.95
        
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        colors.append((r, g, b, 1.0))
    
    return colors

def get_bone_colors(obj):
    if obj and obj.type == 'MESH' and obj.vertex_groups:
        # Generate a color for each vertex group
        groups = list(obj.vertex_groups)
        colors = generate_rainbow_colors(len(groups))
        return {group.name: colors[i] for i, group in enumerate(groups)}
    return {}

def build_vertex_to_loops_map(mesh):
    """Build a mapping from vertices to loop indices to speed up rendering."""
    vertex_to_loops = {}
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            vertex_idx = mesh.loops[loop_idx].vertex_index
            if vertex_idx not in vertex_to_loops:
                vertex_to_loops[vertex_idx] = []
            vertex_to_loops[vertex_idx].append(loop_idx)
    return vertex_to_loops

def draw_rainbow_weights():
    """Draw rainbow weight display. This function can be called directly or via a timer."""
    try:
        context = bpy.context
        
        # Check if there is an active object and scene
        if not context or not hasattr(context, 'scene') or not hasattr(context, 'active_object'):
            return None  # Timer should not repeat
            
        # Get properties
        if not hasattr(context.scene, 'bone_tools'):
            return None
            
        props = context.scene.bone_tools
        if not props.rainbow_weights:
            return None
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return None
        
        # Disable weight paint overlay to prevent it from covering the rainbow effect
        if context.mode == 'PAINT_WEIGHT':
            # Scan all 3D views and set weight paint mode overlay opacity to 0
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            # Save original settings to a global dictionary to ensure independence from scene properties
                            if not hasattr(bpy, "_rainbow_overlay_values"):
                                bpy._rainbow_overlay_values = {}
                            # Use a unique identifier as the key
                            key = f"{space.as_pointer()}"
                            # Save only once to prevent duplication
                            if key not in bpy._rainbow_overlay_values:
                                bpy._rainbow_overlay_values[key] = space.overlay.weight_paint_mode_opacity
                            # Set to 0 to completely hide weight paint overlay
                            space.overlay.weight_paint_mode_opacity = 0.0
        
        # Cache key using reliable properties to track changes
        mesh = obj.data
        
        # Build a more sensitive cache key for weight paint mode
        if context.mode == 'PAINT_WEIGHT':
            # In weight paint mode, we generate a unique cache key to ensure redraw on every update
            # This is to respond to user weight changes, referencing Blender's own weight paint overlay behavior
            cache_key = f"{obj.name}_wp_{bpy.app.driver_namespace.get('_weight_paint_frame_counter', 0)}"
            # Increment counter to ensure a different key is generated next time
            bpy.app.driver_namespace['_weight_paint_frame_counter'] = bpy.app.driver_namespace.get('_weight_paint_frame_counter', 0) + 1
        else:
            # Use standard cache key in other modes
            vertex_groups_key = "_".join(sorted([vg.name for vg in obj.vertex_groups]))
            cache_key = f"{obj.name}_{vertex_groups_key}_{obj.data.is_editmode}"
            
            # Recalculate if the object's position has changed
            if hasattr(obj, "matrix_world"):
                # Use the hash of the string representation of the matrix
                cache_key += f"_{hash(str(obj.matrix_world))}"
        
        # Check if a redraw is needed
        # Redraw every time in weight paint mode, check cache in other modes
        global rainbow_cache
        if context.mode != 'PAINT_WEIGHT' and cache_key in rainbow_cache:
            # Reuse cached settings, skipping expensive calculations
            # Just switch to vertex color display mode
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'SOLID'
                            space.shading.color_type = 'VERTEX'
                            space.shading.light = 'FLAT'
                            break
            return None
        
        # Store initial mode, switch only when needed
        prev_mode = context.mode
        
        # Check necessary conditions
        if not mesh.vertices or not obj.vertex_groups:
            return None
        
        # Get bone colors
        bone_colors = get_bone_colors(obj)
        if not bone_colors:
            return None
        
        # Attempt direct access in weight paint mode to avoid mode switching
        need_mode_switch = prev_mode != 'OBJECT' and prev_mode != 'PAINT_WEIGHT'
        
        # Switch to object mode for editing (only when needed)
        if need_mode_switch:
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Create or get vertex color layer
        if 'RainbowWeights' not in mesh.vertex_colors:
            # In weight paint mode, we need special handling for creating the vertex color layer
            if prev_mode == 'PAINT_WEIGHT':
                # Temporarily switch to OBJECT mode to create the vertex color layer
                bpy.ops.object.mode_set(mode='OBJECT')
                mesh.vertex_colors.new(name='RainbowWeights')
                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            else:
                mesh.vertex_colors.new(name='RainbowWeights')
        vcol_layer = mesh.vertex_colors['RainbowWeights']
        
        # Pre-build vertex to loop mapping to avoid nested loops
        vertex_to_loops = build_vertex_to_loops_map(mesh)
        
        # Initialize all colors to black
        for loop_idx in range(len(mesh.loops)):
            vcol_layer.data[loop_idx].color = (0, 0, 0, 1.0)
        
        # Calculate colors for each vertex
        for v_idx, vertex in enumerate(mesh.vertices):
            # Get weights
            weights = []
            for group in obj.vertex_groups:
                try:
                    weight = group.weight(v_idx)
                    if weight > 0:
                        weights.append((group.name, weight))
                except RuntimeError:
                    continue
            
            if not weights:
                continue
            
            # Calculate weighted color
            r, g, b, a = 0, 0, 0, 0
            total_weight = sum(w for _, w in weights)
            
            for group_name, weight in weights:
                if group_name in bone_colors:
                    color = bone_colors[group_name]
                    normalized_weight = weight / total_weight
                    r += color[0] * normalized_weight
                    g += color[1] * normalized_weight
                    b += color[2] * normalized_weight
                    a += normalized_weight
            
            # Apply color to all related loops using the mapping table
            if v_idx in vertex_to_loops:
                for loop_idx in vertex_to_loops[v_idx]:
                    vcol_layer.data[loop_idx].color = (r, g, b, 1.0)
        
        # Set view mode
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        space.shading.color_type = 'VERTEX'
                        space.shading.light = 'FLAT'
                        break
        
        # Update cache (non-weight paint mode)
        if context.mode != 'PAINT_WEIGHT':
            rainbow_cache[cache_key] = True
            
            # If the cache is too large, clean up the oldest entries
            if len(rainbow_cache) > 20:  # Keep a maximum of 20 cache items
                keys = list(rainbow_cache.keys())
                for old_key in keys[:-20]:  # Remove the oldest entries
                    del rainbow_cache[old_key]
                
        # Restore original mode
        if need_mode_switch and context.active_object == obj:
            bpy.ops.object.mode_set(mode=prev_mode)
            
        return None  # Let the timer know no need to repeat call
        
    except Exception as e:
        print(f"Error in Rainbow Weights: {str(e)}")
        return None  # Do not repeat call on error

def update_rainbow_weights_display(self, context):
    """Handle changes in the rainbow weights checkbox state."""
    try:
        if self.rainbow_weights:
            # Enable rainbow weight display
            # Safely call rainbow weight update, compatible with different Blender versions
            if hasattr(bpy.app, 'timers') and hasattr(bpy.app.timers, 'register'):
                # Blender 2.80+ uses timer API
                bpy.app.timers.register(draw_rainbow_weights, first_interval=0.01)
            else:
                # Directly call
                draw_rainbow_weights()
        else:
            # Clear cache
            global rainbow_cache
            rainbow_cache.clear()
            
            # Restore default display
            obj = context.active_object
            if obj and obj.type == 'MESH':
                # Restore view settings
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                # Attempt to restore to more reasonable default values
                                if context.mode == 'PAINT_WEIGHT':
                                    # If in weight paint mode, keep vertex color but use default weight display
                                    space.shading.color_type = 'VERTEX'
                                    
                                    # Restore weight paint mode overlay opacity
                                    if hasattr(bpy, "_rainbow_overlay_values"):
                                        key = f"{space.as_pointer()}"
                                        if key in bpy._rainbow_overlay_values:
                                            # Restore original value
                                            space.overlay.weight_paint_mode_opacity = bpy._rainbow_overlay_values[key]
                                            # Clear saved value
                                            del bpy._rainbow_overlay_values[key]
                                    
                                    # Switch mode only when needed
                                    if 'RainbowWeights' in obj.data.vertex_colors:
                                        # Remove rainbow weight vertex color layer
                                        try:
                                            obj.data.vertex_colors.remove(obj.data.vertex_colors['RainbowWeights'])
                                        except:
                                            pass
                                        # Force refresh
                                        current_mode = context.mode
                                        bpy.ops.object.mode_set(mode='OBJECT')
                                        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
                                else:
                                    # In other modes, restore to material display
                                    space.shading.color_type = 'MATERIAL'
                                    
                                    # Restore weight paint mode overlay opacity
                                    if hasattr(bpy, "_rainbow_overlay_values"):
                                        key = f"{space.as_pointer()}"
                                        if key in bpy._rainbow_overlay_values:
                                            # Restore original value
                                            space.overlay.weight_paint_mode_opacity = bpy._rainbow_overlay_values[key]
                                            # Clear saved value
                                            del bpy._rainbow_overlay_values[key]
            
            # Ensure all saved overlay values are cleared
            if hasattr(bpy, "_rainbow_overlay_values") and len(bpy._rainbow_overlay_values) > 0:
                bpy._rainbow_overlay_values.clear()
                
    except Exception as e:
        print(f"Error updating rainbow weights: {str(e)}")

# Variable for weight change monitoring
last_update_id = None

# Depsgraph update handler
def rainbow_weights_depsgraph_update(scene, depsgraph):
    try:
        # Check if rainbow weights are enabled and if there is an active mesh object
        if not (scene.bone_tools.rainbow_weights and 
                bpy.context.active_object and 
                bpy.context.active_object.type == 'MESH'):
            return
            
        obj = bpy.context.active_object
        
        # Declare global variables
        global rainbow_cache, last_update_id
        
        # Use direct update mechanism only in weight paint mode
        if bpy.context.mode == 'PAINT_WEIGHT':
            # Reference Blender's weight paint overlay implementation, update unconditionally
            # This ensures immediate update after each paint operation
            
            # Check if update ID has changed to prevent multiple triggers within a single frame
            current_update_id = hash(str(depsgraph.session_uuid) + str(depsgraph.scene_eval_id))
            
            if current_update_id != last_update_id:
                last_update_id = current_update_id
                
                # Clear cache and immediately redraw
                rainbow_cache.clear()
                draw_rainbow_weights()
            return
        
        # In non-weight paint mode, check for relevant updates
        update_needed = False
        
        for update in depsgraph.updates:
            if update.id:
                # Only update if the update is related to the current object or its vertex groups
                if (update.id == obj or 
                    update.id == obj.data or
                    isinstance(update.id, bpy.types.VertexGroup) and update.id.id_data == obj):
                    update_needed = True
                    break
        
        if update_needed:
            # Update immediately, no delay needed
            rainbow_cache.clear()
            draw_rainbow_weights()
            
    except Exception as e:
        print(f"Error in depsgraph update: {str(e)}")

def register():
    # Clear any old handler references
    global rainbow_cache
    rainbow_cache = {}
    
    # Register depsgraph update handler, ensuring it is not added multiple times
    if rainbow_weights_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(rainbow_weights_depsgraph_update)
    bpy.app.handlers.depsgraph_update_post.append(rainbow_weights_depsgraph_update)

def unregister():
    # Clear cache
    global rainbow_cache
    rainbow_cache.clear()
    
    # Clear counter
    if '_weight_paint_frame_counter' in bpy.app.driver_namespace:
        del bpy.app.driver_namespace['_weight_paint_frame_counter']
        
    # Remove handler
    if rainbow_weights_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(rainbow_weights_depsgraph_update)
    
    # If there is a timer, attempt to cancel it
    if hasattr(bpy.app, 'timers') and hasattr(bpy.app.timers, 'unregister'):
        if draw_rainbow_weights in bpy.app.timers.registered():
            bpy.app.timers.unregister(draw_rainbow_weights)
    
    # Attempt to delete any saved properties
    if hasattr(bpy, "_rainbow_overlay_values"):
        # Restore all saved overlay values
        try:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            key = f"{space.as_pointer()}"
                            if key in bpy._rainbow_overlay_values:
                                space.overlay.weight_paint_mode_opacity = bpy._rainbow_overlay_values[key]
        except:
            pass
        # Finally clear the dictionary
        bpy._rainbow_overlay_values.clear()
        delattr(bpy, "_rainbow_overlay_values") 