/**
 * =================================================================================
 * Exploring regional development in Bolivia: A view from outer space (2013-2019)
 * =================================================================================
 * * OVERVIEW:
 * This script visualizes socio-economic and environmental dynamics in Bolivia 
 * (2013-2019) using a split-panel architecture.
 * * * FEATURES:
 * 1. Spatial Clipping: Analysis restricted to Bolivia (LSIB Boundary).
 * 2. Split-Panel: Side-by-side comparison of 2013 vs 2019.
 * 3. Interactive Inspector: Click to calculate pixel-level changes.
 * 4. Contextual Metadata: Full data dictionary and usage instructions.
 * =================================================================================
 */

ui.root.clear();

// =======================================================
// SECTION 0: SPATIAL DEFINITIONS (ROI)
// =======================================================

// Define the Region of Interest (ROI) - Bolivia
var country = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
  .filter(ee.Filter.eq('country_na', 'Bolivia'));

// Standardize the visualization geometry
var roi = country.geometry();


// =======================================================
// SECTION 1: MAP SETUP (SPLIT VIEW)
// =======================================================

var mapLeft = ui.Map();
var mapRight = ui.Map();

// 'HYBRID' provides Satellite imagery + Labels (Roads, Cities)
mapLeft.setOptions('HYBRID');
mapRight.setOptions('HYBRID');

mapLeft.setControlVisibility(true);
mapRight.setControlVisibility(true);

// --- RESTORED: ENABLE DRAWING TOOLS ---
mapLeft.drawingTools().setShown(true);
mapRight.drawingTools().setShown(true);

mapLeft.style().set({cursor: 'crosshair'});
mapRight.style().set({cursor: 'crosshair'});

var linker = ui.Map.Linker([mapLeft, mapRight]);

// STARTUP: Focus on Bolivia
mapLeft.centerObject(roi, 6);

var splitMap = ui.SplitPanel({
  firstPanel: mapLeft,
  secondPanel: mapRight,
  wipe: true,
  style: {stretch: 'both'}
});

var mapContainer = ui.Panel({
  widgets: [splitMap],
  layout: ui.Panel.Layout.flow('vertical'),
  style: {stretch: 'both'}
});


// =======================================================
// SECTION 2: SIDEBAR & CONTROLS (FULL CONTENT)
// =======================================================

var sidebar = ui.Panel({
  style: {width: '400px', padding: '15px', backgroundColor: '#ffffff'}
});

ui.root.add(ui.SplitPanel(sidebar, mapContainer));

// --- Header ---
sidebar.add(ui.Label({
  value: '🇧🇴 Exploring regional development in Bolivia: A view from outer space',
  style: {fontSize: '24px', fontWeight: 'bold', color: '#2c3e50', margin: '0 0 5px 0'}
}));

sidebar.add(ui.Label({
  value: 'Population, Nightlights, Landcover, and GDP (2013-2019)',
  style: {fontSize: '14px', fontWeight: 'bold', color: '#7f8c8d', margin: '0 0 15px 0'}
}));

// --- Context ---
sidebar.add(ui.Label({
  value: 'Geospatial development is a complex interplay between people, economic activity, and the environment. ' +
         'This tool restricts analysis to the Bolivian administrative boundary to explore these dynamics.',
  style: {fontSize: '13px', color: '#555', margin: '10px 0 15px 0'}
}));

// --- RESTORED: INSTRUCTIONS ---
sidebar.add(ui.Label({
  value: 'How to use the app:',
  style: {fontSize: '14px', fontWeight: 'bold', color: '#2980b9', margin: '10px 0 5px 0'}
}));

sidebar.add(ui.Label({
  value: '1. SELECT A LAYER: Use the dropdown to visualize Population, Lights, Land, GDP, or "None" to see the base map.\n' +
         '2. COMPARE YEARS: Drag the central slider left or right to see changes from 2013 to 2019.\n' +
         '3. INSPECT DATA: Click anywhere on the LEFT map within Bolivia to generate a detailed change report.',
  style: {fontSize: '13px', color: '#555', whiteSpace: 'pre-wrap', margin: '0 0 15px 0'}
}));

// --- LAYER SELECTOR WIDGET ---
var layerSelect = ui.Select({
  items: [
    {label: 'None (Satellite View)', value: 'none'},
    {label: 'Population Density', value: 'pop'},
    {label: 'Nighttime Lights', value: 'ntl'},
    {label: 'Land Cover (IGBP)', value: 'lc'},
    {label: 'GDP Estimate', value: 'gdp'}
  ],
  value: 'pop',
  onChange: function(value) {
    updateMapLayers(value);
  },
  style: {width: '95%', margin: '10px 0'}
});

sidebar.add(ui.Label({value: 'Select Visualization Layer:', style: {fontWeight: 'bold'}}));
sidebar.add(layerSelect);
sidebar.add(ui.Label('___________________________________________________'));

// --- INSPECTOR PANEL ---
var resultsPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f9f9f9', border: '1px solid #ccc', margin: '0 0 15px 0'}
});
var resultsLabel = ui.Label({
  value: 'Click on the LEFT map within Bolivia to inspect...',
  style: {fontWeight: 'bold', color: '#555'}
});
resultsPanel.add(resultsLabel);
sidebar.add(resultsPanel);

// --- RESTORED: DATA DICTIONARY ---
sidebar.add(ui.Label({value: 'Data Dictionary & Sources:', style: {fontWeight: 'bold', fontSize: '14px', color: '#2c3e50'}}));

// Helper function
function addLayerInfo(title, provider, dataset, res, desc, method) {
  sidebar.add(ui.Label({value: title, style: {fontSize: '15px', fontWeight: 'bold', margin: '12px 0 2px 0', color: '#2980b9'}}));
  sidebar.add(ui.Label({value: 'Provider: ' + provider, style: {fontSize: '11px', color: '#333', margin: '0 0 1px 0'}}));
  sidebar.add(ui.Label({value: 'Dataset: ' + dataset, style: {fontSize: '11px', color: '#777', margin: '0 0 1px 0', fontStyle: 'italic'}}));
  sidebar.add(ui.Label({value: 'Resolution: ' + res, style: {fontSize: '11px', fontWeight: 'bold', margin: '0 0 2px 0'}}));
  sidebar.add(ui.Label({value: 'Method: ' + method, style: {fontSize: '10px', color: '#555', margin: '0 0 2px 0'}}));
  sidebar.add(ui.Label({value: desc, style: {fontSize: '12px', margin: '0 0 5px 0'}}));
}

addLayerInfo(
  '1. Population Density', 
  'WorldPop Global Project', 
  'Global 100m Population Counts', 
  '~100m (3 arc-seconds)', 
  'Estimated number of people per grid cell.',
  'Random Forest Disaggregation'
);

addLayerInfo(
  '2. Nighttime Lights', 
  'NOAA / NASA', 
  'VIIRS Day/Night Band (DNB)', 
  '~500m (15 arc-seconds)', 
  'Measures average radiance (nanoWatts/cm²/sr).',
  'Monthly Cloud-Free Composites'
);

addLayerInfo(
  '3. Land Cover', 
  'NASA LP DAAC', 
  'MODIS MCD12Q1 V6.1', 
  '~500m (15 arc-seconds)', 
  'Classifies land surface into 17 IGBP categories.',
  'Supervised Decision Tree'
);

addLayerInfo(
  '4. GDP Estimate', 
  'Chen et al. (2022) / Scientific Data', 
  'Global Gridded GDP (PPP) Data', 
  '~1km (30 arc-seconds)', 
  'Gross Domestic Product per capita (PPP, USD).',
  'Ensemble Trees Downscaling'
);

sidebar.add(ui.Label('___________________________________________________'));

// --- RESTORED: CITATION ---
sidebar.add(ui.Label({
  value: 'Mendez (2026) Exploring Regional Development from Outer Space. Web application.',
  style: {fontSize: '11px', color: '#999', margin: '20px 0 0 0', fontStyle: 'italic'}
}));


// =======================================================
// SECTION 3: DATA PROCESSING
// =======================================================

function getLayerStack(year) {
  var startDate = ee.Date.fromYMD(year, 1, 1);
  var endDate = startDate.advance(1, 'year');

  var pop = ee.ImageCollection("WorldPop/GP/100m/pop")
    .filterBounds(roi)
    .filterDate(startDate, endDate)
    .select('population')
    .mosaic()
    .clip(roi) 
    .rename('pop');

  var ntlCol = ee.ImageCollection("NOAA/VIIRS/DNB/ANNUAL_V21")
    .filterBounds(roi)
    .filterDate(startDate, endDate)
    .select('average');
    
  var ntl = ee.Image(ee.Algorithms.If(
    ntlCol.size().gt(0), ntlCol.first(), ee.Image.constant(0).rename('average')
  )).clip(roi).rename('ntl');

  var lcCol = ee.ImageCollection('MODIS/061/MCD12Q1')
    .filterBounds(roi)
    .filterDate(startDate, endDate)
    .select('LC_Type1');
     
  var lc = ee.Image(ee.Algorithms.If(
    lcCol.size().gt(0), lcCol.first(), ee.Image.constant(0).rename('LC_Type1')
  )).clip(roi).rename('lc');

  var gdpCol = ee.ImageCollection("projects/sat-io/open-datasets/GRIDDED_EC-GDP")
    .filterBounds(roi)
    .filterDate(startDate, endDate)
    .select('b1');
     
  var gdp = ee.Image(ee.Algorithms.If(
    gdpCol.size().gt(0), gdpCol.first(), ee.Image.constant(0).rename('b1')
  )).clip(roi).rename('gdp');
     
  var combined = ee.Image.cat([pop, ntl, lc, gdp]);

  return { pop: pop, ntl: ntl, lc: lc, gdp: gdp, combined: combined };
}

var dataStart = getLayerStack(2013);
var dataEnd = getLayerStack(2019);


// =======================================================
// SECTION 4: VISUALIZATION (FIXED LEGENDS)
// =======================================================

var vizParams = {
  'pop': {min: 0, max: 10, palette: ['24123c','4d186e','822681','b73779','eb5760','fbb45d','fcfdbf']},
  'ntl': {min: 0, max: 60, palette: ['black', 'blue', 'purple', 'cyan', 'white']},
  'lc': {min: 1, max: 17, palette: ['05450a','086a10','54a708','78d203','009900','c6b044','dcd159','dade48','fbff13','b6ff05','27ff87','c24f44','a5a5a5','ff6d4c','69fff8','f9ffa4','1c0dff']},
  'gdp': {min: 0, max: 100, palette: ['0d0887','6a00a8','b12a90','e16462','fca636','f0f921']}
};

var layerNames = {
  'none': 'Satellite View',
  'pop': 'Population',
  'ntl': 'Night Lights',
  'lc':  'Land Cover',
  'gdp': 'GDP Estimate'
};

function updateMapLayers(layerType) {
  mapLeft.layers().reset();
  mapRight.layers().reset();
  mapLeft.widgets().reset();
  mapRight.widgets().reset();

  var borderImg = ee.Image().paint(country, 2, 2);
  var borderStyle = {palette: 'white'};
  
  var borderLeft = ui.Map.Layer(borderImg, borderStyle, 'Bolivia Border');
  var borderRight = ui.Map.Layer(borderImg, borderStyle, 'Bolivia Border');
  
  mapLeft.layers().add(borderLeft);
  mapRight.layers().add(borderRight);

  if (layerType !== 'none') {
    var imgStart = dataStart[layerType];
    var imgEnd = dataEnd[layerType];
    var params = vizParams[layerType];

    mapLeft.addLayer(imgStart, params, '2013 ' + layerNames[layerType]);
    mapRight.addLayer(imgEnd, params, '2019 ' + layerNames[layerType]);
  }

  // --- RESTORED: DISTINCT LABEL POSITIONS ---
  var prettyName = layerNames[layerType];
  var labelLeft = (layerType === 'none') ? prettyName : '2013 ' + prettyName;
  var labelRight = (layerType === 'none') ? prettyName : '2019 ' + prettyName;

  var styleLeft = {
    fontWeight: 'bold', fontSize: '16px', 
    backgroundColor: 'rgba(255,255,255,0.7)', 
    position: 'bottom-left', padding: '4px'
  };

  // Right label goes to bottom-right to avoid slider overlap
  var styleRight = {
    fontWeight: 'bold', fontSize: '16px', 
    backgroundColor: 'rgba(255,255,255,0.7)', 
    position: 'bottom-right', padding: '4px'
  };

  mapLeft.add(ui.Label({value: labelLeft, style: styleLeft}));
  mapRight.add(ui.Label({value: labelRight, style: styleRight}));
}

updateMapLayers('pop');


// =======================================================
// SECTION 5: INSPECTOR LOGIC
// =======================================================

mapLeft.onClick(function(coords) {
  resultsPanel.clear();
  resultsPanel.add(ui.Label('Computing Change...'));
    
  var point = ee.Geometry.Point(coords.lon, coords.lat);
    
  var check = country.filterBounds(point);
  
  check.size().evaluate(function(size) {
    if (size === 0) {
      resultsPanel.clear();
      resultsPanel.add(ui.Label({
        value: '❌ Selected point is outside Bolivia.\nPlease click inside the country borders.',
        style: {color: 'red', fontWeight: 'bold'}
      }));
      return; 
    }

    var dotLeft = ui.Map.Layer(point, {color: 'FF0000'}, 'Selected');
    var dotRight = ui.Map.Layer(point, {color: 'FF0000'}, 'Selected');
    
    mapLeft.layers().set(2, dotLeft);
    mapRight.layers().set(2, dotRight);

    var combinedStart = dataStart.combined.select(['pop', 'ntl', 'gdp'], ['pop_start', 'ntl_start', 'gdp_start']);
    var combinedEnd = dataEnd.combined.select(['pop', 'ntl', 'gdp'], ['pop_end', 'ntl_end', 'gdp_end']);
    var finalStack = ee.Image.cat([combinedStart, combinedEnd]);
      
    var sampledValue = finalStack.reduceRegion({
      reducer: ee.Reducer.first(),
      geometry: point,
      scale: 100,
      maxPixels: 1e6
    });

    sampledValue.evaluate(function(result) {
      resultsPanel.clear();
      
      resultsPanel.add(ui.Label({
        value: 'Location: ' + coords.lat.toFixed(4) + ', ' + coords.lon.toFixed(4),
        style: {fontSize: '12px', color: '#777', margin: '0 0 10px 0'}
      }));

      resultsPanel.add(ui.Label({value: 'CHANGE ANALYSIS (2013-2019):', style: {fontWeight: 'bold', fontSize: '16px'}}));
      
      function addRow(label, vStart, vEnd, unit) {
        var valStart = (vStart || 0);
        var valEnd = (vEnd || 0);
        var diff = valEnd - valStart;
        var color = diff >= 0 ? 'green' : 'red';
        var sign = diff >= 0 ? '+' : '';
        
        resultsPanel.add(ui.Label({value: label, style: {fontWeight: 'bold', margin: '10px 0 2px 0'}}));
        resultsPanel.add(ui.Label({value: '2013: ' + valStart.toFixed(2) + ' ' + unit, style: {fontSize: '12px', margin: '0'}}));
        resultsPanel.add(ui.Label({value: '2019: ' + valEnd.toFixed(2) + ' ' + unit, style: {fontSize: '12px', margin: '0'}}));
        resultsPanel.add(ui.Label({value: 'Change: ' + sign + diff.toFixed(2) + ' ' + unit, style: {fontSize: '12px', color: color, fontWeight: 'bold', margin: '0 0 5px 0'}}));
      }

      addRow('Population', result.pop_start, result.pop_end, 'ppl');
      addRow('Night Lights', result.ntl_start, result.ntl_end, 'rad');
      addRow('GDP Est.', result.gdp_start, result.gdp_end, '$M');
    });
  });
});
