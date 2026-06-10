const express = require('express');
const { v4: uuidv4 } = require('uuid');
const axios = require('axios');
const jwt = require('jsonwebtoken');
const db = require('../db');
const multer = require('multer');
const fs = require('fs');

const upload = multer({ dest: 'uploads/' });

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7';
const PYTHON_AI_SERVICE_URL = process.env.PYTHON_AI_SERVICE_URL || 'http://127.0.0.1:8001';

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

// Create Incident
router.post('/', async (req, res) => {
  try {
    const { title, description, category, severity, git_diff, incident_timeline } = req.body;
    
    if (!git_diff || !incident_timeline) {
      return res.status(400).json({ detail: "Git diff and incident timeline are required fields." });
    }
    
    const incidentId = uuidv4();

    // Insert to DB with actual category/severity from frontend
    const result = await db.query(
      `INSERT INTO incidents (id, title, description, status, severity, category, created_by, git_diff, incident_timeline) 
       VALUES ($1, $2, $3, 'open', $4, $5, $6, $7, $8) RETURNING *`,
      [incidentId, title, description, severity || 'medium', category || 'application', req.user.id, git_diff, incident_timeline]
    );

    // Audit Log (Fixed schema: no target_id exists in audit_logs)
    await db.query(
      `INSERT INTO audit_logs (id, user_id, action, details) VALUES ($1, $2, $3, $4)`,
      [uuidv4(), req.user.id, 'CREATE_INCIDENT', `Incident '${title}' created. ID: ${incidentId}`]
    );

    const incident = result.rows[0];
    res.status(201).json(incident);

    // TRIGGER PYTHON AI DIAGNOSTICS IN BACKGROUND
    axios.post(`${PYTHON_AI_SERVICE_URL}/api/ai/diagnostics`, { incident_id: incidentId })
         .catch(err => console.error("Failed to trigger AI diagnostics:", err.message));

  } catch (error) {
    console.error("Create incident error:", error.message, error.stack);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// List Incidents
router.get('/', async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const offset = (page - 1) * limit;

    let queryStr = `
      SELECT i.*, 
             json_build_object('id', u1.id, 'name', u1.name, 'role', u1.role) as creator,
             CASE WHEN i.assigned_to IS NOT NULL THEN json_build_object('id', u2.id, 'name', u2.name, 'role', u2.role) ELSE null END as assignee
      FROM incidents i
      LEFT JOIN users u1 ON i.created_by = u1.id
      LEFT JOIN users u2 ON i.assigned_to = u2.id
      WHERE 1=1
    `;
    const params = [];
    let paramCount = 1;

    // Support engineers can now see all tickets (restriction removed per user request)
    // if (req.user.role === 'support_engineer') {
    //   queryStr += ` AND assigned_to = $${paramCount++}`;
    //   params.push(req.user.id);
    // }

    if (req.query.status) { queryStr += ` AND i.status = $${paramCount++}`; params.push(req.query.status); }
    if (req.query.severity) { queryStr += ` AND i.severity = $${paramCount++}`; params.push(req.query.severity); }
    if (req.query.category) { queryStr += ` AND i.category = $${paramCount++}`; params.push(req.query.category); }
    if (req.query.search) {
      queryStr += ` AND (i.title ILIKE $${paramCount} OR i.description ILIKE $${paramCount} OR i.id::text ILIKE $${paramCount})`;
      params.push(`%${req.query.search}%`);
      paramCount++;
    }

    const countResult = await db.query(`SELECT COUNT(*) FROM (${queryStr}) as t`, params);
    const total = parseInt(countResult.rows[0].count);

    queryStr += ` ORDER BY i.created_at DESC LIMIT $${paramCount++} OFFSET $${paramCount++}`;
    params.push(limit, offset);

    const result = await db.query(queryStr, params);

    res.json({
      total, page, limit, data: result.rows
    });
  } catch (error) {
    console.error("List incidents error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Get Incident Detail
router.get('/:id', async (req, res) => {
  try {
    const result = await db.query('SELECT * FROM incidents WHERE id = $1', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ detail: "Incident not found" });
    
    const incident = result.rows[0];
    // Support engineers can view details (restriction removed)
    // if (req.user.role === 'support_engineer' && incident.assigned_to !== req.user.id) {
    //   return res.status(403).json({ detail: "Access denied" });
    // }

    // Also fetch relationships
    const creator = await db.query('SELECT id, name, role FROM users WHERE id = $1', [incident.created_by]);
    const logs = await db.query('SELECT * FROM logs WHERE incident_id = $1 ORDER BY uploaded_at DESC', [incident.id]);
    const comments = await db.query(`
      SELECT c.*, json_build_object('id', u.id, 'name', u.name, 'role', u.role) as user 
      FROM comments c JOIN users u ON c.user_id = u.id 
      WHERE c.incident_id = $1 ORDER BY c.created_at ASC
    `, [incident.id]);
    const predictions = await db.query('SELECT * FROM predictions WHERE incident_id = $1 ORDER BY created_at DESC', [incident.id]);
    const recommendations = await db.query('SELECT * FROM recommendations WHERE incident_id = $1 ORDER BY created_at DESC', [incident.id]);
    const rcas = await db.query('SELECT * FROM rcas WHERE incident_id = $1 ORDER BY created_at DESC', [incident.id]);
    const histRefs = await db.query(`
      SELECT hr.*, i.title, i.category, i.severity, i.root_cause as fix 
      FROM historical_references hr 
      JOIN incidents i ON hr.historical_incident_id = i.id 
      WHERE hr.incident_id = $1 
      ORDER BY hr.similarity_score DESC
    `, [incident.id]);

    incident.creator = creator.rows[0];
    incident.logs = logs.rows;
    incident.comments = comments.rows;
    incident.predictions = predictions.rows;
    incident.recommendations = recommendations.rows;
    incident.rcas = rcas.rows;
    incident.historical_references = histRefs.rows;

    res.json(incident);
  } catch (error) {
    console.error("Get incident error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Update Status
router.put('/:id/status', async (req, res) => {
  try {
    const { status, assigned_to } = req.body;
    let updateFields = [];
    let params = [];
    let paramCount = 1;

    if (status) {
      updateFields.push(`status = $${paramCount++}`);
      params.push(status);
      if (status === 'resolved' || status === 'closed') {
        updateFields.push(`resolved_at = CURRENT_TIMESTAMP`);
      }
    }
    if (assigned_to) {
      if (req.user.role !== 'admin') return res.status(403).json({ detail: "Only admins can reassign" });
      updateFields.push(`assigned_to = $${paramCount++}`);
      params.push(assigned_to);
    }

    if (updateFields.length === 0) return res.json({});

    updateFields.push(`updated_at = CURRENT_TIMESTAMP`);
    params.push(req.params.id);

    const result = await db.query(
      `UPDATE incidents SET ${updateFields.join(', ')} WHERE id = $${paramCount} RETURNING *`,
      params
    );

    res.json(result.rows[0]);
  } catch (error) {
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Post RCA Trigger
router.post('/:id/rca', async (req, res) => {
  try {
    const result = await db.query('SELECT * FROM incidents WHERE id = $1', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ detail: "Incident not found" });
    const incident = result.rows[0];

    if (incident.status !== 'resolved' && incident.status !== 'closed') {
      return res.status(400).json({ detail: "Incident must be resolved to generate an RCA." });
    }

    // Trigger Python AI microservice to do the heavy lifting
    const aiResponse = await axios.post(`${PYTHON_AI_SERVICE_URL}/api/ai/generate_rca`, {
      incident_id: incident.id,
      user_id: req.user.id
    });

    res.json(aiResponse.data);
  } catch (error) {
    console.error("RCA Trigger error:", error.response ? error.response.data : error.message);
    res.status(500).json({ detail: "Failed to generate RCA via AI Microservice." });
  }
});

// Post Comment (Timeline)
router.post('/:id/comments', async (req, res) => {
  try {
    const { content } = req.body;
    if (!content) return res.status(400).json({ detail: "Content is required" });

    const result = await db.query(
      'INSERT INTO comments (id, incident_id, user_id, content) VALUES ($1, $2, $3, $4) RETURNING *',
      [uuidv4(), req.params.id, req.user.id, content]
    );

    res.status(201).json(result.rows[0]);
  } catch (error) {
    console.error("Post comment error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Post Log (Telemetry)
router.post('/:id/logs', upload.array('files', 5), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ detail: "No files uploaded" });
    }

    const uploadedLogs = [];

    for (const file of req.files) {
      const content = fs.readFileSync(file.path, 'utf8');

      // 1. Send to AI Microservice to parse telemetry
      let parsedData = {};
      try {
        const aiResponse = await axios.post(`${PYTHON_AI_SERVICE_URL}/api/ai/parse_logs`, {
          incident_id: req.params.id,
          raw_text: content
        });
        parsedData = aiResponse.data;
      } catch (err) {
        console.error("Failed to parse logs via AI. Saving raw format.", err.message);
        parsedData = { summary: "Raw log snippet: " + content.substring(0, 100) + "..." };
      }

      // 2. Save to DB
      const result = await db.query(
        'INSERT INTO logs (id, incident_id, filename, file_path, parsed_content) VALUES ($1, $2, $3, $4, $5) RETURNING *',
        [uuidv4(), req.params.id, file.originalname, file.path, parsedData]
      );
      uploadedLogs.push(result.rows[0]);
    }

    res.status(201).json({ detail: "Logs uploaded successfully", logs: uploadedLogs });
  } catch (error) {
    console.error("Post logs error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

module.exports = router;
