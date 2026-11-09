/* Terminal de curvas: lee data/curvas.json (lo genera el proceso diario) y dibuja cada curva. */
(function () {
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const COLORES = ["--s1", "--s2"];
  const fmt = {
    pct: (v) => (v == null ? "—" : d3.format(".2%")(v)),
    pb: (v) => (v == null ? "—" : d3.format("+.0f")(v)),
    pbs: (v) => (v == null ? "—" : d3.format(",.0f")(v)),
    num2: (v) => (v == null ? "—" : d3.format(",.2f")(v)),
    num3: (v) => (v == null ? "—" : d3.format(",.3f")(v)),
    dias: (v) => (v == null ? "—" : d3.format("d")(v)),
    fecha: (v) => (v ? v.split("-").reverse().join("/") : "—"),
    txt: (v) => (v == null ? "—" : String(v)),
    vol: (v) => (v == null ? "—" : new Intl.NumberFormat("es-AR", { notation: "compact", maximumFractionDigits: 1 }).format(v)),
    pctneg: (v) => (v == null ? "—" : d3.format(".1%")(v)),
  };
  const fechaLarga = (iso) => new Date(iso + "T12:00:00").toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  const estado = { verRef: true, verTend: true, datos: null };
  const tip = document.getElementById("tip");

  fetch("data/curvas.json", { cache: "no-store" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((datos) => { estado.datos = datos; iniciar(datos); })
    .catch((e) => {
      document.getElementById("curvas").innerHTML =
        '<p class="error">No se pudieron cargar los datos (data/curvas.json). Si abriste el archivo con doble clic, levantá un servidor: <code>python -m http.server</code> dentro de la carpeta docs.</p>';
      document.getElementById("fecha").textContent = "Sin datos";
      console.error(e);
    });

  function vista() {
    const pedida = (location.hash || "#curvas").slice(1);
    const nombres = ["curvas", "historico", "calculadora"];
    const v = nombres.includes(pedida) ? pedida : (document.getElementById(pedida) ? "curvas" : "curvas");
    nombres.forEach((n) => { document.getElementById(`vista-${n}`).hidden = n !== v; });
    document.querySelectorAll(".tab").forEach((t) => t.setAttribute("aria-current", t.dataset.vista === v ? "page" : "false"));
    if (v === "historico") cargarHistorico();
    if (v === "curvas" && !nombres.includes(pedida)) document.getElementById(pedida)?.scrollIntoView();
    requestAnimationFrame(redibujar);
  }
  window.addEventListener("hashchange", vista);

  function iniciar(datos) {
    document.getElementById("fecha").textContent = `Precios al ${fechaLarga(datos.fecha_precios)}`;
    document.getElementById("dias-atras").textContent = datos.dias_atras;
    const nav = document.getElementById("nav");
    datos.curvas.forEach((c) => {
      const a = document.createElement("a");
      a.href = `#${c.id}`;
      a.textContent = c.titulo.split(":")[0];
      nav.appendChild(a);
    });
    kpis(datos);
    const cont = document.getElementById("curvas");
    datos.curvas.forEach((c) => cont.appendChild(seccion(c, datos)));
    // Breakeven queda en pausa en la web (sigue en los datos y en el Sheet de control)
    if ((datos.calculadora || []).length) seccionCalculadora(datos);
    document.getElementById("ver-ref").addEventListener("change", (e) => { estado.verRef = e.target.checked; redibujar(); });
    document.getElementById("ver-tend").addEventListener("change", (e) => { estado.verTend = e.target.checked; redibujar(); });
    vista();
  }

  function redibujar() { document.querySelectorAll(".grafico").forEach((el) => el._dibujar && el._dibujar()); }

  /* ---------- indicadores de cabecera ---------- */
  function kpis(datos) {
    const box = document.getElementById("kpis");
    const K = datos.kpis || {};
    const defs = [
      ["riesgo_pais", "Riesgo país", (v) => d3.format(",.0f")(v), "pb", (a, b) => `${fmt.pb(a - b)} pb`, true],
      ["tamar", "TAMAR (TNA)", (v) => d3.format(".2%")(v), "", (a, b) => `${fmt.pb((a - b) * 1e4)} pb`, true],
      ["mep", "Dólar MEP implícito", (v) => "$" + d3.format(",.2f")(v), "", (a, b) => d3.format("+.2%")(a / b - 1), true],
      ["a3500", "A3500 mayorista", (v) => "$" + d3.format(",.2f")(v), "", (a, b) => d3.format("+.2%")(a / b - 1), true],
    ];
    defs.forEach(([k, titulo, f, unidad, delta, subeEsMalo]) => {
      const v = K[k]; if (!v) return;
      const t = document.createElement("div"); t.className = "tile"; t.title = v.metodo || "";
      t.innerHTML = '<span class="tile-k"></span><span class="tile-v"></span><span class="tile-d"></span><span class="tile-s"></span>';
      t.querySelector(".tile-k").textContent = titulo;
      const tv = t.querySelector(".tile-v"); tv.textContent = f(v.valor);
      if (unidad) { const sm = document.createElement("small"); sm.textContent = unidad; tv.appendChild(sm); }
      const td = t.querySelector(".tile-d");
      if (v.valor_7d != null) {
        td.textContent = `${delta(v.valor, v.valor_7d)} en ${datos.dias_atras} días`;
        td.classList.add((v.valor > v.valor_7d) === subeEsMalo ? "up" : "down");
      }
      t.querySelector(".tile-s").textContent = v.fecha ? `Dato del ${fmt.fecha(v.fecha)}` : "";
      box.appendChild(t);
    });
  }

  /* ---------- sección de una curva ---------- */
  function seccion(c, datos) {
    const s = document.createElement("section");
    s.className = "curva"; s.id = c.id;
    s.innerHTML = `
      <div class="curva-head"><h2></h2><p></p></div>
      <div class="curva-grid">
        <div class="card"><div class="leyenda"></div><div class="grafico"></div><div class="ecuaciones"></div></div>
        <div class="card"><div class="tabla-box"><table><thead><tr></tr></thead><tbody></tbody></table></div></div>
      </div>`;
    s.querySelector("h2").textContent = c.titulo;
    const campoDelta = c.filas[0] && "delta_tem_pb" in c.filas[0] ? "delta_tem_pb" : "delta_pb";
    const deltas = c.filas.map((r) => r[campoDelta]).filter((v) => v != null);
    if (deltas.length) {
      const prom = d3.mean(deltas), b = document.createElement("span");
      b.className = "badge " + (prom > 0 ? "up" : "down");
      b.textContent = `${fmt.pb(prom)} pb en ${datos.dias_atras} días`;
      b.title = `Cambio promedio de ${c.y.etiqueta}`;
      s.querySelector("h2").append(" ", b);
    }
    s.querySelector(".curva-head p").textContent = c.descripcion;

    const ley = s.querySelector(".leyenda");
    c.grupos.forEach((g, i) => {
      if (!c.filas.some((r) => r[c.campo_grupo] === g.id)) return;
      const sp = document.createElement("span");
      sp.innerHTML = `<i class="sw"></i>`;
      sp.querySelector("i").style.background = `var(${COLORES[i % 2]})`;
      sp.append(g.etiqueta);
      ley.appendChild(sp);
    });
    [["sw hueco", `Hace ${datos.dias_atras} días`], ["sw linea", "Tendencia hoy"], ["sw linea ref", `Tendencia hace ${datos.dias_atras} días`]]
      .forEach(([cls, txt]) => { const sp = document.createElement("span"); sp.innerHTML = `<i class="${cls}"></i>`; sp.append(txt); ley.appendChild(sp); });

    const eq = s.querySelector(".ecuaciones");
    const ecuaciones = () => {
      eq.replaceChildren();
      ajustesVisibles(c).filter((a) => a.serie === "hoy").forEach((a) => {
        const g = c.grupos.find((x) => x.id === a.grupo);
        const d = document.createElement("div");
        d.textContent = `${g ? g.etiqueta + ": " : ""}${c.y.etiqueta} = ${d3.format(".4f")(a.a)} ${a.b < 0 ? "−" : "+"} ${d3.format(".4f")(Math.abs(a.b))}·ln(x)   R² ${d3.format(".2f")(a.r2)}`;
        eq.appendChild(d);
      });
    };

    const graf = s.querySelector(".grafico");
    graf._dibujar = () => { grafico(graf, c, datos); ecuaciones(); };
    if (c.y_opciones) {
      const seg = document.createElement("div"); seg.className = "seg"; seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Tasa a graficar");
      c.y_opciones.forEach((op) => {
        const b = document.createElement("button"); b.type = "button"; b.textContent = op.etiqueta;
        b.setAttribute("aria-pressed", op.campo === c.y.campo);
        b.addEventListener("click", () => {
          c.y = { campo: op.campo, etiqueta: op.etiqueta, formato: "pct" }; c.y_ref = op.ref;
          seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
          graf._dibujar();
        });
        seg.appendChild(b);
      });
      const head = document.createElement("div"); head.className = "card-head";
      const leyendaEl = s.querySelector(".leyenda"); leyendaEl.replaceWith(head); head.append(leyendaEl, seg);
    }
    if (c.id === "tasa-fija") s.appendChild(tablaMep(c, datos));
    if (c.colchon) s.appendChild(tablaColchon(c, datos));
    new ResizeObserver(() => graf._dibujar()).observe(graf);

    tabla(s.querySelector("table"), c, graf);
    return s;
  }

  /* ---------- gráfico ---------- */
  function grafico(el, c, datos) {
    el.replaceChildren();
    const W = Math.max(300, el.clientWidth), H = Math.round(Math.min(420, Math.max(320, W * 0.58)));
    const m = { t: 14, r: 18, b: 42, l: 56 };
    const X = c.x.campo, Y = c.y.campo, YR = c.y_ref, G = c.campo_grupo;
    const color = (g) => css(COLORES[Math.max(0, c.grupos.findIndex((x) => x.id === g)) % 2]);
    const pts = c.filas.filter((r) => r[X] != null && r[Y] != null);
    const ys = pts.flatMap((r) => [r[Y], estado.verRef ? r[YR] : null]).filter((v) => v != null);
    const x = d3.scaleLinear(d3.extent(pts, (r) => r[X]), [m.l, W - m.r]).nice();
    const [y0, y1] = d3.extent(ys); const pad = (y1 - y0) * 0.1 || 0.002;
    const y = d3.scaleLinear([y0 - pad, y1 + pad], [H - m.b, m.t]).nice();

    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
      .attr("aria-label", `${c.titulo}: ${c.y.etiqueta} contra ${c.x.etiqueta}`);
    svg.append("g").selectAll("line").data(y.ticks(6)).join("line")
      .attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y).attr("stroke", css("--grid"));
    const ax = (g) => { g.attr("font-size", null).attr("font-family", null);
      g.selectAll("text").attr("fill", css("--muted")).style("font-size", "11px");
      g.selectAll("line,path").attr("stroke", css("--line")); };
    svg.append("g").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor(W / 95))).tickFormat(c.x.formato === "dias" ? d3.format("d") : d3.format(".1f"))).call(ax);
    svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(y.domain()[1] - y.domain()[0] < 0.02 ? ".2%" : ".1%"))).call(ax)
      .select(".domain").remove();
    svg.append("text").attr("x", W - m.r).attr("y", H - 6).attr("text-anchor", "end").attr("fill", css("--muted")).style("font-size", "11px").text(c.x.etiqueta);

    // tendencias logarítmicas (calculadas en Python)
    if (estado.verTend) {
      ajustesVisibles(c).forEach((a) => {
        if (a.serie === "ref" && !estado.verRef) return;
        const xs = d3.range(0, 61).map((i) => a.x_min * Math.pow(a.x_max / a.x_min, i / 60));
        const col = c.ajuste_por_grupo ? color(a.grupo) : css("--tend");
        svg.append("path").attr("d", d3.line((v) => x(v), (v) => y(a.a + a.b * Math.log(v)))(xs))
          .attr("fill", "none").attr("stroke", col).attr("stroke-width", a.serie === "hoy" ? 1.8 : 1.4)
          .attr("stroke-dasharray", a.serie === "hoy" ? null : "5 4").attr("opacity", a.serie === "hoy" ? 0.75 : 0.5)
          .attr("stroke-linecap", "round");
      });
    }
    // hace N días: círculo vacío unido al punto de hoy
    if (estado.verRef) {
      const r7 = pts.filter((r) => r[YR] != null);
      svg.append("g").selectAll("line").data(r7).join("line")
        .attr("x1", (r) => x(r[X])).attr("x2", (r) => x(r[X])).attr("y1", (r) => y(r[YR])).attr("y2", (r) => y(r[Y]))
        .attr("stroke", (r) => color(r[G])).attr("stroke-opacity", 0.35).attr("stroke-width", 1.5);
      svg.append("g").selectAll("circle").data(r7).join("circle")
        .attr("cx", (r) => x(r[X])).attr("cy", (r) => y(r[YR])).attr("r", 4)
        .attr("fill", css("--panel")).attr("stroke", (r) => color(r[G])).attr("stroke-width", 1.5);
    }
    const puntos = svg.append("g").selectAll("circle").data(pts).join("circle").attr("class", "punto")
      .attr("cx", (r) => x(r[X])).attr("cy", (r) => y(r[Y])).attr("r", 5).attr("fill", (r) => color(r[G]));
    // etiquetas sin superponerse
    const ocupados = [];
    svg.append("g").selectAll("text").data(pts).join("text")
      .attr("x", (r) => x(r[X]) + 7).attr("y", (r) => y(r[Y]) - 7).attr("fill", css("--fg")).style("font-size", "10.5px")
      .text((r) => r.ticker.replace(/D$/, ""))
      .each(function () {
        const b = this.getBBox(); let dy = 0;
        const choca = (o) => b.x < o.x + o.w && b.x + b.width > o.x && b.y + dy < o.y + o.h && b.y + dy + b.height > o.y;
        while (ocupados.some(choca) && dy < 60) dy += 11;
        if (dy) this.setAttribute("y", +this.getAttribute("y") + dy);
        if (b.x + b.width > W) this.setAttribute("x", +this.getAttribute("x") - b.width - 14);
        ocupados.push({ x: b.x, y: b.y + dy, w: b.width, h: b.height });
      });

    // tooltip por punto más cercano
    const del = d3.Delaunay.from(pts, (r) => x(r[X]), (r) => y(r[Y]));
    svg.append("rect").attr("width", W).attr("height", H).attr("fill", "transparent")
      .on("pointermove", (ev) => {
        const [mx, my] = d3.pointer(ev); const i = del.find(mx, my); const r = pts[i];
        puntos.attr("r", (_, j) => (j === i ? 7 : 5));
        mostrarTip(ev, c, r, datos);
        el.dispatchEvent(new CustomEvent("punto", { detail: r.ticker }));
      })
      .on("pointerleave", () => { tip.hidden = true; puntos.attr("r", 5); el.dispatchEvent(new CustomEvent("punto", { detail: null })); });
  }

  function mostrarTip(ev, c, r, datos) {
    const fx = fmt[c.x.formato] || fmt.num2;
    const delta = r.delta_pb ?? r.delta_tem_pb;
    tip.replaceChildren();
    const linea = (k, v, cls) => { const d = document.createElement("div"); const s = document.createElement("span"); s.className = "k"; s.textContent = k + " "; d.append(s, v); if (cls) d.className = cls; tip.appendChild(d); };
    const b = document.createElement("b"); b.textContent = r.ticker; tip.appendChild(b);
    linea(c.y.etiqueta, fmt.pct(r[c.y.campo]));
    if (r[c.y_ref] != null) linea(`Hace ${datos.dias_atras}d`, `${fmt.pct(r[c.y_ref])} (${fmt.pb(delta)} pb)`, delta > 0 ? "up" : "down");
    linea(c.x.etiqueta, fx(r[c.x.campo]));
    linea("Precio", fmt.num3(r.precio));
    tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let left = ev.clientX + 14; if (left + w > window.innerWidth - 8) left = ev.clientX - w - 14;
    tip.style.left = `${Math.max(8, left)}px`;
    tip.style.top = `${Math.min(window.innerHeight - h - 8, Math.max(8, ev.clientY - h / 2))}px`;
  }

  /* ---------- tabla ordenable ---------- */
  function tabla(t, c, graf) {
    const thr = t.querySelector("thead tr"), tb = t.querySelector("tbody");
    let orden = { campo: c.x.campo, asc: true };
    c.columnas.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.etiqueta; th.scope = "col";
      if (col.formato === "txt") th.classList.add("l");
      th.addEventListener("click", () => { orden = { campo: col.campo, asc: orden.campo === col.campo ? !orden.asc : true }; pintar(); });
      thr.appendChild(th);
    });
    function pintar() {
      [...thr.children].forEach((th, i) => th.setAttribute("aria-sort", c.columnas[i].campo === orden.campo ? (orden.asc ? "ascending" : "descending") : "none"));
      const filas = [...c.filas].sort((a, b) => {
        const va = a[orden.campo], vb = b[orden.campo];
        if (va == null) return 1; if (vb == null) return -1;
        return (va > vb ? 1 : va < vb ? -1 : 0) * (orden.asc ? 1 : -1);
      });
      tb.replaceChildren();
      filas.forEach((r) => {
        const tr = document.createElement("tr"); tr.dataset.ticker = r.ticker;
        c.columnas.forEach((col, i) => {
          const td = document.createElement("td");
          td.textContent = (fmt[col.formato] || fmt.txt)(r[col.campo]);
          if (i === 0) td.className = "tk";
          else if (col.formato === "txt") td.className = "l";
          if (col.formato === "pb" && r[col.campo] != null) td.className = r[col.campo] > 0 ? "up" : "down";
          tr.appendChild(td);
        });
        tb.appendChild(tr);
      });
    }
    pintar();
    graf.addEventListener("punto", (e) => {
      tb.querySelectorAll("tr").forEach((tr) => tr.classList.toggle("activa", tr.dataset.ticker === e.detail));
    });
  }

  /* ---------- inflación breakeven ---------- */
  function seccionBreakeven(datos) {
    const sec = document.getElementById("breakeven"); sec.hidden = false;
    const be = datos.breakeven;
    const tb = document.querySelector("#t-breakeven tbody");
    be.pares.forEach((p) => {
      const tr = document.createElement("tr");
      [[`${p.fija} / ${p.cer}`, "tk"], [fmt.fecha(p.vto)], [fmt.dias(p.dias)], [fmt.pct(p.tea_fija)], [fmt.pct(p.tir_real)], [fmt.pct(p.be_mensual)], [fmt.pct(p.be_anual)]]
        .forEach(([v, cls]) => { const td = document.createElement("td"); td.textContent = v; if (cls) td.className = cls; tr.appendChild(td); });
      tb.appendChild(tr);
    });
    const cer = datos.indices?.cer_t10;
    document.getElementById("n-breakeven").textContent =
      (be.curva.length ? "Línea: breakeven entre la tendencia de tasa fija (TEM) y la de CER (TIR real) a " + be.curva.map((c) => c.dias + " días").join(", ") + ". " : "") +
      (cer ? `CER T−10 usado: ${d3.format(",.4f")(cer.valor)} (${fmt.fecha(cer.fecha)}).` : "");
    const el = document.getElementById("g-breakeven");
    const dibujar = () => {
      el.replaceChildren();
      const W = Math.max(300, el.clientWidth), H = 300, m = { t: 14, r: 18, b: 42, l: 56 };
      const pts = be.pares, lin = be.curva;
      const xs = [...pts.map((p) => p.dias), ...lin.map((c) => c.dias)], ys = [...pts.map((p) => p.be_mensual), ...lin.map((c) => c.be_mensual)];
      const x = d3.scaleLinear([0, d3.max(xs) * 1.05], [m.l, W - m.r]).nice();
      const [y0, y1] = d3.extent(ys); const pad = (y1 - y0) * 0.25 || 0.002;
      const y = d3.scaleLinear([y0 - pad, y1 + pad], [H - m.b, m.t]).nice();
      const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", "Inflación breakeven mensual por plazo");
      svg.append("g").selectAll("line").data(y.ticks(5)).join("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y).attr("stroke", css("--grid"));
      const ax = (g) => { g.attr("font-size", null).attr("font-family", null); g.selectAll("text").attr("fill", css("--muted")).style("font-size", "11px"); g.selectAll("line,path").attr("stroke", css("--line")); };
      svg.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.format("d"))).call(ax);
      svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2%"))).call(ax).select(".domain").remove();
      svg.append("text").attr("x", W - m.r).attr("y", H - 6).attr("text-anchor", "end").attr("fill", css("--muted")).style("font-size", "11px").text("Días al vencimiento");
      if (lin.length > 1) svg.append("path").attr("d", d3.line((c) => x(c.dias), (c) => y(c.be_mensual))(lin)).attr("fill", "none").attr("stroke", css("--tend")).attr("stroke-width", 1.6).attr("opacity", .7);
      svg.append("g").selectAll("circle").data(pts).join("circle").attr("cx", (p) => x(p.dias)).attr("cy", (p) => y(p.be_mensual)).attr("r", 5).attr("fill", css("--s1"));
      const usados = [];
      svg.append("g").selectAll("text").data(pts).join("text").attr("x", (p) => x(p.dias) + 7).attr("y", (p) => y(p.be_mensual) - 7)
        .attr("fill", css("--fg")).style("font-size", "10.5px").text((p) => `${p.fija}/${p.cer} ${fmt.pct(p.be_mensual)}`)
        .each(function () {
          const b = this.getBBox(); let dy = 0;
          if (b.x + b.width > W) { this.setAttribute("x", +this.getAttribute("x") - b.width - 14); b.x -= b.width + 14; }
          const choca = (o) => b.x < o.x + o.w && b.x + b.width > o.x && b.y + dy < o.y + o.h && b.y + dy + b.height > o.y;
          while (usados.some(choca) && dy < 60) dy += 12;
          if (dy) this.setAttribute("y", +this.getAttribute("y") + dy);
          usados.push({ x: b.x, y: b.y + dy, w: b.width, h: b.height });
        });
    };
    new ResizeObserver(dibujar).observe(el);
  }

  /* ---------- calculadora ---------- */
  function seccionCalculadora(datos) {
    const sec = document.getElementById("calc-sec"); sec.hidden = false;
    const sel = document.getElementById("c-especie"), ip = document.getElementById("c-precio"),
      il = document.getElementById("c-liq"), it = document.getElementById("c-tir"), res = document.getElementById("c-res");
    const grupos = d3.group(datos.calculadora, (b) => b.curva);
    grupos.forEach((lista, nombre) => {
      const og = document.createElement("optgroup"); og.label = nombre;
      lista.forEach((b) => og.appendChild(new Option(b.ticker, b.ticker)));
      sel.appendChild(og);
    });
    const actual = () => datos.calculadora.find((b) => b.ticker === sel.value);
    const tile = (k, v, s, cls) => {
      const t = document.createElement("div"); t.className = "tile";
      t.innerHTML = '<span class="tile-k"></span><span class="tile-v"></span><span class="tile-s"></span>';
      t.querySelector(".tile-k").textContent = k; t.querySelector(".tile-v").textContent = v;
      const ts = t.querySelector(".tile-s"); ts.textContent = s || ""; if (cls) ts.classList.add(cls);
      res.appendChild(t);
    };
    function calcular(desde) {
      const b = actual(); if (!b) return;
      const liq = il.value || datos.liquidacion;
      if (desde === "tir" && it.value !== "") {
        const objetivo = parseFloat(String(it.value).replace(",", ".")) / 100;
        ip.value = Calc.precioPara(objetivo, b.flujos, liq).toFixed(3);
      }
      const precio = parseFloat(String(ip.value).replace(",", "."));
      res.replaceChildren();
      const r = Calc.tir(precio, b.flujos, liq);
      if (!r) { tile("Resultado", "—", "Revisá el precio y la fecha"); return; }
      const etiqueta = b.tipo === "cer" ? "TIR real" : "TIR";
      const dif = (r.tir - b.tir) * 1e4;
      tile(etiqueta, fmt.pct(r.tir), `Mercado: ${fmt.pct(b.tir)} (${fmt.pb(dif)} pb)`, Math.abs(dif) < 0.5 ? null : dif > 0 ? "up" : "down");
      if (r.tem != null && b.tipo === "pago_final") { tile("TEM", fmt.pct(r.tem)); tile("TNA", fmt.pct(r.tna)); }
      tile("Duration modificada", d3.format(".2f")(r.md), `${fmt.dias(r.dias)} días al vencimiento`);
      tile("Precio usado", fmt.num3(precio), `Mercado: ${fmt.num3(b.precio)} · liquidación ${fmt.fecha(liq)}`);
    }
    sel.addEventListener("change", () => { ip.value = actual().precio; it.value = ""; calcular(); });
    ip.addEventListener("input", () => { it.value = ""; calcular(); });
    it.addEventListener("input", () => calcular("tir"));
    il.addEventListener("change", () => calcular(it.value !== "" ? "tir" : undefined));
    il.value = datos.liquidacion || "";
    sel.value = datos.calculadora[0].ticker; ip.value = datos.calculadora[0].precio;
    calcular();
  }

  function ajustesVisibles(c) { return c.ajustes.filter((a) => !a.y || a.y === c.y.campo); }

  /* ---------- rendimiento en dólares de las letras según el MEP al vencimiento ---------- */
  function tablaMep(c, datos) {
    const mepHoy = datos.kpis?.mep?.valor;
    const card = document.createElement("div"); card.className = "card extra"; card.id = "mep-letras";
    if (!mepHoy) { card.hidden = true; return card; }
    const paso0 = datos.config?.mep_paso || 50, n = datos.config?.mep_niveles || 9;
    card.innerHTML = `<h3 class="card-t">Rendimiento en dólares según el MEP al vencimiento</h3>
      <p class="nota">Rendimiento directo en USD = (pago final / precio) × (MEP hoy / MEP al vencimiento) − 1. MEP implícito de hoy: <b></b>. Verde: le gana al dólar; rojo: pierde.</p>
      <div class="mep-controles"><label>Desde $<input type="number" step="10" id="mep-desde"></label><label>Paso $<input type="number" step="10" id="mep-paso"></label></div>
      <div class="tabla-box"><table class="mapa"><thead></thead><tbody></tbody></table></div>`;
    card.querySelector("b").textContent = "$" + d3.format(",.2f")(mepHoy);
    const iDesde = card.querySelector("#mep-desde"), iPaso = card.querySelector("#mep-paso");
    iPaso.value = paso0; iDesde.value = Math.floor(mepHoy / paso0) * paso0 - paso0;
    const escala = d3.scaleLinear([-0.15, 0, 0.15], ["#b3261e", "#c9c3b8", "#1d7a46"]).clamp(true);
    const pintar = () => {
      const desde = +iDesde.value, paso = +iPaso.value || paso0;
      const niveles = d3.range(n).map((i) => desde + i * paso);
      const thead = card.querySelector("thead"), tb = card.querySelector("tbody");
      thead.innerHTML = ""; tb.innerHTML = "";
      const trh = document.createElement("tr");
      ["Letra", "Días", ...niveles.map((m) => "$" + d3.format(",.0f")(m)), "MEP de equilibrio"].forEach((t, i) => {
        const th = document.createElement("th"); th.textContent = t; if (i === 0) th.className = "l"; trh.appendChild(th);
      });
      const tr2 = document.createElement("tr");
      ["", "", ...niveles.map((m) => d3.format("+.1%")(m / mepHoy - 1)), ""].forEach((t) => { const th = document.createElement("th"); th.textContent = t; tr2.appendChild(th); });
      thead.append(trh, tr2);
      [...c.filas].sort((a, b) => a.dias - b.dias).forEach((r) => {
        const tr = document.createElement("tr");
        const td0 = document.createElement("td"); td0.className = "tk"; td0.textContent = r.ticker; tr.appendChild(td0);
        const td1 = document.createElement("td"); td1.textContent = fmt.dias(r.dias); tr.appendChild(td1);
        niveles.forEach((m) => {
          const v = (r.pago_final / r.precio) * (mepHoy / m) - 1;
          const td = document.createElement("td"); td.className = "c"; td.textContent = d3.format("+.1%")(v);
          td.style.background = escala(v); td.style.color = Math.abs(v) < 0.06 ? "#16202c" : "#fff"; td.title = `${r.ticker} con MEP $${d3.format(",.0f")(m)} al ${fmt.fecha(r.vto)}`;
          tr.appendChild(td);
        });
        const tdq = document.createElement("td"); tdq.textContent = "$" + d3.format(",.0f")(mepHoy * r.pago_final / r.precio); tr.appendChild(tdq);
        tb.appendChild(tr);
      });
    };
    iDesde.addEventListener("input", pintar); iPaso.addEventListener("input", pintar);
    pintar();
    return card;
  }

  /* ---------- colchón de precio hard dollar ---------- */
  function tablaColchon(c, datos) {
    const card = document.createElement("div"); card.className = "card extra"; card.id = "colchon";
    const h = datos.config?.horizonte_colchon;
    card.innerHTML = `<h3 class="card-t">Colchón de precio hasta el ${fmt.fecha(h)}</h3>
      <p class="nota">Si comprás hoy a precio T+1 y cobrás los cupones y amortizaciones hasta el ${fmt.fecha(h)} (dos cupones semestrales, antes de las elecciones de octubre 2027), cuánto puede caer el precio hasta terminar sin ganar ni perder. Sin reinversión.</p>
      <div class="tabla-box"><table><thead><tr></tr></thead><tbody></tbody></table></div>`;
    const cc = { ...c, columnas: c.colchon };
    tabla(card.querySelector("table"), cc, document.createElement("div"));
    return card;
  }

  /* ---------- histórico ---------- */
  const SERIES = [
    ["a3500", "A3500", "#1f5fbf", "A3500"], ["mep", "MEP implícito", "#c4652a", "MEP"], ["cer", "CER", "#0e8a6a", "CER"],
    ["tamar", "TAMAR (TNA)", "#8a5a00", "TAMAR"], ["merval_usd", "Merval en USD", "#7a4fbf", "Merval USD"], ["merval", "Merval en pesos", "#b05a9a", "Merval $"],
    ["bonares_rt", "Bonares (retorno total USD)", "#16202c", "Bonares"], ["globales_rt", "Globales (retorno total USD)", "#5d6878", "Globales"],
  ];
  const hist = { datos: null, cargando: false, modo: "base", rango: "2025", activas: new Set(["a3500", "mep", "cer", "merval_usd", "bonares_rt"]) };

  function cargarHistorico() {
    if (hist.datos || hist.cargando) return;
    hist.cargando = true;
    fetch("data/historico.json", { cache: "no-store" }).then((r) => r.json()).then((d) => {
      hist.datos = d; iniciarHistorico();
    }).catch(() => { document.getElementById("h-nota").textContent = "Todavía no hay datos históricos: se generan en la próxima corrida diaria."; });
  }

  function iniciarHistorico() {
    const S = hist.datos.series;
    const ley = document.getElementById("h-leyenda");
    SERIES.forEach(([k, nombre, col]) => {
      if (!S[k]) return;
      const b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-pressed", hist.activas.has(k));
      b.innerHTML = '<i class="sw"></i>'; b.querySelector("i").style.background = col; b.append(nombre);
      b.addEventListener("click", () => { hist.activas.has(k) ? hist.activas.delete(k) : hist.activas.add(k); b.setAttribute("aria-pressed", hist.activas.has(k)); dibujarHist(); });
      ley.appendChild(b);
    });
    document.querySelectorAll("[data-modo]").forEach((b) => b.addEventListener("click", () => { hist.modo = b.dataset.modo; dibujarHist(); }));
    document.querySelectorAll("[data-rango]").forEach((b) => b.addEventListener("click", () => { hist.rango = b.dataset.rango; dibujarHist(); }));
    tablaRetornos();
    ["h-graf", "h-brecha", "h-rp"].forEach((id) => new ResizeObserver(dibujarHist).observe(document.getElementById(id)));
    if (hist.datos.avisos?.length) document.getElementById("h-nota").textContent = "Sin datos: " + hist.datos.avisos.join(" · ");
  }

  const parse = (s) => s.map(([f, v]) => [new Date(f + "T12:00:00"), v]);
  function desdeRango() {
    const ult = new Date(hist.datos.series.a3500?.at(-1)?.[0] + "T12:00:00");
    if (hist.rango === "2025") return new Date("2025-01-02T00:00:00");
    const d = new Date(ult); d.setMonth(d.getMonth() - +hist.rango); return d;
  }

  function lineas(el, series, opts) {
    el.replaceChildren();
    if (!series.length || !series.some((s) => s.puntos.length)) return;
    const W = Math.max(300, el.clientWidth), H = opts.alto || 360, m = { t: 12, r: 120, b: 30, l: 60 };
    if (W < 520) m.r = 16;
    const todos = series.flatMap((s) => s.puntos);
    const x = d3.scaleUtc(d3.extent(todos, (p) => p[0]), [m.l, W - m.r]);
    const y = d3.scaleLinear(d3.extent(todos, (p) => p[1]), [H - m.b, m.t]).nice();
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", opts.titulo);
    svg.append("g").selectAll("line").data(y.ticks(5)).join("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y).attr("stroke", css("--grid"));
    const ax = (g) => { g.attr("font-size", null).attr("font-family", null); g.selectAll("text").attr("fill", css("--muted")).style("font-size", "11px"); g.selectAll("line,path").attr("stroke", css("--line")); };
    svg.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(Math.max(3, Math.floor(W / 110))).tickFormat(d3.utcFormat("%b %y"))).call(ax);
    svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(opts.fy)).call(ax).select(".domain").remove();
    const etiquetas = [];
    series.forEach((s) => {
      if (!s.puntos.length) return;
      svg.append("path").attr("d", d3.line((p) => x(p[0]), (p) => y(p[1]))(s.puntos)).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", 1.8).attr("stroke-linejoin", "round");
      const u = s.puntos.at(-1); etiquetas.push({ y: y(u[1]), t: `${s.nombre} ${opts.fy(u[1])}`, c: s.color });
    });
    if (m.r > 50) {
      etiquetas.sort((a, b) => a.y - b.y);
      etiquetas.forEach((e, i) => { if (i && e.y - etiquetas[i - 1].y < 12) e.y = etiquetas[i - 1].y + 12; });
      svg.append("g").selectAll("text").data(etiquetas).join("text").attr("x", W - m.r + 6).attr("y", (e) => e.y + 4).attr("fill", (e) => e.c).style("font-size", "10.5px").text((e) => e.t);
    }
    // tooltip con la fecha más cercana
    const fechas = Array.from(new Set(todos.map((p) => +p[0]))).sort((a, b) => a - b);
    const guia = svg.append("line").attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--line")).attr("opacity", 0);
    svg.append("rect").attr("x", m.l).attr("width", W - m.l - m.r).attr("height", H).attr("fill", "transparent")
      .on("pointermove", (ev) => {
        const [mx] = d3.pointer(ev); const t = +x.invert(mx);
        const f = fechas[Math.min(fechas.length - 1, d3.bisectLeft(fechas, t))];
        guia.attr("x1", x(f)).attr("x2", x(f)).attr("opacity", 1);
        tip.replaceChildren(); const b = document.createElement("b"); b.textContent = d3.utcFormat("%d/%m/%Y")(new Date(f)); tip.appendChild(b);
        series.forEach((s) => { const p = s.puntos.find((q) => +q[0] === f); if (!p) return; const d = document.createElement("div"); const sp = document.createElement("span"); sp.className = "k"; sp.textContent = s.nombre + " "; sp.style.color = s.color; d.append(sp, opts.fy(p[1])); tip.appendChild(d); });
        tip.hidden = false; const w = tip.offsetWidth; let left = ev.clientX + 14; if (left + w > innerWidth - 8) left = ev.clientX - w - 14;
        tip.style.left = `${Math.max(8, left)}px`; tip.style.top = `${Math.max(8, ev.clientY - 20)}px`;
      })
      .on("pointerleave", () => { tip.hidden = true; guia.attr("opacity", 0); });
  }

  function dibujarHist() {
    if (!hist.datos) return;
    document.querySelectorAll("[data-modo]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.modo === hist.modo));
    document.querySelectorAll("[data-rango]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.rango === hist.rango));
    const S = hist.datos.series, desde = desdeRango();
    const elegidas = SERIES.filter(([k]) => hist.activas.has(k) && S[k]).map(([k, nombreLargo, color, nombre]) => {
      let p = parse(S[k]).filter(([f]) => f >= desde);
      if (hist.modo !== "valores" && p.length) {
        const base = p[0][1];
        p = p.map(([f, v]) => [f, hist.modo === "base" ? (k === "tamar" ? v * 100 : 100 * v / base) : (k === "tamar" ? v - base : v / base - 1)]);
      }
      return { nombre: k === "tamar" && hist.modo === "base" ? "TAMAR %" : nombre, color, puntos: p };
    });
    const fy = hist.modo === "base" ? d3.format(",.0f") : hist.modo === "var" ? d3.format("+.0%") : d3.format(",.2~f");
    lineas(document.getElementById("h-graf"), elegidas, { fy, titulo: "Evolución comparada" });
    const mep = Object.fromEntries(S.mep || []), a35 = S.a3500 || [];
    const brecha = a35.filter(([f]) => mep[f] && new Date(f + "T12:00:00") >= desde).map(([f, v]) => [new Date(f + "T12:00:00"), mep[f] / v - 1]);
    lineas(document.getElementById("h-brecha"), [{ nombre: "Brecha", color: css("--s2"), puntos: brecha }], { fy: d3.format("+.1%"), alto: 240, titulo: "Brecha MEP / A3500" });
    lineas(document.getElementById("h-rp"), [{ nombre: "Riesgo país", color: css("--s1"), puntos: parse(S.riesgo_pais || []) }], { fy: d3.format(",.0f"), alto: 240, titulo: "Riesgo país desde 2024" });
  }

  function tablaRetornos() {
    const S = hist.datos.series, tb = document.querySelector("#h-tabla tbody");
    const ult = new Date(S.a3500?.at(-1)?.[0] + "T12:00:00");
    const hace = (meses) => { const d = new Date(ult); d.setMonth(d.getMonth() - meses); return d; };
    const cortes = [new Date("2025-01-02T00:00:00"), hace(12), hace(6), hace(1)];
    SERIES.forEach(([k, nombre]) => {
      if (!S[k] || k === "tamar") return;
      const p = parse(S[k]); const fin = p.at(-1)[1];
      const tr = document.createElement("tr");
      const td0 = document.createElement("td"); td0.className = "l"; td0.textContent = nombre; tr.appendChild(td0);
      cortes.forEach((c) => {
        const ini = p.find(([f]) => f >= c);
        const td = document.createElement("td");
        const v = ini ? fin / ini[1] - 1 : null; td.textContent = v == null ? "—" : d3.format("+.1%")(v);
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
  }
})();
