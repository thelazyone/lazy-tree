bl_info = {
    "name": "Lazy Tree",
    "author": "thelazyone - Giacomo pantalone",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "View3D > Sidebar > Create",
    "description": "Generate tree meshes, from the ground up",
    "warning": "",
    "doc_url": "",
    "category": "Add Mesh",
}

import sys
import os
import bpy
import bmesh
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty

# for split logic.
import random
import math

# TODO add seed for noise, same of Random!
from mathutils import Vector, Matrix 

# This path is used only for the development workflow.
# When loading this as an addon this path is irrelevant.
current_script_dir = bpy.context.space_data.text.filepath
if current_script_dir not in sys.path:
    sys.path.append(current_script_dir)

# Importing the rest of the files.
import importlib
import math_functions
importlib.reload(math_functions)
import noise_displacements
importlib.reload(noise_displacements)
import tree_section
importlib.reload(tree_section)
from tree_section import Section
import tree_general_functions
importlib.reload(tree_general_functions)
import tree_light_functions
importlib.reload(tree_light_functions)
import tree_armature_functions
importlib.reload(tree_armature_functions)
from tree_armature_functions import *
import tree_mesh_functions
importlib.reload(tree_mesh_functions)
from tree_mesh_functions import create_section_mesh


def update_tree(self, context):
    bpy.ops.growtree.create_tree()


class GROWTREE_PG_tree_parameters(bpy.types.PropertyGroup):

    # General Properties
    seed: bpy.props.IntProperty(name="Seed", default=0, update=update_tree)
    iterations: bpy.props.IntProperty(name="Iterations", default=20, min=0, max=1024, update=update_tree)
    radius: bpy.props.FloatProperty(name="Trunk Base Radius", default=0.5, min=0.1, max=10, update=update_tree)
    trunk_branches_division_2D: bpy.props.FloatVectorProperty(name="Trunk Branches divisions", default=(0.2, 0.8), min = 0, max = 1, size=2, update=update_tree)

    # Branching
    split_chance_2D: bpy.props.FloatVectorProperty(name="Split Chance %", default=(0.5, 1), min = 0, max = 10, size=2, update=update_tree)
    split_angle: bpy.props.FloatProperty(name="Split Angle (deg)", default=45, min=0, max=90, update=update_tree)
    split_angle_randomness: bpy.props.FloatProperty(name="Split Angle Randomness (deg)", default=10, min=0, max=90, update=update_tree)
    split_ratio_2D: bpy.props.FloatVectorProperty(name="Branch Split Ratio", default=(0.4, 0.1), min=0.1, max=0.5, size=2, update=update_tree)
    split_ratio_random: bpy.props.FloatProperty(name="Branch Split Ratio Randomness", default=0.1, min=0, max=1,  update=update_tree)
    segment_length_2D: bpy.props.FloatVectorProperty(name="Segment Length", default=(0.1, 0.1), min=0, max=10, size=2, update=update_tree)
    tree_ground_factor: bpy.props.FloatProperty(name="Ground Trunk Factor", default=0.2, min=0, max=1, update=update_tree)
    min_length_2D: bpy.props.FloatVectorProperty(name="Average Lenght", default=(10, 5), min=1, max=100, size=2, update=update_tree)

    # Roots
    roots_starting_angle: bpy.props.FloatProperty(name="Roots Starting Angle", default=45, min=0, max=120, update=update_tree)
    roots_starting_position: bpy.props.FloatProperty(name="Roots Starting Position", default=2, min=0, max=120, update=update_tree)
    roots_amount: bpy.props.IntProperty(name="Roots Amount", default=6, min=0, max=36, update=update_tree)
    roots_spread: bpy.props.FloatProperty(name="Roots Spread", default=0.95, min=0, max=1, update=update_tree)
    roots_propagation: bpy.props.FloatProperty(name="Roots Propagation", default=5, min=0.1, max=20, update=update_tree)
    roots_noise: bpy.props.FloatProperty(name="Roots Noise", default=.5, min=0, max=1, update=update_tree)
    root_segment_length:bpy.props.FloatProperty(name="Roots Segment Lenght", default=.1, min=0, max=2, update=update_tree)

    # Deformation
    light_source_3D: bpy.props.FloatVectorProperty(name="Light Source", default=(0, 0, 100), update=update_tree)
    light_searching_2D: bpy.props.FloatVectorProperty(name="Light Searching", default=(0.5, 0.5), min=0, max=2, size=2, update=update_tree)
    light_searching_fringes: bpy.props.FloatProperty(name="Light Searching Fringes", default=3, min=0, max=10, update=update_tree)
    ground_avoiding: bpy.props.FloatProperty(name="Ground Avoiding", default=0.5, min=0, max=5, update=update_tree)
    trunk_gravity: bpy.props.FloatProperty(name="Trunk Gravity", default=0.2, min=0, max=1, update=update_tree)
    noise_2D: bpy.props.FloatVectorProperty(name="Growth Noise", default=(0.5, 0.5), min=0, max=10, size=2, update=update_tree)
    noise_scale_2D: bpy.props.FloatVectorProperty(name="Volumetric Noise Scale", default=(1, 0.2), min=0.01, max=5, size=2, update=update_tree)
    noise_intensity_2D: bpy.props.FloatVectorProperty(name="Volumetric Noise Intensity", default=(1, 0.2), min=0.01, max=5, size=2, update=update_tree)

    # Meshing
    generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=False, update=update_tree)
    branch_resolution: bpy.props.IntProperty(name="Branch Resolution", default=8, min=3, max=64, update=update_tree)
    minimum_thickness: bpy.props.FloatProperty(name="Min Thickness", default=0.05, min=0.01, max=0.5, update=update_tree)
    chunkyness: bpy.props.FloatProperty(name="Chunkyness", default=0.5, min=0.1, max=2, update=update_tree)
    surface_noise_planar_2D: bpy.props.FloatVectorProperty(name="Surface Planar Noise Scale", default=(0.4, 0.2), min=0.01, max=5, size=2, update=update_tree)
    surface_noise_vertical_2D: bpy.props.FloatVectorProperty(name="Surface Vertical Noise Scale", default=(0.4, 0.2), min=0.01, max=5, size=2, update=update_tree)
    surface_noise_intensity_2D: bpy.props.FloatVectorProperty(name="Surface Noise Intensity", default=(0.4, 0.2), min=0.01, max=5, size=2, update=update_tree)


class GROWTREE_OT_create_tree(bpy.types.Operator):
    bl_idname = "growtree.create_tree"
    bl_label = "Create Tree"
    bl_options = {'REGISTER', 'UNDO'}

    tree_parameters: bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)

    def execute(self, context):
        tree_parameters = context.scene.tree_parameters

        mesh = self.create_tree_mesh(tree_parameters)
        obj_name = "Created Tree"
        
        # Unlink and remove the old object if it exists
        if obj_name in bpy.data.objects:
            old_obj = bpy.data.objects[obj_name]
            if old_obj.name in context.collection.objects:
                context.collection.objects.unlink(old_obj)
            bpy.data.objects.remove(old_obj)

        # Create a new object and link it to the scene
        obj = bpy.data.objects.new(obj_name, mesh)
        context.collection.objects.link(obj)

        return {'FINISHED'}

    def create_tree_mesh(self, tree_parameters):

        mesh = bpy.data.meshes.new("Tree")
        bm = bmesh.new()

        # Setting the random seed
        random.seed(tree_parameters.seed)

        # Creating the tree body
        trunk_section = Section( \
            points=[Vector((0, 0, 0)),Vector((0, 0, 0.1))], \
            weight=tree_parameters.iterations, \
            depth=1,\
            distance=1)
        sections = [trunk_section]

        # Growing iterations
        for iteration_number in range(tree_parameters.iterations):
            grow_step(sections, tree_parameters, iteration_number)
            new_sections = check_splits(sections, tree_parameters, iteration_number)

            # Extending only if a pair of new section exists.
            sections.extend(new_sections)                

        # Applying Noise 
        sections = apply_noise(sections, tree_parameters)

        # Creating the roots: very similar to the branches, but not quite.
        root_sections = create_root_sections(tree_parameters)
        for iteration_number in range(tree_parameters.iterations):
            grow_root(root_sections, tree_parameters, iteration_number)
        root_sections = apply_roots_sinking(root_sections, tree_parameters)

        # Extending sections with the root sections:
        sections.extend(root_sections)

        # Creating main mesh
        mesh = bpy.data.meshes.new("Tree")
        bm = bmesh.new()
        
        # If the "Generate Mesh" button is selected.
        if tree_parameters.generate_mesh:
            section_matrix = Matrix.Identity(4)
            
            # Generate mesh with cylinders
            for section in sections:
                section_mesh = create_section_mesh(section, tree_parameters)
                temp_bm = bmesh.new()
                temp_bm.from_mesh(section_mesh)
                temp_bm.transform(section_matrix)
                bmesh.ops.transform(temp_bm, matrix=section_matrix, verts=temp_bm.verts)
                bmesh.ops.contextual_create(temp_bm, geom=temp_bm.edges)
                vertex_map = {}

                for v in temp_bm.verts:
                    new_vert = bm.verts.new(v.co)
                    vertex_map[v.index] = new_vert
                bm.verts.ensure_lookup_table()

                for e in temp_bm.edges:
                    bm.edges.new([vertex_map[e.verts[0].index], vertex_map[e.verts[1].index]])
                bm.edges.ensure_lookup_table()

                for f in temp_bm.faces:
                    bm.faces.new([vertex_map[v.index] for v in f.verts])  # Add this line
                bm.faces.ensure_lookup_table()  # Add this line

                temp_bm.free()

        else:
            # Generate mesh with segments
            for section in sections:
                v0 = bm.verts.new(section.points[0])
                for i in range(len(section.points) - 1):
                    v1 = bm.verts.new(section.points[i + 1])
                    bm.edges.new([v0, v1])
                    v0 = v1

        bm.to_mesh(mesh)  # Keep this line
        bm.free()  # Keep this line

        return mesh


# Blender GUI
class GROWTREE_PT_create_tree_panel(bpy.types.Panel):
    bl_label = "Grow Tree"
    bl_idname = "GROWTREE_PT_create_tree_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Create'

    def draw_prop(self, box, tree_parameters, prop_name):
        if '_2D' in prop_name:  # if the property is a 2D vector
            row = box.row()
            row.prop(tree_parameters, prop_name)
        elif '_3D' in prop_name:  # if the property is a 2D vector
            row = box.row()
            row.prop(tree_parameters, prop_name)
        else:
            box.prop(tree_parameters, prop_name)

    def draw(self, context):
        layout = self.layout
        tree_parameters = context.scene.tree_parameters

        box = layout.box()
        box.label(text="General Properties")
        props = ["seed", "iterations", "radius", "trunk_branches_division_2D"]
        for prop_name in props:
            self.draw_prop(box, tree_parameters, prop_name)

        box = layout.box()
        box.label(text="Branching")
        props = ["split_chance_2D", "split_angle", "split_angle_randomness", 
                 "split_ratio_2D", "split_ratio_random", "segment_length_2D",
                 "tree_ground_factor", "min_length_2D"]
        for prop_name in props:
            self.draw_prop(box, tree_parameters, prop_name)

        box = layout.box()
        box.label(text="Roots")
        props = ["roots_starting_angle", "roots_starting_position", "roots_amount", 
                 "roots_spread", "roots_propagation", "roots_noise", "root_segment_length"]
        for prop_name in props:
            self.draw_prop(box, tree_parameters, prop_name)

        box = layout.box()
        box.label(text="Deformation")
        props = ["light_source_3D", "light_searching_2D", "light_searching_fringes", 
                 "ground_avoiding", "trunk_gravity", "noise_2D", 
                 "noise_scale_2D", "noise_intensity_2D"]
        for prop_name in props:
            self.draw_prop(box, tree_parameters, prop_name)

        box = layout.box()
        box.label(text="Meshing")
        props = ["generate_mesh", "branch_resolution", "minimum_thickness", 
                 "chunkyness", "surface_noise_planar_2D", "surface_noise_vertical_2D", 
                 "surface_noise_intensity_2D"]
        for prop_name in props:
            self.draw_prop(box, tree_parameters, prop_name)

        layout.operator(GROWTREE_OT_create_tree.bl_idname)


def menu_func(self, context):
    self.layout.operator(GROWTREE_OT_create_tree.bl_idname)

# Register / Unregister boilerplate
def register():
    bpy.utils.register_class(GROWTREE_PG_tree_parameters)
    bpy.utils.register_class(GROWTREE_OT_create_tree)
    bpy.utils.register_class(GROWTREE_PT_create_tree_panel)
    bpy.types.Scene.tree_parameters = bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_class(GROWTREE_PG_tree_parameters)
    bpy.utils.unregister_class(GROWTREE_OT_create_tree)
    bpy.utils.unregister_class(GROWTREE_PT_create_tree_panel)
    del bpy.types.Scene.tree_parameters
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()