import bpy
import os
import json
import re
import zipfile
import tempfile
import shutil
import sys
import time
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator
import urllib.request
import urllib.error

def log(msg):
    # Print log message with prefix
    print(f"[Update Online] {msg}")

_latest_tag_name = ""

GITHUB_API_URL = "https://api.github.com/repos/namakoshiro/blender-bone-tools/releases/latest"

class BONE_OT_update_from_online(Operator):
    bl_idname = "bone.update_from_online"
    bl_label = "Update from Online"
    bl_description = "Check and download updates from GitHub"
    
    def get_current_version(self):
        # Read version from __init__.py
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        init_file = os.path.join(addon_dir, "__init__.py")
        with open(init_file, 'r') as f:
            content = f.read()
        version_match = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', content)
        if version_match:
            return (int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3)))
        return None
    
    def get_latest_version_api(self):
        # Get latest version from GitHub API
        api_url = GITHUB_API_URL
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Mozilla/5.0'
        }
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=1) as response:
            data = json.loads(response.read().decode('utf-8'))
            tag_name = data['tag_name']
            version_match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', tag_name)
            if version_match:
                return ((int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3))), tag_name)
        return None, None
    
    def execute(self, context):
        global _latest_tag_name
        
        self.report({'INFO'}, "Checking for updates...")
        log("Getting current version")
        current_version = self.get_current_version()
        if not current_version:
            log("Error: Could not determine current version")
            self.report({'ERROR'}, "Could not determine current version")
            return {'CANCELLED'}
        log(f"Current version: {current_version[0]}.{current_version[1]}.{current_version[2]}")
        
        log("Retrieving latest version")
        latest_version, tag_name = self.get_latest_version_api()
        if not latest_version:
            log("Error: Could not retrieve latest version")
            self.report({'ERROR'}, "Could not retrieve latest version")
            return {'CANCELLED'}
        version_str = f"{latest_version[0]}.{latest_version[1]}.{latest_version[2]}"
        log(f"Latest version: {version_str}")
        
        _latest_tag_name = tag_name
        
        log("Comparing versions")
        # Check if update is needed
        is_newer = False
        if latest_version[0] > current_version[0]:
            is_newer = True
        elif latest_version[0] == current_version[0] and latest_version[1] > current_version[1]:
            is_newer = True
        elif latest_version[0] == current_version[0] and latest_version[1] == current_version[1] and latest_version[2] > current_version[2]:
            is_newer = True
        if not is_newer:
            log("No update required. Current version is up-to-date.")
            self.report({'INFO'}, f"You already have the latest version ({current_version[0]}.{current_version[1]}.{current_version[2]}) installed")
            return {'FINISHED'}
        
        log(f"Update available from {current_version[0]}.{current_version[1]}.{current_version[2]} to {version_str}")
        
        # Store version info in window manager
        context.window_manager["update_new_version"] = version_str
        context.window_manager["update_current_version"] = f"{current_version[0]}.{current_version[1]}.{current_version[2]}"
        
        bpy.ops.bone.show_update_dialog('INVOKE_DEFAULT')
        
        return {'FINISHED'}

class BONE_OT_show_update_dialog(Operator):
    bl_idname = "bone.show_update_dialog"
    bl_label = "Update Available"
    bl_description = "Show update confirmation dialog"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def invoke(self, context, event):
        # Show dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=200)
    
    def draw(self, context):
        # Draw dialog content
        layout = self.layout
        wm = context.window_manager
        
        new_version = wm.get("update_new_version", "unknown")
        current_version = wm.get("update_current_version", "unknown")
        
        layout.label(text=f"New version {new_version} is available!")
        layout.label(text=f"Current version: {current_version}")
        layout.label(text="Do you want to update?")
    
    def execute(self, context):
        # Confirm update
        bpy.ops.bone.confirm_update()
        return {'FINISHED'}
    
    def cancel(self, context):
        # Cancel update
        bpy.ops.bone.cancel_update()
        return {'CANCELLED'}

class BONE_OT_confirm_update(Operator):
    bl_idname = "bone.confirm_update"
    bl_label = "Confirm Update"
    bl_description = "Confirm and download the update"
    
    def execute(self, context):
        global _latest_tag_name
        
        tag = _latest_tag_name
        if not tag:
            log("Error: No version specified")
            self.report({'ERROR'}, "No version specified")
            return {'CANCELLED'}
        
        # Format version string
        version_match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', tag)
        version_str = tag
        if version_match:
            version_str = f"{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}"
        
        log(f"Downloading update {version_str}")
        download_url = f"https://github.com/namakoshiro/blender-bone-tools/releases/download/{tag}/blender-bone-tools-{tag}.zip"
        self.report({'INFO'}, f"Downloading update {version_str}...")
        
        # Download update
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_path = temp_file.name
            req = urllib.request.Request(download_url)
            req.add_header('Accept', 'application/octet-stream')
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(temp_path, 'wb') as out_file:
                    out_file.write(response.read())
        except Exception as e:
            log(f"Download error: {str(e)}")
            self.report({'ERROR'}, f"Download error: {str(e)}")
            return {'CANCELLED'}
        
        log("Installing update")
        self.report({'INFO'}, "Installing update...")
        if not self.install_update(temp_path):
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            log("Error during installation")
            self.report({'ERROR'}, "Failed to install update")
            return {'CANCELLED'}
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        log("Refreshing UI")
        self.refresh_ui()
        log(f"Update to version {version_str} completed successfully")
        self.report({'INFO'}, f"Update to version {version_str} completed successfully!")
        return {'FINISHED'}
            
    def install_update(self, zip_path):
        log("Starting installation")
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        
        if not os.path.exists(zip_path):
            log(f"Error: Update package not found at {zip_path}")
            self.report({'ERROR'}, "Update package not found")
            return False
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                log(f"Extracting zip to {temp_dir}")
                try:
                    # Extract zip file
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        file_list = zip_ref.namelist()
                        log(f"Zip contains {len(file_list)} entries")
                        zip_ref.extractall(temp_dir)
                        log("Extraction completed")
                except Exception as e:
                    log(f"Error during extraction: {str(e)}")
                    self.report({'ERROR'}, f"Extraction error: {str(e)}")
                    return False
                
                all_extracted = os.listdir(temp_dir)
                log(f"Extracted content: {all_extracted}")
                
                # Find source directory
                source_dir = temp_dir
                extracted_folders = [f for f in all_extracted if os.path.isdir(os.path.join(temp_dir, f))]
                
                for folder in extracted_folders:
                    if "blender-bone-tools" in folder.lower():
                        source_dir = os.path.join(temp_dir, folder)
                        log(f"Found specific addon folder: {folder}")
                        break
                if source_dir == temp_dir and extracted_folders:
                    source_dir = os.path.join(temp_dir, extracted_folders[0])
                    log(f"Using first subfolder as source: {extracted_folders[0]}")
                
                log(f"Using source directory: {source_dir}")
                
                if not os.path.exists(os.path.join(source_dir, "__init__.py")):
                    log("Error: Source directory does not contain __init__.py")
                    self.report({'ERROR'}, "Invalid addon structure in zip file")
                    return False
                
                try:
                    log("Scanning current addon files")
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
                    
                    log("Scanning new addon files")
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
                except Exception as e:
                    log(f"Error during file scanning: {str(e)}")
                    self.report({'ERROR'}, f"File scanning error: {str(e)}")
                    return False
                
                try:
                    log("Copy new files to addon directory")
                    # Update files by copying
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
                    
                    return True
                except Exception as e:
                    log(f"File system error: {str(e)}")
                    self.report({'ERROR'}, f"File system error: {str(e)}")
                    return False
                
        except Exception as e:
            log(f"Unexpected error during installation: {str(e)}")
            self.report({'ERROR'}, f"Installation error: {str(e)}")
            return False
    
    def refresh_ui(self):
        # Reload addon and refresh UI
        log("Refreshing UI")
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        addon_name = os.path.basename(addon_dir)
        modules_to_remove = []
        for mod_name in list(sys.modules.keys()):
            if addon_name in mod_name:
                modules_to_remove.append(mod_name)
        for mod_name in modules_to_remove:
            if mod_name in sys.modules:
                del sys.modules[mod_name]
        bpy.ops.script.reload()
        addon_module = None
        for mod_name in bpy.context.preferences.addons.keys():
            if addon_name in mod_name:
                addon_module = mod_name
                break
        if addon_module:
            bpy.ops.preferences.addon_disable(module=addon_module)
            bpy.ops.preferences.addon_enable(module=addon_module)
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return True

class BONE_OT_cancel_update(Operator):
    bl_idname = "bone.cancel_update"
    bl_label = "Cancel Update"
    bl_description = "Cancel the update process"
    
    def execute(self, context):
        # Cancel update
        self.report({'INFO'}, "Update cancelled")
        return {'FINISHED'}

# Register
def register():
    bpy.utils.register_class(BONE_OT_update_from_online)
    bpy.utils.register_class(BONE_OT_confirm_update)
    bpy.utils.register_class(BONE_OT_cancel_update)
    bpy.utils.register_class(BONE_OT_show_update_dialog)

# Unregister
def unregister():
    bpy.utils.unregister_class(BONE_OT_cancel_update)
    bpy.utils.unregister_class(BONE_OT_confirm_update)
    bpy.utils.unregister_class(BONE_OT_update_from_online)
    bpy.utils.unregister_class(BONE_OT_show_update_dialog)