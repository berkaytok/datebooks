import streamlit as st
import pandas as pd
import plotly.express as px

# Set page config
st.set_page_config(
    page_title="Food Purine Analysis",
    page_icon="🍖",
    layout="wide"
)

# Add title and description
st.title("Food Purine Content Analysis")
st.markdown("""
This application visualizes the relationship between purine content and nutritional density in different foods.
- 🔴 Red points represent animal-based foods
- 🔵 Blue points represent plant-based foods
""")

# Read the data
@st.cache_data  # Cache the data loading
def load_data():
    df = pd.read_csv('data/purine.csv')
    return df

df = load_data()

# Create a function to categorize foods
def categorize_food(food_name):
    animal_keywords = ['fish', 'meat', 'liver', 'heart', 'kidney', 'spleen', 
                      'beef', 'pork', 'chicken', 'lamb', 'veal', 'duck', 
                      'goose', 'turkey', 'ham', 'sausage', 'mussel', 'shrimp',
                      'lobster', 'tongue', 'brain', 'lung']
    return 'Animal-based' if any(keyword in food_name.lower() for keyword in animal_keywords) else 'Plant-based'

# Add category column
df['food_category'] = df['foodname'].apply(categorize_food)

# Add filters in sidebar
st.sidebar.header("Filters")
selected_categories = st.sidebar.multiselect(
    "Select Food Categories",
    options=["Animal-based", "Plant-based"],
    default=["Animal-based", "Plant-based"]
)

# Filter the dataframe
filtered_df = df[df['food_category'].isin(selected_categories)]

# Create interactive scatter plot
fig = px.scatter(
    filtered_df,
    x='purine',
    y='density',
    color='food_category',
    color_discrete_map={
        'Animal-based': 'red',
        'Plant-based': 'blue'
    },
    hover_data=['foodname'],
    title='Relationship between Purine Content and Density in Foods',
    labels={
        'purine': 'Purine Content (mg/100g)',
        'density': 'Density (mg/MJ)',
        'foodname': 'Food Name',
        'food_category': 'Food Category'
    },
    trendline="ols"
)

# Customize layout
fig.update_layout(
    height=600,
    hovermode='closest',
    template='plotly_white',
    legend_title_text='Food Type'
)

# Show plot
st.plotly_chart(fig, use_container_width=True)

# Add data table
st.subheader("Raw Data")
st.dataframe(
    filtered_df.sort_values('purine', ascending=False),
    hide_index=True,
    column_config={
        "foodname": "Food Name",
        "purine": "Purine Content",
        "density": "Density",
        "food_category": "Category"
    }
)