// 全局变量
let ws = null;
const MAX_HISTORY_POINTS = 50;
const metrics_history = {
    cpu: [],
    memory: [],
    disk: [],
    response_times: {},
    success_rates: {}
};

// WebSocket连接管理
function initWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
        requestMetrics();
    };

    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'metrics_update') {
                updateDashboard(data.data);
            }
        } catch (e) {
            console.error('Error processing message:', e);
        }
    };

    ws.onclose = function() {
        console.log('WebSocket disconnected');
        setTimeout(initWebSocket, 5000);
    };
}

function requestMetrics() {
    if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'get_metrics' }));
    }
}

// 仪表盘更新函数
function updateDashboard(data) {
    if (data.system) {
        updateSystemMetrics(data.system);
        updateMetricsHistory(data.system);
    }
    if (data.services) {
        updateServicesStatus(data.services);
    }
}

function updateSystemMetrics(metrics) {
    // CPU使用率仪表
    createGauge('cpu-gauge', 'CPU Usage', metrics.cpu_percent || 0);
    document.getElementById('cpu-value').textContent = 
        `${(metrics.cpu_percent || 0).toFixed(1)}%`;

    // 内存使用率仪表
    createGauge('memory-gauge', 'Memory Usage', metrics.memory_percent || 0);
    document.getElementById('memory-value').textContent = 
        `${(metrics.memory_percent || 0).toFixed(1)}%`;

    // 磁盘使用率仪表
    createGauge('disk-gauge', 'Disk Usage', metrics.disk_usage || 0);
    document.getElementById('disk-value').textContent = 
        `${(metrics.disk_usage || 0).toFixed(1)}%`;
}

function createGauge(elementId, title, value) {
    const data = [{
        type: 'indicator',
        mode: 'gauge+number',
        value: value,
        number: { suffix: '%' },
        gauge: {
            axis: { range: [0, 100] },
            bar: { color: getColorForValue(value) },
            bgcolor: 'white',
            borderwidth: 2,
            bordercolor: 'gray',
            steps: [
                { range: [0, 70], color: 'rgb(240,240,240)' },
                { range: [70, 90], color: 'rgb(255,220,220)' },
                { range: [90, 100], color: 'rgb(255,200,200)' }
            ]
        }
    }];

    const layout = {
        height: 150,
        margin: { t: 25, r: 25, l: 25, b: 25 },
        paper_bgcolor: 'white',
        font: { size: 12 }
    };

    Plotly.react(elementId, data, layout);
}

function updateMetricsHistory(metrics) {
    const timestamp = new Date();
    
    // 更新历史数据
    metrics_history.cpu.push({ time: timestamp, value: metrics.cpu_percent || 0 });
    metrics_history.memory.push({ time: timestamp, value: metrics.memory_percent || 0 });
    metrics_history.disk.push({ time: timestamp, value: metrics.disk_usage || 0 });

    // 限制历史数据点数量
    if (metrics_history.cpu.length > MAX_HISTORY_POINTS) {
        metrics_history.cpu.shift();
        metrics_history.memory.shift();
        metrics_history.disk.shift();
    }

    // 更新趋势图
    updateTrendChart('response-time-chart', metrics_history.cpu, 'CPU Usage Trend');
    updateTrendChart('success-rate-chart', metrics_history.memory, 'Memory Usage Trend');
}

function updateTrendChart(elementId, data, title) {
    const times = data.map(point => point.time);
    const values = data.map(point => point.value);

    const plotData = [{
        x: times,
        y: values,
        type: 'scatter',
        mode: 'lines',
        line: { color: 'rgb(75, 192, 192)', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(75, 192, 192, 0.2)'
    }];

    const layout = {
        title: { text: title, font: { size: 14 } },
        height: 250,
        margin: { t: 30, r: 20, b: 30, l: 40 },
        xaxis: {
            type: 'date',
            showgrid: true,
            gridcolor: 'rgb(240,240,240)'
        },
        yaxis: {
            showgrid: true,
            gridcolor: 'rgb(240,240,240)',
            range: [0, 100]
        },
        paper_bgcolor: 'white',
        plot_bgcolor: 'white'
    };

    Plotly.react(elementId, plotData, layout);
}

function updateServicesStatus(services) {
    const tbody = document.getElementById('services-table-body');
    tbody.innerHTML = '';

    Object.entries(services).forEach(([name, service]) => {
        const row = tbody.insertRow();
        const statusClass = service.status === 'UP' ? 'status-up' : 'status-down';

        row.innerHTML = `
            <td class="px-4 py-2 border-b">${name}</td>
            <td class="px-4 py-2 border-b">
                <span class="${statusClass}">${service.status}</span>
            </td>
            <td class="px-4 py-2 border-b">
                ${formatResponseTime(service.response_time)}
            </td>
            <td class="px-4 py-2 border-b">
                ${formatSuccessRate(service.success_rate)}
            </td>
            <td class="px-4 py-2 border-b">
                ${formatDateTime(service.last_check)}
            </td>
        `;
    });
}

// 辅助函数
function getColorForValue(value) {
    if (value >= 90) return 'rgb(239, 68, 68)';
    if (value >= 70) return 'rgb(251, 146, 60)';
    return 'rgb(34, 197, 94)';
}

function formatResponseTime(time) {
    return time ? `${time.toFixed(3)}s` : 'N/A';
}

function formatSuccessRate(rate) {
    return rate ? `${rate.toFixed(1)}%` : 'N/A';
}

function formatDateTime(timestamp) {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    // 定期请求更新
    setInterval(requestMetrics, 5000);
});