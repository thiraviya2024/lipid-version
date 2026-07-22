# ai/explanation.py
from typing import Dict
from .ollama_client import generate_explanation
from .prompt import create_explanation_prompt
from clinical.recommendation_engine import get_lifestyle_recommendations

def generate_clinical_explanation(classified_data: Dict) -> str:
    """Generate safe explanation using Ollama."""
    try:
        prompt = create_explanation_prompt(classified_data)
        llm_text = generate_explanation(prompt)
        
        recs = get_lifestyle_recommendations(classified_data)
        
        final_text = f"{llm_text}\n\n**General Lifestyle Tips:**\n{recs}"
        return final_text
    except Exception as e:
        return f"Overall Risk Level: {classified_data.get('overall_risk', 'Unknown')}\n\nPlease consult your physician for professional advice."