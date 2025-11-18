// Frontend script - talk to backend at this base URL
const API = "http://localhost:8000";

const searchInput = document.getElementById("searchInput");
const objectInput = document.getElementById("objectInput");
const actorSelect = document.getElementById("actorSelect");
const searchBtn = document.getElementById("searchBtn");
const resultsGrid = document.getElementById("resultsGrid");
const statusEl = document.getElementById("status");

function setStatus(msg, isError=false) {
  statusEl.textContent = "Status: " + msg;
  statusEl.style.color = isError ? "#ff9b9b" : "#ffd580";
  console.log(msg);
}

async function fetchJSON(url, opts = {}) {
  try {
    const res = await fetch(url, opts);
    if (!res.ok) {
      const txt = await res.text().catch(()=>"");
      throw new Error(`${res.status} ${res.statusText} ${txt}`);
    }
    return await res.json();
  } catch (err) {
    console.error("fetchJSON error for", url, err);
    throw err;
  }
}

// Load actors into dropdown
async function loadActors() {
  setStatus("loading actors...");
  actorSelect.innerHTML = `<option value="">-- Loading actors... --</option>`;
  try {
    const data = await fetchJSON(`${API}/actors`);
    // data could be array of {actor_id, name} or {actor_id, actor_name}
    if (!Array.isArray(data)) throw new Error("actors response not array");

    actorSelect.innerHTML = `<option value="">-- Select actor (optional) --</option>`;
    data.forEach(a => {
      const id = a.actor_id ?? a.id ?? a.actorId ?? a.id; // try common keys
      const name = a.name ?? a.actor_name ?? a.label ?? "";
      const opt = document.createElement("option");
      opt.value = id ?? "";
      opt.textContent = name || `actor_${id}`;
      actorSelect.appendChild(opt);
    });

    setStatus("actors loaded");
  } catch (err) {
    actorSelect.innerHTML = `<option value="">-- Could not load actors --</option>`;
    setStatus("failed to load actors (open console for details)", true);
  }
}

// Build URL for search using inputs
function buildSearchUrl() {
  const q = searchInput.value?.trim();
  const object = objectInput.value?.trim();
  const actor_id = actorSelect.value;

  // If nothing provided, return null
  if (!q && !object && !actor_id) return null;

  const params = new URLSearchParams();
  if (q) params.append("q", q);
  if (object) params.append("object", object);
  if (actor_id) params.append("actor_id", actor_id);

  return `${API}/search?${params.toString()}`;
}

// Render scenes into grid
function renderScenes(results) {
  resultsGrid.innerHTML = "";
  if (!results || results.length === 0) {
    resultsGrid.innerHTML = `<div class="col-span-full text-yellow-200">No scenes found.</div>`;
    return;
  }

  results.forEach(scene => {
    const card = document.createElement("div");
    card.className = "scene-card bg-gray-800 p-3 rounded shadow";

    // thumbnail path may be thumbnail_path or frame url available via /frame/:scene_id
    const img = document.createElement("img");
    // prefer backend frame endpoint to guarantee access
    img.src = `${API}/frame/${scene.scene_id}`;
    img.alt = `scene ${scene.scene_id}`;
    img.onerror = () => { img.src = scene.thumbnail_path ?? ""; };

    const title = document.createElement("div");
    title.className = "mt-2 font-bold";
    title.textContent = scene.movie_name ?? `Scene ${scene.scene_id}`;

    const times = document.createElement("div");
    const s = Number(scene.start_time ?? 0).toFixed(2);
    const e = Number(scene.end_time ?? 0).toFixed(2);
    times.textContent = `⏱ ${s}s — ${e}s`;

    const obj = document.createElement("div");
    obj.className = "text-sm text-gray-400 mt-1";
    const objs = scene.objects ?? scene.tags ?? [];
    obj.textContent = objs.length ? `🧩 ${objs.join(", ")}` : "";

    // Append
    card.appendChild(img);
    card.appendChild(title);
    card.appendChild(times);
    card.appendChild(obj);

    resultsGrid.appendChild(card);
  });
}

// Search handler
async function searchHandler() {
  const url = buildSearchUrl();
  if (!url) {
    setStatus("Type a query, object or select an actor first", true);
    return;
  }

  setStatus("searching...");
  resultsGrid.innerHTML = "";
  try {
    const data = await fetchJSON(url);
    // backend returns { query: ..., results: [...] }
    const results = data.results ?? data;
    renderScenes(results);
    setStatus(`found ${results?.length ?? 0} scenes`);
  } catch (err) {
    setStatus("error loading scenes (open console)", true);
  }
}

// Wire up events
searchBtn.addEventListener("click", searchHandler);
searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") searchHandler(); });
objectInput.addEventListener("keydown", (e) => { if (e.key === "Enter") searchHandler(); });

// On page load
window.addEventListener("load", () => {
  loadActors();
  setStatus("ready");
});
