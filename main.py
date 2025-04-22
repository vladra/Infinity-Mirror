import bpy
import mathutils
from mathutils import Vector
import bmesh #not installable via pip--must execute script via blender to access
import os
import math

print("Running...")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

#THIS IS WHERE WE CREATE THE SHAPE. CHANGE LINE BELOW TO CHANGE SHAPE OF STRUCTURE
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object

#CHANGE PARAMETER BELOW TO CHANGE FRAME THICKNESS
frame_thickness = 0.02

bpy.context.scene.render.engine = 'CYCLES'

#CHANGE NUMBER OF REFLECTION BOUNCES BELOW -- WILL IMPACT RENDER TIME
bpy.context.scene.cycles.max_bounces = 2
bpy.context.scene.cycles.glossy_bounces = 2

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
bpy.ops.object.camera_add(location=(0, -5, 1), rotation=(math.radians(75), 0, 0))
camera = bpy.context.object
bpy.context.scene.camera = camera

bpy.ops.object.light_add(type='AREA', location=(4, -4, 6))
light = bpy.context.object
light.data.energy = 1000

scene = bpy.context.scene
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.image_settings.file_format = 'PNG'

#exports to pwd/render/
output_path = os.path.join(os.getcwd(), "render", "infinitycube.png")
bpy.context.scene.render.filepath = output_path

bpy.ops.render.render(write_still=True)
print("Successful execution")
