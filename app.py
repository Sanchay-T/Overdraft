import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO
import os
from single_bank_multiple_statement import SingleBankStatementConverter

# Main title
st.title("Bank Statement Converter")


# Sidebar layout and elements
st.sidebar.markdown("## 📝 Input Details")
st.sidebar.markdown("### Bank Selection")
selected_bank_name = st.sidebar.selectbox("", ["HDFC"])

col1, col2 = st.sidebar.columns(2)
with col1:
    st.markdown("### Start Date")
    start_date = st.date_input("", format="DD/MM/YYYY", key="start_date")
with col2:
    st.markdown("### End Date")
    end_date = st.date_input("", format="DD/MM/YYYY", key="end_date")

st.sidebar.markdown("### Credentials")
password = st.sidebar.text_input("Password", value="", type="password")

pdf_file = st.sidebar.file_uploader("Upload PDF file")
print(pdf_file)
submit_button = st.sidebar.button("Submit")

def convert_bank_statements(pdf_file):
    banks = [selected_bank_name]
    pdf_paths = [pdf_file.name]
    passwords = [password]
    start_dates = [start_date.strftime("%d-%m-%Y")]
    end_dates = [end_date.strftime("%d-%m-%Y")]
    account_number = '00000037039495417'  # hardcoded value
    file_name = 'test.py'  # hardcoded value
    excel_file_path = os.path.join("Excel_Files", "SingleBankStatement.xlsx")

    converter = SingleBankStatementConverter(banks, pdf_paths, passwords, start_dates, end_dates, account_number, file_name)
    converter.start_extraction()
    return excel_file_path  

if submit_button and pdf_file:
    with st.spinner("Processing... Please wait."):  # Show a loading spinner while processing
        excel_file_path = convert_bank_statements(pdf_file)

    if os.path.exists(excel_file_path):
        with open(excel_file_path, "rb") as f:
            excel_data = f.read()

        # Display the download button before the sheets
        st.download_button(
            label="Download Excel File",
            data=excel_data,
            file_name="SingleBankStatement.xlsx",
        )

        # Load and display the sheets from the Excel file
        wb = openpyxl.load_workbook(filename=excel_file_path)
        sheet_names = wb.sheetnames

        for sheet_name in sheet_names:
            # Enhanced sheet title display
            st.markdown(f"## 📊 {sheet_name}")
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
            st.dataframe(df)
            st.markdown("---") 


else:
    # Display a welcome message when no file is processed
    st.markdown("""
    ##  HDFC Bank (OD ACCOUNTS) Converter!
    To get started:
    1. Select your bank from the sidebar.
    2. Input the date range.
    3. Provide the necessary credentials.
    4. Upload your PDF bank statement.
    5. Click on the 'Submit' button to convert the statement to Excel format.
    """)

    # Optionally, you can add an image or some other visual element to make the main screen more appealing.
    # Example: st.image("path_to_image.jpg")