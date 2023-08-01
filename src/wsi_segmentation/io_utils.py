# def split_ome_tiff()




# def create_segmentation_image()




# def load_segmentation_image()




# def save_segmentation_mask()

def save_model_output_wrapper(segmentation_mask, output_dir, feature_name, compartment):
    save_model_output(segmentation_mask, output_dir=output_dir, feature_name=feature_name)
    # rename saved mask tiff
    old_name = feature_name + '_feature_0_frame_000.tif'
    
    if compartment == "both":
        suffix = ["nuclear", "whole_cell"]
    elif compartment == "whole-cell":
        suffix = "whole_cell"
    elif compartment == "nuclear":
        suffix = "nuclear"
        
    new_name = feature_name + '_' + suffix + '.tiff'
    
    old_name_path = os.path.join(output_dir, old_name)
    new_name_path =  os.path.join(output_dir, new_name)
    os.rename(old_name_path,new_name_path)