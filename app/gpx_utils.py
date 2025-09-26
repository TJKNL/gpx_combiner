import gpxpy
from typing import List
from fitparse import FitFile
import io
from xml.etree.ElementTree import Element
import datetime as dt
import copy

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

def combine_gpx_files(
    file_contents: List[tuple[str, bytes]],
    *,
    single_track: bool = True,
    fill_pauses: bool = True,
    gap_threshold_seconds: int = 600
) -> str:
    """
    Combine multiple GPX and FIT file contents into a single GPX string.

    - single_track=True merges all points into one <trk>/<trkseg> sorted by time.
      This avoids platforms interpreting multiple tracks as separate rides.
    - fill_pauses=True will insert minimal stationary points around large gaps
      to mark them as 'paused' time without changing distance.

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

    if not single_track:
        # Backwards-compatible behavior (multiple tracks)
        base_gpx = gpx_objs[0]
        for gpx in gpx_objs[1:]:
            for track in gpx.tracks:
                base_gpx.tracks.append(track)
            for route in gpx.routes:
                base_gpx.routes.append(route)
            for waypoint in gpx.waypoints:
                base_gpx.waypoints.append(waypoint)
        return base_gpx.to_xml(version='1.1')

    # New behavior: produce a single track + single segment with all points in time order
    all_points = []
    for g in gpx_objs:
        for trk in g.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    all_points.append(pt)

    if not all_points:
        raise ValueError("No track points found in provided files.")

    # Split into timed and non-timed points; keep insertion order for non-timed
    timed = [p for p in all_points if p.time is not None]
    untimed = [p for p in all_points if p.time is None]
    timed.sort(key=lambda p: p.time)

    # Create new GPX with known extensions to ensure extension prefixes serialize cleanly
    new_gpx = gpxpy.gpx.GPX()
    new_gpx.nsmap = {
        'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
        'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
        'fit': 'http://www.garmin.com/xmlschemas/FitPoint/v1'
    }
    track = gpxpy.gpx.GPXTrack(name="Combined Activity")
    new_gpx.tracks.append(track)
    seg = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(seg)

    def clone_point(src_pt, override_time=None):
        dst = gpxpy.gpx.GPXTrackPoint(
            latitude=src_pt.latitude,
            longitude=src_pt.longitude,
            elevation=src_pt.elevation,
            time=override_time if override_time is not None else src_pt.time,
            speed=getattr(src_pt, 'speed', None)
        )
        # Deep copy extensions to avoid cross-tree element reuse issues
        if getattr(src_pt, 'extensions', None):
            for ext in src_pt.extensions:
                dst.extensions.append(copy.deepcopy(ext))
        return dst

    # Add timed points, optionally inserting minimal stationary points around large gaps
    prev = None
    for p in timed:
        if fill_pauses and prev is not None:
            delta = (p.time - prev.time).total_seconds()
            if delta > gap_threshold_seconds:
                # Insert two stationary points to mark a long pause window without adding distance.
                before = clone_point(prev, override_time=prev.time + dt.timedelta(seconds=1))
                after = clone_point(prev, override_time=p.time - dt.timedelta(seconds=1))
                seg.points.append(before)
                seg.points.append(after)
        seg.points.append(clone_point(p))
        prev = p

    # Append any untimed points at the end, preserving their original order
    for p in untimed:
        seg.points.append(clone_point(p))

    # Set metadata time as the start if available
    if timed:
        new_gpx.time = timed[0].time

    return new_gpx.to_xml(version='1.1') 