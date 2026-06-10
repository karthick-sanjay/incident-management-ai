// --- DASHBOARD CHARTS LIFECYCLE MANAGEMENT ---

let trendsChart = null;
let severityChart = null;
let categoryChart = null;

function renderDashboardCharts(analytics) {
  // 1. WEEKLY TRENDS LINE CHART
  const trendsCtx = document.getElementById("chart-trends");
  if (trendsCtx && analytics.weekly_trends) {
    const dates = analytics.weekly_trends.map(t => t.date);
    const created = analytics.weekly_trends.map(t => t.created);
    const resolved = analytics.weekly_trends.map(t => t.resolved);
    
    if (trendsChart) trendsChart.destroy();
    
    trendsChart = new Chart(trendsCtx, {
      type: "line",
      data: {
        labels: dates,
        datasets: [
          {
            label: "Opened Tickets",
            data: created,
            borderColor: "#3B82F6",
            backgroundColor: "rgba(59, 130, 246, 0.05)",
            tension: 0.2,
            borderWidth: 2,
            fill: true
          },
          {
            label: "Resolved Tickets",
            data: resolved,
            borderColor: "#10B981",
            backgroundColor: "rgba(16, 185, 129, 0.05)",
            tension: 0.2,
            borderWidth: 2,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { font: { family: "Inter", size: 12 } } }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 } } },
          y: { grid: { color: "#F1F5F9" }, ticks: { font: { family: "Inter", size: 11 }, stepSize: 1 } }
        }
      }
    });
  }

  // 2. SEVERITY DOUGHNUT CHART
  const severityCtx = document.getElementById("chart-severity");
  if (severityCtx && analytics.severity_counts) {
    const labels = ["Low", "Medium", "High", "Critical"];
    const counts = [
      analytics.severity_counts.low || 0,
      analytics.severity_counts.medium || 0,
      analytics.severity_counts.high || 0,
      analytics.severity_counts.critical || 0
    ];
    
    if (severityChart) severityChart.destroy();
    
    severityChart = new Chart(severityCtx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: counts,
            backgroundColor: ["#3B82F6", "#F59E0B", "#EF4444", "#DC2626"],
            borderWidth: 2,
            borderColor: "#FFFFFF"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: { position: "bottom", labels: { font: { family: "Inter", size: 12 }, boxWidth: 12 } }
        }
      }
    });
  }

  // 3. CATEGORIES BAR CHART
  const categoryCtx = document.getElementById("chart-category");
  if (categoryCtx && analytics.category_counts) {
    const labels = ["Database", "Network", "Application", "Security", "Infrastructure"];
    const counts = [
      analytics.category_counts.database || 0,
      analytics.category_counts.network || 0,
      analytics.category_counts.application || 0,
      analytics.category_counts.security || 0,
      analytics.category_counts.infrastructure || 0
    ];
    
    if (categoryChart) categoryChart.destroy();
    
    categoryChart = new Chart(categoryCtx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Incident Volume",
            data: counts,
            backgroundColor: "#3D5A80",
            borderRadius: 4,
            barThickness: 24
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 } } },
          y: { grid: { color: "#F1F5F9" }, ticks: { font: { family: "Inter", size: 11 }, stepSize: 1 } }
        }
      }
    });
  }
}
