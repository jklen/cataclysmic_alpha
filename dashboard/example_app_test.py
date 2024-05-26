# Import packages
from dash import Dash, html, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc

# Incorporate data
df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder2007.csv')

# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__, external_stylesheets=external_stylesheets)

# Sidebar layout
sidebar = html.Div(
    [
        dbc.Card(
            [
                html.H4("C alpha"),
                html.Hr(),
                dbc.Nav(
                    [
                        dbc.NavLink("Prompt 1", href="#", id="prompt-1-link"),
                        dbc.NavLink("Prompt 2", href="#", id="prompt-2-link"),
                        dbc.NavLink("Prompt 3", href="#", id="prompt-3-link"),
                    ],
                    vertical=True,
                    pills=True,
                ),
            ],
            body=True
        ),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "18rem",
        "padding": "2rem 1rem",
        "backgroundColor": "#f8f9fa",
    },
)

# Tabs layout
tabs = html.Div(
    [
        dbc.Tabs(
            id='tabs',
            children=[
                dbc.Tab(
                    label='Whole portfolio',
                    children=[
                        dbc.Row([html.Div('daily metrics', id='tab1_daily_metrics')]),
                        dbc.Row([
                            dbc.Col(
                                children=[
                                    dcc.Graph(figure={}, id='tab1_chart1_equity')
                                ],
                                width=9
                            ),
                            dbc.Col(
                                children=[
                                    html.Div('selected metrics', id='tab1_chart1_selected_metrics')
                                ],
                                width=3
                            ),
                        ]),
                        dbc.Row([
                            dbc.Col(
                                [
                                    dcc.Graph(figure={}, id='tab1_chart2_cum_metrics')
                                ],
                                width=6
                            ),
                            dbc.Col(
                                [
                                    dcc.Graph(figure={}, id='tab1_chart3_rolling_metrics')
                                ],
                                width=6
                            ),
                        ]),
                    ]
                ),
                dbc.Tab(
                    label='Subportfolios',
                    children=[
                        dbc.Row([html.Div(id='tab2_daily_metrics')]),
                    ]
                ),
                dbc.Tab(
                    label='Strategies',
                    children=[
                        dbc.Row([html.Div(id='tab3_strategies_high_level')]),
                    ]
                ),
                dbc.Tab(
                    label='Symbols',
                    children=[
                        dbc.Row([
                            dbc.Col(
                                children=[
                                    dcc.Graph(figure={}, id='tab4_chart1')
                                ]
                            ),
                            dbc.Col(
                                children=[
                                    dcc.Graph(figure={}, id='tab4_chart2')
                                ]
                            ),
                        ]),
                    ]
                ),
            ]
        ),
    ],
    style={
        "marginLeft": "20rem",  # Ensure enough margin to prevent overlap with sidebar
        "padding": "2rem 1rem",
    }
)

# App layout
app.layout = html.Div([sidebar, tabs])

# Add controls to build the interaction
@callback(
    Output(component_id='tab1_chart1_equity', component_property='figure'),
    Input(component_id='prompt-1-link', component_property='n_clicks')
)
def update_graph(n_clicks):
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate
    fig = px.histogram(df, x='continent', y='pop', histfunc='avg')
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
