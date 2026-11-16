document.addEventListener("DOMContentLoaded", () => {
  const tiles = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
  const attribution = '&copy; OpenStreetMap contributors';
  const defaultCenter = [17.9689, 79.5941];
  const addTiles = map => L.tileLayer(tiles, { attribution, maxZoom: 19 }).addTo(map);
  const escapeHtml = value => String(value ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));

  // Complaint submission/edit map: search, click-to-pin, geolocation and reverse lookup.
  const mapEl = document.getElementById("pick-map");
  if (mapEl && window.L) {
    const startLat = parseFloat(mapEl.dataset.lat), startLng = parseFloat(mapEl.dataset.lng);
    const hasStart = Number.isFinite(startLat) && Number.isFinite(startLng);
    const map = L.map(mapEl).setView(hasStart ? [startLat, startLng] : defaultCenter, hasStart ? 16 : 13);
    addTiles(map);
    let marker;
    const latInput = document.getElementById("latitude"), lngInput = document.getElementById("longitude");
    const locationInput = document.getElementById("location_text"), coordLabel = document.getElementById("map-coordinates");
    const searchInput = document.getElementById("location-search"), results = document.getElementById("location-results");
    let searchTimer;

    function setPoint(lat, lng, label, shouldReverse = false) {
      const point = [lat, lng];
      if (marker) marker.setLatLng(point); else { marker = L.marker(point, { draggable: true }).addTo(map); marker.on('dragend', () => { const p = marker.getLatLng(); setPoint(p.lat, p.lng, 'Selected map location', true); }); }
      marker.bindPopup(`<strong>${escapeHtml(label || 'Selected location')}</strong><br>${lat.toFixed(5)}, ${lng.toFixed(5)}`).openPopup();
      latInput.value = lat.toFixed(6); lngInput.value = lng.toFixed(6);
      coordLabel.textContent = `Selected coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
      if (label) locationInput.value = label;
      if (shouldReverse) reverseLookup(lat, lng);
    }
    async function reverseLookup(lat, lng) {
      try {
        const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
        if (r.ok) { const d = await r.json(); if (d.display_name) { locationInput.value = d.display_name; if (marker) marker.setPopupContent(`<strong>${escapeHtml(d.display_name)}</strong><br>${lat.toFixed(5)}, ${lng.toFixed(5)}`); } }
      } catch (_) { /* Coordinates remain usable when reverse lookup is unavailable. */ }
    }
    map.on('click', e => setPoint(e.latlng.lat, e.latlng.lng, 'Selected map location', true));
    if (hasStart) setPoint(startLat, startLng, locationInput.value || 'Saved complaint location');
    const locate = document.getElementById("locate-me");
    if (locate) locate.addEventListener("click", () => {
      if (!navigator.geolocation) return alert("Geolocation is not supported by your browser.");
      locate.disabled = true; locate.textContent = 'Finding…';
      navigator.geolocation.getCurrentPosition(pos => {
        const { latitude, longitude } = pos.coords; map.setView([latitude, longitude], 17);
        setPoint(latitude, longitude, 'Current location', true); locate.disabled = false; locate.textContent = 'Use my location';
      }, () => { alert("Could not access your location. Allow location permission or search for a place."); locate.disabled = false; locate.textContent = 'Use my location'; }, { enableHighAccuracy: true, timeout: 12000 });
    });
    if (searchInput) searchInput.addEventListener('input', () => {
      clearTimeout(searchTimer); const q = searchInput.value.trim();
      if (q.length < 3) { results.innerHTML = ''; return; }
      results.innerHTML = '<div class="location-result muted">Searching places…</div>';
      searchTimer = setTimeout(async () => {
        try {
          const r = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=6&q=${encodeURIComponent(q)}`);
          if (!r.ok) throw new Error('Search unavailable');
          const places = await r.json(); results.innerHTML = '';
          if (!places.length) { results.innerHTML = '<div class="location-result muted">No places found. Try a nearby landmark or full address.</div>'; return; }
          places.forEach(place => {
            const button = document.createElement('button'); button.type = 'button'; button.className = 'location-result'; button.textContent = place.display_name;
            button.addEventListener('click', () => { const lat = Number(place.lat), lon = Number(place.lon); map.setView([lat, lon], 17); setPoint(lat, lon, place.display_name); results.innerHTML = ''; searchInput.value = place.display_name; });
            results.appendChild(button);
          });
        } catch (_) { results.innerHTML = '<div class="location-result muted">Place search failed. Check your internet connection or pin the map manually.</div>'; }
      }, 1000);
    });
    setTimeout(() => map.invalidateSize(), 150);
  }

  // Individual complaint detail map with a descriptive popup.
  const detailMap = document.getElementById("detail-map");
  if (detailMap && window.L) {
    const lat = Number(detailMap.dataset.lat), lng = Number(detailMap.dataset.lng);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      const map = L.map(detailMap).setView([lat, lng], 16); addTiles(map);
      L.marker([lat, lng]).addTo(map).bindPopup(`<strong>${detailMap.dataset.title || 'Complaint location'}</strong><br>${detailMap.dataset.category || ''}<br>${detailMap.dataset.location || ''}`).openPopup();
      setTimeout(() => map.invalidateSize(), 150);
    }
  }

  // Map of all geolocated public complaints; marker popups link to full report pages.
  const publicMap = document.getElementById('public-map'), mapData = document.getElementById('public-map-data');
  if (publicMap && mapData && window.L) {
    const items = JSON.parse(mapData.textContent || '[]');
    const map = L.map(publicMap).setView(defaultCenter, 12); addTiles(map);
    const bounds = [];
    items.forEach(item => {
      const marker = L.marker([item.lat, item.lng]).addTo(map);
      marker.bindPopup(`<strong>${escapeHtml(item.title)}</strong><br>${escapeHtml(item.category)}<br>${escapeHtml(item.location)}<br><a href="${escapeHtml(item.url)}">View complaint #${item.id}</a>`);
      bounds.push([item.lat, item.lng]);
    });
    if (bounds.length) map.fitBounds(bounds, { padding: [25, 25], maxZoom: 15 });
    setTimeout(() => map.invalidateSize(), 150);
  }

  const cat = document.getElementById("category-data"), stat = document.getElementById("status-data");
  if (cat && stat && window.Chart) {
    const c = JSON.parse(cat.textContent), s = JSON.parse(stat.textContent);
    new Chart(document.getElementById("categoryChart"), {type:"doughnut",data:{labels:c.map(x=>x.category),datasets:[{data:c.map(x=>x.total)}]},options:{responsive:true,plugins:{legend:{position:"bottom"}}}});
    new Chart(document.getElementById("statusChart"), {type:"bar",data:{labels:s.map(x=>x.status),datasets:[{label:"Complaints",data:s.map(x=>x.total),borderRadius:7}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}}}}});
  }
});
