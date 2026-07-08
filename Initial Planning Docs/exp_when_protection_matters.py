"""
E-DIAGNOSTIC: Under what conditions does self-protection actually beat naive
continuous update? v2 showed naive winning under STATIONARY, INDEPENDENT noise.
That's the wrong regime to conclude from. Real LLM belief corruption comes from
CORRELATED, ADVERSARIAL, PERSISTENT bad input (a wrong review article cited 200x;
a systematic methodological error repeated across a subfield; prompt-injection-like
poisoning). We now test that regime explicitly.

Key change: corruption is (1) CORRELATED (same wrong direction from MANY sources,
defeating naive quorum), (2) PERSISTENT (sustained, not a blip), and (3) the metric
rewards holding a HUMAN-CONFIRMED prior against the flood -- the real identity-
protection goal. We add a 'human_confirmed' signal that locks a few beliefs as
ground-truth anchors, and ask: after a sustained poisoning attack, whose beliefs
survive?
"""
import numpy as np
from dataclasses import dataclass
from scipy import stats

@dataclass
class PoisonWorld:
    K:int=60; horizon:int=4000; noise:float=0.25; seed:int=0
    poison:bool=True; poison_frac:float=0.2; poison_window:tuple=(1500,3000)
    poison_strength:float=0.85     # fraction of sources emitting the WRONG value
    human_confirm_frac:float=0.15  # beliefs the human has verified as ground truth
    def __post_init__(self):
        self.rng=np.random.default_rng(self.seed)
        self.truth=self.rng.integers(0,2,self.K)
        vic=self.rng.choice(self.K,int(self.poison_frac*self.K),replace=False)
        self.victims=set(vic.tolist())
        hc=self.rng.choice(list(self.victims), max(1,int(self.human_confirm_frac*self.K)) if self.victims else 0, replace=False) if self.victims else []
        # ensure some poisoned beliefs are ALSO human-confirmed (the crucial test)
        self.human=set(np.array(hc).tolist()) if len(hc) else set()
    def stream(self):
        p0,p1=self.poison_window
        for t in range(self.horizon):
            k=self.rng.integers(self.K); tv=int(self.truth[k])
            if self.poison and k in self.victims and p0<=t<p1:
                # correlated attack: with high prob emit WRONG, from ANY lab
                obs= (1-tv) if self.rng.random()<self.poison_strength else tv
            else:
                obs= tv if self.rng.random()>self.noise else 1-tv
            yield t,k,int(obs),self.rng.integers(8),(k in self.victims)

@dataclass
class B: 
    logit:float=0.0; locked:bool=False; human:bool=False

class Base:
    def __init__(self,K,world=None,**kw): self.b={k:B() for k in range(K)}
    def seed_human(self,world):
        # human-confirmed beliefs start locked at strong correct logit
        for k in world.human:
            self.b[k].logit=6.0 if world.truth[k]==1 else -6.0
            self.b[k].human=True

class Naive(Base):
    name="naive"
    def observe(self,t,k,o,lab,bud): self.b[k].logit=float(np.clip(self.b[k].logit+0.6*(1 if o else -1),-8,8))

class Quorum(Base):
    name="quorum"
    def __init__(self,K,world=None,**kw):
        super().__init__(K); self.t={k:np.zeros(8) for k in range(K)}
    def observe(self,t,k,o,lab,bud):
        self.t[k]*=0.9; self.t[k][lab]=1 if o else -1
        act=np.abs(self.t[k])>0.3
        if act.sum()>=3:
            m=self.t[k][act].mean()
            if abs(m)>0.5: self.b[k].logit=float(np.clip(self.b[k].logit+0.6*np.sign(m),-8,8))

class HumanAnchored(Quorum):
    """Human-confirmed beliefs require OVERWHELMING, SUSTAINED contrary evidence to
    move (high resist) -- models 'don't let the swarm overwrite what a human verified'."""
    name="human_anchored"
    def __init__(self,K,world=None,resist=0.05,**kw):
        super().__init__(K,world); self.resist=resist
    def observe(self,t,k,o,lab,bud):
        self.t[k]*=0.9; self.t[k][lab]=1 if o else -1
        act=np.abs(self.t[k])>0.3
        if act.sum()>=3:
            m=self.t[k][act].mean()
            if abs(m)>0.5:
                f=self.resist if self.b[k].human else 1.0
                self.b[k].logit=float(np.clip(self.b[k].logit+0.6*np.sign(m)*f,-8,8))

def acc(b,w,subset):
    ok=[1 if ((1 if b[k].logit>0 else 0)==int(w.truth[k])) else 0 for k in subset]
    return float(np.mean(ok)) if ok else 0.0

def run(cls,wk,**kw):
    w=PoisonWorld(**wk); a=cls(w.K,world=w,**kw); a.seed_human(w); bud=[0]
    # accuracy on human-confirmed-but-poisoned beliefs, measured DURING attack and AFTER
    during=[]; 
    for t,k,o,lab,vic in w.stream():
        a.observe(t,k,o,lab,bud)
        if 1500<=t<3000 and t%100==0: during.append(acc(a.b,w,w.human))
    after_human=acc(a.b,w,w.human)                       # did human-verified beliefs survive?
    after_victims=acc(a.b,w,w.victims)                   # all poisoned
    stable=set(range(w.K))-w.victims
    after_stable=acc(a.b,w,stable)
    return (np.mean(during) if during else np.nan), after_human, after_victims, after_stable

def ci(x):
    x=np.array([v for v in x if not np.isnan(v)]); 
    return (x.mean(), stats.t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else (np.nan,np.nan)

def compare(agents,wk,n=50,label=""):
    print(f"\n=== {label} | correlated poison strength={wk.get('poison_strength')} ===")
    print(f"{'agent':<16}{'human_acc_DURING':<20}{'human_acc_AFTER':<20}{'all_poisoned_AFTER':<20}{'stable_AFTER':<14}")
    for name,(cls,kw) in agents.items():
        d,h,v,s=[],[],[],[]
        for i in range(n):
            w=dict(wk); w['seed']=13000+i
            dd,hh,vv,ss=run(cls,w,**kw); d.append(dd);h.append(hh);v.append(vv);s.append(ss)
        dm,dh=ci(d);hm,hh=ci(h);vm,vh=ci(v);sm,sh=ci(s)
        print(f"{name:<16}{dm:.3f}+/-{dh:.3f}      {hm:.3f}+/-{hh:.3f}      {vm:.3f}+/-{vh:.3f}      {sm:.3f}+/-{sh:.3f}")

if __name__=="__main__":
    A={"naive":(Naive,{}),"quorum":(Quorum,{}),"human_anchored":(HumanAnchored,{})}
    compare(A,dict(poison_strength=0.85),label="CORRELATED SUSTAINED POISONING")
    compare(A,dict(poison_strength=0.65),label="milder correlated poisoning")
