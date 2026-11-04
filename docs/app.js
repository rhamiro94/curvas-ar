/* Terminal de curvas: lee data/curvas.json (lo genera el proceso diario) y dibuja cada curva. */
(function () {
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const COLORES = ["--s1", "--s2"];
  const fmt = {
    pct: (v) => (v == null ? "—" : d3.format(".2%")(v)),
    pb: (v) => (v == null ? "—" : d3.format("+.0f")(v)),
    num2: (v) => (v == null ? "—" : d3.format(",.2f")(v)),
    num3: (v) => (v == null ? "—" : d3.format(",.3f")(v)),
    dias: (v) => (v == null ? "—" : d3.format("d")(v)),
    fecha: (v) => (v ? v.split("-").reverse().join("/") : "—"),
    txt: (v) => (v == null ? "—" : String(v)),
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
    resumen(datos);
    const cont = document.getElementById("curvas");
    datos.curvas.forEach((c) => cont.appendChild(seccion(c, datos)));
    document.getElementById("ver-ref").addEventListener("change", (e) => { estado.verRef = e.target.checked; redibujar(); });
    document.getElementById("ver-tend").addEventListener("change", (e) => { estado.verTend = e.target.checked; redibujar(); });
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }

  function redibujar() { document.querySelectorAll(".grafico").forEach((el) => el._dibujar && el._dibujar()); }

  /* ---------- resumen ---------- */
  function resumen(datos) {
    const box = document.getElementById("resumen");
    datos.curvas.forEach((c) => {
      const campoDelta = c.filas[0] && "delta_tem_pb" in c.filas[0] ? "delta_tem_pb" : "delta_pb";
      const deltas = c.filas.map((r) => r[campoDelta]).filter((v) => v != null);
      const prom = deltas.length ? d3.mean(deltas) : null;
      const largo = c.filas.reduce((m, r) => (r[c.x.campo] > (m?.[c.x.campo] ?? -Infinity) ? r : m), null);
      const t = document.createElement("a");
      t.className = "tile"; t.href = `#${c.id}`; t.style.textDecoration = "none"; t.style.color = "inherit";
      t.innerHTML = `<span class="tile-k"></span><span class="tile-v"></span><span class="tile-s"></span>`;
      t.querySelector(".tile-k").textContent = c.titulo.split(":")[0];
      const v = t.querySelector(".tile-v");
      v.textContent = prom == null ? "—" : `${fmt.pb(prom)} pb`;
      if (prom != null) v.classList.add(prom > 0 ? "up" : "down");
      t.querySelector(".tile-s").textContent =
        `Cambio promedio de ${c.y.etiqueta} en ${datos.dias_atras} días · ${c.filas.length} especies` +
        (largo ? ` · ${largo.ticker} ${fmt.pct(largo[c.y.campo])}` : "");
      box.appendChild(t);
    });
    const cer = datos.indices?.cer_t10;
    if (cer) {
      const t = document.createElement("div");
      t.className = "tile";
      t.innerHTML = `<span class="tile-k">CER T−10</span><span class="tile-v"></span><span class="tile-s"></span>`;
      t.querySelector(".tile-v").textContent = d3.format(",.4f")(cer.valor);
      t.querySelector(".tile-s").textContent = `Dato del ${fmt.fecha(cer.fecha)} para liquidación ${fmt.fecha(cer.liquidacion)}`;
      box.appendChild(t);
    }
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
    c.ajustes.filter((a) => a.serie === "hoy").forEach((a) => {
      const g = c.grupos.find((x) => x.id === a.grupo);
      const d = document.createElement("div");
      d.textContent = `${g ? g.etiqueta + ": " : ""}${c.y.etiqueta} = ${d3.format(".4f")(a.a)} ${a.b < 0 ? "−" : "+"} ${d3.format(".4f")(Math.abs(a.b))}·ln(x)   R² ${d3.format(".2f")(a.r2)}`;
      eq.appendChild(d);
    });

    const graf = s.querySelector(".grafico");
    graf._dibujar = () => grafico(graf, c, datos);
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
      c.ajustes.forEach((a) => {
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
})();
