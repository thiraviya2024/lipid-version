# lipid-ai/report/charts.py
"""
Interactive charts using Plotly for lipid values.
"""

import plotly.graph_objects as go
from typing import Dict

def create_lipid_charts(lipid_data: Dict) -> go.Figure:
    """Create bar chart with reference ranges."""
    params = []
    values = []
    colors = []
    
    for param, info in lipid_data.items():
        if param == "overall_risk":
            continue
        params.append(param.replace("_", " ").title())
        values.append(info["value"])
        
        status = info["status"].lower()
        if "high" in status or "very high" in status:
            colors.append("red")
        elif "borderline" in status or "moderate" in status:
            colors.append("orange")
        else:
            colors.append("green")

    fig = go.Figure(data=[
        go.Bar(
            x=params,
            y=values,
            marker_color=colors,
            text=values,
            textposition='auto'
        )
    ])

    fig.update_layout(
        title="Lipid Profile Analysis",
        xaxis_title="Parameter",
        yaxis_title="Value (mg/dL)",
        height=500,
        template="plotly_white"
    )
    
    return fig
