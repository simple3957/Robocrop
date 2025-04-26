// Function to update the dashboard with new data
function updateDashboard(data) {
    // Update sensor readings
    document.getElementById('soil-temp').textContent = `${data.soil_temperature}`;
    document.getElementById('soil-moisture').textContent = `${data.soil_moisture}`;
    document.getElementById('humidity').textContent = `${data.humidity}`;

    // Update irrigation status
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    statusIndicator.classList.toggle('active', data.irrigation_status === 'ON');
    statusText.textContent = data.irrigation_status;

    // Update schedule inputs
    document.getElementById('start-time').value = data.schedule.start_time;
    document.getElementById('end-time').value = data.schedule.end_time;

    // Update pest data
    const pestDataDiv = document.getElementById('pest-data');
    if (Object.keys(data.pest_data).length > 0) {
        let pestHtml = '<ul class="list-unstyled">';
        for (const [pest, count] of Object.entries(data.pest_data)) {
            pestHtml += `<li>${pest}: ${count} detected</li>`;
        }
        pestHtml += '</ul>';
        pestDataDiv.innerHTML = pestHtml;
    } else {
        pestDataDiv.innerHTML = '<p>No pest activity detected</p>';
    }

        // Update recommendations
    // Dummy data for testing
const dummyData = {
    recommendations: [
        {
            type: 'warning',
            message: 'Soil moisture is very low. Immediate irrigation recommended.',
            action: 'Start irrigation system'
        },
        {
            type: 'info',
            message: 'High humidity detected. Reduced water evaporation.',
            action: 'Consider reducing irrigation duration'
        },
        {
            type: 'critical',
            message: 'Critical conditions: Low moisture, high temperature, and low humidity.',
            action: 'Immediate irrigation recommended'
        },
        {
            type: 'success',
            message: 'Soil moisture is at optimal level.',
            action: 'No action needed'
        }
    ]
};

// Simulate rendering recommendations with dummy data
const recommendationsDiv = document.getElementById('recommendations');
if (Array.isArray(dummyData.recommendations) && dummyData.recommendations.length > 0) {
    let recommendationsHtml = '<div class="list-group">';
    dummyData.recommendations.forEach(rec => {
        const badgeClass = rec.type === 'warning' ? 'bg-warning' : 
                          rec.type === 'info' ? 'bg-info' : 
                          rec.type === 'critical' ? 'bg-danger' : 'bg-success';
        recommendationsHtml += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-center">
                    <span class="badge ${badgeClass} me-2">${rec.type.toUpperCase()}</span>
                    <p class="mb-1">${rec.message}</p>
                </div>
                <small class="text-muted">${rec.action}</small>
            </div>
        `;
    });
    recommendationsHtml += '</div>';
    recommendationsDiv.innerHTML = recommendationsHtml;
} else {
    recommendationsDiv.innerHTML = '<p class="text-muted">No recommendations available at the moment.</p>';
}
    // Update last update time
    document.getElementById('last-update').textContent = `Last Update: ${data.timestamp}`;

    // Update AI status
    const aiStatusDiv = document.getElementById('ai-status');
    aiStatusDiv.innerHTML = `<span class="badge ${data.irrigation_status === 'ON' ? 'bg-success' : 'bg-warning'}">
        AI ${data.irrigation_status === 'ON' ? 'recommends' : 'does not recommend'} irrigation
    </span>`;

    // Update button states based on current status
    document.getElementById('turn-on').disabled = data.irrigation_status === 'ON';
    document.getElementById('turn-off').disabled = data.irrigation_status === 'OFF';
}

// Function to fetch data from the API
async function fetchData() {
    try {
        const response = await fetch('http://localhost:5000/api/data'); // Update URL if needed
        const data = await response.json();
        console.log('Fetched data:', data);
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}
// Function to update schedule
async function updateSchedule() {
    const startTime = document.getElementById('start-time').value;
    const endTime = document.getElementById('end-time').value;

    try {
        const response = await fetch('http://<correct-host>:<correct-port>/api/data');

        if (!response.ok) {
            throw new Error('Failed to update schedule');
        }

        const result = await response.json();
        alert('Schedule updated successfully!');
    } catch (error) {
        console.error('Error updating schedule:', error);
        alert('Failed to update schedule. Please try again.');
    }
}

// Function to control irrigation
async function controlIrrigation(status) {
    try {
        const response = await fetch('/api/irrigation/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status })
        });

        if (!response.ok) {
            throw new Error('Failed to control irrigation');
        }

        await fetchData(); // Refresh data after status change
    } catch (error) {
        console.error('Error controlling irrigation:', error);
        alert('Failed to control irrigation. Please try again.');
    }
}

// Function to set auto mode
async function setAutoMode() {
    try {
        const response = await fetch('/api/irrigation/auto', {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to set auto mode');
        }

        await fetchData(); // Refresh data after mode change
        alert('Switched to automatic mode');
    } catch (error) {
        console.error('Error setting auto mode:', error);
        alert('Failed to switch to automatic mode. Please try again.');
    }
}

// Add event listeners
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('turn-on').addEventListener('click', () => controlIrrigation('ON'));
    document.getElementById('turn-off').addEventListener('click', () => controlIrrigation('OFF'));
    document.getElementById('auto-mode').addEventListener('click', setAutoMode);
    document.getElementById('update-schedule').addEventListener('click', updateSchedule);

    // Initial data fetch
    fetchData();
    // Set up periodic refresh
    setInterval(fetchData, 30000);
}); 