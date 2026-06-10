import sys
import os
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path to allow importing backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.database import Base, engine, SessionLocal
from backend.app.models import User, Incident, Log, Prediction, HistoricalReference, Recommendation, Comment, AuditLog

import bcrypt
def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def init_database():
    print("Connecting to database at:", settings.DATABASE_URL)
    
    # Force check connection and drop/create schema tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("SQL tables created successfully.")
    
    db = SessionLocal()
    try:
        # 1. Create Seed Users
        admin_pw = get_password_hash("admin123")
        support_pw = get_password_hash("support123")
        devops_pw = get_password_hash("devops123")
        
        admin_user = User(
            name="Admin User",
            email="admin@company.com",
            password_hash=admin_pw,
            role="admin"
        )
        support_user = User(
            name="Support Engineer",
            email="support@company.com",
            password_hash=support_pw,
            role="support_engineer"
        )
        devops_user = User(
            name="DevOps Engineer",
            email="devops@company.com",
            password_hash=devops_pw,
            role="devops_engineer"
        )
        
        db.add_all([admin_user, support_user, devops_user])
        db.commit()
        
        db.refresh(admin_user)
        db.refresh(support_user)
        db.refresh(devops_user)
        print("Default accounts registered:")
        print(f" - Admin: {admin_user.email}")
        print(f" - Support: {support_user.email}")
        print(f" - DevOps: {devops_user.email}")
        
        # 2. Seed Historical Resolved Incidents
        # 15 tickets to train classifiers and populate ChartJS
        now = datetime.datetime.now(datetime.timezone.utc)
        
        incidents_data = [
            {
                "title": "PostgreSQL connection pool exhaustion",
                "description": "API servers throwing 500 errors. Database connections maxed out with active transactions blocking pool.",
                "category": "database",
                "severity": "critical",
                "root_cause": "Missing db session close in transaction middleware causing connections to leak.",
                "resolution": "Update transaction middleware to wrap session in try/finally blocks and explicitly call db.close().",
                "hours_to_resolve": 1.5
            },
            {
                "title": "Redis caching service timeout on core gateway",
                "description": "Gateway microservice reporting timeout connecting to redis cache cluster, causing checkout delay.",
                "category": "database",
                "severity": "high",
                "root_cause": "High network load and bad Redis client configuration with missing keep-alive connection flags.",
                "resolution": "Enable Redis client connection keepalive and increase socket read timeouts from 100ms to 500ms.",
                "hours_to_resolve": 2.0
            },
            {
                "title": "BGP route leaking causing latency spike",
                "description": "Traffic routed through overseas transit providers instead of direct peering, latency jumped by 150ms.",
                "category": "network",
                "severity": "high",
                "root_cause": "Upstream ISP transit router misconfiguration. BGP advertisements leaked to third parties.",
                "resolution": "Set filter policies on core ingress routers to reject unapproved upstream path prepends.",
                "hours_to_resolve": 4.5
            },
            {
                "title": "Core core-switch port flapping",
                "description": "Link interfaces on rack D3 flaps up and down causing intermittent network loss for database nodes.",
                "category": "network",
                "severity": "medium",
                "root_cause": "Faulty physical fiber SFP transceiver module on switch port 24.",
                "resolution": "Replace hardware SFP optical transceiver module and clean physical fiber end-faces.",
                "hours_to_resolve": 3.0
            },
            {
                "title": "Out of memory OOM crash on auth container",
                "description": "Auth service nodes terminated by system kernel OOM killer during peak signup hours.",
                "category": "application",
                "severity": "high",
                "root_cause": "Memory leak in user profile lookup cache. Invalid cache invalidation strategy.",
                "resolution": "Migrate to LRU cache strategy and configure explicit JVM max memory heap limit flags.",
                "hours_to_resolve": 1.2
            },
            {
                "title": "Null pointer exception on invoice generation API",
                "description": "Invoice service crashes with NullPointerException when rendering invoice PDF for bulk orders.",
                "category": "application",
                "severity": "medium",
                "root_cause": "Missing handling for null fields on order discounts objects.",
                "resolution": "Add default empty object initialization and safe null checks for discounts structures in java service.",
                "hours_to_resolve": 0.8
            },
            {
                "title": "Brute-force credential stuffing attack detected",
                "description": "Spike in login failures (exceeding 200/sec) originating from distributed proxies targetting user login API.",
                "category": "security",
                "severity": "high",
                "root_cause": "Distributed automated password stuffing attack targeting exposed /api/auth/login route.",
                "resolution": "Enable login rate-limiting policy on NGINX (5 requests/minute per IP) and deploy automated fail2ban blocking.",
                "hours_to_resolve": 0.5
            },
            {
                "title": "Unauthorized API credentials scan leak",
                "description": "API keys uploaded to public GitHub repository in custom test script file.",
                "category": "security",
                "severity": "critical",
                "root_cause": "Developer committed active production secret keys in configuration file test script.",
                "resolution": "Revoke leaked API key immediately, generate a new credential, and configure Git guardian webhooks.",
                "hours_to_resolve": 0.3
            },
            {
                "title": "Disk space full on logs partition",
                "description": "Server alerts triggered. System storage on /var/log reaches 100% capacity blocking service writes.",
                "category": "infrastructure",
                "severity": "high",
                "root_cause": "Logrotate utility stopped running due to broken config syntax error.",
                "resolution": "Fix logrotate configuration syntax, purge legacy gz log files, and restart service.",
                "hours_to_resolve": 2.5
            },
            {
                "title": "EC2 instance CPU throttled due to noisy neighbors",
                "description": "Kubernetes worker node reporting extreme scheduling latency and system load spikes.",
                "category": "infrastructure",
                "severity": "medium",
                "root_cause": "AWS hypervisor host noisy neighbor. Shared compute bandwidth degraded.",
                "resolution": "Stop and start EC2 instance to force migration to a different physical hypervisor host machine.",
                "hours_to_resolve": 1.8
            },
            {
                "title": "SQL query deadlock on orders table during flash sale",
                "description": "Concurrent transactions updating order row locks resulting in database transaction timeouts.",
                "category": "database",
                "severity": "high",
                "root_cause": "Orders table locked due to inconsistent locking order in transactional update routes.",
                "resolution": "Enforce sorted transaction locks execution flow inside cart/invoice update scripts.",
                "hours_to_resolve": 1.1
            },
            {
                "title": "DNS resolution timeouts on backend pods",
                "description": "Service-to-service calls fail randomly with temporary host lookup failures.",
                "category": "network",
                "severity": "high",
                "root_cause": "CoreDNS pods overloaded with queries due to bad Kubernetes service endpoints caching.",
                "resolution": "Increase CoreDNS replicas count and enable NodeLocal DNSCache configurations.",
                "hours_to_resolve": 1.9
            },
            {
                "title": "Static asset CDN delivery failure",
                "description": "Frontend static components fail to fetch with TLS handshake errors on client browsers.",
                "category": "infrastructure",
                "severity": "medium",
                "root_cause": "CDN edge SSL certificates expired. Automation cron failed to update certs.",
                "resolution": "Manually re-trigger CDN certificate generation script and verify auto-renew crontab script permissions.",
                "hours_to_resolve": 0.6
            },
            {
                "title": "Nginx gateway proxy timeout on uploads",
                "description": "File uploads above 5MB result in 504 Gateway Timeout responses.",
                "category": "application",
                "severity": "low",
                "root_cause": "Default client_max_body_size restriction and low proxy_read_timeout set on proxy.",
                "resolution": "Set client_max_body_size to 20M and increase proxy_read_timeout limit in gateway configs.",
                "hours_to_resolve": 0.4
            },
            {
                "title": "Docker daemon runtime disk allocation exhaustion",
                "description": "Docker daemon crashes and cannot run containers. No space left on overlay2 storage partition.",
                "category": "infrastructure",
                "severity": "high",
                "root_cause": "Orphaned containers, unused networks, and dangling layer images accumulated over months.",
                "resolution": "Execute 'docker system prune -a --volumes' and expand storage volumes partitions sizing.",
                "hours_to_resolve": 2.2
            }
        ]
        
        for data in incidents_data:
            created_at = now - datetime.timedelta(days=float(uuid.uuid4().int % 30) + 1)
            resolved_at = created_at + datetime.timedelta(hours=data["hours_to_resolve"])
            
            inc = Incident(
                title=data["title"],
                description=data["description"],
                status="resolved",
                severity=data["severity"],
                category=data["category"],
                root_cause=data["root_cause"],
                assigned_to=devops_user.id if data["category"] in ["network", "infrastructure"] else support_user.id,
                created_by=admin_user.id,
                created_at=created_at,
                updated_at=resolved_at,
                resolved_at=resolved_at
            )
            db.add(inc)
            db.commit()
            db.refresh(inc)
            
            # Seed corresponding recommendation text
            rec = Recommendation(
                incident_id=inc.id,
                recommendation_text=f"Past Solution applied:\n{data['resolution']}"
            )
            db.add(rec)
            db.commit()
            
        print(f"Seeded {len(incidents_data)} resolved historic tickets successfully.")
        
    except Exception as e:
        db.rollback()
        print("Database seeding encountered an error:", e)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
