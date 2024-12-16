import os
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from flask_caching import Cache
import dash_bootstrap_components as dbc

# Setup paths and initialize app
current_dir = os.path.dirname(os.path.abspath(__file__))
data_file_path = os.path.join(current_dir, 'data', 'covid_data.csv')

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)
server = app.server

# Setup caching (same as before)
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})
TIMEOUT = 3600

@cache.memoize(timeout=TIMEOUT)
def load_and_process_data():
    """Load and pre-process data with caching"""
    try:
        print(f"Loading data from: {data_file_path}")
        df = pd.read_csv(data_file_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter data
        df = df[df['date'] <= '2024-06-17']
        df = df[df['continent'] != 'Antarctica']
        
        # Pre-process data for each date
        dates = sorted(df['date'].unique())
        processed_data = {}
        
        for date in dates:
            date_data = df[df['date'] == date].copy()
            date_data['total_deaths_per_million'] = date_data['total_deaths_per_million'].fillna(-1)
            processed_data[pd.Timestamp(date)] = date_data
            
        return processed_data, dates
    except Exception as e:
        print(f"Error in data loading: {e}")
        raise

# Create cache directory if needed
cache_dir = os.path.join(current_dir, 'cache-directory')
os.makedirs(cache_dir, exist_ok=True)

# Load data
print("Loading and processing data...")
PROCESSED_DATA, DATES = load_and_process_data()
print("Data processing complete!")

# Custom CSS with new tooltip styles
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>COVID-19 Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #f8f9fa;
                margin: 0;
                padding: 0;
            }
            .dashboard-container {
                background-color: white;
                box-shadow: 0 0 15px rgba(0,0,0,0.1);
                border-radius: 8px;
            }
            .control-panel {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .play-button {
                transition: all 0.3s ease;
            }
            .play-button:hover {
                transform: scale(1.05);
            }
            /* Updated tooltip styles */
            .js-plotly-plot .plotly .hoverlayer {
                pointer-events: none !important;
            }
            .js-plotly-plot .plotly .hovertext {
                background-color: white !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 6px !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
                padding: 8px 12px !important;
                font-family: system-ui, -apple-system, sans-serif !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout remains the same
app.layout = dbc.Container([
    # Header Row
    dbc.Row([
        dbc.Col([
            html.H1('COVID-19 Deaths per Million People',
                   className='text-center text-primary mb-0 fw-bold',
                   style={'fontSize': '24px'}),
            html.P('Interactive visualization of cumulative COVID-19 deaths per million people globally',
                  className='text-center text-muted mb-3',
                  style={'fontSize': '14px'})
        ], width=12)
    ], className='mt-3'),
    
    # Controls Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                '▶ Play',
                                id='play-button',
                                color='primary',
                                className='play-button me-2',
                                style={'width': '100px'}
                            )
                        ], width=2),
                        dbc.Col([
                            dcc.Slider(
                                id='time-slider',
                                min=0,
                                max=len(DATES) - 1,
                                value=len(DATES) - 1,
                                marks={
                                    i: date.strftime('%Y-%m')
                                    for i, date in enumerate(DATES)
                                    if i % 60 == 0
                                },
                                updatemode='drag',
                                className='mt-2'
                            )
                        ], width=10)
                    ]),
                    dcc.Interval(
                        id='interval-component',
                        interval=100,
                        n_intervals=0,
                        disabled=True
                    )
                ])
            ], className='control-panel')
        ], width=12)
    ], className='mb-3'),
    
    # Map Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(
                        id='covid-map',
                        style={'height': 'calc(100vh - 250px)'},
                        config={
                            'displayModeBar': False,
                            'scrollZoom': True
                        }
                    )
                ], className='p-0')
            ], className='dashboard-container')
        ], width=12)
    ])
], fluid=True, className='vh-100 p-3')

# Callbacks for play/pause button and slider remain the same
@app.callback(
    [Output('interval-component', 'disabled'),
     Output('play-button', 'children')],
    [Input('play-button', 'n_clicks')],
    [State('interval-component', 'disabled')]
)
def toggle_animation(n_clicks, current_disabled):
    if n_clicks is None:
        return True, '▶ Play'
    return not current_disabled, '⏸ Pause' if current_disabled else '▶ Play'

@app.callback(
    Output('time-slider', 'value'),
    [Input('interval-component', 'n_intervals'),
     Input('time-slider', 'value')],
    [State('interval-component', 'disabled')]
)
def update_time_slider(n_intervals, slider_value, disabled):
    if disabled:
        return slider_value
    return (slider_value + 1) % len(DATES)

@app.callback(
    Output('covid-map', 'figure'),
    [Input('time-slider', 'value')]
)
def update_map(selected_index):
    selected_date = DATES[selected_index]
    date_data = PROCESSED_DATA[pd.Timestamp(selected_date)]
    
    fig = go.Figure(data=go.Choropleth(
        locations=date_data['iso_code'],
        z=date_data['total_deaths_per_million'],
        customdata=date_data[['location', 'total_deaths']],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>" +
            f"Date: {selected_date.strftime('%B %d, %Y')}<br>" +
            "Deaths per Million: %{z:,.1f}<br>" +
            "Total Deaths: %{customdata[1]:,.0f}" +
            "<extra></extra>"
        ),
        colorscale=[
            [0, '#ffffff'],
            [0.1, '#fee5d9'],
            [0.3, '#fcae91'],
            [0.5, '#fb6a4a'],
            [0.7, '#de2d26'],
            [1.0, '#a50f15']
        ],
        colorbar=dict(
            title=dict(
                text="Deaths per Million",
                font=dict(size=12)
            ),
            thickness=15,
            len=0.5,
            x=1.0,
            y=0.5,
            yanchor='middle',
            tickmode='array',
            ticktext=['No data', '0', '1000', '2000', '3000', '4000'],
            tickvals=[-1, 0, 1000, 2000, 3000, 4000],
            tickfont=dict(size=10)
        ),
        zmin=-1,
        zmax=4000
    ))
    
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular',
            showland=True,
            landcolor='white',
            showocean=True,
            oceancolor='#eef3f7',
            showcountries=True,
            countrycolor='#cccccc',
            center=dict(lon=0, lat=20),
            projection_scale=1.1
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='white',
        plot_bgcolor='white',
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="system-ui, -apple-system, sans-serif"
        ),
        # Enable smooth transitions
        transition_duration=300
    )
    
    return fig

if __name__ == '__main__':
    print("Starting dashboard server...")
    app.run_server(debug=True)