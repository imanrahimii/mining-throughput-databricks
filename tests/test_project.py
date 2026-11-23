import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from notebooks.mining_core import COLUMNS,FEATURES,clean_shifts,machine_summary,temporal_split,fit_model
ROOT=Path(__file__).resolve().parents[1]

class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=pd.read_csv(ROOT/'data/mining_shifts_raw.csv',dtype=str,keep_default_na=False)
        cls.clean,cls.rejects,cls.counts=clean_shifts(cls.raw)
    def test_reconciliation(self):
        self.assertEqual(self.counts,{'raw':610,'exact_duplicates_removed':4,'rejected':6,'accepted':600})
        self.assertEqual(610,4+6+600)
    def test_expected_rejected_ids(self):
        self.assertEqual(set(self.rejects.shift_id),{f'BAD{i:02}' for i in range(1,7)})
    def test_clean_matches_reference(self):
        reference=pd.read_csv(ROOT/'solutions/reference_clean.csv')
        pd.testing.assert_frame_equal(self.clean.reset_index(drop=True),reference,check_dtype=False)
    def test_conflicting_duplicate_stops(self):
        changed=self.raw.iloc[[0]].copy();changed['actual_tonnes']='99999'
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            clean_shifts(pd.concat([self.raw,changed],ignore_index=True))
    def test_schema_mismatch_stops(self):
        with self.assertRaisesRegex(ValueError,'columns'):clean_shifts(self.raw.drop(columns='energy_kwh'))
    def test_whitespace_is_standardised(self):
        row=self.raw.iloc[[0]].copy();row['machine_id']='  M01  '
        clean,_,_=clean_shifts(row);self.assertEqual(clean.iloc[0].machine_id,'M01')
    def test_infinity_rejected(self):
        row=self.raw.iloc[[0]].copy();row['actual_tonnes']='inf'
        clean,rejects,_=clean_shifts(row);self.assertTrue(clean.empty);self.assertEqual(len(rejects),1)
    def test_boundary_availability(self):
        for value,accepted in [('0',1),('1',1),('-0.01',0),('1.01',0)]:
            row=self.raw.iloc[[0]].copy();row['prior_shift_availability']=value
            clean,_,_=clean_shifts(row);self.assertEqual(len(clean),accepted)
    def test_report_ratio_of_totals(self):
        tiny=pd.DataFrame({'machine_id':['A','A'],'shift_id':['a','b'],'actual_tonnes':[10.,90.],'energy_kwh':[100.,90.]})
        report=machine_summary(tiny).iloc[0]
        self.assertEqual(report.shifts,2);self.assertEqual(report.kwh_per_tonne,1.9)
    def test_machine_totals_reconcile(self):
        report=machine_summary(self.clean)
        self.assertEqual(len(report),20);self.assertTrue((report.shifts==30).all())
        self.assertAlmostEqual(report.total_tonnes.sum(),self.clean.actual_tonnes.sum(),places=2)
    def test_temporal_boundary_and_no_overlap(self):
        train,test=temporal_split(self.clean)
        self.assertEqual((len(train),len(test)),(400,200))
        self.assertLess(train.shift_date.max(),test.shift_date.min())
        self.assertFalse(set(train.shift_id)&set(test.shift_id))
    def test_no_same_shift_outcomes_in_features(self):
        self.assertNotIn('energy_kwh',FEATURES);self.assertNotIn('actual_tonnes',FEATURES)
        self.assertNotIn('shift_id',FEATURES)
    def test_fit_and_score_smoke(self):
        model,metrics,_,_,pred=fit_model(self.clean)
        self.assertEqual(len(pred),200);self.assertTrue(np.isfinite(pred).all())
        self.assertTrue(all(np.isfinite(v) for v in metrics.values()))
        self.assertLess(metrics['model_mae'],metrics['baseline_mae'])
        future=pd.read_csv(ROOT/'data/next_shifts.csv')
        self.assertEqual(len(model.predict(future[FEATURES])),10)

if __name__=='__main__':unittest.main()
