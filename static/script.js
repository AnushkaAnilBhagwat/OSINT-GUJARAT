// Global variables to store current filter states
let cachedAiReports = {};
let selectedFrom = "";
let selectedTo = "";
let selectedKeyword = "";
let selectedLocation = "";
let selectedSources = [];

let heatLayer;
let markersLayer;

// Navigation logic (stays mostly the same)
function showMap() {
    document.getElementById("mapSection").classList.add("active");
    document.getElementById("newsSection").classList.remove("active");
    document.getElementById("insightsSection").classList.remove("active");
    setTimeout(() => { map.invalidateSize(); }, 300);
}

function showNews() {
    document.getElementById("newsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
    document.getElementById("insightsSection").classList.remove("active");
}

function showInsights() {
    document.getElementById("insightsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
    document.getElementById("newsSection").classList.remove("active");

    let div = document.getElementById("aiContent");
    let cacheKey = `${selectedKeyword}_${selectedLocation}_${selectedFrom}_${selectedTo}_${selectedSources.join(',')}`;

    if (cachedAiReports[cacheKey]) {
        div.innerHTML = cachedAiReports[cacheKey];
        return;
    }

    div.innerHTML = `
    <div style="text-align:center;padding:50px;">
        <div class="loader"></div>
        <p>AI Agent is performing strategic synthesis...</p>
    </div>`;

    // Agent Prompt Construction based on UI filters
    const agentPrompt = `Analyze ${selectedKeyword} threats in ${selectedLocation} 
                         from ${selectedFrom} to ${selectedTo} using ${selectedSources.join(' and ')} feeds.`;

    // Calling the AI Agent API
    fetch("/api/ai-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prompt: agentPrompt,
            keyword: selectedKeyword,
            location: selectedLocation,
            from: selectedFrom,
            to: selectedTo,
            sources: selectedSources
        })
    })
        .then(res => res.json())
        .then(data => {
            let reportHtml = data.analysis
                .replace(/### Strategic Themes/g, '<div class="intel-heading">I. STRATEGIC THEMES</div>')
                .replace(/### Operational Impact/g, '<div class="intel-heading">II. OPERATIONAL IMPACT</div>')
                .replace(/### Maritime\/Border Implications/g, '<div class="intel-heading">III. MARITIME IMPLICATIONS</div>')
                .replace(/\d+\. \*\*(.*?)\*\*/g, '<div class="intel-item"><strong>$1</strong>')
                .replace(/\n/g, '<br>');

            cachedAiReports[cacheKey] = `
            <div class="intel-brief-card">
                <div class="intel-banner">OFFICIAL USE ONLY // AI AGENT INTEL BRIEF</div>
                <div class="intel-body">
                    <div class="intel-metadata">
                        <span>SECTOR: ${selectedLocation.toUpperCase()}</span>
                        <span>SOURCES: ${selectedSources.join(', ').toUpperCase()}</span>
                    </div>
                    <div class="intel-content">${reportHtml}</div>
                </div>
            </div>`;
            div.innerHTML = cachedAiReports[cacheKey];
        });
}

// Updated Map Logic to handle dynamic locations
var map = L.map('map').setView([20.5937, 78.9629], 5); // Default to center of India
markersLayer = L.layerGroup().addTo(map);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 20
}).addTo(map);

function loadHeatmap() {
    // Build the query URL
    let url = `/api/heatmap?keyword=${encodeURIComponent(selectedKeyword)}&location=${encodeURIComponent(selectedLocation)}&from=${selectedFrom}&to=${selectedTo}&sources=${selectedSources.join(',')}`;

    console.log("Fetching Intel from:", url); // Debugging line

    fetch(url)
        .then(res => res.json())
        .then(data => {
            console.log("Data Received:", data); // Check if data.articles is empty in F12 console

            markersLayer.clearLayers();
            if (heatLayer) map.removeLayer(heatLayer);

            if (data.center) {
                map.setView(data.center, 6);
            }

            // Ensure data.articles exists before looping
            if (data.articles && data.articles.length > 0) {
                data.articles.forEach(article => {
                    // DEFENSIVE FIX: Check if article.source exists, otherwise default to 'News'
                    let source = article.source || 'News';
                    let markerColor = (source === 'Twitter') ? "#1DA1F2" : "#ff0000";

                    let marker = L.circleMarker([article.lat, article.lon], {
                        radius: 6,
                        color: "#ffffff", // White border for better visibility on light map
                        fillColor: markerColor,
                        fillOpacity: 0.9,
                        weight: 2
                    });

                    marker.bindPopup(`
                        <div style="color: #333; font-family: sans-serif;">
                            <strong style="color:${markerColor}">[${source.toUpperCase()}]</strong><br>
                            <b>${article.title}</b><hr>
                            ${article.summary}<br>
                            <small>Location: ${article.lat.toFixed(2)}, ${article.lon.toFixed(2)}</small>
                        </div>
                    `);
                    markersLayer.addLayer(marker);
                });
            } else {
                console.warn("No articles returned for these filters.");
            }

            // Re-add the heatmap layer
            if (data.heat && data.heat.length > 0) {
                heatLayer = L.heatLayer(data.heat, {
                    radius: 25,
                    blur: 15,
                    maxOpacity: 0.8
                }).addTo(map);
            }
        })
        .catch(err => console.error("Map Fetch Error:", err));
}

// Main Filter Execution
// Triggered by the "Execute Intelligence Scan" button
function applyFilters() {
    const keyword = document.getElementById("keywordSelect").value;
    const location = document.getElementById("locationSelect").value;
    const from = document.getElementById("fromDate").value;
    const to = document.getElementById("toDate").value;
    const sources = Array.from(document.querySelectorAll('.src-check:checked')).map(cb => cb.value).join(',');

    const url = `/api/fetch-all-intel?keyword=${keyword}&location=${location}&from=${from}&to=${to}&sources=${sources}`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            markersLayer.clearLayers();
            if (heatLayer) map.removeLayer(heatLayer);
            if (data.center) map.setView(data.center, 6);

            data.articles.forEach(article => {
                let marker = L.circleMarker([article.lat, article.lon], {
                    radius: 7,
                    fillColor: "#ff0000",
                    color: "#ffffff",
                    weight: 2,
                    fillOpacity: 0.9
                }).addTo(markersLayer);

                // This matches the dictionary keys in your Python fetch_news function
                marker.bindPopup(`
                    <div style="min-width:200px">
                        <small><b>${article.published}</b></small><br>
                        <b>${article.title}</b><hr>
                        <p style="font-size:12px">${article.summary}</p>
                        <a href="${article.link}" target="_blank">Full Report →</a>
                    </div>
                `);
            });

            heatLayer = L.heatLayer(data.heat, { radius: 25, blur: 15 }).addTo(map);
        });
}

function updateMapDisplay(data) {
    markersLayer.clearLayers();
    if (heatLayer) map.removeLayer(heatLayer);

    // Fly to the selected state
    map.setView(data.center, 6);

    data.articles.forEach(article => {
        let color = (article.source === 'Twitter') ? "#1DA1F2" : "#ff4d4d";
        L.circleMarker([article.lat, article.lon], {
            radius: 6,
            fillColor: color,
            color: "#fff",
            weight: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>[${article.source}]</b><br>${article.title}`).addTo(markersLayer);
    });

    heatLayer = L.heatLayer(data.heat, { radius: 25, blur: 15 }).addTo(map);
}