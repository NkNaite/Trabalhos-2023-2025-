// === AI AGENT SAFETY DIRECTIVE (DO NOT IGNORE) ===
// 1. NO INFINITE LOOPS: Avoid uncontrolled recursive calls or retry loops.
// 2. RESOURCE ECONOMY: Use debouncing for all UI-triggered API requests.
// 3. NO SYSTEM OVERLOAD: Limit concurrent fetches.

const API_BASE = '/api';

// Utility: Debounce to prevent rapid-fire requests
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Formatting helpers
const formatCurrency = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '-';
    return `${num.toFixed(1)}g`;
};
const formatPercent = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '-';
    return `${num.toFixed(1)}%`;
};

async function fetchJSON(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (e) {
        console.error("Fetch Error:", e);
        return null;
    }
}

function renderTable(containerId, columns, data, filterId = 'tier-filter') {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Store data for filtering locally if needed
    container.dataset.original = JSON.stringify(data);

    // Apply Filter locally just in case
    const filterEl = document.getElementById(filterId);
    const tierVal = filterEl ? filterEl.value : 'all';

    let filteredData = data;
    if (tierVal !== 'all' && data.length > 0 && data[0].hasOwnProperty('Tier')) {
        filteredData = data.filter(d => d.Tier == tierVal);
    }

    if (!filteredData || filteredData.length === 0) {
        container.innerHTML = `
            <div class="loading-state">
                <i class="ri-inbox-archive-line" style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.5"></i>
                <p>No data available</p>
            </div>`;
        return;
    }

    try {
        let html = `<table><thead><tr>`;
        columns.forEach(col => html += `<th>${col.header}</th>`);
        html += `</tr></thead><tbody>`;

        filteredData.forEach(item => {
            html += `<tr>`;
            columns.forEach(col => {
                try {
                    html += `<td>${col.render(item)}</td>`;
                } catch (err) {
                    console.error("Render Error Row:", item, err);
                    html += `<td>Err</td>`;
                }
            })
            html += `</tr>`;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;
    } catch (err) {
        console.error("Render Error Table:", containerId, err);
        container.innerHTML = `<p style="color:red; text-align:center">Error rendering data</p>`;
    }
}

function applyFilters() {
    // Re-render all active tables
    loadCrafting();
    loadLiquidity();
    loadDemandIntensity();
    loadArbitrage();
    loadMercadorias();
}

// Debounced version for rapid-firing UI elements (dropdowns, etc)
const debouncedApplyFilters = debounce(applyFilters, 400);

// --- Tabs ---
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).style.display = 'block';

    // Deactivate all, Activate clicked
    const btns = document.querySelectorAll('.tab-btn');
    btns.forEach(b => {
        if (b.getAttribute('onclick') === `switchTab('${tabId}')`) b.classList.add('active');
    });
}

// --- Features ---

async function loadCrafting() {
    const container = document.getElementById('crafting-container');
    if (container) container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Calculating Smart Sourcing...</p></div>';

    const data = await fetchJSON('/crafting/opportunities?top=25');

    renderTable('crafting-container', [
        { header: 'Product', render: i => `<strong style="color:var(--text-main); cursor:pointer; text-decoration:underline" onclick="loadItemAnalysis('${i.Produto}')">${i.Produto}</strong>` },
        { header: 'Tier', render: i => `<span class="zone-tag">T${i.Tier || '?'}</span>` },
        { header: 'Cost', render: i => `<span class="font-mono" style="color:var(--text-muted)">${formatCurrency(i.Custo_Manufatura)}</span>` },
        { header: 'Sell', render: i => `<span class="font-mono">${formatCurrency(i.Preco_Venda)}</span>` },
        { header: 'Spread', render: i => `<span class="font-mono profit-positive">+${formatCurrency(i.Spread)}</span>` },
        { header: 'Mrg', render: i => `<span class="font-mono">${formatPercent(i.Margem_Perc)}</span>` },
    ], data, 'tier-filter');
}

async function loadLiquidity() {
    const container = document.getElementById('liquidity-container');
    if (container) container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Fetching market volume...</p></div>';

    const data = await fetchJSON('/market/liquidity');
    const topData = data ? data.slice(0, 15) : [];

    renderTable('liquidity-container', [
        { header: 'Item', render: i => `<span style="cursor:pointer; text-decoration:underline" onclick="loadItemAnalysis('${i.Item}')">${i.Item}</span>` },
        { header: 'T', render: i => `<small class="zone-tag">T${i.Tier || 1}</small>` },
        { header: 'Units Sold', render: i => `<span class="font-mono">${i.Units_Sold}</span>` },
        { header: 'Volume', render: i => `<span class="font-mono">${formatCurrency(i.Total_Volume)}</span>` },
        { header: 'Top Zone', render: i => `<span class="zone-tag" style="background: rgba(59, 130, 246, 0.1); color: #60a5fa">${i.Top_Zone || 'Unknown'}</span>` },
    ], topData, 'tier-filter-liquidity');
}

async function loadDemandIntensity() {
    const container = document.getElementById('demand-intensity-container');
    if (container) container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Calculating Intensity...</p></div>';

    const data = await fetchJSON('/market/demand');
    const topData = data ? data.slice(0, 15) : [];

    renderTable('demand-intensity-container', [
        { header: 'Item', render: i => `<span style="cursor:pointer; text-decoration:underline" onclick="loadItemAnalysis('${i.Item}')">${i.Item}</span>` },
        { header: 'T', render: i => `<small class="zone-tag">T${i.Tier || 1}</small>` },
        { header: 'Sold', render: i => `<span>${i.Units_Sold}</span>` },
        { header: 'Listed', render: i => `<span>${i.Total_Supply}</span>` },
        { header: 'Intensity', render: i => `<strong style="color:${i.Intensity_Score > 50 ? '#ef4444' : '#22c55e'}">${i.Intensity_Score.toFixed(1)}%</strong>` },
    ], topData, 'tier-filter-demand');
}

async function loadRegionalLiquidity() {
    const container = document.getElementById('regional-liquidity-container');
    if (container) container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Fetching zones...</p></div>';

    const data = await fetchJSON('/market/liquidity/regional');

    renderTable('regional-liquidity-container', [
        { header: 'Zone', render: i => `<strong>${i.Zone}</strong>` },
        { header: 'Total Volume', render: i => `<span class="font-mono">${formatCurrency(i.Volume_Sold)}</span>` },
        { header: 'Tx Count', render: i => `<span>${i.Transaction_Count}</span>` },
    ], data);
}

const loadArbitrage = debounce(async function () {
    const container = document.getElementById('arbitrage-container');
    if (container) container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Calculating 7d Medians...</p></div>';

    const province = document.getElementById('filter-province-arbitrage')?.value || '';
    let url = '/logistics/arbitrage';
    if (province) url += `?province=${encodeURIComponent(province)}`;

    const data = await fetchJSON(url);

    renderTable('arbitrage-container', [
        { header: 'Item', render: i => `<strong style="cursor:pointer; text-decoration:underline" onclick="loadItemAnalysis('${i.Item}')">${i.Item}</strong>` },
        { header: 'T', render: i => `<small class="zone-tag">T${i.Tier || 1}</small>` },
        { header: 'Buy', render: i => `<div><span class="font-mono">${formatCurrency(i.Buy_Price)}</span><br><small style="color:var(--text-muted)">${i.Buy_Zone} <span style="opacity:0.7">(${i.Amount_Available}x)</span></small></div>` },
        { header: 'Sell At', render: i => `<div><span class="font-mono">${formatCurrency(i.Avg_Sale_Price)}</span><br><small style="color:var(--text-muted)">${i.Sell_Zone}</small></div>` },
        { header: 'Margin', render: i => `<span class="font-mono profit-positive">+${formatCurrency(i.Unit_Profit)}</span><br><small style="color:#fbbf24">${formatPercent(i.Margin)}</small>` },
        { header: 'Score', render: i => `<strong style="color:#fbbf24">${Math.round(i.Score)}</strong>` },
    ], data, 'tier-filter-arbitrage');
}, 500);

// --- Mercadorias (Supply/Demand) ---
let marketLocations = {};

async function loadLocationsForDropdowns() {
    const locations = await fetchJSON('/market/locations');
    if (locations) {
        marketLocations = locations;
        const provSelect = document.getElementById('filter-province');
        if (!provSelect) return;

        let html = '<option value="">Todas as Províncias</option>';
        Object.keys(locations).forEach(prov => {
            html += `<option value="${prov}">${prov}</option>`;
        });
        provSelect.innerHTML = html;
        updateValleyDropdown();
    }
}

window.updateValleyDropdown = function () {
    const provSelect = document.getElementById('filter-province');
    const valSelect = document.getElementById('filter-valley');
    if (!provSelect || !valSelect) return;

    const prov = provSelect.value;
    let html = '<option value="">Todos os Vales</option>';

    if (prov && marketLocations[prov]) {
        marketLocations[prov].forEach(valley => {
            html += `<option value="${valley}">${valley}</option>`;
        });
    }
    valSelect.innerHTML = html;
};

let sortDesc = true;

window.toggleSortOrder = function() {
    sortDesc = !sortDesc;
    const btn = document.getElementById('sort-order-btn');
    if (btn) {
        btn.innerHTML = sortDesc ? '⬇️ Desc' : '⬆️ Asc';
    }
    loadMercadorias();
};

window.loadMercadorias = debounce(async function () {
    const container = document.getElementById('mercadorias-container');
    if (!container) return;
    container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Calculating Supply/Demand Ratio...</p></div>';

    const prov = document.getElementById('filter-province')?.value || '';
    const valley = document.getElementById('filter-valley')?.value || '';
    const days = document.getElementById('filter-days')?.value || '7';

    let url = `/market/supply_demand?days=${days}`;
    if (prov) url += `&province=${encodeURIComponent(prov)}`;
    if (valley) url += `&valley=${encodeURIComponent(valley)}`;

    let data = await fetchJSON(url);

    if (data && data.length) {
        const sortBy = document.getElementById('sort-mercadorias')?.value || 'Total_Supply';
        data.sort((a, b) => {
            const valA = parseFloat(a[sortBy]) || 0;
            const valB = parseFloat(b[sortBy]) || 0;
            return sortDesc ? (valB - valA) : (valA - valB);
        });
    }

    renderTable('mercadorias-container', [
        { header: 'Item', render: i => `<strong style="cursor:pointer; text-decoration:underline" onclick="loadItemAnalysis('${i.Item}')">${i.Item}</strong>` },
        { header: 'T', render: i => `<small class="zone-tag">T${i.Tier || 1}</small>` },
        { header: 'Oferta', render: i => `<span class="font-mono" style="color:#60a5fa">${i.Total_Supply}</span> <small style="opacity:0.6">(${formatCurrency(i.Total_Gold_Supply)})</small>` },
        { header: 'Vendas', render: i => `<span class="font-mono" style="color:#f87171">${i.Units_Sold}</span> <small style="opacity:0.6">(${formatCurrency(i.Gold_Sold)})</small> <small style="opacity:0.6">(${days}d)</small>` },
        { header: 'Score Arb.', render: i => `<span style="color:#fbbf24; font-weight:bold">${Math.round(i.Arbitrage_Score || 0)}</span>` },
        { header: 'Score Craft', render: i => `<span style="color:#10b981; font-weight:bold">${Math.round(i.Profitcraft_Score || 0)}</span>` },
        {
            header: 'Balança Comercial', render: i => {
                const ratio = i.Supply_Ratio || 0;
                return `
                <div style="display:flex; align-items:center; gap:10px;">
                    <div class="supply-demand-wrapper">
                        <div class="demand-bar"></div>
                        <div class="supply-bar" style="width: ${ratio}%;"></div>
                        <div class="center-marker"></div>
                    </div>
                    <span style="font-size:0.8rem; opacity:0.8; font-family:monospace; width:45px; text-align:right">
                        ${ratio.toFixed(0)}%
                    </span>
                </div>
            `;
            }
        }
    ], data ? data.slice(0, 500) : []);
}, 500);

// Item Analysis Logic
let priceChart = null;
let demandChart = null;

async function loadItemAnalysis(itemName) {
    if (!itemName) return;

    // Switch to Analysis Tab
    switchTab('analysis');

    // Update Header
    const titleEl = document.getElementById('analysis-title');
    if (titleEl) titleEl.innerHTML = `Item Analysis: <span style="color:var(--text-accent)">${itemName}</span>`;

    // Clear Search Input
    document.getElementById('search-results').style.display = 'none';
    const searchInput = document.getElementById('global-search');
    if (searchInput) searchInput.value = '';

    // Load History
    const history = await fetchJSON(`/market/item/${itemName}/history`);
    renderCharts(history);

    // Load Producers
    const producers = await fetchJSON(`/market/item/${itemName}/producers`);
    const prodList = document.getElementById('analysis-producers-list');
    if (producers && producers.length > 0) {
        prodList.innerHTML = producers.map(p => `
            <div class="producer-tag">
                <span class="hub-icon ${p.Zone.includes('Kerys') ? 'hub-active' : ''}">📍</span>
                <strong>${p.Zone}</strong> 
                <small>(${p.Unique_Producers} Sellers)</small>
            </div>
        `).join('');
    } else {
        prodList.innerHTML = '<p style="color:var(--text-muted)">No specific producer data found.</p>';
    }

    // Load Blueprint
    const blueprintContainer = document.getElementById('blueprint-container');
    blueprintContainer.innerHTML = '<p>Loading blueprint...</p>';
    const blueprint = await fetchJSON(`/crafting/item/${itemName}/detailed`);

    if (blueprint && blueprint.Ingredients) {
        let html = `<table class="blueprint-table"><thead><tr><th>Ingredient</th><th>Qty</th><th>Avg Cost</th><th>Best Zone(s)</th></tr></thead><tbody>`;
        blueprint.Ingredients.forEach(ing => {
            html += `<tr>
                <td>${ing.Item}</td>
                <td>${ing.Qty_Needed}</td>
                <td>${formatCurrency(ing.Avg_Unit_Cost)}</td>
                <td>${ing.Zones.join(', ')}</td>
            </tr>`;
        });
        html += `<tr style="border-top:2px solid #333">
            <td><strong>TOTAL</strong></td>
            <td>Yield: ${blueprint.Yield}</td>
            <td><strong>${formatCurrency(blueprint.Unit_Cost)} / unit</strong></td>
            <td>Profit: <span style="color:#22c55e">${formatCurrency(blueprint.Profit)}</span></td>
        </tr></tbody></table>`;
        blueprintContainer.innerHTML = html;
    } else {
        blueprintContainer.innerHTML = '<p style="color:var(--text-muted)">No crafting blueprint available for this item.</p>';
    }

    // Load Item Arbitrage
    const arbContainer = document.getElementById('item-arbitrage-container');
    arbContainer.innerHTML = '<p>Checking routes...</p>';
    const arbData = await fetchJSON(`/logistics/arbitrage?item=${itemName}`);

    if (arbData && arbData.length > 0) {
        renderTable('item-arbitrage-container', [
            { header: 'Buy From', render: i => `<strong>${i.Buy_Zone}</strong> (${formatCurrency(i.Buy_Price)})` },
            { header: 'Profit', render: i => `<span class="profit-positive">+${formatCurrency(i.Unit_Profit)}</span>` }
        ], arbData.slice(0, 2));
    } else {
        arbContainer.innerHTML = '<p style="color:var(--text-muted)">No arbitrage opportunities found for this item.</p>';
    }
}

function renderCharts(history) {
    const ctxPrice = document.getElementById('priceChart').getContext('2d');
    if (priceChart) priceChart.destroy();

    if (history && history.length > 0) {
        priceChart = new Chart(ctxPrice, {
            type: 'line',
            data: {
                labels: history.map(h => h.SnapshotDate.split(' ')[0]),
                datasets: [
                    {
                        label: 'Median Price',
                        data: history.map(h => h.Median_Price != null ? h.Median_Price : h.Avg_Price),
                        borderColor: '#fbbf24',
                        tension: 0.1,
                        borderWidth: 2
                    }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { grid: { color: '#222' } } } }
        });
    }

    const ctxDemand = document.getElementById('demandChart').getContext('2d');
    if (demandChart) demandChart.destroy();

    if (history && history.length > 0) {
        demandChart = new Chart(ctxDemand, {
            type: 'bar',
            data: {
                labels: history.map(h => h.SnapshotDate.split(' ')[0]),
                datasets: [{
                    label: 'Units Sold (Daily)',
                    data: history.map(h => h.Units_Sold_Since_Last),
                    backgroundColor: '#22c55e',
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { grid: { color: '#222' }, beginAtZero: true } } }
        });
    }
}

async function triggerFetch() {
    const btn = document.querySelector('.btn-primary');
    btn.innerHTML = '...';
    await fetch('/api/admin/fetch-prices', { method: 'POST' });
    alert("Updated!");
    loadAllData();
    btn.innerHTML = '<i class="ri-refresh-line"></i> Refresh Data';
}

function loadAllData() {
    loadCrafting();
    loadLiquidity();
    loadDemandIntensity();
    loadRegionalLiquidity();
    loadArbitrage();
    loadLocationsForDropdowns().then(() => loadMercadorias());
}

// Search Logic
const searchInput = document.getElementById('global-search');
const resultsBox = document.getElementById('search-results');
if (searchInput) {
    searchInput.addEventListener('input', async (e) => {
        const query = e.target.value;
        if (query.length < 3) { resultsBox.style.display = 'none'; return; }
        const matches = await fetchJSON(`/market/search?query=${query}`);
        if (matches && matches.length > 0) {
            resultsBox.innerHTML = matches.map(item => `
                <div class="search-item" onclick="loadItemAnalysis('${item}')">${item}</div>
            `).join('');
            resultsBox.style.display = 'block';
        }
    });
}

document.addEventListener('DOMContentLoaded', loadAllData);
