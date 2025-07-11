import streamlit as st
import pandas as pd
from io import BytesIO
from utils.data_extraction import upload_to_azure_space, download_from_storage

# Helper to clean data
def clean_column_values(df):
    df.fillna("", inplace=True)
    df["Agent NPN"] = df["Agent NPN"].astype(str).str.replace(".0", "", regex=False)
    return df

# 📌 1. Upload + Explode States + Save to Azure
def handle_structure_file(uploaded_file):
    file_extension = uploaded_file.name.split(".")[-1].lower()
    if file_extension == "xlsx":
        df_dict = pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")
    else:
        df_dict = {"Sheet1": pd.read_csv(uploaded_file)}

    final_urls = []

    for sheet_name, df in df_dict.items():
        df.fillna("", inplace=True)
        df["States"] = df["States"].astype(str).str.split(",")
        df_exploded = df.explode("States")
        df_exploded["States"] = df_exploded["States"].str.strip()

        # Save to memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_exploded.to_excel(writer, index=False, sheet_name=sheet_name)
        output.seek(0)

        # Upload using helper
        file_url = upload_to_azure_space(file_bytes=output)
        final_urls.append((sheet_name, file_url))

    return final_urls

# 📌 2. Compare with Master File
def compare_data(uploaded_file):
    file_extension = uploaded_file.name.split(".")[-1].lower()

    if file_extension == "xlsx":
        df_dict = pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")
    else:
        df_dict = {"Sheet1": pd.read_csv(uploaded_file)}

    df_master = download_from_storage()
    df_master = clean_column_values(df_master)

    column_mapping = {
        "AgentName": "Agent",
        "NPN": "Agent NPN",
        "AgencyName": "Upline Agency",
        "CarrierName": "Carrier",
        "LOBName": "Line of Business",
        "State": "States",
    }

    result = {"unmatched_master": [], "unmatched_uploaded": []}

    for sheet_name, df_uploaded in df_dict.items():
        df_uploaded.rename(columns=column_mapping, inplace=True)
        df_uploaded = clean_column_values(df_uploaded)

        compare_cols = ["Upline Agency", "Agent", "Agent NPN", "Line of Business", "Carrier", "States"]
        df_uploaded = df_uploaded[[col for col in compare_cols if col in df_uploaded.columns]]
        df_master_filtered = df_master[[col for col in compare_cols if col in df_master.columns]]

        unique_agencies = df_uploaded["Upline Agency"].unique()

        for agency in unique_agencies:
            uploaded_subset = df_uploaded[df_uploaded["Upline Agency"] == agency]
            master_subset = df_master_filtered[df_master_filtered["Upline Agency"] == agency]

            uploaded_subset = uploaded_subset.drop_duplicates()
            master_subset = master_subset.drop_duplicates()

            merged_master = master_subset.merge(uploaded_subset, on=compare_cols, how='left', indicator=True)
            unmatched_master = merged_master[merged_master['_merge'] == 'left_only'].drop(columns=['_merge'])

            merged_uploaded = uploaded_subset.merge(master_subset, on=compare_cols, how='left', indicator=True)
            unmatched_uploaded = merged_uploaded[merged_uploaded['_merge'] == 'left_only'].drop(columns=['_merge'])

            result["unmatched_master"].extend(unmatched_master.to_dict(orient="records"))
            result["unmatched_uploaded"].extend(unmatched_uploaded.to_dict(orient="records"))

    return result

# 🖥️ Streamlit UI
st.set_page_config(page_title="📁 File Tool", layout="wide")
st.title("📁 File Uploader & Comparator")

option = st.sidebar.radio("Choose Action", ["🔄 Structure File", "📊 Compare with Master"])

if option == "🔄 Structure File":
    st.subheader("Explode States and Upload to Azure")
    file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    if file and st.button("Process and Upload"):
        with st.spinner("Processing..."):
            urls = handle_structure_file(file)
            st.success("✅ File exploded and uploaded successfully.")
            for name, url in urls:
                st.markdown(f"📄 **{name}**: [Download File]({url})")

elif option == "📊 Compare with Master":
    st.subheader("Compare Uploaded File with Master File")
    file = st.file_uploader("Upload file to compare", type=["csv", "xlsx"])

    if file and st.button("Compare Now"):
        with st.spinner("Comparing..."):
            result = compare_data(file)

            st.success("✅ Comparison Completed!")

            if result["unmatched_master"]:
                st.subheader("🟥 Unmatched in Master")
                st.dataframe(pd.DataFrame(result["unmatched_master"]))
            else:
                st.info("✅ No unmatched rows in master.")

            if result["unmatched_uploaded"]:
                st.subheader("🟨 Unmatched in Uploaded File")
                st.dataframe(pd.DataFrame(result["unmatched_uploaded"]))
            else:
                st.info("✅ No unmatched rows in uploaded file.")
