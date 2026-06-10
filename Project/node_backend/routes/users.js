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

// Get All Users (Admin view)
router.get('/', async (req, res) => {
  try {
    const result = await db.query('SELECT id, name, email, role FROM users ORDER BY name ASC');
    res.json(result.rows);
  } catch (error) {
    console.error("List users error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Get Engineers (for assignment dropdown)
router.get('/engineers', async (req, res) => {
  try {
    const result = await db.query("SELECT id, name, email, role FROM users WHERE role IN ('support_engineer', 'devops_engineer', 'admin') ORDER BY name ASC");
    res.json(result.rows);
  } catch (error) {
    console.error("Get engineers error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Change User Role (Admin only)
router.put('/:id/role', async (req, res) => {
  try {
    if (req.user.role !== 'admin') {
      return res.status(403).json({ detail: "Only admins can change roles" });
    }
    const { role } = req.query; // Frontend uses query param: ?role=xyz
    if (!role) {
      return res.status(400).json({ detail: "Role parameter required" });
    }
    
    const result = await db.query(
      'UPDATE users SET role = $1 WHERE id = $2 RETURNING id, name, email, role',
      [role, req.params.id]
    );
    res.json(result.rows[0]);
  } catch (error) {
    console.error("Change role error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

module.exports = router;
