import streamlit as st
import pandas as pd
import json
import time
import re
from groq import Groq

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# Set page configuration
st.set_page_config(
    page_title="Tele script Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Groq client
def initialize_groq_client():
    api_key = GROQ_API_KEY
    if api_key:
        return Groq(api_key=api_key)
    return None

# Function to format the report with proper point-by-point structure
def format_report_with_bullets(report_text):
    """
    Enhance the AI-generated report to ensure proper point-by-point formatting
    for Pain Points and Recent Initiatives sections
    """
    # Convert numbered lists to bullet points
    report_text = re.sub(r'\d+\.\s', '- ', report_text)
    
    # Ensure Pain Points are properly formatted
    if "Pain Points:" in report_text:
        # Extract pain points section
        pain_points_start = report_text.find("Pain Points:")
        pain_points_end = report_text.find("\n\n", pain_points_start)
        if pain_points_end == -1:
            pain_points_end = len(report_text)
        
        pain_points_section = report_text[pain_points_start:pain_points_end]
        
        # Ensure each pain point is on a new line with bullet points
        pain_points_section = re.sub(r'(- [^\n]+)(?=\n|$)', r'\1', pain_points_section)
        pain_points_section = re.sub(r'(?<!\n)\n(?!-)', ' ', pain_points_section)
        
        # Replace the original section with formatted one
        report_text = report_text[:pain_points_start] + pain_points_section + report_text[pain_points_end:]
    
    # Ensure Recent Initiatives are properly formatted
    if "Recent Initiatives:" in report_text:
        # Extract recent initiatives section
        initiatives_start = report_text.find("Recent Initiatives:")
        initiatives_end = report_text.find("\n\n", initiatives_start)
        if initiatives_end == -1:
            initiatives_end = len(report_text)
        
        initiatives_section = report_text[initiatives_start:initiatives_end]
        
        # Ensure each initiative is on a new line with bullet points
        initiatives_section = re.sub(r'(- [^\n]+)(?=\n|$)', r'\1', initiatives_section)
        initiatives_section = re.sub(r'(?<!\n)\n(?!-)', ' ', initiatives_section)
        
        # Replace the original section with formatted one
        report_text = report_text[:initiatives_start] + initiatives_section + report_text[initiatives_end:]
    
    return report_text

# Function to generate report using Groq with enhanced prompting
def generate_report_with_groq(client, row_data, model_name="mixtral-8x7b-32768"):
    """
    Generate a company analysis report using Groq AI model with specific formatting
    for Pain Points and Recent Initiatives
    """
    try:
        # Prepare the prompt with specific formatting instructions
        prompt = f"""
        Please generate a comprehensive company analysis report in the exact following format based on the data provided below:

        [Prospect Name] - [Company Name]
        
        [Company Name] - Company Brief
        Industry: [Industry]
        Headquarters: [Headquarters]
        Employees: [Employee Count]
        Revenue: [Revenue]
        Recent Initiatives:
        - [Initiative 1 with details]
        - [Initiative 2 with details]
        - [Initiative 3 with details]

        Technology Stack:
        Loan Origination & Servicing: [List systems]
        CRM: [CRM systems]
        Automation / AI: [AI/RPA tools]
        Compliance & Security: [Security systems]

        Focus Areas: [List focus areas]

        Pain Points:
        - [Pain point 1 with details]
        - [Pain point 2 with details]
        - [Pain point 3 with details]

        IMPORTANT FORMATTING INSTRUCTIONS:
        1. For "Recent Initiatives" and "Pain Points", use bullet points (hyphens) with each point on a new line
        2. Each bullet point should be concise but informative
        3. Use only the information provided in the data below
        4. Keep the report professional and focused on banking technology

        Here is the data to use:
        {json.dumps(row_data, indent=2)}
        """
        
        # Create chat completion
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=model_name,
            temperature=0.3,
            max_tokens=4000,
        )
        
        # Format the report to ensure proper bullet points
        report = chat_completion.choices[0].message.content
        formatted_report = format_report_with_bullets(report)
        
        return formatted_report
        
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None

# Function to display report with custom CSS for better formatting
def display_report_with_formatting(report_text):
    """Display the report with enhanced formatting"""
    # Split the report into sections
    sections = report_text.split('\n\n')
    
    for section in sections:
        if section.strip():
            # Check if this is a section with bullet points
            if any(x in section for x in ['Recent Initiatives:', 'Pain Points:', 'Technology Stack:', 'Focus Areas:']):
                st.subheader(section.split(':')[0])
                content = section.split(':', 1)[1].strip()
                
                # Handle bullet points
                if content.startswith('-'):
                    bullets = content.split('\n')
                    for bullet in bullets:
                        if bullet.strip():
                            st.markdown(f"• {bullet.strip()[1:].strip()}")
                else:
                    st.write(content)
            else:
                st.write(section)

# Main application
def main():
    st.title("Speridian TeleScript Generator")
    st.markdown("Upload a CSV file")
    
    # Initialize session state variables
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'reports' not in st.session_state:
        st.session_state.reports = {}
    if 'groq_client' not in st.session_state:
        st.session_state.groq_client = None
    
    # Sidebar for API key and file upload
    with st.sidebar:
        st.header("Configuration")
        st.session_state.groq_client = initialize_groq_client()
        
        st.divider()
        
        uploaded_file = st.file_uploader(
            "Upload CSV file", 
            type=['csv'],
            help="Ensure your CSV contains the required columns for analysis"
        )
        
        if uploaded_file is not None:
            try:
                # Read the CSV file
                st.session_state.df = pd.read_csv(uploaded_file)
                st.success(f"Successfully uploaded {len(st.session_state.df)} records")
                
                # Show dataframe info
                st.subheader("Data Preview")
                st.dataframe(st.session_state.df.head(3))
                
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")
    
    # Main content area
    if st.session_state.df is not None and st.session_state.groq_client is not None:
        # Navigation controls
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        with col1:
            if st.button("◀ Previous") and st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.rerun()
        with col2:
            st.markdown(f"**Record {st.session_state.current_index + 1} of {len(st.session_state.df)}**")
        with col3:
            if st.button("Next ▶") and st.session_state.current_index < len(st.session_state.df) - 1:
                st.session_state.current_index += 1
                st.rerun()
        with col4:
            if st.button("Generate All Reports"):
                with st.spinner("Generating reports for all companies..."):
                    for idx in range(len(st.session_state.df)):
                        if idx not in st.session_state.reports:
                            row_dict = st.session_state.df.iloc[idx].to_dict()
                            report = generate_report_with_groq(st.session_state.groq_client, row_dict)
                            if report:
                                st.session_state.reports[idx] = report
                            time.sleep(1)  # Avoid rate limiting
                    st.success("All reports generated!")
                    st.rerun()
        
        # Get current row data
        current_row = st.session_state.df.iloc[st.session_state.current_index]
        company_name = current_row.get('Company Name', 'Unknown Company')
        prospect_name = current_row.get('Prospect Name', 'Unknown Prospect')
        
        st.header(f"Analysis for: {company_name}")
        st.subheader(f"Prospect: {prospect_name}")
        
        # Check if report already exists for this index
        if st.session_state.current_index not in st.session_state.reports:
            # Generate new report
            with st.spinner("Generating AI analysis... This may take a moment"):
                # Convert row to dictionary for processing
                row_dict = current_row.to_dict()
                
                # Generate report
                report = generate_report_with_groq(st.session_state.groq_client, row_dict)
                
                if report:
                    st.session_state.reports[st.session_state.current_index] = report
                else:
                    st.error("Failed to generate report. Please try again.")
                    st.stop()
        
        # Display the report with enhanced formatting
        report_text = st.session_state.reports[st.session_state.current_index]
        
        # Create expandable sections for better organization
        with st.expander("View Full Report", expanded=True):
            display_report_with_formatting(report_text)
        
        # Show raw text for copying
        with st.expander("Raw Text (For Copying)"):
            st.text_area(
                "Generated Report",
                report_text,
                height=400,
                key=f"report_{st.session_state.current_index}"
            )
        
        # Copy to clipboard button

        
        # Download all reports button
        if st.button(" Download All Reports", key="download_all"):
            # Create a combined report
            all_reports = []
            for idx in range(len(st.session_state.df)):
                if idx in st.session_state.reports:
                    all_reports.append(st.session_state.reports[idx])
                else:
                    all_reports.append("Report not generated yet")
            
            # Create a downloadable file
            download_df = st.session_state.df.copy()
            download_df['Generated_Report'] = all_reports
            
            # Convert to CSV
            csv_data = download_df.to_csv(index=False)
            st.download_button(
                label="Download CSV with Reports",
                data=csv_data,
                file_name="banking_analyses_with_reports.csv",
                mime="text/csv",
                key="download_csv"
            )
    
    elif st.session_state.groq_client is None:
        st.warning("Please enter your Groq API key in the sidebar to continue.")
    
    elif st.session_state.df is None:
        st.info("Please upload a CSV file in the sidebar to get started.")

if __name__ == "__main__":
    main()
