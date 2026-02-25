function showMap() {
    document.getElementById("mapSection").classList.add("active");
    document.getElementById("newsSection").classList.remove("active");
    setTimeout(() => { map.invalidateSize(); }, 300);
}

function showNews() {
    document.getElementById("newsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
}

// Initialize Map
var map = L.map('map').setView([22.5, 71.5], 7);

L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    { attribution: '&copy; OpenStreetMap contributors' }
).addTo(map);

// Load Heatmap Data
fetch('/api/heatmap')
    .then(res => res.json())
    .then(data => {

        data.articles.forEach(article => {

            let marker = L.circleMarker([article.lat, article.lon], {
                radius: 6,
                color: "red",
                fillOpacity: 0.8
            }).addTo(map);

            marker.bindPopup(
                "<b>" + article.title + "</b><br>" + article.summary +
                "<br><br><a href='" + article.link + "' target='_blank'>Read Full Article</a>"
            );
        });

        L.heatLayer(data.heat, {
            radius: 25,
            blur: 20,
            maxZoom: 9,
            minOpacity: 0.4
        }).addTo(map);

    });

// Load Newsletters (Gradient Version)
fetch('/api/newsletters')
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
<h3>${article.title}</h3>
<p>${article.summary}</p>
<a href="${article.link}" target="_blank">Read Full Article →</a>
</div>`;
        });

    });

function showInsights() {
    document.getElementById("insightsSection").classList.add("active");
    document.getElementById("mapSection").classList.remove("active");
    document.getElementById("newsSection").classList.remove("active");

    let div = document.getElementById("aiContent");
    div.innerHTML = `
    <div style="text-align:center;padding:50px;">
        <div class="loader"></div>
        <p>AI is analyzing strategic patterns...</p>
    </div>`;


    fetch('/api/ai-analysis')
        .then(res => res.json())
        .then(data => {
            div.innerHTML = `<p>${data.analysis}</p>`;
        });
}
