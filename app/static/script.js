let uploadedFiles = [];
const fileInput = document.getElementById('gpx-files');
const fileListDiv = document.getElementById('file-list');
const downloadBtn = document.getElementById('download-link');
const mapDiv = document.getElementById('map');
let map, gpxLayers = [];

// Warm, modern color palette matching the site
const routeColors = [
    '#e11d48', // rose-600
    '#f59e42', // amber-400
    '#14b8a6', // teal-500
    '#8b5cf6', // violet-500
    '#84cc16', // lime-500
    '#f472b6', // pink-400
    '#facc15', // yellow-400
    '#38bdf8', // sky-400
];

function initMap() {
    if (map) return;
    map = L.map('map').setView([48.8584, 2.2945], 3);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

function clearMap() {
    gpxLayers.forEach(layer => map.removeLayer(layer));
    gpxLayers = [];
}

function plotAllFiles() {
    clearMap();
    if (!uploadedFiles.length) return;
    let bounds = null;
    uploadedFiles.forEach((fileObj, idx) => {
        if (fileObj.gpxPreview) {
            const color = routeColors[idx % routeColors.length];
            const gpxLayer = plotGPX(fileObj.gpxPreview, color, false); // don't fit bounds yet
            if (gpxLayer) {
                if (!bounds) {
                    bounds = gpxLayer.getBounds ? gpxLayer.getBounds() : null;
                } else if (gpxLayer.getBounds) {
                    bounds = bounds.extend(gpxLayer.getBounds());
                }
            }
        }
    });
    // After all layers are added, fit bounds to all
    if (gpxLayers.length && bounds && bounds.isValid && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] });
    }
}

function plotGPX(gpxText, color, fit=true) {
    if (typeof L.GPX !== 'function') {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet-gpx/1.7.0/gpx.min.js';
        script.onload = () => plotGPX(gpxText, color, fit);
        document.body.appendChild(script);
        return;
    }
    let gpxLayer = new L.GPX(gpxText, {
        async: true,
        polyline_options: {
            color: color,
            weight: 5,
            opacity: 0.85,
        },
        marker_options: { startIconUrl: null, endIconUrl: null, shadowUrl: null }
    });
    if (fit) {
        gpxLayer.on('loaded', function(e) {
            map.fitBounds(e.target.getBounds());
        });
    }
    gpxLayer.addTo(map);
    gpxLayers.push(gpxLayer);
    return gpxLayer;
}

function updateFileList() {
    fileListDiv.innerHTML = '';
    if (!uploadedFiles.length) {
        downloadBtn.disabled = true;
        return;
    }
    downloadBtn.disabled = false;
    const ul = document.createElement('ul');
    ul.className = 'list-disc pl-5';
    uploadedFiles.forEach((fileObj, i) => {
        const li = document.createElement('li');
        li.className = 'flex items-center justify-between py-1';
        const color = routeColors[i % routeColors.length];
        li.innerHTML = `<span><span style="display:inline-block;width:1em;height:1em;background:${color};border-radius:50%;margin-right:0.5em;"></span>${i + 1}. ${fileObj.file.name}${fileObj.loading ? ' <span class=\'italic text-xs text-amber-600\'>(loading...)</span>' : ''}</span>`;
        const removeBtn = document.createElement('button');
        removeBtn.textContent = 'Remove';
        removeBtn.className = 'ml-4 text-xs bg-rose-100 text-rose-700 px-2 py-1 rounded hover:bg-rose-200 transition';
        removeBtn.onclick = () => {
            uploadedFiles.splice(i, 1);
            updateFileList();
            plotAllFiles();
        };
        li.appendChild(removeBtn);
        ul.appendChild(li);
    });
    fileListDiv.appendChild(ul);
}

async function handleFiles(files) {
    for (const file of files) {
        if (!uploadedFiles.some(f => f.file.name === file.name && f.file.size === file.size)) {
            const ext = file.name.split('.').pop().toLowerCase();
            const fileObj = { file, gpxPreview: null, loading: false };
            if (ext === 'gpx') {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    fileObj.gpxPreview = evt.target.result;
                    updateFileList();
                    plotAllFiles();
                };
                reader.readAsText(file);
            } else if (ext === 'fit') {
                fileObj.loading = true;
                uploadedFiles.push(fileObj);
                updateFileList();
                // Send to backend for conversion
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const res = await fetch('/convert-fit', {
                        method: 'POST',
                        body: formData
                    });
                    if (res.ok) {
                        fileObj.gpxPreview = await res.text();
                    } else {
                        fileObj.gpxPreview = null;
                        alert('Failed to convert FIT file: ' + file.name);
                    }
                } catch (e) {
                    fileObj.gpxPreview = null;
                    alert('Error converting FIT file: ' + file.name);
                }
                fileObj.loading = false;
                updateFileList();
                plotAllFiles();
                continue;
            }
            uploadedFiles.push(fileObj);
        }
    }
    updateFileList();
    plotAllFiles();
    fileInput.value = '';
}

fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
});

downloadBtn.addEventListener('click', async () => {
    if (!uploadedFiles.length) return;
    const formData = new FormData();
    uploadedFiles.forEach(f => formData.append('files', f.file));
    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Combining...';
    const res = await fetch('/upload', {
        method: 'POST',
        body: formData
    });
    downloadBtn.textContent = 'Download Combined GPX';
    downloadBtn.disabled = false;
    if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'combined.gpx';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => document.body.removeChild(a), 100);
    } else {
        alert('Failed to combine files.');
    }
});

window.onload = () => {
    initMap();
    updateFileList();
}; 