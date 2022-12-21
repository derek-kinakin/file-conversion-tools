"""
Convert triangular meshes to GEOH5 format file.

Reads the following:
* 3DFACEs from a DXF file
* Any triangular mesh format supported by PyVista (PLY, OBJ, VTK, etc.)

Each target file should contain a single triangulated mesh surface or solid. 

Saves the triangulated mesh as a geoh5 workspace file containing a single mesh
object.

Processes files in "single" or "batch" mode.

@author: D. Kinakin; J. Danielson

Change log:
2022-03-04 Initial version created for PLY and DXF
2022-12-19 Updates to use PyVista to expand supported formats

"""

import sys
import numpy as np
import ezdxf as ed
import pyvista as pv

from pathlib import Path
from tqdm import tqdm
from geoh5py.workspace import Workspace
from geoh5py.objects import Surface

# Globals
MODE = "single"  # batch or single
INFOLDER = r"C:\Users\dkinakin\some_folder"  # for batch mode
INFILE = r"C:\Users\dkinakin\some_file.dxf"  # for single file mode

# Functions
def file_list(fld_pth):
    """List of files and paths

    Args:
        fld_pth: Folder path to all files

    Returns:
        file_list: List of full file paths
    """
    
    pth_obj = Path(fld_pth)
    file_list = list(pth_obj.iterdir())
    return file_list


def read_dxf_file(fp):
    """Loads the specificed DXF document into memory

    Args:
        fp: Filepath of the folder containing the DXF
        fl: Filename of the DXF

    Returns:
        d: DXF file object
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


def read_pyvista_compatible_file(fp):
    """Loads the specificed PLY file into memory

    Args:
        fp: Filepath of the PLY

    Returns:
        msh: PyVista mesh object
    """
    
    msh = pv.read(fp)
    return msh


def extract_dxf_3dfaces(dc):
    """Extracts 3DFACEs from a DXF file object in memory

    Args:
        dc: ezdxf.document.Drawing DXF file object

    Returns:
        fq: A list of 3DFACEs from the DXF
    """
    
    msp = dc.modelspace()
    fq = msp.query("3DFACE")
    return fq


def create_triangle_array(fc):
    """Create vertices for list of 3DFACEs

    Args:
        fc: A 3DFACE queried from a DXF file object

    Returns:
        trngls: An array of the coordinates of the triangle vertices
    """
    
    trngls = np.array((fc.dxf.vtx0, fc.dxf.vtx1, fc.dxf.vtx2))
    trngls = trngls.reshape(3, 3)
    return trngls


def dxf_triangle_list_to_pv_mesh(trngl_vrtx_lst):
    """Extracts 3DFACEs from a DXF file object in memory

    Args:
        trngl_vrtx_lst: List of 3x3 arrays of coordinates for vertices of 
                        multiple triangles

    Returns:
        mesh: A PyVista mesh object
    """
    
    triangle_array = np.stack(trngl_vrtx_lst)
    vertices = triangle_array.reshape((-1, 3))
    faces = np.arange(len(vertices)).reshape((-1, 3))
    msh = pv.make_tri_mesh(vertices, faces)
    return msh


def create_workspace_file(flpth):
    """Creates a geoh5 workspace file on disc to hold a coverted file.

    Args:
        flpth: Path object for the location of mesh

    Returns:
        wkspc: geoh5 workspace
    """
    
    fd = flpth.parent 
    fn = flpth.stem
    xt = ".geoh5"
    nf = fn + xt
    wkspc = Workspace(fd.joinpath(nf))
    return wkspc


def pv_mesh_to_geoh5_surface(pvmsh, gh5wkspc, msh_nm):
    """Writes a PyVista mesh to a geoh5 file on disc.

    Args:
        msh: PyVista mesh object
        wkspc: Geoh5 workspace object on disc

    Returns:
        srfc: Mesh written to geoh5
    """

    vrts = pvmsh.points
    # extract triangle faces without VTK padding
    clls = pvmsh.faces.reshape((pvmsh.n_faces, 4))[:, 1:]  
    srfc = Surface.create(gh5wkspc, vertices=vrts, cells=clls, name=msh_nm)
    return srfc


def dxf_tri_mesh_to_pyvista_mesh(dxf_pth):
    """Convert triangular mesh in DXF format to PyVista PolyData mesh object.

    Args:
        dxf_pth (Path object): Path to tringular mesh in DXF format

    Returns:
        mesh (PyVista PolyData): Triangular mesh object
    """
    
    doc = read_dxf_file(dxf_pth)
    face_list = extract_dxf_3dfaces(doc)
    triangle_vertex_list = [create_triangle_array(f) for f in face_list]
    mesh = dxf_triangle_list_to_pv_mesh(triangle_vertex_list)
    return mesh


def mesh_file_to_geoh5_file(msh_pth):
    """Main function for reading, converting, and writing PLY to geoh5.
    
    Args:
        msh_pth: Path object for mesh location on disk
        decimate: Bool
        decimate_target: Fraction of vertices to remove
    
    Returns:
        None
    """
    msh_name = msh_pth.stem
    
    if msh_pth.suffix == ".dxf":
        msh = dxf_tri_mesh_to_pyvista_mesh(msh_pth)
    else:
        msh = read_pyvista_compatible_file(msh_pth)
    
    wp = create_workspace_file(msh_pth)
    pv_mesh_to_geoh5_surface(msh, wp, msh_name)
    wp.close()


# Script
if __name__ == "__main__":
    if MODE == "single":
        target_path = Path(INFILE)
        with tqdm(total=100,
                  ncols=80,
                  desc="WRITING SINGLE GEOH5...") as pbar:
            mesh_file_to_geoh5_file(target_path)
            pbar.update(100)

    elif MODE == "batch":
        file_path_list = file_list(INFOLDER)
        with tqdm(total=len(file_path_list),
                  ncols=80,
                  desc="BATCH WRITING TO GEOH5...") as pbar:
            for pth in file_path_list:
                target_path = Path(pth)
                mesh_file_to_geoh5_file(target_path)
                pbar.update()
    else:
        print("No mode selected.")
