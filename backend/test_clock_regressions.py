"""Offline clock regressions: no model or DB calls."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, Mock
import query_generator as generator
from query_executor import filter_future_purchase_dates, convert_match_dates
from query_validator import validate_pipeline

class ClockTests(unittest.TestCase):
    def test_plain_latest_never_uses_model_cutoff(self):
        for suffix, expected in [('date', '$Purchase Date'), ('date, excluding future dates', '$Purchase Date'), ('year', {'$year': '$Purchase Date'})]:
            with self.subTest(suffix=suffix), patch.object(generator, 'llm') as model:
                pipeline = generator.generate_query('What is the most recent purchase ' + suffix + '?')['pipeline']
                model.invoke.assert_not_called()
                group = pipeline[0]['$group']
                self.assertEqual(next(v['$max'] for v in group.values() if isinstance(v, dict)), expected)
                for now in [datetime(2026,11,13,tzinfo=timezone.utc), datetime(2027,1,1,tzinfo=timezone.utc)]:
                    filtered = filter_future_purchase_dates(validate_pipeline(pipeline), now)
                    self.assertEqual(filtered[0]['$match']['Purchase Date']['$lte'], now)
                self.assertNotIn('2024-05-22', str(pipeline))

    def test_bounded_latest_preserves_user_filter(self):
        for question, bounds in [
            ('What is the most recent purchase date before 2024-05-22?', {'$lt': {'$date':'2024-05-22T00:00:00Z'}}),
            ('What is the most recent purchase date in 2020?', {'$gte':{'$date':'2020-01-01T00:00:00Z'}, '$lt':{'$date':'2021-01-01T00:00:00Z'}}),
            ('What is the most recent purchase year between 2020 and 2023?', {'$gte':{'$date':'2020-01-01T00:00:00Z'}, '$lt':{'$date':'2024-01-01T00:00:00Z'}}),
        ]:
            pipeline=[{'$match':{'Purchase Date':bounds}}, {'$group':{'_id':None,'latestDate':{'$max':'$Purchase Date'}}}]
            with self.subTest(question=question), patch.object(generator,'llm',Mock(invoke=Mock(return_value=Mock(text=json.dumps({'pipeline':pipeline}))))) as model:
                generated=generator.generate_query(question)['pipeline']
                self.assertEqual(generated,pipeline)
                if model.invoke.called:
                    prompt=model.invoke.call_args.args[0]
                    self.assertIn('Current system UTC time:',prompt)
                    self.assertIn(str(datetime.now(timezone.utc).date()),prompt)
                else:
                    # Explicit ISO bounds and whole years now have safe local plans.
                    self.assertNotIn('between', question)
                safe=validate_pipeline(generated)
                convert_match_dates(safe[0]['$match'])
                filtered=filter_future_purchase_dates(safe)
                self.assertEqual(filtered[1:],safe)

    def test_qualified_questions_not_overridden(self):
        for q in ['What is the most recent purchase date for Transportation?', 'What is the most recent fiscal purchase year?', 'What is the most recent purchase date last month?', 'What is the most recent purchase date after January 2020?']:
            self.assertIsNone(generator.simple_latest_query(q))

if __name__=='__main__': unittest.main()
