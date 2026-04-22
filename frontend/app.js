// piCalendar frontend. Vanilla ES2020, no bundler.
// Single-page, long-lived; Chromium kiosk, Pi 3 target.

(() => {
  "use strict";

  const STATE = {
    config: null,
    weather: null,
    events: [],
    weekStart: null,
    theme: "day",
    perf: "hi",
  };

  const MS = 60 * 1000;
  const HOUR_START = 6;
  const HOUR_END = 23; // exclusive — grid covers [6, 23), i.e. 6 AM through 10:59 PM
  const HOURS_COUNT = HOUR_END - HOUR_START; // 17
  const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const WEEKDAYS_FULL = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
  ];
  const MONTHS_FULL = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  const WMO_TO_ICON = (code) => {
    if (code === 0 || code === 1) return "w-sun";
    if (code === 2) return "w-partly";
    if (code === 3) return "w-cloud";
    if (code === 45 || code === 48) return "w-fog";
    if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) return "w-rain";
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "w-snow";
    if (code >= 95) return "w-thunder";
    return "w-cloud";
  };

  // ---------- Time helpers -----------------------------------------------
  const startOfSunday = (d = new Date()) => {
    const day = new Date(d);
    day.setHours(0, 0, 0, 0);
    day.setDate(day.getDate() - day.getDay()); // Sunday = 0
    return day;
  };

  const sameDay = (a, b) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  const fmtTime = (d) => {
    let h = d.getHours();
    const m = d.getMinutes();
    const ampm = h >= 12 ? "p" : "a";
    h = h % 12 || 12;
    return m === 0 ? `${h}${ampm}` : `${h}:${String(m).padStart(2, "0")}${ampm}`;
  };

  const fmtTimeRange = (s, e) => `${fmtTime(s)} – ${fmtTime(e)}`;

  const parseISO = (s) => {
    // All-day events come as "YYYY-MM-DD" (date-only). Treat as local midnight.
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
      const [y, m, d] = s.split("-").map(Number);
      return new Date(y, m - 1, d, 0, 0, 0, 0);
    }
    return new Date(s);
  };

  // ---------- Config / fetch ---------------------------------------------
  async function fetchConfig() {
    const r = await fetch("/api/config");
    STATE.config = await r.json();
  }

  async function fetchEvents() {
    const start = STATE.weekStart.toISOString();
    const end = new Date(STATE.weekStart.getTime() + 7 * 86400 * 1000).toISOString();
    const r = await fetch(`/api/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    const json = await r.json();
    STATE.events = (json.events || []).map((e) => ({
      ...e,
      _start: parseISO(e.start),
      _end: parseISO(e.end),
    }));
    renderAll();
  }

  async function fetchWeather() {
    const r = await fetch("/api/weather");
    STATE.weather = await r.json();
    renderHeader();
    renderForecast();
    evaluateTheme();
  }

  // ---------- Theme -------------------------------------------------------
  function evaluateTheme() {
    const override = STATE.config && STATE.config.theme_override;
    if (override === "day" || override === "night") {
      applyTheme(override);
      return;
    }
    if (!STATE.weather || !STATE.weather.sunrise_today || !STATE.weather.sunset_today) {
      applyTheme("day");
      return;
    }
    const now = new Date();
    const sr = parseISO(STATE.weather.sunrise_today);
    const ss = parseISO(STATE.weather.sunset_today);
    const isDay = now >= sr && now < ss;
    applyTheme(isDay ? "day" : "night");
  }

  function applyTheme(theme) {
    if (STATE.theme === theme) return;
    STATE.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
  }

  // ---------- Header ------------------------------------------------------
  function renderHeader() {
    const now = new Date();
    $("hdr-weekday").textContent = WEEKDAYS_FULL[now.getDay()];
    $("hdr-month").textContent = MONTHS_FULL[now.getMonth()];
    $("hdr-day").textContent = String(now.getDate());

    const w = STATE.weather;
    if (!w) return;
    $("hdr-wtemp").textContent = `${w.current.temp_f}°`;
    $("hdr-wdesc").textContent = w.current.description || "";
    $("hdr-loc").textContent = (STATE.config && STATE.config.location_label) || "";
    $("hdr-wicon").innerHTML = iconSvg(WMO_TO_ICON(w.current.weather_code));
  }

  // ---------- Forecast pills ---------------------------------------------
  function renderForecast() {
    const host = $("forecast");
    host.innerHTML = "";
    if (!STATE.weather) return;
    const tpl = $("tpl-forecast-pill");
    const days = STATE.weather.daily.slice(0, 7);
    days.forEach((d) => {
      const node = tpl.content.firstElementChild.cloneNode(true);
      const date = parseISO(d.date);
      node.querySelector(".pill__label").textContent = WEEKDAYS[date.getDay()];
      node.querySelector(".pill__icon").innerHTML = iconSvg(WMO_TO_ICON(d.weather_code));
      node.querySelector(".pill__hi").textContent = `${Math.round(d.high_f)}°`;
      node.querySelector(".pill__lo").textContent = `${Math.round(d.low_f)}°`;
      host.appendChild(node);
    });
  }

  // ---------- Day headers + columns + hours ------------------------------
  function renderWeekStructure() {
    const dayheaders = $("dayheaders");
    const cols = $("cols");
    const hours = $("hours");
    dayheaders.innerHTML = "";
    cols.innerHTML = "";
    hours.innerHTML = "";

    // Leading empty cell to align with gutter column.
    const spacer = document.createElement("div");
    dayheaders.appendChild(spacer);

    const today = new Date();
    const tpl = $("tpl-dayheader");
    for (let i = 0; i < 7; i++) {
      const d = new Date(STATE.weekStart);
      d.setDate(d.getDate() + i);
      const node = tpl.content.firstElementChild.cloneNode(true);
      if (sameDay(d, today)) node.classList.add("dayhead--today");
      node.querySelector(".dayhead__label").textContent = WEEKDAYS[d.getDay()].toUpperCase();
      node.querySelector(".dayhead__num").textContent = String(d.getDate());
      dayheaders.appendChild(node);

      const col = document.createElement("div");
      col.className = "col";
      col.dataset.dayIndex = String(i);
      if (sameDay(d, today)) col.classList.add("col--today", "glass--deep");
      cols.appendChild(col);
    }

    // Hour labels along the gutter
    for (let h = HOUR_START; h < HOUR_END; h++) {
      const el = document.createElement("div");
      el.className = "hour";
      const label = h === 12 ? "12p" : h > 12 ? `${h - 12}p` : `${h}a`;
      el.textContent = label;
      hours.appendChild(el);
    }
  }

  // ---------- All-day strip ----------------------------------------------
  function renderAllDay() {
    const host = $("allday");
    host.innerHTML = "";
    // Leading spacer to match time gutter
    const spacer = document.createElement("div");
    host.appendChild(spacer);

    // For each of the 7 day columns, create a vertical stack container
    const dayContainers = [];
    for (let i = 0; i < 7; i++) {
      const c = document.createElement("div");
      c.style.display = "flex";
      c.style.flexDirection = "column";
      c.style.gap = "4px";
      c.style.padding = "0 calc(var(--u) * 0.25)";
      c.style.minWidth = "0";
      host.appendChild(c);
      dayContainers.push(c);
    }

    const tpl = $("tpl-allday");
    const weekEnd = new Date(STATE.weekStart.getTime() + 7 * 86400 * 1000);

    STATE.events
      .filter((e) => e.all_day)
      .forEach((e) => {
        // An all-day event can span multiple days. Add a pill to every column it covers.
        const s = e._start < STATE.weekStart ? new Date(STATE.weekStart) : new Date(e._start);
        const end = e._end > weekEnd ? new Date(weekEnd) : new Date(e._end);
        for (let d = new Date(s); d < end; d.setDate(d.getDate() + 1)) {
          const idx = Math.floor((d - STATE.weekStart) / 86400000);
          if (idx < 0 || idx > 6) continue;
          const node = tpl.content.firstElementChild.cloneNode(true);
          node.style.color = e.color;
          node.querySelector(".alldaypill__title").textContent = e.title;
          node.querySelector(".alldaypill__title").style.color = "var(--ink)";
          dayContainers[idx].appendChild(node);
        }
      });
  }

  // ---------- Timed events with collision layout -------------------------
  function renderEvents() {
    const cols = $("cols").querySelectorAll(".col");
    cols.forEach((c) => {
      c.querySelectorAll(".event").forEach((el) => el.remove());
    });

    const tpl = $("tpl-event");
    const dayBuckets = Array.from({ length: 7 }, () => []);

    STATE.events
      .filter((e) => !e.all_day)
      .forEach((e) => {
        const start = e._start;
        const end = e._end;
        // Determine which day column this event lives in.
        const dayIdx = Math.floor((new Date(start.getFullYear(), start.getMonth(), start.getDate()) - STATE.weekStart) / 86400000);
        if (dayIdx < 0 || dayIdx > 6) return;
        // Clip to visible hour window
        const minStart = new Date(start); minStart.setHours(HOUR_START, 0, 0, 0);
        const maxEnd = new Date(start); maxEnd.setHours(HOUR_END, 0, 0, 0);
        const s = start < minStart ? minStart : start;
        const ePt = end > maxEnd ? maxEnd : end;
        if (ePt <= minStart || s >= maxEnd) return;
        dayBuckets[dayIdx].push({ ev: e, s, e: ePt });
      });

    dayBuckets.forEach((bucket, idx) => {
      const layout = collisionLayout(bucket);
      const col = cols[idx];
      layout.forEach(({ ev, s, e, col: c, cols: total }) => {
        const node = tpl.content.firstElementChild.cloneNode(true);
        node.style.setProperty("--ev-color", ev.color);
        const totalMin = (HOUR_END - HOUR_START) * 60;
        const top = (((s.getHours() + s.getMinutes() / 60) - HOUR_START) / HOURS_COUNT) * 100;
        const height = (((e - s) / 60000) / totalMin) * 100;

        const widthPct = 100 / total;
        const leftPct = widthPct * c;
        node.style.top = `${top}%`;
        node.style.height = `calc(${height}% - 4px)`;
        node.style.left = `calc(${leftPct}% + var(--u) * 0.25)`;
        node.style.right = "auto";
        node.style.width = `calc(${widthPct}% - var(--u) * 0.5)`;
        node.style.setProperty("background-color", "var(--surface)");

        node.querySelector(".event__stripe").style.background = ev.color;
        node.querySelector(".event__title").textContent = ev.title;
        node.querySelector(".event__time").textContent = fmtTimeRange(ev._start, ev._end);

        const durationMin = (e - s) / 60000;
        if (durationMin < 45) node.classList.add("event--short");
        if (durationMin < 25) node.classList.add("event--tiny");

        col.appendChild(node);
      });
    });
  }

  // Greedy column-packing for overlapping events.
  // Returns the input items annotated with {col, cols} where col is the
  // 0-based column and cols is the total column count in its overlap cluster.
  function collisionLayout(items) {
    if (items.length === 0) return [];
    items.sort((a, b) => a.s - b.s || b.e - a.e);

    const result = [];
    let cluster = [];
    let clusterEnd = 0;

    const flush = () => {
      // Assign columns within cluster via greedy packing
      const columns = [];
      cluster.forEach((it) => {
        let placed = false;
        for (let i = 0; i < columns.length; i++) {
          if (columns[i].length === 0 || columns[i][columns[i].length - 1].e <= it.s) {
            columns[i].push(it);
            it._col = i;
            placed = true;
            break;
          }
        }
        if (!placed) {
          columns.push([it]);
          it._col = columns.length - 1;
        }
      });
      const total = columns.length;
      cluster.forEach((it) => {
        result.push({ ...it, col: it._col, cols: total });
      });
      cluster = [];
      clusterEnd = 0;
    };

    items.forEach((it) => {
      if (cluster.length === 0 || it.s < clusterEnd) {
        cluster.push(it);
        clusterEnd = Math.max(clusterEnd, it.e);
      } else {
        flush();
        cluster.push(it);
        clusterEnd = it.e;
      }
    });
    flush();
    return result;
  }

  // ---------- Now line ---------------------------------------------------
  function positionNowLine() {
    const line = $("nowline");
    const now = new Date();
    const weekEnd = new Date(STATE.weekStart.getTime() + 7 * 86400 * 1000);
    if (now < STATE.weekStart || now >= weekEnd) {
      line.hidden = true;
      return;
    }
    const hrs = now.getHours() + now.getMinutes() / 60;
    if (hrs < HOUR_START || hrs >= HOUR_END) {
      line.hidden = true;
      return;
    }
    line.hidden = false;
    const grid = $("weekgrid");
    const cols = $("cols");
    const gridRect = grid.getBoundingClientRect();
    const colsRect = cols.getBoundingClientRect();
    const frac = (hrs - HOUR_START) / HOURS_COUNT;
    const yWithinCols = frac * colsRect.height;
    const y = (colsRect.top - gridRect.top) + yWithinCols;
    line.style.top = `${y}px`;
    line.style.left = `${colsRect.left - gridRect.left}px`;
    line.style.right = `${gridRect.right - colsRect.right}px`;
  }

  // ---------- Render all -------------------------------------------------
  function renderAll() {
    renderWeekStructure();
    renderAllDay();
    renderEvents();
    positionNowLine();
  }

  // ---------- Perf probe -------------------------------------------------
  function perfProbe() {
    let frames = 0;
    let t0 = 0;
    const samples = [];
    let last = 0;
    function tick(ts) {
      if (t0 === 0) t0 = ts;
      if (last > 0) samples.push(ts - last);
      last = ts;
      frames++;
      if (frames < 12) return requestAnimationFrame(tick);
      samples.sort((a, b) => a - b);
      const median = samples[Math.floor(samples.length / 2)];
      if (median > 40) {
        document.documentElement.setAttribute("data-perf", "lite");
        STATE.perf = "lite";
      }
    }
    requestAnimationFrame(tick);
  }

  // ---------- Helpers ----------------------------------------------------
  const $ = (id) => document.getElementById(id);
  const iconSvg = (id) =>
    `<svg width="100%" height="100%" viewBox="0 0 24 24" aria-hidden="true"><use href="#${id}"/></svg>`;

  // ---------- Scheduling -------------------------------------------------
  function scheduleThreeAmReload() {
    const now = new Date();
    const target = new Date(now);
    target.setHours(3, 0, 0, 0);
    if (target <= now) target.setDate(target.getDate() + 1);
    const delay = target - now;
    setTimeout(() => window.location.reload(), delay);
  }

  // ---------- Bootstrap --------------------------------------------------
  async function init() {
    STATE.weekStart = startOfSunday(new Date());
    await fetchConfig();
    renderWeekStructure();
    await Promise.all([fetchWeather(), fetchEvents()]);
    perfProbe();
    scheduleThreeAmReload();

    setInterval(fetchEvents, 5 * 60 * 1000);
    setInterval(fetchWeather, 30 * 60 * 1000);
    setInterval(positionNowLine, 60 * 1000);
    setInterval(renderHeader, 60 * 1000);
    setInterval(evaluateTheme, 5 * 60 * 1000);
    setInterval(() => {
      // If the day has rolled over, rebase the week and re-render.
      const nowStart = startOfSunday(new Date());
      if (nowStart.getTime() !== STATE.weekStart.getTime()) {
        STATE.weekStart = nowStart;
        renderAll();
      }
    }, 60 * 1000);

    window.addEventListener("resize", () => {
      requestAnimationFrame(positionNowLine);
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
