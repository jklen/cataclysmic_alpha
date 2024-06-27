# Import necessary packages
from dash import Dash, html, dcc
import dash_mantine_components as dmc
import pandas as pd

# Initialize the app
app = Dash(__name__)

# Sample DataFrame
data = pd.DataFrame({
    "Category": ["A", "B", "C"],
    "Value": [4, 3, 7]
})

# App layout
app.layout = dmc.MantineProvider(
    children=[
        dmc.Container(
            fluid=True,
            children=[
                # Sidebar
                dmc.Sidebar(
                    fixed=True,
                    width=200,
                    height="100vh",
                    padding="md",
                    children=[
                        dmc.Text("Sidebar Content"),
                        dmc.NavLink(label="Link 1", href="#"),
                        dmc.NavLink(label="Link 2", href="#"),
                        dmc.NavLink(label="Link 3", href="#"),
                    ],
                ),
                # Main content area
                dmc.Container(
                    fluid=True,
                    ml=220,  # Margin left to prevent overlap with sidebar
                    children=[
                        dmc.Title("Main Content", order=1),
                        dmc.Text("This is a simple Dash app using Mantine components."),
                        dcc.Graph(
                            figure={
                                'data': [
                                    {'x': data['Category'], 'y': data['Value'], 'type': 'bar', 'name': 'Value'},
                                ],
                                'layout': {
                                    'title': 'Sample Bar Chart'
                                }
                            }
                        )
                    ]
                )
            ]
        )
    ]
)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
