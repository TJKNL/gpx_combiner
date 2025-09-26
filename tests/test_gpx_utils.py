import pytest
from app.gpx_utils import combine_gpx_files

def test_combine_gpx_files_single_track():
    gpx1 = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test">
      <trk><name>Track 1</name><trkseg><trkpt lat="1" lon="1"></trkpt></trkseg></trk>
    </gpx>'''
    gpx2 = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test">
      <trk><name>Track 2</name><trkseg><trkpt lat="2" lon="2"></trkpt></trkseg></trk>
    </gpx>'''
    combined = combine_gpx_files([
        ("track1.gpx", gpx1.encode('utf-8')),
        ("track2.gpx", gpx2.encode('utf-8'))
    ])
    # Should result in a single <trk> with two <trkpt> points
    assert combined.count("<trk>") == 1
    assert combined.count("<trkpt") == 2

def test_combine_gpx_files_multiple_tracks():
    gpx1 = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test">
      <trk><name>Track 1</name><trkseg><trkpt lat="1" lon="1"></trkpt></trkseg></trk>
    </gpx>'''
    gpx2 = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test">
      <trk><name>Track 2</name><trkseg><trkpt lat="2" lon="2"></trkpt></trkseg></trk>
    </gpx>'''
    combined = combine_gpx_files([
        ("track1.gpx", gpx1.encode('utf-8')),
        ("track2.gpx", gpx2.encode('utf-8'))
    ], single_track=False)
    # Backwards-compatible behavior should result in multiple tracks
    assert combined.count("<trk>") == 2 