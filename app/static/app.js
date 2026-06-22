const canvas = document.getElementById("terrain");
const ctx = canvas.getContext("2d");
const HITBOX_PADDING = 18;
const TAP_MOVE_LIMIT = 10;
const state = {
  events: [],
  filtered: [],
  selected: null,
  selectedDetail: null,
  selectedCategory: null,
  hover: null,
  markers: [],
  query: "",
  startupFetchDone: false,
  selectionRequest: 0,
  aiRequest: 0,
  graph: {
    sectionAngle: 0,
    neuronAngle: 0,
    velocity: 0,
    lastAngle: 0,
    dragging: false,
    moved: false,
    suppressClick: false,
    handledPointerUp: false,
    startX: 0,
    startY: 0,
    lastX: 0,
    lastY: 0,
    lastTime: 0,
    frame: null,
  },
};

const colors = {
  critical: "#ff2a6d",
  warning: "#ffc107",
  information: "#00d4aa",
  verified: "#00d4aa",
  high_confidence: "#00b4d8",
  developing: "#ffc107",
  disputed: "#ff8c42",
  unverified: "#8d99ae",
};

const categoryLabels = {
  "thoi-su": "Thời sự",
  "chinh-sach": "Chính sách",
  "phap-luat": "Pháp luật",
  "the-thao": "Thể thao",
  "giao-thong": "Giao thông",
  "thoi-tiet": "Thời tiết",
  "kinh-doanh": "Kinh doanh",
  "suc-khoe": "Sức khỏe",
  "giao-duc": "Giáo dục",
  "cong-nghe": "Công nghệ",
  "van-hoa": "Văn hóa",
  "du-lich": "Du lịch",
};

const categoryColors = {
  "thoi-su": "#00b4d8",
  "chinh-sach": "#8ecae6",
  "phap-luat": "#ffb703",
  "the-thao": "#80ed99",
  "giao-thong": "#fb8500",
  "thoi-tiet": "#ff2a6d",
  "kinh-doanh": "#b8f2e6",
  "suc-khoe": "#57cc99",
  "giao-duc": "#cdb4db",
  "cong-nghe": "#48cae4",
  "van-hoa": "#f4a261",
  "du-lich": "#ffd166",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "No date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function labelForCategory(category) {
  return categoryLabels[category] || category;
}

function colorForCategory(category) {
  return categoryColors[category] || colors.information;
}

function truncateText(value, maxLength) {
  const text = String(value || "");
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trim()}…`;
}

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setDefaultRecentDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 1);
  document.getElementById("start-date").value = toDateInputValue(start);
  document.getElementById("end-date").value = toDateInputValue(end);
}

function resizeCanvas() {
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = Math.max(620, Math.floor(rect.width * devicePixelRatio));
  canvas.height = Math.max(420, Math.floor(rect.height * devicePixelRatio));
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  drawTerrain();
}

if (window.ResizeObserver) {
  new ResizeObserver(resizeCanvas).observe(canvas.parentElement);
}

function eventQueryParams() {
  const params = new URLSearchParams();
  params.set("date_range", document.getElementById("date-range").value);
  params.set("category", document.getElementById("section-filter").value);
  params.set("read_state", document.getElementById("read-filter").value);
  const startDate = document.getElementById("start-date").value;
  const endDate = document.getElementById("end-date").value;
  if (startDate || endDate) {
    params.set("date_range", "all");
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
  }
  if (state.query) params.set("q", state.query);
  return params.toString();
}

async function loadEvents() {
  const response = await fetch(`/api/events?${eventQueryParams()}`);
  state.events = await response.json();
  renderConfidenceFilters();
  renderSourceFilter();
  applyFilters();
}

function renderConfidenceFilters() {
  const target = document.getElementById("confidence-list");
  const states = [...new Set(state.events.map((event) => event.confidence_state))];
  target.innerHTML = states
    .map(
      (item) =>
        `<label><input type="checkbox" value="${escapeHtml(item)}" class="confidence" checked /> ${escapeHtml(
          item.replaceAll("_", " ")
        )}</label>`
    )
    .join("");
  target.querySelectorAll("input").forEach((input) => input.addEventListener("change", applyFilters));
}

function activeValues(selector) {
  return [...document.querySelectorAll(selector)].filter((item) => item.checked).map((item) => item.value);
}

function sourceNamesForEvent(event) {
  return (event.sources || []).map((source) => source.name || source.type || source.article_id).filter(Boolean);
}

function renderSourceFilter() {
  const select = document.getElementById("source-filter");
  const current = select.value;
  const names = [...new Set(state.events.flatMap(sourceNamesForEvent))].sort((left, right) => left.localeCompare(right));
  select.innerHTML =
    `<option value="all">All sources</option>` +
    names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
  if (names.includes(current)) {
    select.value = current;
  }
}

function applyFilters() {
  const severities = activeValues(".severity");
  const confidences = activeValues(".confidence");
  const source = document.getElementById("source-filter").value;
  const excludeSource = document.getElementById("exclude-source").checked;
  state.filtered = state.events.filter((event) => {
    const hasSource = source === "all" || sourceNamesForEvent(event).includes(source);
    const sourceAllowed = source === "all" || (excludeSource ? !hasSource : hasSource);
    return severities.includes(event.severity_level) && confidences.includes(event.confidence_state) && sourceAllowed;
  });
  drawTerrain();
}

function groupedEvents() {
  const groups = new Map();
  for (const event of state.filtered) {
    if (!groups.has(event.category)) groups.set(event.category, []);
    groups.get(event.category).push(event);
  }
  return [...groups.entries()].sort((left, right) => right[1].length - left[1].length);
}

function drawTerrain() {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  drawGraphBackground(w, h);
  state.markers = [];

  if (!state.filtered.length) {
    ctx.fillStyle = "#9fb9b2";
    ctx.font = "15px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("No news matches the current filters.", w / 2, h / 2);
    return;
  }

  const groups = groupedEvents();
  const selectedGroup = groups.find(([category]) => category === state.selectedCategory);
  if (selectedGroup) {
    drawCategoryNewsGraph(selectedGroup[0], selectedGroup[1], w, h);
  } else {
    state.selectedCategory = null;
    drawSectionGraph(groups, w, h);
  }
}

function drawGraphBackground(w, h) {
  ctx.lineWidth = 1;
  for (let y = 36; y < h; y += 42) {
    ctx.beginPath();
    for (let x = 0; x <= w; x += 18) {
      const wave = Math.sin(x / 95 + y / 120) * 5;
      if (x === 0) ctx.moveTo(x, y + wave);
      else ctx.lineTo(x, y + wave);
    }
    ctx.strokeStyle = "rgba(72, 202, 228, 0.1)";
    ctx.stroke();
  }

  for (let index = 0; index < 72; index += 1) {
    const x = (index * 97 + Math.sin(index) * 18) % Math.max(w, 1);
    const y = (index * 53 + Math.cos(index / 2) * 14) % Math.max(h, 1);
    ctx.fillStyle = index % 5 === 0 ? "rgba(236,247,243,0.18)" : "rgba(142,202,230,0.12)";
    ctx.beginPath();
    ctx.arc(x, y, index % 5 === 0 ? 1.8 : 1.1, 0, Math.PI * 2);
    ctx.fill();
  }
}

function projectSphere(cx, cy, radius, angle, depth, scaleBase = 520) {
  const z = Math.sin(angle * 0.83 + depth) * 0.58;
  const scale = scaleBase / (scaleBase - z * 170);
  return {
    x: cx + Math.cos(angle) * radius * scale,
    y: cy + Math.sin(angle * 1.12) * radius * 0.58 * scale,
    z,
    scale,
  };
}

function drawSectionGraph(groups, w, h) {
  const cx = w / 2;
  const cy = h / 2;
  const orbit = Math.min(w, h) * 0.3;
  const baseAngle = state.graph.sectionAngle;
  ctx.textAlign = "center";

  groups
    .map(([category, events], index) => {
      const angle = baseAngle + (index / Math.max(groups.length, 1)) * Math.PI * 2;
      const point = projectSphere(cx, cy, orbit, angle, index * 0.41);
      const radius = Math.max(62, Math.min(90, 56 + events.length * 7)) * point.scale;
      return { category, events, point, radius };
    })
    .sort((left, right) => left.point.z - right.point.z)
    .forEach(({ category, events, point, radius }) => {
      drawNode({
        x: point.x,
        y: point.y,
        radius,
        color: colorForCategory(category),
        title: labelForCategory(category),
        subtitle: `${events.length} news`,
        active: state.hover?.kind === "category" && state.hover.category === category,
        muted: false,
      });
      state.markers.push({ kind: "category", category, x: point.x, y: point.y, radius, hitRadius: radius + 28, z: point.z });
    });

  drawSceneCaption("Choose a section ball", "Then pick a titled news neuron from that section.", w, h);
}

function drawCategoryNewsGraph(category, events, w, h) {
  const cx = w / 2;
  const cy = h / 2;
  const baseAngle = state.graph.neuronAngle;
  const color = colorForCategory(category);
  const categoryRadius = Math.min(118, Math.max(78, 62 + events.length * 3));
  drawNode({
    x: cx,
    y: cy,
    radius: categoryRadius,
    color,
    title: labelForCategory(category),
    subtitle: `${events.length} news neurons`,
    active: true,
    muted: false,
  });
  state.markers.push({ kind: "category", category, x: cx, y: cy, radius: categoryRadius, hitRadius: categoryRadius + 24, z: 2 });

  const orbit = Math.min(w, h) * 0.34;
  const sorted = [...events].sort((left, right) => right.consensus_score - left.consensus_score);
  const neuronMarkers = sorted.map((event, index) => {
    const angle = baseAngle + (index / Math.max(sorted.length, 1)) * Math.PI * 2;
    const point = projectSphere(cx, cy, orbit, angle, index * 0.67, 470);
    const radius = (event.id === state.selected ? 66 : 56) * point.scale + Math.min(event.cluster_size * 2, 10);
    return { event, point, radius };
  });

  neuronMarkers
    .sort((left, right) => left.point.z - right.point.z)
    .forEach(({ event, point, radius }) => {
      drawConnection(cx, cy, point.x, point.y, point.z, color);
      drawNode({
        x: point.x,
        y: point.y,
        radius,
        color: colors[event.severity_level] || color,
        title: truncateText(event.canonical_title, radius > 62 ? 64 : 48),
        subtitle: `${event.consensus_score} CCS · ${event.cluster_size} src`,
        active: event.id === state.selected || state.hover?.eventId === event.id,
        muted: Boolean(event.is_read),
      });
      state.markers.push({ kind: "event", event, x: point.x, y: point.y, radius, hitRadius: radius + 24, z: point.z });
    });

  drawBackButton();
}

function drawConnection(x1, y1, x2, y2, z, color) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.strokeStyle = z > 0 ? `${color}88` : `${color}42`;
  ctx.lineWidth = z > 0 ? 1.6 : 0.8;
  ctx.stroke();
}

function blendWithWhite(hex, amount) {
  const clean = hex.replace("#", "");
  const value = Number.parseInt(clean.length === 3 ? clean.replace(/(.)/g, "$1$1") : clean, 16);
  if (Number.isNaN(value)) return hex;
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  const mix = (channel) => Math.round(channel + (255 - channel) * amount);
  return `rgb(${mix(r)}, ${mix(g)}, ${mix(b)})`;
}

function roundedRect(x, y, width, height, radius) {
  if (ctx.roundRect) {
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, radius);
    return;
  }
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
}

function drawNode({ x, y, radius, color, title, subtitle, active, muted }) {
  const glow = ctx.createRadialGradient(x, y, radius * 0.45, x, y, radius * 1.34);
  glow.addColorStop(0, `${color}38`);
  glow.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = glow;
  ctx.globalAlpha = muted ? 0.2 : 0.42;
  ctx.beginPath();
  ctx.arc(x, y, radius * 1.12, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;

  const body = ctx.createRadialGradient(x - radius * 0.18, y - radius * 0.22, radius * 0.2, x, y, radius);
  body.addColorStop(0, blendWithWhite(color, 0.08));
  body.addColorStop(0.74, color);
  body.addColorStop(1, "#0c1a18");
  ctx.fillStyle = body;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = active ? "#ecf7f3" : "rgba(236,247,243,0.34)";
  ctx.lineWidth = active ? 2.5 : 1.1;
  ctx.stroke();

  const labelWidth = Math.max(34, radius * 1.58);
  const labelHeight = Math.max(26, Math.min(radius * 1.22, subtitle ? radius * 1.02 : radius * 0.88));
  ctx.fillStyle = "rgba(5, 12, 11, 0.76)";
  roundedRect(x - labelWidth / 2, y - labelHeight / 2, labelWidth, labelHeight, 8);
  ctx.fill();
  ctx.strokeStyle = "rgba(236,247,243,0.12)";
  ctx.lineWidth = 1;
  roundedRect(x - labelWidth / 2, y - labelHeight / 2, labelWidth, labelHeight, 8);
  ctx.stroke();

  ctx.fillStyle = "#ecf7f3";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const titleSize = Math.max(9, Math.min(12.5, radius / 5.4));
  ctx.font = `700 ${titleSize}px Inter, sans-serif`;
  const subtitleHeight = subtitle ? 14 : 0;
  const titleLines = Math.max(1, Math.floor((labelHeight - subtitleHeight - 10) / (titleSize + 3)));
  const titleCenterY = subtitle ? y - subtitleHeight / 2 : y;
  wrapCanvasText(title, x, titleCenterY, labelWidth - 12, titleSize + 3, Math.min(titleLines, subtitle ? 3 : 4));
  if (subtitle) {
    ctx.fillStyle = "#cde2dc";
    ctx.font = "11px Inter, sans-serif";
    ctx.fillText(subtitle, x, y + labelHeight / 2 - 12);
  }

  if (active) {
    ctx.beginPath();
    ctx.arc(x, y, radius + 8, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(236,247,243,0.42)";
    ctx.lineWidth = 1.3;
    ctx.stroke();
  }
}

function wrapCanvasText(text, x, y, maxWidth, lineHeight, maxLines) {
  const words = String(text)
    .split(/\s+/)
    .flatMap((word) => splitLongWord(word, maxWidth));
  const lines = [];
  let line = "";
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  const visible = lines.slice(0, Math.max(1, maxLines));
  if (lines.length > maxLines) visible[maxLines - 1] = `${visible[maxLines - 1].replace(/[.…]+$/, "")}…`;
  const startY = y - ((visible.length - 1) * lineHeight) / 2;
  visible.forEach((item, index) => ctx.fillText(item, x, startY + index * lineHeight));
}

function splitLongWord(word, maxWidth) {
  if (ctx.measureText(word).width <= maxWidth) return [word];
  const chunks = [];
  let chunk = "";
  for (const char of word) {
    const test = `${chunk}${char}`;
    if (chunk && ctx.measureText(test).width > maxWidth) {
      chunks.push(chunk);
      chunk = char;
    } else {
      chunk = test;
    }
  }
  if (chunk) chunks.push(chunk);
  return chunks;
}

function drawBackButton() {
  const x = 82;
  const y = 44;
  const radius = 28;
  drawNode({
    x,
    y,
    radius,
    color: "#8ecae6",
    title: "All",
    subtitle: "",
    active: state.hover?.kind === "back",
    muted: false,
  });
  state.markers.push({ kind: "back", x, y, radius, hitRadius: radius + 14, z: 4 });
}

function drawSceneCaption(title, subtitle, w, h) {
  ctx.textAlign = "center";
  ctx.fillStyle = "#ecf7f3";
  ctx.font = "700 15px Inter, sans-serif";
  ctx.fillText(title, w / 2, 34);
  ctx.fillStyle = "#9fb9b2";
  ctx.font = "13px Inter, sans-serif";
  ctx.fillText(subtitle, w / 2, 56);
}

async function selectEvent(eventId) {
  const requestId = state.selectionRequest + 1;
  state.selectionRequest = requestId;
  state.selected = eventId;
  drawTerrain();
  const response = await fetch(`/api/events/${eventId}`);
  const detail = await response.json();
  if (requestId !== state.selectionRequest) return;
  state.selectedDetail = detail;
  document.getElementById("empty-detail").hidden = true;
  document.getElementById("event-detail").hidden = false;
  document.getElementById("detail-category").textContent = `${detail.event.category} · ${detail.event.geographic_scope}`;
  document.getElementById("detail-title").textContent = detail.event.canonical_title;
  document.getElementById("detail-date").textContent = `Updated ${formatDate(detail.event.last_updated_at)} · First seen ${formatDate(
    detail.event.first_seen_at
  )}`;
  document.getElementById("detail-score").textContent = detail.event.consensus_score;
  document.getElementById("detail-state").textContent = `${detail.event.confidence_state.replaceAll("_", " ")} · ${
    detail.event.is_read ? "read" : "haven't read"
  } · ${detail.event.cluster_size} source${detail.event.cluster_size === 1 ? "" : "s"}`;
  document.getElementById("detail-summary").textContent = detail.event.generated_summary;
  document.getElementById("mark-read").textContent = detail.event.is_read ? "Mark unread" : "Mark read";
  renderConsensus(detail);
  renderAction(detail);
  renderArchaeology(detail);
  renderSources(detail);
  renderAiAnalysis(detail);
}

function renderAiAnalysis(detail) {
  const target = document.getElementById("tab-ai");
  const eventId = detail.event.id;
  const requestId = (state.aiRequest += 1);
  if (detail.event.llm_enriched && detail.event.llm_insights) {
    renderAiPayload(target, { enriched: true, data: detail.event.llm_insights });
    return;
  }
  target.innerHTML = `<div class="fact">✨ Generating AI civic analysis…</div>`;
  fetch(`/api/events/${encodeURIComponent(eventId)}/llm-deepdive`)
    .then((response) => response.json())
    .then((payload) => {
      if (requestId !== state.aiRequest) return;
      renderAiPayload(target, payload);
    })
    .catch(() => {
      if (requestId !== state.aiRequest) return;
      target.innerHTML = `<div class="fact">AI enrichment unavailable – showing deterministic analysis.</div>`;
    });
}

function renderAiPayload(target, payload) {
  const data = payload.data || {};
  const sentimentLabels = { stable: "Stable", concerning: "Concerning", urgent: "Urgent" };
  const sentiment = data.sentiment || "stable";
  const sourceNote = payload.enriched
    ? `✨ AI-enhanced analysis${data.model ? ` · ${data.model}` : ""}.`
    : "Local AI is not connected. Showing deterministic civic analysis instead.";
  const setupHint = !payload.enriched
    ? `<div class="llm-help"><strong>${escapeHtml(payload.error || "LLM is unavailable.")}</strong><br>${escapeHtml(
        payload.hint || "Open /api/llm/status to see the current local AI configuration."
      )}<br><code>curl http://127.0.0.1:8000/api/llm/status</code></div>`
    : "";
  const list = (items, cls, empty) =>
    (items || []).length
      ? items.map((item) => `<div class="${cls}">${escapeHtml(item)}</div>`).join("")
      : `<div class="fact">${empty}</div>`;
  target.innerHTML = `
    <p class="ai-note">${escapeHtml(sourceNote)}</p>
    ${setupHint}
    <h2>AI Summary</h2>
    <div class="fact">${escapeHtml(data.ai_summary || "")}</div>
    <h2>Sentiment</h2>
    <div class="fact"><span class="sentiment-badge ${escapeHtml(sentiment)}">${escapeHtml(sentimentLabels[sentiment] || sentiment)}</span></div>
    <h2>Agreed Facts</h2>
    ${list(data.agreed_facts, "fact", "No agreed facts surfaced.")}
    <h2>Disputed Points</h2>
    ${list(data.disputed_points, "dispute", "No unresolved disputes.")}
    <h2>Action Advice</h2>
    ${list(data.action_advice, "action-item", "No actions returned.")}
  `;
}

function renderConsensus(detail) {
  const debate = detail.debate;
  document.getElementById("tab-consensus").innerHTML = `
    <h2>Agreed Facts</h2>
    ${(debate?.agreed_facts || []).map((item) => `<div class="fact">${escapeHtml(item)}</div>`).join("")}
    <h2>Disputed Points</h2>
    ${
      (debate?.disputed_points || []).length
        ? debate.disputed_points
            .map((item) => `<div class="dispute"><strong>${escapeHtml(item.claim)}</strong><br>${escapeHtml(item.note || "")}</div>`)
            .join("")
        : `<div class="fact">No unresolved dispute in the current cluster.</div>`
    }
    <h2>Agent Trace</h2>
    ${Object.entries(debate?.agent_outputs || {})
      .map(([agent, text]) => `<div class="fact"><strong>${escapeHtml(agent.replaceAll("_", " "))}</strong><br>${escapeHtml(text)}</div>`)
      .join("")}
  `;
}

function renderAction(detail) {
  const action = detail.action_protocol || fallbackActionProtocol(detail.event);
  const target = document.getElementById("tab-action");
  target.innerHTML = `
    <h2>Immediate Actions</h2>
    ${action.immediate_actions.map((item) => `<div class="action-item">${escapeHtml(item)}</div>`).join("")}
    <h2>Verification</h2>
    ${action.verification_steps.map((item) => `<div class="action-item">${escapeHtml(item)}</div>`).join("")}
    <h2>Community Sharing</h2>
    ${action.community_sharing.map((item) => `<div class="action-item">${escapeHtml(item)}</div>`).join("")}
  `;
}

function fallbackActionProtocol(event) {
  return {
    immediate_actions: [
      `Read the full update about "${event.canonical_title}" and identify whether it affects your household, route, school, work, or finances.`,
      "Check one official source or responsible news source before changing plans or resharing.",
      "Save the link, source name, and update time so you can compare it with newer information.",
    ],
    verification_steps: [
      "Compare the publication time against another reliable source.",
      "Look for a government, school, hospital, transport, or agency notice related to the same issue.",
      "Avoid repeating casualty numbers, accusations, offers, or instructions that are not clearly verified.",
    ],
    community_sharing: [
      `Citizen update: ${event.canonical_title}. Verify the source and timestamp before forwarding, especially while the story is still developing.`,
    ],
  };
}

function renderArchaeology(detail) {
  const layers = detail.archaeology?.layers || {};
  document.getElementById("tab-archaeology").innerHTML = Object.entries(layers)
    .map(([name, value]) => `<h2>${escapeHtml(name.replaceAll("_", " "))}</h2><div class="fact">${formatLayer(value)}</div>`)
    .join("");
}

function formatLayer(value) {
  if (Array.isArray(value)) return value.map(escapeHtml).join("<br>");
  if (typeof value === "object" && value !== null) {
    return Object.entries(value)
      .map(([key, text]) => `<strong>${escapeHtml(key.replaceAll("_", " "))}:</strong> ${escapeHtml(text)}`)
      .join("<br>");
  }
  return escapeHtml(value);
}

function renderSources(detail) {
  const primary = detail.articles[0];
  document.getElementById("tab-sources").innerHTML = `
    <div class="source-cluster">
      <h2>${escapeHtml(detail.event.canonical_title)}</h2>
      <div class="cluster-line">
        ${detail.articles
          .map((article, index) => `<span title="${escapeHtml(article.title)}">${index === 0 ? "Primary" : `Source ${index + 1}`}</span>`)
          .join("")}
      </div>
      ${
        primary?.url
          ? `<a class="primary-link" href="${escapeHtml(primary.url)}" target="_blank" rel="noreferrer">Open primary source</a>`
          : ""
      }
    </div>
    ${detail.articles
      .map(
        (article) => `<details class="source-item" ${article.id === primary?.id ? "open" : ""}><summary><strong>${escapeHtml(
          article.title
        )}</strong><small>${escapeHtml(article.source_name || article.source_id || "Unknown source")} · ${escapeHtml(article.modality_type)} · ${
        article.published_at ? `published ${escapeHtml(formatDate(article.published_at))} · ` : ""
      }ingested ${escapeHtml(formatDate(article.ingested_at))} · confidence ${Math.round(article.extraction_confidence * 100)}%</small>${
        article.url ? `<a href="${escapeHtml(article.url)}" target="_blank" rel="noreferrer">Open source</a>` : ""
      }</summary><p>${escapeHtml(article.clean_text)}</p></details>`
      )
      .join("")}
  `;
}

function activeAngleKey() {
  return state.selectedCategory ? "neuronAngle" : "sectionAngle";
}

function rotateGraph(delta) {
  state.graph[activeAngleKey()] += delta;
}

function kickPhysics() {
  if (state.graph.frame) return;
  state.graph.frame = requestAnimationFrame(physicsTick);
}

function physicsTick() {
  state.graph.frame = null;
  if (!state.graph.dragging && Math.abs(state.graph.velocity) > 0.00035) {
    rotateGraph(state.graph.velocity);
    state.graph.velocity *= 0.945;
    drawTerrain();
    kickPhysics();
    return;
  }
  state.graph.velocity = 0;
}

function markerAt(x, y) {
  return [...state.markers]
    .map((marker) => {
      const hitRadius = marker.hitRadius || marker.radius + HITBOX_PADDING;
      const distance = Math.hypot(marker.x - x, marker.y - y);
      return { marker, distance, hitRadius };
    })
    .filter(({ distance, hitRadius }) => distance <= hitRadius)
    .sort((left, right) => {
      const depth = (right.marker.z || 0) - (left.marker.z || 0);
      if (Math.abs(depth) > 0.001) return depth;
      return left.distance - right.distance;
    })[0]?.marker;
}

function graphCenter() {
  return {
    x: canvas.clientWidth / 2,
    y: canvas.clientHeight / 2,
  };
}

function pointerAngle(x, y) {
  const center = graphCenter();
  return Math.atan2((y - center.y) / 0.58, x - center.x);
}

function shortestAngleDelta(next, previous) {
  return Math.atan2(Math.sin(next - previous), Math.cos(next - previous));
}

function activateMarker(hit) {
  if (!hit) return false;
  state.graph.velocity = 0;
  if (hit.kind === "back") {
    state.selectedCategory = null;
    state.hover = null;
    drawTerrain();
    return true;
  }
  if (hit.kind === "category") {
    state.selectedCategory = hit.category;
    state.hover = null;
    drawTerrain();
    return true;
  }
  if (hit.kind === "event") {
    selectEvent(hit.event.id);
    return true;
  }
  return false;
}

canvas.addEventListener("pointerdown", (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  state.graph.dragging = true;
  state.graph.moved = false;
  state.graph.suppressClick = false;
  state.graph.handledPointerUp = false;
  state.graph.velocity = 0;
  state.graph.startX = x;
  state.graph.startY = y;
  state.graph.lastX = x;
  state.graph.lastY = y;
  state.graph.lastAngle = pointerAngle(x, y);
  state.graph.lastTime = performance.now();
  canvas.setPointerCapture(event.pointerId);
  canvas.style.cursor = "grabbing";
});

canvas.addEventListener("pointermove", (event) => {
  if (!state.graph.dragging) return;
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const now = performance.now();
  const dx = x - state.graph.lastX;
  const dy = y - state.graph.lastY;
  const totalDistance = Math.hypot(x - state.graph.startX, y - state.graph.startY);
  if (totalDistance > TAP_MOVE_LIMIT) state.graph.moved = true;
  const nextAngle = pointerAngle(x, y);
  const angularDelta = shortestAngleDelta(nextAngle, state.graph.lastAngle);
  const dt = Math.max(12, now - state.graph.lastTime);
  const linearAssist = dx * 0.0018 + dy * 0.0008;
  const delta = Math.max(-0.22, Math.min(0.22, angularDelta + linearAssist));
  rotateGraph(delta);
  state.graph.velocity = Math.max(-0.18, Math.min(0.18, delta * (16 / dt)));
  state.graph.lastX = x;
  state.graph.lastY = y;
  state.graph.lastAngle = nextAngle;
  state.graph.lastTime = now;
  drawTerrain();
});

function endGraphDrag(event) {
  if (!state.graph.dragging) return;
  const rect = canvas.getBoundingClientRect();
  const x = event ? event.clientX - rect.left : state.graph.lastX;
  const y = event ? event.clientY - rect.top : state.graph.lastY;
  const wasTap = Math.hypot(x - state.graph.startX, y - state.graph.startY) <= TAP_MOVE_LIMIT;
  state.graph.dragging = false;
  state.graph.suppressClick = state.graph.moved || wasTap;
  if (event?.pointerId !== undefined && canvas.hasPointerCapture(event.pointerId)) {
    canvas.releasePointerCapture(event.pointerId);
  }
  canvas.style.cursor = state.hover ? "pointer" : "grab";
  if (wasTap) {
    state.graph.handledPointerUp = activateMarker(markerAt(x, y));
  } else if (state.graph.moved && Math.abs(state.graph.velocity) > 0.001) {
    kickPhysics();
  } else {
    state.graph.velocity = 0;
  }
  setTimeout(() => {
    state.graph.suppressClick = false;
    state.graph.handledPointerUp = false;
  }, 90);
}

canvas.addEventListener("pointerup", endGraphDrag);
canvas.addEventListener("pointercancel", endGraphDrag);

canvas.addEventListener("mousemove", (event) => {
  if (state.graph.dragging) return;
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const hit = markerAt(x, y);
  const nextHover = hit?.kind === "event" ? { kind: "event", eventId: hit.event.id } : hit ? { kind: hit.kind, category: hit.category } : null;
  const changed = JSON.stringify(nextHover) !== JSON.stringify(state.hover);
  state.hover = nextHover;
  canvas.style.cursor = hit ? "pointer" : "grab";
  if (changed) drawTerrain();
});

canvas.addEventListener("mouseleave", () => {
  state.hover = null;
  canvas.style.cursor = "grab";
  drawTerrain();
});

canvas.addEventListener("click", (event) => {
  if (state.graph.suppressClick || state.graph.handledPointerUp) return;
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  activateMarker(markerAt(x, y));
});

document.querySelectorAll(".severity").forEach((input) => input.addEventListener("change", applyFilters));
["date-range", "start-date", "end-date", "read-filter"].forEach((id) => {
  document.getElementById(id).addEventListener("change", loadEvents);
});
document.getElementById("section-filter").addEventListener("change", (event) => {
  state.selectedCategory = event.target.value === "all" ? null : event.target.value;
  loadEvents();
});
["source-filter", "exclude-source"].forEach((id) => {
  document.getElementById(id).addEventListener("change", applyFilters);
});
document.getElementById("search").addEventListener("input", (event) => {
  state.query = event.target.value;
  loadEvents();
});
document.getElementById("refresh").addEventListener("click", loadEvents);
document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((item) => (item.hidden = true));
    button.classList.add("active");
    document.getElementById(`tab-${button.dataset.tab}`).hidden = false;
  });
});

document.getElementById("mark-read").addEventListener("click", async () => {
  if (!state.selectedDetail) return;
  const next = !state.selectedDetail.event.is_read;
  const response = await fetch(`/api/events/${state.selectedDetail.event.id}/read?is_read=${next}`, { method: "PATCH" });
  if (response.ok) {
    await loadEvents();
    await selectEvent(state.selectedDetail.event.id);
  }
});

document.getElementById("delete-event").addEventListener("click", async () => {
  if (!state.selectedDetail) return;
  const response = await fetch(`/api/events/${state.selectedDetail.event.id}`, { method: "DELETE" });
  if (response.ok) {
    state.selected = null;
    state.selectedDetail = null;
    document.getElementById("empty-detail").hidden = false;
    document.getElementById("event-detail").hidden = true;
    await loadEvents();
  }
});

document.getElementById("ingest-submit").addEventListener("click", async () => {
  const status = document.getElementById("ingest-status");
  const title = document.getElementById("ingest-title").value.trim() || "Quick ingest";
  const url = document.getElementById("ingest-url").value.trim();
  const clean_text = document.getElementById("ingest-text").value.trim();
  if (!url && clean_text.length < 20) {
    status.textContent = "Provide a URL or at least 20 characters of text.";
    return;
  }
  status.textContent = url && clean_text.length < 20 ? "Fetching URL..." : "Submitting...";
  const body = {
    title,
    category: document.getElementById("ingest-category").value,
    source_name: "Live demo submission",
    source_type: url ? "web" : "direct_url",
    modality_type: url ? "direct_url" : "web",
    geographic_scope: "Việt Nam",
    latitude: null,
    longitude: null,
  };
  if (url) {
    try {
      body.source_name = new URL(url).hostname;
    } catch {
      status.textContent = "Enter a valid URL including https://";
      return;
    }
    body.url = url;
  }
  if (clean_text) body.clean_text = clean_text;

  const response = await fetch("/api/ingest/multi-modal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    status.textContent = error.detail || "Ingest failed.";
    return;
  }
  const result = await response.json();
  status.textContent = `Created ${result.event.canonical_title}`;
  document.getElementById("ingest-title").value = "";
  document.getElementById("ingest-url").value = "";
  document.getElementById("ingest-text").value = "";
  await loadEvents();
  selectEvent(result.event.id);
});

async function loadNewsSources() {
  const response = await fetch("/api/news/sources");
  if (!response.ok) return;
  const payload = await response.json();
  const select = document.getElementById("live-source");
  select.innerHTML =
    `<option value="all">All configured sources</option>` +
    payload.sources
      .map((source) => `<option value="${escapeHtml(source.key)}">${escapeHtml(source.name)}</option>`)
      .join("");
}

async function fetchLiveSources(source = document.getElementById("live-source").value) {
  const status = document.getElementById("live-status");
  const params = new URLSearchParams();
  params.set("source", source);
  params.set("limit", document.getElementById("live-limit").value || "8");
  params.set("fetch_full_text", document.getElementById("live-full-text").checked ? "true" : "false");
  const startDate = document.getElementById("start-date").value;
  const endDate = document.getElementById("end-date").value;
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  status.textContent = source === "all" ? "Fetching all live sources..." : "Fetching live source...";
  const response = await fetch(`/api/ingest/live-news?${params.toString()}`, { method: "POST" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    status.textContent = payload.detail || "Live fetch failed.";
    return payload;
  }
  const errors = payload.errors?.length ? `, ${payload.errors.length} source errors` : "";
  status.textContent = `Ingested ${payload.ingested_count || 0} article(s)${errors}.`;
  await loadEvents();
  return payload;
}

document.getElementById("live-fetch").addEventListener("click", async () => {
  await fetchLiveSources();
});

async function fetchStartupNews() {
  if (state.startupFetchDone) return;
  state.startupFetchDone = true;
  await fetchLiveSources("all");
}

function connectTerrainStream() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/terrain/stream`);
  socket.addEventListener("message", () => loadEvents());
  socket.addEventListener("close", () => setTimeout(connectTerrainStream, 5000));
}

window.addEventListener("resize", resizeCanvas);
setInterval(loadEvents, 30000);
setDefaultRecentDates();
resizeCanvas();
loadNewsSources().then(fetchStartupNews);
connectTerrainStream();
loadEvents();
