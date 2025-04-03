import streamlit as st
import pandas as pd
import zipfile
import os
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import skew, kurtosis
from scipy.signal import find_peaks
from scipy.fftpack import fft, fftfreq

# Function to reset session state
def reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# Streamlit UI
st.title("Bead Segmentation & Feature Extraction")

# Sidebar
st.sidebar.header("Upload & Settings")

# File uploader
uploaded_file = st.sidebar.file_uploader("Upload a ZIP file containing CSV files", type=["zip"], on_change=reset_session)

if uploaded_file:
    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        extract_path = "temp_extracted"
        zip_ref.extractall(extract_path)
        csv_files = [os.path.join(extract_path, f) for f in os.listdir(extract_path) if f.endswith(".csv")]
        st.session_state["csv_files"] = csv_files  # Reset stored CSV files
        st.sidebar.success(f"Loaded {len(csv_files)} CSV files.")

# Select CSV file(s) for correlation analysis
if "csv_files" in st.session_state and st.session_state["csv_files"]:
    selected_csvs = st.sidebar.multiselect("Select CSV file(s) for correlation", [os.path.basename(f) for f in st.session_state["csv_files"]])
    aggregation = st.sidebar.checkbox("Aggregate multiple files")

# Select filter column and threshold
if "csv_files" in st.session_state and st.session_state["csv_files"]:
    sample_df = pd.read_csv(st.session_state["csv_files"][0])
    filter_column = st.sidebar.selectbox("Select filter column", sample_df.columns)
    filter_threshold = st.sidebar.number_input("Enter filter threshold", value=0.0)
    
    if st.sidebar.button("Segment Beads"):
        st.session_state["segmented_data"] = []  # Reset segmented data
        st.session_state["metadata"] = []
        for file in st.session_state["csv_files"]:
            df = pd.read_csv(file)
            signal = df[filter_column].to_numpy()
            start_indices, end_indices = [], []
            i = 0
            while i < len(signal):
                if signal[i] > filter_threshold:
                    start = i
                    while i < len(signal) and signal[i] > filter_threshold:
                        i += 1
                    end = i - 1
                    start_indices.append(start)
                    end_indices.append(end)
                else:
                    i += 1
            segments = list(zip(start_indices, end_indices))
            for bead_num, (start, end) in enumerate(segments, start=1):
                st.session_state["metadata"].append({
                    "file": file,
                    "bead_number": bead_num,
                    "start_index": start,
                    "end_index": end
                })
        st.sidebar.success("Bead segmentation completed!")

# Feature selection
if "metadata" in st.session_state and st.session_state["metadata"]:
    feature_options = [
        "mean", "std", "var", "min", "max", "median", "skewness", "kurtosis"
    ]
    selected_features = st.sidebar.multiselect("Select features to extract", ["All"] + feature_options)
    if "All" in selected_features:
        selected_features = feature_options
    
    if st.sidebar.button("Extract Features"):
        extracted_features = []
        progress_bar = st.progress(0)
        for i, entry in enumerate(st.session_state["metadata"]):
            df = pd.read_csv(entry["file"])
            signal = df.iloc[entry["start_index"]:entry["end_index"] + 1, 0].values
            features = {}
            if "mean" in selected_features:
                features["mean"] = np.mean(signal)
            if "std" in selected_features:
                features["std"] = np.std(signal)
            if "var" in selected_features:
                features["var"] = np.var(signal)
            if "min" in selected_features:
                features["min"] = np.min(signal)
            if "max" in selected_features:
                features["max"] = np.max(signal)
            if "median" in selected_features:
                features["median"] = np.median(signal)
            if "skewness" in selected_features:
                features["skewness"] = skew(signal)
            if "kurtosis" in selected_features:
                features["kurtosis"] = kurtosis(signal)
            features.update({"bead_number": entry["bead_number"], "file": entry["file"]})
            extracted_features.append(features)
            progress_bar.progress((i + 1) / len(st.session_state["metadata"]))
        
        features_df = pd.DataFrame(extracted_features)
        features_df["file_name"] = features_df["file"].str.split("/").str[-1]
        features_df = features_df.rename(columns={"file": "file_dir"})
        st.session_state["features_df"] = features_df
        st.sidebar.success("Feature extraction completed!")

# Correlation Heatmap
if "features_df" in st.session_state and selected_csvs:
    filtered_df = st.session_state["features_df"][st.session_state["features_df"]["file_name"].isin(selected_csvs)]
    
    if aggregation and not filtered_df.empty:
        filtered_df = filtered_df.groupby("file_name").mean().reset_index()
    
    if not filtered_df.empty:
        if st.button("Show Correlation Heatmap"):
            corr = filtered_df.drop(columns=["file_dir", "file_name", "bead_number"], errors='ignore').corr()
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, ax=ax)
            st.pyplot(fig)

# Download button
if "features_df" in st.session_state:
    st.download_button(
        label="Download Results", 
        data=st.session_state["features_df"].to_csv(index=False),
        file_name="extracted_features.csv",
        mime="text/csv"
    )
