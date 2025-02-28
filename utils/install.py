import bpy
import os
import zipfile
import tempfile
import shutil
import sys
import time
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator


def log(msg):
    # Print log message with prefix
    print(f"[Install] {msg}")

class BONE_OT_update_from_local(Operator, ImportHelper):
    bl_idname = "bone.update_from_local"
    bl_label = "Install"
    bl_description = "Select a local zip file to update the addon"
    
    filename_ext = ".zip"
    filter_glob: StringProperty(default="*.zip", options={'HIDDEN'})
    
    def execute(self, context):
        log("Validating update package")
        zip_path = self.filepath
        if not os.path.exists(zip_path):
            log("Error: File not found")
            self.report({'ERROR'}, "File not found")
            return {'CANCELLED'}
        
        log("Extracting update package")
        # Get addon directory and name
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        addon_name = os.path.basename(addon_dir)
        
        # Store modules with register function
        main_modules = {}
        for mod_name in sys.modules.keys():
            if addon_name in mod_name and hasattr(sys.modules[mod_name], 'register'):
                main_modules[mod_name] = sys.modules[mod_name]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                log("Extracting zip file")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find source directory
                extracted_folders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
                if not extracted_folders:
                    log("Error: No folders found in zip file")
                    self.report({'ERROR'}, "No folders found in zip file")
                    return {'CANCELLED'}
                
                source_dir = os.path.join(temp_dir, extracted_folders[0])
                
                log("Comparing current and new addon files")
                # List current files
                old_files_and_dirs = set()
                for root, dirs, files in os.walk(addon_dir):
                    rel_path = os.path.relpath(root, addon_dir)
                    if rel_path != '.':
                        old_files_and_dirs.add(rel_path)
                    for file in files:
                        if rel_path == '.':
                            old_files_and_dirs.add(file)
                        else:
                            old_files_and_dirs.add(os.path.join(rel_path, file))
                
                # List new files
                new_files_and_dirs = set()
                for root, dirs, files in os.walk(source_dir):
                    rel_path = os.path.relpath(root, source_dir)
                    if rel_path != '.':
                        new_files_and_dirs.add(rel_path)
                    for file in files:
                        if rel_path == '.':
                            new_files_and_dirs.add(file)
                        else:
                            new_files_and_dirs.add(os.path.join(rel_path, file))
                
                log("Updating addon files")
                # Copy new files
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)
                    d = os.path.join(addon_dir, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                
                # Remove old files not in new version
                files_to_remove = old_files_and_dirs - new_files_and_dirs
                for item in sorted(files_to_remove, key=lambda x: len(x), reverse=True):
                    item_path = os.path.join(addon_dir, item)
                    if os.path.exists(item_path):
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                
                log("Refreshing addon modules and UI")
                try:
                    # Find addon module
                    addon_module = None
                    for mod_name in bpy.context.preferences.addons.keys():
                        if addon_name in mod_name:
                            addon_module = mod_name
                            break
                    
                    try:
                        # Unregister panels and operators
                        panels_and_ops = []
                        for cls_name in dir(bpy.types):
                            if 'PT_' in cls_name or 'OT_' in cls_name:
                                cls = getattr(bpy.types, cls_name)
                                if hasattr(cls, 'bl_idname') or hasattr(cls, 'bl_label'):
                                    if addon_name.lower() in cls_name.lower() or 'bone' in cls_name.lower():
                                        panels_and_ops.append(cls)
                        for cls in panels_and_ops:
                            try:
                                bpy.utils.unregister_class(cls)
                            except:
                                pass
                    except:
                        pass
                    
                    # Remove modules from sys.modules
                    modules_to_remove = []
                    for mod_name in list(sys.modules.keys()):
                        if addon_name in mod_name or 'bone_tools' in mod_name:
                            modules_to_remove.append(mod_name)
                    for mod_name in modules_to_remove:
                        if mod_name in sys.modules:
                            del sys.modules[mod_name]
                    
                    # Call unregister on main modules
                    for mod_name, module in main_modules.items():
                        if hasattr(module, 'unregister'):
                            try:
                                module.unregister()
                            except:
                                pass
                    
                    # Reload and enable addon
                    bpy.ops.script.reload()
                    if addon_module:
                        try:
                            bpy.ops.preferences.addon_disable(module=addon_module)
                            bpy.app.timers.register(lambda: force_enable_addon(addon_module), first_interval=0.5)
                        except Exception as e:
                            log(f"Warning: Could not disable/enable addon: {str(e)}")
                    
                    # Force UI redraw
                    def force_redraw_all():
                        for window in bpy.context.window_manager.windows:
                            for area in window.screen.areas:
                                area.tag_redraw()
                        return None
                    
                    bpy.app.timers.register(force_redraw_all, first_interval=0.2)
                    bpy.app.timers.register(force_redraw_all, first_interval=1.0)
                    bpy.app.timers.register(force_redraw_all, first_interval=2.0)
                except Exception as e:
                    log(f"Warning: Error during UI refresh: {str(e)}")
                
                log("Update completed successfully")
                self.report({'INFO'}, "Addon updated successfully")
                return {'FINISHED'}
            except Exception as e:
                log(f"Error updating addon: {str(e)}")
                self.report({'ERROR'}, f"Error updating addon: {str(e)}")
                return {'CANCELLED'}


def force_enable_addon(addon_module):
    # Re-enable addon and redraw UI
    try:
        bpy.ops.preferences.addon_enable(module=addon_module)
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return None
    except Exception as e:
        log(f"Error enabling addon: {str(e)}")
        return None

# Register
def register():
    bpy.utils.register_class(BONE_OT_update_from_local)

# Unregister
def unregister():
    bpy.utils.unregister_class(BONE_OT_update_from_local) 