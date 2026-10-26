"""Engineering visualizations with observed/predicted/peer evidence separated."""
import numpy as np
import plotly.graph_objects as go
from ess.anomaly.statistics import GROUP

COLORS={'NORMAL':'#16826c','WATCH':'#d5a229','HIGH RISK':'#db7731','CRITICAL':'#c7464b'}

def trajectory(d,r):
    peers=d
    for c in GROUP: peers=peers[peers[c]==r[c]]
    times=[t for t in [0,24,96,168] if f'value_{t}h' in d]
    cols=[f'value_{t}h' for t in times]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=times,y=peers[cols].quantile(.95),line=dict(width=0),name='Peer 95th percentile'))
    fig.add_trace(go.Scatter(x=times,y=peers[cols].quantile(.05),fill='tonexty',fillcolor='rgba(75,132,155,.16)',line=dict(width=0),name='Peer 5–95% range'))
    fig.add_trace(go.Scatter(x=times,y=peers[cols].median(),mode='lines',line=dict(color='#899da9',dash='dot'),name='Peer median'))
    observed=[t for t in times if t<=r.stage]
    future=[t for t in times if t>r.stage]
    fig.add_trace(go.Scatter(x=observed,y=[r[f'value_{t}h'] for t in observed],mode='lines+markers',line=dict(color='#087da0',width=3),name='Observed at screening cutoff'))
    if future: fig.add_trace(go.Scatter(x=future,y=[r[f'value_{t}h'] for t in future],mode='markers',marker=dict(color='#b5bcc3',symbol='circle-open'),name='Retrospective actual (not used)'))
    if np.isfinite(r.predicted_168h):
        fig.add_trace(go.Scatter(x=[168],y=[r.predicted_168h],mode='markers',marker=dict(color='#ca772c',size=13,symbol='diamond'),name='168h prediction'))
    fig.add_hline(y=r.spec_max,line_color='#c7464b',annotation_text='Specification maximum')
    fig.add_hline(y=r.spec_min,line_color='#c7464b',line_dash='dot',annotation_text='Specification minimum')
    fig.add_hline(y=r.safety_threshold,line_color='#d5a229',line_dash='dash',annotation_text='Upper safety threshold')
    fig.update_layout(xaxis_title='Burn-in duration (h)',yaxis_title=f'{r.parameter} ({r.unit})',height=450,legend=dict(orientation='h',y=-.25),margin=dict(t=35,b=80))
    return fig
