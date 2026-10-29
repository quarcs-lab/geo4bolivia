// Interactive indicator map (Leaflet), loaded only on indicator pages. It draws the dataset's values
// (assets/data/<dataset>.json, written by site/build.mjs from data/) on geoBoundaries' public-domain
// municipalities (assets/data/municipality.geojson, written by scripts/web_boundaries.py), in five
// Fisher-Jenks classes over the keyless basemap of project.yaml's `site` block.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { MAP_VIEW } from './content.js';

const SITE = __SITE_CONFIG__;   // project.yaml `site`, injected by the build
const COLORS = { background: '#071417', no_data: '#5c6b6a', classes: ['#1f8a80', '#ec8f99', '#ffd9de'], ...(SITE.colors || {}) };
const BASEMAP = SITE.basemap || {};
const BOUNDARY_CREDIT = 'Boundaries: <a href="https://www.geoboundaries.org" target="_blank" rel="noopener noreferrer">geoBoundaries</a> (GeoBolivia, public domain)';
const N_CLASSES = 5;

const cache = {};
const getJSON = (url) => cache[url] || (cache[url] = fetch(url).then((r) => {
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}).catch((err) => { delete cache[url]; throw err; }));

// Fisher-Jenks natural breaks: the upper bound of each of k classes (exact, O(k n²); n is a few hundred)
const jenks = (values, k) => {
  const x = [...values].sort((a, b) => a - b);
  const n = x.length;
  if (n <= k) return x;
  const lower = Array.from({ length: n + 1 }, () => Array(k + 1).fill(0));
  const cost = Array.from({ length: n + 1 }, () => Array(k + 1).fill(Infinity));
  for (let j = 1; j <= k; j++) { lower[1][j] = 1; cost[1][j] = 0; }
  for (let l = 2; l <= n; l++) {
    let s = 0, s2 = 0, w = 0;
    for (let m = 1; m <= l; m++) {
      const i = l - m + 1, v = x[i - 1];
      s += v; s2 += v * v; w += 1;
      const variance = s2 - (s * s) / w;
      if (i > 1) for (let j = 2; j <= k; j++) {
        if (cost[l][j] >= variance + cost[i - 1][j - 1]) { lower[l][j] = i; cost[l][j] = variance + cost[i - 1][j - 1]; }
      }
    }
    lower[l][1] = 1; cost[l][1] = s2 - (s * s) / w;
  }
  const breaks = Array(k).fill(0);
  let end = n;
  for (let j = k; j >= 1; j--) { breaks[j - 1] = x[end - 1]; end = lower[end][j] - 1; }
  return breaks;
};

// Colours of k classes, interpolated along a list of colours (low ... high)
const hex = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
const ramp = (anchors, k) => Array.from({ length: k }, (_, i) => {
  const t = (i / (k - 1)) * (anchors.length - 1), a = Math.floor(t), f = t - a;
  const [c0, c1] = [hex(anchors[a]), hex(anchors[Math.min(a + 1, anchors.length - 1)])];
  return `#${c0.map((v, j) => Math.round(v + (c1[j] - v) * f).toString(16).padStart(2, '0')).join('')}`;
});
const PALETTE = COLORS.ramp && COLORS.ramp.length === N_CLASSES ? COLORS.ramp : ramp(COLORS.classes, N_CLASSES);

const fmt = (v) => {
  if (v === null || v === undefined) return 'No data';
  const a = Math.abs(v);
  if (a >= 1000) return Math.round(v).toLocaleString('en-US');
  if (a >= 100) return v.toFixed(1);
  if (a >= 1) return v.toFixed(2);
  return String(Number(v.toPrecision(3)));
};

const useMapData = (dataset) => {
  const [state, setState] = useState({ status: 'loading' });
  useEffect(() => {
    let live = true;
    setState({ status: 'loading' });
    Promise.all([getJSON(`assets/data/${dataset}.json`), getJSON('assets/data/municipality.geojson'), getJSON('assets/data/department.geojson')])
      .then(([data, units, departments]) => { if (live) setState({ status: 'ready', data, units, departments }); })
      .catch(() => { if (live) setState({ status: 'error' }); });
    return () => { live = false; };
  }, [dataset]);
  return state;
};

const Select = ({ id, label, value, onChange, options, disabled }) => (
  <label htmlFor={id} className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wider text-salt-400 min-w-0">
    {label}
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}
            className="w-full rounded-lg bg-lagoon-900 border border-white/15 px-3 py-2 text-sm font-normal normal-case tracking-normal text-salt-100 disabled:opacity-70 focus:border-brand-turquoise">
      {options.map(([v, text]) => <option key={v} value={v}>{text}</option>)}
    </select>
  </label>
);

export default function IndicatorMap({ datasets, id = 'map' }) {
  const [dataset, setDataset] = useState(datasets[0]);
  const state = useMapData(dataset);
  const [choice, setChoice] = useState({ variable: null, year: null });
  const el = useRef(null);
  const leaflet = useRef(null);
  const current = useRef({});

  // The dataset's headline variable and year by default
  const data = state.status === 'ready' ? state.data : null;
  const variable = data && (data.variables.find((v) => v.name === choice.variable)
    || data.variables.find((v) => v.name === data.default?.variable) || data.variables[0]);
  const years = variable ? Object.keys(variable.years).sort() : [];
  const year = years.includes(String(choice.year)) ? String(choice.year)
    : years.includes(String(data?.default?.year)) && variable?.name === data?.default?.variable ? String(data.default.year) : years[years.length - 1];

  // Values by geo_id, classes and legend for the chosen variable and year
  const view = useMemo(() => {
    if (!variable || !year) return null;
    const values = Object.fromEntries(data.units.map((u, i) => [u, variable.years[year][i]]));
    const present = Object.values(values).filter((v) => v !== null);
    const positive = present.every((v) => v > 0);
    const sorted = [...present].sort((a, b) => a - b);
    const skewed = positive && sorted[sorted.length - 1] / sorted[Math.floor(sorted.length / 2)] > 20;
    const scale = skewed ? Math.log : (v) => v;   // classify very skewed positive values (e.g. density) on logs
    const breaks = jenks(present.map(scale), Math.min(N_CLASSES, new Set(present).size)).map((b) => (skewed ? Math.exp(b) : b));
    const classOf = (v) => (v === null ? -1 : breaks.findIndex((b) => v <= b * (1 + 1e-9)));
    const counts = breaks.map((_, i) => present.filter((v) => classOf(v) === i).length);
    const ranked = data.units.filter((u) => values[u] !== null).sort((a, b) => values[b] - values[a]);
    const colors = breaks.length === N_CLASSES ? PALETTE : ramp(COLORS.ramp || COLORS.classes, Math.max(breaks.length, 2));
    return { values, breaks, counts, classOf, colors, ranked, min: sorted[0], max: sorted[sorted.length - 1], missing: data.units.length - present.length, skewed };
  }, [data, variable, year]);
  current.current = { view, variable, year };

  // Create the map once the boundaries are in
  useEffect(() => {
    if (state.status !== 'ready' || leaflet.current || !el.current) return undefined;
    if (!document.querySelector('link[data-leaflet]')) {
      const link = Object.assign(document.createElement('link'), { rel: 'stylesheet', href: 'assets/leaflet.css' });
      link.dataset.leaflet = '';
      document.head.appendChild(link);
    }
    const map = L.map(el.current, { center: MAP_VIEW.center, zoom: MAP_VIEW.zoom, minZoom: 4, maxZoom: 11, zoomSnap: 0.5, scrollWheelZoom: false, attributionControl: false });
    L.control.attribution({ prefix: false }).addAttribution([BOUNDARY_CREDIT, BASEMAP.attribution].filter(Boolean).join(' · ')).addTo(map);
    map.createPane('labels').style.zIndex = 650;
    map.getPane('labels').style.pointerEvents = 'none';
    if (BASEMAP.base) L.tileLayer(BASEMAP.base, { maxZoom: 16 }).addTo(map);
    if (BASEMAP.labels) L.tileLayer(BASEMAP.labels, { maxZoom: 16, pane: 'labels' }).addTo(map);
    const style = (f) => {
      const { view: v } = current.current;
      const c = v ? v.classOf(v.values[f.properties.geo_id]) : -1;
      return { color: COLORS.background, weight: 0.5, fillOpacity: 0.85, fillColor: c < 0 ? COLORS.no_data : v.colors[c] };
    };
    const units = L.geoJSON(state.units, {
      style,
      onEachFeature: (f, layer) => {
        layer.bindTooltip(() => {
          const { view: v, variable: va, year: y } = current.current;
          const name = String(f.properties.name).replace(/</g, '&lt;');
          return `<strong>${name}</strong><br>${va ? `${va.title.replace(/</g, '&lt;')} (${y}): ${fmt(v.values[f.properties.geo_id])}` : ''}`;
        }, { sticky: true, className: 'gdo-tooltip', direction: 'top', offset: [0, -8] });
        layer.on({ mouseover: () => layer.setStyle({ weight: 2, color: '#ffffff' }), mouseout: () => units.resetStyle(layer) });
      },
    }).addTo(map);
    L.geoJSON(state.departments, { interactive: false, style: { color: '#e3ecea', weight: 1.2, opacity: 0.7, fill: false } }).addTo(map);
    map.fitBounds(units.getBounds(), { padding: [8, 8] });
    leaflet.current = { map, units, style };
    return undefined;
  }, [state.status]);

  useEffect(() => () => { if (leaflet.current) { leaflet.current.map.remove(); leaflet.current = null; } }, []);
  useEffect(() => { if (leaflet.current) leaflet.current.units.setStyle(leaflet.current.style); }, [view]);

  const pick = (key) => (value) => setChoice((c) => ({ ...c, [key]: value }));
  const nameOf = useMemo(() => Object.fromEntries((state.units?.features || []).map((f) => [f.properties.geo_id, f.properties.name])), [state.units]);
  const unit = variable?.unit && !variable.title.includes(variable.unit) ? ` (${variable.unit})` : '';

  return (
    <div>
      <div className={`grid grid-cols-1 gap-3 mb-4 ${datasets.length > 1 ? 'sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_8rem]' : 'sm:grid-cols-[minmax(0,1fr)_8rem]'}`}>
        {datasets.length > 1 && <Select id={`${id}-dataset`} label="Dataset" value={dataset} onChange={(d) => { setDataset(d); setChoice({ variable: null, year: null }); }} options={datasets.map((d) => [d, d])} />}
        <Select id={`${id}-variable`} label="Variable" value={variable?.name || ''} onChange={(v) => setChoice({ variable: v, year: null })}
                options={(data?.variables || []).map((v) => [v.name, `${v.title} (${v.name})`])} disabled={!data} />
        <Select id={`${id}-year`} label="Year" value={year || ''} onChange={pick('year')} options={years.map((y) => [y, y])} disabled={years.length < 2} />
      </div>
      <div className="relative rounded-xl overflow-hidden border border-white/10 bg-lagoon-900">
        <div ref={el} role="region" aria-label={variable ? `Interactive map of ${variable.title} in ${year} by municipality` : 'Interactive map'}
             aria-describedby={`${id}-summary`} className="h-[420px] sm:h-[520px] w-full" />
        {state.status !== 'ready' && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-salt-400 p-6 text-center" role={state.status === 'error' ? 'alert' : 'status'}>
            {state.status === 'error' ? 'The map could not be loaded.' : 'Loading the map…'}
          </p>
        )}
      </div>
      {view && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-6 text-sm">
          <div>
            <p id={`${id}-summary`} className="text-salt-300 mb-3">
              {variable.title}{unit}, {year}: {fmt(view.min)} to {fmt(view.max)} across {data.units.length - view.missing} municipalities
              {view.missing > 0 && `, ${view.missing} without data`}. Hover over or tap a municipality for its value.
            </p>
            <ul className="space-y-1.5" aria-label="Legend">
              {view.breaks.map((b, i) => (
                <li key={i} className="flex items-center gap-2 text-salt-300">
                  <span className="w-5 h-3.5 rounded-sm flex-shrink-0" style={{ background: view.colors[i] }} aria-hidden="true"></span>
                  {fmt(i === 0 ? view.min : view.breaks[i - 1])} – {fmt(b)} <span className="text-salt-400">({view.counts[i]})</span>
                </li>
              ))}
              {view.missing > 0 && (
                <li className="flex items-center gap-2 text-salt-300">
                  <span className="w-5 h-3.5 rounded-sm flex-shrink-0" style={{ background: COLORS.no_data }} aria-hidden="true"></span>No data <span className="text-salt-400">({view.missing})</span>
                </li>
              )}
            </ul>
            <p className="text-xs text-salt-400 mt-3">Fisher–Jenks natural breaks{view.skewed ? ', computed on logs because the values are very skewed' : ''}. Holes are salt flats and lakes outside any municipality.</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[['Highest', view.ranked.slice(0, 5)], ['Lowest', view.ranked.slice(-5).reverse()]].map(([label, list]) => (
              <div key={label}>
                <h3 className="text-xs font-bold uppercase tracking-widest text-salt-400 mb-2">{label}</h3>
                <ol className="space-y-1 text-salt-300">
                  {list.map((u) => <li key={u} className="flex justify-between gap-2"><span className="truncate">{nameOf[u] || u}</span><span className="font-mono text-xs text-salt-200">{fmt(view.values[u])}</span></li>)}
                </ol>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
