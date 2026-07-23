# lipid-ai/app.py
import streamlit as st
from pathlib import Path
import sys
sys.path.append(".")

from config.settings import UPLOAD_DIR, ALLOWED_EXTENSIONS
from utils.logger import logger
from utils.helpers import validate_file_extension

# Import all modules
from parser.file_parser import parse_uploaded_file
from extractor.parameter_extractor import extract_lipid_parameters
from extractor.validator import is_lipid_report
from clinical.rule_engine import get_rule_engine, RuleEngineError
from clinical.risk_engine import calculate_overall_risk
from ai.explanation import generate_clinical_explanation
from report.charts import create_lipid_charts
from report.report_generator import generate_summary_report

st.set_page_config(page_title="LipidAI", page_icon="🧪", layout="wide")

st.title("🧪 LipidAI")
st.subheader("Specialized Lipid Profile Analysis System")
st.caption("Upload your lab report → Get clear insights (Rule-based + Groq AI)")


# ---------------------------------------------------------------------- #
# Load the Excel-driven Rule Engine exactly once per app session/process.
# st.cache_resource guarantees this runs a single time no matter how many
# times Streamlit re-runs the script on user interaction.
# ---------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def _load_rule_engine():
    return get_rule_engine()


try:
    rule_engine = _load_rule_engine()
except RuleEngineError as e:
    logger.error(f"Rule Engine failed to load: {e}")
    st.error(
        "⚠️ Could not load clinical rules from `config/lipid_rules.xlsx`. "
        f"Details: {e}"
    )
    st.stop()


# File Upload
uploaded_file = st.file_uploader(
    "Upload Lipid Profile Report (PDF, DOCX, XLSX, TXT, CSV)",
    type=["pdf", "docx", "xlsx", "xls", "txt", "csv"],
    help="Maximum 10MB"
)

if uploaded_file:
    if not validate_file_extension(uploaded_file.name, ALLOWED_EXTENSIONS):
        st.error("Unsupported file format!")
        st.stop()

    # Save uploaded file
    file_path = UPLOAD_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"Uploaded: **{uploaded_file.name}**")

    with st.spinner("Analyzing report..."):
        try:
            # 1. Parse
            raw_text, structured = parse_uploaded_file(file_path)

            if not is_lipid_report(raw_text):
                st.warning("This doesn't appear to be a Lipid Profile report. Please upload a valid one.")
                st.stop()

            # 2. Extract parameters
            lipid_values = extract_lipid_parameters(raw_text, structured)

            if not lipid_values:
                st.error("Could not extract any lipid parameters from this report.")
                st.stop()

            # 3. Rule Engine (Excel-driven) -- decides Normal/Borderline/High
            #    per parameter using config/lipid_rules.xlsx. No hardcoded
            #    ranges exist anywhere in the Python code.
            rule_results = rule_engine.evaluate(lipid_values)

            # 4. Risk Engine -- aggregates the Rule Engine's already-decided
            #    statuses into one overall risk level. It does not re-decide
            #    any individual status.
            analyzed_data = calculate_overall_risk(rule_results)

            # 5. Groq AI -- explains the already-decided findings in plain
            #    language. It does not determine Normal/High itself.
            explanation = generate_clinical_explanation(analyzed_data)

            # Display Results
            col1, col2 = st.columns([3, 2])

            with col1:
                st.subheader("📊 Your Lipid Profile")
                display_data = {k: v for k, v in analyzed_data.items() if k != "overall_risk"}
                st.dataframe(display_data, use_container_width=True)

                fig = create_lipid_charts(analyzed_data)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("💡 Summary & Insights")
                st.markdown(explanation)

                st.success(f"**Overall Risk Level: {analyzed_data.get('overall_risk')}**")

            # Download Report
            pdf_path = generate_summary_report(analyzed_data, explanation, uploaded_file.name)
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📄 Download Full PDF Report",
                    data=pdf_file,
                    file_name=f"LipidAI_Report_{uploaded_file.name}.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            logger.error(f"Processing error: {e}")
            st.error(f"An error occurred: {str(e)}")

else:
    st.info("👆 Please upload your lipid profile report to begin.")

st.divider()
st.caption("⚠️ This tool is for educational purposes only. Always consult a qualified physician for medical advice.")