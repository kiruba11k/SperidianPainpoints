import streamlit as st
import pandas as pd
import json
import time
import csv
import io
from groq import Groq
import base64
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Speridian Tele Script Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Groq client
def initialize_groq_client():
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            st.error("GROQ_API_KEY not found in secrets. Please check your configuration.")
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing Groq client: {str(e)}")
        return None

# Function to generate report using Groq
def generate_report_with_groq(client, row_data, model_name="llama-3.3-70b-versatile"):
    """
    Generate a company analysis report using Groq AI model
    """
    try:
        # Prepare the prompt with specific instructions
        prompt = f"""
        Please generate a comprehensive company analysis report in the exact following format based on the data provided below:

        [Prospect Name] - [Company Name]

        [Company Name] - Company Brief
        Industry: [Industry]
        Headquarters: [Headquarters]
        Employees: [Employee Count]
        Revenue: [Revenue]
        Recent Initiatives:
        • [List recent initiatives as bullet points, only include what's in the data]

        Technology Stack:
        Loan Origination & Servicing: [List systems]
        CRM: [CRM systems]
        Automation / AI: [AI/RPA tools]
        Compliance & Security: [Security systems]

        Focus Areas: [List the company's actual focus areas based on data, not recommendations]

        Pain Points Relevant to [Prospect Name]:
        • [Pain point 1 - be specific and reference the data]
        • [Pain point 2 - be specific and reference the data]
        • [Pain point 3 - be specific and reference the data]
        • [Pain point 4 - be specific and reference the data]
        • [Pain point 5 - be specific and reference the data]

        IMPORTANT: 
        - Use only the information provided in the data
        - Do not make recommendations in the Focus Areas or Pain Points sections
        - For Pain Points, be specific and reference the actual challenges the company faces based on the data
        - Use bullet points for lists
        - Keep the report professional and concise

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
            temperature=0.2,  # Lower temperature for more factual responses
            max_tokens=4000,
        )
        
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None

# Function to create a downloadable link
def create_download_link(data, filename, file_type):
    """Create a download link for the given data"""
    if file_type == "csv":
        data = data.to_csv(index=False)
        b64 = base64.b64encode(data.encode()).decode()
    else:
        b64 = base64.b64encode(data.encode()).decode()
    
    href = f'<a href="data:file/{file_type};base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

# Main application
def main():
    st.title("Speridian Tele Script Generator")
    st.markdown("Upload a CSV file to generate comprehensive company analysis reports")
    
    # Initialize session state variables
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'reports' not in st.session_state:
        st.session_state.reports = {}
    if 'groq_client' not in st.session_state:
        st.session_state.groq_client = initialize_groq_client()
    
    # Sidebar for file upload
    with st.sidebar:
        st.header("Configuration")
        
        if st.session_state.groq_client:
            st.success("Groq API connected successfully")
        else:
            st.error(" Groq API not connected")
        
        st.divider()
        
        uploaded_file = st.file_uploader(
            "Upload CSV file", 
            type=['csv'],
            help="Ensure your CSV contains columns like 'Company Name', 'Prospect Name', etc."
        )
        
        if uploaded_file is not None:
            try:
                # Read the CSV file
                st.session_state.df = pd.read_csv(uploaded_file)
                st.session_state.reports = {}  # Reset reports when new file is uploaded
                st.session_state.current_index = 0  # Reset to first record
                
                st.success(f" Successfully uploaded {len(st.session_state.df)} records")
                
                # Show dataframe info
                st.subheader("Data Preview")
                st.dataframe(st.session_state.df.head(3))
                
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")
    
    # Main content area
    if st.session_state.df is not None and st.session_state.groq_client is not None:
        # Progress bar
        progress_value = (st.session_state.current_index + 1) / len(st.session_state.df)
        st.progress(progress_value, text=f"Progress: {st.session_state.current_index + 1} of {len(st.session_state.df)} records")
        
        # Navigation controls
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.current_index <= 0):
                st.session_state.current_index -= 1
                st.rerun()
        with col2:
            st.markdown(f"**Record {st.session_state.current_index + 1} of {len(st.session_state.df)}**")
        with col3:
            if st.button("Next ▶", disabled=st.session_state.current_index >= len(st.session_state.df) - 1):
                st.session_state.current_index += 1
                st.rerun()
        with col4:
            if st.button("Generate All", key="generate_all"):
                with st.spinner(f"Generating {len(st.session_state.df)} reports. This may take a while..."):
                    for idx in range(len(st.session_state.df)):
                        if idx not in st.session_state.reports:
                            row_dict = st.session_state.df.iloc[idx].to_dict()
                            report = generate_report_with_groq(st.session_state.groq_client, row_dict)
                            if report:
                                st.session_state.reports[idx] = report
                            time.sleep(1)  # Rate limiting
                st.rerun()
        
        # Get current row data
        current_row = st.session_state.df.iloc[st.session_state.current_index]
        company_name = current_row.get('Company Name', 'Unknown Company')
        prospect_name = current_row.get('Prospect Name', 'Unknown Prospect')
        
        st.header(f"Analysis for: {company_name}")
        st.subheader(f"Prospect: {prospect_name}")
        
        # Display raw data
        with st.expander("View Raw Data"):
            st.json(current_row.to_dict())
        
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
        
        # Display the report
        report_text = st.session_state.reports[st.session_state.current_index]
        
        # Create a text area for the report with copy functionality
        st.text_area(
            "Generated Report",
            report_text,
            height=500,
            key=f"report_{st.session_state.current_index}"
        )
        
        # Copy button
        if st.button("Copy Report to Clipboard", key=f"copy_{st.session_state.current_index}"):
            st.code(report_text, language="text")
            st.success("Report copied to clipboard!")
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            # Download current report
            st.download_button(
                label="Download Current Report",
                data=report_text,
                file_name=f"{company_name.replace(' ', '_')}_report.txt",
                mime="text/plain"
            )
        with col2:
            # Download all reports
            if len(st.session_state.reports) == len(st.session_state.df):
                # Create a combined report
                all_reports = []
                for idx in range(len(st.session_state.df)):
                    if idx in st.session_state.reports:
                        all_reports.append(st.session_state.reports[idx])
                
                # Create a downloadable file
                download_df = st.session_state.df.copy()
                download_df['Generated_Report'] = all_reports
                
                # Convert to CSV
                csv_data = download_df.to_csv(index=False)
                st.download_button(
                    label="Download All Reports as CSV",
                    data=csv_data,
                    file_name="company_analyses_with_reports.csv",
                    mime="text/csv",
                    key="download_csv"
                )
            else:
                st.button("Download All Reports as CSV", disabled=True, 
                         help="Generate all reports first to enable this feature")
    
    elif st.session_state.groq_client is None:
        st.warning("Please configure your Groq API key to continue.")
    
    elif st.session_state.df is None:
        st.info("Please upload a CSV file in the sidebar to get started.")

if __name__ == "__main__":
    main()
