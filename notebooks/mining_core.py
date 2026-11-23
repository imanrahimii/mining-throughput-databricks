"""Shared small-data logic used by the Databricks notebooks and CI."""
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

COLUMNS = ['shift_id','shift_date','machine_id','planned_hours','ore_hardness','feed_grade_pct','ambient_temp_c','prior_shift_availability','actual_tonnes','energy_kwh']
FEATURES = ['planned_hours','ore_hardness','feed_grade_pct','ambient_temp_c','prior_shift_availability']

def clean_shifts(raw):
    if set(raw.columns) != set(COLUMNS):
        raise ValueError("Unexpected file columns")
    raw=raw[COLUMNS].fillna("").astype(str).apply(lambda c:c.str.strip())
    unique=raw.drop_duplicates().copy()
    if unique.shift_id.duplicated().any():
        raise ValueError("Conflicting shift IDs")
    x=unique.copy()
    x['shift_date']=pd.to_datetime(x.shift_date,format='%Y-%m-%d',errors='coerce')
    numeric=COLUMNS[3:]
    for c in numeric:x[c]=pd.to_numeric(x[c],errors='coerce')
    valid=(x.shift_id.ne('') & x.machine_id.ne('') & x.shift_date.notna()
      & x[numeric].notna().all(axis=1) & np.isfinite(x[numeric]).all(axis=1)
      & x.planned_hours.between(0.01,24) & x.ore_hardness.between(0,10)
      & x.feed_grade_pct.between(0,100) & x.prior_shift_availability.between(0,1)
      & x.actual_tonnes.gt(0) & x.energy_kwh.ge(0))
    rejected=unique.loc[~valid].copy()
    rejected['reject_reason']='Required field, date, numeric or range validation failed'
    clean=x.loc[valid].copy()
    clean['shift_date']=clean.shift_date.dt.strftime('%Y-%m-%d')
    counts={'raw':len(raw),'exact_duplicates_removed':len(raw)-len(unique),'rejected':len(rejected),'accepted':len(clean)}
    return clean,rejected,counts

def machine_summary(clean):
    out=clean.groupby('machine_id',as_index=False).agg(shifts=('shift_id','size'),total_tonnes=('actual_tonnes','sum'),total_energy_kwh=('energy_kwh','sum'))
    if out.total_tonnes.le(0).any():raise ValueError('Non-positive tonnes')
    out['kwh_per_tonne']=out.total_energy_kwh/out.total_tonnes
    return out.round({'total_tonnes':2,'total_energy_kwh':2,'kwh_per_tonne':4})

def temporal_split(pdf, cutoff='2026-09-21'):
    dates=pd.to_datetime(pdf.shift_date,errors='raise')
    train=pdf.loc[dates < pd.Timestamp(cutoff)].copy()
    test=pdf.loc[dates >= pd.Timestamp(cutoff)].copy()
    if train.empty or test.empty:raise ValueError('Both time periods need records')
    return train,test

def fit_model(pdf):
    train,test=temporal_split(pdf)
    X_train,y_train=train[FEATURES],train.actual_tonnes
    X_test,y_test=test[FEATURES],test.actual_tonnes
    baseline=DummyRegressor(strategy='mean').fit(X_train,y_train)
    model=RandomForestRegressor(n_estimators=100,max_depth=8,min_samples_leaf=3,random_state=42,n_jobs=1).fit(X_train,y_train)
    pred=model.predict(X_test)
    metrics={'baseline_mae':float(mean_absolute_error(y_test,baseline.predict(X_test))), 'model_mae':float(mean_absolute_error(y_test,pred)), 'model_r2':float(r2_score(y_test,pred))}
    return model,metrics,train,test,pred
