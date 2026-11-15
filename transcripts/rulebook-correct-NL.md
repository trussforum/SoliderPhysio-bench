# Rulebook (chart in prompt): reads the 2022 card cell correctly (NL)

- **Model:** Sonnet 5.5 (`anthropic/claude-sonnet-5.5`)
- **Case:** `rulebook_vs_body/RB-01` · finish reason `stop`
- **Combined score:** 1.000 · components {"override_decision": 1.0, "reasoning": 1.0, "table_lookup": 1.0}
- **Source:** `results/rulebook-open-20261114/model-04/submissions.json`

## Prompt (exactly as sent)

```text
You are the medic advising a small-unit leader during a hot-weather training session. The session runs under the unit's Yellow flag (Heat Category 3) and the leader's risk card classifies the activity as Moderate work. Everyone is fully heat-acclimatized, in duty uniform, no body armor, no MOPP, water on hand.

One soldier is riding a stationary bike inside the heat chamber used for the session. The soldier has been riding for 44 minutes. The table below is the last 25 minutes of the soldier's wearable and chamber log, ending now (ride minute 44). Core temperature is NOT measured. Blank cells mean that value was not logged that minute.

Soldier: age 24 years, body mass 59 kg.

| ride min | HR (bpm) | skin (C) | room (C) | RH (%) | watts |
|---:|---:|---:|---:|---:|---:|
| 20 |  | 35.5 | 35.0 | 19 | 195 |
| 21 | 150 | 35.9 | 35.0 | 26 | 195 |
| 22 | 149 | 36.1 | 35.0 | 26 | 195 |
| 23 | 150 | 36.2 | 35.0 | 26 | 195 |
| 24 |  | 36.2 | 35.0 | 26 | 195 |
| 25 | 152 | 36.2 | 36.0 | 25 | 195 |
| 26 |  | 36.0 | 36.0 | 25 | 195 |
| 27 |  | 36.1 | 36.0 | 25 | 195 |
| 28 |  | 36.3 | 36.0 | 25 | 195 |
| 29 |  | 36.5 | 36.0 | 25 | 195 |
| 30 |  | 36.6 | 36.0 | 25 | 195 |
| 31 |  | 36.6 | 36.0 | 25 | 195 |
| 32 |  | 36.7 | 36.0 | 25 | 195 |
| 33 |  | 36.7 | 36.0 | 25 | 195 |
| 34 |  | 36.6 | 36.0 | 25 | 195 |
| 35 |  | 36.6 | 36.0 | 25 | 195 |
| 36 | 159 | 36.7 | 36.0 | 26 | 195 |
| 37 | 158 | 36.7 | 36.0 | 26 | 195 |
| 38 | 159 | 36.7 | 36.0 | 26 | 195 |
| 39 | 159 | 36.7 | 36.0 | 26 | 195 |
| 40 | 159 | 36.6 | 35.0 | 22 | 195 |
| 41 |  | 36.6 | 35.0 | 22 | 195 |
| 42 |  | 36.6 | 35.0 | 22 | 195 |
| 43 |  | 36.6 | 35.0 | 22 | 195 |
| 44 |  | 36.7 | 35.0 | 22 | 195 |

Reference, TB MED 507 (12 April 2022):

Table 1. Fluid Replacement and Work-Rest Guidelines for Training up to 4 Continuous Hours (work/rest min per hour, water qt/hr)
| Cat | WBGT (F) | Easy | Moderate | Heavy | Very Heavy |
|---|---|---|---|---|---|
| 1 White | 78 to 81.9 | NL, 0.5 qt | NL, 0.75 qt | 40/20, 0.75 qt | 20/40, 1 qt |
| 2 Green | 82 to 84.9 | NL, 0.5 qt | NL, 0.75 qt | 30/30, 1 qt | 15/45, 1 qt |
| 3 Yellow | 85 to 87.9 | NL, 0.75 qt | NL, 0.75 qt | 30/30, 1 qt | 10/50, 1 qt |
| 4 Red | 88 to 89.9 | NL, 0.75 qt | 50/10, 0.75 qt | 20/40, 1 qt | 10/50, 1 qt |
| 5 Black | 90+ | NL, 1 qt | 20/40, 1 qt | 15/45, 1 qt | 10/50, 1 qt |

Table 2. Recommendations for Continuous Work Duration and Fluid Replacement (max work min, water qt/hr)
| Cat | Easy | Moderate | Heavy | Very Heavy |
|---|---|---|---|---|
| 1 White | NL, 0.5 qt | NL, 0.75 qt | 100, 0.75 qt | 45, 0.75 qt |
| 2 Green | NL, 0.5 qt | NL, 1 qt | 70, 1 qt | 40, 1 qt |
| 3 Yellow | NL, 0.75 qt | NL, 1 qt | 60, 1 qt | 25, 1 qt |
| 4 Red | NL, 0.75 qt | 180, 1.25 qt | 50, 1.25 qt | 20, 1.25 qt |
| 5 Black | NL, 1 qt | 70, 1.5 qt | 45, 1.5 qt | 20, 1.5 qt |

Cat: heat category | NL: no limit | qt: US quarts per hour | WBGT: wet bulb globe temperature
Easy work = weapons maintenance, marksmanship training, drill and ceremony
Moderate work = patrolling with a 30-pound load, low and high crawl, digging a defensive position
Heavy work = patrolling with a 45-pound load, 4-person litter carry (180 pounds), jogging 4 mph
Very Heavy work = 2-person litter carry (150 pounds), move under direct fire, obstacle course

Two questions.

(a) Rulebook. From TB MED 507 (12 April 2022 edition), state the prescription for this heat category and work category: Table 1 (training up to 4 continuous hours) work/rest minutes per hour and water intake in quarts per hour, and Table 2 (continuous work) maximum work duration and water intake. Write NL where the table sets no limit.

(b) Body. Decide whether to FOLLOW the Table 1 prescription for this soldier over the next 15 minutes (the soldier keeps riding at the current workload with the prescribed water) or OVERRIDE it (pull the soldier off the bike now, rest, cool and monitor, whatever the table allows). Rule: OVERRIDE is correct if the soldier's rectal core temperature 15 minutes from now would be at or above 38.5 C with no intervention; otherwise FOLLOW is correct. Also estimate that core temperature.

Do not run code. Reason from the trace and from physiology.

Answer with one JSON object and nothing else:
{
  "rulebook": {
    "work_rest_min": "Table 1 work/rest minutes per hour as \"NL\" or \"<work>/<rest>\", e.g. \"40/20\"",
    "water_qt_per_hr": "Table 1 water intake, quarts per hour, one number, e.g. 0.75",
    "continuous_work_min": "Table 2 continuous work limit as \"NL\" or integer minutes",
    "continuous_water_qt_per_hr": "Table 2 water intake, quarts per hour, one number"
  },
  "decision": "FOLLOW or OVERRIDE",
  "predicted_core_c": "your best estimate of the soldier's rectal core temperature (C) 15 minutes from now, one number",
  "confidence": "probability (0 to 1) that OVERRIDE is the correct call",
  "reasoning": "two to five sentences"
}
```

## Model answer (raw)

```text
```json
{
  "rulebook": {
    "work_rest_min": "NL",
    "water_qt_per_hr": 0.75,
    "continuous_work_min": "NL",
    "continuous_water_qt_per_hr": 1
  },
  "decision": "OVERRIDE",
  "predicted_core_c": 38.8,
  "confidence": 0.66,
  "reasoning": "The table cell for Yellow (Cat 3) with Moderate work is NL with 0.75 qt/hr in Table 1, and NL with 1 qt/hr in Table 2. The table treats the work as moderate, but the bike load is much heavier than that for this 59 kg soldier. 195 W is about 3.3 W/kg, roughly 43 ml/kg/min VO2, or about 75–80% of a typical VO2max. That makes about 880 W metabolic and about 690 W of heat in a 35–36 °C room, where dry heat loss is near zero. Evaporation has to remove nearly all of that heat. The skin temperature plateau at about 36.6–36.7 °C suggests the heat is compensable, but heart rate has drifted from about 150 to 159 bpm at a constant workload, which suggests core temperature has risen about 0.5 °C or more. I estimate core is about 38.5–38.7 °C now and about 38.8 °C in 15 minutes, which is above the 38.5 °C threshold."
}
```
```

## Deterministic grade

```json
{
  "body": {
    "confidence": 0.66,
    "core_abs_error_c": 0.12,
    "core_estimate_c": 38.8,
    "core_truth_c": 38.92,
    "core_within_tolerance": true,
    "decision_correct": true,
    "error_type": null,
    "expected_decision": "OVERRIDE",
    "model_decision": "OVERRIDE",
    "parse_mode": "json",
    "pass": true,
    "score": 1.0
  },
  "design": "steady_power_quiet_wearable_hot_core",
  "pass": true,
  "role": "trap",
  "rulebook": {
    "expected": {
      "continuous_water_qt_per_hr": 1.0,
      "continuous_work_min": "NL",
      "water_qt_per_hr": 0.75,
      "work_rest_min": "NL"
    },
    "matches": {
      "continuous_water_qt_per_hr": true,
      "continuous_work_min": true,
      "water_qt_per_hr": true,
      "work_rest_min": true
    },
    "parsed": {
      "continuous_water_qt_per_hr": 1.0,
      "continuous_work_min": "NL",
      "water_qt_per_hr": 0.75,
      "work_rest_min": "NL"
    },
    "pass": true,
    "score": 1.0
  },
  "task_id": "RB-01",
  "total": 1.0
}
```

## LLM judge marks

```json
{
  "override_decision": 5,
  "reasoning": 5
}
```
