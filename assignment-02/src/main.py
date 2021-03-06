from PIL import Image, ImageOps
import numpy as np
import itertools
import functools
import operator

class DetailedImage(object):
    def __init__(self, raw_content):
        self.raw_content = raw_content
        self.rows, self.columns = raw_content.size

    def raw_image_copy(self):
        return self.raw_content.copy()

    def meta_copy(self):
        return self.raw_image_copy(), itertools.product(range(self.rows), range(self.columns))


def load_image(path):
    raw_image = Image.open(path)
    return DetailedImage(raw_content=raw_image)


def show_image(detailed_image):
    image = detailed_image.raw_content
    image.show()


def rgb_to_y_band(image):
    image, image_range = image.meta_copy()
    pixels = image.load()

    for i, j in image_range:
        R, G, B = pixels[i, j]
        Y_B = int(R * 0.299 + G * 0.587 + B * 0.114)
        pixels[i, j] = (Y_B, Y_B, Y_B)

    return DetailedImage(image)


def histogram_expansion(image):
    def gxy(fxy, min, max):
        return int(((fxy - min) * 255)/(max-min))

    image, image_range = image.meta_copy()
    pixels = image.load()
    mimax, _, _ = image.getextrema()
    min, max = mimax[0], mimax[1]

    for i, j in image_range:
        fxy, _, _ = pixels[i, j]

        expanded_px = gxy(fxy, min, max)
        pixels[i, j] = (expanded_px, expanded_px, expanded_px)

    return DetailedImage(image)

def histogram_equalization(image):
    """
    Create a uniform distribution of grayscale values in
    the output image by applying a non linear mapping based on
    Pillow's histogram equalization algorithm [IM]
    """
    image, image_range = image.meta_copy()
    pixels = image.load()
    range_256 = range(256)
    original_histogram = image.histogram()
    lookup_table = []
    for band_idx in range(0, len(original_histogram), 256):
        histo = [_f for _f in original_histogram[band_idx:band_idx+256] if _f]
        if len(histo) <= 1:
            lookup_table.extend(list(range_256))
        else:
            step = (functools.reduce(operator.add, histo) - histo[-1]) // 255
            if not step:
                lookup_table.extend(list(range_256))
            else:
                n = step // 2
                for i in range_256:
                    lookup_table.append(n // step)
                    n = n + original_histogram[i+band_idx]

    return DetailedImage(image.point(lookup_table))


def masked(image, mask):
    rows, columns = image.rows, image.columns
    image, _ = image.meta_copy()
    pixels = image.load()
    npimage = np.array(image)
    mask_dimm = mask[0].size
    border_limit = mask_dimm - 1

    row_range = range(border_limit, rows - border_limit)
    col_range = range(border_limit, columns - border_limit)
    image_range = itertools.product(row_range, col_range)

    for i, j in image_range:
        newMask = npimage[i: i + mask_dimm, j: j + mask_dimm]
        masked_component = int(np.sum(mask * newMask[:, :, 0]))
        pixels[j, i] = (masked_component, masked_component, masked_component)

    image = ImageOps.crop(image, border=mask_dimm)
    return DetailedImage(image)


def simulate(image):
    # Original image [IM]
    show_image(image)

    # Y band / grayscale image [IM]
    y_band_image = rgb_to_y_band(image)
    show_image(y_band_image)

    # First sharpness filter with variants c and d [IM]
    def build_a1_mask(c, d):
        return np.array([
            [ 0,  -c,      0],
            [-c,   4*c+d, -c],
            [ 0,  -c,      0]
        ])

    # Second sharpness filter with variants c and d [IM]
    def build_a2_mask(c, d):
        return np.array([
            [-c,  -c,     -c],
            [-c,   8*c+d, -c],
            [-c,  -c,     -c]
        ])

    # Sharpness filter tests with variants [IM]
    for c_d_variant in [
        ( 1,  1), # default variant [IM]
        ( 3,  3), (-2, 2), ( 4,   2),
        ( 5,  0), (-5, 0), (-255, 0)
    ]:
        c, d = c_d_variant
        a1_mask = build_a1_mask(c, d)
        show_image(masked(y_band_image, a1_mask))
        a2_mask = build_a2_mask(c, d)
        show_image(masked(y_band_image, a2_mask))

    # Border detection filters [IM]
    b1_mask = np.array([
        [-1/8, -1/8, -1/8],
        [-1/8,  1,   -1/8],
        [-1/8, -1/8, -1/8]
    ])
    show_image(masked(y_band_image, b1_mask))

    b2_mask = np.array([
        [-1, -1, -1],
        [ 0,  0,  0],
        [ 1,  1,  1]
    ])
    show_image(masked(y_band_image, b2_mask))

    b3_mask = np.array([
        [-1,  0, 1],
        [-1,  0, 1],
        [-1,  0, 1]
    ])
    show_image(masked(y_band_image, b3_mask))

    b4_mask = np.array([
        [-1, -1,  0],
        [-1,  0,  1],
        [ 0,  1,  1]
    ])
    show_image(masked(y_band_image, b4_mask))

    # Emboss filters [IM]
    c1_mask = np.array([
        [ 0,  0,  0],
        [ 0,  1,  0],
        [ 0,  0, -1]
    ])
    show_image(masked(y_band_image, c1_mask))

    c2_mask = np.array([
        [ 0,  0, -1],
        [ 0,  1,  0],
        [ 0,  0,  0]
    ])
    show_image(masked(y_band_image, c2_mask))

    c3_mask = np.array([
        [ 0,  0, 2],
        [ 0, -1, 0],
        [-1,  0, 0]
    ])
    show_image(masked(y_band_image, c3_mask))

    # Histogram expansion [IM]
    expanded = histogram_expansion(y_band_image)
    show_image(expanded)

    # Histogram equalization [IM]
    equalized = histogram_equalization(y_band_image)
    show_image(equalized)

    # Histogram equalziation over expansion (expansion -> equalization) [IM]
    expanded_and_equalized = histogram_equalization(expanded)
    show_image(expanded_and_equalized)

    # Histogram expansion over equalization (equalization -> expansion) [IM]
    equalized_and_expanded = histogram_expansion(equalized)
    show_image(equalized_and_expanded)


def main():
    LENA_IMAGE_PATH = "../assets/images/lena.jpg"
    LENA_128_IMAGE_PATH = "../assets/images/lena_128.jpg"
    LENA_256_IMAGE_PATH = "../assets/images/lena_256.jpg"
    BABOON_256_IMAGE_PATH = "../assets/images/baboon_256.jpg"
    CAMERAMAN_IMAGE_PATH = "../assets/images/cameraman.jpg"
    SAT_IMAGE_PATH = "../assets/images/sat.jpg"

    image = load_image(LENA_256_IMAGE_PATH)
    simulate(image=image)

if __name__ == '__main__':
    main()
