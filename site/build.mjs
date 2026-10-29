// Build the website into _site/: bundle the React app (esbuild), compile Tailwind, write the data of
// the interactive maps and the search index, and pre-render one HTML page per route, each with its
// own title, description, preview card and structured data.
//
//   node site/build.mjs                    # _site/ for https://<owner>.github.io/<repo>/ (project.yaml)
//   node site/build.mjs --base / --serve 8765   # preview at http://localhost:8765/
//   node site/build.mjs --full             # also copy every tracked file, as GitHub Pages deploys it
//
// Generic: the site's identity comes from project.yaml and site/src/content.js.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync, createReadStream, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { basename, dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as esbuild from 'esbuild';
import postcss from 'postcss';
import tailwindcss from 'tailwindcss';
import sharp from 'sharp';
import YAML from 'yaml';

const require = createRequire(import.meta.url);
const SITE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(SITE, '..');

// --------------------------------------------------------------------------- options
const argv = process.argv.slice(2);
const opt = (name, fallback) => { const i = argv.indexOf(`--${name}`); return i < 0 ? fallback : argv[i + 1]; };
const project = YAML.parse(readFileSync(join(ROOT, 'project.yaml'), 'utf8'));
const SITE_URL = project.website.endsWith('/') ? project.website : `${project.website}/`;
const BASE = opt('base', new URL(SITE_URL).pathname);
const OUT = resolve(opt('out', join(ROOT, '_site')));
const FULL = argv.includes('--full');
const SERVE = opt('serve', null);

const C = await import(pathToFileURL(join(SITE, 'src/content.js')));
const readJSON = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const write = (p, text) => { const f = join(OUT, p); mkdirSync(dirname(f), { recursive: true }); writeFileSync(f, text); };
const hash = (text) => createHash('sha256').update(text).digest('hex').slice(0, 10);
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const plain = (s) => String(s ?? '').replace(/`/g, '');
const itemPath = (item) => `${item.section}/${item.id}/`;

rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });

// --------------------------------------------------------------------------- static files
// --full reproduces the old "serve the repository" deployment, so URLs of data and docs keep working
if (FULL) {
  const files = execFileSync('git', ['ls-files', '-z'], { cwd: ROOT, encoding: 'utf8' }).split('\0').filter(Boolean);
  for (const f of files) {
    if (/^(site|\.github)\//.test(f) || ['index.html', '404.html', 'sitemap.xml'].includes(f)) continue;
    mkdirSync(dirname(join(OUT, f)), { recursive: true });
    cpSync(join(ROOT, f), join(OUT, f));
  }
} else {
  for (const p of ['images', 'metadata', 'robots.txt', 'site.webmanifest']) {
    if (existsSync(join(ROOT, p))) cpSync(join(ROOT, p), join(OUT, p), { recursive: true });
  }
}
writeFileSync(join(OUT, '.nojekyll'), '');

// --------------------------------------------------------------------------- metadata
const DATASETS = readJSON('metadata/index.json').datasets;
const PKG = Object.fromEntries(DATASETS.map((d) => [d, readJSON(`metadata/${d}.datapackage.json`)]));
const itemDatasets = (item) => (item.datasets || (item.dataset ? [item.dataset] : [])).filter((d) => PKG[d]);
const variables = (pkg) => pkg.resources[0].schema.fields.filter((f) => !f['geo:role']);

// --------------------------------------------------------------------------- data of the interactive maps
// One JSON per dataset: the units in a fixed order and, for every numeric variable, its values by year
const parseCSV = (text) => {
  const rows = []; let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const [head, ...body] = rows;
  return body.filter((r) => r.length === head.length).map((r) => Object.fromEntries(head.map((h, j) => [h, r[j]])));
};
const units = parseCSV(readFileSync(join(ROOT, 'geo/units.csv'), 'utf8'));
const mapData = {};
for (const d of DATASETS) {
  const pkg = PKG[d]; const res = pkg.resources[0];
  const scale = res['geo:scale'];
  const ids = units.filter((u) => u.scale === scale).map((u) => u.geo_id).sort();
  const index = Object.fromEntries(ids.map((id, i) => [id, i]));
  const rows = parseCSV(readFileSync(join(ROOT, res['geo:path']), 'utf8'));
  const vars = variables(pkg).filter((f) => f.type === 'number' || f.type === 'integer').map((f) => {
    const years = {};
    for (const r of rows) {
      if (r[f.name] === '' || r[f.name] === undefined || !(r.geo_id in index)) continue;
      const v = Number(r[f.name]);
      if (!Number.isFinite(v)) continue;
      (years[r.year] ||= Array(ids.length).fill(null))[index[r.geo_id]] = Number(v.toPrecision(6));
    }
    return { name: f.name, title: f.title, unit: f['geo:unit'] || '', years };
  }).filter((v) => Object.keys(v.years).length);
  mapData[d] = { dataset: d, title: pkg.title, scale, units: ids, variables: vars, default: pkg['geo:map'] || null };
  write(`assets/data/${d}.json`, JSON.stringify(mapData[d]));
}
for (const f of ['municipality.geojson', 'department.geojson', 'country.geojson']) {
  if (existsSync(join(SITE, 'data', f))) cpSync(join(SITE, 'data', f), join(OUT, 'assets/data', f));
}

// --------------------------------------------------------------------------- search index
write('assets/search.json', JSON.stringify(C.CONTENT_REGISTRY.map((item) => ({
  href: itemPath(item), type: item.type, subtype: item.subtype || '', title: item.title, summary: plain(item.summary),
  tags: item.tags || [], text: plain(item.description),
  variables: itemDatasets(item).flatMap((d) => variables(PKG[d]).map((f) => ({ name: f.name, title: f.title, dataset: d }))),
}))));

// --------------------------------------------------------------------------- JavaScript and CSS
const js = await esbuild.build({
  entryPoints: { app: join(SITE, 'src/app.jsx') },
  outdir: join(OUT, 'assets'), entryNames: '[name]-[hash]', chunkNames: 'chunk-[hash]',
  bundle: true, splitting: true, format: 'esm', target: 'es2020', minify: true, jsx: 'automatic',
  legalComments: 'linked', sourcemap: 'linked', metafile: true, logLevel: 'warning',
  define: {
    'process.env.NODE_ENV': '"production"',
    __SITE_CONFIG__: JSON.stringify(project.site || {}),
  },
});
const appJs = `assets/${basename(Object.entries(js.metafile.outputs).find(([, o]) => o.entryPoint && o.entryPoint.endsWith('src/app.jsx'))[0])}`;

const twConfig = require(join(SITE, 'tailwind.config.cjs'));
twConfig.content = [join(SITE, 'src/**/*.{js,jsx}'), join(SITE, 'template.html'), join(SITE, 'build.mjs')];
const { css } = await postcss([tailwindcss(twConfig)]).process(readFileSync(join(SITE, 'src/styles.css'), 'utf8'), { from: undefined });
const { code: cssMin } = await esbuild.transform(css, { loader: 'css', minify: true });
const appCss = `assets/app-${hash(cssMin)}.css`;
write(appCss, cssMin);
cpSync(join(dirname(require.resolve('leaflet')), 'leaflet.css'), join(OUT, 'assets/leaflet.css'));

// --------------------------------------------------------------------------- preview images
// A 1200 x 630 JPEG per item from its card, for link previews (WebP is not read everywhere)
const ogImage = {};
for (const item of C.CONTENT_REGISTRY) {
  if (!item.image || !existsSync(join(ROOT, item.image))) continue;
  const p = `assets/og/${item.id}.jpg`;
  mkdirSync(join(OUT, 'assets/og'), { recursive: true });
  await sharp(join(ROOT, item.image)).resize(1200, 630, { fit: 'cover' }).flatten({ background: '#071417' })
    .jpeg({ quality: 82, mozjpeg: true }).toFile(join(OUT, p));
  ogImage[item.id] = p;
}

// --------------------------------------------------------------------------- structured data
const ORG = `${SITE_URL}#org`;
const orgGraph = [
  { '@type': 'WebSite', '@id': `${SITE_URL}#website`, url: SITE_URL, name: C.SITE_NAME, alternateName: C.SHORT_NAME, inLanguage: 'en', publisher: { '@id': ORG } },
  {
    '@type': 'ResearchProject', '@id': ORG, name: C.SITE_NAME, alternateName: C.SHORT_NAME, url: SITE_URL,
    logo: `${SITE_URL}images/logo/emblem-512.png`, sameAs: [C.REPO_URL],
    member: C.PEOPLE.core.map((p) => ({ '@type': 'Person', name: p.name, affiliation: p.affiliation })),
  },
];
const period = (p) => String(p || '').replace(/[–-]/, '/');
const itemLD = (item) => {
  const url = SITE_URL + itemPath(item);
  const base = { '@id': `${url}#item`, url, name: item.title, description: plain(item.description || item.summary), keywords: item.tags, creator: { '@id': ORG } };
  if (item.type === 'indicator') {
    const pkgs = itemDatasets(item).map((d) => PKG[d]);
    return {
      '@type': 'Dataset', ...base, isAccessibleForFree: true,
      license: pkgs[0]?.licenses?.[0]?.path, temporalCoverage: period(item.period),
      spatialCoverage: { '@type': 'Place', name: project.country.name },
      variableMeasured: pkgs.flatMap((p) => variables(p).map((f) => f.title)).filter((t, i, a) => a.indexOf(t) === i).slice(0, 100),
    };
  }
  if (item.type === 'package') {
    const repo = (item.links || []).find((l) => l.kind === 'github');
    return { '@type': 'SoftwareSourceCode', ...base, programmingLanguage: 'Python', codeRepository: repo?.url };
  }
  if (item.type === 'notebook') return { '@type': 'LearningResource', ...base, learningResourceType: 'Jupyter notebook' };
  if (item.type === 'app') return { '@type': 'WebApplication', ...base, applicationCategory: 'Map', operatingSystem: 'Web browser' };
  if (item.type === 'insight') return { '@type': 'ScholarlyArticle', ...base, headline: item.title, sameAs: item.doi, datePublished: item.date };
  if (item.type === 'event') return { '@type': 'Event', ...base, startDate: item.date };
  return { '@type': 'CreativeWork', ...base };
};
const SECTION_LABEL = { indicators: 'Indicators', tools: 'Tools', insights: 'Insights', events: 'Events' };
const breadcrumb = (item) => ({
  '@type': 'BreadcrumbList', itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
    { '@type': 'ListItem', position: 2, name: SECTION_LABEL[item.section], item: `${SITE_URL}#${item.section}` },
    { '@type': 'ListItem', position: 3, name: item.title, item: SITE_URL + itemPath(item) },
  ],
});
const jsonLD = (graph) => JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }).replace(/</g, '\\u003c');

// --------------------------------------------------------------------------- crawlable fallbacks
const ul = (lis) => (lis.length ? `<ul>${lis.map((li) => `<li>${li}</li>`).join('')}</ul>` : '');
const a = (href, text) => `<a href="${esc(href)}">${esc(text)}</a>`;
const BY_SECTION = (section) => C.CONTENT_REGISTRY.filter((i) => i.section === section);
const homeFallback = () => [
  `<img src="images/logo/emblem-192.png" alt="${esc(C.SHORT_NAME)} emblem" width="72" height="72">`,
  `<h1 style="font-size:2.25rem;font-weight:800;margin:1rem 0">${esc(C.SITE_NAME)}</h1>`,
  `<p>${esc(C.SITE_DESCRIPTION)}</p>`,
  ...Object.entries(SECTION_LABEL).filter(([s]) => BY_SECTION(s).length).flatMap(([s, label]) => [
    `<h2>${esc(label)}</h2>`, ul(BY_SECTION(s).map((i) => `${a(itemPath(i), i.title)}: ${esc(plain(i.summary))}`)),
  ]),
  `<p>Data, code and documentation: ${a(C.REPO_URL, 'GitHub repository')}.</p>`,
].join('\n');
const itemFallback = (item) => {
  const pkgs = itemDatasets(item).map((d) => PKG[d]);
  return [
    `<p>${a('./', C.SITE_NAME)} / ${a(`./#${item.section}`, SECTION_LABEL[item.section])}</p>`,
    `<h1 style="font-size:2.25rem;font-weight:800;margin:1rem 0">${esc(item.title)}</h1>`,
    `<p>${esc(plain(item.summary))}</p>`,
    item.description ? `<p>${esc(plain(item.description))}</p>` : '',
    item.citation ? `<p>${esc(item.citation)} ${a(item.doi, item.doi)}</p>` : '',
    ul((item.links || []).map((l) => a(l.url, l.label))),
    ...pkgs.flatMap((p) => [
      `<h2>Variables of ${esc(p.name)}</h2>`,
      ul(variables(p).map((f) => `<code>${esc(f.name)}</code>: ${esc(f.title)}. ${esc(plain(f.description))}`)),
      '<h2>Sources</h2>', ul((p.sources || []).map((s) => `${esc(s.title)}${s.path ? ` ${a(s.path, s.path)}` : ''}`)),
    ]),
    `<p>${a('./', `Back to the ${C.SITE_NAME}`)}</p>`,
  ].filter(Boolean).join('\n');
};

// --------------------------------------------------------------------------- pages
const template = readFileSync(join(SITE, 'template.html'), 'utf8');
const page = (p) => {
  const fields = {
    BASE, TITLE: p.title, DESCRIPTION: p.description, URL: p.url, OG_TYPE: p.ogType || 'website',
    OG_TITLE: p.ogTitle || p.title, OG_DESCRIPTION: p.description, OG_IMAGE: SITE_URL + p.image, OG_IMAGE_ALT: p.imageAlt || '',
    SHORT_NAME: C.SHORT_NAME, REPO_URL: C.REPO_URL, APP_JS: appJs, APP_CSS: appCss,
  };
  let html = template.replace(/\{\{(\w+)\}\}/g, (m, k) => (k in fields ? esc(fields[k]) : m));
  const raw = {
    JSONLD: p.jsonld, FALLBACK: p.fallback, BOOT: p.boot || '', PRELOAD: p.preload || '',
    ROBOTS: p.noindex ? '<meta name="robots" content="noindex">' : '',
  };
  return html.replace(/\{\{(\w+)\}\}/g, (m, k) => (k in raw ? raw[k] : m));
};
const indicatorItems = C.CONTENT_REGISTRY.filter((i) => i.type === 'indicator');
write('index.html', page({
  title: C.DEFAULT_TITLE, ogTitle: C.SITE_NAME, description: C.SITE_DESCRIPTION, url: SITE_URL,
  image: 'images/og-image.jpg', imageAlt: `${C.SITE_NAME}: satellite view of Bolivia`,
  jsonld: jsonLD([...orgGraph, ...C.CONTENT_REGISTRY.filter((i) => ['indicator', 'package'].includes(i.type)).map(itemLD)]),
  fallback: homeFallback(), boot: '<div class="boot-hero" aria-hidden="true"></div>',
  preload: '<link rel="preload" as="image" href="images/hero-day.webp">',
}));
for (const item of C.CONTENT_REGISTRY) {
  write(`${itemPath(item)}index.html`, page({
    title: `${item.title} | ${C.SHORT_NAME}`, ogTitle: item.title, description: plain(item.summary),
    url: SITE_URL + itemPath(item), ogType: item.type === 'insight' ? 'article' : 'website',
    image: ogImage[item.id] || 'images/og-image.jpg', imageAlt: item.imageAlt,
    jsonld: jsonLD([...orgGraph, itemLD(item), breadcrumb(item)]), fallback: itemFallback(item),
    // The page's largest image (an indicator's map, else the item's picture) is found before the app runs
    preload: (item.map || item.image) ? `<link rel="preload" as="image" href="${esc(item.map || item.image)}" fetchpriority="high">` : '',
  }));
}
// Retired pages send visitors and search engines to the page that replaced them
for (const [from, to] of Object.entries(C.REDIRECTS || {})) {
  write(`${from}/index.html`, `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved</title>
<meta name="robots" content="noindex"><link rel="canonical" href="${esc(SITE_URL + to)}/">
<meta http-equiv="refresh" content="0; url=${esc(BASE + to)}/">
<script>location.replace(${JSON.stringify(BASE + to + '/')} + location.hash)</script>
</head><body><p><a href="${esc(BASE + to)}/">This page has moved.</a></p></body></html>
`);
}
// Unknown paths: GitHub Pages serves 404.html, and the app shows its "not found" page there
write('404.html', page({
  title: `Page not found | ${C.SHORT_NAME}`, description: C.SITE_DESCRIPTION, url: SITE_URL, image: 'images/og-image.jpg',
  jsonld: jsonLD(orgGraph), noindex: true,
  fallback: `<h1>Page not found</h1><p>${a('./', `Back to the ${C.SITE_NAME}`)}</p>`,
}));

const today = new Date().toISOString().slice(0, 10);
const lastmod = (item) => itemDatasets(item).map((d) => PKG[d]['geo:updated']).filter(Boolean).sort().pop() || item.date;
write('sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${SITE_URL}</loc><lastmod>${today}</lastmod><priority>1.0</priority></url>
${C.CONTENT_REGISTRY.map((i) => `  <url><loc>${SITE_URL}${itemPath(i)}</loc><lastmod>${lastmod(i)}</lastmod></url>`).join('\n')}
</urlset>
`);

console.log(`Built ${C.CONTENT_REGISTRY.length + 2} pages, ${DATASETS.length} map datasets and the search index into ${OUT} (base ${BASE})`);

// --------------------------------------------------------------------------- preview server
if (SERVE) {
  const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
    '.geojson': 'application/geo+json', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
    '.xml': 'application/xml', '.txt': 'text/plain', '.webmanifest': 'application/manifest+json' };
  createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (!p.startsWith(BASE)) p = BASE;
    let f = join(OUT, p.slice(BASE.length));
    if (existsSync(f) && statSync(f).isDirectory()) f = join(f, 'index.html');
    const found = existsSync(f) && f.startsWith(OUT);
    res.writeHead(found ? 200 : 404, { 'Content-Type': TYPES[found ? extname(f) : '.html'] || 'application/octet-stream' });
    createReadStream(found ? f : join(OUT, '404.html')).pipe(res);
  }).listen(Number(SERVE), '127.0.0.1', () => console.log(`Preview: http://localhost:${SERVE}${BASE}`));
}
