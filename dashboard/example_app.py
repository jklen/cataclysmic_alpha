from dash import Dash, html, dcc
from dash.dash_table import DataTable
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
import plotly.express as px

df = px.data.iris()
fig = px.parallel_coordinates(
    df,
    color="species_id",
    labels={
        "species_id": "Species",
        "sepal_width": "Sepal Width",
        "sepal_length": "Sepal Length",
        "petal_width": "Petal Width",
        "petal_length": "Petal Length",
    },
    color_continuous_scale=px.colors.diverging.Tealrose,
    color_continuous_midpoint=2)

app = Dash(__name__)

app.layout = html.Div([
    my_graph := dcc.Graph(figure=fig), my_table :=
    DataTable(df.to_dict('records'), [{
        "name": i,
        "id": i
    } for i in df.columns],
              row_selectable='single')
])


@app.callback(Output(my_graph, 'figure'), 
              Input(my_table, 'selected_rows'),
              State(my_graph, 'figure'))
def pick(r, f):
    if r is None:
        raise PreventUpdate

    row = df[[
        "sepal_length", "sepal_width", "petal_length", "petal_width",
        "species_id"
    ]].loc[r[0]].to_list()

    for i, v in enumerate(f.get('data')[0].get('dimensions')):
        v.update({'constraintrange': [row[i] - row[i] / 100000, row[i]]})

    return f


if __name__ == "__main__":
    app.run_server(debug=True)