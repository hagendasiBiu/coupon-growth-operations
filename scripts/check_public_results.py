"""只依赖标准库，核对公开聚合结果；不读取用户明细。"""
from pathlib import Path
import csv
import json
import math

root = Path(__file__).resolve().parents[1]
tables = root/'reports/tables'
p = json.loads((tables/'final_policy_replay.json').read_text(encoding='utf-8'))
with (tables/'final_policy_allocation.csv').open(encoding='utf-8-sig', newline='') as f:
    allocation = list(csv.DictReader(f))
assert sum(int(r['candidate_users']) for r in allocation) == p['candidate_users'] == 76257
assert sum(int(r['selected_users']) for r in allocation) == p['capacity'] == 10000
assert sum(int(r['observed_redemptions']) for r in allocation) == p['policy_observed_redemptions'] == 1127
expected = p['capacity'] * p['population_first_coupon_redemptions'] / p['candidate_users']
assert math.isclose(expected, p['random_expected_redemptions'])
assert p['label_flip_selection_invariance'] == 'passed'
assert not p['causal_claim'] and not p['new_campaign_effect_identified']
with (tables/'final_budget_scenarios.csv').open(encoding='utf-8-sig', newline='') as f:
    scenarios = list(csv.DictReader(f))
assert len(scenarios) == 270
assert all(r['result_type'] == 'assumption_scenario_not_real_business_roi' for r in scenarios)
for name in ['final_policy_replay.png', 'final_roi_scenarios.png', 'lesson4_behavior_dashboard.png']:
    assert (root/'reports/figures'/name).is_file()
print('PASS: aggregate counts, random expectation, evidence labels and figures match.')
