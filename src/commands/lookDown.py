import numpy as np

from chimerax.core.commands import CmdDesc, EnumOf
from chimerax.atomic import AtomsArg

from AaronTools.utils.utils import rotation_matrix

lookDown_description = CmdDesc(
    required=[
        ("atom1", AtomsArg),
    ],
    keyword=[
        ("atom2", AtomsArg),
        ("axis", EnumOf(["x", "y", "z"])), 
    ],
    required_arguments=["atom2"],
    synopsis="orient the molecule such that the atom1-atom2 vector is out of the screen",
)

def lookDown(session, atom1, atom2, axis="z"):
    models_g1 = dict()
    for atom in atom1:
        if atom.structure not in models_g1:
            models_g1[atom.structure] = []
        models_g1[atom.structure].append(atom)
    
    models_g2 = dict()
    for atom in atom2:
        if atom.structure not in models_g2:
            models_g2[atom.structure] = []
        models_g2[atom.structure].append(atom)
    
    if axis == "z":
        align_to = session.view.camera.get_position().axes()[2]
    if axis == "y":
        align_to = session.view.camera.get_position().axes()[1]
    if axis == "x":
        align_to = session.view.camera.get_position().axes()[0]
    
    for model in models_g1:
        if model not in models_g2:
            continue
        
        stop = sum([atom.coord for atom in models_g1[model]]) / len(models_g1[model])
        start = sum([atom.coord for atom in models_g2[model]]) / len(models_g2[model])
    
        v = stop - start
        if np.linalg.norm(v) < 1e-6:
            session.warning("short vector for model %s" % model.atomspec)
        v /= np.linalg.norm(v)
        
        rot_axis = np.cross(align_to, v)
        angle = np.arccos(np.dot(v, align_to))
        
        rot_mat = rotation_matrix(-angle, rot_axis)
        
        xyzs = model.active_coordset.xyzs
        xyzs -= start
        xyzs = np.dot(xyzs, rot_mat)
        xyzs += start
        for atom, coord in zip(model.atoms, xyzs):
            atom.coord = coord