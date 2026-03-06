// Global variables for map layers
let heatLayer;
let markersLayer;

// Initialize Map
var map = L.map('map', {
    zoomControl: false // Disable the default top-left control
}).setView([20.5937, 78.9629], 5);

// Add the zoom control to the bottom right instead
L.control.zoom({
    position: 'bottomright'
}).addTo(map);
markersLayer = L.layerGroup().addTo(map);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 20
}).addTo(map);

// Navigation Logic
function showMap() {
    document.getElementById("mapSection").classList.add("active");
    document.getElementById("newsSection").classList.remove("active");
    document.getElementById("insightsSection").classList.remove("active");
    setTimeout(() => { map.invalidateSize(); }, 300);

    updateNavButtons("Map");
}

function showNews() {
    document.getElementById("newsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
    document.getElementById("insightsSection").classList.remove("active");

    updateNavButtons("List");
}

function showInsights() {
    document.getElementById("insightsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
    document.getElementById("newsSection").classList.remove("active");
    // Trigger AI Analysis based on currently loaded store
    fetchAiAnalysis();

    updateNavButtons("Insights");
}

// Unified Intelligence Scan Function
// Add a global layer group for maritime markers if not already present
let maritimeMarkersLayer = L.layerGroup().addTo(map);

function applyFilters() {
    // 1. Clear all existing data layers
    markersLayer.clearLayers();
    maritimeMarkersLayer.clearLayers();
    if (heatLayer) map.removeLayer(heatLayer);

    // 2. Capture UI values
    const keyword = document.getElementById("keywordSelect").value;
    const location = document.getElementById("locationSelect").value;
    const from = document.getElementById("fromDate").value;
    const to = document.getElementById("toDate").value;
    const sources = Array.from(document.querySelectorAll('.src-check:checked')).map(cb => cb.value).join(',');
    const country = document.getElementById("countrySelect").value;
    const vesselType = document.getElementById("typeSelect").value;

    // --- Keyword and Location display ---
    const infoBar = document.getElementById("scanInfoBar");
    const displaySector = document.getElementById("displaySector");
    const displayKeyword = document.getElementById("displayKeyword");

    // Show the bar and update text
    infoBar.style.display = "flex";
    displaySector.innerText = location;
    displayKeyword.innerText = keyword || "General Surveillance";

    // 3. Fetch News & Twitter Intelligence
    const intelUrl = `/api/fetch-all-intel?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}&from=${from}&to=${to}&sources=${sources}`;

    fetch(intelUrl)
        .then(res => res.json())
        .then(data => {
            if (data.center) map.setView(data.center, 6);

            data.articles.forEach(article => {
                let markerColor = (article.source === 'Twitter') ? "#1DA1F2" : "#8800ff";

                let marker = L.circleMarker([article.lat, article.lon], {
                    radius: 7,
                    fillColor: markerColor,
                    color: "#ffffff",
                    weight: 2,
                    fillOpacity: 0.9
                });

                // RESTORED: Professional News Popup Format
                marker.bindPopup(`
                    <div style="min-width:250px; color:#333; font-family: 'Segoe UI', sans-serif;">
                        <small style="color:#666;"><b>[${article.source.toUpperCase()}] - ${article.published}</b></small><br>
                        <strong style="font-size:15px; display:block; margin-top:5px;">${article.title}</strong>
                        <hr style="margin:8px 0; border:0; border-top:1px solid #eee;">
                        <p style="font-size:13px; line-height:1.4; color:#444;">${article.summary}</p>
                        <a href="${article.link}" target="_blank" style="color:#007bff; font-weight:bold; text-decoration:none; font-size:12px;">Full Report →</a>
                    </div>
                `);
                markersLayer.addLayer(marker);
            });

            if (data.heat && data.heat.length > 0) {
                heatLayer = L.heatLayer(data.heat, { radius: 25, blur: 15 }).addTo(map);
            }
            updateNewsTab(data.articles);
        });

    // 4. Fetch Maritime Data (Separate functionality as requested)
    fetch(`/api/maritime-data?country=${country}&type=${vesselType}`)
        .then(res => res.json())
        .then(data => {
            // Add Ports
            data.ports.forEach(port => {
                L.marker([port.lat, port.lon])
                    .bindPopup(`<b>PORT:</b> ${port.name}<br>${port.country}`)
                    .addTo(maritimeMarkersLayer);
            });

            // Add Vessels
            data.vessels.forEach(vessel => {
                let vColor = vessel.type === "Naval" ? "red" : vessel.type === "Cargo" ? "blue" : "green";
                L.circleMarker([vessel.lat, vessel.lon], {
                    radius: 8,
                    fillColor: vColor,
                    color: "#fff",
                    weight: 1,
                    fillOpacity: 0.9
                }).bindPopup(`
                    <div style="color:#333;">
                        <strong>${vessel.name}</strong><br>
                        Type: ${vessel.type}<br>
                        Flag: ${vessel.country}
                    </div>
                `).addTo(maritimeMarkersLayer);
            });
        });
}
function updateNewsTab(articles) {
    const container = document.getElementById("newsContent");
    container.innerHTML = articles.map(art => `
        <div class="news-card">
            <h4>${art.title}</h4>
            <p>${art.summary}</p>
            <small>Source: ${art.source} | ${art.published}</small>
        </div>
    `).join('');
}

function fetchAiAnalysis() {
    const div = document.getElementById("aiContent");
    div.innerHTML = '<div class="loader"></div><p>AI Agent is performing strategic synthesis...</p>';

    fetch("/api/ai-analysis")
        .then(res => res.json())
        .then(data => {
            let reportHtml = data.analysis
                .replace(/### (.*?)\n/g, '<div class="intel-heading">$1</div>')
                .replace(/\n/g, '<br>');
            div.innerHTML = `<div class="intel-content">${reportHtml}</div>`;
        });
}

function updateNavButtons(activeId) {
    // Remove active class from all buttons
    document.querySelectorAll('.nav button').forEach(btn => {
        btn.classList.remove('active-nav');
    });

    // Add active class to the button that matches the text
    const navButtons = document.querySelectorAll('.nav button');
    navButtons.forEach(btn => {
        if (btn.innerText.toLowerCase().includes(activeId.toLowerCase())) {
            btn.classList.add('active-nav');
        }
    });
}