import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=json.loads((ROOT/'certification/FR0333_CONSTITUTIONAL_RAIL_0001.json').read_text())
class ConstitutionalRail0001(unittest.TestCase):
 def test_humanlock(self): self.assertEqual(R['humanlock'],'ACTIVE')
 def test_first_amendment_complete(self): self.assertEqual(R['amendments']['I']['functions'],['RELIGION','SPEECH','PRESS','ASSEMBLY','PETITION'])
 def test_first_through_fifth_present(self):
  for n in ['I','II','III','IV','V']: self.assertIn(n,R['amendments'])
 def test_fourteenth_router(self): self.assertIn('INCORPORATION',R['amendments']['XIV']['functions'])
 def test_press_controls(self):
  t=R['amendments']['I']['tests']
  for x in ['PRIOR_RESTRAINT','LICENSING','CONTENT_BASED_RESTRICTION','VIEWPOINT_DISCRIMINATION']: self.assertIn(x,t)
 def test_private_action_not_auto_constitutional(self): self.assertIn('DO_NOT_AUTOMATICALLY',R['decision_rule']['PRIVATE_ACTION'])
 def test_unknown_holds(self): self.assertEqual(R['decision_rule']['UNKNOWN'],'HOLD')
 def test_no_overclaim(self):
  self.assertIn('NO_FIRST_AMENDMENT_CERTIFIED_CLAIM',R['overclaim_guard'])
  self.assertIn('NO_AI_EQUALS_PRINTING_PRESS_AS_BINDING_PRECEDENT_CLAIM',R['overclaim_guard'])
if __name__=='__main__': unittest.main()
