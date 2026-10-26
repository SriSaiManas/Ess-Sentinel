"""Portable reports and spreadsheet-safe CSV exports."""
from io import BytesIO
from html import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from ess.risk.engine import component_summary

NOTICE='Decision-support prototype. Synthetic results are not real-world qualification evidence. Final disposition requires qualified engineering review.'

def csv_bytes(d):
    out=d.copy()
    for c in out.select_dtypes(include=['object','string']).columns:
        out[c]=out[c].map(lambda v: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v)
    return out.to_csv(index=False).encode('utf-8-sig')

def pdf_report(results, title='ESS Screening Report'):
    buf=BytesIO(); styles=getSampleStyleSheet(); story=[]
    p=lambda text,style='BodyText':Paragraph(escape(str(text)),styles[style])
    story += [p(title,'Title'),Spacer(1,12),p(NOTICE),Spacer(1,12)]
    summary=component_summary(results)
    counts=summary.status.value_counts().to_dict()
    story.append(p(f'Unique components: {len(summary)} | Parameter records: {len(results)} | Status counts: {counts}'))
    story.append(p(f'Population anomalies: {int(results.population_anomaly.sum())}; predicted safety crossings: {int(results.predicted_crossing.sum())}'))
    if len(results):
        for key in ['model_version','timestamp','dataset_hash','policy_hash','stage']:
            story.append(p(f'{key}: {results.iloc[0][key]}'))
    story.append(Spacer(1,12))
    lots=results.groupby('lot_id').agg(records=('component_id','size'),flagged=('dynamic_flag','sum'),predicted_crossings=('predicted_crossing','sum')).reset_index()
    table=Table([list(lots.columns)]+lots.astype(str).values.tolist(),repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ef')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.3,colors.grey)]))
    story += [table,Spacer(1,12)]
    # Batch reports are summaries. A selected component report contains all parameter records.
    if len(summary)<=1:
        for index,(_,r) in enumerate(results.iterrows()):
            if index: story.append(PageBreak())
            story.append(p(f'{r.component_id} / {r.parameter} / {r.status}','Heading2'))
            fields=[c for c in results if c.startswith('value_')]+['unit','spec_min','spec_max','safety_threshold','predicted_168h','interval_lower','interval_upper','population_z','population_mad','population_percentile','if_score','absolute_drift','overall_slope','risk_score']
            for c in fields:
                v=r[c]
                if isinstance(v,(int,float)): v=f'{v:.5g}'
                story.append(p(f"{c.replace('_',' ').title()}: {v}"))
            story.append(p(r.explanation))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8)
        canvas.drawString(72,30,'ESS Sentinel | Engineering decision support')
        canvas.drawRightString(520,30,f'Page {doc.page}')
    SimpleDocTemplate(buf).build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
