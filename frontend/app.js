// PAL to TREVEE Migration Dashboard JavaScript

const API_BASE_URL = 'http://localhost:5000/api';
const REFRESH_INTERVAL = 300000; // 5 minutes in milliseconds

// Debug mode - enable by setting localStorage.debug = 'true' in browser console
const DEBUG = localStorage.getItem('debug') === 'true';

// Global chart instances
let cumulativeChart = null;
let dailyChart = null;
let distributionChart = null;
let sourceChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('PAL Migration Dashboard Initializing...');
    initializeCharts();
    refreshData();

    // Auto-refresh every 5 minutes
    setInterval(refreshData, REFRESH_INTERVAL);

    // Allow Enter key for address lookup
    document.getElementById('addressInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            lookupAddress();
        }
    });
});

// Initialize all charts
function initializeCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: {
                    color: '#a8b2d1'
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#6b7592' },
                grid: { color: '#2d3454' }
            },
            y: {
                ticks: { color: '#6b7592' },
                grid: { color: '#2d3454' }
            }
        }
    };

    // Cumulative Chart
    const cumulativeCtx = document.getElementById('cumulativeChart').getContext('2d');
    cumulativeChart = new Chart(cumulativeCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Cumulative PAL Migrated',
                data: [],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // Daily Chart
    const dailyCtx = document.getElementById('dailyChart').getContext('2d');
    dailyChart = new Chart(dailyCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Daily PAL Migrated',
                data: [],
                backgroundColor: '#7b61ff',
                borderColor: '#7b61ff',
                borderWidth: 1
            }]
        },
        options: chartOptions
    });

    // Distribution Chart
    const distributionCtx = document.getElementById('distributionChart').getContext('2d');
    distributionChart = new Chart(distributionCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Number of Migrations',
                data: [],
                backgroundColor: '#00ff88',
                borderColor: '#00ff88',
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                x: {
                    ...chartOptions.scales.x,
                    title: {
                        display: true,
                        text: 'Migration Size (PAL)',
                        color: '#a8b2d1'
                    }
                },
                y: {
                    ...chartOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Count',
                        color: '#a8b2d1'
                    }
                }
            }
        }
    });

    // Source Chart (Pie)
    const sourceCtx = document.getElementById('sourceChart').getContext('2d');
    sourceChart = new Chart(sourceCtx, {
        type: 'pie',
        data: {
            labels: ['TREVEE', 'stkTREVEE (Staked)'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [
                    '#00d4ff',
                    '#7b61ff'
                ],
                borderColor: '#1a1f3a',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#a8b2d1',
                        padding: 15
                    }
                }
            }
        }
    });
}

// Main refresh function
async function refreshData() {
    console.log('Refreshing data...');

    const refreshIcon = document.getElementById('refreshIcon');
    refreshIcon.classList.add('spinning');

    try {
        // Fetch all metrics
        const metrics = await fetchAPI('/metrics');

        if (metrics) {
            updateSummaryCards(metrics.summary);
            updateCharts(metrics);
            updateTopMigrations(metrics.top_migrations);
            updateLastUpdate();
        }

        // Fetch migration rate
        const rate = await fetchAPI('/migration-rate?days=7');
        if (rate) {
            updateMigrationRate(rate);
        }

        // Fetch Trevee metrics
        await refreshTreveeMetrics();

    } catch (error) {
        console.error('Error refreshing data:', error);
        showError('Failed to refresh data. Make sure the API server is running.');
    } finally {
        refreshIcon.classList.remove('spinning');
    }
}

// Update summary cards
function updateSummaryCards(summary) {
    document.getElementById('uniqueAddresses').textContent =
        formatNumber(summary.total_unique_addresses);

    document.getElementById('totalPAL').textContent =
        formatNumber(summary.total_pal_migrated, 2) + ' PAL';

    document.getElementById('totalMigrations').textContent =
        formatNumber(summary.total_migrations);

    document.getElementById('avgMigration').textContent =
        formatNumber(summary.average_migration_size, 2) + ' PAL';

    document.getElementById('medianMigration').textContent =
        'Median: ' + formatNumber(summary.median_migration_size, 2) + ' PAL';
}

// Update all charts
function updateCharts(metrics) {
    if (DEBUG) console.log('Updating charts with metrics:', metrics);

    // Update cumulative chart
    if (metrics.cumulative_data && metrics.cumulative_data.length > 0) {
        if (DEBUG) console.log(`Cumulative data points: ${metrics.cumulative_data.length}`);
        cumulativeChart.data.labels = metrics.cumulative_data.map(d => d.date);
        cumulativeChart.data.datasets[0].data = metrics.cumulative_data.map(d => d.cumulative_pal);
        cumulativeChart.update('none'); // Disable animation for immediate update
    }

    // Update daily chart
    if (metrics.daily_stats && metrics.daily_stats.length > 0) {
        if (DEBUG) console.log(`Daily stats data points: ${metrics.daily_stats.length}`);
        dailyChart.data.labels = metrics.daily_stats.map(d => d.date);
        dailyChart.data.datasets[0].data = metrics.daily_stats.map(d => d.total_pal);
        dailyChart.update('none'); // Disable animation for immediate update
    }

    // Update distribution chart
    if (metrics.distribution) {
        if (DEBUG) console.log(`Distribution bins: ${metrics.distribution.labels?.length || 0}`);
        distributionChart.data.labels = metrics.distribution.labels;
        distributionChart.data.datasets[0].data = metrics.distribution.counts;
        distributionChart.update('none');
    }

    // Update source chart
    if (metrics.source_breakdown) {
        if (DEBUG) console.log('Updating source breakdown chart');
        sourceChart.data.datasets[0].data = [
            metrics.source_breakdown.sonic?.pal || 0,  // TREVEE migrations
            metrics.source_breakdown.layerzero?.pal || 0  // stkTREVEE migrations
        ];
        sourceChart.update('none');
    }
}

// Update top migrations table
function updateTopMigrations(topMigrations) {
    const tbody = document.getElementById('topMigrationsBody');

    if (!topMigrations || topMigrations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No migrations found</td></tr>';
        return;
    }

    tbody.innerHTML = topMigrations.map((migration, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>
                <a href="https://sonicscan.org/address/${migration.from_address}"
                   target="_blank"
                   style="color: #00d4ff; text-decoration: none;">
                    ${shortenAddress(migration.from_address)}
                </a>
            </td>
            <td>${formatNumber(migration.amount_pal, 2)} PAL</td>
            <td>
                <a href="https://sonicscan.org/tx/${migration.tx_hash}"
                   target="_blank"
                   style="color: #00d4ff; text-decoration: none;">
                    ${shortenHash(migration.tx_hash)}
                </a>
            </td>
            <td>${formatTimestamp(migration.timestamp)}</td>
        </tr>
    `).join('');
}

// Update migration rate
function updateMigrationRate(rate) {
    document.getElementById('dailyAvgMigrations').textContent =
        formatNumber(rate.daily_average_migrations, 1) + ' migrations/day';

    document.getElementById('dailyAvgPAL').textContent =
        formatNumber(rate.daily_average_pal, 2) + ' PAL/day';
}

// Update last update timestamp
function updateLastUpdate() {
    const now = new Date();
    document.getElementById('lastUpdate').textContent =
        now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
}

// Address lookup
async function lookupAddress() {
    const addressInput = document.getElementById('addressInput');
    const address = addressInput.value.trim();

    if (!address || !address.startsWith('0x')) {
        showError('Please enter a valid Ethereum address (starts with 0x)');
        return;
    }

    const resultDiv = document.getElementById('lookupResult');
    resultDiv.innerHTML = '<p style="color: #6b7592;">Searching...</p>';

    try {
        const result = await fetchAPI(`/address/${address}`);

        if (!result.found) {
            resultDiv.innerHTML = `
                <p style="color: #ffb800;">
                    Address not found in migration records.
                </p>
            `;
            return;
        }

        resultDiv.innerHTML = `
            <div style="color: #a8b2d1;">
                <p><strong>Address:</strong> ${result.address}</p>
                <p><strong>Total Migrations:</strong> ${result.migration_count}</p>
                <p><strong>Total PAL Migrated:</strong> ${formatNumber(result.total_pal_migrated, 2)} PAL</p>
                <p style="margin-top: 10px;"><strong>Transactions:</strong></p>
                <ul style="margin-top: 5px; padding-left: 20px;">
                    ${result.migrations.slice(0, 5).map(m => `
                        <li>
                            ${formatNumber(m.amount_pal, 2)} PAL -
                            <a href="https://sonicscan.org/tx/${m.tx_hash}"
                               target="_blank"
                               style="color: #00d4ff; text-decoration: none;">
                                ${shortenHash(m.tx_hash)}
                            </a>
                        </li>
                    `).join('')}
                    ${result.migrations.length > 5 ? `<li>...and ${result.migrations.length - 5} more</li>` : ''}
                </ul>
            </div>
        `;
    } catch (error) {
        resultDiv.innerHTML = `<p style="color: #ff4757;">Error: ${error.message}</p>`;
    }
}

// Export functions
async function exportCSV() {
    window.open(`${API_BASE_URL}/export/csv`, '_blank');
}

async function exportJSON() {
    window.open(`${API_BASE_URL}/export/json`, '_blank');
}

// Helper: Fetch API with error handling
async function fetchAPI(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
}

// Helper: Format numbers
function formatNumber(num, decimals = 0) {
    if (num === null || num === undefined) return '--';
    return Number(num).toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// Helper: Shorten address
function shortenAddress(address) {
    if (!address) return '--';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

// Helper: Shorten transaction hash
function shortenHash(hash) {
    if (!hash) return '--';
    return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
}

// Helper: Format timestamp
function formatTimestamp(timestamp) {
    if (!timestamp) return '--';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Helper: Show error message
function showError(message) {
    alert(message);
}

// ============================================================================
// TREVEE MULTI-CHAIN METRICS
// ============================================================================

async function refreshTreveeMetrics() {
    try {
        const treveeData = await fetchAPI('/trevee/metrics');

        if (!treveeData) {
            console.log('Trevee metrics not available');
            return;
        }

        updateTreveeStakingCards(treveeData.staking_stats);
        updateTreveeChainBreakdown(treveeData.tvl_by_chain, treveeData.enabled_chains);

    } catch (error) {
        console.error('Error fetching Trevee metrics:', error);
        // Don't show error to user - these are optional metrics
    }
}

function updateTreveeStakingCards(stakingStats) {
    if (!stakingStats) return;

    // Update staked amount
    document.getElementById('treveeStakedAmount').textContent =
        formatNumber(stakingStats.total_staked, 0) + ' TREVEE';

    // Update staking percentage
    document.getElementById('treveeStakingPercentage').textContent =
        formatNumber(stakingStats.staking_percentage, 2) + '%';
}

function updateTreveeChainBreakdown(tvlData, enabledChains) {
    if (!tvlData || !enabledChains) return;

    // Update active chains count
    document.getElementById('treveeActiveChains').textContent = enabledChains.length;

    // Update chain names
    const chainNames = enabledChains
        .map(chain => tvlData[chain]?.name || chain)
        .join(', ');
    document.getElementById('treveeChainNames').textContent = chainNames;

    // Build chain grid
    const chainGrid = document.getElementById('chainGrid');
    chainGrid.innerHTML = '';

    enabledChains.forEach(chainKey => {
        const chainData = tvlData[chainKey];
        if (!chainData) return;

        const chainItem = document.createElement('div');
        chainItem.className = 'chain-item';

        const chainEmojis = {
            'sonic': '⚡',
            'plasma': '🔷',
            'ethereum': '🌐'
        };

        // All chains show TREVEE supply + holders now
        if (chainKey === 'ethereum') {
            chainItem.innerHTML = `
                <div class="chain-name">
                    <span>${chainEmojis[chainKey] || '⛓️'}</span>
                    <span>${chainData.name}</span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">TREVEE Supply:</span>
                    <span class="chain-stat-value">
                        ${chainData.total_supply !== null && chainData.total_supply !== undefined ? formatNumber(chainData.total_supply, 0) + ' TREVEE' : 'Not deployed'}
                    </span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">Holders:</span>
                    <span class="chain-stat-value">
                        ${chainData.holder_count !== null && chainData.holder_count !== undefined ? formatNumber(chainData.holder_count, 0) : 'Calculating...'}
                    </span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">PAL Migrated:</span>
                    <span class="chain-stat-value">
                        ${chainData.pal_migrated ? formatNumber(chainData.pal_migrated, 0) + ' PAL' : '0 PAL'}
                    </span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">Explorer:</span>
                    <span class="chain-stat-value">
                        <a href="${chainData.explorer}" target="_blank" style="color: var(--accent-primary); text-decoration: none;">
                            View →
                        </a>
                    </span>
                </div>
            `;
        } else {
            chainItem.innerHTML = `
                <div class="chain-name">
                    <span>${chainEmojis[chainKey] || '⛓️'}</span>
                    <span>${chainData.name}</span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">Total Supply:</span>
                    <span class="chain-stat-value">
                        ${chainData.total_supply ? formatNumber(chainData.total_supply, 0) + ' TREVEE' : 'Not configured'}
                    </span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">Staked Amount:</span>
                    <span class="chain-stat-value">
                        ${chainData.staked_amount !== null && chainData.staked_amount !== undefined ? formatNumber(chainData.staked_amount, 0) + ' TREVEE' : 'No staking yet'}
                    </span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">Holders:</span>
                    <span class="chain-stat-value">
                        ${chainData.holder_count ? formatNumber(chainData.holder_count, 0) : 'Coming soon'}
                    </span>
                </div>
                <div class="chain-stat">
                    <span class="chain-stat-label">Explorer:</span>
                    <span class="chain-stat-value">
                        <a href="${chainData.explorer}" target="_blank" style="color: var(--accent-primary); text-decoration: none;">
                            View →
                        </a>
                    </span>
                </div>
            `;
        }

        chainGrid.appendChild(chainItem);
    });

    // If no chains configured
    if (enabledChains.length === 0) {
        chainGrid.innerHTML = '<div class="loading">No chains configured yet. Update config.py with Trevee token addresses.</div>';
    }
}

