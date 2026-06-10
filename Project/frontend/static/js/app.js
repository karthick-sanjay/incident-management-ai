// --- API BASE PATH CONFIGURATION ---
const API_BASE = ""; 

// Auth JWT check & Redirect Guard
function checkSession() {
  const token = localStorage.getItem("token");
  const path = window.location.pathname;
  
  const isAuthPage = path.includes("login.html") || path.includes("register.html");
  
  if (!token && !isAuthPage) {
    window.location.href = "login.html";
  } else if (token && isAuthPage) {
    window.location.href = "index.html";
  }
}

// Get request auth headers
function getAuthHeaders(isMultipart = false) {
  const token = localStorage.getItem("token");
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!isMultipart) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

// Log out user
function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.href = "login.html";
}

// Parse user info and update sidebar details
function updateUserInfo() {
  const userStr = localStorage.getItem("user");
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      const nameEl = document.getElementById("user-name-display");
      const roleEl = document.getElementById("user-role-display");
      if (nameEl) nameEl.textContent = user.name;
      if (roleEl) {
        // Format role
        roleEl.textContent = user.role.replace("_", " ").toUpperCase();
      }
      
      // Enforce role-based menu items visibility
      if (user.role !== "admin") {
        const adminItems = document.querySelectorAll(".admin-only");
        adminItems.forEach(el => el.style.display = "none");
      }
    } catch (e) {
      console.error("Failed to parse user details:", e);
    }
  }
}

// Alerts helpers
function showAlert(containerId, message, type = "success") {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const alertEl = document.createElement("div");
  alertEl.className = `alert alert-${type}`;
  alertEl.textContent = message;
  
  // Clear previous and append new
  container.innerHTML = "";
  container.appendChild(alertEl);
}

// Run checks on page loads
document.addEventListener("DOMContentLoaded", () => {
  checkSession();
  updateUserInfo();
});
