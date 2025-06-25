import gpxpy
from typing import List
from fitparse import FitFile
import io
from xml.etree.ElementTree import Element

# Constant for converting from Garmin's semicircle format to degrees
SEMICIRCLES_TO_DEGREES = 180 / 2**31

def fit_to_gpx_xml(fit_content: bytes) -> str:
    """
    Convert FIT file content (bytes) to a GPX XML string.
    Includes track points and all available workout details as <extensions>.
    """
    fitfile = FitFile(io.BytesIO(fit_content))
    gpx = gpxpy.gpx.GPX()

    # Define namespaces for better GPX compatibility
    gpx.nsmap = {
        'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
        'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
        'fit': 'http://www.garmin.com/xmlschemas/FitPoint/v1'
    }
    
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    # Fields that are part of the standard GPX trackpoint
    base_fields = {'position_lat', 'position_long', 'altitude', 'timestamp'}

    for record in fitfile.get_messages('record'):
        fields = {d.name: d.value for d in record}
        lat = fields.get('position_lat')
        lon = fields.get('position_long')

        if lat is not None and lon is not None:
            lat *= SEMICIRCLES_TO_DEGREES
            lon *= SEMICIRCLES_TO_DEGREES
            
            pt = gpxpy.gpx.GPXTrackPoint(
                latitude=lat,
                longitude=lon,
                elevation=fields.get('altitude'),
                time=fields.get('timestamp')
            )
            
            # Find fields that are not part of the base GPX data to add as extensions
            extension_fields = {k: v for k, v in fields.items() if k not in base_fields and v is not None}
            
            if extension_fields:
                ext_element = Element('gpxtpx:TrackPointExtension')
                for key, value in extension_fields.items():
                    sub_element = Element(f'fit:{key}')
                    sub_element.text = str(value)
                    ext_element.append(sub_element)
                pt.extensions.append(ext_element)
            
            segment.points.append(pt)
            
    return gpx.to_xml(version='1.1')

def combine_gpx_files(file_contents: List[tuple[str, bytes]]) -> str:
    """
    Combine multiple GPX and FIT file contents into a single GPX string.
    file_contents: list of (filename, content_bytes)
    """
    if not file_contents:
        raise ValueError("No files provided.")

    gpx_objs = []
    for filename, content in file_contents:
        try:
            if filename.lower().endswith('.gpx'):
                gpx_objs.append(gpxpy.parse(content.decode('utf-8')))
            elif filename.lower().endswith('.fit'):
                gpx_xml = fit_to_gpx_xml(content)
                gpx_objs.append(gpxpy.parse(gpx_xml))
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            # Add context to the error for better debugging.
            # Using `from e` preserves the original traceback.
            raise ValueError(f"Failed to process file '{filename}': {e}") from e

    if not gpx_objs:
        raise ValueError("No valid GPX data could be parsed from the provided files.")

    # Use the first GPX object as the base and merge others into it
    base_gpx = gpx_objs[0]
    for gpx in gpx_objs[1:]:
        for track in gpx.tracks:
            base_gpx.tracks.append(track)
        for route in gpx.routes:
            base_gpx.routes.append(route)
        for waypoint in gpx.waypoints:
            base_gpx.waypoints.append(waypoint)

    return base_gpx.to_xml(version='1.1') 