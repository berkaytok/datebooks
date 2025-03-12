import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Purine Content Comparison", layout="wide")

# Read the Excel file
df = pd.read_excel('data/PURINE2023.XLSX', sheet_name=0)

# Define the exact purine column name
purine_column = "Total of 4 Purine Bases (mg/100 g)"

# More robust data cleaning - explicitly convert Category column to string first
df['Category'] = df['Category'].astype(str).fillna('Uncategorized').str.strip()
df['Food Description'] = df['Food Description'].fillna('Unknown').astype(str).str.strip()
df[purine_column] = pd.to_numeric(df[purine_column], errors='coerce').fillna(0)

# Remove any empty categories
df = df[df['Category'] != '']

# Add title
st.title("Food Purine Content Comparison Tool")

# Create two columns for side-by-side comparison
col1, col2 = st.columns(2)

with col1:
    st.subheader("First Food Selection")
    # Force conversion to string BEFORE sorting
    # This explicit approach ensures no type comparison issues
    categories1 = sorted(list(map(str, df['Category'].unique())))
    selected_category1 = st.selectbox('Select Food Category 1:', categories1, key='cat1')
    
    # Filter foods by selected category
    foods1 = sorted(df[df['Category'] == selected_category1]['Food Description'].unique().tolist())
    selected_food1 = st.selectbox('Select Food Item 1:', foods1, key='food1')
    
    # Display purine content with safer access
    purine1 = float(df[df['Food Description'] == selected_food1][purine_column].iloc[0])
    st.metric("Purine Content", f"{purine1:.1f} mg/100g")

with col2:
    st.subheader("Second Food Selection")
    # Use the same approach for consistency
    categories2 = sorted(list(map(str, df['Category'].unique())))
    selected_category2 = st.selectbox('Select Food Category 2:', categories2, key='cat2')
    
    # Filter foods by selected category
    foods2 = sorted(df[df['Category'] == selected_category2]['Food Description'].unique().tolist())
    selected_food2 = st.selectbox('Select Food Item 2:', foods2, key='food2')
    
    # Display purine content - ensure this is also converted to float like purine1
    purine2 = float(df[df['Food Description'] == selected_food2][purine_column].iloc[0])
    st.metric("Purine Content", f"{purine2:.1f} mg/100g")

# Show difference
difference = purine1 - purine2
st.markdown("---")
st.subheader("Comparison")
if difference > 0:
    st.write(f"🔍 {selected_food1} has {abs(difference):.1f} mg/100g more purine than {selected_food2}.")
elif difference < 0:
    st.write(f"🔍 {selected_food2} has {abs(difference):.1f} mg/100g more purine than {selected_food1}.")
else:
    st.write(f"🔍 Both {selected_food1} and {selected_food2} have the same purine content.")

# Add data quality warning
st.markdown("---")
st.caption("Note: Some values may have been cleaned or corrected for display purposes.")