import numpy as np
from scipy.spatial.distance import cdist

def dist_mat(in_array):
    """
    Return lower triangular distance matrix of coordinate array

    Parameters
    ----------
    in_array : Nat X 3 numpy array
        Coordinate array
    Returns
    -------
    dist_mat : Nat X Nat numpy array
        Lower triangular distance matrix

    """
    dist_mat = np.tril(cdist(in_array,in_array))
    return dist_mat

def find_largest(in_array, n_largest):
    """
    Return the coordinates of the N largest elements of an ND-array

    Parameters
    ----------
    in_array : M x N numpy array
        Numpy array
    n_largest : int
        Number of required pairs of atoms
    Returns
    -------
    n_largest : n_largest X 2 array-like
        The coordinates of the n_largest elements. It's an n_largest dimensional
        array of tuples.

    """
    new_arr = np.copy(in_array)
    shape = np.shape(new_arr)
    indices = []
    while len(indices) < n_largest:
        flat_index = np.argmax(new_arr)
        folded_index = np.unravel_index(flat_index,shape)
        indices.append(folded_index)
        new_arr[folded_index] = 0
    return indices

def plane_from_coord(coord_arr):
    """
    Return plane coefficients which best includes the coordinates

    This is done via a singular value decomposition of the coordinates. Read
    the following:
    http://caves.org/section/commelect/DUSI/openmag/pdf/SphereFitting.pdf

    Parameters
    ----------
    coord_arr : Nat x 3 numpy array
        The input coordinates array
    Returns
    -------
    a, b, c, d : floats
        Plane equation coefficients such that a point on the plane is:
        ax + by + cz + d = 0

    """
    centroid = np.average(coord_arr, axis=0)
    # coordinates translated to origin
    cen_coords = coord_arr - centroid

    U, S, Vt = np.linalg.svd(cen_coords)
    # The last row of V matrix indicate the eigenvectors of
    # smallest eigenvalues (singular values).
    N = Vt[-1]

    # Extract a, b, c, d coefficients.
    x0, y0, z0 = centroid
    a, b, c = N
    d = -(a * x0 + b * y0 + c * z0)

    return a, b, c, d

def extreme_pairs(coord_arr, n_pairs):
    """
    Return a list of pairs of extreme coordinates

    Parameters
    ----------
    coord_arr : Nat x 3 numpy array
        The input coordinates array
    n_pairs : int
        Number of extreme atom pairs requested
    Returns
    -------
    pairs : numpy array of n_pairs x 2 x 3
        Coordinates of the N pairs of points

    """
    dmat = dist_mat(coord_arr)
    pairs_inds = find_largest(dmat,2)
    pairs = np.zeros((n_pairs,2,3))
    for i,ind in enumerate(pairs_inds):
        pairs[i][0] = coord_arr[ind[0]]
        pairs[i][1] = coord_arr[ind[1]]

    return pairs
