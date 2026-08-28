let metricsChart = null;
const maxDataPoints = 30;
const timeLabels = [];
const errorRateData = [];
const p99LatencyData = [];

function initChart() {
    const canvas = document.getElementById('metricsChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    metricsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Độ trễ P99 (ms)',
                    data: p99LatencyData,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'yLatency',
                    fill: true
                },
                {
                    label: 'Tỷ lệ lỗi (%)',
                    data: errorRateData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'yError',
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono' } }
                },
                yLatency: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#38bdf8', callback: v => v + 'ms' },
                    title: { display: true, text: 'P99 Latency (ms)', color: '#38bdf8' }
                },
                yError: {
                    type: 'linear',
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#ef4444', callback: v => v + '%' },
                    title: { display: true, text: 'Tỷ lệ lỗi (%)', color: '#ef4444' },
                    min: 0,
                    max: 40
                }
            },
            plugins: {
                legend: { labels: { color: '#f1f5f9', font: { family: 'Inter' } } }
            }
        }
    });
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/stream`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        const wsEl = document.getElementById('ws-status');
        if (wsEl) wsEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 inline-block mr-1.5"></span>Online (Edge Live)`;
    };

    socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'metric_update') {
            updateMetrics(msg.data);
        } else if (msg.type === 'alert_event') {
            addAlertItem(msg.data);
        } else if (msg.type === 'initial_state') {
            if (msg.metrics) updateMetrics(msg.metrics);
            if (msg.recent_alerts) {
                msg.recent_alerts.forEach(addAlertItem);
            }
        }
    };

    socket.onclose = () => {
        const wsEl = document.getElementById('ws-status');
        if (wsEl) wsEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500 inline-block mr-1.5"></span>Mất kết nối (Đang thử lại...)`;
        setTimeout(connectWebSocket, 2000);
    };
}

function updateMetrics(m) {
    if (!m) return;
    const elRec = document.getElementById('val-total-records');
    const elErr = document.getElementById('val-error-rate');
    const elLat = document.getElementById('val-p99-latency');
    const elCpu = document.getElementById('val-cpu');
    if (elRec) elRec.innerText = (m.total_stored_records || 0).toLocaleString();
    if (elErr) elErr.innerText = (m.error_rate_pct || 0) + '%';
    if (elLat) elLat.innerText = (m.p99_latency || 0) + ' ms';
    if (elCpu) elCpu.innerText = (m.avg_cpu || 0) + '%';

    const alertCard = document.getElementById('card-error-rate');
    if (alertCard) {
        if ((m.error_rate_pct || 0) > 15.0) {
            alertCard.classList.add('pulse-red');
        } else {
            alertCard.classList.remove('pulse-red');
        }
    }

    if (metricsChart && m.timestamp) {
        timeLabels.push(m.timestamp);
        p99LatencyData.push(m.p99_latency || 0);
        errorRateData.push(m.error_rate_pct || 0);

        if (timeLabels.length > maxDataPoints) {
            timeLabels.shift();
            p99LatencyData.shift();
            errorRateData.shift();
        }
        metricsChart.update();
    }
}

function addAlertItem(alert) {
    const list = document.getElementById('alert-feed');
    if (!list) return;
    const badgeClass = alert.severity === 'CRITICAL' ? 'badge-critical' : 'badge-warning';
    
    const itemHtml = `
        <div class="p-3 rounded-lg border card-glass mb-2 flex items-start justify-between">
            <div class="flex-1 pr-3">
                <div class="flex items-center space-x-2 mb-1">
                    <span class="px-2 py-0.5 text-xs font-semibold rounded ${badgeClass}">${alert.severity}</span>
                    <span class="text-xs text-slate-400 mono">${alert.time}</span>
                    <span class="text-xs font-semibold text-slate-200">${alert.name}</span>
                </div>
                <p class="text-xs text-slate-300">${alert.message}</p>
            </div>
            <div class="text-right">
                <span class="text-xs mono text-rose-400 font-semibold">${JSON.stringify(alert.trigger_val?.error_rate_pct || alert.trigger_val?.p99_latency_ms || '')}</span>
            </div>
        </div>
    `;
    list.insertAdjacentHTML('afterbegin', itemHtml);
}

async function triggerRollup() {
    const btn = document.getElementById('btn-rollup');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Đang xuất Parquet...';
    }
    try {
        const res = await fetch('/api/trigger-rollup', { method: 'POST' });
        const data = await res.json();
        alert(`Xuất thành công! File: ${data.file}\nDung lượng nén: ${data.size_kb} KB (Tiết kiệm >90% băng thông Cloud)`);
    } catch (e) {
        alert('Lỗi khi xuất rollup: ' + e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Xuất Bản Tóm Tắt Parquet';
        }
    }
}

async function runWebBenchmark() {
    const btn = document.getElementById('btn-run-bench');
    const loading = document.getElementById('bench-loading');
    const tableDiv = document.getElementById('bench-table-container');
    const imgElem = document.getElementById('bench-chart-img');

    if (btn) btn.disabled = true;
    if (loading) loading.classList.remove('hidden');
    if (tableDiv) tableDiv.classList.add('hidden');

    try {
        const res = await fetch('/api/run-benchmark?rows=100000', { method: 'POST' });
        const json = await res.json();
        
        if (json.status === 'success') {
            renderBenchmarkTable(json.data);
            if (imgElem) imgElem.src = '/api/benchmark-image?t=' + new Date().getTime();
            if (tableDiv) tableDiv.classList.remove('hidden');
        }
    } catch (e) {
        alert('Lỗi chạy benchmark: ' + e);
    } finally {
        if (btn) btn.disabled = false;
        if (loading) loading.classList.add('hidden');
    }
}

function renderBenchmarkTable(data) {
    const tbody = document.getElementById('bench-tbody');
    if (!tbody) return;
    let rowsHtml = `
        <tr class="border-b border-slate-700 bg-slate-800/40 font-semibold">
            <td class="py-2.5 px-3">Tốc độ nạp (Ingestion Throughput)</td>
            <td class="py-2.5 px-3 text-sky-400">${data.ingestion.duckdb_rows_per_sec.toLocaleString()} rows/s</td>
            <td class="py-2.5 px-3 text-rose-400">${data.ingestion.sqlite_rows_per_sec.toLocaleString()} rows/s</td>
            <td class="py-2.5 px-3 text-emerald-400 font-bold">${(data.ingestion.duckdb_rows_per_sec / data.ingestion.sqlite_rows_per_sec).toFixed(1)}x</td>
        </tr>
        <tr class="border-b border-slate-700">
            <td class="py-2.5 px-3">Dung lượng file trên đĩa Flash</td>
            <td class="py-2.5 px-3 text-sky-400 font-bold">${data.storage.duckdb_size_mb} MB</td>
            <td class="py-2.5 px-3 text-rose-400">${data.storage.sqlite_size_mb} MB</td>
            <td class="py-2.5 px-3 text-emerald-400 font-bold">Tiết kiệm ${data.storage.space_saving_pct}%</td>
        </tr>
    `;

    for (const [k, q] of Object.entries(data.queries)) {
        rowsHtml += `
            <tr class="border-b border-slate-800 hover:bg-slate-800/30">
                <td class="py-2 px-3 text-slate-300 text-xs">${q.name}</td>
                <td class="py-2 px-3 text-sky-400 font-semibold">${q.duckdb_ms} ms</td>
                <td class="py-2 px-3 text-rose-400 font-semibold">${q.sqlite_ms} ms</td>
                <td class="py-2 px-3 text-emerald-400 font-bold">${q.speedup}x Nhanh hơn</td>
            </tr>
        `;
    }
    tbody.innerHTML = rowsHtml;
}

window.runWebBenchmark = runWebBenchmark;
window.triggerRollup = triggerRollup;
window.renderBenchmarkTable = renderBenchmarkTable;

window.addEventListener('DOMContentLoaded', () => {
    initChart();
    connectWebSocket();
    fetch('/api/benchmark-results')
        .then(r => r.json())
        .then(data => {
            if (!data.error) {
                renderBenchmarkTable(data);
                const imgElem = document.getElementById('bench-chart-img');
                if (imgElem) imgElem.src = '/api/benchmark-image?t=' + new Date().getTime();
                const tableDiv = document.getElementById('bench-table-container');
                if (tableDiv) tableDiv.classList.remove('hidden');
            }
        }).catch(() => {});
});
