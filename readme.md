# Lazy Tree Generator

A ground-up approach to a 3D-printer-friendly tree generator, as a Blender addon.
![TreeBanner](https://github.com/thelazyone/lazy-tree/assets/10134358/9101992e-1458-4406-97da-630dfaa76a77 "Examples of generated trees, with extrenal bark texture added")

# Introduction
Unlike most of the other (excellent) tree generators, LTG focuses on generating 3D-printable models using a combination of watertight meshes with additional attention to minimum thicknesses and branches directions. Currently the addon doesn't create a fully-functional tree: roots must be cropped manually and I'd recommend a general tree remeshing.
The initial design of this generator aimed to a true bottom-up simulation, keeping all the design parameters as little emulative as possible, but currently the generation follows something in between: .ost of the rules are "local", there is no "tree shape" parameter and each branch is (almost) not aware of its position on the tree, but at the same time there are some global filters to keep the shapes printable.

# Installation
Install the lazy-tere.py files within the Blender add-ons interface. Tested with Blender 3.4

# Getting started
Once the plugin is installed, you should find yourself a tab "Create" on the properties panel on the right.
You *will* likely be overwhelmed by the amount of parameters, which yet need to be organized in sections with brief tooltips or labels. Till then, keep the following pointers in mind: 
* The plugin updates the tree every time a parameter change. This means that dragging a value causes multiple generations, resulting in a real-time movement.
* If the "Generate Mesh" is ticked, the tree will be generated with the whole mesh; otherwise, only the "graph" of the tree armature is shown. I'd recommend using the latter if you want to experiment with real-time parameters changes.
* The resulting mesh is composed of a separated watertight mesh for each branch section. Remeshing is always an option.
* The roots are programmed to grow until they get fully under Z = 0.
* The "Create Tree" button allows to recreate the tree even if no parameters have changed. It's wonky, and a better UX will be implemented.
<img width="890" alt="image" src="https://github.com/thelazyone/lazy-tree/assets/10134358/80bdc087-cea5-4381-8255-99dbda951754">


# TO-DOs
Future versions of the script should implement several more features:
* Add general presets
* Group parameters in different sections each with a preset
* Allow to save and load the options.
* Implement a pruning logic, that adds a chance for thin branches to break over time depending on the weight on them and the number of iterations (If a branch is broken, the child branches won't be displayed)


# Licensing
Check out the LICENSE.txt file. The TL;DR would be "use it for whatever, but not to sell models, please".
