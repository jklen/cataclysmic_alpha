# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc

# Incorporate data
df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder2007.csv')

# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__, external_stylesheets=external_stylesheets)

sidebar = dbc.Container([
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
            )
        ], body = True
            )
],
    style={
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "18rem"
})

tabs = dbc.Container([
    dbc.Tabs(id = 'tabs',
                 children = [
                     dbc.Tab(label = 'Whole portfolio', children = [
                         dbc.Row([
                             html.Div('daily metrics', 
                                      id = 'tab1_daily_metrics')
                         ]),
                         dbc.Row([
                             dbc.Col(children = [
                                 dcc.Graph(figure = {},
                                           id = 'tab1_chart1_equity')
                             ], width = 9),
                             dbc.Col(children = [
                                 html.Div('selected metrics',
                                          id = 'tab1_chart1_selected_metrics')
                             ], width = 3)
                         ]),
                         dbc.Row([
                             dbc.Col([
                                 dcc.Graph(figure = {},
                                           id = 'tab1_chart2_cum_metrics')
                             ], width = 6),
                             dbc.Col([
                                 dcc.Graph(figure = {},
                                           id = 'tab1_chart3_rolling_metrics')
                             ], width = 6)
                         ])
                     ]),
                     dbc.Tab(label = 'Subportfolios', children = [
                         dbc.Row([
                             html.Div(id = 'tab2_daily_metrics')
                         ])
                     ]),
                     dbc.Tab(label = 'Strategies', children = [
                         dbc.Row([
                             html.Div(id = 'tab3_strategies_high_level')
                         ])
                     ]),
                     dbc.Tab(label = 'Symbols', children = [
                         dbc.Row([
                             dbc.Col(children = [
                                 dcc.Graph(figure = {},
                                           id = 'tab4_chart1')
                             ]),
                             dbc.Col(children = [
                                 dcc.Graph(figure = {},
                                           id = 'tab4_chart2')
                             ])
                         ])
                     ])
                 ])
    ])

# App layout
main_content = html.Div(children = [
        dbc.Row([
            dbc.Col([
                sidebar
            ], width = 2),
            dbc.Col([
                tabs
            ], width = 10)
        ]),
        

    ])

app.layout = main_content

# Add controls to build the interaction
@callback(
    Output(component_id='my-first-graph-final', component_property='figure'),
    Input(component_id='radio-buttons-final', component_property='value')
)
def update_graph(col_chosen):
    fig = px.histogram(df, x='continent', y=col_chosen, histfunc='avg')
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

# taby
#
# 1. whole portfolio
#   - current metrics ako singletons (equity, total_return, last daily return, SR, CR, SR...)
#   - line chart - equity v case
#      - ked selectnem periodu, uvidim dane metriky za danu periodu
#   - chart - kumulativne metriky v case
#   - chart - klzave metriky (1w, 1m, 3m - total_return, SR, absolute_return, nr ov trades, traded symbols, ,,,)
#   - tabulka so vsetkymyi metrikami ako v db
# 2. subportfolios
#   - barharty - current metrics v grafoch, grouped podla subportfolia
#   - line chart - equity v case, grouped podla subportfolia
#      - ked selectnem periodu, uvidim dane metriky za danu periodu pre vsetky subportfolia v barchartoch
#   - chart - kumulativna metrika v case podla subportfolioa, + filter na metriku
#   - chart - klzava metrika v case podla subportfolia - fitler na metriku
#   - chart - vaha symbolov v case + filter na subportfolio
#   - tabulka so vsetkymi metrikami ako v db + filter na subportfolio
#   - tabulka so subportfolio info - napr. sposob vazenia, symboly a pod
# 3. strategies
#   - singletons - pocet strategii, pocet long, pocet short, pocet longshort
#   - line chart - equity v case, grouped podla strategie
#      - select periody => metriky za danu periodu
#   - rovnako ako 1, 2
#   - histogramy daily returns strategii
#   - histogramy vynosov z tradov
# 4. symbols
#   - filter podla subportfolia a strategie a symbol
#   - line chart ceny vs. equity strategie na danom symbole
#      - zobrazene trady
#   - tabulka s tradami podla selekcie v charte
#   - line chart - vaha symbolu v case
#   - line chart equity z backtestu vs. nazivo
