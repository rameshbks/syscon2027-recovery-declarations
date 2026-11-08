import unittest,numpy as np
from plant import *
class Physics(unittest.TestCase):
 def test_equilibrium(self):
  h1,h2,q=equilibrium()
  a,b=rhs(h1,h2,q)
  self.assertLess(abs(a)+abs(b),1e-12)
 def test_closed_total_mass(self):
  p=dict(PARAMS,k2=0.)
  h1,h2=.4,.2;initial=p['A1']*h1+p['A2']*h2
  for _ in range(1000):h1,h2=step(h1,h2,0.,.001,p)
  self.assertAlmostEqual(initial,p['A1']*h1+p['A2']*h2,places=10)
 def test_analytic_tank1_drain(self):
  p=PARAMS;h1,h2=.4,.2;t=1.
  for _ in range(1000):h1,h2=step(h1,h2,0.,.001,p)
  exact=(np.sqrt(.4)-p['k1']*t/(2*p['A1']))**2
  self.assertLess(abs(h1-exact),1e-9)
 def test_saturation_and_recovery(self):
  q,i=control(np.array([.5,.5]),np.array([100.,-100.]),np.zeros(2),.02)
  np.testing.assert_allclose(q,[PARAMS['qmax'],0.]);np.testing.assert_allclose(i,0.)
 def test_refinement(self):
  def run(dt):
   h1,h2,_=equilibrium()
   for _ in range(round(8/dt)):h1,h2=step(h1,h2,.028,dt)
   return np.array([h1,h2])
  self.assertLess(np.max(abs(run(.01)-run(.005))),1e-7)
 def test_disturbance_dynamic(self):
  h1,h2,q=equilibrium()
  for _ in range(1000):h1,h2=step(h1,h2,.03,.01)
  self.assertGreater(h2,.6)
if __name__=='__main__':unittest.main()
