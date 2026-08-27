from pathlib import Path

import numpy as np
import oic_toolkit
import pandas as pd
import skimage
from bioio import BioImage
from matplotlib import pyplot as plt


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


def count_nuclei(image_path, output_dir, debug=False):

    image_path = Path(image_path)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    reader = BioImage(image_path)
    image = reader.get_image_data("YX", Z=0, C=0)

    threshold = skimage.filters.threshold_otsu(image)

    mask = image > (0.8 * threshold)
    mask = skimage.morphology.opening(mask, skimage.morphology.disk(2))
    mask = skimage.morphology.remove_small_objects(mask, max_size=10)

    # Find large objects
    mask_large = skimage.morphology.remove_small_objects(mask, max_size=2000)

    mask_final = mask ^ mask_large

    # Watershed

    label_final = oic_toolkit.segment.separate_objects(mask_final)

    # Measure data
    cell_data = skimage.measure.regionprops(label_final)

    mask_centroid = np.zeros_like(mask)
    for cell in cell_data:
        rr, cc = skimage.draw.disk(cell.centroid, radius=3, shape=image.shape)
        mask_centroid[rr, cc] = 255

    overlay = oic_toolkit.display.overlay_mask(image, label_final > 0)
    overlay = oic_toolkit.display.overlay_mask(
        overlay, mask_centroid, color=(1, 1, 0), alpha=1
    )

    if debug:
        plt.imshow(overlay)
        plt.show()

    # Get a quick count
    num_objects = len(np.unique(label_final))

    fn = image_path.stem
    skimage.io.imsave(output_dir / (fn + ".png"), overlay, check_contrast=False)
    skimage.io.imsave(
        output_dir / (fn + "_labels.tif"), label_final, check_contrast=False
    )

    return num_objects


def main():
    print("Hello from template-analysis-uv!")


if __name__ == "__main__":
    main()
