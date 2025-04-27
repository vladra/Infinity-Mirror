import bpy
import mathutils
from mathutils import Vector
import bmesh #not installable via pip--must execute script via blender to access
import os
import math
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QComboBox, QLineEdit, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QLineEdit, QFormLayout
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QPixmap
from PyQt5.QtWidgets import QColorDialog
import sys
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QFileDialog

#get output from blender terminal
class EmittingStream(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass

#run pyqt5 app
app = QApplication([])

#possible settings: photo resolution, shape, frame thickness, color, number of bounces
#user can adjust input
window = QWidget()
main_layout = QHBoxLayout()
left_layout = QVBoxLayout()
right_layout = QVBoxLayout()

render_status_label = QLabel('Not Rendered')
render_status_label.setFixedSize(400, 400)  
render_status_label.setStyleSheet("background-color: lightgray;")
render_status_label.setAlignment(Qt.AlignCenter)

right_layout.addWidget(render_status_label)

shape_selector = QComboBox()
shape_selector.addItems(['Cube', 'Sphere', 'Icosphere', 'Cylinder', 'Cone', 'Torus', 'Import Shape'])

def on_shape_selected(index):
    if shape_selector.itemText(index) == 'Import Shape':
        file_selector = QPushButton('Select File')

        def open_file_dialog():
            file_path, _ = QFileDialog.getOpenFileName(window, 'Select File', '', '3D Files (*.stl *.obj *.fbx *.dae *.glb)')
            if file_path:
                file_selector.setText(file_path)

        file_selector.clicked.connect(open_file_dialog)
        left_layout.addWidget(file_selector)

        def import_shape():
            file_path = file_selector.text()
            if file_path.lower().endswith(('.stl', '.obj', '.fbx', '.dae', '.glb')):
                try:
                    if file_path.lower().endswith('.stl'):
                        bpy.ops.import_mesh.stl(filepath=file_path)
                    elif file_path.lower().endswith('.obj'):
                        bpy.ops.import_scene.obj(filepath=file_path)
                    elif file_path.lower().endswith('.fbx'):
                        bpy.ops.import_scene.fbx(filepath=file_path)
                    elif file_path.lower().endswith('.dae'):
                        bpy.ops.wm.collada_import(filepath=file_path)
                    elif file_path.lower().endswith('.glb'):
                        bpy.ops.import_scene.gltf(filepath=file_path)

                    imported_objects = bpy.context.selected_objects
                    if imported_objects:
                        imported_obj = imported_objects[0]
                        bpy.context.view_layer.objects.active = imported_obj
                        print(f"Successfully imported {file_path}")
                        print(f"Set {imported_obj.name} as active object")
                    else:
                        print("Warning: No objects selected after import!")
                except Exception as e:
                    print(f"Failed to import {file_path}: {e}")
            else:
                print("Unsupported file format. Program accepts STL, OBJ, FBX, DAE, or GLB files.")

        import_button = QPushButton('Import')
        import_button.clicked.connect(import_shape)
        left_layout.addWidget(import_button)

form_layout = QFormLayout()
left_layout.addLayout(form_layout)
shape_selector.currentIndexChanged.connect(on_shape_selected)
form_layout.addWidget(shape_selector)

resolution_width_label = QLabel('Resolution (width in pixels)')
resolution_width_input = QLineEdit()
resolution_width_input.setText('1920')  
resolution_width_input.setValidator(QIntValidator())  #int only
form_layout.addRow(resolution_width_label, resolution_width_input)

resolution_height_label = QLabel('Resolution (height in pixels)')
resolution_height_input = QLineEdit()
resolution_height_input.setText('1080')  
resolution_height_input.setValidator(QIntValidator())  #int only
form_layout.addRow(resolution_height_label, resolution_height_input)

frame_thickness_label = QLabel('Frame thickness')
frame_thickness_input = QLineEdit()
frame_thickness_input.setText('0.05') 
frame_thickness_input.setValidator(QDoubleValidator())  #floating point 
form_layout.addRow(frame_thickness_label, frame_thickness_input)

render_samples_label = QLabel('Render sample size (lower = faster)')
render_samples_input = QLineEdit()
render_samples_input.setText('5')  # default to 5
render_samples_input.setValidator(QIntValidator())  # int only
form_layout.addRow(render_samples_label, render_samples_input)

# color

color_label = QLabel('Color')
color_button = QPushButton('Select Color')
color_display = QLineEdit()
color_display.setText('#FFFFFF')  # default color to white
color_display.setReadOnly(True)

def open_color_dialog():
    color = QColorDialog.getColor()
    if color.isValid():
        color_display.setText(color.name()) 

color_button.clicked.connect(open_color_dialog)
form_layout.addRow(color_label, color_button)
form_layout.addRow(QLabel('Selected Color'), color_display)

#num bounces
num_bounces_label = QLabel('Number of bounces')
num_bounces_input = QLineEdit()
num_bounces_input.setValidator(QIntValidator())  #int only
num_bounces_input.setText('4')  # default to 4
form_layout.addRow(num_bounces_label, num_bounces_input)

# Camera position and rotation inputs
camera_position_label = QLabel('Camera Position (x, y, z)')
camera_position_input = QLineEdit()
camera_position_input.setText('0, -10, 3')  # default position

def parse_camera_position():
    try:
        return tuple(map(float, camera_position_input.text().split(',')))
    except ValueError:
        print("Invalid camera position input. Please enter values in the format: x, y, z")
        return (0, -10, 3)  # fallback to default position

form_layout.addRow(camera_position_label, camera_position_input)

camera_rotation_label = QLabel('Camera Rotation (x, y, z in degrees)')
camera_rotation_input = QLineEdit()
camera_rotation_input.setText('75, 0, 0')  # default rotation

def parse_camera_rotation():
    try:
        return tuple(map(float, camera_rotation_input.text().split(',')))
    except ValueError:
        print("Invalid camera rotation input. Please enter values in the format: x, y, z")
        return (75, 0, 0)  # fallback to default rotation

form_layout.addRow(camera_rotation_label, camera_rotation_input)

submit_button = QPushButton('Submit')


def runblender():

    print("Running...")
    obj = None 
    shape = shape_selector.currentText()

    if shape == 'Import Shape':
        imported_objects = bpy.context.selected_objects
        if imported_objects:
            obj = imported_objects[0]
            bpy.context.view_layer.objects.active = obj
            print(f"Using imported object: {obj.name}")
        else:
            raise RuntimeError("No imported object available after import.")
    else:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        if shape == 'Cube':
            bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
        elif shape == 'Sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
        elif shape == 'Icosphere':
            bpy.ops.mesh.primitive_ico_sphere_add(radius=1, location=(0, 0, 0))
        elif shape == 'Cylinder':
            bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2, location=(0, 0, 0))
        elif shape == 'Cone':
            bpy.ops.mesh.primitive_cone_add(radius1=1, depth=2, location=(0, 0, 0))
        elif shape == 'Torus':
            bpy.ops.mesh.primitive_torus_add(location=(0, 0, 0))
        else:
            raise ValueError(f"Unknown shape: {shape}")

        obj = bpy.context.active_object
        print(f"Using primitive object: {obj.name}")

    if obj is None:
        raise RuntimeError("No object selected or created.")

    obj.data.materials.clear()


    #CHANGE PARAMETER BELOW TO CHANGE FRAME THICKNESS
    frame_thickness = float(frame_thickness_input.text()) 

    bpy.context.scene.render.engine = 'CYCLES'

    #CHANGE NUMBER OF REFLECTION BOUNCES BELOW -- WILL IMPACT RENDER TIME
    bpy.context.scene.cycles.max_bounces = int(num_bounces_input.text())
    bpy.context.scene.cycles.glossy_bounces = int(num_bounces_input.text())

    #sample size--affects quality
    bpy.context.scene.cycles.samples = int(render_samples_input.text())

    ##
    ##  END OF PARAMETERS
    ##

    ##
    ## MIRROR STUFF BELOW
    ##

    # info on how to make different material on different sides of plane
    #https://blender.stackexchange.com/questions/2082/how-can-i-make-a-material-only-apply-to-a-side-of-a-plane


    mirror_mat = bpy.data.materials.new(name="MirrorMaterial")
    mirror_mat.use_nodes = True
    nodes = mirror_mat.node_tree.nodes
    links = mirror_mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    material_output = nodes.new(type="ShaderNodeOutputMaterial")

    mix_shader = nodes.new(type="ShaderNodeMixShader")

    transparent_bsdf = nodes.new(type="ShaderNodeBsdfTransparent")

    glossy_bsdf = nodes.new(type="ShaderNodeBsdfGlossy")
    glossy_bsdf.inputs["Roughness"].default_value = 0.0  

    geometry_node = nodes.new(type="ShaderNodeNewGeometry")

    links.new(geometry_node.outputs["Backfacing"], mix_shader.inputs["Fac"])
    links.new(transparent_bsdf.outputs["BSDF"], mix_shader.inputs[1])
    links.new(glossy_bsdf.outputs["BSDF"], mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], material_output.inputs["Surface"])


    obj.data.materials.clear()
    obj.data.materials.append(mirror_mat)

    bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
    interior_light = bpy.context.active_object
    interior_light.data.energy = 500  




    ##
    ## FRAME STUFF BELOW
    ##

    #create bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    beams = []

    #make beam at each edge
    for edge in bm.edges:

        #the middle of the edge will be the avg of the two vertices
        v1 = edge.verts[0].co.copy() 
        v2 = edge.verts[1].co.copy()
        middle = (v1 + v2) / 2.0

        #create beam from cube. the cube is put at middle then stretched
        bpy.ops.mesh.primitive_cube_add(size=1, location=middle)
        beam = bpy.context.active_object

        #set color via a material
        mat = bpy.data.materials.new(name="beam")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            color = color_display.text()
            if color:
                r, g, b = tuple(int(color[i:i+2], 16) / 255.0 for i in (1, 3, 5))  
                bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)  # rgba with opacity set to 1.0

        # set 
        if beam.data.materials:
            beam.data.materials[0] = mat
        else:
            beam.data.materials.append(mat)

        #need to correctly rotate the cube now
        # https://blender.stackexchange.com/questions/28478/python-script-to-align-object-to-edge-or-two-vertex-coordinates?utm_source=chatgpt.com 

        vector = v2 - v1    
        
        # https://blender.stackexchange.com/questions/19533/align-object-to-vector-using-python 

        bpy.context.object.rotation_mode = 'QUATERNION'
        bpy.context.object.rotation_quaternion = vector.to_track_quat('X','Z')
        
        #scale after rotating
        length = vector.length
        beam.scale = (length, frame_thickness, frame_thickness)
        beams.append(beam)

    bpy.ops.object.select_all(action='DESELECT')
    for beam in beams:
        beam.select_set(True)
    bpy.context.view_layer.objects.active = beams[0]
    bpy.ops.object.join()

    print("Rendering...")

    ##
    ## RENDERING STUFF BELOW
    ##
    bpy.ops.object.camera_add(location=(0, -10, 3), rotation=(math.radians(75), 0, 0))
    camera = bpy.context.object
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type='AREA', location=(4, -4, 6))
    light = bpy.context.object
    light.data.energy = 1000

    scene = bpy.context.scene
    scene.render.resolution_x = int(resolution_width_input.text())
    scene.render.resolution_y = int(resolution_height_input.text())
    scene.render.image_settings.file_format = 'PNG'

    #exports to pwd/render/
    output_path = os.path.join(os.getcwd(), "render", "infinitycube.png")
    bpy.context.scene.render.filepath = output_path

    bpy.ops.render.render(write_still=True)
    print("Successful execution")
    pixmap = QPixmap(os.path.join(os.getcwd(), "render", "infinitycube.png"))
    scaled_pixmap = pixmap.scaled(render_status_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    render_status_label.setPixmap(scaled_pixmap)
    render_status_label.setScaledContents(False)


def on_submit():
    print("Resolution Width:", resolution_width_input.text())
    print("Resolution Height:", resolution_height_input.text())
    print("Frame Thickness:", frame_thickness_input.text())
    print("Color:", color_display.text())
    print("Number of Bounces:", num_bounces_input.text())
    render_status_label.setText('Loading...')
    render_status_label.setStyleSheet("background-color: gray;")
    runblender()

submit_button.clicked.connect(on_submit)
form_layout.addWidget(submit_button)

main_layout.addLayout(left_layout)
main_layout.addLayout(right_layout)

window.setLayout(main_layout)
window.show()
app.exec()
