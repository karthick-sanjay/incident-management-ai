const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const { validate } = require('deep-email-validator');
const db = require('../db');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7';

// Middleware to parse urlencoded for login matching FastAPI's OAuth2PasswordRequestForm
router.use(express.urlencoded({ extended: true }));
router.use(express.json());

// Registration
router.post('/register', async (req, res) => {
  try {
    const { email, password, name, department, role } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ detail: "Email and password are required" });
    }

    // 1. Strict Email Verification (Checking Domain MX Records)
    const emailValidation = await validate({
      email: email,
      validateRegex: true,
      validateMx: false, // Disabled due to local network DNS blocking (throws Reason: mx on valid emails)
      validateTypo: true,
      validateDisposable: true,
      validateSMTP: false
    });

    if (!emailValidation.valid) {
      return res.status(400).json({ 
        detail: `Email verification failed. This does not appear to be a valid or working email address. Reason: ${emailValidation.reason}`
      });
    }

    // 2. Check if user already exists
    const existing = await db.query('SELECT id FROM users WHERE email = $1', [email]);
    if (existing.rows.length > 0) {
      return res.status(400).json({ detail: "Email already registered" });
    }

    // 3. Hash Password & Insert
    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = uuidv4();
    const result = await db.query(
      `INSERT INTO users (id, email, password_hash, name, role) 
       VALUES ($1, $2, $3, $4, $5) RETURNING id, email, name as full_name, role`,
      [userId, email, hashedPassword, name, role || 'support_engineer']
    );

    res.status(201).json(result.rows[0]);

  } catch (error) {
    console.error("Registration error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Login
router.post('/login', async (req, res) => {
  try {
    // FastAPI OAuth2PasswordRequestForm uses 'username' field for email, but the frontend sends 'email'
    const email = req.body.username || req.body.email;
    const password = req.body.password;

    if (!email || !password) {
      return res.status(400).json({ detail: "Incorrect email or password" });
    }

    const result = await db.query('SELECT * FROM users WHERE email = $1', [email]);
    if (result.rows.length === 0) {
      return res.status(401).json({ detail: "Incorrect email or password" });
    }

    const user = result.rows[0];
    const passwordMatch = await bcrypt.compare(password, user.password_hash);
    
    if (!passwordMatch) {
      return res.status(401).json({ detail: "Incorrect email or password" });
    }

    // Generate JWT
    const token = jwt.sign(
      { sub: user.email, id: user.id, role: user.role },
      JWT_SECRET,
      { expiresIn: '24h' }
    );

    res.json({
      access_token: token,
      token_type: 'bearer',
      user: {
        id: user.id,
        name: user.name,
        role: user.role
      }
    });

  } catch (error) {
    console.error("Login error:", error);
    res.status(500).json({ detail: "Internal Server Error" });
  }
});

// Get Current User (Auth Check)
router.get('/me', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ detail: "Not authenticated" });
    }

    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, JWT_SECRET);
    
    const result = await db.query('SELECT id, email, name as full_name, role FROM users WHERE id = $1', [decoded.id]);
    if (result.rows.length === 0) {
      return res.status(401).json({ detail: "User not found" });
    }

    res.json(result.rows[0]);
  } catch (error) {
    return res.status(401).json({ detail: "Could not validate credentials" });
  }
});

module.exports = router;
