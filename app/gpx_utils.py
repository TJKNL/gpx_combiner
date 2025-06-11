import gpxpy
from typing import List


def combine_gpx_files(gpx_file_contents: List[str]) -> str:
    """
    Combine multiple GPX file contents into a single GPX string.
    """
    if not gpx_file_contents:
        raise ValueError("No GPX files provided.")

    # Parse the first file as the base
    base_gpx = gpxpy.parse(gpx_file_contents[0])

    for content in gpx_file_contents[1:]:
        gpx = gpxpy.parse(content)
        for track in gpx.tracks:
            base_gpx.tracks.append(track)
        for route in gpx.routes:
            base_gpx.routes.append(route)
        for waypoint in gpx.waypoints:
            base_gpx.waypoints.append(waypoint)

    return base_gpx.to_xml() 