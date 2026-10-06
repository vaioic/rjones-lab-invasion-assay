from pathlib import Path

import cv2
import numpy as np
import oic_toolkit
import pandas as pd
import skimage
from bioio import BioImage
from cellpose import models
from matplotlib import pyplot as plt

model = models.CellposeModel(gpu=True)


def process_directory(source_dir, output_dir):

    source_dir = Path(source_dir)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all images in source
    image_list = list(source_dir.glob("*.czi"))

    all_data = []
    for image in image_list:
        count = count_nuclei(image, output_dir)

        all_data.append(
            {
                "filename": image.stem,
                "count": count,
            }
        )

    df = pd.DataFrame(all_data)
    df.to_csv(output_dir / "counts.csv")


def segment_nuclei(image_path, output_dir, debug=True):

    image_path = Path(image_path)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    reader = BioImage(image_path)
    image = reader.get_image_data("YX", Z=0, C=0)

    image_filt = skimage.morphology.opening(image, skimage.morphology.disk(3))

    plt.imshow(image_filt)
    plt.show()

    exit()

    image[mask_low] = np.min(image)

    # files = ['/media/carsen/DATA1/TIFFS/onechan.tif']

    # imgs = [imread(f) for f in files]
    # nimg = len(imgs)

    masks, _, _ = model.eval(image)

    if debug:
        rgb_labels = skimage.color.label2rgb(masks, bg_label=0, image=image)
        merged = oic_toolkit.display.merge_images(image, rgb_labels, mode="blend")
        plt.imshow(merged)
        plt.show()

    return masks


font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1
color = (255, 0, 255)  # Green color in BGR format
thickness = 2

# Predefine the cell area
max_cell_area = 735


def count_nuclei(image_path, output_dir, debug=False):

    image_path = Path(image_path)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    reader = BioImage(image_path)
    image = reader.get_image_data("YX", Z=0, C=0)

    threshold = skimage.filters.threshold_otsu(image)

    mask = image > (0.65 * threshold)
    mask = skimage.morphology.opening(mask, skimage.morphology.disk(2))
    mask = skimage.morphology.remove_small_objects(mask, max_size=10)

    # Find large objects
    mask_large = skimage.morphology.remove_small_objects(mask, max_size=2000)

    # Mask  only the single cells
    mask_final = mask ^ mask_large

    # Watershed the single cells
    label_final = oic_toolkit.segment.separate_objects(mask_final)

    # Measure single-cell data
    cell_data = skimage.measure.regionprops(label_final)

    mask_centroid = np.zeros_like(mask)
    for cell in cell_data:
        rr, cc = skimage.draw.disk(cell.centroid, radius=3, shape=image.shape)
        mask_centroid[rr, cc] = 255

    overlay = oic_toolkit.display.overlay_mask(image, label_final > 0, alpha=0.2)

    overlay = oic_toolkit.display.overlay_mask(
        overlay, mask_centroid, mask_color=(1, 0, 0), alpha=1
    )

    # Get a quick count
    num_objects = len(np.unique(label_final))

    # # Calculate the average area of single cells
    # max_cell_area = np.mean([prop.area for prop in cell_data])
    # print(max_cell_area)
    # exit()

    # Attempt to estimate the number of equivalent cells in the larger objects
    mask_artifact = skimage.morphology.remove_small_objects(mask, max_size=30000)

    mask_large = mask_large ^ mask_artifact

    overlay = oic_toolkit.display.overlay_mask(
        overlay, mask_large, mask_color=(0, 1, 0), alpha=0.2
    )

    labels_large = skimage.measure.label(mask_large)

    cell_data_large = skimage.measure.regionprops(labels_large)

    for large_cell in cell_data_large:
        est_num_objects = int(np.floor((large_cell.area) / max_cell_area))
        num_objects += est_num_objects

        yy, xx = large_cell.centroid

        cv2.putText(
            overlay,
            str(est_num_objects),
            (int(xx), int(yy)),
            font,
            font_scale,
            color,
            thickness,
        )

    label_final = label_final + labels_large

    if debug:
        plt.imshow(overlay)
        plt.show()

    fn = image_path.stem
    skimage.io.imsave(output_dir / (fn + ".png"), overlay, check_contrast=False)
    skimage.io.imsave(
        output_dir / (fn + "_labels.tif"), label_final, check_contrast=False
    )

    return num_objects
