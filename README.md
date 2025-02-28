## [**👉 Download Latest Version 👈**](https://github.com/namakoshiro/blender-bone-tools/releases/latest)

- **For first time installation**
    - Drag the Zip file into Blender and click "OK"
    - Search for `Bone Tools` in `Preferences` > `Add-ons`
    - Make sure `Bone Tools` is enabled
    - Press shortcut key `N` in viewport to open the `N-Panel`

- **For update from previous version to 1.2.0**  
    - Drag the `Zip` into Blender and click `OK`
    - `Restart` Blender to complete the update

- **For update from version 1.2.0**  
    - Press `Update from online` button to update the addon online
    - If it's not working, please download the latest version from the [`Release Page`](https://github.com/namakoshiro/blender-bone-tools/releases/latest)
    - Press `Update from local` button and select `Zip` file to update the addon

## **😊 Information**

**This is a Blender addon to manage bones and weights**  

- Author: [`namakoshiro`](https://x.com/namakoshiro)  
- Version: `1.2.0`  
- Last Updated: `2025/2/28`  

## **📖 How to Use**

### **Physbone Renamer**
Rename physical bone chains (skirt, hair, tail, etc.) with a hierarchy numbering system `Prefix_n_n_n`
- Enter a prefix
- Select bone chains except `Root` bone
- Click the button

<img width="640" alt="RootNotSelected" src="https://github.com/user-attachments/assets/99d795a6-d8b1-4ced-a603-886ee25a9b64" />  

### **Name Matcher**
Convert names of body bones (including eyes and fingers) between different naming conventions
- Select `Source` and `Target` naming conventions
- Click the button  

The naming convention presets now include  
`AutoRigPro` `VRChat` `MikuMikuDance` `Unity` `Mixamo` `VRoid`    

### **Weight Transfer**
Export vertex weights as files and import them to other objects, even in different projects  

- Import weights to all vertices of the object
    - Select an object
    - Click the `Export` button to export vertex weights as a file
    - Import the file to another object in any Blender project

- Import weights to selected vertices of the object  
    - Select some vertices in `Edit Mode`
    - Back to `Object Mode` or `Weight Paint Mode`
    - Import the file to selected vertices only

## **Update History**

- **1.2.0 (2025/2/28)**
    - Convert to multi-file system
    - New feature: Update from online/local

- **1.1.0 (2025/2/25)**
    - New feature: Name Matcher
    - New feature: Weight Transfer

- **1.0.0 (2025/1/18)**
    - Public release