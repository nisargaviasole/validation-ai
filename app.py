import streamlit as st
import pandas as pd
import asyncio
from io import BytesIO
from utils.data_extraction import *


def upload_csv(file):
    try:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension == "xlsx":
            df_dict = pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")
        else:
            df_dict = {"Sheet1": pd.read_csv(uploaded_file)}

        for sheet_name, df in df_dict.items():
            df.fillna("", inplace=True)
            df["States"] = df["States"].str.split(",")
            df_exploded = df.explode("States")
            df_exploded["States"] = df_exploded["States"].str.strip()

            # Save to memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_exploded.to_excel(writer, index=False, sheet_name=sheet_name)
            output.seek(0)

            # Upload using helper
            file_url = upload_to_azure_space(
                file_bytes=output,
            )

            return file_url

    except Exception as e:
        print("❌ Error occurred:", str(e))
        raise Exception(f"Processing error: {str(e)}")


def compare_files(uploaded_file):
    try:
        file_extension = uploaded_file.name.split(".")[-1].lower()

        if file_extension == "xlsx":
            df_dict = pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")
        else:
            df_dict = {"Sheet1": pd.read_csv(uploaded_file)}

        print("⬇️ Downloading master file from storage...")
        df_dict_master = download_from_storage()
        print("✅ Master file downloaded successfully.")

        column_mapping = {
            "AgentName": "Agent",
            "NPN": "Agent NPN",
            "AgencyName": "Upline Agency",
            "CarrierName": "Carrier",
            "LOBName": "Line of Business",
            "State": "States",
        }

        final_result = {
            "unmatched_master": [],
            "unmatched_uploaded": []
        }

        for sheet_name, df_uploaded in df_dict.items():
            print(f"📄 Processing sheet: {sheet_name}")
            df_uploaded.rename(columns=column_mapping, inplace=True)

            df_master = df_dict_master
            df_uploaded = clean_column_values(df_uploaded)
            df_master = clean_column_values(df_master)
            compare_cols = ["Upline Agency", "Agent", "Agent NPN", "Line of Business", "Carrier", "States"]

            # Get only required columns
            df_uploaded = df_uploaded[[col for col in compare_cols if col in df_uploaded.columns]]
            df_master = df_master[[col for col in compare_cols if col in df_master.columns]]

            # Get unique agencies from uploaded file only
            unique_agencies = df_uploaded["Upline Agency"].unique()
            print(f"🔍 Found {len(unique_agencies)} unique agencies to compare.")

            unmatched_master_rows = []
            unmatched_uploaded_rows = []

            for agency in unique_agencies:
                print(f"➡️ Comparing data for Agency: {agency}")

                uploaded_subset = df_uploaded[df_uploaded["Upline Agency"] == agency]
                master_subset = df_master[df_master["Upline Agency"] == agency]

                # Drop duplicates for safety
                uploaded_subset = uploaded_subset.drop_duplicates()
                master_subset = master_subset.drop_duplicates()

                # Compare: master not in uploaded
                merged_master = master_subset.merge(uploaded_subset, on=compare_cols, how='left', indicator=True)
                unmatched_master = merged_master[merged_master['_merge'] == 'left_only'].drop(columns=['_merge'])
                unmatched_master_rows.extend(unmatched_master.to_dict(orient="records"))

                # Compare: uploaded not in master
                merged_uploaded = uploaded_subset.merge(master_subset, on=compare_cols, how='left', indicator=True)
                unmatched_uploaded = merged_uploaded[merged_uploaded['_merge'] == 'left_only'].drop(columns=['_merge'])
                unmatched_uploaded_rows.extend(unmatched_uploaded.to_dict(orient="records"))

            final_result["unmatched_master"] = unmatched_master_rows
            final_result["unmatched_uploaded"] = unmatched_uploaded_rows

        print("✅ Comparison completed.")
        return final_result

    except Exception as e:
        print("❌ Error occurred:", str(e))
        raise Exception(f"Processing error: {str(e)}")


# 🖥️ Streamlit UI
st.set_page_config(page_title="📁 File Tool", layout="wide")
st.title("📁 File Uploader & Comparator")

option = st.sidebar.radio("Choose Action", ["🔄 Structure Master File", "📊 Compare with Master"])

if option == "🔄 Structure Master File":
    st.subheader("Explode States and Upload to Azure")
    file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    if file and st.button("Process and Upload"):
        with st.spinner("Processing..."):
            url = upload_csv(file) 
            st.success("✅ File exploded and uploaded successfully.")
            for name, url in urls:
                st.markdown(f"📄 **{name}**: [Download File]({url})")

elif option == "📊 Compare with Master":
    st.subheader("Compare Uploaded File with Master File")
    file = st.file_uploader("Upload file to compare", type=["csv", "xlsx"])

    if file and st.button("Compare Now"):
        with st.spinner("Comparing..."):
            result = compare_files(file)

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