
import os
import numpy as np
from deepcell.applications import Mesmer
from pathlib import Path
import gc
from math import ceil

def find_optimal_tile_size(row_dim, col_dim, overlap, max_tile_dim = 10000, max_tile_area = None):
    max_tile_area = pow(max_tile_dim,2) if max_tile_area == None else max_tile_area

    dims = [row_dim, col_dim]
    dim_1_idx = dims.index(min(dims))
    
    dim_1, dim_2 = (row_dim, col_dim) if dim_1_idx == 0 else (col_dim, row_dim)

    d1= dim_1//max_tile_dim
    r1= dim_1%max_tile_dim
    
    if (d1==0 or (d1==1 and r1==0)):
        tile_size_dim_1 = dim_1
    else:
        tile_size_dim_1 = ceil((dim_1 - overlap)/(d1+1)+overlap)

    dim_2_max = ceil(max_tile_area/tile_size_dim_1)
    
    d2 = (dim_2)//(dim_2_max)
    r2 = (dim_2)%(dim_2_max)

    if (d2==0 or (d2 == 1 and r2 == 0)):
        tile_size_dim_2 = dim_2
    else:
        tile_size_dim_2 = ceil((dim_2 - overlap)/(d2+1)+overlap)

    tile_size_row, tile_size_col = (tile_size_dim_1, tile_size_dim_2) if dim_1_idx == 0 else (tile_size_dim_2,tile_size_dim_1)

    return(int(tile_size_row), int(tile_size_col))


def remove_boundary_mask(arr, boundary, boundary_sides, dummy_var):
    boundary_ids = list()
    for boundary_side in boundary_sides:
        if "t" in boundary_side:
            boundary_mask = arr[0:boundary, :]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
            
        elif "b" in boundary_side:
            boundary_mask = arr[-boundary:, :]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
            
        elif "r" in boundary_side:
            boundary_mask = arr[:, -boundary:]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]

        elif "l" in boundary_side:
            boundary_mask = arr[:, 0:boundary]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
    
    boundary_ids = np.unique(boundary_ids)
    boundary_ids= [i for i in boundary_ids if i != 0]
    cleaned_arr = np.where(np.isin(arr, boundary_ids), dummy_var, arr)

    return(cleaned_arr)
    

def determine_boundaries(img, r0,r1,c0,c1):
    boundaries = list()
    if c0 != 0:
        boundaries.append("l")
    if c1 != img.shape[2]:
        boundaries.append("r")
    if r0 != 0:
        boundaries.append("t")
    if r1 != img.shape[1]:
        boundaries.append("b")
    
    return(boundaries)

def tiled_segmentation_overlap(img, start_row, start_col, stop_row, stop_col, step_size_row, step_size_col, dummy_var, overlap = 0, cutoff=2, background_threshold = 0.1, compartment='whole-cell', app=None, image_mpp = None, postprocess_kwargs_whole_cell={}, postprocess_kwargs_nuclear={}):
    if compartment in ["whole-cell", "nuclear"]:
        mask_array = np.expand_dims(np.full_like(img, -99, dtype=int)[:,:,:,0], 3)
    elif compartment == "both":
        mask_array = np.full_like(img, -99, dtype=int)
    
    if app == None:
        app = Mesmer()

    max_current_cell_id = np.zeros(mask_array.shape[3]) 
    
    for row in range(start_row, stop_row - overlap, step_size_row - overlap):
        for col in range(start_col, stop_col - overlap, step_size_col - overlap):
            r0, r1 = np.maximum(row, 0), np.minimum(np.maximum(row, 0) + step_size_row, img.shape[1])
            c0, c1 = np.maximum(col, 0), np.minimum(np.maximum(col, 0) + step_size_col, img.shape[2])
                        
            boundaries = determine_boundaries(img, r0,r1,c0,c1)
            
            if (np.max(img[:, r0:r1, c0:c1,:]) >= background_threshold) and (np.unique(img[:, r0:r1, c0:c1,0]).shape[0] > 1) and (np.unique(img[:, r0:r1, c0:c1,1]).shape[0] > 1) :
                tmp_segmentation = app.predict(img[:, r0:r1, c0:c1,:], image_mpp = image_mpp, compartment=compartment, postprocess_kwargs_whole_cell=postprocess_kwargs_whole_cell, postprocess_kwargs_nuclear=postprocess_kwargs_nuclear)

                for j in range(tmp_segmentation.shape[3]):
                    tmp_segmentation[0,:,:,j] = remove_boundary_mask(tmp_segmentation[0,:,:,j], cutoff, boundaries, dummy_var)

                    tmp_segmentation[0,:,:,j] = make_cell_mask_unique(tmp_segmentation[0,:,:,j], dummy_var, max_current_cell_id[j])
                    max_current_cell_id[j] = np.maximum(0,np.max(tmp_segmentation[0,:,:,j]))

                    insert_mask = np.isin(mask_array[0, r0:r1, c0:c1, j], [dummy_var, 0])
                    mask_array[0, r0:r1, c0:c1, j][insert_mask] = tmp_segmentation[0,:,:,j][insert_mask]

    gc.collect()
    return(mask_array)


def getval_array(d):
    # based on https://stackoverflow.com/a/46870227
    v = np.array(list(d.values()))
    k = np.array(list(d.keys()))
    maxv = k.max()
    minv = k.min()
    n = maxv - minv + 1
    val = np.empty(n,dtype=v.dtype)
    val[k] = v
    return val


def make_cell_mask_unique(input_array, dummy_var, offset):
    cell_ids = np.unique(input_array)
    cell_ids = cell_ids[~np.isin(cell_ids, [dummy_var, 0])]
    
    transdict = {cell_ids[n] : n + offset + 1 for n in range(0,cell_ids.shape[0])}
    transdict.update({0 : 0})
    transdict.update({dummy_var : dummy_var})
    
    val_arr = getval_array(transdict)
    out = val_arr[input_array]
    
    return(out)


def _combine_overlapping_masks(mask_x, mask_y, dummy_var):
    max_cell_id_x = np.max(mask_x)

    mask_out_x = make_cell_mask_unique(mask_x, dummy_var, 0)
    mask_out_y = make_cell_mask_unique(mask_y, dummy_var, max_cell_id_x)

    # mask_xy = np.copy(mask_x)
    mask_x[np.isin(mask_out_x, dummy_var)] = mask_out_y[np.isin(mask_out_x, dummy_var)]
    gc.collect()
    return(mask_x)

def predict_tiled(img, tile_size_row=None, tile_size_col=None, dummy_var=-99, overlap=0, cutoff=2, background_threshold= 0.1, max_tile_dim = 10000, max_tile_area=None, infer_gaps = False, compartment='whole-cell', cell_size_threshold=None, app=None, image_mpp = None, postprocess_kwargs_whole_cell={}, postprocess_kwargs_nuclear={}):
    #   ensure the image has 4 dimensions to start with and that the last one is 2 dims
    if len(img.shape) != 4:
        raise ValueError(f"Image data must be 4D, got image of shape {img.shape}")
    if img.shape[3] != 2:
        raise ValueError(f"Each FOV/slide must have 2 channels, the image has {img.shape[3]} channels")
    
    
    #   iterate over the first dimension
    for fov_idx in range(img.shape[0]):
        fov = img[[fov_idx], ...]
        overlap = overlap if infer_gaps == True else 0
        if (tile_size_row) == None or (tile_size_col == None):
            tile = find_optimal_tile_size(fov.shape[1], fov.shape[2], overlap, max_tile_dim = max_tile_dim, max_tile_area = max_tile_area)
            step_size_row = tile[0]
            step_size_col = tile[1]
            overlap_tiles = overlap
        else:
            step_size_row = tile_size_row
            step_size_col = tile_size_col
            overlap_tiles = overlap

        
        print("The tile size chosen is: " + str(step_size_row) +"px X " + str(step_size_col) + "px\nThe overlap is: " + str(overlap_tiles) +"px")

        start_row, start_col, stop_row, stop_col = 0, 0, fov.shape[1], fov.shape[2]
        
        _mask = tiled_segmentation_overlap(fov, start_row, start_col, stop_row, stop_col, step_size_row, step_size_col, dummy_var,overlap = overlap_tiles, cutoff = cutoff, background_threshold = background_threshold, compartment = compartment, app=app, image_mpp = image_mpp, postprocess_kwargs_whole_cell=postprocess_kwargs_whole_cell, postprocess_kwargs_nuclear=postprocess_kwargs_nuclear)
        _mask[np.isin(_mask, [-99])] = 0
        
        ## remove small cells
        if (cell_size_threshold != None) and (compartment == 'whole-cell'):
            pixel_count_per_id = np.unique(_mask, return_counts =True)
            low_pixel_count_ids = pixel_count_per_id[0][pixel_count_per_id[1] < cell_size_threshold]
            _mask[np.isin(_mask, low_pixel_count_ids)] = 0

        for j in range(_mask.shape[3]):
            _mask[:,:,:,j] = make_cell_mask_unique(_mask[:,:,:,j], -99, 0)
        
        if fov_idx == 0:
            if img.shape[0] == 1:
                return(_mask)
            else:
                mask = np.copy(_mask)
        else:
            mask = np.concatenate([mask, _mask], axis=0)
        
        gc.collect()
        
    return(mask)