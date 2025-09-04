import streamlit as st
import pandas as pd
import json
import time
import csv
import io
from groq import Groq
import pyperclip  # For copy to clipboard functionality

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
# Set page configuration
st.set_page_config(
    page_title="Tele Script Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Groq client
def initialize_groq_client():
    api_key = GROQ_API_KEY
    if api_key:
        return Groq(api_key=api_key)
    return None

# Function to generate report using Groq
def generate_report_with_groq(client, row_data, model_name="llama-3.3-70b-versatile"):
    """
    Generate a company analysis report using Groq AI model
    """
    try:
        # Prepare the prompt with the row data
        prompt = f"""
        Please generate a comprehensive company analysis report in the exact following format based on the data provided below:
        [Prospect Name] - [Company Name]
        
        [Company Name] - Company Brief
        Industry: [Industry]
        Headquarters: [Headquarters]
        Employees: [Employee Count]
        Revenue: [Revenue]
        Recent Initiatives:
        [List recent initiatives]

        Technology Stack:
        Loan Origination & Servicing: [List systems]
        CRM: [CRM systems]
        Automation / AI: [AI/RPA tools]
        Compliance & Security: [Security systems]

        Focus Areas: [List focus areas]

        Pain Points:
        [List pain points]

        Here is the data to use:
        {json.dumps(row_data, indent=2)}

        Ensure the report is professional, concise, and uses only the information provided.
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
            temperature=0.3,  # Lower temperature for more factual responses
            max_tokens=4000,
        )
        
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None

# Main application
def main():
    st.title("Speridian Tele Script Generator")
    st.markdown("Upload a CSV file ")
    
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
            help="Ensure your CSV contains the required columns "
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
        col1, col2, col3 = st.columns([1, 2, 1])
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
        
        # Get current row data
        current_row = st.session_state.df.iloc[st.session_state.current_index]
        company_name = current_row.get('Company Name', 'Unknown Company')
        prospect_name = current_row.get('Prospect Name', 'Unknown Prospect')
        
        st.header(f"Analysis for: {company_name}")
        st.subheader(f"Prospect: {prospect_name}")
        
        # Check if report already exists for this index
        if st.session_state.current_index not in st.session_state.reports:
            # Generate new report
            with st.spinner("Generating  analysis... This may take a moment"):
                # Convert row to dictionary for processing
                row_dict = current_row.to_dict()
                
                # Generate report
                report = generate_report_with_groq(st.session_state.groq_client, row_dict)
                
                if report:
                    st.session_state.reports[st.session_state.current_index] = report
                else:
                    st.error("Failed to generate report. Please try again.")
                    st.stop()
        
        # Display the report
        report_text = st.session_state.reports[st.session_state.current_index]
        
        # Create a text area for the report with copy functionality
        st.text_area(
            "Generated Report",
            report_text,
            height=400,
            key=f"report_{st.session_state.current_index}"
        )
        
        # Copy to clipboard button
        if st.button(" Copy Report to Clipboard", key=f"copy_{st.session_state.current_index}"):
            pyperclip.copy(report_text)
            st.success("Report copied to clipboard!")
        
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
            csv = download_df.to_csv(index=False)
            st.download_button(
                label="Download CSV with Reports",
                data=csv,
                file_name="analyses_with_reports.csv",
                mime="text/csv",
                key="download_csv"
            )
    
    elif st.session_state.groq_client is None:
        st.warning("Please enter your Groq API key in the sidebar to continue.")
    
    elif st.session_state.df is None:
        st.info("Please upload a CSV file in the sidebar to get started.")

if __name__ == "__main__":
    main()
