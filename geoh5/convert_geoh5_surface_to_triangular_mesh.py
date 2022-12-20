"""
Convert a GEOH5 surface to a PLY mesh.

Reads the one or multiple surface objects from a GEOH5 format files and saves
the object as a PLY file to disk.

Processes files in "single" or "batch" mode.

@author: D. Kinakin

Change log:
2022-12-20 Initial version

"""

import pyvista as pv

from pathlib import Path
from tqdm import tqdm
from geoh5py.workspace import Workspace

# Globals
MODE = "single"  # batch or single
INFOLDER = r"C:\Users\dkinakin\Desktop\OT GI data\Pit designs\surfs\small"  # for batch mode
INFILE = r"C:\Users\dkinakin\Desktop\OT GI data\Pit designs\surfs\small\P5a_v4.4_surf.geoh5"  # for single file mode

# Functions
def file_list(fld_pth):
    """List of files and paths

    Args:
        fld_pth: Folder path to all files

    Returns:
        file_list: List of full file paths
    """
    
    pth_obj = Path(fld_pth)
    xt = "*.geoh5"
    file_list = sorted(pth_obj.glob(xt))
    return file_list


def create_solid_entity_list(wp):
    slds_lst = []
    for g in wp.groups:
        slds_lst.extend(wp.get_entity(g.name)[0].children)
    #TODO: Add check to ensure surface objects only...
    return slds_lst


def geoh5_file_to_mesh_file(msh_pth):
    with Workspace(msh_pth) as workspace:
        solids_entity_list = create_solid_entity_list(workspace)
        for fp in solids_entity_list:
            name = fp.name
            mesh_verts = fp.vertices
            mesh_faces = fp.cells
            pv_msh = pv.make_tri_mesh(mesh_verts, mesh_faces)
            fd = msh_pth.parent
            if msh_pth.stem == name:
                msh_name = name
            else:
                msh_name = f"{msh_pth.stem}_{name}"
            xt = ".ply"
            nf = msh_name + xt
            save_path = fd.joinpath(nf)
            pv_msh.save(save_path)


# Script
if __name__ == "__main__":
    if MODE == "single":
        target_path = Path(INFILE)
        with tqdm(total=100,
                  ncols=80,
                  desc="WRITING SINGLE PLY...") as pbar:
            geoh5_file_to_mesh_file(target_path)
            pbar.update(100)

    elif MODE == "batch":
        file_path_list = file_list(INFOLDER)
        with tqdm(total=len(file_path_list),
                  ncols=80,
                  desc="BATCH WRITING TO PLY...") as pbar:
            for pth in file_path_list:
                target_path = Path(pth)
                geoh5_file_to_mesh_file(target_path)
                pbar.update()
    else:
        print("No mode selected.")
