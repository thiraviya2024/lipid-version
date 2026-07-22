# lipid-ai/app.py
import streamlit as st
from pathlib import Path
import sys
import sys
sys.path.append(".")
from config.settings import UPLOAD_DIR, ALLOWED_EXTENSIONS
from utils.logger import logger
from utils.helpers import validate_file_extension

# Import all modules
from parser.file_parser import parse_uploaded_file
from extractor.parameter_extractor import extract_lipid_parameters
from extractor.validator import is_lipid_report
from clinical.risk_engine import calculate_overall_risk
from ai.explanation import generate_clinical_explanation
from report.charts import create_lipid_charts
from report.report_generator import generate_summary_report

st.set_page_config(page_title="LipidAI", page_icon="🧪", layout="wide")

st.title("🧪 LipidAI")
st.subheader("Specialized Lipid Profile Analysis System")
st.caption("Upload your lab report → Get clear insights (Rule-based + Ollama)")

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
            # Parse
            raw_text, structured = parse_uploaded_file(file_path)

            if not is_lipid_report(raw_text):
                st.warning("This doesn't appear to be a Lipid Profile report. Please upload a valid one.")
                st.stop()

            # Extract parameters
            lipid_values = extract_lipid_parameters(raw_text, structured)

            if not lipid_values:
                st.error("Could not extract any lipid parameters from this report.")
                st.stop()

            # Clinical Analysis
            analyzed_data = calculate_overall_risk(lipid_values)

            # Generate Explanation
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