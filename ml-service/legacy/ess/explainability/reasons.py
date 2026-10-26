"""Human-readable rule explanations for every screened record."""

def explain_row(r):
    reasons=[]
    if r.static_violation: reasons.append('Observed specification violation: engineering review required.')
    if r.population_anomaly: reasons.append(f'Population anomaly: robust Z={r.population_z:.2f}; peer median={r.population_median:.3g} {r.unit}, MAD={r.population_mad:.3g}.')
    if r.temporal_anomaly: reasons.append(f'Abnormal drift: peer-relative drift Z={r.temporal_z:.2f}; observed change={r.absolute_drift:.3g} {r.unit}.')
    if r.predicted_crossing: reasons.append(f'Predicted safety crossing: 168h estimate={r.predicted_168h:.3g} {r.unit}; upper safety threshold={r.safety_threshold:.3g}; margin={r.predicted_margin:.3g}.')
    if r.ml_anomaly: reasons.append(f'Isolation Forest score is at training-reference percentile {r.if_percentile:.1f}; this is not a failure probability.')
    if not r.peer_sufficient: reasons.append(f'Only {int(r.peer_count)} comparable peers; population evidence withheld.')
    if r.prediction_note: reasons.append(str(r.prediction_note))
    if r.incomplete_assessment: reasons.append('Incomplete or unsupported assessment; do not interpret as a pass.')
    if not reasons: reasons.append('No configured screening rule triggered; this does not establish absence of latent defects.')
    return ' '.join(reasons)
