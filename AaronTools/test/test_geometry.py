#!/usr/bin/env python3
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import zip
from builtins import str
from builtins import range
from builtins import int
from future import standard_library
standard_library.install_aliases()
import random
import unittest
from copy import copy

import numpy as np

from AaronTools.atoms import Atom
from AaronTools.substituent import Substituent
from AaronTools.ringfragment import RingFragment
from AaronTools.fileIO import FileReader, FileWriter
from AaronTools.geometry import Geometry
from AaronTools.test import TestWithTimer, prefix, rmsd_tol


def is_close(a, b, tol=10 ** -8, debug=False):
    n = None
    if isinstance(a, np.ndarray) and isinstance(a, np.ndarray):
        n = np.linalg.norm(a - b)
    elif isinstance(a, np.ndarray):
        n = np.linalg.norm(a) - b
    elif isinstance(b, np.ndarray):
        n = a - np.linalg.norm(b)
    else:
        n = a - b
    if debug:
        print(abs(n))
    return abs(n) < tol


def check_atom_list(ref, comp):
    rv = True
    for i, j in zip(ref, comp):
        rv &= i.__repr__() == j.__repr__()
    return rv


class TestGeometry(TestWithTimer):
    benz_NO2_Cl = prefix + "test_files/benzene_1-NO2_4-Cl.xyz"
    benz_NO2_Cl_conn = [
        "2,6,12",
        "1,3,7",
        "2,4,8",
        "3,5,11",
        "4,6,9",
        "1,5,10",
        "2",
        "3",
        "5",
        "6",
        "4",
        "1,13,14",
        "12",
        "12",
    ]
    benz_NO2_Cl_conn = [i.split(",") for i in benz_NO2_Cl_conn]
    benzene = prefix + "test_files/benzene.xyz"
    naphthalene = prefix + "ref_files/naphthalene.xyz"
    tetrahydronaphthalene = prefix + "ref_files/tetrahydronaphthalene.xyz"
    pyrene = prefix + "ref_files/pyrene.xyz"
    benz_Cl = prefix + "test_files/benzene_4-Cl.xyz"
    benz_OH_Cl = prefix + "test_files/benzene_1-OH_4-Cl.xyz"
    benz_Ph_Cl = prefix + "test_files/benzene_1-Ph_4-Cl.xyz"
    Et_NO2 = prefix + "test_files/Et_1-NO2.xyz"
    pent = prefix + "test_files/pentane.xyz"

    def test_init(self):
        ref = FileReader(TestGeometry.benz_NO2_Cl)
        conn_valid = TestGeometry.benz_NO2_Cl_conn
        rank_valid = [8, 7, 5, 4, 5, 7, 3, 1, 1, 3, 0, 6, 2, 2]

        for i, a in enumerate(ref.atoms):
            a.connected = set(conn_valid[i])
            a._rank = rank_valid[i]

        mol = Geometry(TestGeometry.benz_NO2_Cl)

        # name
        self.assertEqual(mol.name, ref.name)
        # comment
        self.assertEqual(mol.comment, ref.comment)
        # atoms
        for a, b in zip(ref.atoms, mol.atoms):
            for attr in a.__dict__:
                if attr == "file_type":
                    continue
                if attr == "connected":
                    tmpa = [int(c) for c in a.connected]
                    tmpb = [int(c.name) for c in b.connected]
                    self.assertSequenceEqual(sorted(tmpa), sorted(tmpb))
                    continue
                if attr == "_rank":
                    continue
                if attr == "constraint":
                    # this is checked in test_parse_comment
                    continue
                try:
                    self.assertEqual(a.__dict__[attr], b.__dict__[attr])
                except ValueError:
                    self.assertSequenceEqual(
                        sorted(a.__dict__[attr]), sorted(b.__dict__[attr])
                    )

        # test blank
        blank = Geometry()
        self.assertEqual(blank.name, "")
        self.assertEqual(blank.comment, "")
        self.assertEqual(blank.atoms, [])

    # utilities
    def test_equality(self):
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        benz = Geometry(TestGeometry.benzene)
        # same object should be equal
        self.assertEqual(mol, mol)
        # copy should be equal
        self.assertEqual(mol, mol.copy())
        # different molecules should be unequal
        self.assertNotEqual(mol, benz)

    def test_find_atom(self):
        geom = Geometry(TestGeometry.benz_NO2_Cl)
        geom.atoms[0].add_tag("find_me")

        # find a specific atom
        a = geom.find(geom.atoms[0])
        self.assertEqual(a, geom.atoms[0:1])

        # find by tag
        a = geom.find("find_me")
        self.assertEqual(a, geom.atoms[0:1])

        # find by name
        a = geom.find("1")
        self.assertEqual(a, geom.atoms[0:1])

        # find by list-style name
        a = geom.find("1,2-5,12")
        self.assertSequenceEqual(
            a, geom.atoms[0:1] + geom.atoms[1:5] + geom.atoms[11:12]
        )

        # find using tag and name
        a = geom.find("find_me", "1")
        self.assertEqual(a, geom.atoms[0:1])

        b = geom.find(["find_me", "2"])
        self.assertEqual(b, geom.atoms[0:2])

        c = geom.find(["1", "2"], "find_me")
        self.assertEqual(c, geom.atoms[0:1])

        d = geom.find(["2", "3"], "find_me")
        self.assertEqual(d, [])

        # find all Carbons
        a = geom.find("C")
        b = []
        for i in geom.atoms:
            if i.element == "C":
                b += [i]
        self.assertSequenceEqual(a, b)

        # raise error when atom not found
        self.assertRaises(LookupError, geom.find, "definitely not in here")

    def test_refresh_connected(self):
        # refresh_connected should be run upon creation
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        conn_valid = TestGeometry.benz_NO2_Cl_conn
        for a, b in zip(mol.atoms, conn_valid):
            tmpa = [int(c.name) for c in a.connected]
            tmpb = [int(c) for c in b]
            self.assertSequenceEqual(sorted(tmpa), sorted(tmpb))

        # old connectivity shouldn't remain in the set
        mol.atoms[0].connected.add(Atom())
        old = mol.atoms[0].connected
        mol.refresh_connected()
        self.assertTrue(len(old) - len(mol.atoms[0].connected) == 1)

    def test_canonical_rank(self):
        pentane = Geometry(TestGeometry.pent)
        pentane_rank = [0, 1, 2, 1, 0]

        test_rank = pentane.canonical_rank(heavy_only=True)
        self.assertSequenceEqual(test_rank, pentane_rank)

    def test_flag(self):
        geom = Geometry(TestGeometry.benz_NO2_Cl)

        # freeze all
        if isinstance(geom, list):
            test =  geom[:]
        else:
            test = geom.copy()
        test.freeze()
        for a in test.atoms:
            self.assertTrue(a.flag)

        # freeze some
        if isinstance(geom, list):
            test =  geom[:]
        else:
            test = geom.copy()
        test.freeze("C")
        for a in test.atoms:
            if a.element == "C":
                self.assertTrue(a.flag)
            else:
                self.assertFalse(a.flag)

        geom.freeze()
        # relax all
        if isinstance(geom, list):
            test =  geom[:]
        else:
            test = geom.copy()
        test.relax()
        for a in test.atoms:
            self.assertFalse(a.flag)

        # relax some
        if isinstance(geom, list):
            test =  geom[:]
        else:
            test = geom.copy()
        test.relax("C")
        for a in test.atoms:
            if a.element == "C":
                self.assertFalse(a.flag)
            else:
                self.assertTrue(a.flag)

    def test_update_geometry(self):
        test = Geometry(TestGeometry.benz_NO2_Cl)

        # using coordinate matrix to update
        if isinstance(test, list):
            ref =  test[:]
        else:
            ref = test.copy()
        ref.coord_shift([-10, 0, 0])
        tmp = test._stack_coords()
        for t in tmp:
            tmp = tmp - np.array([-10, 0, 0])
        test.update_geometry(tmp)
        self.assertEqual(ref, test)

        # using file
        ref.coord_shift([10, 0, 0])
        test.update_geometry(TestGeometry.benz_NO2_Cl)
        self.assertEqual(ref, test)

    # geometry measurement

    def test_angle(self):
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        angle = mol.angle("13", "12", "14")
        self.assertTrue(is_close(np.rad2deg(angle), 124.752, 10 ** -2))

    def test_dihedral(self):
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        dihedral = mol.dihedral("13", "12", "1", "6")
        self.assertTrue(is_close(np.rad2deg(dihedral), 45.023740, 10 ** -5))

    def test_COM(self):
        mol = Geometry(TestGeometry.benz_NO2_Cl)

        # all atoms
        com = mol.COM(mass_weight=True)
        self.assertTrue(
            is_close(com, [-1.41347592e00, -1.35049427e00, 9.24797359e-04])
        )

        # only carbons
        com = mol.COM(targets="C")
        self.assertTrue(
            is_close(com, [-1.27963500e00, -1.11897500e00, 8.53333333e-04])
        )
        # mass weighting COM shouldn't change anythin if they are all C
        com = mol.COM(targets="C", mass_weight=True)
        self.assertTrue(
            is_close(com, [-1.27963500e00, -1.11897500e00, 8.53333333e-04])
        )

        # only heavy atoms
        com = mol.COM(heavy_only=True, mass_weight=True)
        self.assertTrue(
            is_close(com, [-1.41699980e00, -1.35659562e00, 9.31512531e-04])
        )

    def test_RMSD(self):
        ref = Geometry(TestGeometry.benz_NO2_Cl)

        # RMSD of copied object should be 0
        if isinstance(ref, list):
            other =  ref[:]
        else:
            other = ref.copy()
        self.assertTrue(ref.RMSD(other) < rmsd_tol(ref, superTight=True))
        # if they are out of order, sorting should help
        res = ref.RMSD(other, longsort=True)
        self.assertTrue(res < rmsd_tol(other, superTight=True))

        # RMSD of shifted copy should be 0
        if isinstance(ref, list):
            other =  ref[:]
        else:
            other = ref.copy()
        other.coord_shift([1, 2, 3])
        self.assertTrue(ref.RMSD(other) < rmsd_tol(ref, superTight=True))

        # RMSD of rotated copy should be 0
        if isinstance(ref, list):
            other =  ref[:]
        else:
            other = ref.copy()
        other.rotate([1, 2, 3], 2.8)
        other.write("tmp")
        self.assertTrue(ref.RMSD(other) < rmsd_tol(ref))

        # RMSD of two different structures should not be 0
        other = Geometry(TestGeometry.pent)
        self.assertTrue(ref.RMSD(other) > 10 ** -2)

        # RMSD of similar molecule
        other = Geometry(TestGeometry.benzene)
        res = ref.RMSD(other, targets="C", ref_targets="C")
        self.assertTrue(res < rmsd_tol(ref))
        res = ref.RMSD(other, sort=True)

    # geometry manipulation
    def test_get_fragment(self):
        mol = Geometry(TestGeometry.benz_NO2_Cl)

        # get NO2 fragment using tag
        frag = mol.get_fragment(mol.atoms[11], mol.atoms[0], copy=False)
        v_frag = mol.atoms[11:]
        self.assertSequenceEqual(frag, v_frag)

        # get Cl using name
        frag = mol.get_fragment("11", "4", copy=False)
        v_frag = mol.atoms[10:11]
        self.assertSequenceEqual(frag, v_frag)

        # get ring without NO2 using atoms
        frag = mol.get_fragment(mol.atoms[0], mol.atoms[11], copy=False)
        v_frag = mol.atoms[:11]
        self.assertSequenceEqual(sorted(frag), sorted(v_frag))

        # get fragment as Geometry()
        frag = mol.get_fragment(mol.atoms[0], mol.atoms[11], as_object=True)
        self.assertIsInstance(frag, Geometry)

    def test_remove_fragment(self):
        benzene = Geometry(TestGeometry.benzene)
        benz_Cl = Geometry(TestGeometry.benz_Cl)
        Et_NO2 = Geometry(TestGeometry.Et_NO2)

        # remove NO2 group using atom name
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        mol.remove_fragment("12", "1")
        self.assertEqual(mol, benz_Cl)
        # remove Cl using elements
        mol.remove_fragment("Cl", "C")
        self.assertEqual(mol, benzene)

        # multiple start atoms
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        mol.remove_fragment(["3", "6"], ["2", "1"])
        self.assertEqual(mol, Et_NO2)

    def test_coord_shift(self):
        benzene = Geometry(TestGeometry.benzene)
        mol = Geometry(TestGeometry.benzene)

        # shift all atoms
        vector = np.array([0, 3.2, -1.0])
        for a in benzene.atoms:
            a.coords += vector
        mol.coord_shift([0, 3.2, -1.0])
        self.assertTrue(np.linalg.norm(benzene.coords() - mol.coords()) == 0)

        # shift some atoms
        vector = np.array([0, -3.2, 1.0])
        for a in benzene.atoms[0:5]:
            a.coords += vector
        mol.coord_shift([0, -3.2, 1.0], [str(i) for i in range(1, 6)])
        self.assertTrue(np.linalg.norm(benzene.coords() - mol.coords()) == 0)

    def test_change_distance(self):
        def validate_distance(before, after, moved):
            dist = np.linalg.norm(after.coords - before.coords)
            return abs(dist - moved)

        threshold = 10 ** (-8)
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        a1 = mol.atoms[0]  # C1
        a3 = mol.atoms[5]  # attached to C1
        a2 = mol.atoms[11]  # N12
        a4 = mol.atoms[12]  # attached to N12

        # set distance and move fragments
        a3_before = copy(a3)
        a4_before = copy(a4)
        dist_before = np.linalg.norm(a1.coords - a2.coords)
        mol.change_distance(a1, a2, dist=2.00)
        dist = np.linalg.norm(a1.coords - a2.coords)
        self.assertTrue(is_close(dist, 2.00, threshold))
        self.assertTrue(validate_distance(a3_before, a3, dist - dist_before))
        self.assertTrue(validate_distance(a4_before, a4, dist - dist_before))

        # adjust_distance and move fragments
        a3_before = copy(a3)
        a4_before = copy(a4)
        dist_before = np.linalg.norm(a1.coords - a2.coords)
        mol.change_distance(a1, a2, dist=-0.5, adjust=True)
        self.assertTrue(is_close(a1.dist(a2), 1.5, threshold))
        self.assertTrue(validate_distance(a3_before, a3, -0.5))
        self.assertTrue(validate_distance(a4_before, a4, -0.5))

        # set and fix atom 1
        a1_before = copy(a1)
        mol.change_distance(a1, a2, dist=2.00, fix=1)
        self.assertTrue(is_close(a1.dist(a2), 2.00, threshold))
        self.assertTrue(a1_before.dist(a1) < threshold)

        # adjust and fix atom 2
        a2_before = copy(a2)
        mol.change_distance(a1, a2, dist=-0.5, adjust=True, fix=2)
        self.assertTrue(is_close(a1.dist(a2), 1.5, threshold))
        self.assertTrue(a2_before.dist(a2) < threshold)

        # set and don't move fragments
        a3_before = copy(a3)
        a4_before = copy(a4)
        dist_before = np.linalg.norm(a1.coords - a2.coords)
        mol.change_distance(a1, a2, dist=2.00, as_group=False)
        dist = np.linalg.norm(a1.coords - a2.coords)
        self.assertTrue(is_close(a1.dist(a2), 2.00, threshold))
        self.assertTrue(validate_distance(a3_before, a3, dist - dist_before))
        self.assertTrue(validate_distance(a4_before, a4, dist - dist_before))

    def test_change_angle(self):
        def diff(a, b):
            return abs(a - b)

        mol = Geometry(TestGeometry.benz_NO2_Cl)

        # set angle
        mol.change_angle("13", "12", "14", np.pi / 2, fix=1)
        angle = mol.angle("13", "12", "14")
        self.assertTrue(diff(np.rad2deg(angle), 90) < 10 ** -8)

        # change angle
        mol.change_angle(
            "13", "12", "14", 30, fix=3, adjust=True, radians=False
        )
        angle = mol.angle("13", "12", "14")
        self.assertTrue(diff(np.rad2deg(angle), 120) < 10 ** -8)

        mol.change_angle("13", "12", "14", -30, adjust=True, radians=False)
        angle = mol.angle("13", "12", "14")
        self.assertTrue(diff(np.rad2deg(angle), 90) < 10 ** -8)

    def test_change_dihedral(self):
        mol = Geometry(TestGeometry.benz_NO2_Cl)
        atom_args = ("13", "12", "1", "6")
        original_dihedral = mol.dihedral(*atom_args)

        # adjust dihedral by 30 degrees
        mol.change_dihedral(*atom_args, 30, radians=False, adjust=True)
        self.assertTrue(
            is_close(
                mol.dihedral(*atom_args), original_dihedral + np.deg2rad(30)
            )
        )
        self.assertEqual(
            mol, Geometry(prefix + "test_files/change_dihedral_0.xyz")
        )

        # set dihedral to 60 deg
        mol.change_dihedral(*atom_args, 60, radians=False)
        self.assertTrue(is_close(mol.dihedral(*atom_args), np.deg2rad(60)))

        # adjust using just two atoms
        mol.change_dihedral("12", "1", -30, radians=False, adjust=True)
        self.assertTrue(is_close(mol.dihedral(*atom_args), np.deg2rad(30)))


    def test_substitute(self):
        ref = Geometry(TestGeometry.benz_NO2_Cl)
        mol = Geometry(TestGeometry.benzene)

        mol.substitute(Substituent("NO2"), "12")
        mol.substitute(Substituent("Cl"), "11")

        rmsd = mol.RMSD(ref, align=True)
        self.assertTrue(rmsd < rmsd_tol(ref))
    
    def test_close_ring(self):
        mol = Geometry(TestGeometry.benzene)
        
        ref1 = Geometry(TestGeometry.naphthalene)
        if isinstance(mol, list):
            mol1 =  mol[:]
        else:
            mol1 = mol.copy()
        mol1.ring_substitute(['7', '8'], RingFragment('benzene'))
        rmsd = mol1.RMSD(ref1, align=True)
        self.assertTrue(rmsd < rmsd_tol(ref1))

        ref2 = Geometry(TestGeometry.tetrahydronaphthalene)
        if isinstance(mol, list):
            mol2 =  mol[:]
        else:
            mol2 = mol.copy()
        mol2.ring_substitute(['7', '8'], RingFragment('cyclohexane-chair.1'))
        rmsd = mol2.RMSD(ref2, align=True)
        self.assertTrue(rmsd < rmsd_tol(ref2))

        mol3 = Geometry(TestGeometry.naphthalene)
        ref3 = Geometry(TestGeometry.pyrene)
        targets1 = mol3.find(['9', '15'])
        targets2 = mol3.find(['10', '16'])
        mol3.ring_substitute(targets1, RingFragment('benzene'))
        mol3.ring_substitute(targets2, RingFragment('benzene'))
        rmsd = mol3.RMSD(ref3, align=True)
        self.assertTrue(rmsd < rmsd_tol(ref3, superLoose=True))

if __name__ == "__main__":
    unittest.main()