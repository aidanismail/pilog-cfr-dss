import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pilog_cfr_dss.application.market_case import new_market_case, active_catalog, apply_profile, apply_route
from pilog_cfr_dss.application.case_package import export_case, import_case
from pilog_cfr_dss.sources.fearnpulse import latest_saved, save_runtime_snapshot

ROOT = Path(__file__).resolve().parents[2]


def workspace():
    case = new_market_case(ROOT, latest_saved(ROOT), dynamic_route=True)
    profiles = active_catalog(ROOT)
    apply_profile(case, profiles['profiles'][0], profiles['policy'])
    apply_route(case, ('Bontang', 'Indonesia'), ('Muara', 'Brunei'), {
        'value': '820', 'unit': 'NM', 'loading_port': 'Bontang', 'discharging_port': 'Muara',
        'source_status': 'simulation_only_user_input', 'source_reference': 'Test fixture'})
    return case


class WorkspaceHardening(unittest.TestCase):
    def test_argus_regional_references_keep_fob_separate_from_cfr(self):
        from pilog_cfr_dss.sources.market_comparables import read_argus_comparables, read_comparables, voyage_matches
        argus = read_argus_comparables(ROOT)
        self.assertEqual((argus['cfr']['India']['low'], argus['cfr']['India']['high']), ('390.00', '394.00'))
        self.assertNotIn('Libya', argus['cfr'])
        self.assertEqual((argus['regional_fob']['Libya']['basis'], argus['regional_fob']['Libya']['low'], argus['regional_fob']['Libya']['high']), ('FOB', '430', '515'))
        matches = voyage_matches(read_comparables(ROOT)['voyages'], 'Bontang', 'Mersa Al Brega')
        self.assertTrue(matches)
        self.assertTrue(all(item['match_scope'] == 'tujuan_kawasan_asal_berbeda' for item in matches))
        self.assertTrue(all(item['origin'] != 'Bontang' for item in matches))

    def test_all_port_pairs_have_labelled_context_when_reports_available(self):
        from pilog_cfr_dss.sources.market_comparables import read_argus_comparables, read_comparables, voyage_matches
        from pilog_cfr_dss.sources.route_distance import ports
        argus, fertecon = read_argus_comparables(ROOT), read_comparables(ROOT)
        self.assertEqual(argus['global_fob']['basis'], 'FOB')
        self.assertEqual(fertecon['global_fob']['basis'], 'FOB')
        locations = ports(ROOT / 'data/raw/Ports.xlsx')
        for origin, _ in locations:
            for destination, country in locations:
                if origin == destination:
                    continue
                with self.subTest(origin=origin, destination=destination):
                    price_context = (country in argus['cfr'] or destination in argus['cfr_ports'] or
                                     country in fertecon['cfr'] or country in argus['regional_fob'] or
                                     argus['global_fob'] or fertecon['global_fob'])
                    self.assertTrue(price_context)
                    self.assertTrue(voyage_matches(fertecon['voyages'], origin, destination))

    def test_active_constructor_never_reads_od(self):
        with patch('pilog_cfr_dss.application.market_case.read_distance', side_effect=AssertionError('OD read')), patch('pilog_cfr_dss.sources.voyage_estimates.read_distance', side_effect=AssertionError('OD read')):
            case = workspace()
        self.assertEqual(case.context['capacity_basis'], 'dataset_allowances_v1')

    def test_allowances_prevent_loading_full_gross_dwt(self):
        case = workspace()
        for row in case.rows:
            if row['key'] == 'cargo_mt':
                row['value'] = case.values()['dwt_mt']
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'CARGO_EXCEEDS_CAPACITY_AFTER_ALLOWANCES'):
                case.prepare(Path(folder))

    def test_dwt_cannot_bypass_selected_class(self):
        case = workspace()
        for row in case.rows:
            if row['key'] == 'dwt_mt':
                row.update(value='100000', source_status='simulation_only_user_input', source_reference='Test manual edit')
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'CASE_VESSEL_OUTSIDE_CLASS_RANGE'):
                case.prepare(Path(folder))

    def test_invalid_edit_is_atomic(self):
        case = workspace()
        fingerprint = case.fingerprint
        with self.assertRaises(ValueError):
            case.apply_inputs({'port_other_total_usd': '1'}, target_tce='1000',
                observations={'argus': {'low': '900', 'high': '100'}}, oe_hps='400')
        self.assertEqual(case.fingerprint, fingerprint)

    def test_sensitivity_holds_freight_and_reduces_surplus(self):
        from decimal import Decimal
        case = workspace()
        case.context['scenarios'] = [{'scenario_id': 'delay', 'label': 'Delay',
            'fuel_price_increase_fraction': '0', 'extra_port_days': '2', 'source_status': 'test_fixture'}]
        with TemporaryDirectory() as folder:
            result = case.prepare(Path(folder))
        scenario = result['fixed_freight_sensitivities'][0]
        self.assertEqual(scenario['economics']['freight_usd_mt'], result['baseline']['freight_usd_mt'])
        self.assertLess(Decimal(scenario['change_from_baseline_usd']), 0)
        self.assertLess(Decimal(scenario['economics']['tce_before_running_usd_day']), Decimal(result['baseline']['tce_before_running_usd_day']))

    def test_package_roundtrip_recalculates_same_values(self):
        case = workspace()
        restored = import_case(export_case(case))
        self.assertEqual(restored.values(), case.values())
        self.assertIsNone(restored.preparation)
        with TemporaryDirectory() as folder:
            original = case.prepare(Path(folder))
            replay = restored.prepare(Path(folder))
        self.assertEqual(original['baseline'], replay['baseline'])
        self.assertEqual(original['fixed_freight_sensitivities'], replay['fixed_freight_sensitivities'])

    def test_package_rejects_duplicate_keys_and_size(self):
        with self.assertRaises(ValueError):
            import_case(b'{"package_version":"PILOG-CASE.1","package_version":"bad"}')
        with self.assertRaisesRegex(ValueError, 'TOO_LARGE'):
            import_case(b' ' * (5 * 1024 * 1024 + 1))

    def test_corrupt_cache_does_not_break_fallback(self):
        snapshot = latest_saved(ROOT)
        with TemporaryDirectory() as folder:
            cache = Path(folder)
            save_runtime_snapshot(snapshot, cache)
            (cache / 'fp_broken.json').write_text('{', encoding='utf-8')
            recovered = latest_saved(ROOT, cache)
        self.assertEqual(recovered['snapshot_id'], snapshot['snapshot_id'])
