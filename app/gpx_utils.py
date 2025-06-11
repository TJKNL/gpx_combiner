import gpxpy
from typing import List
from fitparse import FitFile
import io
from xml.etree.ElementTree import Element, tostring

def fit_to_gpx_xml(fit_content: bytes) -> str:
    """
    Convert FIT file content (bytes) to a GPX XML string.
    Includes track points and all available workout details as <extensions>.
    """
    fitfile = FitFile(io.BytesIO(fit_content))
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)
    for record in fitfile.get_messages('record'):
        fields = {d.name: d.value for d in record}
        lat = fields.get('position_lat')
        lon = fields.get('position_long')
        if lat is not None and lon is not None:
            # Convert semicircles to degrees
            lat = lat * (180 / 2**31)
            lon = lon * (180 / 2**31)
            ele = fields.get('altitude')
            time = fields.get('timestamp')
            pt = gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=ele, time=time)
            # Add all available workout details as extensions
            ext = Element('extensions')
            for k, v in fields.items():
                if k not in ('position_lat', 'position_long', 'altitude', 'timestamp') and v is not None:
                    sub = Element(f'fit:{k}')
                    sub.text = str(v)
                    ext.append(sub)
            if len(ext):
                pt.extensions = [ext]
            segment.points.append(pt)
    return gpx.to_xml()

def combine_gpx_files(file_contents: List[tuple[str, bytes]]) -> str:
    """
    Combine multiple GPX and FIT file contents into a single GPX string.
    file_contents: list of (filename, content_bytes)
    """
    if not file_contents:
        raise ValueError("No files provided.")
    gpx_objs = []
    for filename, content in file_contents:
        if filename.lower().endswith('.gpx'):
            gpx_objs.append(gpxpy.parse(content.decode('utf-8')))
        elif filename.lower().endswith('.fit'):
            gpx_xml = fit_to_gpx_xml(content)
            gpx_objs.append(gpxpy.parse(gpx_xml))
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    # Use the first as base
    base_gpx = gpx_objs[0]
    for gpx in gpx_objs[1:]:
        for track in gpx.tracks:
            base_gpx.tracks.append(track)
        for route in gpx.routes:
            base_gpx.routes.append(route)
        for waypoint in gpx.waypoints:
            base_gpx.waypoints.append(waypoint)
    return base_gpx.to_xml() 