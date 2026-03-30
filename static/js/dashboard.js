document.addEventListener('DOMContentLoaded', () => {
    const runBtn = document.getElementById('run-audit-btn');
    const feedBox = document.getElementById('live-feed');
    const logsContainer = document.getElementById('feed-logs');
    
    // UI Elements for stats
    const statTotal = document.getElementById('stat-total');
    const statGhosts = document.getElementById('stat-ghosts');
    const statMonthly = document.getElementById('stat-monthly');
    const statAnnual = document.getElementById('stat-annual');
    const membersTbody = document.getElementById('members-tbody');
    
    let isPolling = false;
    let pollInterval = null;

    if (runBtn) {
        runBtn.addEventListener('click', async () => {
            runBtn.disabled = true;
            runBtn.innerHTML = 'Starting Audit...';
            
            try {
                const res = await fetch('/audit', { method: 'POST' });
                const data = await res.json();
                
                if (data.status === 'started' || data.status === 'already_running') {
                    startPolling();
                } else {
                    alert('Could not start audit: ' + (data.error || 'Unknown error'));
                    runBtn.disabled = false;
                    runBtn.innerHTML = 'Run Live Audit';
                }
            } catch (err) {
                console.error(err);
                alert('Connection error starting audit.');
                runBtn.disabled = false;
                runBtn.innerHTML = 'Run Live Audit';
            }
        });
    }

    function startPolling() {
        if (isPolling) return;
        isPolling = true;
        
        feedBox.style.display = 'block';
        logsContainer.innerHTML = '';
        
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.innerHTML = 'Audit Running...';
        }
        
        pollInterval = setInterval(fetchStatus, 3000);
        fetchStatus(); // immediate call
    }

    async function fetchStatus() {
        try {
            const res = await fetch('/status');
            const data = await res.json();
            
            // Render logs
            if (data.log && data.log.length > 0) {
                logsContainer.innerHTML = data.log.map(line => `<div class="feed-line">${line}</div>`).join('');
                feedBox.scrollTop = feedBox.scrollHeight;
            }
            
            if (!data.running) {
                // Done running
                clearInterval(pollInterval);
                isPolling = false;
                
                if (runBtn) {
                    runBtn.disabled = false;
                    runBtn.innerHTML = 'Run Live Audit';
                }
                
                // Keep the feed visible for a bit to read the final message
                setTimeout(() => {
                    feedBox.style.display = 'none';
                }, 10000);
                
                // Update table completely
                updateDashboardUI(data);
            }
        } catch (err) {
            console.error('Polling error', err);
        }
    }

    function updateDashboardUI(data) {
        if (!data || !data.members) return;
        
        // Update stats
        statTotal.textContent = data.total_provisioned || 0;
        statGhosts.textContent = data.inactive_ghosts || 0;
        statMonthly.textContent = `$${(data.monthly_wasted || 0).toFixed(2)}`;
        statAnnual.textContent = `$${((data.monthly_wasted || 0) * 12).toFixed(2)}`;
        
        // Render rows
        if (data.members.length === 0) {
            membersTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 40px;">No members found.</td></tr>`;
            return;
        }
        
        const rowsHtml = data.members.map(m => {
            const isInactive = m.is_inactive;
            const badge = isInactive 
                ? '<span class="badge ghost">GHOST (30+ DAYS)</span>' 
                : '<span class="badge active">ACTIVE</span>';
                
            const waste = isInactive 
                ? `<span class="waste-text">-$${(SEAT_COST || 7).toFixed(2)}</span>`
                : '<span style="color: var(--text-secondary);">-</span>';
                
            return `
                <tr>
                    <td>${m.name || 'Unknown'}</td>
                    <td style="color: var(--text-secondary);">${m.email || 'N/A'}</td>
                    <td>${badge}</td>
                    <td style="color: var(--text-secondary);">${m.last_active || 'Never'}</td>
                    <td>${waste}</td>
                </tr>
            `;
        }).join('');
        
        membersTbody.innerHTML = rowsHtml;
    }
    
    // Check initially if an audit is already running
    fetchStatus();
});
