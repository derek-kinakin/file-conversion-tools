"""
Convert DXF or PLY triangular meshes to GEOH5 format workspace files.

Reads 3DFACEs from a DXF or mesh vertices and faces from a PLY file containing
a single triangulated mesh surface or solid. Saves the triangulated mesh as a
geoh5 workspace file containing a single mesh object.

Processes files in "single" or "batch" mode.

D. Kinakin, J. Danielson

2022-03-04
"""

import sys
import os
import numpy as np
import ezdxf as ed
import trimesh as tm

from tqdm import tqdm
from geoh5py.workspace import Workspace
from geoh5py.objects import Surface


# Globals
MODE = "batch" # batch or single
INFOLDER = r"C:\Users\dkinakin\Desktop\batch_test" # for batch mode
INFILE = r"C:\Users\dkinakin\Desktop\Fault Model V1\EN1_V1.ply" # for single mode
EXT = "ply"

# Functions
def file_list(fld_pth, fl_xt):
    """List of files and paths

    Paramters
    ---------
    fld_pth : str
       Folder path to all files 
    
    fl_xt : str
       File extension of interest
    
    Returns
    -------
    List
        List of full file paths
    """
    folder_contents = os.listdir(fld_pth)
    filtered_file_list = [os.path.join(fld_pth, f) for f in folder_contents if f.endswith(fl_xt)]

    return filtered_file_list


def read_dxf_file(fp):
    """Loads the specificed DXF document into memory

    Paramters
    ---------
    fp : str
        Filepath of the folder containing the DXF
    fl : str
        Filename of the DXF
    
    Returns
    -------
    DXF file object
    """
    try:
        d = ed.readfile(fp)
        return d
    except IOError:
        print(f"Not a DXF file or a generic I/O error.")
        sys.exit(1)
    except ed.DXFStructureError:
        print(f"Invalid or corrupted DXF file.")
        sys.exit(2)


def read_ply_file(fp):
    """Loads the specificed PLY file into memory

    Paramters
    ---------
    fp : str
        Filepath of the PLY
    
    Returns
    -------
    Trimesh mesh object
    """
    try:
        msh = tm.load_mesh(file_obj=fp, file_type="ply")
        return msh
    except IOError:
        print(f"Not a PLY file or a generic I/O error.")
        sys.exit(1)


def dxf_3dfaces(dc):
    """Extracts 3DFACEs from a DXF file object in memory

    Paramters
    ---------
    dc : ezdxf.document.Drawing
        DXF file object
    
    Returns
    -------
    list
        A list of 3DFACEs from the DXF
    """
    msp = dc.modelspace()
    fq = msp.query("3DFACE")
    return fq


def triangle_array(fc):
    """Extracts 3DFACEs from a ezdxf.document.Drawing object in memory

    Paramters
    ---------
    fc : ?
        A 3DFACE queried from a DXF file object
    
    Returns
    -------
    array
        An array of the coordinates of the triangle vertices
    """
    trngl = np.array((fc.dxf.vtx0, fc.dxf.vtx1, fc.dxf.vtx2))
    trngl = trngl.reshape(3, 3)
    return trngl


def triangles_to_mesh(ta):
    """Extracts 3DFACEs from a DXF file object in memory

    Paramters
    ---------
    ta : array
        An of array of coordinates for vertices of multiple triangles 
    
    Returns
    -------
    mesh
        A Trimesh mesh object
    """
    trikwargs = tm.triangles.to_kwargs(ta)
    m = tm.Trimesh(**trikwargs, validate=True)
    m.fix_normals()
    return m


def create_workspace_file(flpth):
    """Creates a geoh5 workspace file on disc to hold a coverted file.

    Paramters
    ---------
    flpth : str
        Filepath of the DXF or PLY file being converted 
    
    Returns
    -------
    wkspc
        geoh5 worskspace
    """
    fd, fn = os.path.split(flpth)
    nm = fn.split(".")[0]
    xt = ".geoh5"
    nf = nm+xt
    wkspc = Workspace(os.path.join(fd, nf))
    return wkspc


def geoh5_export(wkspc, msh):
    """Writes a surface to a geoh5 workspace file on disc.

    Paramters
    ---------
    wkspc : object
        Workspace object on disc 
    
    msh : object
        Mesh object from PLY or DXF file
    
    Returns
    -------
    srfc
        Mesh written to geoh5 worskspace
    """
    vrts = msh.vertices
    clls = msh.faces
    srfc = Surface.create(wkspc,
                          vertices=vrts,
                          cells=clls)
    return srfc


def dxf_to_geoh5(dxf_pth):
    """Main function for reading, converting, and writing DXF to geoh5.
    """
    doc = read_dxf_file(dxf_pth)
    face_list = dxf_3dfaces(doc)
    triangle_list = [triangle_array(f) for f in face_list]
    triangle_arrays = np.stack(triangle_list)
    mesh = triangles_to_mesh(triangle_arrays)
    wp = create_workspace_file(dxf_pth)
    geoh5_export(wp, mesh)
    wp.finalize()


def ply_to_geoh5(ply_pth):
    """Main function for reading, converting, and writing PLY to geoh5.
    """
    mesh = read_ply_file(ply_pth)
    wp = create_workspace_file(ply_pth)
    geoh5_export(wp, mesh)
    wp.finalize()


# Script
if __name__ == "__main__":
    if MODE == "single":
        if EXT == "dxf":
            with tqdm(total=100, ncols=80, desc="DXF>GEOH5") as pbar:
                dxf_to_geoh5(INFILE)
                pbar.update(100)
        elif EXT == "ply":
            with tqdm(total=100, ncols=80, desc="PLY>GEOH5") as pbar:
                ply_to_geoh5(INFILE)
                pbar.update(100)
        else:
            print("No valid extension selected.")

    elif MODE == "batch":
        conversion_file_path_list = file_list(INFOLDER, EXT)
        if EXT == "dxf":
            with tqdm(total=len(conversion_file_path_list), ncols=80, desc="DXF>GEOH5") as pbar:
                for dxf in conversion_file_path_list:
                    dxf_to_geoh5(dxf)
                    pbar.update()
        elif EXT == "ply":
            with tqdm(total=len(conversion_file_path_list), ncols=80, desc="PLY>GEOH5") as pbar:
                for ply in conversion_file_path_list:
                    ply_to_geoh5(ply)
                    pbar.update()
        else:
            print("No valid extension selected.")     

    else:
        print("No mode selected.")
