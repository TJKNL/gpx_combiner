import pytest
from app.gpx_utils import combine_gpx_files

def test_combine_gpx_files():
    gpx1 = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test">
      <trk><name>Track 1</name><trkseg><trkpt lat="1" lon="1"></trkpt></trkseg></trk>
    </gpx>'''
    gpx2 = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test">
      <trk><name>Track 2</name><trkseg><trkpt lat="2" lon="2"></trkpt></trkseg></trk>
    </gpx>'''
    combined = combine_gpx_files([gpx1, gpx2])
    assert "Track 1" in combined
    assert "Track 2" in combined
    assert combined.count("<trk>") == 2 