import streamlit as st

# Kullanıcının giriş yapıp yapmadığını kontrol et
if not st.session_state.get('logged_in', False):
    st.warning("Bu sayfayı görüntülemek için giriş yapmanız gerekmektedir.")
    st.switch_page("Home_Page.py") # Giriş sayfasına yönlendir
    st.stop() # Sayfanın geri kalan kodunu çalıştırmayı durdur
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
Hoş geldin Murat! Bu uygulama finansal verilerini görselleştirmen için sana yardımcı olacak.
CSV veya Excel dosyalarını yükleyebilir, ya da ham metin verilerini yapıştırabilirsin. Uygulama, finansal metrikleri ve yılları otomatik olarak algılamaya ve grafik oluşturmaya çalışacak.
""")

# --- Helper Function for Data Cleaning ---
def clean_and_convert_numeric(series):
    if series.dtype == 'object':
        series = series.astype(str)
        # Remove common currency symbols, percentage signs, thousands separators, and extra spaces
        series = series.str.replace(r'[\$,€£%]', '', regex=True) 
        # Handle comma as decimal separator if dot is thousands, or vice-versa
        # Let's remove all dots (thousands) and replace comma with dot (decimal) for standardization
        series = series.str.replace(r'\.', '', regex=True) # Remove thousands dots (e.g., 1.000 -> 1000)
        series = series.str.replace(r',', '.', regex=True) # Replace comma decimal with dot decimal (e.g., 123,45 -> 123.45)
        series = series.str.strip() # Remove leading/trailing spaces
    return pd.to_numeric(series, errors='coerce')

# --- Function to intelligently find header and data start ---
def find_data_start_and_header(df_raw):
    num_rows, num_cols = df_raw.shape
    
    potential_header_row_index = -1
    for r_idx in range(min(num_rows, 100)): # Search first 100 rows for a potential header
        row_values = df_raw.iloc[r_idx].dropna().tolist()
        if not row_values: # Skip entirely empty rows
            continue

        row_str_values = [str(val).lower().strip() for val in row_values]
        
        # Check for keywords related to financial items in header candidates
        financial_keywords = ['financial items', 'finansal kalemler', 'metrik', 'açıklama', 'description', 'gider', 'gelir', 'kalem', 'item', 'metrics', 'kalemler']
        has_financial_keywords = any(any(keyword in s for keyword in financial_keywords) for s in row_str_values)
        
        # Check for year-like numbers (e.g., 1900-2099)
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
            # Handle duplicate column names by appending a number
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

# --- IMPROVED: Function to extract data from raw text ---
def process_text_data(raw_text):
    lines = raw_text.strip().split('\n')
    
    # Try to read with different delimiters
    # Prioritize tab, then semicolon, then comma, then multiple spaces
    delimiters = ['\t', ';', ',', r'\s{2,}'] # Regex for 2 or more spaces

    df_raw = None
    for delim in delimiters:
        try:
            # Create a list of lists from the raw text using the current delimiter
            temp_data = []
            for line in lines:
                if not line.strip(): # Skip empty lines
                    continue
                # Split based on delimiter, ensuring to handle potential extra spaces around parts
                parts = re.split(delim, line.strip())
                temp_data.append([p.strip() for p in parts if p.strip()]) # Strip parts and remove empty strings

            # Find the maximum number of columns found in any row
            max_cols = max(len(row) for row in temp_data) if temp_data else 0
            if max_cols == 0:
                continue # No data found with this delimiter

            # Pad rows to ensure they all have the same number of columns
            padded_data = [row + [''] * (max_cols - len(row)) for row in temp_data]
            
            df_temp = pd.DataFrame(padded_data)
            
            # Check if this DataFrame looks plausible (e.g., more than 1 column and more than 1 row)
            if df_temp.shape[0] > 1 and df_temp.shape[1] > 1:
                df_raw = df_temp
                st.write(f"  Debug (Text Data): Successfully parsed with delimiter: '{delim}'")
                break # Found a suitable delimiter
        except Exception as e:
            st.write(f"  Debug (Text Data): Failed with delimiter '{delim}': {e}")
            continue

    if df_raw is None or df_raw.empty:
        st.warning("Yapıştırılan metin verisi yaygın ayırıcılarla ayrıştırılamadı. Lütfen net bir tablo formatı olduğundan emin olun.")
        return None
    
    st.write("  Debug (Text Data): Ham ayrıştırılmış metin verisi ilk 5 satır:")
    st.dataframe(df_raw.head())

    # --- Now apply the header and metric detection logic similar to Excel ---
    df_processed, header_row_index = find_data_start_and_header(df_raw)

    if df_processed is None or df_processed.empty:
        st.warning("Yapıştırılan metinden başlık ve veri başlangıcı otomatik olarak algılanamadı veya sonuç DataFrame boş. Metin verisi atlanıyor.")
        return None
    
    st.write(f"  Debug (Text Data): Başlık satırı şu indekste bulundu: {header_row_index}. Başlangıç DataFrame sütunları: {df_processed.columns.tolist()}")

    # Identify and rename the 'Metric' column
    metric_col_name = None
    potential_metric_cols = []
    for col_idx, col in enumerate(df_processed.columns):
        # Heuristic: A metric column should contain mostly text (non-numeric)
        # and have some unique values, not be entirely empty.
        non_numeric_ratio = pd.to_numeric(df_processed[col], errors='coerce').isna().sum() / len(df_processed[col].dropna()) if len(df_processed[col].dropna()) > 0 else 0
        
        col_lower = str(col).lower()
        financial_keywords = ['financial items', 'finansal kalemler', 'metrik', 'açıklama', 'description', 'gider', 'gelir', 'kalem', 'item', 'metrics', 'kalemler']
        has_keyword_in_header = any(keyword in col_lower for keyword in financial_keywords)

        # Check first few rows of the column for text (not just numbers or empty)
        is_text_content = False
        for cell_val in df_processed[col].head(5).dropna():
            if isinstance(cell_val, str) and not clean_and_convert_numeric(pd.Series([cell_val])).iloc[0] == clean_and_convert_numeric(pd.Series([cell_val])).iloc[0]: # isna check for parsed numeric
                is_text_content = True
                break

        if has_keyword_in_header: # Strong candidate
            metric_col_name = col
            break
        elif non_numeric_ratio > 0.7 and df_processed[col].nunique() > 1 and is_text_content: # Mostly text, not just one repeated value or empty, and has text content
            potential_metric_cols.append(col)
    
    if metric_col_name is None and potential_metric_cols:
        metric_col_name = potential_metric_cols[0]

    if metric_col_name:
        # Filter out rows where the metric column is empty or NaN
        df_processed = df_processed[df_processed[metric_col_name].notna() & (df_processed[metric_col_name] != '')].copy()
        if df_processed.empty:
            st.warning(f"  Uyarı (Metin Verisi): Metrik sütunu temizlendikten sonra geçerli veri satırı bulunamadı. Atlanıyor.")
            return None
        
        # Handle duplicate metric names for unique indexing
        if not df_processed[metric_col_name].is_unique:
             df_processed[metric_col_name] = df_processed[metric_col_name].astype(str) + '_' + df_processed.groupby(metric_col_name).cumcount().astype(str)
             st.warning(f"  Uyarı (Metin Verisi): Tekrarlayan metrik adları bulundu. Tekil hale getirmek için numaralar ekleniyor.")

        df_processed.rename(columns={metric_col_name: 'Metric'}, inplace=True)
        df_processed.set_index('Metric', inplace=True)
        st.write(f"  Debug (Text Data): 'Metric' olarak ayarlandıktan sonraki şekil: {df_processed.shape}")
    else:
        st.warning(f"  Uyarı (Metin Verisi): Uygun bir 'Metrik' sütunu (örn. 'Finansal Kalemler' veya benzeri metin tabanlı sütun) tespit edilemedi. Atlanıyor.")
        return None
    
    # Transpose the DataFrame to have years as rows and metrics as columns
    df_transposed = df_processed.T
    st.write(f"  Debug (Text Data): Transpoze edilmiş DataFrame şekil: {df_transposed.shape}")

    # Clean and convert all new columns (financial metrics and years)
    for col in df_transposed.columns:
        df_transposed[col] = clean_and_convert_numeric(df_transposed[col])
    
    # Ensure the index (which should be years after transpose) is numeric
    df_transposed.index = pd.to_numeric(df_transposed.index, errors='coerce')
    
    # Drop rows where year is not a valid number (NaN)
    df_transposed = df_transposed[df_transposed.index.notna()]
    if df_transposed.empty:
        st.warning(f"  Uyarı (Metin Verisi): İndeks yıla dönüştürüldükten sonra geçerli yıl verisi bulunamadı. Atlanıyor.")
        return None

    df_transposed.reset_index(inplace=True)
    df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)
    st.write(f"  Debug (Text Data): Son işlenmiş DataFrame ilk 5 satır:")
    st.dataframe(df_transposed.head()) 

    # Final check: ensure there are still numeric columns other than 'Year'
    if df_transposed.select_dtypes(include=['number']).drop(columns=['Year'], errors='ignore').empty:
        st.warning(f"İşlenmiş metin verisinde tüm adımlardan sonra metrikler için sayısal veri bulunamadı. Atlanıyor.")
        return None

    return df_transposed


# --- File Upload Section ---
st.header("Veri Dosyalarını Yükle 📁 veya Metin Verisi Yapıştır 📋")

uploaded_files = st.file_uploader(
    "Lütfen CSV veya Excel dosyalarını buraya sürükleyip bırakın ya da seçmek için göz atın.",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

raw_text_input = st.text_area(
    "Alternatif olarak, finansal verilerinizi buraya yapıştırın (örn. bir rapordan kopyalanan tablo):",
    height=200,
    help="Sütunları sekmeler, boşluklar, virgüller veya noktalı virgüllerle ayrılmış verileri yapıştırın. Genellikle ilk sütun finansal kalem olarak, sonraki sütunlar ise yıllar/değerler olarak tanınır."
)

all_loaded_sheets_data = {} # Stores {file_name_sheet_name: DataFrame}

if uploaded_files or raw_text_input:
    # Process uploaded files first
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.write(f"Dosya işleniyor: **{uploaded_file.name}**")
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                    st.write(f"  Debug: CSV dosyası yüklendi. Sütunlar: {df.columns.tolist()}")
                    
                    # Heuristic for CSVs: try to identify the 'Metric' column and 'Year' column
                    potential_metric_col = None
                    potential_year_col = None
                    
                    for col in df.columns:
                        # Check if column is mostly numeric and contains year-like values
                        is_numeric_col = pd.to_numeric(df[col], errors='coerce').notna().sum() / len(df[col].dropna()) > 0.8 if len(df[col].dropna()) > 0 else 0
                        has_year_pattern = df[col].astype(str).str.match(r'^\d{4}$').any() and pd.to_numeric(df[col], errors='coerce').max() <= 2099 and pd.to_numeric(df[col], errors='coerce').min() >= 1900
                        
                        if is_numeric_col and has_year_pattern:
                            potential_year_col = col
                        # More robust check for metric column: high non-numeric ratio and some unique text values
                        elif pd.to_numeric(df[col], errors='coerce').isna().sum() / len(df[col].dropna()) > 0.5 and df[col].nunique() > 1 and \
                             any(isinstance(val, str) and len(val.strip()) > 1 for val in df[col].dropna().head()): 
                            if potential_metric_col is None: # Take the first suitable non-numeric column
                                potential_metric_col = col
                    
                    if potential_metric_col and potential_year_col:
                        st.write(f"  Debug: CSV - Tespit Edilen Metrik Sütunu: '{potential_metric_col}', Yıl Sütunu: '{potential_year_col}'")
                        df.rename(columns={potential_metric_col: 'Metric'}, inplace=True)
                        
                        # Handle duplicate metric names
                        if not df['Metric'].is_unique:
                             df['Metric'] = df['Metric'].astype(str) + '_' + df.groupby('Metric').cumcount().astype(str)
                             st.warning(f"  Uyarı: '{uploaded_file.name}' dosyasında tekrarlayan metrik adları bulundu. Tekil hale getirmek için numaralar ekleniyor.")

                        df.set_index('Metric', inplace=True)
                        df_processed = df.T.copy() # Transpose to get metrics as columns
                        df_processed.reset_index(inplace=True)
                        df_processed.rename(columns={df_processed.columns[0]: 'Year'}, inplace=True) # First col after transpose becomes Year
                        
                        for col in df_processed.columns:
                            df_processed[col] = clean_and_convert_numeric(df_processed[col])
                        
                        df_processed['Year'] = pd.to_numeric(df_processed['Year'], errors='coerce')
                        df_processed.dropna(subset=['Year'], inplace=True) # Drop rows where Year is NaN

                        if not df_processed.empty and not df_processed.select_dtypes(include=['number']).drop(columns=['Year'], errors='ignore').empty:
                            all_loaded_sheets_data[f"{uploaded_file.name}_sheet_1"] = df_processed
                        else:
                            st.warning(f"CSV dosyası '{uploaded_file.name}' işlendi ancak grafiğe uygun geçerli sayısal veri içermiyor. Atlanıyor.")
                    else:
                        st.warning(f"CSV dosyası '{uploaded_file.name}' içinde Metrik ve Yıl sütunları otomatik olarak tespit edilemedi. Lütfen CSV'nizin finansal veriler için net bir yapıya sahip olduğundan emin olun.")


                elif uploaded_file.name.endswith('.xlsx'):
                    xls = pd.ExcelFile(uploaded_file)
                    sheet_names = xls.sheet_names
                    
                    st.subheader(f"{uploaded_file.name} içindeki sayfalar:")
                    for sheet_name in sheet_names:
                        st.write(f"- Sayfa okunuyor: **{sheet_name}**")
                        try:
                            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
                            st.write(f"  Debug: '{sheet_name}' için ham DataFrame şekli: {df_raw.shape}")
                            
                            df_sheet, header_row_index = find_data_start_and_header(df_raw)
                            
                            if df_sheet is None or df_sheet.empty:
                                st.warning(f"'{sheet_name}' sayfası için başlık ve veri başlangıcı otomatik olarak algılanamadı veya sonuç DataFrame boş. Bu sayfa atlanıyor.")
                                continue
                            
                            st.write(f"  Debug: Başlık satırı şu indekste bulundu: {header_row_index}. Başlangıç DataFrame sütunları: {df_sheet.columns.tolist()}")

                            # --- Identify and rename the 'Metric' column (the column containing financial item names) ---
                            metric_col_name = None
                            potential_metric_cols = []
                            for col_idx, col in enumerate(df_sheet.columns):
                                # Heuristic: A metric column should contain mostly text (non-numeric)
                                # and have some unique values, not be entirely empty.
                                non_numeric_ratio = pd.to_numeric(df_sheet[col], errors='coerce').isna().sum() / len(df_sheet[col].dropna()) if len(df_sheet[col].dropna()) > 0 else 0
                                
                                col_lower = str(col).lower()
                                financial_keywords = ['financial items', 'finansal kalemler', 'metrik', 'açıklama', 'description', 'gider', 'gelir', 'kalem', 'item', 'metrics', 'kalemler']
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
                                    st.warning(f"  Uyarı: '{sheet_name}' sayfasında metrik sütunu temizlendikten sonra geçerli veri satırı bulunamadı. Atlanıyor.")
                                    continue
                                
                                if not df_sheet[metric_col_name].is_unique:
                                     df_sheet[metric_col_name] = df_sheet[metric_col_name].astype(str) + '_' + df_sheet.groupby(metric_col_name).cumcount().astype(str)
                                     st.warning(f"  Uyarı: '{sheet_name}' sayfasında tekrarlayan metrik adları bulundu. Tekil hale getirmek için numaralar ekleniyor.")

                                df_sheet.rename(columns={metric_col_name: 'Metric'}, inplace=True)
                                df_sheet.set_index('Metric', inplace=True)
                                st.write(f"  Debug: '{sheet_name}' için 'Metric' olarak indeks ayarlandıktan sonraki şekil: {df_sheet.shape}")
                            else:
                                st.warning(f"  Uyarı: '{sheet_name}' sayfasında uygun bir 'Metrik' sütunu (örn. 'Finansal Kalemler' veya benzeri metin tabanlı sütun) tespit edilemedi. Atlanıyor.")
                                continue
                            
                            # Transpose the DataFrame
                            df_transposed = df_sheet.T
                            st.write(f"  Debug: '{sheet_name}' için transpoze edilmiş DataFrame şekli: {df_transposed.shape}")

                            # Clean and convert all new columns (financial metrics and years)
                            for col in df_transposed.columns:
                                df_transposed[col] = clean_and_convert_numeric(df_transposed[col])
                            
                            # Ensure the index (years) is also numeric if possible
                            df_transposed.index = pd.to_numeric(df_transposed.index, errors='coerce')
                            
                            df_transposed = df_transposed[df_transposed.index.notna()] # Drop rows where year is NaN
                            if df_transposed.empty:
                                st.warning(f"  Uyarı: '{sheet_name}' sayfasında indeks yıla dönüştürüldükten sonra geçerli yıl verisi bulunamadı. Atlanıyor.")
                                continue

                            df_transposed.reset_index(inplace=True)
                            df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)
                            st.write(f"  Debug: '{sheet_name}' için son işlenmiş DataFrame ilk 5 satır:")
                            st.dataframe(df_transposed.head()) 

                            if df_transposed.select_dtypes(include=['number']).drop(columns=['Year'], errors='ignore').empty:
                                st.warning(f"İşlenmiş '{sheet_name}' sayfası, tüm adımlardan sonra metrikler için sayısal veri içermiyor. Atlanıyor.")
                                continue

                            all_loaded_sheets_data[f"{uploaded_file.name}_{sheet_name}"] = df_transposed

                        except Exception as sheet_e:
                            st.error(f"'{uploaded_file.name}' dosyasındaki '{sheet_name}' sayfası işlenirken hata oluştu: {sheet_e}. Bu sayfa beklenmeyen bir yapıya sahip olabilir. Hata ayıklama bilgisi: Daha önceki hata ayıklama mesajlarını kontrol edin.")
                            st.info("Excel sayfanızın net başlıklara ('Finansal Kalemler' ve yıllar gibi) ve tutarlı veri formatlarına sahip olduğundan emin olun.")

                else:
                    st.warning(f"Desteklenmeyen dosya türü: {uploaded_file.name}. Yalnızca CSV, Excel ve yapıştırılan metin grafik için işlenir.")
                    
            except Exception as file_e:
                st.error(f"'{uploaded_file.name}' okunurken hata oluştu: {file_e}")

    # Process pasted text data
    if raw_text_input:
        st.write("Yapıştırılan metin verisi işleniyor...")
        try:
            df_text_data = process_text_data(raw_text_input)
            if df_text_data is not None and not df_text_data.empty:
                st.success("Metin verisi başarıyla işlendi!")
                st.dataframe(df_text_data.head())
                all_loaded_sheets_data["Pasted_Text_Data"] = df_text_data
            else:
                st.warning("Yapıştırılan metinden anlamlı veri çıkarılamadı. Lütfen formatı kontrol edin.")
        except Exception as text_e:
            st.error(f"Yapıştırılan metin verisi işlenirken hata oluştu: {text_e}")


    # --- Data Selection and Visualization Section ---
    if all_loaded_sheets_data:
        st.success("Tüm mevcut veri kaynakları yüklendi ve işlendi!")
        
        # --- Sheet Selection ---
        st.header("📝 Analiz Edilecek Veri Kaynaklarını Seç")
        available_sheet_keys = list(all_loaded_sheets_data.keys())
        
        selected_sheet_keys = st.multiselect(
            "Analiz etmek istediğin sayfaları/veri kaynaklarını seç:",
            options=available_sheet_keys,
            default=available_sheet_keys, 
            help="Birden fazla kaynak seçebilirsin. Seçilen kaynaklardan gelen veriler birleştirilecektir."
        )

        if not selected_sheet_keys:
            st.warning("Görselleştirmeye devam etmek için lütfen en az bir sayfa/veri kaynağı seç.")
            st.stop() 

        combined_df = pd.concat([all_loaded_sheets_data[key] for key in selected_sheet_keys], ignore_index=True)
        
        st.subheader("Birleştirilmiş ve İşlenmiş Verinin İlk 5 Satırı")
        st.dataframe(combined_df.head())

        # --- Chart Creation Section ---
        st.header("📈 Veri Görselleştirme")

        all_numeric_columns = combined_df.select_dtypes(include=['number']).columns.tolist()
        if 'Year' in all_numeric_columns:
            all_numeric_columns.remove('Year')
        
        # Remove columns that are entirely null after cleaning
        all_numeric_columns = [col for col in all_numeric_columns if not combined_df[col].isnull().all()]
        
        if not all_numeric_columns:
            st.warning("Seçili sayfalarda görselleştirme için sayısal metrik bulunamadı. Lütfen dosya yapınızı kontrol edin.")
            st.stop()

        # --- Metric Selection ---
        custom_metric_input = st.text_input(
            "Özel grafikler için belirli metrik adlarını girin (virgülle ayrılmış, büyük/küçük harf duyarsız), veya listeden seçmek için boş bırakın:",
            help="Örn: EBITDA, İNDİRGENMİŞ NAKİT AKIŞI, AĞIRLIKLI ORTALAMA SERMAYE MALİYETİ. Bunlar finansal kalem başlıklarınızla eşleşmelidir."
        )

        selected_metrics_for_chart = []

        if custom_metric_input:
            input_metrics_raw = [col.strip() for col in custom_metric_input.split(',')]
            
            # Create a map for case-insensitive matching
            metric_name_map = {col.lower().strip(): col for col in all_numeric_columns}
            
            valid_custom_metrics = []
            not_found_metrics = []

            for input_metric in input_metrics_raw:
                if input_metric.lower().strip() in metric_name_map:
                    valid_custom_metrics.append(metric_name_map[input_metric.lower().strip()])
                else:
                    not_found_metrics.append(input_metric)

            if not valid_custom_metrics:
                st.warning("Girilen metriklerden hiçbiri bulunamadı veya sayısal veri içermiyor. Lütfen yazımı kontrol edin ve bunların finansal metrik olduğundan emin olun.")
            else:
                selected_metrics_for_chart = list(set(valid_custom_metrics)) # Use set to avoid duplicates
                st.info(f"Özel metrikler seçildi: **{', '.join(selected_metrics_for_chart)}**")
                if not_found_metrics:
                    st.warning(f"Girdiğiniz bazı metrikler bulunamadı: {', '.join(not_found_metrics)}. Lütfen tam yazımlarını kontrol edin.")
        else:
            default_metrics_multiselect = []
            # Updated and expanded default potential metrics in Turkish and English
            potential_defaults = [
                'EBITDA', 'DISCOUNTED CASH FLOW', 'GROWTH RATE', 'WACC', 
                'PROFIT', 'LOAN REFUND PAYMENT', 'LOAN', 'GROWTH %', 'INTEREST',
                'Gelir', 'Gider', 'Kar', 'Büyüme Oranı', 'Nakit Akışı', 'Faiz Gideri',
                'Brüt Kar', 'Net Kar', 'Satış Gelirleri', 'Operasyonel Giderler'
            ] 
            for p_col in potential_defaults:
                # Find case-insensitive match from available numeric columns
                found_col = next((col for col in all_numeric_columns if col.lower() == p_col.lower()), None)
                if found_col and found_col not in default_metrics_multiselect:
                    default_metrics_multiselect.append(found_col)

            selected_metrics_for_chart = st.multiselect(
                "Veya, genel analiz için listeden metrikleri seç:",
                options=all_numeric_columns,
                default=default_metrics_multiselect,
                help="Grafikte görselleştirmek istediğiniz finansal metrikleri seçin."
            )

        if not selected_metrics_for_chart:
            st.warning("Lütfen görselleştirmek için en az bir sayısal metrik seçin veya girin.")
            st.stop() 

        # --- Chart Type Selection (MORE OPTIONS) ---
        chart_type = st.selectbox(
            "Hangi tür grafiği istersin?",
            ("Line Chart", "Bar Chart", "Stacked Bar Chart", "Area Chart", "Box Plot", "Scatter Plot", "Histogram"),
            key="chart_type_selector",
            help="Verilerinizi görselleştirmek için bir grafik türü seçin."
        )

        st.write(f"Şu anda görselleştirilenler: {', '.join(selected_metrics_for_chart)} bir **{chart_type}** ile.")

        st.subheader("Karşılaştırmalı Grafikler")
        
        # Use a consistent figure size
        fig, ax = plt.subplots(figsize=(14, 7)) 

        try:
            # Ensure 'Year' column exists and is used if available for time-series charts
            cols_to_plot = ['Year'] + selected_metrics_for_chart if 'Year' in combined_df.columns else selected_metrics_for_chart
            plot_data_df = combined_df[cols_to_plot].copy() 
            
            # Drop rows where all selected metrics are NaN
            plot_data_df.dropna(how='all', inplace=True, subset=selected_metrics_for_chart)

            if plot_data_df.empty:
                st.warning("Temizlemeden sonra seçilen metrikler için geçerli sayısal veri bulunamadı. Lütfen verilerinizi kontrol edin.")
                st.stop() # Stop if no data to plot

            if 'Year' in plot_data_df.columns:
                plot_data_df['Year'] = pd.to_numeric(plot_data_df['Year'], errors='coerce')
                plot_data_df.sort_values(by='Year', inplace=True)
                # Convert Year to int if it's float and looks like a year (e.g., 2020.0 -> 2020)
                if plot_data_df['Year'].dtype == 'float64' and (plot_data_df['Year'] % 1 == 0).all():
                    plot_data_df['Year'] = plot_data_df['Year'].astype(int)

            if chart_type == "Line Chart":
                if 'Year' in plot_data_df.columns:
                    df_melted = plot_data_df.melt(
                        id_vars=['Year'], 
                        value_vars=selected_metrics_for_chart, 
                        var_name="Metric", 
                        value_name="Value"
                    )
                    # Filter out NaN values from melted data to prevent plotting issues
                    df_melted.dropna(subset=['Value'], inplace=True)
                    if df_melted.empty:
                        st.warning("Çizgi grafik için yeterli veri bulunamadı (değerler boş olabilir).")
                        st.stop()
                    sns.lineplot(data=df_melted, x='Year', y="Value", hue="Metric", ax=ax, marker='o') 
                    ax.set_xlabel("Yıl")
                    ax.set_title("Seçilen Metrikler - Yıllar Boyunca Çizgi Grafiği")
                else:
                    st.warning("'Yıl' sütunu bulunamadı. Veri noktası indeksine göre çiziliyor.")
                    df_melted = plot_data_df.reset_index().melt(
                        id_vars=['index'], 
                        value_vars=selected_metrics_for_chart, 
                        var_name="Metric", 
                        value_name="Value"
                    )
                    df_melted.dropna(subset=['Value'], inplace=True)
                    if df_melted.empty:
                        st.warning("Çizgi grafik için yeterli veri bulunamadı (değerler boş olabilir).")
                        st.stop()
                    sns.lineplot(data=df_melted, x="index", y="Value", hue="Metric", ax=ax, marker='o')
                    ax.set_xlabel("Veri Noktası İndeksi")
                    ax.set_title("Seçilen Metrikler - Çizgi Grafiği")

                ax.set_ylabel("Değer")
                ax.legend(title="Metrik", loc='best')
                ax.grid(True)
            
            elif chart_type == "Bar Chart":
                if 'Year' in plot_data_df.columns and len(selected_metrics_for_chart) == 1:
                    sns.barplot(x='Year', y=selected_metrics_for_chart[0], data=plot_data_df, ax=ax)
                    ax.set_title(f"Yıllar Boyunca {selected_metrics_for_chart[0]} - Çubuk Grafiği")
                    ax.set_xlabel("Yıl")
                    ax.set_ylabel(selected_metrics_for_chart[0])
                    ax.tick_params(axis='x', rotation=45)
                    # Add value labels on bars if there are not too many bars
                    if len(plot_data_df['Year'].unique()) < 15:
                        for container in ax.containers:
                            ax.bar_label(container, fmt='%.2f')
                elif len(selected_metrics_for_chart) > 0: # Multiple metrics or no year column
                    bar_data = plot_data_df[selected_metrics_for_chart].mean().reset_index()
                    bar_data.columns = ['Metric', 'Average Value']
                    sns.barplot(x='Metric', y='Average Value', data=bar_data, ax=ax)
                    ax.set_title("Seçilen Metrikler - Ortalama Değerler (Çubuk Grafiği)")
                    ax.set_ylabel("Ortalama Değer")
                    ax.set_xlabel("Metrik")
                    ax.tick_params(axis='x', rotation=45)
                    for container in ax.containers:
                        ax.bar_label(container, fmt='%.2f')
                else:
                    st.warning("Çubuk grafik için en az bir metrik seçili olmalı.")
                    st.stop()
                    
            elif chart_type == "Stacked Bar Chart":
                if 'Year' in plot_data_df.columns:
                    plot_data_df.set_index('Year')[selected_metrics_for_chart].plot(kind='bar', stacked=True, ax=ax)
                    ax.set_title("Seçilen Metrikler - Yıllar Boyunca Yığılmış Çubuk Grafiği")
                    ax.set_xlabel("Yıl")
                    ax.set_ylabel("Değer")
                    ax.legend(title="Metrik", loc='best')
                    ax.tick_params(axis='x', rotation=45)
                else:
                    st.warning("Yığılmış Çubuk Grafiği için 'Yıl' sütunu gereklidir. Lütfen farklı bir grafik türü kullanın veya verilerinizin bir 'Yıl' sütunu içerdiğinden emin olun.")
                    st.stop() 

            elif chart_type == "Area Chart":
                if 'Year' in plot_data_df.columns:
                    plot_data_df.set_index('Year')[selected_metrics_for_chart].plot(kind='area', stacked=True, ax=ax, alpha=0.7)
                    ax.set_title("Seçilen Metrikler - Yıllar Boyunca Yığılmış Alan Grafiği")
                    ax.set_xlabel("Yıl")
                    ax.set_ylabel("Değer")
                    ax.legend(title="Metrik", loc='best')
                else:
                    st.warning("Alan Grafiği için 'Yıl' sütunu gereklidir. Lütfen farklı bir grafik türü kullanın veya verilerinizin bir 'Yıl' sütunu içerdiğinden emin olun.")
                    st.stop() 

            elif chart_type == "Box Plot":
                if len(selected_metrics_for_chart) > 0:
                    sns.boxplot(data=plot_data_df[selected_metrics_for_chart], ax=ax)
                    ax.set_title("Seçilen Metrikler - Kutu Grafiği")
                    ax.set_ylabel("Değer Aralığı")
                    ax.set_xlabel("Metrik")
                    ax.tick_params(axis='x', rotation=45)
                else:
                    st.warning("Kutu grafiği için en az bir metrik seçili olmalı.")
                    st.stop()


            elif chart_type == "Scatter Plot":
                if 'Year' in plot_data_df.columns and len(selected_metrics_for_chart) >= 1:
                    df_melted = plot_data_df.melt(
                        id_vars=['Year'], 
                        value_vars=selected_metrics_for_chart, 
                        var_name="Metric", 
                        value_name="Value"
                    )
                    df_melted.dropna(subset=['Value'], inplace=True)
                    if df_melted.empty:
                        st.warning("Saçılım grafik için yeterli veri bulunamadı (değerler boş olabilir).")
                        st.stop()
                    sns.scatterplot(data=df_melted, x='Year', y="Value", hue="Metric", ax=ax)
                    ax.set_xlabel("Yıl")
                    ax.set_ylabel("Değer")
                    ax.set_title("Seçilen Metrikler - Yıllar Boyunca Saçılım Grafiği")
                    ax.legend(title="Metrik", loc='best')
                    ax.grid(True)
                else:
                    st.warning("Saçılım Grafiği için bir 'Yıl' sütunu ve en az bir metrik gereklidir. Lütfen verilerinizin bir 'Yıl' sütunu içerdiğinden emin olun.")
                    st.stop()
            
            elif chart_type == "Histogram":
                if len(selected_metrics_for_chart) == 1:
                    sns.histplot(data=plot_data_df, x=selected_metrics_for_chart[0], kde=True, ax=ax)
                    ax.set_title(f"{selected_metrics_for_chart[0]} Dağılımı - Histogram")
                    ax.set_xlabel(selected_metrics_for_chart[0])
                    ax.set_ylabel("Frekans")
                else:
                    st.warning("Histogram sadece tek bir seçili metrik için oluşturulabilir. Lütfen histogram için yalnızca bir metrik seçin.")
                    st.stop()

            plt.tight_layout()
            st.pyplot(fig)

            chart_buffer = BytesIO()
            fig.savefig(chart_buffer, format="png", bbox_inches="tight")
            chart_buffer.seek(0)
            st.download_button(
                label="Grafiği PNG Olarak İndir 🖼️",
                data=chart_buffer.getvalue(),
                file_name="finansal_grafik.png",
                mime="image/png",
                help="Oluşturulan grafiği PNG görüntü dosyası olarak indirin."
            )

            plt.close(fig) # Close the figure to free up memory

        except Exception as e:
            st.error(f"Grafik oluşturulurken hata oluştu: {e}")
            st.info("Lütfen seçtiğiniz metriklerin sayısal veri içerdiğinden ve temizlendikten sonra tamamen boş olmadığından emin olun. Hata ayıklama bilgisi: Daha önceki hata ayıklama mesajlarını kontrol edin.")
    else:
        st.info("Henüz dosya yüklenmedi veya metin yapıştırılmadı. Lütfen finansal verilerinizi buraya sürükleyin veya yapıştırın!")