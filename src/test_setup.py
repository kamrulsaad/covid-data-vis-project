# test_setup.py
import pandas as pd
import plotly.express as px

# Read the data
df = pd.read_csv('../data/covid_data.csv')

# Create a simple test plot
fig = px.line(df[df['location'] == 'World'], 
              x='date', 
              y='total_cases',
              title='Global COVID-19 Cases')
fig.show()