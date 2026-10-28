# Web applications

Interactive GeoDevelopment apps for Bolivia, built on Google Earth Engine (GEE). They run in the browser.

| App | Launch | Source |
| --- | --- | --- |
| GeoExplorer v1.0 — Bolivia: space-time dynamics of population, night-time lights, land cover and GDP (2013–2019) | [geoexplorer1v100bolivia](https://carlos-mendez.projects.earthengine.app/view/geoexplorer1v100bolivia) | [`geoexplorer1v100bolivia.js`](geoexplorer1v100bolivia.js) |

## Using the GEE source

1. Open the [Earth Engine code editor](https://code.earthengine.google.com/).
2. Paste the contents of a `.js` file into a new script and press **Run**.

`geoexplorer1v100bolivia.js` comes from [DS4Bolivia](https://github.com/quarcs-lab/ds4bolivia/tree/master/apps). It shows WorldPop population (`WorldPop/GP/100m/pop`), VIIRS night-time lights (`NOAA/VIIRS/DNB/ANNUAL_V21`), land cover and gridded GDP (`projects/sat-io/open-datasets/GRIDDED_EC-GDP`) for Bolivia's 339 municipalities.
