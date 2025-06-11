const form = document.getElementById('upload-form');
const fileInput = document.getElementById('gpx-files');
const fileListDiv = document.getElementById('file-list');
const mapDiv = document.getElementById('map');
const downloadLink = document.getElementById('download-link');
let map, gpxLayers = [];

function updateFileList(files) {
    fileListDiv.innerHTML = '';
    if (files.length === 0) return;
    const ul = document.createElement('ul');
    ul.className = 'list-disc pl-5';
    Array.from(files).forEach((file, i) => {
        const li = document.createElement('li');
        li.textContent = `${i + 1}. ${file.name}`;
        ul.appendChild(li);
    });
    fileListDiv.appendChild(ul);
}

function initMap() {
    if (map) return;
    map = L.map('map').setView([48.8584, 2.2945], 3); // Default to Europe
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

function clearMap() {
    gpxLayers.forEach(layer => map.removeLayer(layer));
    gpxLayers = [];
}

function plotGPX(gpxText) {
    // Use leaflet-gpx for parsing (CDN)
    if (typeof L.GPX !== 'function') {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet-gpx/1.7.0/gpx.min.js';
        script.onload = () => plotGPX(gpxText);
        document.body.appendChild(script);
        return;
    }
    const gpxLayer = new L.GPX(gpxText, {
        async: true,
        marker_options: { startIconUrl: null, endIconUrl: null, shadowUrl: null }
    }).on('loaded', function(e) {
        map.fitBounds(e.target.getBounds());
    }).addTo(map);
    gpxLayers.push(gpxLayer);
}

fileInput.addEventListener('change', (e) => {
    updateFileList(e.target.files);
    clearMap();
    Array.from(e.target.files).forEach(file => {
        const reader = new FileReader();
        reader.onload = (evt) => {
            plotGPX(evt.target.result);
        };
        reader.readAsText(file);
    });
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files.length) return;
    const formData = new FormData();
    Array.from(fileInput.files).forEach(f => formData.append('files', f));
    const res = await fetch('/upload', {
        method: 'POST',
        body: formData
    });
    if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        downloadLink.href = url;
        downloadLink.download = 'combined.gpx';
        downloadLink.classList.remove('hidden');
    } else {
        alert('Failed to combine GPX files.');
    }
});

window.onload = initMap; 