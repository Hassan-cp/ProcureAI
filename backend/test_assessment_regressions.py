import unittest
from unittest.mock import patch
from fast_queries import common_query, aggregate_answer
from query_validator import validate_pipeline
from procurement_agent import ask_procurement

class AssessmentTests(unittest.TestCase):
 def test_quarter_semantics(self):
  for suffix,year in [('',True),(' in 2024',True),(' aggregated across years',False),(' across all years',False)]:
   p=common_query('Which quarter had the highest total spending'+suffix+'?')['pipeline'];validate_pipeline(p)
   self.assertEqual('year' in p[1]['$group']['_id'],year)
   if suffix==' in 2024':self.assertIn('2024',str(p[0]))
 def test_no_dropped_qualifiers(self):
  for q in ['Which quarter had the highest total spending for Health?', 'What is the total spending in fiscal year 2024?', 'most frequently ordered line items in 2020', 'Which fiscal quarter had the highest total spending?']:
   self.assertIsNone(common_query(q))
 def test_operator_security(self):
  for e in [{'$ceil':[]},{'$ceil':[1,2]},{'$quarter':'$Purchase Date'},{'$ceil':{'$function':{}}},{'$ceil':'$$NOW'}]:
   with self.assertRaises(ValueError):validate_pipeline([{'$project':{'q':e}}])
  for field,value in [('Item Name','date'),('Purchase Date','object'),('Purchase Date',{'$ne':'date'})]:
   with self.assertRaises(ValueError):validate_pipeline([{'$match':{field:{'$type':value}}}])
 def test_answers_do_not_need_model(self):
  for q,result,expected in [('Which quarter had the highest total spending?',[{'_id':{'year':2004,'quarter':3.0},'totalSpending':13619535015.7}],'2004 Q3:'),('most frequently ordered line items',[{'_id':'Medical Supplies','orderCount':2916}],'2,916')]:
   with patch('procurement_agent.execute_query',return_value=result),patch('query_generator.llm') as qm,patch('answer_generator.llm') as am:
    r=ask_procurement(q);self.assertIn(expected,r['answer']);qm.invoke.assert_not_called();am.invoke.assert_not_called()
 def test_purchase_year_not_fiscal(self):
  p=common_query('What is the total spending in 2024?')['pipeline'];validate_pipeline(p)
  self.assertNotIn('Fiscal Year',str(p));self.assertIn('2025-01-01',str(p))
  self.assertIn('Purchase Date',aggregate_answer(p,[{'_id':None,'totalSpending':59129}]))
 def test_ties_and_missing_names(self):
  p=common_query('most frequently ordered line items')['pipeline'];self.assertEqual(p[0]['$match']['Item Name'],{'$nin':[None,'']});self.assertEqual(p[2]['$sort'],{'orderCount':-1,'_id':1})
if __name__=='__main__':unittest.main()
