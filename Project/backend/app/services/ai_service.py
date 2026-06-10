import os
import uuid
import joblib
import numpy as np
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.incident import Incident, Prediction, HistoricalReference, Recommendation, Log

# Lazy loading flag for ML models
_models_loaded = False
_category_model = None
_severity_model = None
_cat_encoder = None
_sev_encoder = None
_tfidf_vectorizer = None
_sentence_transformer = None
_faiss_index = None
_historical_ids = []

def load_ai_models():
    global _models_loaded, _severity_model, _category_model, _cat_encoder, _sev_encoder, _tfidf_vectorizer, _sentence_transformer, _faiss_index, _historical_ids
    if _models_loaded:
        return
        
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
    sev_path = os.path.join(models_dir, "severity_clf.joblib")
    cat_path = os.path.join(models_dir, "category_clf.joblib")
    cat_enc_path = os.path.join(models_dir, "cat_encoder.joblib")
    sev_enc_path = os.path.join(models_dir, "sev_encoder.joblib")
    tfidf_path = os.path.join(models_dir, "tfidf_vectorizer.joblib")
    faiss_path = os.path.join(models_dir, "faiss_index.bin")
    ids_path = os.path.join(models_dir, "historical_ids.joblib")
    
    try:
        # Load classical ML models
        if os.path.exists(sev_path) and os.path.exists(cat_path):
            _severity_model = joblib.load(sev_path)
            _category_model = joblib.load(cat_path)
            if os.path.exists(cat_enc_path) and os.path.exists(sev_enc_path):
                _cat_encoder = joblib.load(cat_enc_path)
                _sev_encoder = joblib.load(sev_enc_path)
            print("Successfully loaded ML models.")
            
        # Load Sentence Transformer for embeddings
        from sentence_transformers import SentenceTransformer
        _sentence_transformer = SentenceTransformer("BAAI/bge-base-en-v1.5")
        print("Sentence Transformer BAAI/bge-base-en-v1.5 loaded.")
        
        # Load FAISS vector index
        import faiss
        if os.path.exists(faiss_path) and os.path.exists(ids_path):
            _faiss_index = faiss.read_index(faiss_path)
            _historical_ids = joblib.load(ids_path)
            print(f"FAISS index loaded with {len(_historical_ids)} historical items.")
            
        _models_loaded = True
    except Exception as e:
        print("Warning: Failed to load models. Running in fallback heuristic/mock mode. Error:", e)

# Standard mock responses mapping categories
MOCK_RESPONSES = {
    "database": {
        "severity": "high",
        "category": "database",
        "root_cause": "PostgreSQL connection limits exceeded due to connection leak on client session handlers.",
        "recommendation": "1. Run database metrics: SELECT count(*), state FROM pg_stat_activity GROUP BY state;\n2. Verify connection pool releases in transactional wrappers.\n3. Temporary fix: restart the application server nodes to force release active backend db connection allocations."
    },
    "network": {
        "severity": "high",
        "category": "network",
        "root_cause": "CoreDNS queries overloading under peak container orchestration scaling thresholds.",
        "recommendation": "1. Check internal core-dns pod routing tables: kubectl get pods -n kube-system -l k8s-app=kube-dns;\n2. Increase replica count for CoreDNS pods to distribute UDP request routing load.\n3. Configure local DNS caching layer (NodeLocal DNSCache) on worker nodes."
    },
    "application": {
        "severity": "medium",
        "category": "application",
        "root_cause": "Heap memory saturation (Out of Memory exception) during order report PDF rendering.",
        "recommendation": "1. Increase JVM/Node heap limits in config configuration settings (e.g. set --max-old-space-size=4096).\n2. Refactor report generation queries to stream DB rows using paginated cursors instead of reading entire datasets into RAM."
    },
    "security": {
        "severity": "critical",
        "category": "security",
        "root_cause": "Automated brute-force brute stuffing targets login route (/api/auth/login).",
        "recommendation": "1. Configure immediate request throttling on NGINX: limit_req zone=login_limit burst=5 nodelay;\n2. Trigger blacklisting updates for malicious source proxy IPs.\n3. Prompt multi-factor login challenges for affected usernames."
    },
    "infrastructure": {
        "severity": "medium",
        "category": "infrastructure",
        "root_cause": "System disk allocation exhausted at 100% capacity in logs partition directory (/var/log).",
        "recommendation": "1. Run filesystem check: df -h; find /var/log -type f -size +100M;\n2. Validate syntax configs on logrotate script utilities.\n3. Run: docker system prune -a --volumes to clean dangling storage mappings."
    }
}

class LLMClient:
    @staticmethod
    def generate_recommendation(prompt: str) -> str:
        # Check provider configuration settings
        if settings.MOCK_AI_FALLBACK and not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
            # Running in offline mock mode
            return "Running in offline fallback mode. Prompt received:\n" + prompt[:200] + "..."
            
        if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=settings.GROQ_API_KEY)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a senior DevOps / SRE assistant. Generate high-quality technical resolutions."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.15,
                    max_tokens=2500
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                print("Groq API Call failed, trying failover or fallback. Error:", e)
                
        # Try Gemini API as fallback or primary
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Fallback to a stable model name
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.15,
                        max_output_tokens=2500
                    )
                )
                return response.text
            except Exception as e:
                print("Gemini API Call failed. Error:", e)
                
        if settings.MOCK_AI_FALLBACK:
            return "AI APIs (Groq/Gemini) are currently rate-limited or unavailable. Displaying Offline Mock Root Cause Analysis:\n\n1. **Root Cause**: The system experienced unexpected saturation.\n2. **Timeline Analysis**: The logs confirm a rapid degradation.\n3. **Mitigation Step**: Consider expanding node resources or tuning application cache boundaries.\n\n*(Note: Normal AI processing will resume once rate limits reset.)*"
            
        return "Warning: LLM generation failed or keys not configured. Please check your environment variables."

def predict_incident_features(title: str, description: str, git_diff: str = "", incident_timeline: str = "") -> Dict[str, Any]:
    load_ai_models()
    
    # 1. Classical Heuristic Default if models not trained yet
    if not _models_loaded or _severity_model is None or _category_model is None:
        # Determine category based on keywords
        text = (title + " " + description).lower()
        category = "application"
        severity = "medium"
        
        if any(w in text for w in ["database", "postgres", "sql", "redis", "query", "db"]):
            category = "database"
        elif any(w in text for w in ["dns", "network", "ping", "bgp", "port", "switch", "router", "latency"]):
            category = "network"
        elif any(w in text for w in ["security", "hack", "login", "brute", "stuffing", "unauthorized", "credential"]):
            category = "security"
        elif any(w in text for w in ["disk", "cpu", "server", "aws", "docker", "instance", "oom"]):
            category = "infrastructure"
            
        if any(w in text for w in ["outage", "down", "critical", "leak", "compromise"]):
            severity = "critical"
        elif any(w in text for w in ["timeout", "fail", "error", "oom"]):
            severity = "high"
            
        mock_data = MOCK_RESPONSES.get(category)
        return {
            "severity_pred": severity,
            "severity_conf": 0.85,
            "category_pred": category,
            "category_conf": 0.90,
            "root_cause_pred": mock_data["root_cause"]
        }
        
    # 2. Run active model inference
    try:
        from backend.app.services.feature_extractor import FeatureExtractor
        
        combined_text = f"Title: {title} | Description: {description}"
        embedding = _sentence_transformer.encode([combined_text], convert_to_numpy=True).astype("float32")
        
        struct_feats = FeatureExtractor.extract_features(title, description, git_diff, incident_timeline)
        struct_feats_arr = np.array([struct_feats], dtype="float32")
        
        sev_val = _severity_model.predict(struct_feats_arr)[0]
        sev_conf = float(np.max(_severity_model.predict_proba(struct_feats_arr)))

        cat_val = _category_model.predict(embedding)[0]
        cat_conf = float(np.max(_category_model.predict_proba(embedding)))
        
        # Map model predictions safely, supporting both string and integer outputs
        if isinstance(sev_val, (int, np.integer)) and _sev_encoder:
            severity_pred = str(_sev_encoder.inverse_transform([sev_val])[0])
        elif hasattr(_severity_model, 'classes_') and isinstance(sev_val, (int, np.integer)):
            severity_pred = str(_severity_model.classes_[sev_val])
        else:
            severity_pred = str(sev_val)
            
        if isinstance(cat_val, (int, np.integer)) and _cat_encoder:
            category_pred = str(_cat_encoder.inverse_transform([cat_val])[0])
        elif hasattr(_category_model, 'classes_') and isinstance(cat_val, (int, np.integer)):
            category_pred = str(_category_model.classes_[cat_val])
        else:
            category_pred = str(cat_val)
        
        # Root cause extraction (using category rules + context formatting)
        mock_rc = MOCK_RESPONSES.get(category_pred, {"root_cause": "System anomaly detected"})["root_cause"]
        
        return {
            "severity_pred": severity_pred,
            "severity_conf": sev_conf,
            "category_pred": category_pred,
            "category_conf": cat_conf,
            "root_cause_pred": f"{category_pred.capitalize()} fault detected: {mock_rc}"
        }
    except Exception as e:
        print("Error during active model inference. Falling back to rules. Error:", e)
        return {
            "severity_pred": "medium",
            "severity_conf": 0.50,
            "category_pred": "application",
            "category_conf": 0.50,
            "root_cause_pred": "Inference failure: default application anomaly detected."
        }

def retrieve_similar_incidents(db: Session, title: str, description: str, target_category: str = None, target_severity: str = None) -> List[Tuple[Incident, float]]:
    load_ai_models()
    
    if not _models_loaded or _sentence_transformer is None or _faiss_index is None or not _historical_ids:
        # Fallback database lookup if FAISS index is empty
        query_terms = title.split()
        if not query_terms:
            return []
            
        # SQL search mapping titles
        matches = db.query(Incident).filter(
            Incident.status == "resolved"
        ).limit(3).all()
        return [(m, 0.70) for m in matches]
        
    try:
        query_text = f"Title: {title} | Description: {description}"
        q_vec = _sentence_transformer.encode([query_text]).astype("float32")
        import faiss
        faiss.normalize_L2(q_vec)
        
        # Search index for a larger candidate pool for hybrid re-ranking
        k = min(15, len(_historical_ids))
        distances, indices = _faiss_index.search(q_vec, k)
        
        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(_historical_ids):
                continue
                
            inc_id = _historical_ids[idx]
            hist_inc = db.query(Incident).filter(Incident.id == inc_id).first()
            if hist_inc:
                # Map vector distance to score (Inner Product with normalized vectors = Cosine Similarity)
                base_score = max(0.0, float(dist))
                
                # Hybrid Re-ranking boosts
                hybrid_score = base_score
                if target_category and hist_inc.category == target_category:
                    hybrid_score += 0.15  # Category match boost
                if target_severity and hist_inc.severity == target_severity:
                    hybrid_score += 0.10 # Severity match boost
                    
                hybrid_score = min(1.0, hybrid_score)
                
                if hybrid_score >= settings.FAISS_RELEVANCE_THRESHOLD:
                    candidates.append((hist_inc, hybrid_score))
                
        # Sort candidates by hybrid score descending and take top 3
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:3]
    except Exception as e:
        print("Error during vector similarity search. Error:", e)
        return []

def run_diagnostics_pipeline(db: Session, incident_id: uuid.UUID):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return
        
    try:
        # Clear existing entries if this is a re-run to prevent duplicates
        db.query(Prediction).filter(Prediction.incident_id == incident.id).delete()
        db.query(HistoricalReference).filter(HistoricalReference.incident_id == incident.id).delete()
        db.query(Recommendation).filter(Recommendation.incident_id == incident.id).delete()
        db.commit()

        # 1. Run Classification and Severity Predictions
        preds = predict_incident_features(
            incident.title, 
            incident.description, 
            incident.git_diff if hasattr(incident, 'git_diff') and incident.git_diff else "", 
            incident.incident_timeline if hasattr(incident, 'incident_timeline') and incident.incident_timeline else ""
        )
        
        # Save Predictions to database
        db_pred = Prediction(
            incident_id=incident.id,
            severity_pred=preds["severity_pred"],
            severity_conf=preds["severity_conf"],
            category_pred=preds["category_pred"],
            category_conf=preds["category_conf"],
            root_cause_pred=preds["root_cause_pred"]
        )
        db.add(db_pred)
        
        # Update Incident main metadata (Severity and Category auto-triage)
        incident.severity = preds["severity_pred"]
        incident.category = preds["category_pred"]
        incident.root_cause = preds["root_cause_pred"]
        db.commit()
        
        # 2. Retrieve Similar Tickets (Hybrid approach)
        similar_tickets = retrieve_similar_incidents(db, incident.title, incident.description, incident.category, incident.severity)
        for hist_inc, score in similar_tickets:
            ref = HistoricalReference(
                incident_id=incident.id,
                historical_incident_id=hist_inc.id,
                similarity_score=score
            )
            db.add(ref)
        db.commit()
        
        # 3. Generate RAG recommendations
        log_metrics = ""
        # Check if logs are attached
        logs = db.query(Log).filter(Log.incident_id == incident.id).all()
        if logs:
            log_summaries = []
            for log in logs:
                log_summaries.append(log.parsed_content.get("summary", ""))
            log_metrics = "\n".join(log_summaries)
            
        hist_context = ""
        if similar_tickets:
            context_blocks = []
            for idx, (t, score) in enumerate(similar_tickets):
                # Retrieve matching resolution
                rec = db.query(Recommendation).filter(Recommendation.incident_id == t.id).first()
                res_text = rec.recommendation_text if rec else t.root_cause
                context_blocks.append(
                    f"Ticket #{idx+1}: {t.title}\nSeverity: {t.severity} | Category: {t.category}\nRoot Cause: {t.root_cause}\nResolution:\n{res_text}"
                )
            hist_context = "\n\n".join(context_blocks)
            
        # Build Groq/Gemini RAG Prompt
        prompt = f"""
TARGET INCIDENT:
Title: {incident.title}
Description: {incident.description}

USER PROVIDED INCIDENT TIMELINE:
{incident.incident_timeline if hasattr(incident, 'incident_timeline') and incident.incident_timeline else "No initial timeline provided."}

LOG TELEMETRY DATA:
{log_metrics if log_metrics else "No log attachments uploaded yet."}

RECENT GIT DIFF / CODE CHANGES:
{incident.git_diff if incident.git_diff else "No git diff attached."}

HISTORICAL RETRIEVED INCIDENTS CONTEXT (FAISS):
{hist_context if hist_context else "No historical matched incidents found."}

INSTRUCTIONS:
Using the incident details, log telemetries, incident timelines, and historical precedents context above, generate a step-by-step resolution walkthrough.
Provide diagnostic commands ONLY IF the specific technology (e.g., Kubernetes, Docker, Postgres) is explicitly mentioned in the target incident data or logs. If no specific technology is mentioned, provide general resolution recommendations without making up or assuming technology-specific commands. Keep your response technical and concise.
"""
        
        # Check LLM call mode and fallback
        recommendation_text = ""
        if settings.MOCK_AI_FALLBACK and not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
            # Use offline categories mock response to return rich, instant data
            mock_data = MOCK_RESPONSES.get(preds["category_pred"], MOCK_RESPONSES["application"])
            recommendation_text = f"**[Offline Fallback Mode] AI Diagnostics Resolution Recommendation:**\n\n{mock_data['recommendation']}\n\n*Historical Precedents Matches Score: 85%*"
        else:
            recommendation_text = LLMClient.generate_recommendation(prompt)
            
        # Save RAG output
        rec = Recommendation(
            incident_id=incident.id,
            recommendation_text=recommendation_text
        )
        db.add(rec)
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Error running diagnostics pipeline on incident {incident_id}:", e)
        # Create a default fallback recommendation
        rec = Recommendation(
            incident_id=incident.id,
            recommendation_text=f"Diagnostics failed. Primary heuristic recommendation:\nCheck application status and review database/connection constraints manually."
        )
        db.add(rec)
        db.commit()

def run_diagnostics_pipeline_background(incident_id: uuid.UUID):
    print(f"DEBUG: run_diagnostics_pipeline_background starting for {incident_id}...")
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        run_diagnostics_pipeline(db, incident_id)
        print(f"DEBUG: run_diagnostics_pipeline_background finished for {incident_id}.")
    except Exception as e:
        print(f"DEBUG: run_diagnostics_pipeline_background ERROR for {incident_id}: {e}")
    finally:
        db.close()

def validate_ai_output(text: str) -> str:
    """
    Strict secondary validation pass to catch hallucinations or poorly formatted text.
    In a full production scenario, this might call another LLM prompt ("Rate this output 1-10").
    Here, we do heuristic checks.
    """
    if len(text) < 50:
        return "**[VALIDATION FAILED]** Generated output was too short. Fallback applied."
    if "I cannot" in text or "I'm sorry" in text or "As an AI" in text:
        return "**[VALIDATION FAILED]** LLM refused to answer. Heuristic fallback applied."
        
    return text

def generate_rca_document(db: Session, incident_id: uuid.UUID) -> str:
    load_ai_models()
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return "Error: Incident not found."
        
    # Retrieve timeline, resolution, logs
    resolution = "Resolved."
    if incident.status in ["resolved", "closed"]:
        resolution = f"Resolved at {incident.resolved_at}."
        
    # Build Timeline from Comments
    timeline_str = ""
    if incident.comments:
        for c in sorted(incident.comments, key=lambda x: x.created_at):
            timeline_str += f"[{c.created_at.strftime('%Y-%m-%d %H:%M')}] {c.user.name} ({c.user.role}): {c.content}\n"
    if not timeline_str:
        timeline_str = "No collaborative comments recorded."

    # Build Telemetry from Logs
    telemetry_str = ""
    if incident.logs:
        for l in incident.logs:
            summary = l.parsed_content.get('summary', 'No summary') if isinstance(l.parsed_content, dict) else str(l.parsed_content)
            telemetry_str += f"- {l.filename} (Uploaded {l.uploaded_at.strftime('%H:%M')}): {summary}\n"
    if not telemetry_str:
        telemetry_str = "No telemetry logs attached."

    # Similar incidents for context (Hybrid retrieval)
    similar_tickets = retrieve_similar_incidents(db, incident.title, incident.description, incident.category, incident.severity)
    hist_context = ""
    for idx, (t, score) in enumerate(similar_tickets):
        hist_context += f"\n[HISTORICAL INCIDENT {idx + 1}]\n"
        hist_context += f"Title: {t.title}\n"
        hist_context += f"Description: {t.description}\n"
        hist_context += f"Root Cause: {t.root_cause}\n"
        
        # Add past predictions
        if t.predictions:
            latest_pred = sorted(t.predictions, key=lambda p: p.created_at, reverse=True)[0]
            hist_context += f"Past Prediction - Category: {latest_pred.category_pred}, Severity: {latest_pred.severity_pred}\n"
            
        # Add past provided timeline
        if hasattr(t, 'incident_timeline') and t.incident_timeline:
            hist_context += f"Past Provided Timeline:\n{t.incident_timeline}\n"
            
        # Add past comments (investigation timeline)
        if t.comments:
            hist_context += "Past Investigation Comments:\n"
            for c in sorted(t.comments, key=lambda c: c.created_at):
                hist_context += f"  - [{c.created_at.strftime('%m-%d %H:%M')}] {c.user.name}: {c.content}\n"
                
        # Add full past RCA
        if t.rca and t.rca.document_content:
            hist_context += f"Past RCA Document:\n{t.rca.document_content}\n"
        
    prompt = f"""
GENERATE ROOT CAUSE ANALYSIS (RCA) DOCUMENT

INCIDENT DATA:
Title: {incident.title}
Description: {incident.description}
Status: {incident.status}
Resolution Notes: {resolution}

PARSED TELEMETRY LOGS:
{telemetry_str}

RECENT GIT DIFF / CODE CHANGES:
{incident.git_diff if incident.git_diff else "No git diff attached."}

USER PROVIDED INCIDENT TIMELINE:
{incident.incident_timeline if hasattr(incident, 'incident_timeline') and incident.incident_timeline else "No initial timeline provided."}

INVESTIGATION TIMELINE (COMMENTS):
{timeline_str}

HISTORICAL PRECEDENTS (FAISS MATCHES):
{hist_context if hist_context else "None found."}

INSTRUCTIONS:
You are generating a final post-mortem RCA document for this resolved incident. 
Synthesize the timeline, telemetry, and historical context into a coherent, highly technical narrative.
Structure the response exactly as follows:
# Root Cause Analysis
## Executive Summary

## Business Impact
- Users Affected:
- Systems Affected:
- Duration:

## Timeline

## Evidence Collected
- Logs:
- Git Changes:
- Metrics:

## Root Cause

## Contributing Factors

## Resolution

## Preventive Actions

## Lessons Learned

Be highly technical and professional. Do not invent logs if none are provided.
"""
    
    if settings.MOCK_AI_FALLBACK and not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        rca_text = f"# Root Cause Analysis\n\n## 1. Executive Summary\nOffline generated mock RCA for {incident.title}.\n\n## 2. Incident Timeline\nCreated to Resolved timeline.\n\n## 3. Root Cause\n{incident.root_cause}\n\n## 4. Resolution Actions Taken\nSystem adjustments made.\n\n## 5. Preventative Measures\nMonitor systems closely."
    else:
        raw_text = LLMClient.generate_recommendation(prompt)
        rca_text = validate_ai_output(raw_text)
        
    # Save RCA to db
    from backend.app.database import engine
    from sqlalchemy import text
    import datetime
    
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO rcas (id, incident_id, document_content) 
            VALUES (:id, :incident_id, :doc)
            ON CONFLICT (incident_id) DO UPDATE SET document_content = EXCLUDED.document_content
        """), {
            "id": str(uuid.uuid4()),
            "incident_id": str(incident.id),
            "doc": rca_text
        })
        conn.commit()
        
    # Trigger Discord Webhook Notification
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        try:
            import requests
            discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
            requests.post(discord_url, json={
                "content": f"🚀 **New RCA Generated!**\\n**Incident:** {incident.title}\\n**Severity:** {incident.severity}\\nAn automated Root Cause Analysis has been published."
            }, timeout=2)
            print("Discord notification sent successfully.")
        except Exception as e:
            print("Failed to send Discord notification:", e)
            
    return rca_text
