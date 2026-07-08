"""
E1-E3 v2: fixes two measurement confounds found in v1.

Confound 1: v1 accuracy is measured at the FINAL timestep only, which rewards
'recency-chasing' agents in a low-noise world (naive_absorb just tracks the last
few obs, and with low noise the last obs is usually right). The real objective is
STABLE, CALIBRATED belief under NOISE plus resistance to CORRUPTION -- so we now
report (a) time-averaged accuracy over the back half, (b) accuracy under an
adversarial corruption burst restricted to a subset of STABLE (non-flipping)
propositions, which is the actual catastrophic-forgetting analogue.

Confound 2: v1 membrane 'consumed' evidence on commit, starving it. Fixed: the
membrane now uses a sliding independent-lab quorum without destroying the buffer.

This is the honest iteration a research program requires: v1 gave a counterintuitive
result, we diagnosed WHY, and we re-ran under a metric that matches the real goal.
"""
import numpy as np
from dataclasses import dataclass, field
from scipy import stats

@dataclass
class World2:
    K: int = 60
    flip_frac: float = 0.25
    horizon: int = 4000
    noise: float = 0.30
    seed: int = 0
    corrupt_stable: bool = False      # adversarial burst on STABLE props
    corrupt_window: tuple = (2000, 2400)
    corrupt_noise: float = 0.9

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self.truth = self.rng.integers(0, 2, self.K).astype(int)
        self.flip_time = {}
        flippers = self.rng.choice(self.K, int(self.flip_frac*self.K), replace=False)
        self.flippers = set(flippers.tolist())
        for k in flippers:
            self.flip_time[k] = self.rng.integers(self.horizon//3, 2*self.horizon//3)
        # choose stable victims for corruption (never flip)
        stable = [k for k in range(self.K) if k not in self.flippers]
        self.victims = set(self.rng.choice(stable, max(1,len(stable)//3), replace=False).tolist())

    def truth_at(self,k,t):
        v=self.truth[k]
        if k in self.flip_time and t>=self.flip_time[k]: v=1-v
        return int(v)

    def stream(self):
        c0,c1=self.corrupt_window
        for t in range(self.horizon):
            k=self.rng.integers(self.K)
            true_v=self.truth_at(k,t)
            noise=self.noise
            if self.corrupt_stable and k in self.victims and c0<=t<c1:
                noise=self.corrupt_noise      # adversarial flood of wrong labels
            obs=true_v if self.rng.random()>noise else 1-true_v
            lab=self.rng.integers(4)
            yield t,k,int(obs),lab,(k in self.victims)

@dataclass
class Belief:
    logit: float=0.0; locked: bool=False

def acc_subset(b,w,t,subset=None):
    ok=[]
    for k,bb in b.items():
        if subset is not None and k not in subset: continue
        pred=1 if bb.logit>0 else 0
        ok.append(pred==w.truth_at(k,t))
    return float(np.mean(ok)) if ok else 0.0

# ---- agents (v2 membrane keeps a decaying multi-lab tally, non-destructive) ----
class Agent:
    def __init__(self,K,**kw):
        self.b={k:Belief() for k in range(K)}
    def commit(self,k,d,s=0.6):
        self.b[k].logit=float(np.clip(self.b[k].logit+s*d,-8,8))

class Naive(Agent):
    name="naive"
    def observe(self,t,k,obs,lab,budget):
        self.commit(k,1.0 if obs==1 else -1.0); return 0

class Membrane(Agent):
    name="membrane"
    def __init__(self,K,**kw):
        super().__init__(K); self.tally={k:np.zeros(4) for k in range(K)}; self.age={k:np.zeros(4) for k in range(K)}
    def observe(self,t,k,obs,lab,budget):
        self.tally[k]*=0.9
        self.tally[k][lab]=1.0 if obs==1 else -1.0
        active=np.abs(self.tally[k])>0.3
        if active.sum()>=2:
            m=self.tally[k][active].mean()
            if abs(m)>0.5:
                self.commit(k,np.sign(m),0.6)
        return 0

class Anchored(Membrane):
    name="anchored"
    def __init__(self,K,lock_at=4.0,resist=0.2,**kw):
        super().__init__(K); self.lock_at=lock_at; self.resist=resist
    def commit(self,k,d,s=0.6):
        if abs(self.b[k].logit)>=self.lock_at: self.b[k].locked=True
        f=self.resist if self.b[k].locked else 1.0
        self.b[k].logit=float(np.clip(self.b[k].logit+s*d*f,-8,8))

class AnchoredSurprise(Anchored):
    name="anchored_surprise"
    def observe(self,t,k,obs,lab,budget):
        p=1/(1+np.exp(-self.b[k].logit))
        surprise=abs((1 if obs==1 else 0)-p)
        super().observe(t,k,obs,lab,budget)
        if budget[0]>0 and surprise>0.6 and abs(self.b[k].logit)<6 and not self.b[k].locked:
            budget[0]-=1
            self.commit(k,1.0 if obs==1 else -1.0,0.9)
        return 0

def run(cls,wk,budget_per_1k=40,**akw):
    w=World2(**wk); a=cls(w.K,**akw); budget=[int(budget_per_1k*w.horizon/1000)]
    backhalf=[]; 
    for t,k,obs,lab,vic in w.stream():
        a.observe(t,k,obs,lab,budget)
        if t>w.horizon//2 and t%100==0:
            backhalf.append(acc_subset(a.b,w,t))
    stable=set(range(w.K))-w.flippers
    victim_acc=acc_subset(a.b,w,w.horizon-1,subset=w.victims)
    stable_acc=acc_subset(a.b,w,w.horizon-1,subset=stable)
    return float(np.mean(backhalf)), stable_acc, victim_acc

def ci(x):
    x=np.array(x); m=x.mean(); h=stats.t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x)); return m,h

def compare(agents,wk,n=40,budget=40,label=""):
    print(f"\n=== {label} | noise={wk.get('noise')} corrupt_stable={wk.get('corrupt_stable')} | {n} worlds ===")
    print(f"{'agent':<18}{'backhalf_acc':<20}{'stable_acc':<20}{'victim_acc(corrupted)':<22}")
    res={}
    for name,(cls,kw) in agents.items():
        bh,st,vi=[],[],[]
        for s in range(n):
            w=dict(wk); w['seed']=7000+s
            b,ss,vv=run(cls,w,budget,**kw); bh.append(b); st.append(ss); vi.append(vv)
        bm,bhh=ci(bh); sm,sh=ci(st); vm,vh=ci(vi)
        print(f"{name:<18}{bm:.3f}+/-{bhh:.3f}      {sm:.3f}+/-{sh:.3f}      {vm:.3f}+/-{vh:.3f}")
        res[name]=dict(backhalf=(bm,bhh),stable=(sm,sh),victim=(vm,vh))
    return res

if __name__=="__main__":
    A={"naive":(Naive,{}),"membrane":(Membrane,{}),"anchored":(Anchored,{}),
       "anchored_surprise":(AnchoredSurprise,{})}
    # clean high noise: does membrane give more STABLE, calibrated belief over time?
    r1=compare(A,dict(noise=0.35,corrupt_stable=False),label="E2v2 high-noise (time-avg)")
    # adversarial: burst of wrong labels on stable props -> corruption resistance
    r2=compare(A,dict(noise=0.30,corrupt_stable=True),label="E_ANCHORv2 corruption burst on stable beliefs")
    import json
    with open("results/memory_v2_results.json","w") as f:
        json.dump({"E2v2":r1,"E_anchor_v2":r2},f,indent=2)
    print("\nSaved -> results/memory_v2_results.json")
