/* Motor de cálculo para la web: mismas convenciones que src/curvas/motor.py
   (TIR efectiva anual, base actual/365, desde la fecha de liquidación). */
(function (raiz) {
  const DIA = 86400000;
  const fecha = (iso) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  const dias = (a, b) => Math.round((fecha(b) - fecha(a)) / DIA);

  function tir(precio, flujos, liq) {
    const fut = flujos.filter(([f]) => dias(liq, f) > 0).map(([f, m]) => [dias(liq, f) / 365, m]);
    if (!fut.length || !(precio > 0)) return null;
    const vp = (r) => fut.reduce((s, [t, m]) => s + m / Math.pow(1 + r, t), 0);
    let lo = -0.99, hi = 10;
    for (let i = 0; i < 200; i++) {
      const mid = (lo + hi) / 2;
      if (vp(mid) > precio) lo = mid; else hi = mid;
    }
    const r = (lo + hi) / 2;
    const pv = fut.map(([t, m]) => [t, m / Math.pow(1 + r, t)]);
    const total = pv.reduce((s, [, v]) => s + v, 0);
    const macaulay = pv.reduce((s, [t, v]) => s + t * v, 0) / total;
    const out = { tir: r, duration: macaulay, md: macaulay / (1 + r), dias: dias(liq, flujos[flujos.length - 1][0]) };
    if (fut.length === 1) {               // pago único: TEM y TNA como en LECAP / BONCAP
      out.tem = Math.pow(1 + r, 1 / 12) - 1;
      out.tna = out.tem * 12;
    }
    return out;
  }

  /* Precio que da una TIR objetivo (la inversa, para "¿a qué precio rinde X?") */
  function precioPara(tirObjetivo, flujos, liq) {
    return flujos.filter(([f]) => dias(liq, f) > 0)
      .reduce((s, [f, m]) => s + m / Math.pow(1 + tirObjetivo, dias(liq, f) / 365), 0);
  }

  const api = { tir, precioPara, dias };
  if (typeof module !== "undefined") module.exports = api; else raiz.Calc = api;
})(typeof window !== "undefined" ? window : globalThis);
