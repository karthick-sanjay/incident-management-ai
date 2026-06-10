import os
import sys
import numpy as np
import joblib
from sqlalchemy.orm import Session

# Prevent HF Tokenizer deadlocks during parallel encoding
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models.incident import Incident

import json

def train_and_index():
    print("Preparing training models outputs...")
    
    # 1. Hybrid Machine Learning models training (Structured + Embeddings)
    from xgboost import XGBClassifier
    from backend.app.services.feature_extractor import FeatureExtractor
    from sentence_transformers import SentenceTransformer
    import numpy as np
    
    # Load datasets
    cat_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "category_training_dataset_27000.json")
    sev_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "severity_training_dataset_27000.json")
    
    with open(cat_data_path, "r") as f:
        cat_data = json.load(f)
    with open(sev_data_path, "r") as f:
        sev_data = json.load(f)
        
    print(f"Loaded {len(cat_data)} category items and {len(sev_data)} severity items.")
    
    # Prepare Category Arrays
    texts = [f"Title: {item['title']} | Description: {item['description']}" for item in cat_data]
    categories = [item['category'] for item in cat_data]
    
    print("Extracting semantic embeddings (BAAI/bge-base-en-v1.5)...")
    st_model = SentenceTransformer("BAAI/bge-base-en-v1.5")
    embeddings = st_model.encode(texts, convert_to_numpy=True).astype("float32")
    X_cat = embeddings

    # Prepare Severity Arrays
    severities = [item['severity'] for item in sev_data]
    structured_features = []
    for item in sev_data:
        feats = [
            float(item.get('users_affected', 0)),
            float(item.get('error_count', 0)),
            float(item.get('duration_minutes', 0)),
            float(item.get('customer_facing', False)),
            float(item.get('full_outage', False)),
            float(item.get('data_loss', False)),
            float(item.get('security_breach', False)),
            float(item.get('revenue_impact', False))
        ]
        structured_features.append(feats)
    
    X_sev = np.array(structured_features, dtype="float32")
    
    print(f"Category feature matrix shape: {X_cat.shape}")
    print(f"Severity feature matrix shape: {X_sev.shape}")
    
    # Encode targets
    from sklearn.preprocessing import LabelEncoder
    cat_encoder = LabelEncoder()
    y_cat = cat_encoder.fit_transform(categories)
    
    sev_encoder = LabelEncoder()
    y_sev = sev_encoder.fit_transform(severities)
    
    # Train Category Classifier (XGBoost)
    cat_model = XGBClassifier(n_estimators=200, max_depth=10, learning_rate=0.1, random_state=42, use_label_encoder=False, eval_metric='mlogloss')
    cat_model.fit(X_cat, y_cat)
    
    # Train Severity Classifier (XGBoost)
    sev_model = XGBClassifier(n_estimators=200, max_depth=10, learning_rate=0.1, random_state=42, use_label_encoder=False, eval_metric='mlogloss')
    sev_model.fit(X_sev, y_sev)
    
    # Write ML binaries
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # joblib.dump(vectorizer, os.path.join(models_dir, "tfidf_vectorizer.joblib")) # NO LONGER NEEDED
    joblib.dump(cat_encoder, os.path.join(models_dir, "cat_encoder.joblib"))
    joblib.dump(sev_encoder, os.path.join(models_dir, "sev_encoder.joblib"))
    joblib.dump(cat_model, os.path.join(models_dir, "category_clf.joblib"))
    joblib.dump(sev_model, os.path.join(models_dir, "severity_clf.joblib"))
    print("Saved Isolated Classification model binaries to 'models/'.")
    
    # 2. Embedding Indexing via SentenceTransformers and FAISS
    print("Building FAISS semantic index from database incidents...")
    db = SessionLocal()
    try:
        resolved_incidents = db.query(Incident).filter(Incident.status == "resolved").all()
        if not resolved_incidents:
            print("Warning: No resolved tickets found in Database. Run backend/init_db.py first!")
            return
            
        print(f"Loading embeddings for {len(resolved_incidents)} tickets...")
        from sentence_transformers import SentenceTransformer
        import faiss
        import numpy as np
        
        # Initialize Sentence Transformer
        model = SentenceTransformer("BAAI/bge-base-en-v1.5")
        
        # Build document text representations
        corpus_texts = []
        incident_ids = []
        for inc in resolved_incidents:
            corpus_texts.append(f"Title: {inc.title} | Description: {inc.description}")
            incident_ids.append(inc.id)
            
        embeddings = model.encode(corpus_texts, convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(embeddings)
        
        # Build FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        
        # Save FAISS structures
        faiss.write_index(index, os.path.join(models_dir, "faiss_index.bin"))
        joblib.dump(incident_ids, os.path.join(models_dir, "historical_ids.joblib"))
        print(f"FAISS index written successfully to 'models/faiss_index.bin' ({index.ntotal} vectors indexed).")
        
    except Exception as e:
        print("FAISS indexing encountered an error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    train_and_index()
