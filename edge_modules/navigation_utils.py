import math
import numpy as np

from edge_modules.config import BASE_LAT, BASE_LON


def fake_gps_from_odom(x_m, y_m):
    return {
        "lat": BASE_LAT + x_m / 111000.0,
        "lon": BASE_LON + y_m / 88000.0,
    }


def pixel_x_to_angle(x_px, image_w, camera_fov_deg):
    fov_rad = math.radians(camera_fov_deg)
    ratio = float(x_px) / float(image_w)
    return (ratio - 0.5) * fov_rad


def bbox_short_median_distance(
    bbox,
    image_w,
    angle_min,
    angle_max,
    angle_inc,
    ranges,
    camera_fov_deg,
    max_range=12.0,
    num_samples=100,
    short_k=3,
):
    if not ranges or image_w <= 0:
        return None, None, 0

    x1, _, x2, _ = bbox
    bbox_width = max(1, x2 - x1 + 1)
    sample_count = int(min(num_samples, max(5, bbox_width)))
    xs = np.linspace(x1, x2, sample_count).astype(int)

    valid_pairs = []
    for x in xs:
        angle_global = pixel_x_to_angle(x, image_w, camera_fov_deg)
        idx = int(round((angle_global - angle_min) / angle_inc))

        if 0 <= idx < len(ranges):
            dist = float(ranges[idx])
            if 0.02 < dist < max_range:
                valid_pairs.append((dist, idx))

    if not valid_pairs:
        return None, None, 0

    valid_pairs.sort(key=lambda item: item[0])
    short_group = valid_pairs[: min(short_k, len(valid_pairs))]

    short_dists = [d for d, _ in short_group]
    short_idxs = [i for _, i in short_group]

    stable_dist = float(np.median(short_dists))
    stable_idx = int(np.median(short_idxs))
    return stable_dist, stable_idx, len(valid_pairs)
