const express = require('express');
const jwt = require('jsonwebtoken');
const db = require('../db');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7';

// Auth Middleware
const authenticate = (req, res, next) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ detail: "Not authenticated" });
  }
  const token = authHeader.split(' ')[1];
  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (err) {
    return res.status(401).json({ detail: "Invalid token" });
  }
};

router.use(authenticate);

// Get Dashboard Analytics
router.get('/dashboard', async (req, res) => {
  try {
    // 1. Total Incidents
    const totalRes = await db.query('SELECT COUNT(*) FROM incidents');
    const total = parseInt(totalRes.rows[0].count);

    // 2. Status counts (Open, In Progress, Resolved, Closed, Archived)
    const statusRes = await db.query('SELECT status, COUNT(*) FROM incidents GROUP BY status');
    const status_counts = {
      open: 0,
      in_progress: 0,
      resolved: 0,
      closed: 0,
      archived: 0
    };
    statusRes.rows.forEach(r => {
      status_counts[r.status] = parseInt(r.count);
    });

    const active_tickets = status_counts.open + status_counts.in_progress;

    // 3. Category distribution (Network, Application, Security, Infrastructure, Database)
    const catRes = await db.query('SELECT category, COUNT(*) FROM incidents GROUP BY category');
    const category_counts = {};
    catRes.rows.forEach(r => category_counts[r.category] = parseInt(r.count));

    // 4. Severity counts
    const sevRes = await db.query('SELECT severity, COUNT(*) FROM incidents GROUP BY severity');
    const severity_counts = {};
    sevRes.rows.forEach(r => severity_counts[r.severity] = parseInt(r.count));

    // 5. Weekly Trends
    const trendsRes = await db.query(`
      SELECT 
        DATE(created_at) as date,
        COUNT(*) as created,
        SUM(CASE WHEN status IN ('resolved', 'closed') THEN 1 ELSE 0 END) as resolved
      FROM incidents
      WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
      GROUP BY DATE(created_at)
      ORDER BY DATE(created_at) ASC
    `);
    
    // 6. Team Performance
    const teamRes = await db.query(`
      SELECT 
        u.name, 
        u.role,
        COUNT(i.id) FILTER (WHERE i.status IN ('open', 'in_progress')) as assigned_active,
        COUNT(i.id) FILTER (WHERE i.status IN ('resolved', 'closed')) as resolved
      FROM users u
      LEFT JOIN incidents i ON u.id = i.assigned_to
      WHERE u.role = 'support_engineer' OR u.role = 'admin'
      GROUP BY u.id, u.name, u.role
    `);

    res.json({
      active_tickets: active_tickets,
      mttr_minutes: 45.5, // Placeholder metric for Mean Time To Resolve
      status_counts: status_counts,
      category_counts: category_counts,
      severity_counts: severity_counts,
      weekly_trends: trendsRes.rows,
      team_performance: teamRes.rows
    });

  } catch (error) {
    console.error("Dashboard analytics error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

module.exports = router;
