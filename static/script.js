// Global variable to store the report once loaded
let cachedAiReport = null;
let selectedFrom = "";
let selectedTo = "";

let heatLayer;
let markersLayer;

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
    // 1. Switch the active section
    document.getElementById("insightsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
    document.getElementById("newsSection").classList.remove("active");

    let div = document.getElementById("aiContent");

    // Check if we already have the data
    if (cachedAiReport) {
        div.innerHTML = cachedAiReport;
        return; // Exit the function early
    }

    div.innerHTML = `
    <div style="text-align:center;padding:50px;">
        <div class="loader"></div>
        <p>AI is analyzing strategic patterns...</p>
    </div>`;


    fetch('/api/ai-analysis')
        .then(res => res.json())
        .then(data => {
            // Transform raw markdown into structured HTML components
            let reportHtml = data.analysis
                .replace(/### Strategic Themes/g, '<div class="intel-heading">I. STRATEGIC THEMES</div>')
                .replace(/### Operational Impact/g, '<div class="intel-heading">II. OPERATIONAL IMPACT</div>')
                .replace(/### Maritime\/Border Implications/g, '<div class="intel-heading">III. MARITIME IMPLICATIONS</div>')
                .replace(/\d+\. \*\*(.*?)\*\*/g, '<div class="intel-item"><strong>$1</strong>') // Bold titles
                .replace(/\n/g, '<br>');

            // Save the structured HTML into our cache
            cachedAiReport = `
                <div class="intel-brief-card">
                    <div class="intel-banner">OFFICIAL USE ONLY // COMMAND INTELLIGENCE BRIEF</div>
                    <div class="intel-body">
                        <div class="intel-metadata">
                            <span>DESTINATION: SENIOR COMMAND</span>
                            <span>ORIGIN: OSINT AI ENGINE</span>
                        </div>
                        <div class="intel-content">${reportHtml}</div>
                    </div>
                </div>`;

            div.innerHTML = cachedAiReport;
        });
}


// Initialize Map
var map = L.map('map').setView([22.5, 71.5], 7);

markersLayer = L.layerGroup().addTo(map);

L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }
).addTo(map);

// Load Heatmap Data
function loadHeatmap() {

    let url = "/api/heatmap";

    if (selectedFrom && selectedTo) {
        url += `?from=${selectedFrom}&to=${selectedTo}`;
    }

    fetch(url)
        .then(res => res.json())
        .then(data => {

            // Clear old markers
            markersLayer.clearLayers();

            // Remove old heat layer if exists
            if (heatLayer) {
                map.removeLayer(heatLayer);
            }

            data.articles.forEach(article => {

                let marker = L.circleMarker([article.lat, article.lon], {
                    radius: 4,
                    color: "#1a2b3c",
                    fillColor: "#ff0000",
                    fillOpacity: 0.6,
                    weight: 1
                });

                marker.bindPopup(
                    "<div style='color: #333;'>" +
                    "<small><b>DATE: " + article.published + "</b></small><br>" +
                    "<b>" + article.title + "</b><hr>" +
                    article.summary +
                    "<br><br><a href='" + article.link + "' target='_blank'>Full Report</a>" +
                    "</div>"
                );

                markersLayer.addLayer(marker);
            });

            heatLayer = L.heatLayer(data.heat, {
                radius: 15,
                blur: 15,
                maxZoom: 10,
                minOpacity: 0.3,
                gradient: {
                    0.2: 'blue',
                    0.4: 'cyan',
                    0.6: 'lime',
                    0.8: 'yellow',
                    1.0: 'red'
                }
            }).addTo(map);
        });
}

// Load Newsletters (Gradient Version)
function loadNews() {

    let url = "/api/newsletters";

    if (selectedFrom && selectedTo) {
        url += `?from=${selectedFrom}&to=${selectedTo}`;
    }

    fetch(url)
        .then(res => res.json())
        .then(data => {

            let div = document.getElementById("newsContent");
            div.innerHTML = "";

            const gradients = [
                "linear-gradient(145deg,#0f1f2f,#13283c)",
                "linear-gradient(145deg,#112b3c,#0e2233)",
                "linear-gradient(145deg,#1a2636,#122030)",
                "linear-gradient(145deg,#0e2433,#163a52)"
            ];

            data.forEach((article, index) => {
                div.innerHTML += `
                <div class="card" style="background:${gradients[index % gradients.length]}">
                    <div class="card-header">
                        <span class="date-tag">📅 ${article.published}</span>
                    </div>
                    <h3>${article.title}</h3>
                    <p>${article.summary}</p>
                    <div class="card-footer">
                        <a href="${article.link}" target="_blank">Read Full Article →</a>
                    </div>
                </div>`;
            });
        });
}

function applyDateFilter() {

    selectedFrom = document.getElementById("fromDate").value;
    selectedTo = document.getElementById("toDate").value;

    if (!selectedFrom || !selectedTo) {
        alert("Please select both From and To dates.");
        return;
    }

    if (selectedFrom > selectedTo) {
        alert("From date cannot be after To date.");
        return;
    }

    loadHeatmap();
    loadNews();
}
