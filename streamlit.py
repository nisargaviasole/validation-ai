import streamlit as st
import requests
import pandas as pd
from io import BytesIO

API_URL = "http://localhost:8000"  # Change this if deployed elsewhere

st.set_page_config(page_title="File Comparator", layout="centered")

st.title("📊 Excel/CSV File Comparator")

st.write("Upload your structured file for storage or run a comparison with the master file.")

tab1, tab2 = st.tabs(["🧾 Structure File", "🔍 Compare File"])

with tab1:
    st.subheader("Upload File to Structure and Store")
    structure_file = st.file_uploader("Upload Excel or CSV file", type=["xlsx", "csv"], key="structure")

    if structure_file is not None:
        if st.button("Upload & Store"):
            with st.spinner("Uploading and processing..."):
                files = {"file": (structure_file.name, structure_file, structure_file.type)}
                res = requests.post(f"{API_URL}/structure_file/", files=files)
                if res.status_code == 200:
                    st.success("✅ File structured and uploaded successfully!")
                    st.markdown(f"**File URL:** [Download File]({res.json().get('url')})")
                else:
                    st.error(f"❌ Error: {res.text}")

with tab2:
    st.subheader("Upload File for Comparison with Master File")
    compare_file = st.file_uploader("Upload Excel or CSV file", type=["xlsx", "csv"], key="compare")

    if compare_file is not None:
        if st.button("Compare"):
            with st.spinner("Comparing..."):
                files = {"file": (compare_file.name, compare_file, compare_file.type)}
                res = requests.post(f"{API_URL}/compare_file/", files=files)
                if res.status_code == 200:
                    data = res.json().get("differences", {})
                    unmatched_master = data.get("unmatched_master", [])
                    unmatched_uploaded = data.get("unmatched_uploaded", [])

                    st.success("✅ Comparison Completed!")

                    if unmatched_master:
                        st.subheader("📁 Unmatched Rows in Master File")
                        st.dataframe(pd.DataFrame(unmatched_master))
                    else:
                        st.info("🎉 No unmatched data in Master file")

                    if unmatched_uploaded:
                        st.subheader("📂 Unmatched Rows in Uploaded File")
                        st.dataframe(pd.DataFrame(unmatched_uploaded))
                    else:
                        st.info("🎉 No unmatched data in Uploaded file")
                else:
                    st.error(f"❌ Error: {res.text}")
