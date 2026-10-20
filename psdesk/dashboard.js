(function () {
  const data = JSON.parse(document.getElementById("ps-data").textContent);
  const state = {
    book: "summary",
    boat: "All",
    fiscal: "All",
    stage: "All",
    coverage: "All",
    recordType: "All",
    account: "All",
    closeTiming: "All",
    status: "All",
    band: "All",
    q: "",
    sort: "value",
    dir: "desc",
    open: "",
  };

  const params = new URLSearchParams(location.search);
  ["book", "boat", "fiscal", "stage", "coverage", "recordType", "account", "closeTiming", "status", "band", "q", "sort", "dir"].forEach((key) => {
    if (params.get(key)) state[key] = params.get(key);
  });
  if (!["summary", "services", "shadow", "other"].includes(state.book)) state.book = "summary";

  const coverageLabel = {
    missing: "No primary quote",
    unlisted: "Quote not in export",
    linked: "Linked",
  };

  function bookRows() {
    const key = state.book === "summary" ? "services" : state.book;
    return data[key] || [];
  }

  function matches(row, skip) {
    if (skip !== "boat" && state.boat !== "All" && row.boat !== state.boat) return false;
    if (skip !== "fiscal" && state.fiscal !== "All" && row.fiscal !== state.fiscal) return false;
    if (skip !== "stage" && state.stage !== "All" && row.stage !== state.stage) return false;
    if (skip !== "account" && state.account !== "All" && row.account !== state.account) return false;
    if (state.closeTiming !== "All" && row.closeTiming !== state.closeTiming) return false;
    if (state.book === "services" && skip !== "coverage" && state.coverage !== "All" && row.coverage !== state.coverage) return false;
    if (state.book === "services" && state.status === "fresh" && row.statusFresh !== true) return false;
    if (state.book === "services" && state.status === "stale" && row.statusFresh !== false) return false;
    if (state.book === "services" && state.band !== "All" && row.band !== state.band) return false;
    if (state.book !== "services" && state.recordType !== "All" && row.recordType !== state.recordType) return false;
    if (state.q) {
      const hay = [row.account, row.name, row.owner, row.id, row.primaryQuote, row.statusNote, row.servicesType]
        .concat((row.quotes || []))
        .concat((row.lines || []).flatMap((line) => [line.product, line.family, line.quote, line.line]))
        .join(" ")
        .toLowerCase();
      if (!hay.includes(state.q.trim().toLowerCase())) return false;
    }
    return true;
  }

  function selected() {
    return bookRows().filter((row) => matches(row));
  }

  function valueOf(row) {
    if (state.book === "services" || state.book === "summary") return Number(row.servicesValue) || 0;
    return Number(row.net) || 0;
  }

  function money(value) {
    if (value == null || Number.isNaN(Number(value))) return "—";
    return Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function pct(value) {
    if (value == null) return "";
    return (Number(value) * 100).toFixed(1) + "%";
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function options(values) {
    return ["All"].concat(values.filter((value, index) => value && values.indexOf(value) === index));
  }

  function boatNames(rows) {
    return options(rows.map((row) => row.boat).filter(Boolean)).slice(1).sort((a, b) => {
      const rank = (name) => (name === "Unassigned" || name === "Mixed" ? 1 : 0);
      return rank(a) - rank(b) || a.localeCompare(b);
    });
  }

  function drawBars(host, rows, key, label) {
    host.replaceChildren();
    const title = el("h2", "", label);
    host.append(title);
    const totals = new Map();
    rows.forEach((row) => {
      const name = row[key] || "Unassigned";
      totals.set(name, (totals.get(name) || 0) + valueOf(row));
    });
    const entries = [...totals.entries()].sort((a, b) => b[1] - a[1]);
    const max = entries.reduce((peak, entry) => Math.max(peak, entry[1]), 0);
    if (!entries.length) {
      host.append(el("p", "empty", "Nothing in this cut."));
      return;
    }
    entries.forEach(([name, total]) => {
      const button = el("button", "bar");
      button.type = "button";
      if ((key === "boat" && state.boat === name) || (key === "fiscal" && state.fiscal === name)) button.classList.add("active");
      button.append(el("span", "bar-label", name));
      const track = el("span", "bar-track");
      const fill = el("span", "bar-fill");
      fill.style.width = max ? Math.max(2, (total / max) * 100) + "%" : "0";
      track.append(fill);
      button.append(track, el("span", "bar-value", money(total)));
      button.addEventListener("click", () => {
        if (key === "boat") state.boat = state.boat === name ? "All" : name;
        if (key === "fiscal") state.fiscal = state.fiscal === name ? "All" : name;
        state.open = "";
        render();
      });
      host.append(button);
    });
  }

  function renderLead(rows) {
    const lead = document.getElementById("lead");
    const unit = data.currency ? " " + data.currency : "";
    if (state.book === "services" || state.book === "summary") {
      const value = rows.reduce((sum, row) => sum + (Number(row.servicesValue) || 0), 0);
      const weighted = rows.reduce((sum, row) => sum + (Number(row.weighted) || 0), 0);
      const missing = rows.filter((row) => row.coverage === "missing").length;
      const unlisted = rows.filter((row) => row.coverage === "unlisted").length;
      const noun = rows.length === 1 ? "opportunity" : "opportunities";
      const due = rows.filter((row) => row.closeTiming === "due").length;
      const soon = rows.filter((row) => row.closeTiming === "soon").length;
      const stale = rows.filter((row) => row.statusFresh === false).length;
      const forecast = rows.filter((row) => row.band === "forecast");
      const pipeline = rows.filter((row) => row.band === "pipeline");
      const forecastValue = forecast.reduce((sum, row) => sum + (Number(row.servicesValue) || 0), 0);
      const pipelineValue = pipeline.reduce((sum, row) => sum + (Number(row.servicesValue) || 0), 0);
      lead.textContent = rows.length + " services " + noun + ", " + money(value) + unit + " services value and " + money(weighted) + unit + " weighted. Forecast " + money(forecastValue) + unit + " across " + forecast.length + ". Pipeline " + money(pipelineValue) + unit + " across " + pipeline.length + ". " + missing + " with no primary quote. " + unlisted + " with a primary quote and no lines in the quote export. " + due + " close today or earlier. " + soon + " close in the next " + (data.soonDays || 14) + " days. " + stale + " need a status.";
      return;
    }
    const nouns = {
      shadow: "license and renewal ",
      outside: "services quote ",
      other: "other ",
    };
    const net = rows.reduce((sum, row) => sum + (Number(row.net) || 0), 0);
    const deal = rows.length === 1 ? "deal" : "deals";
    lead.textContent = rows.length + " " + (nouns[state.book] || "") + deal + ", " + money(net) + unit + ".";
  }

  function renderStats(rows) {
    const host = document.getElementById("stats");
    host.replaceChildren();
    const unit = data.currency ? ", " + data.currency : "";
    let cards;
    if (state.book === "services") {
      const value = rows.reduce((sum, row) => sum + (Number(row.servicesValue) || 0), 0);
      const weighted = rows.reduce((sum, row) => sum + (Number(row.weighted) || 0), 0);
      cards = [
        [money(value), "Services value" + unit, "", "", ""],
        [money(weighted), "Weighted, as exported" + unit, "", "", ""],
        [String(rows.filter((row) => row.coverage === "missing").length), "No primary quote", "flag", "coverage", "missing"],
        [String(rows.filter((row) => row.coverage === "unlisted").length), "Quote not in export", "watch", "coverage", "unlisted"],
      ];
    } else {
      const net = rows.reduce((sum, row) => sum + (Number(row.net) || 0), 0);
      cards = [
        [money(net), "Net total" + unit, "watch", "", ""],
        [String(rows.length), "Deals", "", "", ""],
        [String(new Set(rows.map((row) => row.boat)).size), "Boats", "", "", ""],
        [String(rows.filter((row) => row.negativeDiscount).length), "Negative discount", "watch", "", ""],
      ];
    }
    const due = rows.filter((row) => row.closeTiming === "due").length;
    const soon = rows.filter((row) => row.closeTiming === "soon").length;
    cards.push(
      [String(due), "Close today or past", due ? "flag" : "", "closeTiming", "due"],
      [String(soon), "Close in the next " + (data.soonDays || 14) + " days", soon ? "watch" : "", "closeTiming", "soon"]
    );
    if (state.book === "services") {
      const stale = rows.filter((row) => row.statusFresh === false).length;
      cards.push([String(stale), "Status overdue", stale ? "flag" : "", "status", "stale"]);
    }
    cards.forEach(([value, label, kind, filterKey, filterValue]) => {
      const button = el("button", "stat " + kind);
      button.type = "button";
      if (filterKey && state[filterKey] === filterValue) button.classList.add("active");
      button.append(el("b", "", value), el("span", "", label));
      if (filterKey) {
        button.addEventListener("click", () => {
          state[filterKey] = state[filterKey] === filterValue ? "All" : filterValue;
          state.open = "";
          render();
        });
      }
      host.append(button);
    });
  }

  function select(host, label, value, choices, key) {
    const control = document.createElement("select");
    control.setAttribute("aria-label", label);
    choices.forEach((choice) => {
      const option = el("option", "", choice === "All" ? label : choice);
      option.value = choice;
      if (choice === value) option.selected = true;
      control.append(option);
    });
    control.addEventListener("change", () => {
      state[key] = control.value;
      state.open = "";
      render();
    });
    host.append(control);
  }

  function bookTabs() {
    const tabs = [
      ["summary", "Summary"],
      ["services", "Services"],
      ["shadow", "License and renewal"],
    ];
    if ((data.other || []).length) tabs.push(["other", "Other record types"]);
    return tabs;
  }

  let filterStamp = "";

  function renderFilters() {
    const books = document.getElementById("books");
    books.replaceChildren();
    bookTabs().forEach(([id, label]) => {
      const count = id === "summary" ? "" : " " + (data[id] || []).length;
      const button = el("button", state.book === id ? "active" : "", label + count);
      button.type = "button";
      button.addEventListener("click", () => {
        state.book = id;
        state.boat = "All";
        state.fiscal = "All";
        state.stage = "All";
        state.coverage = "All";
        state.recordType = "All";
        state.account = "All";
        state.closeTiming = "All";
        state.status = "All";
        state.band = "All";
        state.open = "";
        state.sort = "value";
        state.dir = "desc";
        render();
      });
      books.append(button);
    });

    const boats = document.getElementById("boats");
    boats.replaceChildren();
    const boatButton = (name) => {
      const button = el("button", state.boat === name ? "active" : "", name);
      button.type = "button";
      button.addEventListener("click", () => {
        state.boat = name;
        state.open = "";
        render();
      });
      boats.append(button);
    };
    boatButton("All");
    boatNames(bookRows()).forEach(boatButton);

    const filters = document.getElementById("filters");
    filters.replaceChildren();
    const universe = bookRows();
    const accounts = universe.map((row) => row.account).filter(Boolean).sort((a, b) => a.localeCompare(b));
    select(filters, "All accounts", state.account, options(accounts), "account");
    if (state.book !== "summary") {
      select(filters, "All periods", state.fiscal, options(universe.map((row) => row.fiscal)), "fiscal");
      select(filters, "All stages", state.stage, options(universe.map((row) => row.stage).sort()), "stage");
      const closeLabels = { due: "Today or past", soon: "Next " + (data.soonDays || 14) + " days" };
      select(filters, "All close dates", state.closeTiming, ["All", "due", "soon"], "closeTiming");
      labelOptions(filters, closeLabels);
    }
    if (state.book === "services") {
      select(filters, "All coverage", state.coverage, ["All", "missing", "unlisted", "linked"], "coverage");
      labelOptions(filters, coverageLabel);
      select(filters, "All status", state.status, ["All", "stale", "fresh"], "status");
      labelOptions(filters, { stale: "Status overdue", fresh: "Status current" });
      select(filters, "All bands", state.band, ["All", "forecast", "pipeline"], "band");
      labelOptions(filters, { forecast: "Forecast", pipeline: "Pipeline" });
    } else if (state.book !== "summary") {
      select(filters, "All record types", state.recordType, options(universe.map((row) => row.recordType)), "recordType");
    }
    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "Name, account, or quote";
    search.value = state.q;
    search.setAttribute("aria-label", "Opportunity name or account");
    search.addEventListener("input", () => {
      state.q = search.value;
      render();
    });
    filters.append(search);
  }

  function labelOptions(host, labels) {
    const control = host.querySelector("select:last-of-type");
    [...control.options].forEach((option) => {
      if (labels[option.value]) option.textContent = labels[option.value];
    });
  }

  function sortValue(row, key) {
    if (key === "value") return valueOf(row);
    if (key === "close") return row.closeIso || null;
    if (key === "status") return row.statusIso || null;
    if (key === "weighted") return row.weighted == null ? null : Number(row.weighted);
    if (key === "coverage") return coverageLabel[row.coverage] || null;
    const value = row[key];
    if (value == null || value === "") return null;
    return value;
  }

  function sortRows(rows) {
    const dir = state.dir === "asc" ? 1 : -1;
    const key = state.sort;
    return rows.slice().sort((a, b) => {
      const av = sortValue(a, key);
      const bv = sortValue(b, key);
      const aEmpty = av == null || av === "";
      const bEmpty = bv == null || bv === "";
      if (aEmpty && bEmpty) return 0;
      if (aEmpty) return 1;
      if (bEmpty) return -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv), undefined, { numeric: true, sensitivity: "base" }) * dir;
    });
  }

  function header(table, label, key, numeric) {
    const cell = el("th", numeric ? "num" : "");
    const button = el("button", "", label);
    button.type = "button";
    if (state.sort === key) {
      button.textContent = label + (state.dir === "asc" ? " ↑" : " ↓");
      cell.setAttribute("aria-sort", state.dir === "asc" ? "ascending" : "descending");
    }
    button.addEventListener("click", () => {
      if (state.sort === key) state.dir = state.dir === "asc" ? "desc" : "asc";
      else {
        state.sort = key;
        state.dir = key === "value" || key === "weighted" ? "desc" : "asc";
      }
      render();
    });
    cell.append(button);
    table.querySelector("thead tr").append(cell);
  }

  function stageCell(row) {
    const wrap = el("td");
    wrap.textContent = row.stage || "—";
    wrap.append(el("div", "tag " + (row.band === "forecast" ? "forecast" : "pipeline"), row.band === "forecast" ? "Forecast" : "Pipeline"));
    return wrap;
  }

  function closeCell(row) {
    const wrap = el("td", "when");
    wrap.textContent = row.close || "—";
    if (row.closeTiming === "due") wrap.append(el("div", "tag flag", "Today or past"));
    if (row.closeTiming === "soon") wrap.append(el("div", "tag watch", "Next " + (data.soonDays || 14) + " days"));
    return wrap;
  }

  function bandLabel(band) {
    return { weekly: "Weekly", fortnightly: "Fortnightly", monthly: "Monthly" }[band] || "";
  }

  function statusCell(row) {
    const wrap = el("td", "when");
    wrap.textContent = row.statusDate || "No status date";
    if (row.statusFresh === false) wrap.append(el("div", "tag flag", "Needs a " + bandLabel(row.statusBand).toLowerCase() + " status"));
    else if (row.statusBand) wrap.append(el("div", "tag", bandLabel(row.statusBand)));
    return wrap;
  }

  function coverageCell(row) {
    const wrap = el("td");
    wrap.textContent = coverageLabel[row.coverage] || "";
    if (row.coverage === "unlisted" && row.primaryQuote) wrap.append(el("div", "tag watch", row.primaryQuote));
    if (row.quoteMismatch) wrap.append(el("div", "tag watch", "Quote number differs"));
    if (row.duplicateId) wrap.append(el("div", "tag flag", "Duplicate id"));
    return wrap;
  }

  function lineTable(lines) {
    const table = document.createElement("table");
    const head = el("tr");
    ["Product", "Family", "Line", "Quote", "Qty", "Net", "Discount"].forEach((label, index) => {
      head.append(el("th", index >= 4 ? "num" : "", label));
    });
    const thead = document.createElement("thead");
    thead.append(head);
    const body = document.createElement("tbody");
    lines.forEach((line) => {
      const tr = document.createElement("tr");
      [line.product, line.family, line.line, line.quote].forEach((value) => tr.append(el("td", "", value || "—")));
      tr.append(el("td", "num", line.qty == null ? "—" : String(line.qty)));
      tr.append(el("td", "num", money(line.net)));
      tr.append(el("td", "num", line.discount == null ? "—" : pct(line.discount)));
      body.append(tr);
    });
    table.append(thead, body);
    return table;
  }

  function renderTable(rows) {
    const host = document.getElementById("table");
    host.replaceChildren();
    const head = document.getElementById("table-head");
    head.replaceChildren();
    const noun = rows.length === 1 ? "row" : "rows";
    const titles = {
      services: "Services opportunities",
      shadow: "PS on a license or renewal quote",
      outside: "Services quotes outside the closing file",
      other: "Other record types",
    };
    head.append(el("h2", "", titles[state.book] || "Opportunities"));
    head.append(el("p", "", rows.length + " " + noun));
    if (!rows.length) {
      host.append(el("p", "empty", "Nothing matches this cut."));
      return;
    }
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    thead.append(document.createElement("tr"));
    table.append(thead);
    const columns = state.book === "services"
      ? [["Account", "account"], ["Opportunity", "name"], ["Boat", "boat"], ["Stage", "stage"], ["Close", "close"], ["Status", "status"], ["Fiscal period", "fiscal"], ["Services value", "value", true], ["Weighted", "weighted", true], ["Coverage", "coverage"], ["Owner", "owner"]]
      : [["Record type", "recordType"], ["Account", "account"], ["Opportunity", "name"], ["Boat", "boat"], ["Stage", "stage"], ["Close", "close"], ["Net", "value", true], ["Owner", "owner"]];
    columns.forEach(([label, key, numeric]) => header(table, label, key, numeric));
    const body = document.createElement("tbody");
    sortRows(rows).forEach((row) => {
      const attention = row.coverage === "missing" || row.closeTiming === "due" || row.statusFresh === false;
      const watch = row.coverage === "unlisted" || row.closeTiming === "soon" || row.negativeDiscount;
      const tr = el("tr", "row" + (attention ? " flag" : watch ? " watch" : ""));
      tr.addEventListener("click", () => {
        state.open = state.open === row.id + row.name ? "" : row.id + row.name;
        render();
      });
      if (state.book === "services") {
        [row.account, row.name, row.boat].forEach((value) => tr.append(el("td", "", value || "—")));
        tr.append(stageCell(row));
        tr.append(closeCell(row), statusCell(row));
        tr.append(el("td", "", row.fiscal || "—"));
        tr.append(el("td", "num", money(row.servicesValue)));
        tr.append(el("td", "num", money(row.weighted)));
        tr.append(coverageCell(row));
        tr.append(el("td", "", row.owner || "—"));
      } else {
        [row.recordType, row.account, row.name, row.boat, row.stage].forEach((value) => tr.append(el("td", "", value || "—")));
        tr.append(closeCell(row));
        tr.append(el("td", "num", money(row.net)));
        tr.append(el("td", "", row.owner || "—"));
      }
      body.append(tr);
      if (state.open === row.id + row.name) {
        const detail = document.createElement("tr");
        detail.className = "detail";
        const cell = document.createElement("td");
        cell.colSpan = columns.length;
        const box = el("div", "detail");
        if (row.statusNote) box.append(el("p", "note", row.statusNote));
        const bits = [];
        if (row.servicesType) bits.push(row.servicesType);
        if (row.probability != null) bits.push("Probability " + pct(row.probability));
        if (row.age) bits.push("Age " + row.age);
        if (row.statusDate) bits.push("Status date " + row.statusDate);
        if (row.statusBand) bits.push(bandLabel(row.statusBand) + " status" + (row.statusFresh === false ? ", overdue" : ", current") + (row.statusAge == null ? ", no status date" : ", " + row.statusAge + " days"));
        if (row.primaryQuote) bits.push("Primary quote " + row.primaryQuote);
        if ((row.quotes || []).length) bits.push("Quote " + row.quotes.join(", "));
        if (row.inServicesBook) bits.push("Also in the services book");
        if (row.negativeDiscount) bits.push("A line discount is negative");
        if (row.id) bits.push(row.id);
        if (row.quoteTotal && row.coverage === "linked") bits.push("Quote lines " + money(row.quoteTotal));
        box.append(el("p", "meta", bits.join(" · ")));
        if ((row.lines || []).length) box.append(lineTable(row.lines));
        cell.append(box);
        detail.append(cell);
        body.append(detail);
      }
    });
    table.append(body);
    const scroll = el("div", "scroll");
    scroll.append(table);
    host.append(scroll);
  }

  function sumValue(rows) {
    return rows.reduce((sum, row) => sum + (Number(row.servicesValue) || 0), 0);
  }

  function openServices(patch) {
    state.book = "services";
    Object.assign(state, patch);
    state.open = patch.open || "";
    render();
  }

  function summaryStat(value, label, onClick) {
    const button = el("button", "stat");
    button.type = "button";
    button.append(el("b", "", value), el("span", "", label));
    if (onClick) button.addEventListener("click", onClick);
    return button;
  }

  function actionGroups(rows) {
    const soon = data.soonDays || 14;
    const reset = { status: "All", coverage: "All", closeTiming: "All", band: "All" };
    return [
      { title: "Close today or past", hint: "Bad dates", kind: "flag", rows: rows.filter((row) => row.closeTiming === "due"), go: { ...reset, closeTiming: "due" } },
      { title: "Close in the next " + soon + " days", hint: "Upcoming", kind: "watch", rows: rows.filter((row) => row.closeTiming === "soon"), go: { ...reset, closeTiming: "soon" } },
      { title: "Status overdue", hint: "No recent status", kind: "flag", rows: rows.filter((row) => row.statusFresh === false), go: { ...reset, status: "stale" } },
      { title: "No primary quote", hint: "No quote link", kind: "flag", rows: rows.filter((row) => row.coverage === "missing"), go: { ...reset, coverage: "missing" } },
      { title: "Quote not in export", hint: "Primary quote has no lines here", kind: "watch", rows: rows.filter((row) => row.coverage === "unlisted"), go: { ...reset, coverage: "unlisted" } },
    ];
  }

  function actionBlock(group) {
    const section = el("section", "action");
    const head = el("button", "action-head " + group.kind);
    head.type = "button";
    head.append(el("span", "action-title", group.title), el("span", "action-hint", group.hint), el("b", "", String(group.rows.length)), el("span", "action-value", money(sumValue(group.rows))));
    head.addEventListener("click", () => openServices(group.go));
    section.append(head);
    if (!group.rows.length) {
      section.append(el("p", "empty", "None"));
      return section;
    }
    const table = document.createElement("table");
    const headRow = document.createElement("tr");
    ["Account", "Opportunity", "Boat", "Stage", "Close", "Services value"].forEach((label, index) => headRow.append(el("th", index === 5 ? "num" : "", label)));
    const thead = document.createElement("thead");
    thead.append(headRow);
    const body = document.createElement("tbody");
    group.rows.slice().sort((a, b) => sumValue([b]) - sumValue([a])).forEach((row) => {
      const tr = el("tr", "row");
      tr.addEventListener("click", () => openServices({ ...group.go, open: row.id + row.name }));
      [row.account, row.name, row.boat].forEach((value) => tr.append(el("td", "", value || "—")));
      tr.append(stageCell(row), closeCell(row), el("td", "num", money(row.servicesValue)));
      body.append(tr);
    });
    table.append(thead, body);
    section.append(table);
    return section;
  }

  function renderSummary(rows) {
    const host = document.getElementById("summary");
    host.replaceChildren();
    const unit = data.currency ? ", " + data.currency : "";
    const forecast = rows.filter((row) => row.band === "forecast");
    const pipeline = rows.filter((row) => row.band === "pipeline");
    const stats = el("div", "stats");
    stats.append(
      summaryStat(money(sumValue(rows)), "Services value" + unit, () => openServices({ band: "All", coverage: "All", closeTiming: "All", status: "All" })),
      summaryStat(money(rows.reduce((sum, row) => sum + (Number(row.weighted) || 0), 0)), "Weighted, as exported" + unit),
      summaryStat(String(rows.length), rows.length === 1 ? "Opportunity" : "Opportunities")
    );
    host.append(stats);
    const split = el("div", "split");
    split.append(
      summaryStat(money(sumValue(forecast)), "Forecast · " + forecast.length + " · stage 80 and above", () => openServices({ band: "forecast", coverage: "All", closeTiming: "All", status: "All" })),
      summaryStat(money(sumValue(pipeline)), "Pipeline · " + pipeline.length + " · below stage 80", () => openServices({ band: "pipeline", coverage: "All", closeTiming: "All", status: "All" }))
    );
    host.append(split);
    const chart = document.createElement("div");
    host.append(chart);
    drawBars(chart, bookRows().filter((row) => matches(row, "boat")), "boat", "Services value" + unit + " by boat");
    host.append(el("h2", "actions-title", "Actions"));
    actionGroups(rows).forEach((group) => host.append(actionBlock(group)));
  }

  function render() {
    const rows = selected();
    document.getElementById("asof").textContent = data.asOf;
    renderLead(rows);
    const stamp = [state.book, state.boat, state.fiscal, state.stage, state.coverage, state.recordType, state.account, state.closeTiming, state.status, state.band].join("\0");
    if (stamp !== filterStamp) {
      filterStamp = stamp;
      renderFilters();
    }
    const summary = state.book === "summary";
    document.getElementById("summary").hidden = !summary;
    document.getElementById("stats").hidden = summary;
    document.querySelector(".charts").hidden = summary;
    document.getElementById("table-head").hidden = summary;
    document.getElementById("table").hidden = summary;
    if (summary) {
      renderSummary(rows);
    } else {
      document.getElementById("summary").replaceChildren();
      renderStats(rows);
      const boatRows = bookRows().filter((row) => matches(row, "boat"));
      const fiscalRows = bookRows().filter((row) => matches(row, "fiscal"));
      const valueLabel = (state.book === "services" ? "Services value" : "Net total") + (data.currency ? ", " + data.currency : "");
      drawBars(document.getElementById("chart-boat"), boatRows, "boat", valueLabel + " by boat");
      drawBars(document.getElementById("chart-fiscal"), fiscalRows, "fiscal", valueLabel + " by fiscal period");
      renderTable(rows);
    }
    const next = new URLSearchParams();
    ["book", "boat", "fiscal", "stage", "coverage", "recordType", "account", "closeTiming", "status", "band", "q", "sort", "dir"].forEach((key) => {
      if (state[key] && state[key] !== "All" && !(key === "book" && state[key] === "summary") && !(key === "sort" && state[key] === "value") && !(key === "dir" && state[key] === "desc")) {
        next.set(key, state[key]);
      }
    });
    const query = next.toString();
    history.replaceState(null, "", query ? "?" + query : location.pathname);
  }

  render();
})();
