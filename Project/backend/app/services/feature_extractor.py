import re

class FeatureExtractor:
    @staticmethod
    def extract_features(title: str, description: str, git_diff: str = "", timeline: str = "") -> list:
        """
        Extracts structured operational features from incident text.
        Returns a list of float values representing the engineered features.
        """
        text = f"{title} {description} {git_diff} {timeline}".lower()
        
        # 1. users_affected
        users_match = re.search(r'(\d+)\s+users?(?:\s+affected)?', text)
        users_affected = float(users_match.group(1)) if users_match else 0.0
        
        # 2. error_count
        error_match = re.search(r'(\d+)\s+errors?', text)
        error_count = float(error_match.group(1)) if error_match else 0.0
        
        # 3. duration_minutes
        dur_match = re.search(r'(?:duration|lasting)\s*(?:of\s*)?(\d+)\s*(?:mins?|minutes?)', text)
        duration_minutes = float(dur_match.group(1)) if dur_match else 0.0
        
        # 4. customer_facing
        customer_facing = 1.0 if any(k in text for k in ['customer', 'client', 'public']) else 0.0
        
        # 5. full_outage
        full_outage = 1.0 if any(k in text for k in ['outage', 'unavailable', 'down', 'offline']) else 0.0
        
        # 6. data_loss
        data_loss = 1.0 if any(k in text for k in ['data loss', 'lost data', 'corrupt', 'dropped tables']) else 0.0
        
        # 7. security_breach
        security_breach = 1.0 if any(k in text for k in ['breach', 'compromise', 'hack', 'unauthorized', 'injected']) else 0.0
        
        # 8. revenue_impact
        revenue_impact = 1.0 if any(k in text for k in ['revenue', 'sales', 'checkout', 'payment failed']) else 0.0
        
        return [
            users_affected, error_count, duration_minutes, customer_facing,
            full_outage, data_loss, security_breach, revenue_impact
        ]
