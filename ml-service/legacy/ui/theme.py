"""Central design tokens. Styling uses our own HTML classes and the public theme."""
from html import escape
import streamlit as st
import plotly.io as pio
from pathlib import Path

COLORS={'NORMAL':'#37C991','WATCH':'#F5B84B','HIGH RISK':'#EE9754','CRITICAL':'#F16C76'}
CSS='''<style>
.ess-wordmark{font:700 22px/1.2 system-ui,sans-serif;letter-spacing:1.2px;color:#f1f5fb;margin:4px 0 0}
.ess-wordmark span{color:#36d6c5}.ess-tag{font:10px system-ui,sans-serif;letter-spacing:2px;color:#96a6bc;margin:6px 0 24px}
.ess-breadcrumb{color:#96a6bc;text-transform:uppercase;letter-spacing:1.7px;font-size:11px;margin-bottom:9px}
.ess-title{font-size:30px;letter-spacing:-1px;font-weight:650;margin:0 0 7px;color:#f1f5fb}
.ess-subtitle{font-size:14px;color:#96a6bc;margin:0 0 24px}
.ess-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:12px 0 22px}
.ess-kpi{background:#111c2e;border:1px solid #23324a;border-radius:11px;padding:19px 20px;min-height:117px;box-sizing:border-box}
.ess-kpi-label{font-size:11px;letter-spacing:1px;color:#96a6bc;text-transform:uppercase}
.ess-kpi-value{font-size:31px;font-weight:650;line-height:1.5;font-variant-numeric:tabular-nums;letter-spacing:-1px}
.ess-kpi-note{font-size:11px;color:#96a6bc}.ess-batch{background:#0d1422;border-left:3px solid #36d6c5;padding:17px 20px;border-radius:6px;font-size:13px;line-height:1.8;margin-bottom:18px}
.ess-pill{display:inline-block;border:1px solid #23324a;border-radius:20px;padding:3px 9px;font:10px ui-monospace,monospace;color:#36d6c5;letter-spacing:1px}
.ess-nav-label{font-size:10px;color:#96a6bc;letter-spacing:1.8px;margin:20px 0 7px}
.ess-status{font-size:11px;color:#96a6bc;border-top:1px solid #23324a;padding-top:15px;margin-top:18px;line-height:1.9}
.ess-finding{border-left:2px solid #f5b84b;padding:5px 0 5px 13px;margin:8px 0;color:#c7d2e4;font-size:13px}
@media(min-width:1700px){.ess-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}
@media(max-width:800px){.ess-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.ess-title{font-size:26px}}
@media(max-width:480px){.ess-grid{grid-template-columns:1fr}}
@media(prefers-reduced-motion:no-preference){.ess-kpi{transition:border-color .15s}.ess-kpi:hover{border-color:#397d84}}
</style>'''

def apply():
    st.html(CSS)
    pio.templates.default='plotly_dark'

def title(name,subtitle,group):
    st.html(f'<div class="ess-breadcrumb">{escape(group)} / LOCAL WORKSPACE <span class="ess-pill">LOCAL</span></div><h1 class="ess-title">{escape(name)}</h1><p class="ess-subtitle">{escape(subtitle)}</p>')

def kpis(items):
    cards=[]
    for label,value,note,color in items:
        cards.append(f'<div class="ess-kpi" title="{escape(note,quote=True)}"><div class="ess-kpi-label">{escape(label)}</div><div class="ess-kpi-value" style="color:{color}">{escape(str(value))}</div><div class="ess-kpi-note">{escape(note)}</div></div>')
    st.html('<div class="ess-grid">'+''.join(cards)+'</div>')

def chart(fig,key=None):
    fig.update_layout(paper_bgcolor='#111C2E',plot_bgcolor='#111C2E',font=dict(color='#c9d6e7',size=12),margin=dict(l=35,r=25,t=40,b=40),colorway=['#36D6C5','#57A6FF','#F5B84B','#F16C76'],legend=dict(orientation='h',y=-.23),height=350)
    fig.update_xaxes(gridcolor='#23324A',zerolinecolor='#23324A');fig.update_yaxes(gridcolor='#23324A',zerolinecolor='#23324A')
    st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False})
