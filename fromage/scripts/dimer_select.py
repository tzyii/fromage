#!/usr/bin/env python
"""
Utility for selecting unique dimers from a .xyz file

The unique dimers are written to separate output files, *_dimer_*.xyz

"""

from __future__ import division
import sys
import argparse
import time
import numpy as np

from fromage.io import read_file as rf
from fromage.io import edit_file as ef
from fromage.utils import handle_atoms as ha
from fromage.fdist import fdist as fd

start = time.time()


def vector_distance(x1, y1, z1, x2, y2, z2):
    """
    Calculate the distances between two cartesian coordinates

    Parameters
    ----------
    (x1,y1,z1,x2,y2,z2): hextuple of floats
            atomic coordinates of atoms 1 and 2
    Returns
    -------
    dist: Float
            distance in units of coordinates
    """
    # calculate distance
    #dist = sqrt(fd.dist2(x1, y1, z1, x2, y2, z2))
    dist = fd.dist(x1, y1, z1, x2, y2, z2)

    return dist


def make_dimers_cd(molecules, cd):
    """
    Generate a list of dimers based on centroid distances cd

    Parameters
    ----------
    molecules: list of lists
        M molecules containing N atom objects
    cd: float
        Length between centroids of molecules
    Returns
    -------
    dimers: list of lists
        List L of length D dimers, where each member of L is a list of 2N atom objects
    """
    dimers = []
    for mol_1_no, mol1 in enumerate(molecules):
        for mol_2_no, mol2 in enumerate(molecules[mol_1_no:]):
            if mol1 != mol2:
                cent_1 = ha.find_centroid(mol1)
                cent_2 = ha.find_centroid(mol2)
                if vector_distance(cent_1[0], cent_1[1], cent_1[2], cent_2[0], cent_2[1], cent_2[2]) <= cd:
                    new_mol = mol1 + mol2
                    dimers.append(new_mol)
    return dimers


def make_dimers_vdw(molecules):
    """
    Generate a list of dimers based on van der waals radii of closest atoms

    Parameters
    ----------
    molecules: list of lists
        M molecules containing N atom objects
    Returns
    -------
    dimers: list of lists
        List L of length D dimers, where each member of L is a list of 2N atom objects
    """
    dimers = []
    for mol_1_no, mol1 in enumerate(molecules):
        # loop over atoms in another molecule
        for mol_2_no, mol2 in enumerate(molecules[mol_1_no:]):
            if mol1 != mol2:
                for atom1 in mol1:
                    for atom2 in mol2:
                        # vdw distances + 1.5 damping factor, as per Day et al.
                        if vector_distance(atom1.x, atom1.y, atom1.z, atom2.x, atom2.y, atom2.z) <= atom1.vdw + atom2.vdw + 1.5:
                            dimer = mol1 + mol2
                            dimers.append(dimer)
                            break

    return dimers


def loop_atoms(mol_1, mol_2, ad):
    """
    Generate a dimer based on intermolecular atomic distances between two molecules

    Parameters
    ----------
    mol_1: list of atom objects
    mol_2: list of atom objects
    ad: float
        Maximum ntermolecular atomic distance
    Returns
    -------
    mol1+mol2: list of atom objects
    """
    for atom1 in mol_1:
        for atom2 in mol_2:
            if vector_distance(atom1.x, atom1.y, atom1.z, atom2.x, atom2.y, atom2.z) <= ad:
                return mol_1 + mol_2


def make_dimers_ad(molecules, ad):
    """
    Generate a list of dimers based on intermolecular atomic distancead

    Parameters
    ----------
    molecules: list of lists
        M molecules containing N atom objects
    ad: float
        Maximum ntermolecular atomic distance
    Returns
    -------
    dimers: list of lists
        List L of length D dimers, where each member of L is a list of 2N atom objects
    """
    dimers = []
    for mol_1_no, mol1 in enumerate(molecules):
        for mol_2_no, mol2 in enumerate(molecules[mol_1_no:]):
            if mol1 != mol2:
                dimer = loop_atoms(mol1, mol2, args.dist)
                if dimer:
                    dimers.append(dimer)
    return dimers


def differences(A, B):
    """
    Calulate the sum of squares difference between two lists, nominally of atomic distances

    Parameters
    ----------
    A,B: lists of floats
        Bond distances in dimers
    Returns
    -------
    SSD: float
        Sum of squares differences
    """
    SSD = np.sum(np.square(np.array(A) - np.array(B)))
    return float(SSD) / len(A)


def interatomic_distances(dimers):
    """
    Generate a list of the interatomic distances for each dimer in list of dimers

    Parameters
    ----------
    dimers: list of lists
     List of L of length D dimers, where each member of L is a list of 2N atom objects
    Returns
    -------
    connections: list
        Connections per dimer
    """
    connections = []
    for dim_no, dim_atom in enumerate(dimers):
        dim_cons = []
        for atom_no_A, atom_A in enumerate(dim_atom):
            for atom_no_B, atom_B in enumerate(dim_atom[atom_no_A:]):
                if atom_A != atom_B:
                    dim_cons.append(round(vector_distance(
                        atom_A.x, atom_A.y, atom_A.z, atom_B.x, atom_B.y, atom_B.z), 0))
        connections.append(sorted(dim_cons))
    return connections

if __name__ == "__main__":
    # parse the input
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input .xyz file", type=str)
    parser.add_argument("-b", "--bond", help="Maximum length (in unites of input file) that qualifies as a bond",
                        default=1.6, type=float)
    parser.add_argument("-t", "--dimtype", help="Use centroid distance [C], or shortest atomic distances [A], or van der waals radii [vdw] to define a dimer",
                        default=str("c"), type=str.lower)
    parser.add_argument("-d", "--dist", help="Distance criterion (in units of input file) to define a dimer",
                        default=7, type=float)
    user_input = sys.argv[1:]
    args = parser.parse_args(user_input)
    atoms = rf.read_xyz(args.input)[-1]
    natoms = len(atoms)

    print("{} atoms".format(natoms))

    # SELECT MOLECULE
    print("\n1. Generating molecules.\nMax bond length {}".format(args.bond))
    molecules = ha.make_molecules(atoms, args.bond)
    print("{} molecules generated".format(len(molecules)))
    lengths = []
    for atom1 in molecules[0]:
        for atom2 in molecules[0]:
            x1, y1, z1, x2, y2, z2 = atom1.x, atom1.y, atom1.z, atom2.x, atom2.y, atom2.z
            lengths.append(vector_distance(x1, y1, z1, x2, y2, z2))

    # SELECT DIMERS
    print("\n2. Generating dimers")
    if args.dimtype == "c":
        print("Using centroid distance of {}".format(args.dist))
        dimers = make_dimers_cd(molecules, args.dist)
    elif args.dimtype == "a":
        print("Using intermolecular atomic distance of {}".format(args.dist))
        dimers = make_dimers_ad(molecules, args.dist)
    elif args.dimtype == "vdw":
        print("Using van der Waals radii to generate dimers")
        dimers = make_dimers_vdw(molecules)
    else:
        sys.exit(
            "Please choose 'C', or 'A', or 'vdw'. Run --help for more info.\nExiting...")
    if len(dimers) == 0:
        exit("No dimers found. Try adjusting the selection criteria.\nExiting")
    elif len(dimers) == 1:
        outfile = str(args.input[:-4]) + "_dimer_0.xyz"
        ef.write_xyz(outfile, dimers[0])
        exit("One  dimer found, writing {}.\nExiting".format(outfile))
    else:
        print("{} dimers generated".format(len(dimers)))

    # SELECT UNIQUE DIMERS

    print("\n3. Finding unique dimers")
    distances = interatomic_distances(dimers)

    # Start a list of unique dimer geometries (unique_dims) coupled with the
    # corresponding interatomic distances (unique_distances). Populate each with
    # the first dimer. Each list is a list itself, containing the geometry (or distances)
    # as the first element, with the number of occurances as the second element

    unique_dims = [dimers[0]]
    unique_distances = [[distances[0], 1]]

    # filter out the unique dimers
    for i, distance in enumerate(distances[1:]):  # loop over all dimers
        unique = True
        for cross_check in unique_distances:  # loop over dimers which are unique
            # if the distance array is already considered unique
            if differences(distance, cross_check[0]) < 0.1:
                unique = False
                # Increase the number of occurances for that dimer
                # configuration
                cross_check[1] += 1
                break
        # if it's still unique after the checks
        if unique:
            unique_dims.append(dimers[i + 1])
            unique_distances.append([distance, 1])

    print("Number of unique dimers: {}".format(len(unique_dims)))
    print("Ratio of dimers in input structure:")
    for i, dimer in enumerate(unique_distances):
        print("Dimer {}: {}/{} ({}%)".format(i,
                                             dimer[1], len(dimers), round(dimer[1] / len(dimers) * 100, 0)))
    # write the files
    for dim_no, dim in enumerate(unique_dims):
        outfile = str(args.input[:-4]) + "_dimer_" + str(dim_no) + ".xyz"
        print("Writing {}".format(outfile))
        ef.write_xyz(outfile, dim)

    end = time.time()
    print("\nTotal time: {}s".format(round((end - start), 1)))
