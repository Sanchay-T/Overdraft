# dont forget to uplad the "axis_cateegory.xlsx" sheet
import re
import os
import io
import pandas as pd
import numpy as np
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
from datetime import datetime
from dateutil.relativedelta import relativedelta
import regex as re
import datefinder
from calendar import monthrange
import calendar
from openpyxl.styles import Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime, timedelta

pd.options.display.float_format = "{:,.2f}".format


class SingleBankStatementConverter:
    def __init__(self, bank_names, pdf_paths, pdf_passwords, start_date, end_date, account_number, file_name):
        self.writer = None
        self.bank_names = bank_names
        self.pdf_paths = pdf_paths
        self.pdf_passwords = pdf_passwords
        self.start_date = start_date
        self.end_date = end_date
        self.account_number = account_number
        self.file_name = None

    @classmethod
    def extract_text_from_pdf(cls, filename):
        # Open the PDF file in read-binary mode
        with open(filename, "rb") as file:
            # Create a PDF file reader object
            pdf_reader = PyPDF2.PdfFileReader(file)

            # Get the text from the first page
            page = pdf_reader.getPage(0)
            text = page.extractText()
            lines = text.split("\n")

            # Extract Account Name
            match = re.search(r"Account Name\s+:\s+(.*)", text)
            if match:
                account_name = match.group(1).strip()
            else:
                account_name = "Account Name not found"

            print(account_name)
            # Extract Account Number
            match = re.search(r"Account Number\s+:\s+(\d+)", text)
            if match:
                account_number = match.group(1)
                cls.masked_account_number = (
                        "*" * (len(account_number) - 4) + account_number[-4:]
                )
            else:
                account_number = None
                cls.masked_account_number = "Account Number not found"
            print("\n\nThis is the account number ", account_number, "\n\n")

            # Account desc
            match1 = re.search(r"Account Description\s*:\s*(.*)", text)

            if match1:
                cls.account_description = match1.group(1)
                print(cls.account_description)
            else:
                print("Account Description not found")

            return account_number

    def unlock_the_pdfs_path(self, pdf_path, pdf_password):
        # Create the "saved_pdf" folder if it doesn't exist
        os.makedirs("saved_pdf", exist_ok=True)
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            if pdf_reader.is_encrypted:
                pdf_reader.decrypt(pdf_password)
                try:
                    _ = pdf_reader.numPages  # Check if decryption was successful
                    pdf_writer = PyPDF2.PdfWriter()
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                    unlocked_pdf_path = f"saved_pdf/unlocked.pdf"
                    with open(unlocked_pdf_path, 'wb') as unlocked_pdf_file:
                        pdf_writer.write(unlocked_pdf_file)
                    print("PDF unlocked and saved successfully.")
                except PyPDF2.utils.PdfReadError:
                    print("Incorrect password. Unable to unlock the PDF.")
            else:
                # Copy the PDF file to the "saved_pdf" folder without modification
                unlocked_pdf_path = f"saved_pdf/unlocked.pdf"
                with open(pdf_path, 'rb') as unlocked_pdf_file:
                    with open(unlocked_pdf_path, 'wb') as output_file:
                        output_file.write(unlocked_pdf_file.read())
                print("PDF saved in the 'saved_pdf' folder.")
        return unlocked_pdf_path

    def insert_separator(self, page, y_position, page_width, page_height):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFillColorRGB(0, 0, 0)  # Set fill color to black
        can.setStrokeColorRGB(0, 0, 0)  # Set stroke color to black
        can.setLineWidth(2)  # Set line width
        line_height = page_height / (len(page.extract_text().split('\n')) + 1)
        line_extension = page_width * 2
        can.line(0, y_position, page_width + line_extension, y_position)
        can.save()
        packet.seek(0)
        sep_pdf = PdfReader(packet)
        sep_page = sep_pdf.pages[0]
        sep_page.mediabox.upper_right = (page_width + line_extension, page_height)
        page.merge_page(sep_page)

    def separate_lines_in_pdf(self, input_pdf_path):
        output_pdf_path = 'saved_pdf/output_horizontal.pdf'
        input_pdf = PdfReader(input_pdf_path)
        output_pdf = PdfWriter()
        for page_num in range(len(input_pdf.pages)):
            page = input_pdf.pages[page_num]
            page_width = page.mediabox.upper_right[0] - page.mediabox.lower_left[0]
            page_height = page.mediabox.upper_right[1] - page.mediabox.lower_left[1]
            content = page.extract_text()
            lines = content.split('\n')
            for line_num, line in enumerate(lines):
                if line.strip():
                    self.insert_separator(page, line_num * (page_height / (len(lines) + 1)), page_width, page_height)
            output_pdf.add_page(page)
        with open(output_pdf_path, 'wb') as output_file:
            output_pdf.write(output_file)
        return output_pdf_path

    def insert_vertical_lines(self, page, x_positions, page_height):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFillColorRGB(0, 0, 0)  # Set fill color to black
        can.setStrokeColorRGB(0, 0, 0)  # Set stroke color to black
        can.setLineWidth(2)  # Set line width
        for x_position in x_positions:
            can.line(x_position, 0, x_position, page_height)
        can.save()
        packet.seek(0)
        sep_pdf = PdfReader(packet)
        sep_page = sep_pdf.pages[0]
        sep_page.mediabox.upper_right = (page.mediabox.upper_right[0], page_height)
        page.merge_page(sep_page)

    def separate_lines_in_vertical_pdf(self, input_pdf_path, x_positions):
        output_pdf_path = 'saved_pdf/output_vertical.pdf'
        input_pdf = PdfReader(input_pdf_path)
        output_pdf = PdfWriter()
        for page_num in range(len(input_pdf.pages)):
            page = input_pdf.pages[page_num]
            page_width = page.mediabox.upper_right[0] - page.mediabox.lower_left[0]
            page_height = page.mediabox.upper_right[1] - page.mediabox.lower_left[1]
            content = page.extract_text()
            lines = content.split('\n')
            self.insert_vertical_lines(page, x_positions, page_height)
            output_pdf.add_page(page)
        with open(output_pdf_path, 'wb') as output_file:
            output_pdf.write(output_file)
        return output_pdf_path

    def check_date(self, df):
        if pd.to_datetime(df['Value Date'].iloc[-1], dayfirst=True) < pd.to_datetime(df['Value Date'].iloc[0],
                                                                                     dayfirst=True):
            new_df = df[::-1].reset_index(drop=True)
        else:
            new_df = df.copy()  # No reversal required
        return new_df


    def check_balance(self, df):
        df.loc[:, 'Debit'] = pd.to_numeric(df['Debit'], errors='coerce')  # Convert 'Debit' column to numeric
        df.loc[:, 'Credit'] = pd.to_numeric(df['Credit'], errors='coerce')  # Convert 'Credit' column to numeric
        df.loc[:, 'Balance'] = pd.to_numeric(df['Balance'], errors='coerce')  # Convert 'Balance' column to numeric

        prev_balance = df['Balance'].iloc[0]
        for index, row in df.iloc[1:].iterrows():
            current_balance = row['Balance']
            if row['Debit'] > 0 and prev_balance > 0:
                calculated_balance = prev_balance + row['Debit']
                if round(calculated_balance, 2) != round(current_balance, 2):
                    raise ValueError(f"Error at row {index}: Calculated balance ({calculated_balance}) "
                                     f"doesn't match current balance ({current_balance}) and Error at row DEBIT{row['Debit']} between {row['Value Date']} ")
            elif row['Credit'] > 0 and prev_balance > 0:
                calculated_balance = prev_balance - row['Credit']
                if round(calculated_balance, 2) != round(current_balance, 2):
                    raise ValueError(f"Error at row {index}: Calculated balance ({calculated_balance}) "
                                     f"doesn't match current balance ({current_balance}) and Error at row CREDIT{row['Credit']} between {row['Value Date']} ")
            prev_balance = current_balance
        return df

    def extract_the_df(self, idf):
        balance_row_index = idf[idf.apply(lambda row: 'balance' in ' '.join(row.astype(str)).lower(), axis=1)].index

        # Check if "Balance" row exists
        if not balance_row_index.empty:
            # Get the index of the "Balance" row
            balance_row_index = balance_row_index[0]
            # Create a new DataFrame from the "Balance" row till the end
            new_df = idf.iloc[balance_row_index:]
        else:
            return idf
        return new_df

    def uncontinuous(self, df):
        df = df[~df.apply(lambda row: row.astype(str).str.contains('Balance', case=False)).any(axis=1)]
        return df

    #################--------******************----------#####################

    ###HDFC BANK
    def hdfc(self, unlocked_pdf_path):
        lined_pdf_path = self.separate_lines_in_pdf(unlocked_pdf_path)
        pdf = pdfplumber.open(lined_pdf_path)

        df_total = pd.DataFrame()
        for i in range(len(pdf.pages)):
            p0 = pdf.pages[i]
            table = p0.extract_table()
            df_total = df_total._append(table, ignore_index=True)
            df_total.replace({r'\n': ' '}, regex=True, inplace=True)
            df_total = df_total.replace('', np.nan, regex=True)
        w = df_total.drop_duplicates()
        new_df = self.extract_the_df(w)
        df = self.uncontinuous(new_df)
        df['new_column'] = np.nan
        counter = 0
        # Iterate over the dataframe rows
        for index, row in df.iterrows():
            if pd.notnull(row[0]):
                counter += 1
            df.at[index, 'new_column'] = counter
        # Iterate over the dataframe rows
        for index, row in df.iterrows():
            if pd.isna(row[0]):
                df.at[index, 'new_column'] = np.NaN
        df['new_column'].fillna(method='ffill', inplace=True)
        df[1].fillna('', inplace=True)
        df[1] = df.groupby('new_column')[1].transform(lambda x: ' '.join(x))
        df = df.drop_duplicates(subset='new_column').reset_index(drop=True)
        df = df.drop([2, 3]).reset_index(drop=True)
        df = df.rename(columns={0: 'Value Date', 1: 'Description', 4: 'Debit', 5: 'Credit', 6: 'Balance'})
        df['Value Date'] = pd.to_datetime(df['Value Date'], format='%d/%m/%y', errors='coerce').dt.strftime(
            '%d-%m-%Y')
        df = self.check_date(df)
        df['Balance'] = df['Balance'].str.replace(r'[^\d.-]+', '', regex=True)
        df['Debit'] = df['Debit'].str.replace(r'[^\d.-]+', '', regex=True)
        df['Credit'] = df['Credit'].str.replace(r'[^\d.-]+', '', regex=True)
        df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce')
        df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce')
        df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce')
        df = df.dropna(subset=["Value Date"])

        # Reorder the columns
        idf = df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance']]

        idf['Bank'] = 'HDFC Bank'
        return idf

    #################--------******************------------#####################

    # Function to extract text from a PDF file
    def extract_text_from_pdf(self, unlocked_file_path):
        with open(unlocked_file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text

    def check_statement_period_monthwise(self, start_date_str, end_date_str):
        date_format = "%d-%m-%Y"
        start_date = datetime.strptime(start_date_str, date_format)
        end_date = datetime.strptime(end_date_str, date_format)
        if start_date.day != 1:
            print(f"The statement should start from the first day of a month. Your statement starts on {start_date_str}.")
        next_day = end_date + timedelta(days=1)
        if next_day.day != 1:
            print(f"The statement should end on the last day of a month. Your statement ends on {end_date_str}.")
        return print("Statement starts from first day of month and ends on last day of month.")


    def convert_to_dt_format(self, date_str):
        formats_to_try = ["%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d/%m/%Y"]
        for format_str in formats_to_try:
            try:
                date_obj = datetime.strptime(date_str, format_str)
                return date_obj.strftime("%d-%m-%Y")
            except ValueError:
                pass
        raise ValueError("Invalid date format: {}".format(date_str))

    def find_names_and_account_numbers_hdfc(self, text):
        # Customize the regex patterns according to your needs
        name_pattern = re.compile(r'(?:MR\.|M/S\.)\s*([^\n]+)', re.IGNORECASE)
        account_number_pattern = re.compile(r'Account No\s*:\s*(\d+)', re.IGNORECASE)

        from_index = text.find("From :") + len("From :")
        start_date = text[from_index + 1: from_index + 11].strip()
        to_index = text.find("To :") + len("To :")
        end_date = text[to_index + 1: to_index + 11].strip()
        complete_date_range = f"{start_date} to {end_date}"
        date_str = complete_date_range
        start_date_str = self.convert_to_dt_format(date_str.split(" to ")[0])
        end_date_str = self.convert_to_dt_format(date_str.split(" to ")[1])
        self.check_statement_period_monthwise(start_date_str, end_date_str)

        names = name_pattern.findall(text)
        account_numbers = account_number_pattern.findall(text)
        if not names:
            names = [None]
        if not account_numbers:
            account_numbers = [None]
        listO = [names[0], account_numbers[0]]
        return listO

    def extraction_process(self, bank, pdf_path, pdf_password, start_date, end_date):
        bank = re.sub(r'\d+', '', bank)
        unlocked_pdf_path = self.unlock_the_pdfs_path(pdf_path, pdf_password)
        print(unlocked_pdf_path)
        text = self.extract_text_from_pdf(unlocked_pdf_path)

       
        if bank == "HDFC":
            df = pd.DataFrame(self.hdfc(unlocked_pdf_path))
            acc_name_n_number = self.find_names_and_account_numbers_hdfc(text)

        else:
            df = pd.NA
            acc_name_n_number = pd.NA
            raise ValueError("Bank Does not Exist")

        df = df.reset_index(drop=True)
        return df, acc_name_n_number

    def process_repeating_columns(self, oy):
        df = pd.concat(oy, axis=1)
        df = df.loc[:, ~df.columns.duplicated(keep='first') | (df.columns != 'Day')]
        repeating_columns = [col for col in df.columns if df.columns.tolist().count(col) > 1]

        idf = pd.DataFrame({col: df[col].sum(axis=1).round(4) for col in repeating_columns})
        df = df.drop(columns=repeating_columns)
        concatenated_df = pd.concat([df, idf], axis=1)

        sorted_columns = sorted([col for col in concatenated_df.columns if col != 'Day'],
                                key=lambda x: pd.to_datetime(x, format="%b-%Y"))
        sorted_columns_formatted = [col.strftime("%b-%Y") if isinstance(col, pd.Timestamp) else col for col in
                                    sorted_columns]
        concatenated_df = concatenated_df[['Day'] + sorted_columns_formatted]
        return concatenated_df

    def months_between(self, start_month, end_month):
        def month_sort_key(month_str):
            return datetime.strptime(month_str, '%b-%Y')

        start_ate = datetime.strptime(start_month, '%b-%Y')
        end_ate = datetime.strptime(end_month, '%b-%Y')
        months_list = []
        current_date = start_ate
        while current_date <= end_ate:
            months_list.append(current_date.strftime('%b-%Y'))
            current_date += relativedelta(months=1)
        return sorted(months_list, key=month_sort_key)

    def monthly(self, df):
        # add a new row with the average of month values in each column
        new_row = pd.DataFrame(df.iloc[0:31].mean(axis=0)).T
        monthly_avg = pd.concat([df, new_row], ignore_index=True)
        monthly_avg.iloc[-1, 0] = 'Average'
        return monthly_avg

    def eod(self, df):
        end_day = df["Date"].iloc[-1]
        df = df[["Value Date", "Balance", "Month", "Date", "Bank"]]
        bank_names = df["Bank"].unique().tolist()
        multiple_eods = []

        for bank in bank_names:
            idf = df[df["Bank"] == bank]
            result_eod = pd.DataFrame()
            for month in idf['Month'].unique():
                eod_month_df = idf.loc[idf['Month'] == month].drop_duplicates(subset='Date', keep='last')

                # Loop through each day in the month
                for day in range(1, 32):
                    # Check if there are any rows with the current day
                    day_present = False
                    for index, row in eod_month_df.iterrows():
                        if row['Date'] == day:
                            day_present = True
                            break

                    # If day is not present, add a row with NaN values for all columns except the date
                    if not day_present:
                        new_row = {'Balance': 0, 'Month': eod_month_df.iloc[0]['Month'], 'Date': day}
                        eod_month_df = pd.concat([eod_month_df, pd.DataFrame(new_row, index=[0])], ignore_index=True)
                        eod_month_df = eod_month_df.sort_values(by='Date')

                result_eod = pd.concat([result_eod, eod_month_df], ignore_index=True)

            # iterate through column and replace zeros with previous value
            previous_eod = 0
            for i, value in enumerate(result_eod['Balance']):
                if value == 0:
                    result_eod.loc[i, 'Balance'] = previous_eod
                else:
                    previous_eod = value

            pivot_df = result_eod.pivot(index='Date', columns='Month', values='Balance').reset_index(drop=True)
            column_order = idf["Month"].unique()  # do not change
            pivot_df = pivot_df.reindex(columns=column_order)
            pivot_df.insert(0, 'Day', range(1, 32))

            columns = pivot_df.columns[1:]
            col_values = ['Feb', 'Apr', 'Jun', 'Sep',
                          'Nov']  # no hard code now :: these are the months in every year not having 31 days

            for i, row in pivot_df.iterrows():
                for month in columns:
                    if any(col in month for col in col_values):
                        if 'Feb' in month and row['Day'] > 28:
                            pivot_df.loc[i, month] = 0.0
                        elif row['Day'] > 30:
                            pivot_df.loc[i, month] = 0.0

            # last_column_list = pivot_df.iloc[:, -1].tolist()
            # new_column = last_column_list.copy()
            # new_column[end_day + 1:] = [0] * (len(new_column) - end_day - 1)
            # pivot_df.iloc[:, -1] = new_column

            multiple_eods.append(pivot_df)

            if len(multiple_eods) < 1:
                adf = multiple_eods[0]
                # add a new row with the sum of values in each column
                new_row = pd.DataFrame(adf.iloc[0:31].sum(axis=0)).T
                total_df = pd.concat([adf, new_row], ignore_index=True)
                total_df.iloc[-1, 0] = 'Total'
                all_df = self.monthly(total_df)
            else:
                adf = self.process_repeating_columns(multiple_eods)
                # add a new row with the sum of values in each column
                new_row = pd.DataFrame(adf.iloc[0:31].sum(axis=0)).T
                total_df = pd.concat([adf, new_row], ignore_index=True)
                total_df.iloc[-1, 0] = 'Total'
                all_df = self.monthly(total_df)

        return all_df

    def category_add(self, df):
        df2 = pd.read_excel('common_category_sheet.xlsx')
        # df2 = pd.read_excel("category_sheet/multiple_category.xlsx")

        category = []
        for desc in df['Description'].str.lower():
            match_found = False
            for value in df2["Particulars"].str.lower():
                if value in desc:
                    summary = df2.loc[df2["Particulars"].str.lower() == value, "Category"].iloc[0]
                    category.append(summary)
                    match_found = True
                    break
            if not match_found:
                category.append("Suspense")
        df['Category'] = category
        # Reorder the columns
        # df = df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']]
        return df

    ##SHEETS
    # for investment
    def total_investment(self, df):
        invest_df = pd.DataFrame()
        for index, row in df.iterrows():
            arow = row["Category"]
            if arow == "Investment":
                invest_df = invest_df._append(row, ignore_index=True)
        return invest_df

    # for return of investment
    def redemption_investment(self, df):
        red_df = pd.DataFrame()
        for index, row in df.iterrows():
            arow = row["Category"]
            if arow == "Redemption of Investment":
                red_df = red_df._append(row, ignore_index=True)
        return red_df

    # for cash withdrawal
    def cash_withdraw(self, df):
        cashw_df = pd.DataFrame()
        for index, row in df.iterrows():
            arow = row["Category"]
            if arow == "Cash Withdrawal":
                cashw_df = cashw_df._append(row, ignore_index=True)
        return cashw_df

    # for cash deposit
    def cash_depo(self, df):
        cashd_df = pd.DataFrame()
        for index, row in df.iterrows():
            arow = row["Category"]
            if arow == "Cash Deposits":
                cashd_df = cashd_df._append(row, ignore_index=True)
        return cashd_df

    # dividend/interest
    def div_int(self, df):
        iii = pd.DataFrame()
        for index, row in df.iterrows():
            arow = row["Category"]
            if arow == "Dividend/interest":
                iii = iii._append(row, ignore_index=True)
        return iii

    # recurring emi
    def emi(self, df):
        em_i = pd.DataFrame()
        for index, row in df.iterrows():
            arow = row["Category"]
            if arow == "EMI":
                em_i = em_i._append(row, ignore_index=True)
        return em_i


    # for creditor list
    def creditor_list(self, df):
        # credit_list = pd.DataFrame()
        # for index, row in df.iterrows():
        #     debit_amount = pd.to_numeric(row['Debit'], errors='coerce')
        #     if debit_amount > 0:
        #         credit_list = credit_list._append(row, ignore_index=True)
        # return credit_list
        debit = df[df['Debit'].notnull()]
        Creditor_list = debit[
            debit["Description"].str.contains("BRN-CLG-CHQ") | debit[
                "Description"].str.contains("NEFT/MB/") | debit["Description"].str.contains("MOB/TPFT") | debit[
                "Description"].str.contains("NLC INDIA LTD") | debit[
                "Description"].str.contains("NEFT/MB/AX") | debit[
                "Description"].str.contains("NLC INDIA LTD") | debit[
                "Description"].str.contains("MOB/TPFT/") | debit[
                "Description"].str.contains("INB/") | debit[
                "Description"].str.contains("BRN-CLG-CHQ") | debit["Description"].str.contains("IMPS") | debit[
                "Description"].str.contains("IMPS/P2A")]
        Creditor_list = Creditor_list[~Creditor_list["Description"].str.contains("BILLDESK")]
        Creditor_list = Creditor_list[~Creditor_list["Description"].str.contains("GST TAX PAYMENT")]
        Creditor_list = Creditor_list[~Creditor_list["Description"].str.contains("ATOM STOCK BROKER")]
        Creditor_list = Creditor_list[~Creditor_list["Category"].str.contains("Suspense")]
        Creditor_list = Creditor_list[~Creditor_list["Category"].str.contains("fastag")]
        # Creditor_list.drop(['Chq No', 'Credit', 'Balance', 'Init. Br'], axis=1, inplace=True)
        Creditor_list = Creditor_list.sort_values(by='Category')
        return Creditor_list

    # for debtor list
    def debtor_list(self, df):
        # debit_list = pd.DataFrame()
        # for index, row in df.iterrows():
        #     credit_amount = pd.to_numeric(row['Credit'], errors='coerce')
        #     if credit_amount > 0:
        #         debit_list = debit_list._append(row, ignore_index=True)
        # return debit_list
        credit = df[df['Credit'].notnull()]
        Debtor_list = credit[
            credit["Description"].str.contains("NEFT") | credit["Description"].str.contains("IMPS") | credit[
                "Description"].str.contains("RTGS") | credit[
                "Description"].str.contains("ECS/") | credit[
                "Description"].str.contains("MOB/TPFT/")]
        Debtor_list = Debtor_list[~Debtor_list["Category"].str.contains("Dividend/interest")]
        Debtor_list = Debtor_list[~Debtor_list["Category"].str.contains('Suspense')]
        Debtor_list = Debtor_list[~Debtor_list["Category"].str.contains('Redemption of Investment')]
        Debtor_list = Debtor_list.sort_values(by='Category')
        return Debtor_list

    #
    # for suspense credit
    def suspense_credit(self, df):
        suspense_cr = df[df["Category"].str.contains("Suspense")].groupby('Credit')
        suspense_cr = suspense_cr.apply(lambda x: x)
        return suspense_cr
        # c_df = pd.DataFrame()
        # for index, row in df.iterrows():
        #     credit_amount = pd.to_numeric(row['Credit'], errors='coerce')
        #     arow = row["Category"]
        #     if arow == "Suspense" and credit_amount > 0:
        #         c_df = c_df._append(row, ignore_index=True)
        # return c_df

    # for suspense debit


    def suspense_debit(self, df):
        suspense_dr = df[df["Category"].str.contains("Suspense")].groupby('Debit')
        suspense_dr = suspense_dr.apply(lambda x: x)
        return suspense_dr
        # d_df = pd.DataFrame()
        # for index, row in df.iterrows():
        #     debit_amount = pd.to_numeric(row['Debit'], errors='coerce')
        #     arow = row["Category"]
        #     if arow == "Suspense" and debit_amount > 0:
        #         d_df = d_df._append(row, ignore_index=True)
        # return d_df

    # ***************/-first page summary sheet-/*********************#

    def summary_sheet(self, idf, open_bal, close_bal):
        opening_bal = open_bal
        closing_bal = close_bal

        # total amount of credit transactions
        def total_amount_cr(df):
            sum = df["Credit"].sum(axis=0)
            return sum

        # total amount of debit transactions
        def total_amount_dr(df):
            sum = df["Debit"].sum(axis=0)
            return sum

        # total amount of cash deposits ###money credited to your account
        def total_amount_cd(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "Cash Deposits" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # total amount of cash withdrawn ### money is debited from your account
        def total_amount_cw(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Cash Withdrawal" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # POS transaction cr ###money credited to your account
        def total_amount_pos_cr(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "POS-cr" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # POS transaction dr ### money is debited from your account
        def total_amount_pos_dr(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "POS-dr" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # investment (money debited in total)
        def total_investment(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Investment" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # interest recieved fropm bank
        def recieved_interest(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "Interest Credit" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # salary recieved
        def recieved_salary(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "Salary Received" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # loans recieved
        def loan_recieved(df):
            count = 0
            for index, row in df.iterrows():
                if row["Category"] == "Loan":
                    count += 1
            return count

        # nach reciepts (no of times NACH transactions took place)
        def nach_reciept(df):
            count = 0
            for index, row in df.iterrows():
                description = row['Description']
                if 'nach' in description.lower():
                    count += 1
            return count

        # income tax refund
        def recieved_tax(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "Income Tax" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # rent recieved
        def recieved_rent(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "Rent Recieved" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # dividend
        def dividend_i(df):
            amount = 0
            for index, row in df.iterrows():
                credit_amount = row['Credit']
                if row["Category"] == "Dividend/interest" and credit_amount > 0:
                    amount += credit_amount
            return amount

        # interest paid
        def paid_interest(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Interest Debit" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # salary paid
        def paid_salary(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Salary paid" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # bank charges
        def paid_bank(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Bank Charges" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # emi
        def paid_emi(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "EMI" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # tds_deducted
        def paid_tds(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "TDS" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # income tax
        def paid_tax(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Income Tax Paid" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # gst
        def GST(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "GST Paid" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # utitlity bills
        def utility_bills_i(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Utility Bills" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # travelling expense
        def travelling_bills(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Travelling bills" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # rent paid
        def paid_rent(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Rent Paid" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # general insurance
        def paid_general_insurance(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "General insurance" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # life insurance
        def paid_life_insurance(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Life insurance" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # food expense
        def food_expense(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Food Expense" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # credit card payment
        def credit_card_payment(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Credit Card" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # online_shopping
        def paid_online_shopping(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Online Shopping" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # property_tax
        def paid_property_tax(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Property Tax" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # gas_payment
        def paid_gas_payment(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Gas Payments" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # gold_loan
        def paid_gold_loan(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Gold Loan" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # suspense
        def suspenses(df):
            amount = 0
            for index, row in df.iterrows():
                debit_amount = row['Debit']
                if row["Category"] == "Suspense" and debit_amount > 0:
                    amount += debit_amount
            return amount

        # -----------------------X----------------------------------#
        idf['Credit'] = pd.to_numeric(idf['Credit'], errors='coerce')
        idf['Debit'] = pd.to_numeric(idf['Debit'], errors='coerce')
        # idf['Month'] = idf['Value Date'].dt.strftime('%b-%Y')
        months = idf["Month"].unique()

        amount_cr = {}
        amount_dr = {}
        amount_cd = {}
        amount_cw = {}
        amount_pos_cr = {}
        amount_pos_dr = {}
        investment = {}

        interest_recieved = {}
        salary_recieved = {}
        nach_reciepts = {}
        loans_recieved = {}
        income_tax_refund = {}
        dividend = {}
        rent_recieved = {}

        interest_paid = {}
        salary_paid = {}
        bank_charges = {}
        emi = {}
        tds_deducted = {}
        gst = {}
        income_tax_paid = {}
        utility_bills = {}
        travelling_expense = {}
        rent_paid = {}
        total_expense = {}

        general_insurance = {}
        life_insurance = {}
        food_expenses = {}
        credit_card_payments = {}
        online_shopping = {}
        property_tax = {}
        gas_payment = {}
        gold_loan = {}
        rent_paid = {}
        total_amount = {}
        suspense = {}

        for month in months:
            new_df = idf[idf['Month'] == month].reset_index(drop=True)
            amount_cr.update({month: total_amount_cr(new_df)})
            amount_dr.update({month: total_amount_dr(new_df)})
            amount_cd.update({month: total_amount_cd(new_df)})
            amount_cw.update({month: total_amount_cw(new_df)})
            amount_pos_cr.update({month: total_amount_pos_cr(new_df)})
            amount_pos_dr.update({month: total_amount_pos_dr(new_df)})
            investment.update({month: total_investment(new_df)})

            interest_recieved.update({month: recieved_interest(new_df)})
            salary_recieved.update({month: recieved_salary(new_df)})
            nach_reciepts.update({month: nach_reciept(new_df)})
            loans_recieved.update({month: loan_recieved(new_df)})
            income_tax_refund.update({month: recieved_tax(new_df)})
            dividend.update({month: dividend_i(new_df)})
            rent_recieved.update({month: recieved_rent(new_df)})

            interest_paid.update({month: paid_interest(new_df)})
            salary_paid.update({month: paid_salary(new_df)})
            bank_charges.update({month: paid_bank(new_df)})
            emi.update({month: paid_emi(new_df)})
            tds_deducted.update({month: paid_tds(new_df)})
            gst.update({month: GST(new_df)})
            income_tax_paid.update({month: paid_tax(new_df)})
            utility_bills.update({month: utility_bills_i(new_df)})
            travelling_expense.update({month: travelling_bills(new_df)})
            rent_paid.update({month: paid_rent(new_df)})

            general_insurance.update({month: paid_general_insurance(new_df)})
            life_insurance.update({month: paid_life_insurance(new_df)})
            food_expenses.update({month: food_expense(new_df)})
            credit_card_payments.update({month: credit_card_payment(new_df)})
            online_shopping.update({month: paid_online_shopping(new_df)})
            property_tax.update({month: paid_property_tax(new_df)})
            gas_payment.update({month: paid_gas_payment(new_df)})
            gold_loan.update({month: paid_gold_loan(new_df)})
            rent_paid.update({month: paid_rent(new_df)})
            suspense.update({month: suspenses(new_df)})

            ###now we make sheets
            sheet_1 = pd.DataFrame(
                [amount_cr, amount_dr, amount_cw, amount_cd, amount_pos_cr, investment, amount_pos_dr, opening_bal,
                 closing_bal])
            sheet_1.insert(0, "Particulars",
                           ["Total Amount of Credit Transactions", "Total Amount of Debit Transactions",
                            "Total Amount of Cash Withdrawals", "Total Amount of Cash Deposits",
                            "POS Txns - Cr", "Investment Details", "POS Txns - Dr", "Opening Balance",
                            "Closing Balance"])
            sheet_1['Total'] = sheet_1.iloc[:, 1:].sum(axis=1)

            sheet_2 = pd.DataFrame(
                [amount_cr, interest_recieved, salary_recieved, nach_reciepts, loans_recieved, income_tax_refund,
                 dividend, rent_recieved])
            sheet_2.insert(0, "Income",
                           ["Total Amount of Credit Transactions", "Bank Interest Recieved", "Salary Recieved",
                            "NACH Reciepts", "Loans Recieved", "Income Tax Refund", "Dividend", "Rent Recieved"])
            sheet_2 = sheet_2._append(sheet_2.sum(), ignore_index=True)
            sheet_2.iloc[-1, 0] = "Total"
            sheet_2['Total'] = sheet_2.iloc[:, 1:].sum(axis=1)

            sheet_3 = pd.DataFrame(
                [amount_dr, interest_paid, salary_paid, bank_charges, emi, tds_deducted, gst, income_tax_paid,
                 utility_bills, travelling_expense, rent_paid])
            sheet_3.insert(0, "Expenditure",
                           ["Total Amount of Debit Transactions", "Bank Interest Paid (Only in OD/CC A/c)",
                            "Salaries Paid", "Bank Charges", "EMI***", "TDS Deducted", "Total GST",
                            "Total Income Tax Paid", "Utility Bills", "Travelling Expense", "Rent Paid"])
            sheet_3 = sheet_3._append(sheet_3.sum(), ignore_index=True)
            sheet_3.iloc[-1, 0] = "Total"
            sheet_3['Total'] = sheet_3.iloc[:, 1:].sum(axis=1)

            sheet_4 = pd.DataFrame(
                [general_insurance, life_insurance, food_expenses, credit_card_payments, online_shopping, property_tax,
                 gas_payment, gold_loan, rent_paid])
            sheet_4.insert(0, "Personal Expenses",
                           ["General Insurance", "Life Insurance", "Food Expenses", "Credit Card Payment",
                            "Online Shopping", "Property Tax", "Gas payments", "Gold Loan (Only Interest)",
                            "Rent Paid"])
            sheet_4 = sheet_4._append(sheet_4.sum(), ignore_index=True)
            sheet_4.iloc[-1, 0] = "Total"
            sheet_4['Total'] = sheet_4.iloc[:, 1:].sum(axis=1)

            sheet_5 = pd.DataFrame(
                [amount_dr, interest_paid, salary_paid, bank_charges, emi, tds_deducted, gst, income_tax_paid,
                 utility_bills, travelling_expense, general_insurance, life_insurance, food_expenses,
                 credit_card_payments, online_shopping, property_tax, gas_payment, gold_loan, rent_paid, suspense])
            sheet_5.insert(0, "Expenditure",
                           ["Total Amount of Debit Transactions", "Bank Interest Paid (Only in OD/CC A/c)",
                            "Salaries Paid", "Bank Charges", "EMI***", "TDS Deducted", "Total GST",
                            "Total Income Tax Paid", "Utility Bills", "Travelling Expense", "General Insurance",
                            "Life Insurance", "Food Expenses", "Credit Card Payment", "Online Shopping", "Property Tax",
                            "Gas payments", "Gold Loan (Only Interest)", "Rent Paid", "Suspense"])
            sheet_5 = sheet_5._append(sheet_5.sum(), ignore_index=True)
            sheet_5.iloc[-1, 0] = "Total"
            sheet_5['Total'] = sheet_5.iloc[:, 1:].sum(axis=1)

            df_list = [sheet_1, sheet_2, sheet_3, sheet_4, sheet_5]

        return df_list

    def process_transaction_sheet_df(self, df):
        start_month = df["Month"].iloc[0]
        end_month = df["Month"].iloc[-1]
        A = pd.date_range(start=start_month, end=end_month, freq='M').strftime('%b-%Y')
        B = df["Month"].tolist()
        results = list(set(A) - set(B))
        new_data = {
            'Value Date': [0] * len(results),
            'Description': ["None"] * len(results),
            'Debit': [0] * len(results),
            'Credit': [0] * len(results),
            'Balance': [0] * len(results),
            'Month': results,
            'Date': [1] * len(results),
            'Category': ["None"] * len(results),
            'Bank': [0] * len(results)
        }
        odf = pd.DataFrame(new_data)
        idf = pd.concat([df, odf], ignore_index=True)
        idf["Month"] = pd.to_datetime(idf["Month"], format="%b-%Y")
        adf = idf.copy()
        idf.sort_values(by="Month", inplace=True)
        idf["Month"] = idf["Month"].dt.strftime("%b-%Y")
        idf.reset_index(drop=True, inplace=True)
        for index, row in idf.iterrows():
            if row['Bank'] == 0 and row['Balance'] == 0:
                idf.at[index, 'Bank'] = idf.at[index - 1, 'Bank']
                idf.at[index, 'Balance'] = idf.at[index - 1, 'Balance']
        B = idf.copy()
        none_rows_positions = B[B['Category'] == 'None'].index.tolist()
        rows_as_dict = {}
        for position in none_rows_positions:
            row_as_dict = B.loc[position].to_dict()
            rows_as_dict[position] = row_as_dict
        for index, row_data in rows_as_dict.items():
            if index in adf.index:
                adf.loc[index + 1:] = adf.loc[index:].shift(1)
            # Insert the new row at the given index
            adf.loc[index] = row_data
        adf.reset_index(drop=True, inplace=True)
        idf = adf.copy()
        idf["Month"] = idf["Month"].dt.strftime("%b-%Y")
        idf.reset_index(drop=True, inplace=True)
        for index, row in idf.iterrows():
            if row['Category'] == "None":
                idf.at[index, 'Bank'] = idf.at[index - 1, 'Bank']
                idf.at[index, 'Balance'] = idf.at[index - 1, 'Balance']
        return idf


    def Single_Bank_statement(self, dfs, name_dfs):
        data = []
        for key, value in name_dfs.items():
            bank_name = key
            acc_name = value[0]
            acc_num = value[1]
            if str(acc_num) == "None":
                masked_acc_num = "None"
            else:
                masked_acc_num = "X" * (len(acc_num) - 4) + acc_num[-4:]
            data.append([masked_acc_num, acc_name, bank_name])

        name_n_num_df = pd.DataFrame(data, columns=['Account Number', 'Account Name', 'Bank'])
        num_pairs = len(pd.Series(dfs).to_dict())

        # print(dfs.values())

        concatenated_df = pd.concat(list(dfs.values()))
        concatenated_df = concatenated_df.fillna('')
        concatenated_df['Value Date'] = pd.to_datetime(concatenated_df['Value Date'], format='%d-%m-%Y',
                                                       errors='coerce')
        concatenated_df['Month'] = concatenated_df['Value Date'].dt.strftime('%b-%Y')
        concatenated_df['Date'] = concatenated_df['Value Date'].dt.day
        # df = concatenated_df.sort_values(by='Value Date',  ascending=True).reset_index(drop=True)
        concatenated_df.drop_duplicates(keep='first', inplace=True)
        df = concatenated_df.reset_index(drop=True)

        old_transaction_sheet_df = self.category_add(df)
        transaction_sheet_df = self.process_transaction_sheet_df(old_transaction_sheet_df)
        old_excel_transaction_sheet_df = old_transaction_sheet_df[
            ['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']]

        excel_transaction_sheet_df = self.check_balance(old_excel_transaction_sheet_df)

        eod_sheet_df = self.eod(transaction_sheet_df)
        # #opening & closing balance
        opening_bal = eod_sheet_df.iloc[0, 1:].to_dict()
        closing_bal = {}
        for column in eod_sheet_df.columns[1:]:
            non_zero_rows = eod_sheet_df.loc[eod_sheet_df[column] != 0]
            if len(non_zero_rows) > 0:
                last_non_zero_row = non_zero_rows.iloc[-1]
                closing_bal[column] = last_non_zero_row[column]
        # for summary sheets
        summary_df_list = self.summary_sheet(transaction_sheet_df.copy(), opening_bal, closing_bal)
        sheet_name = "Summary"  # summary joining
        name_n_num_df.to_excel(self.writer, sheet_name=sheet_name, index=False)
        summary_df_list[0].to_excel(self.writer, sheet_name=sheet_name, startrow=name_n_num_df.shape[0] + 2,
                                    index=False)
        summary_df_list[1].to_excel(self.writer, sheet_name=sheet_name,
                                    startrow=name_n_num_df.shape[0] + summary_df_list[0].shape[0] + 4,
                                    index=False)
        summary_df_list[2].to_excel(self.writer, sheet_name=sheet_name,
                                    startrow=name_n_num_df.shape[0] + summary_df_list[0].shape[0] +
                                             summary_df_list[1].shape[0] + 6, index=False)
        summary_df_list[3].to_excel(self.writer, sheet_name=sheet_name,
                                    startrow=name_n_num_df.shape[0] + summary_df_list[0].shape[0] +
                                             summary_df_list[1].shape[0] +
                                             summary_df_list[2].shape[0] + 8, index=False)
        summary_df_list[4].to_excel(self.writer, sheet_name=sheet_name,
                                    startrow=name_n_num_df.shape[0] + summary_df_list[0].shape[0] +
                                             summary_df_list[1].shape[0] +
                                             summary_df_list[2].shape[0] + summary_df_list[3].shape[0] + 10,
                                    index=False)
        if num_pairs > 1:
            excel_transaction_sheet_df.to_excel(self.writer, sheet_name='Combined Transaction', index=False)
            eod_sheet_df.to_excel(self.writer, sheet_name='Combined EOD Balance', index=False)
        else:
            sheets_oNc_list = []
            for key, value in dfs.items():
                bank_name = key
                df = pd.DataFrame(value)
                df = df.fillna('')
                # Convert 'Value Date' column to datetime format
                df['Value Date'] = pd.to_datetime(df['Value Date'], format='%d-%m-%Y', errors='coerce')
                df['Month'] = df['Value Date'].dt.strftime('%b-%Y')
                df['Date'] = df['Value Date'].dt.day
                df = df.reset_index(drop=True)
                old_transaction_sheet_df = self.category_add(df)
                transaction_sheet_df = self.process_transaction_sheet_df(old_transaction_sheet_df)
                excel_transaction_sheet_df = old_transaction_sheet_df[
                    ['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']]
                excel_transaction_sheet_df.to_excel(self.writer, sheet_name=f'{bank_name} Transaction', index=False)
                eod_sheet_df = self.eod(transaction_sheet_df)
                eod_sheet_df.to_excel(self.writer, sheet_name=f'{bank_name} EOD Balance', index=False)
                # #opening & closing balance
                eod_sheet_df_2 = eod_sheet_df.iloc[:-2]
                opening_bal = eod_sheet_df_2.iloc[0, 1:].to_dict()
                closing_bal = {}
                for column in eod_sheet_df_2.columns[1:]:
                    non_zero_rows = eod_sheet_df_2.loc[eod_sheet_df_2[column] != 0]
                    if len(non_zero_rows) > 0:
                        last_non_zero_row = non_zero_rows.iloc[-1]
                        closing_bal[column] = last_non_zero_row[column]
                sheet_1 = pd.DataFrame([opening_bal, closing_bal])
                sheet_1.insert(0, bank_name, ["Opening Balance", "Closing Balance"])
                sheet_1['Total'] = sheet_1.iloc[:, 1:].sum(axis=1)
                sheets_oNc_list.append(sheet_1)
                # sheet_name = "Opening and Closing Balance"  # summary joining
                # start_row = 0
                # for sheet in sheets_oNc_list:
                #     sheet.to_excel(self.writer, sheet_name=sheet_name, startrow=start_row, index=False)
                #     start_row += sheet.shape[0] + 2

        investment_df = self.total_investment(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        investment_df.to_excel(self.writer, sheet_name='Investment', index=False)
        redemption_investment_df = self.redemption_investment(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        redemption_investment_df.to_excel(self.writer, sheet_name='Redemption of Investment', index=False)
        creditor_df = self.creditor_list(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        creditor_df.to_excel(self.writer, sheet_name='Creditor List', index=False)
        debtor_df = self.debtor_list(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        debtor_df.to_excel(self.writer, sheet_name='Debtor List', index=False)
        cash_withdrawal_df = self.cash_withdraw(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        cash_withdrawal_df.to_excel(self.writer, sheet_name='Cash Withdrawal', index=False)
        cash_deposit_df = self.cash_depo(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        cash_deposit_df.to_excel(self.writer, sheet_name='Cash Deposit', index=False)
        dividend_int_df = self.div_int(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        dividend_int_df.to_excel(self.writer, sheet_name='Dividend-Interest', index=False)
        emi_df = self.emi(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        emi_df.to_excel(self.writer, sheet_name='Recurring EMI', index=False)
        suspense_credit_df = self.suspense_credit(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        suspense_credit_df.to_excel(self.writer, sheet_name='Suspense Credit', index=False)
        suspense_debit_df = self.suspense_debit(
            transaction_sheet_df[['Value Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Bank']])
        suspense_debit_df.to_excel(self.writer, sheet_name='Suspense Debit', index=False)

    def start_extraction(self):
        dfs = {}
        name_dfs = {}
        i = 0
        for bank in self.bank_names:
            bank = str(f"{bank}{i}")
            pdf_path = self.pdf_paths[i]
            pdf_password = self.pdf_passwords[i]
            start_date = self.start_date[i]
            end_date = self.end_date[i]
            dfs[bank], name_dfs[bank] = self.extraction_process(bank, pdf_path, pdf_password, start_date, end_date)
            i += 1
        print('|------------------------------|')
        print(self.account_number)
        print('|------------------------------|')
        # cleaned_account_number = clean_account_number(self.account_number)
        #file_name = os.path.join('Excel_Files', f'SingleBankStatement_{self.account_number}.xlsx')
        file_name = os.path.join('Excel_Files', 'SingleBankStatement.xlsx')
        # file_name = "TestSingle_Extracted_statements_file.xlsx"
        self.writer = pd.ExcelWriter(file_name, engine='xlsxwriter')

        self.Single_Bank_statement(dfs, name_dfs)
        self.writer._save()



# """Bank Names should be:
# "Axis": "IDBI": "SBI": "IDFC": "PNB": "Yes Bank": "Kotak": "Union":
# "ICICI": "BOB": "IndusInd": "Indian": "TJSB": "NKGSB": "HDFC"

# bank_names = ["HDFC"]
# pdf_paths = ["/workspaces/Overdraft/HDFC INR STMT 2642 APR 2022 (1) (1).pdf"]
# passwords = [""]

# # # dates should be in the format dd-mm-yy
# start_date = ["01-04-2022"]
# end_date = ["30-04-2022"]
# converter = SingleBankStatementConverter(bank_names, pdf_paths, passwords, start_date, end_date, '00000037039495417',
#                                          'test.py')
# converter.start_extraction()


# def clean_account_number(account_number):
#         # Remove non-digit characters from the account number
#         cleaned_account_number = re.sub(r'\D', '', account_number)
#         return cleaned_account_number

# if __name__ == "__main__":
#     converter = SingleBankStatementConverter(bank_names=["HDFC"], pdf_paths=["/Users/sanchaythalnerkar/OD/HDFC INR STMT 2642 APR 2022 (1).pdf"], pdf_passwords=[None], start_date="01-04-2022", end_date="30-04-2022", account_number="05922320002642", file_name="output_name.xlsx")
