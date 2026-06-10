import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.incident import Incident
from backend.app.models.user import User
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard")
def get_dashboard_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Total counts by status
    status_counts = db.query(
        Incident.status, func.count(Incident.id)
    ).group_by(Incident.status).all()
    status_map = {status: count for status, count in status_counts}
    
    # Fill defaults
    for status in ["open", "in_progress", "resolved", "closed", "archived"]:
        if status not in status_map:
            status_map[status] = 0
            
    active_count = status_map["open"] + status_map["in_progress"]
    
    # 2. MTTR (Mean Time to Resolution)
    # Filter by resolved tickets
    resolved_incidents = db.query(Incident).filter(
        Incident.resolved_at.isnot(None),
        Incident.created_at.isnot(None)
    ).all()
    
    total_time_minutes = 0.0
    mttr_val = 0.0
    if resolved_incidents:
        for inc in resolved_incidents:
            diff = inc.resolved_at - inc.created_at
            total_time_minutes += diff.total_seconds() / 60.0
        mttr_val = round(total_time_minutes / len(resolved_incidents), 1)
        
    # 3. Severity Distribution
    severity_counts = db.query(
        Incident.severity, func.count(Incident.id)
    ).group_by(Incident.severity).all()
    severity_map = {sev: count for sev, count in severity_counts}
    for sev in ["low", "medium", "high", "critical"]:
        if sev not in severity_map:
            severity_map[sev] = 0
            
    # 4. Category Distribution
    category_counts = db.query(
        Incident.category, func.count(Incident.id)
    ).group_by(Incident.category).all()
    category_map = {cat: count for cat, count in category_counts}
    for cat in ["database", "network", "application", "security", "infrastructure"]:
        if cat not in category_map:
            category_map[cat] = 0
            
    # 5. Weekly Trends (Last 7 days)
    weekly_trends = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for i in range(6, -1, -1):
        day = now - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day.date(), datetime.time.min, tzinfo=datetime.timezone.utc)
        day_end = datetime.datetime.combine(day.date(), datetime.time.max, tzinfo=datetime.timezone.utc)
        
        created = db.query(Incident).filter(
            Incident.created_at >= day_start,
            Incident.created_at <= day_end
        ).count()
        
        resolved = db.query(Incident).filter(
            Incident.resolved_at >= day_start,
            Incident.resolved_at <= day_end
        ).count()
        
        weekly_trends.append({
            "date": day.strftime("%Y-%m-%d"),
            "created": created,
            "resolved": resolved
        })
        
    # 6. Team Performance (Top assignees workload)
    team_data = []
    engineers = db.query(User).filter(User.role.in_(["support_engineer", "devops_engineer"])).all()
    for eng in engineers:
        assigned = db.query(Incident).filter(Incident.assigned_to == eng.id, Incident.status.in_(["open", "in_progress"])).count()
        resolved = db.query(Incident).filter(Incident.assigned_to == eng.id, Incident.status == "resolved").count()
        team_data.append({
            "name": eng.name,
            "role": eng.role,
            "assigned_active": assigned,
            "resolved": resolved
        })
        
    return {
        "active_tickets": active_count,
        "mttr_minutes": mttr_val,
        "status_counts": status_map,
        "severity_counts": severity_map,
        "category_counts": category_map,
        "weekly_trends": weekly_trends,
        "team_performance": team_data
    }
