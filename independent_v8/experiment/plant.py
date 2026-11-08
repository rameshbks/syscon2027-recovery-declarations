"""Standalone nonlinear two-tank plant. No imports from the Stage 4 plant."""
import numpy as np
PARAMS=dict(A1=.12,A2=.10,k1=.035,k2=.025,kp=.025,ki=.006,qmax=.04)
def equilibrium(p=PARAMS):
 h2=.5;h1=(p['k2']/p['k1'])**2*h2
 return h1,h2,p['k2']*np.sqrt(h2)
def rhs(h1,h2,q,p=PARAMS):
 f1=p['k1']*np.sqrt(np.maximum(h1,0))
 f2=p['k2']*np.sqrt(np.maximum(h2,0))
 return (q-f1)/p['A1'],(f1-f2)/p['A2']
def step(h1,h2,q,dt,p=PARAMS):
 a,b=rhs(h1,h2,q,p)
 c,d=rhs(h1+dt*a/2,h2+dt*b/2,q,p)
 e,f=rhs(h1+dt*c/2,h2+dt*d/2,q,p)
 g,h=rhs(h1+dt*e,h2+dt*f,q,p)
 return np.maximum(0,h1+dt*(a+2*c+2*e+g)/6),np.maximum(0,h2+dt*(b+2*d+2*f+h)/6)
def control(h2,target,integral,dt,p=PARAMS):
 ff=p['k2']*np.sqrt(.5)
 err=target-h2;raw=ff+p['kp']*err+p['ki']*integral
 q=np.clip(raw,0,p['qmax'])
 accept=((raw>=0)&(raw<=p['qmax']))|((raw>p['qmax'])&(err<0))|((raw<0)&(err>0))
 integral=integral+np.where(accept,err*dt,0)
 return q,integral
