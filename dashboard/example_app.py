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

# App layout
app.layout = dbc.Container([
    dbc.Row([
        html.Div('My First App with Data, Graph, and Controls', className="text-primary text-center fs-3")
    ]),

    dbc.Row([
        dbc.RadioItems(options=[{"label": x, "value": x} for x in ['pop', 'lifeExp', 'gdpPercap']],
                       value='lifeExp',
                       inline=True,
                       id='radio-buttons-final')
    ]),

    dbc.Row([
        dbc.Col([
            dash_table.DataTable(data=df.to_dict('records'), page_size=12, style_table={'overflowX': 'auto'})
        ], width=6),

        dbc.Col([
            dcc.Graph(figure={}, id='my-first-graph-final')
        ], width=6),
    ]),

], fluid=True)

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
