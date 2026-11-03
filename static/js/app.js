document.addEventListener("DOMContentLoaded", () => {
  const mapEl = document.getElementById("pick-map");
  if (mapEl && window.L) {
    const map = L.map(mapEl).setView([17.9689, 79.5941], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    let marker;
    function setPoint(lat, lng) {
      if (marker) marker.setLatLng([lat, lng]); else marker = L.marker([lat, lng]).addTo(map);
      document.getElementById("latitude").value = lat.toFixed(6);
      document.getElementById("longitude").value = lng.toFixed(6);
    }
    map.on("click", e => setPoint(e.latlng.lat, e.latlng.lng));
    const locate = document.getElementById("locate-me");
    if (locate) locate.addEventListener("click", () => {
      if (!navigator.geolocation) return alert("Geolocation is not supported by your browser.");
      navigator.geolocation.getCurrentPosition(pos => {
        const { latitude, longitude } = pos.coords;
        map.setView([latitude, longitude], 16); setPoint(latitude, longitude);
      }, () => alert("Could not access your location. Please select a point on the map."));
    });
  }
  const detailMap = document.getElementById("detail-map");
  if (detailMap && window.L) {
    const lat = Number(detailMap.dataset.lat), lng = Number(detailMap.dataset.lng);
    const map = L.map(detailMap).setView([lat,lng], 15);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    L.marker([lat,lng]).addTo(map);
  }
  const cat = document.getElementById("category-data"), stat = document.getElementById("status-data");
  if (cat && stat && window.Chart) {
    const c = JSON.parse(cat.textContent), s = JSON.parse(stat.textContent);
    new Chart(document.getElementById("categoryChart"), {type:"doughnut",data:{labels:c.map(x=>x.category),datasets:[{data:c.map(x=>x.total)}]},options:{responsive:true,plugins:{legend:{position:"bottom"}}}});
    new Chart(document.getElementById("statusChart"), {type:"bar",data:{labels:s.map(x=>x.status),datasets:[{label:"Complaints",data:s.map(x=>x.total),borderRadius:7}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}}}}});
  }
});
