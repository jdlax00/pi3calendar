// piCalendar — portrait agenda (mom-vertical branch only).
// Today card + the next N days stacked down a TV mounted on its side.
// app.js owns fetching, theme, and timers; it calls PiPortrait.render()
// from renderAll() whenever events, weather, or the clock change.

(() => {
  "use strict";

  const DAY_NAMES = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
  ];
  const MONTHS_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  // Local YYYY-MM-DD — matches weather.daily[].date from Open-Meteo.
  const isoDate = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  // "9:00 am" — fuller than the grid's "9a"; read from across the room.
  const fmtClock = (d) => {
    let h = d.getHours();
    const m = String(d.getMinutes()).padStart(2, "0");
    const ampm = h >= 12 ? "pm" : "am";
    h = h % 12 || 12;
    return `${h}:${m} ${ampm}`;
  };

  // setDate, not +86400000 — keeps midnight correct across DST changes.
  const addDays = (d, n) => {
    const out = new Date(d);
    out.setDate(out.getDate() + n);
    return out;
  };

  function dayName(i, date) {
    if (i === 0) return "Today";
    if (i === 1) return "Tomorrow";
    return DAY_NAMES[date.getDay()];
  }

  // Events overlapping [dayStart, dayEnd). All-day first, then by start time,
  // so a multi-day trip leads every day it covers.
  function eventsForDay(events, dayStart, dayEnd) {
    return events
      .filter((e) => e._start < dayEnd && e._end > dayStart)
      .sort((a, b) => {
        if (a.all_day !== b.all_day) return a.all_day ? -1 : 1;
        return a._start - b._start;
      });
  }

  function timeLabel(e, dayStart, dayEnd) {
    if (e.all_day) return "All day";
    if (e._start < dayStart) {
      // Continuing from a previous day (overnight / multi-day timed event).
      return e._end < dayEnd ? `until ${fmtClock(e._end)}` : "All day";
    }
    return fmtClock(e._start);
  }

  function renderDay(i, dayStart, state, h) {
    const dayEnd = addDays(dayStart, 1);
    const now = new Date();

    const card = document.createElement("article");
    card.className = i === 0 ? "agday glass agday--today" : "agday glass";

    const head = document.createElement("header");
    head.className = "agday__head";
    const name = document.createElement("span");
    name.className = "agday__name";
    name.textContent = dayName(i, dayStart);
    const date = document.createElement("span");
    date.className = "agday__date";
    date.textContent = `${MONTHS_SHORT[dayStart.getMonth()]} ${dayStart.getDate()}`;
    head.append(name, date);

    const wx = state.weather && (state.weather.daily || []).find((d) => d.date === isoDate(dayStart));
    if (wx) {
      const w = document.createElement("span");
      w.className = "agday__wx";
      w.innerHTML =
        `<span class="agday__wicon">${h.iconSvg(h.WMO_TO_ICON(wx.weather_code))}</span>` +
        `<span class="agday__hi">${Math.round(wx.high_f)}°</span>` +
        `<span class="agday__lo">${Math.round(wx.low_f)}°</span>`;
      head.appendChild(w);
    }
    card.appendChild(head);

    const list = document.createElement("ul");
    list.className = "agday__list";
    const evs = eventsForDay(state.events, dayStart, dayEnd);
    if (evs.length === 0) {
      const li = document.createElement("li");
      li.className = "agev agev--empty";
      li.textContent = "Nothing scheduled";
      list.appendChild(li);
    }
    evs.forEach((e) => {
      const li = document.createElement("li");
      li.className = "agev";
      if (i === 0 && !e.all_day && e._end <= now) li.classList.add("agev--past");
      li.style.setProperty("--ev-color", e.color || "currentColor");
      li.innerHTML =
        '<span class="agev__stripe"></span>' +
        '<span class="agev__time"></span>' +
        '<span class="agev__title"></span>';
      li.querySelector(".agev__time").textContent = timeLabel(e, dayStart, dayEnd);
      li.querySelector(".agev__title").textContent = e.title;
      list.appendChild(li);
    });
    card.appendChild(list);
    return card;
  }

  // Drop rows from the end until the list fits its card, then say how many
  // were hidden. Runs after layout, so it measures real rendered heights.
  function fitList(list) {
    if (list.scrollHeight <= list.clientHeight + 1) return;
    const rows = Array.from(list.querySelectorAll(".agev"));
    const more = document.createElement("li");
    more.className = "agev agev--more";
    list.appendChild(more);
    let hidden = 0;
    while (rows.length > 1 && list.scrollHeight > list.clientHeight + 1) {
      rows.pop().remove();
      hidden++;
      more.textContent = `+${hidden} more`;
    }
  }

  // Split the column's height between cards by water-filling: a quiet day
  // gets exactly what it needs, and whatever is left is shared evenly (Today
  // weighted up) among the days that would overflow. Plain flex-shrink can't
  // do this — it squeezes in proportion to size, so busy days collapse to a
  // single row while quiet days keep slack.
  const TODAY_WEIGHT = 1.6;
  function allocateHeights(host) {
    const cards = Array.from(host.children);
    host.classList.add("portrait--measuring");
    const natural = cards.map((c) => c.getBoundingClientRect().height);
    host.classList.remove("portrait--measuring");

    const gap = parseFloat(getComputedStyle(host).rowGap) || 0;
    let remaining = host.clientHeight - gap * (cards.length - 1);
    if (natural.reduce((a, b) => a + b, 0) <= remaining) return; // all fits

    const weight = (i) => (i === 0 ? TODAY_WEIGHT : 1);
    const alloc = new Array(cards.length);
    let open = cards.map((_, i) => i);
    // Each pass settles every card that fits inside its current share.
    for (;;) {
      const totalW = open.reduce((a, i) => a + weight(i), 0);
      const fits = open.filter((i) => natural[i] <= (remaining * weight(i)) / totalW);
      if (fits.length === 0) {
        open.forEach((i) => { alloc[i] = (remaining * weight(i)) / totalW; });
        break;
      }
      fits.forEach((i) => { alloc[i] = natural[i]; remaining -= natural[i]; });
      open = open.filter((i) => !fits.includes(i));
      if (open.length === 0) break;
    }
    cards.forEach((c, i) => { c.style.flex = `0 0 ${alloc[i]}px`; });
  }

  function render(state, h) {
    const host = h.$("portrait");
    if (!host || !state.weekStart) return;
    const days = ((state.config && state.config.agenda_days) || 7) + 1;

    const frag = document.createDocumentFragment();
    for (let i = 0; i < days; i++) {
      frag.appendChild(renderDay(i, addDays(state.weekStart, i), state, h));
    }
    host.replaceChildren(frag);
    host.hidden = false;
    allocateHeights(host);
    host.querySelectorAll(".agday__list").forEach(fitList);
  }

  window.PiPortrait = { render };
})();
