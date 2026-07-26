# Revision Plan: FlexINA (TNSM-2025-09156)

**Manuscript:** FlexINA: In-Network Aggregation for Accelerating Distributed Machine Learning with Flexible Routing  
**Journal:** IEEE Transactions on Network and Service Management (TNSM)  
**Decision:** Major Revision  
**Editor-in-Chief:** Dr. Abdallah Shami  
**Associate Editor:** Dr. Federica Paganelli  
**Submission Deadline:** 27-Feb-2026

---

## 1. Summary of Decision

The Associate Editor and reviewers recognize the timeliness and relevance of the work. However, major revisions are required in the following areas:

1. Articulation of novelty compared to recent works (GOAT, InArt).
2. Formal mathematical analysis of complexity reduction.
3. Practical guidelines for parameter tuning (ρ and τ).
4. Scalability evaluation on large-scale topologies (100+ switches).
5. Real-world implementation considerations (P4, packet loss, convergence).
6. Evaluation of impact on model convergence under non-IID data.

---

## 2. Point-by-Point Response to Reviewers

### 2.1 Response to Reviewer 1

#### Major Comments

- **R1.1 (Complexity Analysis is Superficial)**  
  **Action:** Added Theorems 1-3 with formal proofs in Section IV. Added new subsection IV-D: "Complexity Analysis" with full asymptotic bounds and Table III comparing complexity before/after each phase.
  - Theorem 1: Phase 1 reduces subsets from O(2^(W·F)) to O(2^(W₁·F/Mₛ)).
  - Theorem 2: Phase 2 reduces variables from O(S·2^W) to O(S/C · 2^(W/C)).
  - Theorem 3: Phase 3 reduces problem size from O(T·2^W) to O(τ_F·2^W) per iteration.

- **R1.2 (Manual Parameter Tuning: ρ and τ)**  
  **Action:** Added new subsection IV-E: "Practical Parameter Selection" with systematic methodology:
  - Formula for τ_F: `D + (F̂-1)·δ` (D = topology diameter, δ = aggregation latency).
  - Guideline: ρ ∈ [30%, 50%] as the "sweet spot".
  - Added discussion on auto-tuning via Bayesian optimization and online profiling.

- **R1.3 (Missing Baselines: GOAT, InArt)**  
  **Action:** Added GOAT and InArt as baselines. Updated Section II with detailed descriptions. Added Table IV comparing FlexINA vs. GOAT, InArt, DINA, and ATP. Added new results in Fig. 3a and Fig. 4a.

- **R1.4 (Impact on Model Convergence/Accuracy under Non-IID)**  
  **Action:** Added subsection V-B.7: "Impact on Model Convergence". Trained ResNet-18 on CIFAR-10 under IID, Dirichlet-0.5, and Dirichlet-0.1 distributions. Added Figure 10 showing loss curves and final accuracy. Discussed trade-offs between aggregation delay and overall training time.

#### Specific Questions

- **R1.Q1 (Novelty Delineation)**  
  **Action:** Added explicit "Novelty Statement" paragraph in Section I listing 4 key differentiators: (1) joint scheduling+routing optimization, (2) time-slotted model for fine-grained resource allocation, (3) systematic 3-phase complexity reduction, (4) source routing for full path flexibility.

- **R1.Q2 (Formal Theoretical Analysis)**  
  **Action:** Addressed via Theorems 1-3 and subsection IV-D.

- **R1.Q3 (Real-world Implementation: P4, state sync, latency)**  
  **Action:** Added new Section VI: "Implementation Considerations" covering P4 primitives (registers, match-action tables), centralized controller for state synchronization, and latency mapping (1 slot ≈ 100ns pipeline stage).

- **R1.Q4 (Convergence under Non-IID)**  
  **Action:** Addressed in R1.4.

- **R1.Q5 (Parameter Tuning Guidance / Auto-tuning)**  
  **Action:** Addressed via new subsection IV-E and Section V-C.6 discussing dynamic adaptation.

- **R1.Q6 (Scalability to Large Clusters: 1000 Workers)**  
  **Action:** Added subsection V-B.8: "Scalability Analysis". Extended simulations to 100 switches and 1000 workers (synthetic fat-tree). Showed runtime scales as O(F̂·τ_F·(S/C)·M·2^(W₁/C)). Added Figure 12.

#### Additional Minor Comments

- R1.2.1: Added hyperlinks to all DOIs; fixed citation styles.
- R1.2.2: Added total training time metric; discussed Age of Information (AoI).
- R1.2.3: Addressed in R1.Q1.
- R1.2.4: Punctuated all equations properly.
- R1.2.5: Regenerated all figures with larger fonts.
- R1.2.6: Tested on 3 architectures: Tofino-like, Broadcom-like, Generic ASIC.
- R1.2.7: Added AoI analysis (Figure 13).
- R1.2.8: Fixed all reference formatting (vol/issue/arXiv links).
- R1.2.9: Added the missed IoT Journal reference.

---

### 2.2 Response to Reviewer 2

- **R2.1 (Novelty Limited)** → Addressed in R1.Q1.  
- **R2.2 (ILP Complexity Analysis Not Rigorous)** → Addressed in R1.1.  
- **R2.3 (Small Topologies Only)** → Addressed in R1.Q6 (large-scale sims).  
- **R2.4 (Lack of Practical Implementation Discussion)** → Addressed via new Section VI.  
- **R2.5 (Unrealistic Zero-Error Assumption; No Congestion Handling)** → Added reliability discussion in Section VI covering TCP retransmission, priority queuing, XOR-based redundancy, and packet loss simulations (2%, 5%, 10%).

---

### 2.3 Response to Reviewer 3

- **R3.1 (Well-Structured, Comprehensive Sims)** → Thanked the reviewer.  
- **R3.2 (ILP Formulation Needs Clearer Explanation)** → Revised Section III.B with more explanatory text and a detailed walkthrough of constraints.  
- **R3.3 (Switch Memory Model Oversimplified)** → Refined the memory model in Section III.A describing register-based vs. stateful memory and hardware mapping.  
- **R3.4 (No Handling of Packet Loss/Retransmissions)** → Addressed in R2.5.

---

### 2.4 Response to Associate Editor

The Associate Editor summarized 5 key areas, all addressed as follows:

1. **Novelty articulation** → R1.Q1 + new comparison tables.
2. **Formal complexity analysis** → Theorems 1-3 + IV-D.
3. **Manual parameter tuning** → IV-E.
4. **Limited topology scale** → R1.Q6 (100-switch sims).
5. **System-level complexities** → New Section VI + convergence tests.

---

## 3. Complete Revision Checklist

**Legend:**
- `[ $ ]` = Requires editing the paper text.
- `[ # ]` = Requires code changes and re-running experiments.

---

### 3.1 Paper Text Edits (`$`)

#### Introduction (Section I)
- `[ $ ]` Add explicit "Novelty Statement" paragraph at the end listing 4 key differentiators.

#### Related Work (Section II)
- `[ $ ]` Expand descriptions of GOAT and InArt. ✓ Added comparison with InArt's single-path/single-aggregation assumption.
- `[ $ ]` Add **Table I**: Feature comparison (Scheduling, Routing, Aggregation Scope, Memory Mgmt) vs. ATP, DINA, GRID, GOAT, InArt.
- `[ $ ]` Add **Table IV**: Summary of key differences between FlexINA and SOTA.

#### Problem Formulation (Section III)
- `[ $ ]` Improve clarity of ILP constraints with a detailed walking example.
- `[ $ ]` Punctuate all equations correctly (add missing periods/commas).
- `[ $ ]` Refine memory model description (register vs. stateful, hardware mapping).

#### Proposed Solution (Section IV)
- `[ $ ]` Add **Theorem 1** (Phase 1 complexity proof) in IV-A.
- `[ $ ]` Add **Theorem 2** (Phase 2 complexity proof) in IV-B.
- `[ $ ]` Add **Theorem 3** (Phase 3 complexity proof) in IV-C.
- `[ $ ]` Add **Subsection IV-D**: "Complexity Analysis" (overall asymptotic bounds).
- `[ $ ]` Add **Subsection IV-E**: "Practical Parameter Selection" (formulas/guidelines).

#### Performance Evaluation (Section V)
- `[ $ ]` Add **Subsection V-B.7**: "Impact on Model Convergence" (ResNet-18/CIFAR-10, non-IID).
- `[ $ ]` Add **Subsection V-B.8**: "Scalability Analysis" (1000-worker cluster).
- `[ $ ]` Add references to new figures (Fig. 3a, 4a, 9, 10, 12, 13).
- `[ $ ]` Add **Section V-C.4**: Discussion on Age of Information (AoI).
- `[ $ ]` Add **Section V-C.6**: Discussion on auto-tuning / dynamic adaptation.
- `[ $ ]` Add **Section V-C.7**: Discussion on communication delay vs. convergence.

#### New Section VI: Implementation Considerations
- `[ $ ]` P4 mapping (registers, match-action tables).
- `[ $ ]` Controller integration (centralized coordination).
- `[ $ ]` State synchronization and consensus.
- `[ $ ]` Latency analysis (1 slot ≈ 100ns).
- `[ $ ]` Reliability: TCP retransmission, priority queuing, XOR redundancy.

#### Conclusion (Section VII)
- `[ $ ]` Acknowledge limitations (single PS, fixed timing assumptions).
- `[ $ ]` Mention future work: multi-PS, auto-tuning, uncertain delays.

#### References & Formatting
- `[ $ ]` Add missing reference: "Resource Allocation for Twin Maintenance and Task Processing in Vehicular Edge Computing Network".
- `[ $ ]` Fix formatting for references [43], [44], [45] (add vol/issue/pages).
- `[ $ ]` Add DOIs and hyperlinks to all references.
- `[ $ ]` Add arXiv access links where applicable.
- `[ $ ]` Enlarge font sizes in ALL figures.
- `[ $ ]` Fix inconsistent figure citations (remove "Fig. ??", cleanup "text[[...]]").

#### Tables
- `[ $ ]` Add **Table III**: Complexity comparison before/after each phase.
- `[ $ ]` Add **Table IV**: FlexINA vs. SOTA feature comparison.

---

### 3.2 Code Changes & Experiment Re-Runs (`#`)

#### Implement New Baselines
- `[ # ]` Implement **GOAT** (partitioned model aggregation + knapsack-based routing).
- `[ # ]` Implement **InArt** (multi-PS support + adaptive route selection).

#### Re-run Experiments for New Comparisons
- `[ # ]` Generate **Fig. 3a**: Packet count comparison on 3 topologies (incl. GOAT/InArt).
- `[ # ]` Generate **Fig. 4a**: Worker distribution impact (uniform, Zipf 1.5, Zipf 2) incl. GOAT/InArt.

#### Scalability Experiments
- `[ # ]` Simulate 100 switches, 1000 workers (synthetic fat-tree).
- `[ # ]` Measure ILP runtime scaling vs. number of workers/switches.
- `[ # ]` Generate **Fig. 12** (Runtime scaling).

#### Convergence Experiments (ML workload)
- `[ # ]` Train ResNet-18 on CIFAR-10 with IID, Dirichlet-0.5, Dirichlet-0.1 distributions.
- `[ # ]` Measure training loss, test accuracy, total training time.
- `[ # ]` Generate **Fig. 10** (Convergence curves).

#### Packet Loss Experiments
- `[ # ]` Simulate 2%, 5%, and 10% packet loss.
- `[ # ]` Measure degradation in packet reduction and runtime.

#### Switch Architecture Experiments
- `[ # ]` Model 3 architectures: Tofino (6-stage, 32-port), Broadcom (4-stage, 64-port), Generic (8-stage, 16-port).
- `[ # ]` Measure performance metrics across architectures.

#### Age of Information (AoI) Analysis
- `[ # ]` Calculate AoI (delay from worker to PS) for FlexINA vs. baselines.
- `[ # ]` Generate **Fig. 13** (AoI comparison).

#### Parameter Trade-off Data
- `[x]` Sweep ρ from 10% to 90%. *(block `param_sweep` in main.py — 2-D heatmap, ρ × τ_F)*
- `[x]` Sweep τ_F (window size) from 6 to 12. *(same block `param_sweep` heatmap)*
- `[x]` Generate the trade-off scatter (Packet reduction vs. Runtime). *(block `param_sweep` in main.py; saves `plots/param_sweep_tradeoff_data.json`)*

#### Online Adaptive (ρ, τ_F) Model
- `[x]` Online external model (k-NN vs linear SGD) that picks (ρ, τ_F) per step from observable state and updates after each solve. *(block `online_model` in main.py; module `sim/online_model.py`)*
  - State features (realistically observable at dispatch time): `num_switches, num_workers, num_clusters, num_active_frags, avg_steps_to_switch, iteration_index, T_max_2_current`.
  - Reward = runtime (s); controller picks argmin predicted runtime with ε-greedy exploration (ε decays).
  - Fair online comparison plots: learning curve, action trace, runtime trace, JSON log.

---

## 4. Understanding GOAT and InArt (For Baseline Implementation)

### 4.1 GOAT
- **Key Challenge:** Handles asynchronous gradient arrivals.
- **Method:** Partitions model into sub-models. Uses a knapsack-based randomized rounding algorithm to decide which switch aggregates which sub-model.
- **Result:** Up to 1.5× faster training.
- **Implementation Insight:** Dynamic assignment of model partitions to switches based on expected traffic patterns.

### 4.2 InArt
- **Key Challenge:** Single Parameter Server bandwidth bottleneck.
- **Method:** Two-phase approach: (1) Partition model across multiple PSs; (2) Dynamically select optimal routes for aggregation.
- **Result:** Reduces communication time by 48%–57%.
- **Implementation Insight:** Multi-PS support and dynamic route selection logic based on switch resource availability.

---

## 5. Summary of Major Changes in Revised Manuscript

1. **Theoretical Foundation**
   - 3 new formal theorems with proofs.
   - New subsections IV-D (Complexity Analysis) and IV-E (Parameter Selection).

2. **Experimental Validation**
   - Added 2 new baselines (GOAT, InArt).
   - Added convergence analysis (ResNet-18/CIFAR-10, non-IID).
   - Added 1000-worker scalability analysis.
   - Added packet loss, AoI, and multi-architecture tests.

3. **Practical Roadmap**
   - New Section VI (Implementation & Challenges).
   - Practical parameter tuning guidelines.
   - Auto-tuning and adaptation discussion.

4. **Clarity and Positioning**
   - Explicit novelty statement.
   - Enhanced related work with detailed comparisons (Tables I, IV).
   - Cleaned up all references, formatting, and figure quality.

---

**END OF REVISION PLAN**