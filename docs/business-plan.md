# Fitness Evaluation App — Business Plan

> **Version:** 1.1  
> **Date:** 2026-02-19  
> **Phase:** POC Planning  
> **Status:** Draft — Pending Approval

---

## 1. Vision Statement

A SaaS platform that transforms raw fitness assessment data into scientifically-backed, actionable intelligence — giving coaches, gyms, and their clients a clear picture of physical status, progress over time, and personalized training direction.

The product is **not** a coaching platform. It is the **intelligence layer** that existing coaches and gyms plug into their workflow.

---

## 2. Problem Statement

| Who | Problem | Current Workaround |
|:---|:---|:---|
| **Independent coaches** | Conduct fitness assessments manually, interpret results from memory/experience, produce inconsistent reports | Spreadsheets, gut feeling, or generic templates |
| **Gym franchises** | No standardized assessment protocol across locations, can't prove member progress | Paper forms, no data continuity |
| **Clients/Members** | Receive vague feedback ("you're doing great"), no objective baseline, no visible progress | Trust the coach blindly or lose motivation |

**Core insight:** Assessment data exists, but interpretation is manual, inconsistent, and not scalable.

---

## 3. Target Market (Phased)

### Phase 1 — Independent & Boutique Coaches (B2B)
- Personal trainers, strength coaches, rehab-adjacent fitness pros
- Estimated market: ~300K+ in US alone
- Pain point: Want to look professional, differentiate from "bro science" trainers
- Willingness to pay: $20–50/month for tools that help retain clients

### Phase 2 — B2B2C (Coach buys, Client sees)
- Coach subscribes, client gets a branded portal/app to view their own results and progress
- This creates **stickiness** — the client expects the assessment experience as part of the service
- Coach churn drops because their clients are tied to the platform

### Phase 3 — White-label for Gyms & Franchises
- Gym chains license the platform under their own brand
- Standardized assessments across all locations
- Corporate wellness programs (annual fitness assessments for employees)
- Contract value: $500–5,000/month per location

---

## 4. Revenue Model

| Phase | Model | Pricing (Estimate) | Key Metric |
|:---|:---|:---|:---|
| 1 | SaaS subscription (per coach) | $29–49/month | MRR per coach |
| 2 | Tiered plans (# of active clients) | $49–149/month | Clients per coach |
| 3 | White-label licensing | $500–5,000/month per location | Locations onboarded |
| Future | API access (other apps integrate our engine) | Usage-based | API calls/month |

### Upsell Opportunities
- Premium report templates (branded, detailed)
- AI-generated workout plan suggestions (Phase 2+)
- Progress analytics dashboard
- Bulk assessment events (e.g., "Fitness Day" at a corporate office)

---

## 5. The Core Differentiator: Goal-Driven, Facility-Aware Assessments

This is the key innovation that separates us from every competitor.

### 5.1 Goal-Driven Test Selection

Assessments are **not one-size-fits-all**. The tests administered should be driven by the **trainee's stated goal**. A client who wants to lose weight needs different measurements than one training for strength or physique.

Sources: [Hevy Coach](https://hevycoach.com/personal-trainer-assessments/), [ISSA](https://www.issaonline.com/blog/post/how-to-do-fitness-assessments-for-online-clients-that-work), [Glofox](https://www.glofox.com/blog/personal-training-assessment/), [Educate Fitness](https://educatefitness.co.uk/fitness-assessments-for-clients-a-comprehensive-guide-to-evaluating-physical-fitness/)

#### Goal → Assessment Priority Matrix

| Trainee Goal | Primary Focus | Secondary Focus | Lower Priority |
|:---|:---|:---|:---|
| **Weight Loss** | Body Composition (BMI, WHR, BF%, circumferences), Cardio (VO2 estimate) | Muscular Endurance (calorie-burning capacity) | Max Strength, Flexibility |
| **Get Stronger** | Muscular Strength (1RM estimates, grip strength), Muscular Endurance (push-up, plank) | Core Stability, Flexibility (injury prevention) | Body Composition (unless weight class sport) |
| **Physique / Bodybuilding** | Body Composition (BF%, circumference measurements of arms, chest, legs), Muscular Endurance | Symmetry Assessment (left vs right, push vs pull), Flexibility | Cardio (unless cutting phase) |
| **General Fitness / Health** | All categories equally weighted | Blood Pressure, Resting HR, BMI | — |
| **Athletic Performance** | Cardio (VO2), Power (vertical jump), Agility, Muscular Strength | Flexibility, Balance | Body Composition (sport-dependent) |
| **Rehab / Return to Activity** | Flexibility, Balance, Functional Movement | Muscular Endurance (low load) | Max Strength, High-intensity Cardio |
| **Senior / Active Aging** | Balance, Flexibility, Functional Movement (chair stand, walk test) | Cardio (submaximal), Grip Strength | High-intensity tests |

**How the app uses this:**
1. Coach selects trainee's primary goal
2. App recommends a **prioritized test battery** (required + optional tests)
3. Coach can override/customize
4. Report and LLM analysis are **contextualized to the goal** (e.g., a "Below Average" cardio score is flagged as critical for a weight-loss client but informational for a strength client)

### 5.2 Facility-Aware Test Alternatives

Not every coach has a full gym. The app must offer **alternative tests** based on available equipment, so assessments are accessible everywhere — from a home gym to a fully equipped facility.

Sources: [TopEndSports Protocol Examples](https://www.topendsports.com/testing/protocol-examples.htm), [PMC - Reliability of Fitness Tests](https://pmc.ncbi.nlm.nih.gov/articles/PMC3418957/), [NSCA CPT Chapter 10](https://www.ptpioneer.com/personal-training/certifications/nsca-cpt/nsca-cpt-chapter-10/), [Trainer Academy](https://traineracademy.org/cpt-textbook/cardiorespiratory-fitness-assessments/)

#### Facility Tiers

| Tier | Description | Example Setting |
|:---|:---|:---|
| **Minimal** | No equipment beyond stopwatch, tape measure, wall | Home visits, outdoor, online coaching |
| **Basic** | Stopwatch, step/box, yoga mat, tape measure, ruler/yardstick | Small studio, home gym |
| **Standard** | Above + dumbbells, pull-up bar, scale, BP cuff | Personal training studio, small gym |
| **Full** | Above + treadmill, cycle ergometer, calipers, HR monitor | Commercial gym, fitness center |

#### Test Alternatives by Category & Facility

| Category | Sub-Category | Minimal Equipment | Basic Equipment | Standard Equipment | Full Equipment |
|:---|:---|:---|:---|:---|:---|
| **Strength** | Upper Body (Push) | Push-up Test | Push-up Test | Bench Press 1RM Estimate | Bench Press 1RM |
| | Upper Body (Pull) | — | Flexed Arm Hang | Pull-up Test | Lat Pulldown 1RM |
| | Lower Body | Bodyweight Squat Test | Wall Sit Test | Goblet Squat Reps | Leg Press 1RM |
| | Core | Plank Hold | Plank Hold, Crunch Test | Plank Hold, Crunch Test | Plank Hold, Crunch Test |
| | Grip | — | — | Handgrip Dynamometer | Handgrip Dynamometer |
| **Flexibility** | Hamstrings/Back | Toe Touch (qualitative) | Sit-and-Reach (yardstick + box) | Sit-and-Reach | Sit-and-Reach |
| | Shoulder | Zipper Test (hands behind back) | Zipper Test | Zipper Test | Goniometer measurement |
| | Hip | Thomas Test (qualitative) | Thomas Test | Thomas Test | Thomas Test |
| **Cardio** | Aerobic Fitness | 12-Min Cooper Walk/Run | YMCA 3-Min Step Test | YMCA 3-Min Step Test | Treadmill VO2 Max (submaximal) |
| | Recovery | — | — | Resting HR + Recovery HR | HR Monitor + Recovery Protocol |
| **Body Comp** | Weight/Height | BMI (scale + tape) | BMI | BMI | BMI |
| | Fat Distribution | Waist-to-Hip Ratio (tape) | Waist-to-Hip Ratio | Waist-to-Hip Ratio | Skinfold Calipers (3-site or 7-site) |
| | Circumferences | Tape measure (waist, hips) | Tape (waist, hips, arms, chest, thighs) | Full circumference protocol | Full + BIA or DEXA referral |
| **Health** | Blood Pressure | — | — | Manual BP Cuff | Digital BP Monitor |
| | Resting Heart Rate | Manual pulse (15s × 4) | Manual pulse | HR Monitor | HR Monitor |
| **Balance** | Static Balance | Single Leg Stand (eyes closed) | Single Leg Stand | Single Leg Stand | Balance Pad Test |
| | Dynamic Balance | — | — | Y-Balance Test | Y-Balance Test |

**How the app uses this:**
1. During onboarding, the coach selects their **facility tier** (or customizes available equipment)
2. The app filters available tests accordingly
3. When a test requires equipment the coach doesn't have, it automatically suggests the best alternative
4. Reports note which test variant was used, so longitudinal comparisons are valid only between identical test protocols

### 5.3 Comprehensive Body Mapping (Not Single Metrics)

A single test per category is insufficient. To truly understand a trainee's status, we need **multiple data points per category** that paint a complete picture.

#### Strength Sub-Categories
- **Upper Body Push** (chest, shoulders, triceps) → Push-up Test or Bench Press
- **Upper Body Pull** (back, biceps) → Pull-up / Flexed Arm Hang
- **Lower Body** (quads, glutes, hamstrings) → Wall Sit / Squat Test
- **Core** (abs, obliques, lower back) → Plank Hold / Crunch Test
- **Grip** → Handgrip Dynamometer (when available)

This reveals **imbalances** — e.g., strong push but weak pull = shoulder injury risk. The LLM can flag this pattern and explain why it matters.

#### Flexibility Sub-Categories
- **Posterior Chain** (hamstrings, lower back) → Sit-and-Reach
- **Shoulder Mobility** (rotator cuff, chest tightness) → Zipper Test
- **Hip Flexor** → Thomas Test

#### Body Composition Sub-Categories
- **Overall** → BMI
- **Distribution** → Waist-to-Hip Ratio
- **Regional** → Circumference measurements (arms, chest, waist, hips, thighs)

---

## 6. Competitive Landscape

| Competitor | What They Do | What They Lack |
|:---|:---|:---|
| **Trainerize** | Client management, workout delivery | No standardized assessment intelligence, no goal-driven test selection |
| **CoachRx (OPEX)** | Program design for elite coaches | Expensive, niche, no auto-interpretation, no facility-awareness |
| **Exercise.com** | All-in-one gym management | Assessment is a checkbox feature, not the core product |
| **FitBot / AI coaches** | AI-generated workout plans | No real assessment input, generic outputs |
| **Total PT Fitness** | Assessment software with normative data | No AI interpretation, no goal-driven selection, dated UI |
| **Manual (Excel/Sheets)** | Coach tracks data themselves | No percentile context, no progress viz, not scalable |

**Our differentiator: The "Brain"**
- Nobody else combines **goal-driven test selection + facility-aware alternatives + normative data lookup + percentile ranking + LLM-driven explanation + longitudinal tracking** in a single workflow
- We don't replace the coach — we make the coach look like they have a sports science team behind them

---

## 7. Product Workflow (Super-Coach Model)

```
┌─────────────────────────────────────────────────────────────┐
│                     COACH WORKFLOW                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Create Client Profile                                   │
│     → Name, Age, Gender, Goal, Health Notes                 │
│                                                             │
│  2. Select Assessment Context                               │
│     → Goal (Weight Loss / Strength / Physique / etc.)       │
│     → Facility Tier (Minimal / Basic / Standard / Full)     │
│                                                             │
│  3. App Recommends Test Battery                             │
│     → Required tests (based on goal + facility)             │
│     → Optional tests (nice-to-have)                         │
│     → Coach can add/remove tests                            │
│                                                             │
│  4. Input Raw Data                                          │
│     → Forms organized by category tabs                      │
│     → E.g., "Push-ups: [25]  Wall Sit: [45s]"              │
│                                                             │
│  5. Automatic Scoring (THE BRAIN)                           │
│     → Lookup normative tables by age, gender                │
│     → Calculate percentile / rating for each test           │
│     → Identify imbalances across categories                 │
│                                                             │
│  6. LLM Report Generation (invisible to end user)          │
│     → Generate explanation text contextualized to goal      │
│     → Suggest training priorities                           │
│     → Flag imbalances with reasoning                        │
│                                                             │
│  7. Coach Review & Edit                                     │
│     → Preview report, edit LLM text if needed               │
│     → Add personal notes                                    │
│                                                             │
│  8. Generate PDF Report                                     │
│     → Branded, professional, downloadable                   │
│     → Includes scores, ratings, explanations, next steps    │
│                                                             │
│  9. (Future) Track Over Time                                │
│     → Store assessment, compare to previous                 │
│     → Show progress charts                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|:---|:---|:---|
| **LLM hallucination** (bad health advice) | Legal liability, trust loss | LLM generates explanations only, never prescriptions. Coach reviews before client sees. Disclaimer on every report. |
| **Normative data accuracy** | Wrong percentile → wrong advice | Use only peer-reviewed / ACSM-sourced tables. Version and cite every data point in `norms.json`. |
| **Coaches won't pay** | No revenue | Validate with 5–10 coaches before building Phase 2. Free tier with limited assessments. |
| **"ChatGPT can do this"** | Perceived commodity | ChatGPT can't do percentile lookups, goal-driven test selection, facility-aware alternatives, progress tracking, or branded PDFs. Our value is the **integrated pipeline**. |
| **Scope creep** | Never ship | POC is ruthlessly scoped: defined test battery, one report type, one frontend. No workout plans, no client portal, no auth. |
| **Test protocol inconsistency** | Invalid longitudinal comparisons | Lock test variant per client; warn if protocol changes between assessments. |

---

## 9. Success Metrics

### POC Phase

| Metric | Target | How to Measure |
|:---|:---|:---|
| End-to-end demo working | Input → Scores → LLM Summary → PDF | Manual test |
| Time to generate a report | < 60 seconds | Stopwatch |
| Goal-driven test recommendation works | Correct battery suggested for 3+ goals | Manual verification |
| Facility-aware filtering works | Correct alternatives shown per tier | Manual verification |
| LLM output quality | Coach edits < 30% of generated text | Track edit rate |

### Phase 1 (Post-Launch)

| Metric | Target | How to Measure |
|:---|:---|:---|
| Paying coaches | 50 within 6 months | Stripe dashboard |
| Coach retention (monthly) | > 80% | Churn tracking |
| Reports generated per coach per month | > 5 | App analytics |
| Coach qualitative feedback | "I would recommend this" from 70%+ | NPS survey |

---

## 10. Long-term Vision (12–18 months)

1. **Progress Tracking Dashboard** — "Your client improved 23% in core strength over 3 months"
2. **AI Workout Suggestions** — Based on assessment gaps and trainee goal (weak core + weight loss goal → specific core + cardio program)
3. **Client-facing Portal** — Client logs in, sees their own results, shares with doctor
4. **Wearable Integration** — Pull resting HR from Apple Watch instead of manual entry
5. **Marketplace** — Coaches sell their branded assessment packages through the platform
6. **Corporate Wellness** — Bulk assessment events with automated reporting for HR departments
7. **Multi-language Support** — Expand beyond English-speaking markets
8. **API Platform** — Other fitness apps integrate our assessment engine

---

## 11. Open Questions

1. **Free tier** — Do we offer a free tier (e.g., 3 clients, limited tests) to drive adoption, or go paid-only from day one?
2. **Client data ownership** — When a coach leaves, does the client keep their data? Legal and product implications.
3. **Normative data licensing** — Some ACSM tables are behind paywalls. Need to verify which data we can use freely vs. need to license.
4. **International norms** — Normative data may vary by population. Do we need region-specific tables?

---

*End of Business Plan v1.1*