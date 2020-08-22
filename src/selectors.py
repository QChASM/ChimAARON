import numpy as np

from chimerax.atomic import AtomicStructure, Atoms, Atom
from chimerax.core.commands import register_selector

from AaronTools.atoms import BondOrder
from AaronTools.substituent import Substituent
from AaronTools.geometry import Geometry
from AaronTools.const import TMETAL
from AaronTools.utils.prime_numbers import Primes

from SEQCROW.residue_collection import ResidueCollection

from collections import deque

Primes()
BondOrder()

def register_selectors(logger, name):
    if name == "tm":
        register_selector("tm", tm_selector, logger, desc="transition metals")

    elif any(name == sub for sub in Substituent.list()):
        register_selector(name, 
                          lambda sess, models, results, sub_name=name:
                              substituent_selection(sess, sub_name, models, results),
                          logger,
                          desc="substituent %s" % name
        )
    
def tm_selector(session, models, results):
    """select transition metals using AaronTools' TMETAL dictionary"""
        
    atoms = []
    for model in models:
        if isinstance(model, AtomicStructure):
            for atom in model.atoms:
                if atom.element.name in TMETAL:
                    atoms.append(atom)
    
    #need to add a Collection, not just a list of atoms
    results.add_atoms(Atoms(atoms))

#reimplemented some AaronTools but with chimerax stuff because of 
#performace reasons
def substituent_selection(session, sub_name, models, results): 
    #TODO: optimize
    #TODO: make it so it doesn't select things with just an H bonded to them
    #      e.g. sel OH should not select water molecules
    #      probably do a get_all_connected for each fragment and
    #      check if all_connected.subtract(Atoms[atom]).subtract(frag) leave just an H
    atoms = Atoms()
    
    sub = Substituent(sub_name)
    chix_sub = ResidueCollection(sub).get_chimera(session)
    sub_elements = sorted(chix_sub.atoms.elements.names)
    sub_ranks = canonical_rank(Atoms(chix_sub.atoms))
    sorted_sub_atoms = [x for _, x in sorted(zip(sub_ranks, chix_sub.atoms), key = lambda pair: pair[0])]
    
    length = len(sub.atoms)
    
    found = False
    
    for model in models:
        if isinstance(model, AtomicStructure):
            for atom in model.atoms:
                #session.logger.info("checking groups on %s" % atom.atomspec)
                for bonded_atom in atom.neighbors:
                    if bonded_atom.element.name != sub.atoms[0].element:
                        continue
                    #session.logger.info("fragment for %s" % bonded_atom.atomspec)
                    frag = get_fragment(model, bonded_atom, atom, length)
                    frag = frag.subtract(Atoms([atom]))

                    if len(frag) != length:
                        continue

                    elements = sorted(frag.elements.names)
                    
                    if sub_elements != elements:
                        continue

                    frag_ranks = canonical_rank(frag)
                    
                    #session.logger.warning(", ".join(sub_elements))
                    #session.logger.warning("%s;\n%s" % (", ".join(str(x) for x in sorted(frag_ranks)), ", ".join(str(x) for x in sorted(sub_ranks))))
                    
                    sorted_frag_atoms = [x for _, x in sorted(zip(frag_ranks, frag.instances()), key = lambda pair: pair[0])]
                    #session.logger.warning("%s;\n%s" % (", ".join(x.atomspec for x in sorted_frag_atoms), ", ".join(x.name for x in sorted_sub_atoms)))
                    for a, b in zip(sorted_frag_atoms, sorted_sub_atoms):
                        #session.logger.info("%s %s" % (a.atomspec, b.name))
                        if a.element.name != b.element.name:
                            #session.logger.info("different elements")
                            break

                        #session.logger.info("bonded: %s; other: %s" % (bonded_atom.atomspec, atom.atomspec))

                        if a is not bonded_atom and len(a.neighbors) != len(b.neighbors):
                            #session.logger.info("different num neighbors")
                            #session.logger.info("%s and %s" % (a.atomspec, b.name))
                            #session.logger.info("%i vs %i" % (len(a.neighbors), len(b.neighbors)))
                            break
                        elif a is bonded_atom and (len(a.neighbors) - 1) != len(b.neighbors):
                            #session.logger.info("first atom, different num neighbors")
                            #session.logger.info("%s and %s" % (a.atomspec, b.name))
                            #session.logger.info("%i vs %i" % (len(a.neighbors) - 1, len(b.neighbors)))
                            break
                            
                        failed = False
                        for i, j, k in zip(
                            sorted([aa.element.name for aa in a.neighbors]), 
                            sorted([bb.element.name for bb in b.neighbors]), 
                            [x for _, x in sorted(zip([aa.element.name for aa in a.neighbors], [aa for aa in a.neighbors]), key=lambda pair: pair[0])], 
                        ):
                            if a is bonded_atom and k is atom:
                                continue
                            
                            if i != j:
                                #session.logger.info("failed %s %s %s" % i, j, k.atomspec)
                                failed = True
                                break
                            
                        if failed:
                            break
                    
                    else:
                        atoms = atoms.merge(frag)
    
    results.add_atoms(atoms)

def get_fragment(atoms, start, stop, max_len):
    """
    see AaronTools.geometry.Geometry.get_fragment
    """

    stack = deque([start])
    frag = Atoms([start])
    while len(stack) > 0 and len(frag) <= max_len:
        connected = stack.popleft()
        connected = Atoms(connected.neighbors).subtract(Atoms([stop]))
        connected = connected.subtract(frag)
        stack.extend(connected.instances())
        frag = frag.merge(connected)

    return frag

def get_invariant(atom, atoms):
    """gets initial invariant
    (1) number of non-hydrogen connections (\d{1}): nconn
    (2) sum of bond order of non-hydrogen bonds * 10 (\d{2}): nB
    (3) atomic number (\d{3}): z
    #(4) sign of charge (\d{1})
    #(5) absolute charge (\d{1})
    (6) number of attached hydrogens (\d{1}): nH
    """
    #atom is chimerax atom
    heavy = set([x for x in atom.neighbors if x.element.name != "H" and x in atoms])
    # number of non-hydrogen connections:
    nconn = len(heavy)
    # number of bonds with heavy atoms
    nB = 0
    for h in heavy:
        nB += bond_order(h, atom)
    # number of connected hydrogens
    nH = len([x for x in atom.neighbors if x in atoms]) - len(heavy)
    # atomic number
    z = atom.element.number

    return "{:01d}{:03d}{:03d}{:01d}".format(
        int(nconn), int(nB * 10), int(z), int(nH)
    )
    
def bond_order(atom1, atom2):
    #atom is chimerax atom
    ele1 = atom1.element.name
    ele2 = atom2.element.name
    
    try:
        key = " ".join(sorted([ele1, ele2]))
        bonds = BondOrder.bonds[key]
    except KeyError:
        if ele1 == "H" or ele2 == "H":
            return 1
        else:
            BondOrder.warn_atoms.add((ele1, ele2))
            return 1
        
    dist = np.linalg.norm(atom1.coord - atom2.coord)
    closest = 0, None
    for order, length in bonds.items():
        diff = abs(length - dist)
        if closest[1] is None or diff < closest[1]:
            closest = order, diff
    
    return float(closest[0])

def canonical_rank(structure, heavy_only=False, break_ties=True):
    """see AaronTools.geometry.Geometry.canonical_rank
    structure is Atoms collection"""
    primes = Primes.list(len(structure.instances()))
    atoms = []
    ranks = []

    def neighbors_rank(ranks):
        # partitions key is product of rank and neighbors' rank
        # use prime numbers for product so products are distinct
        # eg: primes[2]*primes[2] != primes[1]*primes[4]
        partitions = {}
        for i, a in enumerate(atoms):
            key = primes[ranks[i]]
            for b in a.neighbors:
                if b in atoms:
                    key *= primes[ranks[atoms.index(b)]]
            partitions.setdefault(ranks[i], {})
            partitions[ranks[i]].setdefault(key, [])
            partitions[ranks[i]][key] += [i]
        return update_ranks(ranks, partitions)

    def update_ranks(ranks, partitions):
        new_ranks = ranks.copy()
        for rank, key_dict in partitions.items():
            if len(key_dict) == 1:
                continue
            for key in sorted(key_dict.keys()):
                for idx in key_dict[key]:
                    new_ranks[idx] = rank
                rank += len(key_dict[key])
        return new_ranks

    def tie_break(ranks):
        """
        Uses atom angles around COM -> shared_atom axis to break ties[
        Does not break symmetry (eg: pentane carbons still [0, 2, 4, 2, 0]
        because C2 and C4 are ~180 deg apart relative to COM-C5 axis)
        """

        def get_angle(vi, vj, norm):
            dot = np.dot(vi, vj)
            cross = np.cross(vi, vj)
            det = np.dot(norm, cross)
            rv = np.arctan2(det, dot)
            return round(rv, 1)

        partitions = {}
        for i, rank in enumerate(ranks):
            partitions.setdefault(rank, {})
            partitions[rank].setdefault(rank, [])
            partitions[rank][rank] += [i]

        new_partitions = partitions.copy()
        for rank, rank_dict in partitions.items():
            idx_list = rank_dict[rank]
            if len(idx_list) == 1:
                continue
            # split ties into groups connected to same atom
            groups = {}
            for i in idx_list[:-1]:
                a = atoms[i]
                for j in idx_list[1:]:
                    b = atoms[j]
                    connected = [x for x in a.neighbors if x in b.neighbors]
                    if len(connected) == 1:
                        k = connected.pop()
                        if k in atoms:
                            k = atoms.index(k)
                        else:
                            continue
                        groups.setdefault(k, set([i]))
                        groups[k] |= set([j])
            # atoms in each group sorted in counter clockwise order
            # around axis between shared atom and COM
            for shared_idx, connected in groups.items():
                shared = atoms[shared_idx]
                connected = sorted(connected)
                center = np.mean(structure.coords, axis=0)
                norm = shared.coord - center
                start_idx = None
                min_dist = None
                for c in connected:
                    this = np.linalg.norm(atoms[c].coord - center)
                    if min_dist is None or this < min_dist:
                        min_dist = this
                        start_idx = c
                start = atoms[start_idx].coord - shared.coord
                angles = {0: [start_idx]}
                for c in connected:
                    if c == start_idx:
                        continue
                    this = atoms[c].coord - shared.coord
                    angle = get_angle(start, this, norm)
                    angles.setdefault(angle, [])
                    angles[angle] += [c]
                for i, angle in enumerate(sorted(angles.keys())):
                    new_partitions[rank].setdefault(rank + i, [])
                    new_partitions[rank][rank + i] += angles[angle]
                    for idx in angles[angle]:
                        new_partitions[rank][rank].remove(idx)
                break
        return update_ranks(ranks, new_partitions)

    # rank all atoms the same initially
    for a in structure.instances():
        if heavy_only and a.element.name == "H":
            continue
        atoms += [a]
        ranks += [0]

    # partition and re-rank using invariants
    partitions = {}
    for i, a in enumerate(atoms):
        invariant = get_invariant(a, atoms)
        partitions.setdefault(invariant, [])
        partitions[invariant] += [i]
    new_rank = 0
    for key in sorted(partitions.keys()):
        idx_list = partitions[key]
        for idx in idx_list:
            ranks[idx] = new_rank
        new_rank += len(idx_list)

    # re-rank using neighbors until no change
    for i in range(500):
        new_ranks = neighbors_rank(ranks)
        if ranks == new_ranks:
            break
        ranks = new_ranks
    else:
        warn("Max cycles reached in canonical sorting (neighbor-ranks)")

    # break ties using spatial positions
    # AND update neighbors until no change
    if break_ties:
        for i in range(500):
            new_ranks = tie_break(ranks)
            new_ranks = neighbors_rank(new_ranks)
            if ranks == new_ranks:
                break
            ranks = new_ranks
        else:
            warn("Max cycles reached in canonical sorting (tie-breaking)")

    return ranks