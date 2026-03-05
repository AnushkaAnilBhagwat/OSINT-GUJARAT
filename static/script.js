// Global variables for map layers
let heatLayer;
let markersLayer;

// Initialize Map
var map = L.map('map').setView([20.5937, 78.9629], 5);
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
    // Trigger AI Analysis based on currently loaded store
    fetchAiAnalysis();
}

// Unified Intelligence Scan Function
function applyFilters() {
    // 1. Capture current values from UI
    const keyword = document.getElementById("keywordSelect").value;
    const location = document.getElementById("locationSelect").value;
    const from = document.getElementById("fromDate").value;
    const to = document.getElementById("toDate").value;
    const sources = Array.from(document.querySelectorAll('.src-check:checked')).map(cb => cb.value).join(',');

    const url = `/api/fetch-all-intel?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}&from=${from}&to=${to}&sources=${sources}`;

    console.log("Executing Scan:", url);

    fetch(url)
        .then(res => res.json())
        .then(data => {
            // Clear existing data
            markersLayer.clearLayers();
            if (heatLayer) map.removeLayer(heatLayer);

            // Handle "No Data" case
            if (!data.articles || data.articles.length === 0) {
                alert(`No intelligence found for ${location} with these filters.`);
                return;
            }

            // Center map
            if (data.center) map.setView(data.center, 6);

            // Add Markers
            data.articles.forEach(article => {
                let markerColor = (article.source === 'Twitter') ? "#1DA1F2" : "#ff0000";

                let marker = L.circleMarker([article.lat, article.lon], {
                    radius: 7,
                    fillColor: markerColor,
                    color: "#ffffff",
                    weight: 2,
                    fillOpacity: 0.9
                });

                marker.bindPopup(`
                    <div style="min-width:200px; color:#333;">
                        <small><b>[${article.source.toUpperCase()}] - ${article.published}</b></small><br>
                        <strong style="font-size:14px;">${article.title}</strong><hr style="margin:5px 0;">
                        <p style="font-size:12px;">${article.summary}</p>
                        <a href="${article.link}" target="_blank" style="color:#00d4ff; font-weight:bold;">Full Report →</a>
                    </div>
                `);
                markersLayer.addLayer(marker);
            });

            // Add Heatmap
            if (data.heat && data.heat.length > 0) {
                heatLayer = L.heatLayer(data.heat, { radius: 25, blur: 15 }).addTo(map);
            }

            // Update News Tab Content
            updateNewsTab(data.articles);
        })
        .catch(err => console.error("Scan Error:", err));
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