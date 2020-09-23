import numpy as np

import re

from AaronTools.atoms import Atom
from AaronTools.const import TMETAL
from AaronTools.geometry import Geometry
from AaronTools.ring import Ring

from chimerax.atomic import AtomicStructure
from chimerax.atomic import Residue as ChimeraResidue
from chimerax.atomic import Atom as ChixAtom
from chimerax.atomic.colors import element_color

from warnings import warn


def fromChimAtom(atom=None, *args, serial_number=None, atomspec=None, **kwargs):
    """get AaronTools Atom object from ChimeraX Atom"""
    aarontools_atom = Atom(*args, name=str(atom.serial_number), element=str(atom.element), coords=atom.coord, **kwargs)
    
    aarontools_atom.add_tag(atom.atomspec)
    aarontools_atom.atomspec = atom.atomspec
    aarontools_atom.serial_number = atom.serial_number
    aarontools_atom.chix_atom = atom

    return aarontools_atom
   

class Residue(Geometry):
    """Residue is an intermediary between chimerax Residues and AaronTools Geometrys
    Residue has the following attributes:
    resnum      - same as chimerax Residue.number
    name        - same as chimerax Residue.name
    """
    def __init__(self, geom, resnum=None, atomspec=None, chain_id=None, name=None, **kwargs):      
        if isinstance(geom, ChimeraResidue):
            aaron_atoms = []
            for atom in geom.atoms:
                if not atom.deleted:                      
                    aaron_atom = fromChimAtom(atom=atom)
                    aaron_atoms.append(aaron_atom)
            
            self.chix_residue = geom
            
            super().__init__(aaron_atoms, name=geom.name, **kwargs)
            if resnum is None:
                self.resnum = geom.number
            else:
                self.resnum = resnum
                
            if atomspec is None:
                self.atomspec = geom.atomspec
            else:
                self.atomspec = atomspec
                
            if chain_id is None:
                self.chain_id = geom.chain_id
            else:
                self.chain_id = chain_id
            
        else:
            if name is None:
                name = "UNK"
            super().__init__(geom, **kwargs)
            self.name = name
            self.resnum = resnum
            self.atomspec = atomspec
            self.chix_residue = None
            if chain_id is None:
                self.chain_id = "a"
            else:
                self.chain_id = chain_id

    def get_element_count(self):
        """returns a dictionary with element symbols as keys and values corresponding to the
        occurences of an element in self's atoms"""
        out = {}
        for atom in self.atoms:
            if atom.element not in out:
                out[atom.element] = 1
            else:
                out[atom.element] += 1
                
        return out
    
    def update_chix(self, chix_residue, refresh_connected=True):
        """changes chimerax residue to match self"""
        elements = {}
        known_atoms = []

        #print("updating residue", self.name, chix_residue.name)

        chix_residue.name = self.name

        #print("updating residue:")
        #print(self.write(outfile=False))
        
        for atom in self.atoms:
            #print(atom, hasattr(atom, "chix_atom"))
            if not hasattr(atom, "chix_atom") or \
               atom.chix_atom is None or \
               atom.chix_atom.deleted or atom.chix_atom not in chix_residue.atoms:
                #if not hasattr(atom, "chix_atom"):
                #    print("no chix atom", atom)
                #elif atom.chix_atom is None:
                #    print("no chix atom yet", atom)
                #elif atom.chix_atom.deleted:
                #    print("chix_atom deleted", atom)
                #else:
                #    print("atoms do not match", atom.chix_atom)
                    
                atom_name = "%s1" % atom.element
                k = 1
                while any([chix_atom.name == atom_name for chix_atom in chix_residue.atoms]):
                    k += 1
                    atom_name = "%s%i" % (atom.element, k)
                
                #print("new chix atom for", atom)
                
                new_atom = chix_residue.structure.new_atom(atom_name, atom.element)
                new_atom.draw_mode = ChixAtom.BALL_STYLE
                new_atom.color = element_color(new_atom.element.number)
                new_atom.coord = atom.coords
                
                chix_residue.add_atom(new_atom)
                atom.chix_atom = new_atom
                known_atoms.append(new_atom)

            else:
                atom.chix_atom.coord = atom.coords
                known_atoms.append(atom.chix_atom)
                
        for atom in chix_residue.atoms:
            if atom not in known_atoms:
                #print("deleting %s" % atom.atomspec)
                atom.delete()

        if refresh_connected:
            self.refresh_chix_connected(chix_residue)

        for atom in chix_residue.atoms:
            if atom.serial_number == -1:
                atom.serial_number = atom.structure.atoms.index(atom) + 1

    def refresh_chix_connected(self, chix_residue):
        known_bonds = []
        known_chix_bonds = []
        residue_bonds = [bond for bond in chix_residue.structure.bonds if bond.atoms[0] in chix_residue.atoms and bond.atoms[1] in chix_residue.atoms]
        
        for i, aaron_atom1 in enumerate(self.atoms):
            atom1 = [atom for atom in chix_residue.atoms if aaron_atom1.chix_atom == atom][0]
            for aaron_atom2 in self.atoms[:i]:
                if aaron_atom2 not in aaron_atom1.connected:
                    continue

                if sorted((aaron_atom1, aaron_atom2,)) in known_bonds:
                    continue
                
                known_bonds.append(sorted((aaron_atom1, aaron_atom2,)))

                atom2 = [atom for atom in chix_residue.atoms if atom == aaron_atom2.chix_atom]
                if len(atom2) > 0:
                    atom2 = atom2[0]
                else:
                    #we cannot draw a bond to an atom that is not in the residue
                    #this could happen when previewing a substituent or w/e with the libadd tool
                    continue
                
                try:
                    new_bond = chix_residue.structure.new_bond(atom1, atom2)

                    if any([aaron_atom.element in TMETAL for aaron_atom in [aaron_atom1, aaron_atom2]]):
                        pbg = chix_residue.structure.pseudobond_group(chix_residue.structure.PBG_METAL_COORDINATION, create_type='normal') 
                        pbg.new_pseudobond(atom1, atom2)
                        new_bond.delete()
                    else:
                        known_chix_bonds.append(new_bond)
                except Exception as e:
                    bond = [bond for bond in residue_bonds if atom1 in bond.atoms and atom2 in bond.atoms]
                    if len(bond) != 1:
                        continue
                    else:
                        bond = bond[0]
                        
                    if bond not in known_chix_bonds:
                        known_chix_bonds.append(bond)
                    pass
        
        for bond in residue_bonds:
            if bond not in known_chix_bonds:
                bond.delete()


class ResidueCollection(Geometry):
    """geometry object used for SEQCROW to easily convert to AaronTools but keep residue info"""
    def __init__(self, molecule, convert_residues=None, **kwargs):
        """molecule       - chimerax AtomicStructure or [AtomicStructure] or AaronTools Geometry (for easy compatibility stuff)
        convert_residues  - None to convert everything or [chimerax.atomic.Residue] to convert only specific residues
                            this only applies to chimerax AtomicStructures"""
        self.convert_residues = convert_residues
        
        if isinstance(molecule, AtomicStructure):
            self.chix_atomicstructure = molecule
            self.residues = []
            self.atomspec = molecule.atomspec
            
            #convert chimerax stuff to AaronTools
            all_atoms = []
            if convert_residues is None:
                convert_residues = molecule.residues
            for i, residue in enumerate(convert_residues):  
                new_res = Residue(residue, \
                                  comment=molecule.comment if hasattr(molecule, "comment") else None, \
                          )
                
                self.residues.append(new_res)
                
                all_atoms.extend(new_res.atoms)
            
            super().__init__(all_atoms, name=molecule.name, comment=molecule.comment if hasattr(molecule, "comment") else "", **kwargs)
        
            #update bonding to match that of the chimerax molecule
            for atom in all_atoms:
                for atom2 in all_atoms:
                    if atom2.chix_atom not in atom.chix_atom.neighbors:
                        continue
                    
                    atom.connected.add(atom2)
                            
                    
            #for bond in molecule.bonds:
            #    atom1 = bond.atoms[0]
            #    atom2 = bond.atoms[1]
            #    if self.convert_residues is not None and (atom1.residue not in self.convert_residues or atom2.residue not in self.convert_residues):
            #        continue
            #    
            #    aaron_atom1 = [atom for atom in all_atoms if atom.chix_atom is atom1][0]
            #    aaron_atom2 = [atom for atom in all_atoms if atom.chix_atom is atom2][0]
            #
            #    aaron_atom1.connected.add(aaron_atom2)
            #    aaron_atom2.connected.add(aaron_atom1)
            
            #add bonds to metals
            tm_bonds = molecule.pseudobond_group(molecule.PBG_METAL_COORDINATION, create_type=None)
            if tm_bonds is not None:
                for pseudobond in tm_bonds.pseudobonds:
                    atom1, atom2 = pseudobond.atoms
                    if self.convert_residues is not None and (atom1.residue not in self.convert_residues or atom2.residue not in self.convert_residues):
                        continue
                    
                    aaron_atom1 = self.find(atom1.atomspec)[0]
                    aaron_atom2 = self.find(atom2.atomspec)[0]
                    aaron_atom1.connected.add(aaron_atom2)
                    aaron_atom2.connected.add(aaron_atom1)
                    
        else:
            #assume whatever we got is something AaronTools can turn into a Geometry
            super().__init__(molecule, **kwargs)
            self.chix_atomicstructure = None
            self.atomspec = None
            if "comment" in kwargs:
                self.residues = [Residue(molecule, resnum=1, name="UNK", comment=kwargs['comment'])]
            elif hasattr(molecule, "comment"):
                self.residues = [Residue(molecule, resnum=1, name="UNK", comment=molecule.comment)]
            else:
                self.residues = [Residue(molecule, resnum=1, name="UNK")]

            return
  
    def _atom_update(self):
        old_atoms = [a for a in self.atoms]
        self.atoms = []
        for res in self.residues:
            self.atoms.extend([a for a in res.atoms if a in old_atoms])

    def map_ligand(self, *args, **kwargs):
        """map_ligand, then put new atoms in the residue they are closest to"""
        super().map_ligand(*args, **kwargs)
        
        atoms_not_in_residue = []
        for atom in self.atoms:
            if not any(atom in residue for residue in self.residues):
                atoms_not_in_residue.append(atom)
        
        new_lig = Residue(atoms_not_in_residue, name="LIG", resnum=len(self.residues)+1)
        self.residues.append(new_lig)

        for residue in self.residues:
            remove_atoms = []
            for atom in residue.atoms:
                if atom not in self.atoms:
                    remove_atoms.append(atom)
            
            for atom in remove_atoms:
                residue.atoms.remove(atom)

    def substitute(self, sub, target, *args, **kwargs):
        """find the residue that target is on and substitute it for sub"""
        target = self.find(target)
        if len(target) != 1:
            raise RuntimeError("substitute can only apply to one target at a time: %s" % ", ".join(str(t) for t in target))
        else:
            target = target[0]
            
        residue = self.find_residue(target)
        if len(residue) != 1:
            raise RuntimeError("multiple or no residues found containing %s" % str(target))
        else:
            residue = residue[0]
        
        residue.substitute(sub, target, *args, **kwargs)

        self._atom_update()

    def ring_substitute(self, target, ring, *args, **kwargs):
        """put a ring on the given targets"""
        if not isinstance(ring, Ring):
            ring = Ring(ring)

        residue = self.find_residue(target[0])[0]
        
        super().ring_substitute(target, ring)

        new_atoms = [atom for atom in self.atoms if not hasattr(atom, "chix_atom")]
        residue.atoms.extend(new_atoms)

        for res in self.residues:
            deleted_atoms = []
            for atom in res.atoms:
                if not hasattr(atom, "chix_atom"):
                    continue

                if atom.chix_atom.residue is not res.chix_residue and atom in self.atoms:
                    deleted_atoms.append(atom)
                elif atom not in self.atoms:
                    deleted_atoms.append(atom)
                
            for atom in deleted_atoms:
                res.atoms.remove(atom)

    def find_residue(self, target):
        """returns a list of residues containing the specified target"""
        atom = self.find(target)
        if len(atom) != 1:
            raise LookupError("multiple or no atoms found for %s" % target)
        else:
            atom = atom[0]
        
        out = []
        for residue in self.residues:
            if target in residue.atoms:
                out.append(residue)
                
        return out

    def difference(self, atomic_structure):
        """returns {'geom missing':[chimerax.atomic.Atom], 'chix missing':[ChimAtom]} 
        'geom missing' are atoms that are missing from self but are on the ChimeraX AtomicStructure
        'chix missing' are atoms that are on self but not on the ChimeraX AtomicStructure"""
        
        geom_missing = []
        chix_missing = []
        
        for atom in self.atoms:
            if not hasattr(atom, "chix_atom") or atom.chix_atom not in atomic_structure.atoms:
                chix_missing.append(atom)
               
        for atom in atomic_structure.atoms:
            if not any([atom == aaron_atom.chix_atom for aaron_atom in self.atoms if hasattr(aaron_atom, "chix_atom")]) \
                    and (atom.residue in self.convert_residues or self.convert_residues is None):
                geom_missing.append(atom)
                
        out = {'geom missing': geom_missing, 'chix missing': chix_missing}
        return out
    
    def update_chix(self, atomic_structure):
        """update chimerax atomic structure to match self
        may also change residue numbers for self"""

        atomic_structure.comment = self.comment

        for residue in self.residues:
            if residue.chix_residue is None or \
               residue.chix_residue.deleted or \
               residue.chix_residue not in atomic_structure.residues:
                res = atomic_structure.new_residue(residue.name, residue.chain_id, residue.resnum)
                residue.chix_residue = res
            else:
                res = residue.chix_residue
            
            try:
                residue.update_chix(res, refresh_connected=False)
            except RuntimeError:
                # somtimes I get an error saying the residue has already
                # been deleted even though I checked if chix_residue.deleted...
                # maybe all the atoms got deleted?
                res = atomic_structure.new_residue(residue.name, residue.chain_id, residue.resnum)
                residue.chix_residue = res
                
        if self.convert_residues is None:
            for residue in atomic_structure.residues:
                if not any(residue is res.chix_residue for res in self.residues):
                    residue.delete()            
            
            for residue in atomic_structure.residues[len(self.residues):]:
                residue.delete()

        else:
            for residue in atomic_structure.residues:
                if residue in self.convert_residues and not any(residue is res.chix_residue for res in self.residues):
                    residue.delete()

        self.refresh_chix_connected(atomic_structure, sanity_check=False)

    def refresh_chix_connected(self, atomic_structure, sanity_check=True):
        """updates atomic_structure's bonds to match self's connectivity
        sanity_check - bool; check to make sure atomic_structure corresponds to self"""
        if sanity_check:
            diff = self.difference(atomic_structure)
            for key in diff:
                if len(diff[key]) != 0:
                    raise Exception("ResidueCollection does not correspond to AtomicStructure: \n%s\n\n%s" % \
                        (repr(self), repr(ResidueCollection(atomic_structure))))
                    
        for bond in atomic_structure.bonds:
            if self.convert_residues is None or all(atom.residue in self.convert_residues for atom in bond.atoms):
                bond.delete()

        known_bonds = []
        for i, aaron_atom1 in enumerate(self.atoms):
            atom1 = [atom for atom in atomic_structure.atoms if aaron_atom1.chix_atom is atom][0]

            for aaron_atom2 in aaron_atom1.connected:
                if sorted((aaron_atom1, aaron_atom2,)) in known_bonds:
                    continue
                
                if not hasattr(aaron_atom2, "chix_atom"):
                    print(aaron_atom2, "has no chix_atom")
                
                known_bonds.append(sorted((aaron_atom1, aaron_atom2,)))

                atom2 = [atom for atom in atomic_structure.atoms if atom == aaron_atom2.chix_atom]
                if len(atom2) > 0:
                    atom2 = atom2[0]
                else:
                    #we cannot draw a bond to an atom that is not in the residue
                    #this could happen when previewing a substituent or w/e with the libadd tool
                    continue
                
                if atom2 not in atom1.neighbors:
                    new_bond = atomic_structure.new_bond(atom1, atom2)

                    if any([aaron_atom.element in TMETAL for aaron_atom in [aaron_atom1, aaron_atom2]]):
                        pbg = atomic_structure.pseudobond_group(atomic_structure.PBG_METAL_COORDINATION, create_type='normal') 
                        pbg.new_pseudobond(atom1, atom2)
                        new_bond.delete()

    def all_geom_coordsets(self, filereader):
        if filereader.all_geom is None:
            warn("coordsets requested, but the file contains one or fewer sets of coordinates")
            coordsets = struc.coordset(1)
        else:
            coordsets = np.zeros((len(filereader.all_geom), len(self.atoms), 3))
            for i, all_geom in enumerate(filereader.all_geom):
                if not all([isinstance(a, Atom) for a in all_geom]):
                    atom_list = [l for l in all_geom if isinstance(l, list) and len(l) == len(self.atoms)][0]
                else:
                    atom_list = all_geom
                for j, atom in enumerate(atom_list):
                    coordsets[i][j] = atom.coords

        return coordsets                    
    
    def get_chimera(self, session, coordsets=False, filereader=None):
        """returns a chimerax equivalent of self"""
        struc = AtomicStructure(session, name=self.name)
        struc.comment = self.comment

        self.update_chix(struc)

        if coordsets and filereader is not None and filereader.all_geom is not None:
            #make a trajectory
            #each list of atoms in filereader.all_geom is a frame in the trajectory
            #replace previous coordinates
            #this matters when a filereader is given because the
            #geometry created from a filereader (which was probably passed as geom)
            #is the last geometry in the log or xyz file
            xyzs = self.all_geom_coordsets(filereader)
            struc.add_coordsets(xyzs, replace=True)

        return struc