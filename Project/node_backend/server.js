const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const authRoutes = require('./routes/auth');
const incidentRoutes = require('./routes/incidents');

const userRoutes = require('./routes/users');
const analyticsRoutes = require('./routes/analytics');

const app = express();
const PORT = process.env.PORT || 8000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/incidents', incidentRoutes);
app.use('/api/users', userRoutes);
app.use('/api/analytics', analyticsRoutes);

// Health Route
app.get('/api/health', (req, res) => {
  res.json({ status: "ok" });
});

// Serve Frontend Static Files
const frontendDir = path.join(__dirname, '..', 'frontend');
app.use(express.static(frontendDir));

// Fallback for single page apps or html files
app.use((req, res) => {
  res.sendFile(path.join(frontendDir, 'login.html'));
});

app.listen(PORT, () => {
  console.log(`Node.js API Gateway & Frontend Server running on http://127.0.0.1:${PORT}`);
});
