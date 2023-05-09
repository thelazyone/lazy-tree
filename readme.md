# Lazy Tree Generator

A ground-up approach to tree generator, as a Blender addon.

# Introduction
Unlike most of the other (excellent) tree generators, LTG focuses on generating 3D-printable models using a combination of watertight meshes with additional attention to minimum thicknesses and branches directions. Currently the addon doesn't create a fully-functional tree: roots must be cropped manually and I'd recommend a general tree remeshing.
The initial design of this generator aimed to a true bottom-up simulation, keeping all the design parameters as little emulative as possible, but currently the generation follows something in between: .ost of the rules are "local", there is no "tree shape" parameter and each branch is (almost) not aware of its position on the tree, but at the same time there are some global filters to keep the shapes printable.

# Installation
Install the lazy-tere.py files within the Blender add-ons interface. Tested with Blender 3.4

# TO-DOs
Future versions of the script should implement several more features:
* Add general presets
* Group parameters in different sections each with a preset
* Allow to save and load the options.
* Implement a pruning logic, that adds a chance for thin branches to break over time depending on the weight on them and the number of iterations (If a branch is broken, the child branches won't be displayed)


# Licensing
Check out the LICENSE.txt file. The TL;DR would be "use it for whatever, but not to sell models, please".
