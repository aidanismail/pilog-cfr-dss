from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pilog_cfr_dss.application.market_case import new_market_case
from pilog_cfr_dss.application.tender_examples import generate_example, record_applied_example, input_digest
from pilog_cfr_dss.models.tender_clock import bid_in_round
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.orchestration.iteration_04 import evaluate

ROOT = Path(__file__).resolve().parents[2]


class RandomTenderExampleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.drafts, self.runs = Path(self.temp.name)/"drafts", Path(self.temp.name)/"runs"
        self.case = new_market_case(ROOT, latest_saved(ROOT))
        self.case.prepare(self.drafts); self.case.fix_freight(self.drafts)

    def apply(self, example, case=None):
        case = case or self.case
        case.apply_tender(example["bids"], example["evaluation_cutoff"])
        case.apply_scenarios(example["scenarios"])
        record_applied_example(case, example)
        return case

    def test_generation_reproducible_without_mutating_case_or_quote(self):
        original = self.case.fingerprint
        a,b = generate_example(self.case,0),generate_example(self.case,0)
        self.assertEqual(a["bids"],b["bids"])
        self.assertEqual(a["scenarios"],b["scenarios"])
        self.assertEqual(a["metadata"]["generated_input_sha256"],b["metadata"]["generated_input_sha256"])
        self.assertEqual(self.case.fingerprint,original)
        self.assertNotEqual(a["bids"],generate_example(self.case,1)["bids"])
        self.assertNotEqual(a["scenarios"],generate_example(self.case,1)["scenarios"])

    def test_seeded_input_population_can_pass_and_fail_floor_without_bad_data(self):
        quote,clock = deepcopy(self.case.context["freight_tender"]),deepcopy(self.case.context["auction_clock"])
        actions=set()
        for seed in range(16):
            case=deepcopy(self.case)
            example=generate_example(case,seed)
            self.assertEqual(len(example["bids"]),9)
            self.assertEqual({b["round"] for b in example["bids"]},{1,2,3})
            self.assertEqual(len({b["buyer_id"] for b in example["bids"]}),3)
            self.assertTrue(all(bid_in_round(b,clock) for b in example["bids"]))
            self.apply(example,case)
            report=case.evaluate(self.drafts,self.runs)
            actions.add(report["recommendation"]["action"])
            self.assertNotIn("DATA_ISSUE",report["recommendation"]["reason_codes"])
            self.assertEqual(case.context["freight_tender"],quote)
            self.assertEqual(case.context["auction_clock"],clock)
            self.assertTrue(all(D(b["fob_usd_mt"]) >= 0 for b in report["tender"]["bids"]))
        self.assertEqual(actions,{"GO","NO_GO"})

    def test_seed_metadata_saved_and_offline_replay_does_not_draw_random_values(self):
        self.apply(generate_example(self.case,1))
        record=self.case.context["tender_example"]
        self.assertFalse(record["edited_before_apply"])
        self.assertEqual(record["seed"],"1")
        self.assertEqual(record["applied_input_sha256"], input_digest(self.case.context["bids"],self.case.context["scenarios"]))
        result=self.case.evaluate(self.drafts,self.runs)
        with patch("pilog_cfr_dss.application.tender_examples.random.Random",side_effect=AssertionError("no RNG during evaluation")):
            replay=evaluate(self.case.run_dir/"input_snapshot/case_fixture.json")
        for key in ("baseline","tender","recommendation","scenarios"):
            self.assertEqual(result[key],replay[key])

    def test_edited_example_and_later_manual_change_do_not_claim_exact_seed_match(self):
        example=generate_example(self.case,0)
        self.case.apply_tender([{**b,"alpha_usd_mt":"99"} for b in example["bids"]],example["evaluation_cutoff"])
        self.case.apply_scenarios(example["scenarios"]); record_applied_example(self.case,example)
        self.assertTrue(self.case.context["tender_example"]["edited_before_apply"])
        bids=deepcopy(self.case.context["bids"]); bids[0]["alpha_usd_mt"]="98"
        self.case.apply_tender(bids,self.case.context["evaluation_cutoff"])
        self.assertNotIn("tender_example",self.case.context)
        self.apply(example)
        self.assertNotIn("tender_example",self.case.revise().context)
        self.case.apply_scenarios([{**x,"extra_port_days":"1"} for x in self.case.context["scenarios"]])
        self.assertNotIn("tender_example",self.case.context)

    def test_stress_loss_is_disclosed_without_changing_a_positive_baseline_decision(self):
        self.apply(generate_example(self.case,0))
        self.case.apply_scenarios([{"scenario_id":"severe","label":"Explicit 100 day stress",
                                   "fuel_price_increase_fraction":"0.45","extra_port_days":"100"}])
        result=self.case.evaluate(self.drafts,self.runs)
        self.assertEqual(result["recommendation"]["action"],"GO")
        stress=next(s for s in result["scenarios"] if s["scenario_id"]=="severe")
        self.assertLess(D(stress["economics"]["contribution_usd"]),0)
        self.assertIn("STRESS_LOSS_DISCLOSED_NOT_VETO",result["recommendation"]["reason_codes"])

    def test_synthetic_alpha_cannot_create_a_negative_fob_even_at_zero_floor(self):
        case=self.case.revise()
        case.apply_inputs({}, target_tce=case.context["pricing"]["target_tce"]["value"],
                          observations={p:{"low":"415.12345","high":"415.12345"} for p in ("argus","fertecon")},oe_hps="0")
        case.prepare(self.drafts); case.fix_freight(self.drafts)
        for seed in range(8):
            example=generate_example(case,seed)
            self.assertTrue(all(D("415.12345")+D(b["alpha_usd_mt"])>=0 for b in example["bids"]))

    def test_seed_and_unfixed_preconditions_rejected(self):
        for seed in (-1,2**64,True,"1"):
            with self.assertRaisesRegex(ValueError,"INVALID_EXAMPLE_SEED"): generate_example(self.case,seed)
        with self.assertRaisesRegex(ValueError,"FREIGHT_NOT_FIXED"):generate_example(self.case.revise(),0)
