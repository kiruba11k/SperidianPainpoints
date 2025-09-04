import streamlit as st
import pandas as pd
import json
import time
import re
from groq import Groq
import base64

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

# Function to clean and extract data from the row
def extract_row_data(row):
    """Extract and clean data from the row for better processing"""
    data = {}
    
    # Basic company info
    data['prospect_name'] = row.get('Prospect Name', '')
    data['prospect_designation'] = row.get('Prospect Designation', '')
    data['company_name'] = row.get('Company Name', '')
    data['industry'] = row.get('Industry', '')
    data['headquarters'] = row.get('Headquarters Country', '')
    data['employees'] = row.get('Company Size (Employees)', '')
    data['revenue'] = row.get('Revenue (Approx.)', '')
    data['sub_industry'] = row.get('Sub-Industry', '')
    
    # Technology stack
    data['crm'] = row.get('Uses CRM (Salesforce/Dynamics)', '')
    data['core_banking'] = row.get('Uses Core Banking System', '')
    data['los'] = row.get('Uses Loan Origination System (LOS)', '')
    data['ai_tools'] = row.get('Uses AI tools', '')
    data['rpa_tools'] = row.get('Uses RPA Tools', '')
    data['automation_loan_servicing'] = row.get('AI or Automation in Loan Servicing?', '')
    data['compliance_systems'] = row.get('Compliance Systems in Use for lending and morgage industry', '')
    
    # Initiatives and activities
    data['digital_initiative'] = row.get('Digital Transformation Initiative', '')
    data['branch_expansion'] = row.get('Branch Expansion', '')
    data['ma_activity'] = row.get('M&A Activity', '')
    
    # Pain points and relevance
    data['pain_points'] = row.get('Pain Point', '')
    data['relevance'] = row.get('Relevance for Speridian?', '')
    data['relevance_reason'] = row.get('Reason', '')  # This might need adjustment based on your CSV structure
    
    # Clean up the data
    for key in data:
        if pd.isna(data[key]):
            data[key] = ''
        elif isinstance(data[key], str):
            # Remove any markdown formatting or unwanted prefixes
            data[key] = re.sub(r'^.*?:', '', data[key]).strip()
    
    return data

# Function to generate report using Groq
def generate_report_with_groq(client, row_data, model_name="llama-3.3-70b-versatile"):
    """
    Generate a company analysis report using Groq AI model
    """
    try:
        # Prepare the prompt with specific instructions
        prompt = f"""
        Please generate a comprehensive company analysis report in the exact following format based on the data provided below:

        {row_data['prospect_name']} - {row_data['company_name']}

        {row_data['company_name']} - Company Brief
        Industry: {row_data['industry']} / {row_data['sub_industry']}
        Headquarters: {row_data['headquarters']}
        Employees: {row_data['employees']}
        Revenue: {row_data['revenue']}
        Recent Initiatives:
        • {row_data['ma_activity'] if row_data['ma_activity'] else 'No recent initiatives found'}

        Technology Stack:
        Loan Origination & Servicing: {row_data['los']}
        CRM: {row_data['crm']}
        Automation / AI: {"No dedicated AI or RPA tools detected" if row_data['ai_tools'] == 'No AI tools identified' and row_data['rpa_tools'] == 'No RPA tools' else f"{row_data['ai_tools']}, {row_data['rpa_tools']}"}
        Compliance & Security: {row_data['compliance_systems']}

        Focus Areas: Digital lending operations, loan processing efficiency, compliance, customer experience{", post-merger integration" if row_data['ma_activity'] else ""}

        Pain Points Relevant to {row_data['prospect_name']}:
        • {row_data['pain_points'].replace('→', '-').replace('. ', '.\n• ')}

        IMPORTANT: 
        - Use only the information provided above
        - Do not make recommendations in any section
        - For Pain Points, use exactly the information from the provided data
        - Keep the report professional and concise
        - Format with bullet points for lists
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
            temperature=0.1,  # Very low temperature for factual responses
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
            st.success("✅ Groq API connected successfully")
        else:
            st.error("❌ Groq API not connected")
        
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
                
                st.success(f"✅ Successfully uploaded {len(st.session_state.df)} records")
                
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
                            row_data = extract_row_data(st.session_state.df.iloc[idx])
                            report = generate_report_with_groq(st.session_state.groq_client, row_data)
                            if report:
                                st.session_state.reports[idx] = report
                            time.sleep(1)  # Rate limiting
                st.rerun()
        
        # Get current row data
        current_row = st.session_state.df.iloc[st.session_state.current_index]
        row_data = extract_row_data(current_row)
        company_name = row_data.get('company_name', 'Unknown Company')
        prospect_name = row_data.get('prospect_name', 'Unknown Prospect')
        
        st.header(f"Analysis for: {company_name}")
        st.subheader(f"Prospect: {prospect_name}")
        
        # Display raw data
        with st.expander("View Raw Data"):
            st.json(current_row.to_dict())
        
        # Check if report already exists for this index
        if st.session_state.current_index not in st.session_state.reports:
            # Generate new report
            with st.spinner("Generating AI analysis... This may take a moment"):
                # Generate report
                report = generate_report_with_groq(st.session_state.groq_client, row_data)
                
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
