import numpy as np

def seqcrow_bse(session):
    """non-H atoms are displayed with B&S
    H atoms are displayed with S
    atoms colored by Jmol colors"""

    from AaronTools.const import RADII
    from chimerax.atomic import AtomicStructure, Atom, Bond
    from chimerax.atomic.colors import element_color
    
    view = session.main_view
    view.set_background_color([1., 1., 1., 0])
    view.silhouette.enabled = True
    
    lighting_profile = view.lighting
    
    lighting_profile.key_light_intensity = 1.
    lighting_profile.depth_cue = True
    lighting_profile.shadows = False
    lighting_profile.multishadow = 0
    lighting_profile.fill_light_intensity = 0.5
    lighting_profile.ambient_light_intensity = 0.4
    lighting_profile.key_light_color = [1., 1., 1., 0]
    lighting_profile.fill_light_color = [1., 1., 1., 0]
    lighting_profile.ambient_light_color = [1., 1., 1., 0]
    lighting_profile.depth_cue_color = [1., 1., 1.]
    
    view.update_lighting = True
    view.redraw_needed = True

    geoms = session.models.list(type=AtomicStructure)
    
    for geom in geoms:
        geom.ball_scale = 0.4
        for bond in geom.bonds:
            bond.halfbond = True
            bond.radius = 0.16
            bond.hide = False
            
        for atom in geom.atoms:
            ele = atom.element.name
            color = element_color(atom.element.number)
            if hasattr(atom, "ghost"):
                color = tuple(*color, atom.color[-1])
                
            atom.color = color
            
            if ele in RADII:
                #AaronTools has bonding radii, maybe I should use vdw?
                #check to see how necessary this is
                atom.radius = RADII[ele]
            
            if ele != 'H':
                atom.draw_mode = Atom.BALL_STYLE
            elif len(atom.neighbors) > 1:
                atom.radius = 0.625
                atom.draw_mode = Atom.BALL_STYLE
            else:
                atom.draw_mode = Atom.STICK_STYLE

def seqcrow_s(session):
    """atoms are represented with sticks
    atoms colored by Jmol colors"""

    from AaronTools.const import RADII
    from chimerax.atomic import AtomicStructure, Atom, Bond
    from chimerax.atomic.colors import element_color
    
    view = session.main_view
    view.set_background_color([1., 1., 1., 0])
    view.silhouette.enabled = True

    lighting_profile = view.lighting
    
    lighting_profile.key_light_intensity = 1.
    lighting_profile.depth_cue = True
    lighting_profile.shadows = True
    lighting_profile.multishadow = 64
    lighting_profile.multishadow_map_size = 1024
    lighting_profile.multishadow_depth_bias = 0.01
    lighting_profile.fill_light_intensity = 0.5
    lighting_profile.ambient_light_intensity = 0.4
    lighting_profile.key_light_color = [1., 1., 1., 0]
    lighting_profile.fill_light_color = [1., 1., 1., 0]
    lighting_profile.ambient_light_color = [1., 1., 1., 0]
    lighting_profile.depth_cue_color = [1., 1., 1.]

    view.update_lighting = True
    view.redraw_needed = True
    
    geoms = session.models.list(type=AtomicStructure)
    
    for geom in geoms:
        geom.ball_scale = 0.625
        for bond in geom.bonds:
            bond.halfbond = True
            bond.radius = 0.25
            bond.hide = False
            
        for atom in geom.atoms:
            ele = atom.element.name
            color = element_color(atom.element.number)
            if hasattr(atom, "ghost"):
                color = tuple(*color, atom.color[-1])
             
            atom.color = color
            
            if len(atom.neighbors) == 0:
                atom.draw_mode = Atom.BALL_STYLE
                if ele in RADII:
                    atom.radius = RADII[ele]
            
            else:
                atom.draw_mode = Atom.STICK_STYLE

def indexLabel(session):
    from chimerax.core.objects import Objects
    from chimerax.atomic import AtomicStructure, Atoms
    from chimerax.label.label3d import label
    
    for m in session.models.list(type=AtomicStructure):
        for i, atom in enumerate(m.atoms):
            l = str(i+1)
            label(session, objects=Objects(atoms=Atoms([atom])), object_type='atoms', \
                text=l, offset=(-0.11*len(l),-0.2,-0.2), height=0.4, on_top=True)

