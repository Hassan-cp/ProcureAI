import unittest
from datetime import datetime
from unittest.mock import patch
from fast_queries import common_query, aggregate_answer
from query_validator import validate_pipeline
from procurement_agent import ask_procurement

class SpeedTests(unittest.TestCase):
    def test_qualifiers_never_dropped(self):
        for q in ['How many purchases are in the database for Health?', 'How many purchases were made in 2020 excluding cancelled orders?', 'Who are the top 5 suppliers by total spending in 2020?', 'What is the total spending across all purchases before 2024-05-22?', 'Who are the top 101 suppliers by total spending?']:
            self.assertIsNone(common_query(q), q)
    def test_year_boundaries_and_readonly(self):
        for y in [1,2020,2026,9998]:
            q=common_query(f'How many purchases were made in {y:04d}?')
            validate_pipeline(q['pipeline'])
            bounds=q['pipeline'][0]['$match']['Purchase Date']
            self.assertEqual(bounds['$gte']['$date'],f'{y:04d}-01-01T00:00:00Z')
            self.assertEqual(bounds['$lt']['$date'],f'{y+1:04d}-01-01T00:00:00Z')
        self.assertIsNone(common_query('How many purchases were made in 9999?'))
    def test_common_questions_skip_both_model_calls(self):
        from query_generator import llm
        with patch('query_generator.llm') as query_model, patch('answer_generator.llm') as answer_model, patch('procurement_agent.execute_query',return_value=[{'count':346018}]) as execute:
            response=ask_procurement('How many purchases are in the database?')
            query_model.invoke.assert_not_called();answer_model.invoke.assert_not_called()
            self.assertIn('346,018',response['answer'])
            execute.assert_called_once_with([{'$count':'count'}])
    def test_render_from_expression_not_invented_alias(self):
        p=[{'$group':{'_id':None,'foo':{'$sum':'$Total Price'}}}]
        self.assertIn('$151,243,580,498.20',aggregate_answer(p,[{'_id':None,'foo':151243580498.2}]))
        self.assertIsNone(aggregate_answer(p+[{'$project':{'foo':1}}],[{'foo':10}]))
        p=[{'$group':{'_id':None,'d':{'$max':'$Purchase Date'}}}]
        self.assertIn('November 3, 2025',aggregate_answer(p,[{'_id':None,'d':datetime(2025,11,3)}]))
    def test_rank_and_untrusted_names(self):
        p=common_query('Who are the top 5 suppliers by total spending?')['pipeline']
        self.assertIn('\\[do this\\]',aggregate_answer(p,[{'_id':'[do this](url)','totalSpending':42}]))
        p[1]['$sort']={'totalSpending':1}
        self.assertIsNone(aggregate_answer(p,[{'_id':'supplier','totalSpending':42}]))
    def test_explicit_bounds_and_leap_dates(self):
        for phrase, expected in [
            ('before 2020', {'$lt': {'$date':'2020-01-01T00:00:00Z'}}),
            ('after 2020-02-29', {'$gte': {'$date':'2020-03-01T00:00:00Z'}}),
            ('on or before 2020-02-29', {'$lt': {'$date':'2020-03-01T00:00:00Z'}}),
            ('since 2020-02-29', {'$gte': {'$date':'2020-02-29T00:00:00Z'}}),
            ('in 2020', {'$gte':{'$date':'2020-01-01T00:00:00Z'}, '$lt':{'$date':'2021-01-01T00:00:00Z'}}),
        ]:
            p=common_query('What is the most recent purchase year '+phrase+'?')['pipeline']
            self.assertEqual(p[0]['$match']['Purchase Date'],expected)
            self.assertEqual(p[1]['$group']['latestYear'],{'$max':{'$year':'$Purchase Date'}})
            validate_pipeline(p)
        self.assertIsNone(common_query('What is the most recent purchase date before 2020-02-30?'))
        self.assertIsNone(common_query('What is the most recent purchase date before 2024-05-22 for Health?'))

    def test_unknown_shapes_fall_back(self):
        for p,r in [([{'$group':{'_id':None,'x':{'$avg':'$Quantity'}}}],[{'_id':None,'x':5}]), ([{'$count':'n'}],[{'wrong':3}])]:
            self.assertIsNone(aggregate_answer(p,r))

if __name__=='__main__': unittest.main()
