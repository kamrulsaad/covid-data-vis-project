import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Get the absolute path to the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_file_path = os.path.join(project_root, 'data', 'covid_data.csv')

print(f"Attempting to read data from: {data_file_path}")

# Read the data
df = pd.read_csv(data_file_path)

# Convert date strings to datetime objects
df['date'] = pd.to_datetime(df['date'])

def format_number(value):
    """
    Helper function to format numbers, handling missing values gracefully.
    Returns 'No data' for missing values, otherwise formats the number with commas.
    """
    if pd.isna(value):
        return 'No data'
    return f"{int(value):,}"

def prepare_choropleth_data(date, metric='total_cases_per_million'):
    """
    Prepare data for a specific date and metric, handling missing values.
    """
    # Filter data for the specific date
    date_data = df[df['date'] == date].copy()
    
    # Create hover text with proper handling of missing values
    date_data['hover_text'] = date_data.apply(
        lambda x: f"""
        Country: {x['location']}<br>
        Total Cases: {format_number(x['total_cases'])}<br>
        Total Deaths: {format_number(x['total_deaths'])}<br>
        Cases per Million: {format_number(x[metric])}
        """, axis=1)
    
    return date_data

# Get the most recent date in our dataset
latest_date = df['date'].max()

# Create the choropleth map
date_data = prepare_choropleth_data(latest_date)

# Create the figure using Plotly
fig = go.Figure(data=go.Choropleth(
    locations=date_data['iso_code'],
    z=date_data['total_cases_per_million'],
    text=date_data['hover_text'],
    colorscale='Reds',
    autocolorscale=False,
    colorbar_title="Cases per Million",
    # Add handling for missing values in the color scale
    zmin=0,
    zmid=date_data['total_cases_per_million'].median(),
    zmax=date_data['total_cases_per_million'].quantile(0.95),  # Using 95th percentile to handle outliers
))

# Update the layout to match OWID style
fig.update_layout(
    title={
        'text': f'COVID-19 Cases per Million People (as of {latest_date.strftime("%B %d, %Y")})',
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'
    },
    geo=dict(
        showframe=False,
        showcoastlines=True,
        projection_type='equirectangular'
    ),
    width=1000,
    height=600
)

# Show the figure in your browser
fig.show()