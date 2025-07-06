import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import re

st.set_page_config(layout="wide")

# Application Title
st.title("📊 Financial Data Visualization Tool")

st.write("""
Welcome, Murat! This application helps you visualize your financial data.
Upload your CSV or Excel files, or paste raw text data, and the application will try to automatically detect
and process the financial metrics and years for charting.
""")

# --- Helper Function for Data Cleaning ---
def clean_and_convert_numeric(series):
    if series.dtype == 'object':
        series = series.astype(str)
        # Remove common currency symbols, percentage signs, thousands separators, and extra spaces
        series = series.str.replace(r'[\$,€£%]', '', regex=True) 
        # Handle comma as decimal separator if dot is thousands, or vice-versa
        # This is a bit tricky, best is to standardize before conversion
        # Let's remove all dots (thousands) and replace comma with dot (decimal)
        series = series.str.replace(r'\.', '', regex=True) # Remove thousands dots
        series = series.str.replace(r',', '.', regex=True) # Replace comma decimal with dot decimal
        series = series.str.strip() # Remove leading/trailing spaces
    return pd.to_numeric(series, errors='coerce')

# --- NEW: Function to intelligently find header and data start ---
def find_data_start_and_header(df_raw):
    num_rows, num_cols = df_raw.shape
    
    # Search first 100 rows for a potential header row
    potential_header_row_index = -1
    for r_idx in range(min(num_rows, 100)): 
        row_values = df_raw.iloc[r_idx].dropna().tolist()
        if not row_values: # Skip entirely empty rows
            continue

        row_str_values = [str(val).lower().strip() for val in row_values]
        
        # Check for keywords related to financial items
        financial_keywords = ['financial items', 'finansal kalemler', 'metrik', 'açıklama', 'description', 'gider', 'gelir', 'kalem', 'item', 'metrics']
        has_financial_keywords = any(any(keyword in s for keyword in financial_keywords) for s in row_str_values)
        
        # Check for year-like numbers (e.g., 2020-2099)
        has_numeric_year = any(re.match(r'^\d{4}$', s) and 1900 <= int(s) <= 2099 for s in row_str_values if s.isdigit())
        
        # A strong header candidate has both a descriptive text and year-like numbers
        if has_financial_keywords and has_numeric_year:
            potential_header_row_index = r_idx
            break 
        # Less strong but still a candidate: mostly text in first column, and year-like numbers in other columns
        elif has_numeric_year and any(len(s) > 2 and not s.isdigit() for s in row_str_values[0:min(len(row_str_values), 3)]): # Check first few columns for text
             if potential_header_row_index == -1: # Only assign if no stronger candidate found yet
                 potential_header_row_index = r_idx

    if potential_header_row_index != -1:
        header_row_values = df_raw.iloc[potential_header_row_index].values
        
        actual_columns = []
        seen = {}
        for idx, val in enumerate(header_row_values):
            col_name = str(val).strip() if pd.notna(val) else f'Unnamed_{idx}'
            if col_name in seen:
                seen[col_name] += 1
                col_name = f"{col_name}_{seen[col_name]}"
            else:
                seen[col_name] = 0
            actual_columns.append(col_name)
        
        data_start_row_index = potential_header_row_index + 1
        df_data = df_raw.iloc[data_start_row_index:].copy()
        df_data.columns = actual_columns
        df_data.reset_index(drop=True, inplace=True) 
        
        return df_data, potential_header_row_index
    
    return None, None # No suitable header found

# --- NEW: Function to extract data from raw text ---
def process_text_data(raw_text):
    lines = raw_text.strip().split('\n')
    data = []
    headers = []
    
    # Try to identify header line and data lines
    for i, line in enumerate(lines):
        # Split by common delimiters: tab, multiple spaces, comma, semicolon
        parts = re.split(r'\s{2,}|\t|,|;', line.strip()) 
        parts = [p.strip() for p in parts if p.strip()] # Remove empty parts
        
        if not parts:
            continue
        
        # Try to guess if it's a header line or data line
        # A header line might contain text and year-like numbers
        # A data line usually starts with text (metric name) and then numbers
        
        numeric_parts = [clean_and_convert_numeric(pd.Series([p])).iloc[0] for p in parts]
        is_numeric = [pd.notna(n) for n in numeric_parts]
        
        # Heuristic for header: Contains text and some year-like numbers
        has_year_like = any(re.match(r'^\d{4}$', p) and 1900 <= int(p) <= 2099 for p, num in zip(parts, numeric_parts) if pd.notna(num))
        has_text_metric = any(not num_val and len(p) > 2 for p, num_val in zip(parts, is_numeric))
        
        if not headers and has_year_like and has_text_metric: # Found a potential header line
            headers = [p for p in parts] # Use original parts as headers
            continue
        
        # If headers are found, or if we are past the first few lines and it looks like data
        if headers and len(parts) == len(headers):
            row_data = [p for p in parts]
            data.append(row_data)
        elif not headers and i > 0: # If no header found, but subsequent lines look like data
            # This is a simple case, assuming first column is metric, rest are values
            data.append([p for p in parts])

    if not data:
        return None

    df = pd.DataFrame(data)
    
    # If headers were found, assign them
    if headers and len(headers) == df.shape[1]:
        df.columns = headers
    else: # Try to infer headers if not explicitly found, or use default
        # Simple heuristic: first column is metric, remaining are values (years or similar)
        new_cols = ['Metric'] + [f'Value_{i}' for i in range(df.shape[1] - 1)]
        if len(new_cols) == df.shape[1]:
            df.columns = new_cols
        else: # Fallback for mismatched columns/headers
             df.columns = [f'Col_{i}' for i in range(df.shape[1])]
    
    # Now, try to transpose and clean like Excel data
    # Identify metric column (first non-numeric)
    metric_col = None
    for col in df.columns:
        if pd.to_numeric(df[col], errors='coerce').isna().sum() > (len(df) * 0.5): # More than 50% non-numeric
            metric_col = col
            break
    
    if metric_col:
        df.rename(columns={metric_col: 'Metric'}, inplace=True)
        if not df['Metric'].is_unique:
             df['Metric'] = df['Metric'].astype(str) + '_' + df.groupby('Metric').cumcount().astype(str)
        df.set_index('Metric', inplace=True)
        df = df.T.copy()
        df.reset_index(inplace=True)
        df.rename(columns={df.columns[0]: 'Year'}, inplace=True)
        
        # Clean and convert numeric columns
        for col in df.columns:
            df[col] = clean_and_convert_numeric(df[col])
        
        # Ensure Year column is numeric
        if 'Year' in df.columns:
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
            df.dropna(subset=['Year'], inplace=True)

        return df
    else:
        st.warning("Could not identify a suitable 'Metric' column from the pasted text data. Please ensure your text data has a clear structure.")
        return None


# --- File Upload Section ---
st.header("Upload Your Data Files 📁 or Paste Text Data 📋")

uploaded_files = st.file_uploader(
    "Please drag and drop your CSV or Excel files here, or browse to select them.",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

raw_text_input = st.text_area(
    "Alternatively, paste your financial data here (e.g., table copied from a report):",
    height=200,
    help="Paste data with columns separated by tabs, spaces, commas, or semicolons. The first column is usually recognized as financial item, and subsequent columns as years/values."
)

all_loaded_sheets_data = {} # Stores {file_name_sheet_name: DataFrame}

if uploaded_files or raw_text_input:
    # Process uploaded files first
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.write(f"Processing file: **{uploaded_file.name}**")
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                    st.write(f"  Debug: CSV file loaded. Columns: {df.columns.tolist()}")
                    
                    # Heuristic for CSVs: try to identify the 'Metric' column and 'Year' column
                    potential_metric_col = None
                    potential_year_col = None
                    
                    for col in df.columns:
                        # Check if column is mostly numeric and contains year-like values
                        is_numeric_col = pd.to_numeric(df[col], errors='coerce').notna().sum() / len(df[col].dropna()) > 0.8 if len(df[col].dropna()) > 0 else 0
                        has_year_pattern = df[col].astype(str).str.match(r'^\d{4}$').any() and pd.to_numeric(df[col], errors='coerce').max() <= 2099 and pd.to_numeric(df[col], errors='coerce').min() >= 1900
                        
                        if is_numeric_col and has_year_pattern:
                            potential_year_col = col
                        elif pd.to_numeric(df[col], errors='coerce').isna().sum() > (len(df[col].dropna()) * 0.5) and df[col].nunique() > 1: # More than 50% non-numeric, and more than 1 unique value
                            if potential_metric_col is None: # Take the first suitable non-numeric column
                                potential_metric_col = col
                    
                    if potential_metric_col and potential_year_col:
                        st.write(f"  Debug: CSV - Detected Metric Col: '{potential_metric_col}', Year Col: '{potential_year_col}'")
                        df.rename(columns={potential_metric_col: 'Metric'}, inplace=True)
                        if not df['Metric'].is_unique:
                             df['Metric'] = df['Metric'].astype(str) + '_' + df.groupby('Metric').cumcount().astype(str)
                        df.set_index('Metric', inplace=True)
                        df_processed = df.T.copy() # Transpose to get metrics as columns
                        df_processed.reset_index(inplace=True)
                        df_processed.rename(columns={df_processed.columns[0]: 'Year'}, inplace=True) # First col after transpose becomes Year
                        
                        for col in df_processed.columns:
                            df_processed[col] = clean_and_convert_numeric(df_processed[col])
                        
                        df_processed['Year'] = pd.to_numeric(df_processed['Year'], errors='coerce')
                        df_processed.dropna(subset=['Year'], inplace=True)

                        if not df_processed.empty and not df_processed.select_dtypes(include=['number']).drop(columns=['Year'], errors='ignore').empty:
                            all_loaded_sheets_data[f"{uploaded_file.name}_sheet_1"] = df_processed
                        else:
                            st.warning(f"CSV file '{uploaded_file.name}' processed but contains no valid numeric data for plotting. Skipping.")
                    else:
                        st.warning(f"Could not automatically detect Metric and Year columns in CSV file '{uploaded_file.name}'. Please ensure your CSV has a clear structure for financial data.")


                elif uploaded_file.name.endswith('.xlsx'):
                    xls = pd.ExcelFile(uploaded_file)
                    sheet_names = xls.sheet_names
                    
                    st.subheader(f"Sheets in {uploaded_file.name}:")
                    for sheet_name in sheet_names:
                        st.write(f"- Reading sheet: **{sheet_name}**")
                        try:
                            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
                            st.write(f"  Debug: Raw DataFrame shape for '{sheet_name}': {df_raw.shape}")
                            
                            df_sheet, header_row_index = find_data_start_and_header(df_raw)
                            
                            if df_sheet is None or df_sheet.empty:
                                st.warning(f"Could not automatically detect header and data start for sheet '{sheet_name}' or resulting DataFrame is empty. Skipping this sheet.")
                                continue
                            
                            st.write(f"  Debug: Header row found at index: {header_row_index}. Initial DataFrame columns: {df_sheet.columns.tolist()}")

                            # --- Identify and rename the 'Metric' column (the column containing financial item names) ---
                            metric_col_name = None
                            potential_metric_cols = []
                            for col_idx, col in enumerate(df_sheet.columns):
                                # Heuristic: A metric column should contain mostly text (non-numeric)
                                # and have some unique values, not be entirely empty.
                                non_numeric_ratio = pd.to_numeric(df_sheet[col], errors='coerce').isna().sum() / len(df_sheet[col].dropna()) if len(df_sheet[col].dropna()) > 0 else 0
                                
                                col_lower = str(col).lower()
                                financial_keywords = ['financial items', 'finansal kalemler', 'metrik', 'açıklama', 'description', 'gider', 'gelir', 'kalem', 'item', 'metrics']
                                has_keyword_in_header = any(keyword in col_lower for keyword in financial_keywords)

                                # Check first few rows of the column for text (not just numbers or empty)
                                is_text_content = False
                                for cell_val in df_sheet[col].head(5).dropna():
                                    if isinstance(cell_val, str) and not clean_and_convert_numeric(pd.Series([cell_val])).iloc[0] == clean_and_convert_numeric(pd.Series([cell_val])).iloc[0]: # isna check for parsed numeric
                                        is_text_content = True
                                        break

                                if has_keyword_in_header: # Strong candidate
                                    metric_col_name = col
                                    break
                                elif non_numeric_ratio > 0.7 and df_sheet[col].nunique() > 1 and is_text_content: # Mostly text, not just one repeated value or empty, and has text content
                                    potential_metric_cols.append(col)
                            
                            if metric_col_name is None and potential_metric_cols:
                                # If no strong keyword match, take the first suitable potential column
                                metric_col_name = potential_metric_cols[0]

                            if metric_col_name:
                                df_sheet = df_sheet[df_sheet[metric_col_name].notna() & (df_sheet[metric_col_name] != '')].copy()
                                if df_sheet.empty:
                                    st.warning(f"  Warning: No valid data rows found after cleaning metric column in sheet '{sheet_name}'. Skipping.")
                                    continue
                                
                                if not df_sheet[metric_col_name].is_unique:
                                    df_sheet[metric_col_name] = df_sheet[metric_col_name].astype(str) + '_' + df_sheet.groupby(metric_col_name).cumcount().astype(str)
                                    st.warning(f"  Warning: Duplicate metric names found in sheet '{sheet_name}'. Appending numbers to make them unique.")

                                df_sheet.rename(columns={metric_col_name: 'Metric'}, inplace=True)
                                df_sheet.set_index('Metric', inplace=True)
                                st.write(f"  Debug: After identifying and setting 'Metric' as index for '{sheet_name}'. Shape: {df_sheet.shape}")
                            else:
                                st.warning(f"  Warning: Could not identify a suitable 'Metric' column (e.g., 'Financial Items' or similar text-based column) in sheet '{sheet_name}'. Skipping.")
                                continue
                            
                            # Transpose the DataFrame
                            df_transposed = df_sheet.T
                            st.write(f"  Debug: Transposed DataFrame shape for '{sheet_name}': {df_transposed.shape}")

                            # Clean and convert all new columns (financial metrics and years)
                            for col in df_transposed.columns:
                                df_transposed[col] = clean_and_convert_numeric(df_transposed[col])
                            
                            # Ensure the index (years) is also numeric if possible
                            df_transposed.index = pd.to_numeric(df_transposed.index, errors='coerce')
                            
                            df_transposed = df_transposed[df_transposed.index.notna()]
                            if df_transposed.empty:
                                st.warning(f"  Warning: No valid year data found after converting index to numeric in sheet '{sheet_name}'. Skipping.")
                                continue

                            df_transposed.reset_index(inplace=True)
                            df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)
                            st.write(f"  Debug: Final processed DataFrame head for '{sheet_name}':")
                            st.dataframe(df_transposed.head()) 

                            if df_transposed.select_dtypes(include=['number']).drop(columns=['Year'], errors='ignore').empty:
                                st.warning(f"Processed sheet '{sheet_name}' but found no numeric data for metrics after all steps. Skipping.")
                                continue

                            all_loaded_sheets_data[f"{uploaded_file.name}_{sheet_name}"] = df_transposed

                        except Exception as sheet_e:
                            st.error(f"Error processing sheet '{sheet_name}' in '{uploaded_file.name}': {sheet_e}. This sheet might have an unexpected structure. Debug info: Check previous debug messages for details.")
                            st.info("Ensure your Excel sheet has clear headers (like 'Financial Items' and years) and consistent data formats.")

                else:
                    st.warning(f"Unsupported file type: {uploaded_file.name}. Only CSV, Excel, and pasted text are processed for charting.")
                    
            except Exception as file_e:
                st.error(f"Error reading '{uploaded_file.name}': {file_e}")

    # Process pasted text data
    if raw_text_input:
        st.write("Processing pasted text data...")
        try:
            df_text_data = process_text_data(raw_text_input)
            if df_text_data is not None and not df_text_data.empty:
                st.success("Text data successfully processed!")
                st.dataframe(df_text_data.head())
                all_loaded_sheets_data["Pasted_Text_Data"] = df_text_data
            else:
                st.warning("Could not extract meaningful data from the pasted text. Please check the format.")
        except Exception as text_e:
            st.error(f"Error processing pasted text data: {text_e}")


    # --- Data Selection and Visualization Section ---
    if all_loaded_sheets_data:
        st.success("All available data sources loaded and processed!")
        
        # --- Sheet Selection ---
        st.header("📝 Select Data Sheets for Analysis")
        available_sheet_keys = list(all_loaded_sheets_data.keys())
        
        selected_sheet_keys = st.multiselect(
            "Select the sheets/data sources you want to analyze:",
            options=available_sheet_keys,
            default=available_sheet_keys, 
            help="You can select multiple sources. Data from selected sources will be combined."
        )

        if not selected_sheet_keys:
            st.warning("Please select at least one sheet/data source to proceed with visualization.")
            st.stop() 

        combined_df = pd.concat([all_loaded_sheets_data[key] for key in selected_sheet_keys], ignore_index=True)
        
        st.subheader("First 5 Rows of Combined & Processed Data")
        st.dataframe(combined_df.head())

        # --- Chart Creation Section ---
        st.header("📈 Data Visualization")

        all_numeric_columns = combined_df.select_dtypes(include=['number']).columns.tolist()
        if 'Year' in all_numeric_columns:
            all_numeric_columns.remove('Year')
        
        all_numeric_columns = [col for col in all_numeric_columns if not combined_df[col].isnull().all()]
        
        if not all_numeric_columns:
            st.warning("No numeric metrics found across selected sheets for visualization. Please check your file structure.")
            st.stop()

        # --- Metric Selection ---
        custom_metric_input = st.text_input(
            "Enter specific metric names (comma-separated, case-insensitive) for custom charts, or leave empty to select from list:",
            help="E.g., EBITDA, DISCOUNTED CASH FLOW, WACC. These must match your financial item headers."
        )

        selected_metrics_for_chart = []

        if custom_metric_input:
            input_metrics_raw = [col.strip() for col in custom_metric_input.split(',')]
            
            metric_name_map = {col.lower().strip(): col for col in all_numeric_columns}
            
            valid_custom_metrics = []
            not_found_metrics = []

            for input_metric in input_metrics_raw:
                if input_metric.lower().strip() in metric_name_map:
                    valid_custom_metrics.append(metric_name_map[input_metric.lower().strip()])
                else:
                    not_found_metrics.append(input_metric)

            if not valid_custom_metrics:
                st.warning("None of the entered metrics were found or contain numeric data. Please check spelling and ensure they are financial metrics.")
            else:
                selected_metrics_for_chart = list(set(valid_custom_metrics))
                st.info(f"Custom metrics selected: **{', '.join(selected_metrics_for_chart)}**")
                if not_found_metrics:
                    st.warning(f"Could not find some metrics you entered: {', '.join(not_found_metrics)}. Please check their exact spelling.")
        else:
            default_metrics_multiselect = []
            potential_defaults = ['EBITDA', 'DISCOUNTED CASH FLOW', 'GROWTH RATE', 'WACC', 'PROFIT', 'LOAN REFUND PAYMENT', 'LOAN', 'GROWTH %', 'INTEREST'] # Added more potential defaults
            for p_col in potential_defaults:
                found_col = next((col for col in all_numeric_columns if col.lower() == p_col.lower()), None)
                if found_col and found_col not in default_metrics_multiselect:
                    default_metrics_multiselect.append(found_col)

            selected_metrics_for_chart = st.multiselect(
                "Or, select metrics from the list for general analysis:",
                options=all_numeric_columns,
                default=default_metrics_multiselect,
                help="Choose financial metrics you want to visualize in the chart."
            )

        if not selected_metrics_for_chart:
            st.warning("Please select or enter at least one numeric metric to visualize.")
            st.stop() 

        # --- Chart Type Selection (MORE OPTIONS) ---
        chart_type = st.selectbox(
            "Which type of chart would you like?",
            ("Line Chart", "Bar Chart", "Stacked Bar Chart", "Area Chart", "Box Plot", "Scatter Plot", "Histogram"),
            key="chart_type_selector",
            help="Select a chart type to visualize your data."
        )

        st.write(f"Currently visualizing: {', '.join(selected_metrics_for_chart)} with a **{chart_type}**.")

        st.subheader("Comparative Charts")
        
        fig, ax = plt.subplots(figsize=(14, 7)) 

        try:
            cols_to_plot = ['Year'] + selected_metrics_for_chart if 'Year' in combined_df.columns else selected_metrics_for_chart
            plot_data_df = combined_df[cols_to_plot].copy() 
            plot_data_df.dropna(how='all', inplace=True, subset=selected_metrics_for_chart)

            if plot_data_df.empty:
                st.warning("No valid numeric data found for the selected metrics after cleaning. Please check your data.")
            else:
                if 'Year' in plot_data_df.columns:
                    plot_data_df['Year'] = pd.to_numeric(plot_data_df['Year'], errors='coerce')
                    plot_data_df.sort_values(by='Year', inplace=True)
                    if plot_data_df['Year'].dtype == 'float64':
                        plot_data_df['Year'] = plot_data_df['Year'].astype(int, errors='ignore')

                if chart_type == "Line Chart":
                    if 'Year' in plot_data_df.columns:
                        df_melted = plot_data_df.melt(
                            id_vars=['Year'], 
                            value_vars=selected_metrics_for_chart, 
                            var_name="Metric", 
                            value_name="Value"
                        )
                        sns.lineplot(data=df_melted, x='Year', y="Value", hue="Metric", ax=ax, marker='o') 
                        ax.set_xlabel("Year")
                        ax.set_title("Selected Metrics - Line Chart Over Years")
                    else:
                        st.warning("No 'Year' column found for line chart. Plotting against data point index.")
                        df_melted = plot_data_df.reset_index().melt(
                            id_vars=['index'], 
                            value_vars=selected_metrics_for_chart, 
                            var_name="Metric", 
                            value_name="Value"
                        )
                        sns.lineplot(data=df_melted, x="index", y="Value", hue="Metric", ax=ax, marker='o')
                        ax.set_xlabel("Data Point Index")
                        ax.set_title("Selected Metrics - Line Chart")

                    ax.set_ylabel("Value")
                    ax.legend(title="Metric", loc='best')
                    ax.grid(True)
                
                elif chart_type == "Bar Chart":
                    if 'Year' in plot_data_df.columns and len(selected_metrics_for_chart) == 1:
                        sns.barplot(x='Year', y=selected_metrics_for_chart[0], data=plot_data_df, ax=ax)
                        ax.set_title(f"{selected_metrics_for_chart[0]} Over Years - Bar Chart")
                        ax.set_xlabel("Year")
                        ax.set_ylabel(selected_metrics_for_chart[0])
                        ax.tick_params(axis='x', rotation=45)
                    else:
                        bar_data = plot_data_df[selected_metrics_for_chart].mean().reset_index()
                        bar_data.columns = ['Metric', 'Average Value']
                        sns.barplot(x='Metric', y='Average Value', data=bar_data, ax=ax)
                        ax.set_title("Selected Metrics - Average Values (Bar Chart)")
                        ax.set_ylabel("Average Value")
                        ax.set_xlabel("Metric")
                        ax.tick_params(axis='x', rotation=45)
                        for container in ax.containers:
                            ax.bar_label(container, fmt='%.2f')
                    
                elif chart_type == "Stacked Bar Chart":
                    if 'Year' in plot_data_df.columns:
                        plot_data_df.set_index('Year')[selected_metrics_for_chart].plot(kind='bar', stacked=True, ax=ax)
                        ax.set_title("Selected Metrics - Stacked Bar Chart Over Years")
                        ax.set_xlabel("Year")
                        ax.set_ylabel("Value")
                        ax.legend(title="Metric", loc='best')
                        ax.tick_params(axis='x', rotation=45)
                    else:
                        st.warning("Stacked Bar Chart requires a 'Year' column for plotting. Please use a different chart type or ensure your data has a 'Year' column.")
                        st.stop() 

                elif chart_type == "Area Chart":
                    if 'Year' in plot_data_df.columns:
                        plot_data_df.set_index('Year')[selected_metrics_for_chart].plot(kind='area', stacked=True, ax=ax, alpha=0.7)
                        ax.set_title("Selected Metrics - Stacked Area Chart Over Years")
                        ax.set_xlabel("Year")
                        ax.set_ylabel("Value")
                        ax.legend(title="Metric", loc='best')
                    else:
                        st.warning("Area Chart requires a 'Year' column for plotting. Please use a different chart type or ensure your data has a 'Year' column.")
                        st.stop() 

                elif chart_type == "Box Plot":
                    sns.boxplot(data=plot_data_df[selected_metrics_for_chart], ax=ax)
                    ax.set_title("Selected Metrics - Box Plot")
                    ax.set_ylabel("Value Range")
                    ax.set_xlabel("Metric")
                    ax.tick_params(axis='x', rotation=45)

                elif chart_type == "Scatter Plot":
                    if 'Year' in plot_data_df.columns and len(selected_metrics_for_chart) >= 1:
                        df_melted = plot_data_df.melt(
                            id_vars=['Year'], 
                            value_vars=selected_metrics_for_chart, 
                            var_name="Metric", 
                            value_name="Value"
                        )
                        sns.scatterplot(data=df_melted, x='Year', y="Value", hue="Metric", ax=ax)
                        ax.set_xlabel("Year")
                        ax.set_ylabel("Value")
                        ax.set_title("Selected Metrics - Scatter Plot Over Years")
                        ax.legend(title="Metric", loc='best')
                        ax.grid(True)
                    else:
                        st.warning("Scatter Plot requires a 'Year' column. For single metric, it plots against Year. For multiple metrics, it differentiates by hue. Please ensure your data has a 'Year' column.")
                        st.stop()
                
                elif chart_type == "Histogram":
                    if len(selected_metrics_for_chart) == 1:
                        sns.histplot(data=plot_data_df, x=selected_metrics_for_chart[0], kde=True, ax=ax)
                        ax.set_title(f"Distribution of {selected_metrics_for_chart[0]} - Histogram")
                        ax.set_xlabel(selected_metrics_for_chart[0])
                        ax.set_ylabel("Frequency")
                    else:
                        st.warning("Histogram can only be generated for a single selected metric. Please select only one metric for a histogram.")
                        st.stop()

                plt.tight_layout()
                st.pyplot(fig)

                chart_buffer = BytesIO()
                fig.savefig(chart_buffer, format="png", bbox_inches="tight")
                chart_buffer.seek(0)
                st.download_button(
                    label="Download Chart as PNG 🖼️",
                    data=chart_buffer.getvalue(),
                    file_name="financial_chart.png",
                    mime="image/png",
                    help="Download the generated chart as a PNG image file."
                )

                plt.close(fig)

        except Exception as e:
            st.error(f"Error creating chart: {e}")
            st.info("Please ensure your selected metrics contain numeric data suitable for plotting and are not entirely empty after cleaning. Debug info: Check previous debug messages for details.")
    else:
        st.info("No files uploaded or text pasted yet. Please drag your financial data here or paste it!")