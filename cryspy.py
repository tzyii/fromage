#!/usr/bin/env python
"""Minimises the energy or the gap penalty function of a molecule in a cluster.

Template files are needed as well as an xyz file for the molecule and another
one for the surrounding molecules. Overall the use of subprocess is ugly as it
is repeated 3 or 4 times but it was found to handle memory better than Pool
when interfacing with Gaussian.

"""
import numpy as np
import subprocess
import os
import read_file as rf
import edit_file as ef
import handle_atoms as ha
import calc
from atom import Atom
from scipy.optimize import minimize
from datetime import datetime

def sequence(in_pos):
    """
    Run Gaussian calculations in parallel and write and return results

    This function is designed to work with the scipy.optimise.minimize function.
    This is why it can only receive one array of floats as input and return two
    arrays of floats. As a result some variables in this function are defined
    elsewhere in the module which is a necessary evil.

    Parameter
    ----------
    in_pos : list of floats
        Input coordinates in array form
    Returns
    -------
    en_out : float
        Combined energy or penalty function value in Hartree
    gr_out : list of floats
        Gradients of en_out in Hartree/Angstrom
    References
    ----------
    Levine, B. G., Coe, J. D. & Martinez, T. J. Optimizing conical intersections
    without derivative coupling vectors: Application to multistate
    multireference second-order perturbation theory (MS-CASPT2).
    J. Phys. Chem. B 112, 405-413 (2008).

    """
    # initialise calculation objects
    rl = calc.Gauss_calc("rl")
    ml = calc.Gauss_calc("ml")
    mh = calc.Gauss_calc("mh")
    if bool_ci:
        mg = calc.Gauss_calc("mg")

    # Run the calculations as subprocesses with a maximum of 2 simultameous ones
    # at the same time. This order is optimised for the mh calculation being
    # the longest
    mh_proc = mh.run(ha.array2atom(mol_atoms, in_pos))
    rl_proc = rl.run(ha.array2atom(mol_atoms, in_pos))
    rl_proc.wait()
    ml_proc = ml.run(ha.array2atom(mol_atoms, in_pos))
    ml_proc.wait()
    if bool_ci:
        mg_proc = mg.run(ha.array2atom(mol_atoms, in_pos))
        mg_proc.wait()
    mh_proc.wait()

    # read results. Each x_en_gr is a tuple (energy,gradients,scf_energy)
    rl_en_gr = rl.read_out(True, in_pos, mol_atoms, shell_atoms)
    ml_en_gr = ml.read_out(False, in_pos)
    mh_en_gr = mh.read_out(False, in_pos)
    if bool_ci:
        mg_en_gr = mg.read_out(False, in_pos)

    # combine results
    en_combo = rl_en_gr[0] - ml_en_gr[0] + mh_en_gr[0]
    gr_combo = rl_en_gr[1] - ml_en_gr[1] + mh_en_gr[1]
    scf_combo = rl_en_gr[2] - ml_en_gr[2] + mh_en_gr[2]

    if bool_ci:
        # corresponding ground state energy and gradients
        en_combo_g = rl_en_gr[0] - ml_en_gr[0] + mg_en_gr[0]
        gr_combo_g = rl_en_gr[1] - ml_en_gr[1] + mg_en_gr[1]

        # Penalty function parameters and calculation
        alpha = 0.02
        # sigma is called lambda in some papers but that is a bad variable name
        # in Python
        sigma = 3.5
        e_mean = (en_combo + en_combo_g) / 2
        e_diff = en_combo - en_combo_g
        g_ij = e_diff**2 / (e_diff + alpha)
        en_out = e_mean + sigma * g_ij
        gr_out = 0.5 * (gr_combo + gr_combo_g) + sigma * ((e_diff**2 + 2 *
                                                           alpha * e_diff) / (e_diff + alpha)**2) * (gr_combo - gr_combo_g)
    else:
        en_out = en_combo
        gr_out = gr_combo

    # print some updates in the output
    out_file.write("------------------------------\n")
    global iteration
    iteration += 1
    out_file.write("Iteration: " + str(iteration) + "\n")
    out_file.write("Real low energy: {:>30.8f} eV\n".format(
        rl_en_gr[0] * evconv))
    out_file.write("Model low energy: {:>29.8f} eV\n".format(
        ml_en_gr[0] * evconv))
    out_file.write("Model high energy: {:>28.8f} eV\n".format(
        mh_en_gr[0] * evconv))
    out_file.write(
        "ONIOM Total energy: {:>27.8f} eV\n".format(en_combo * evconv))
    out_file.write(
        "ONIOM SCF energy: {:>29.8f} eV\n".format(scf_combo * evconv))
    out_file.write(
        "Energy grad. norm: {:>28.8f} eV/A\n".format(np.linalg.norm(gr_combo * evconv)))
    if bool_ci == True:
        out_file.write(
            "Penalty function value: {:>23.8f} eV\n".format(en_combo * evconv))
        out_file.write("Penalty function grad. norm: {:>18.8f} eV\n".format(
            np.linalg.norm(gr_combo * evconv)))
    out_file.write("Gap: {:>43.8f} eV\n".format(
        (en_combo - scf_combo) * evconv))
    out_file.flush()
    return (en_out, gr_out)

if __name__ == '__main__':

    evconv = 27.2114  # Something in Hartree * evconv = Something in eV
    bohrconv = 1.88973  # Something in Angstrom * bohrconv = Something in Bohr

    # default settings

    def_inputs = {"mol_file": "mol.init.xyz", "shell_file": "shell.xyz",
              "out_file": "cryspy.out", "bool_ci": "", "high_level": "gaussian", "low_level": "gaussian"}

    # read user inputs
    new_inputs = rf.read_config("cryspy.in")

    inputs=def_inputs.copy()
    inputs.update(new_inputs)

    mol_file = inputs["mol_file"]
    shell_file = inputs["shell_file"]
    out_file = inputs["out_file"]
    bool_ci = bool(int(inputs["bool_ci"]))
    high_level = inputs["high_level"]
    low_level = inputs["low_level"]

    # output
    out_file = open(out_file, "w", 1)
    # print start time
    start_time = datetime.now()
    out_file.write("STARTING TIME: " + str(start_time) + "\n")

    iteration = 0


    # clean up the last output
    if os.path.exists("geom_mol.xyz"):
        subprocess.call("rm geom_mol.xyz", shell=True)
    if os.path.exists("geom_cluster.xyz"):
        subprocess.call("rm geom_cluster.xyz", shell=True)

    # read initial coordniates
    mol_atoms = rf.read_xyz(mol_file)[0]

    # read shell atoms
    shell_atoms = rf.read_xyz(shell_file)[0]

    # make the initial coordinates into a flat list
    atoms_array = []
    for atom in mol_atoms:
        atoms_array.append(atom.x)
        atoms_array.append(atom.y)
        atoms_array.append(atom.z)

    # make the list into an array
    atoms_array = np.array(atoms_array)

    res = minimize(sequence, atoms_array, jac=True,
                   options={'disp': True})

    out_file.write("DONE\n")
    end_time = datetime.now()
    out_file.write("ELAPSED TIME: " + str(end_time - start_time) + "\n")
    out_file.write("ENDING TIME: " + str(end_time) + "\n")
    out_file.close()
