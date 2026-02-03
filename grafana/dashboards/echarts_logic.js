// ECharts Dynamic Map Configuration suitable for Grafana
// Requires a data query returning: city, longitude, latitude, count

// Central Point (Colombia - Bogota approx)
const center = [-74.07, 4.71];

// Prepare Data
const data = context.panel.data.series[0].fields;
const city = data[0].values;
const lat = data[1].values;
const lon = data[2].values;
const count = data[3].values;

const linesData = [];
const pointsData = [];

for (let i = 0; i < city.length; i++) {
    const source = [lon[i], lat[i]];
    const val = count[i];

    // Only add if we have valid coordinates
    if (source[0] && source[1]) {
        // Line from Source -> Center
        linesData.push({
            coords: [source, center],
            value: val
        });

        // Point at Source
        pointsData.push({
            name: city[i],
            value: [...source, val]
        });
    }
}

// Add center point
pointsData.push({
    name: "Data Center (Colombia)",
    value: [...center, 100],
    itemStyle: { color: '#ff0000' },
    label: { show: true, position: 'right', formatter: '{b}' }
});

return {
    backgroundColor: 'transparent',
    geo: {
        map: 'world',
        roam: true,
        silent: true,
        itemStyle: {
            borderColor: '#003',
            areaColor: '#001a33'
        },
        emphasis: {
            areaColor: '#2a333d'
        }
    },
    series: [
        // Pulsing Points (Effect Scatter)
        {
            type: 'effectScatter',
            coordinateSystem: 'geo',
            zlevel: 2,
            rippleEffect: {
                brushType: 'stroke',
                period: 4,
                scale: 2.5
            },
            label: {
                show: true,
                position: 'right',
                formatter: '{b}'
            },
            itemStyle: {
                color: '#a6c84c'
            },
            data: pointsData
        },
        // Animated Lines
        {
            type: 'lines',
            zlevel: 1,
            effect: {
                show: true,
                period: 6,
                trailLength: 0.7,
                color: '#fff',
                symbolSize: 3
            },
            lineStyle: {
                color: '#a6c84c',
                width: 0,
                curveness: 0.2
            },
            data: linesData
        },
        // Faint Lines background
        {
            type: 'lines',
            zlevel: 2,
            effect: {
                show: false
            },
            lineStyle: {
                color: '#a6c84c',
                width: 1,
                opacity: 0.4,
                curveness: 0.2
            },
            data: linesData
        }
    ]
};
