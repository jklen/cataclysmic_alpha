import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

sidebar = html.Div(
    [
        dbc.Card(
            [
                html.H4("C alpha"),
                html.Hr(),
                dbc.Nav(
                    [
                        dbc.NavLink("Whole Portfolio", href="/", id="whole_portfolio_link", active="exact"),
                        dbc.NavLink("Subportfolios", href="/subportfolios", id="subportfolios_link", active="exact"),
                        dbc.NavLink("Strategies", href="/strategies", id="strategies_link", active="exact"),
                        dbc.NavLink("Symbols", href="/symbols", id="symbols_link", active="exact"),
                        dbc.NavLink("Market", href="/market", id="market_link", active="exact")
                    ],
                    vertical=True,
                    pills=True,
                ),
            ],
            body=True
        ),
        html.Div(id='prompts')
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "18rem",
        "padding": "0.5rem 0.5rem",
        "backgroundColor": "#f8f9fa",
    },
)

content = html.Div(id="page-content")

app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    content
])

@app.callback(
    [Output(f"{link}_link", "active") for link in ["whole_portfolio", "subportfolios", "strategies", "symbols", "market"]],
    [Input("url", "pathname")]
)
def toggle_active_links(pathname):
    if pathname is None:
        pathname = "/"
    return [pathname == "/" if link == "whole_portfolio" else pathname == f"/{link}" for link in ["whole_portfolio", "subportfolios", "strategies", "symbols", "market"]]

@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/":
        return html.Div(children = [
            html.H2("Whole Portfolio Content")], style = {'marginLeft':'600px'})
    elif pathname == "/subportfolios":
        return html.Div(children = [
            html.H2("SUbportfolios Content")], style = {'marginLeft':'600px'})
    elif pathname == "/strategies":
        return html.Div(children = [
            html.H2("Strategies content")], style = {'marginLeft':'600px'})
    elif pathname == "/symbols":
        return html.Div(children = [
            html.H2("Symbols content")], style = {'marginLeft':'600px'})
    elif pathname == "/market":
        return html.Div(children = [
            html.H2("Market content")], style = {'marginLeft':'600px'})
    else:
        return html.H2("404 Page Not Found")

if __name__ == '__main__':
    app.run_server(debug=True)
