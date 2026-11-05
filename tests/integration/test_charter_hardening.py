"""Approved charter cost boundary, independent hire, portable cases and legacy replay."""
from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pilog_cfr_dss.application.case_package import export_case, import_case
from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.application.market_case import (
    new_market_case, active_catalog, apply_profile, apply_route, apply_market,
)
from pilog_cfr_dss.models.case import CHARTER_VERSION
from pilog_cfr_dss.sources.fearnpulse import latest_saved

ROOT = Path(__file__).resolve().parents[2]


def charter_case():
    case = new_market_case(ROOT, latest_saved(ROOT), dynamic_route=True)
    apply_route(case, ('Bontang', 'Indonesia'), ('Mundra', 'India'), {
        'value': '1440', 'unit': 'NM', 'loading_port': 'Bontang', 'discharging_port': 'Mundra',
        'source_status': 'simulation_only_user_input', 'source_reference': 'Deterministic test route'})
    observations = {p: {k: case.context['market_index'][p][k] for k in ('low', 'high')}
                    for p in ('argus', 'fertecon')}
    case.apply_inputs({'cargo_mt': '20000', 'speed_knots': '12',
                       'loading_rate_mt_day': '8000', 'discharge_rate_mt_day': '8000',
                       'waiting_days': '0', 'sea_fo_mt_day': '20', 'sea_do_mt_day': '0',
                       'port_do_mt_day': '0', 'fo_price_usd_mt': '600', 'do_price_usd_mt': '900',
                       'port_other_total_usd': '20000'}, target_tce='15000',
                      observations=observations, oe_hps=case.context['oe_hps']['value'])
    return case


def edit(case, **values):
    case.apply_inputs(values, target_tce=case.context['pricing']['target_tce']['value'],
                      observations={}, oe_hps=case.context['oe_hps']['value'])


class CharterHardeningTests(unittest.TestCase):
    def prepare(self, case):
        with TemporaryDirectory() as folder:
            return case.prepare(Path(folder))

    def test_default_has_hire_and_no_owned_running(self):
        case = charter_case()
        self.assertEqual(case.context['schema_version'], CHARTER_VERSION)
        self.assertEqual(case.values()['vessel_mode'], 'chartered')
        self.assertEqual(case.values()['hire_usd_day'], '13000')
        self.assertNotIn('running_usd_day', case.values())
        source = next(r for r in case.rows if r['key'] == 'hire_usd_day')
        self.assertEqual(source['source_status'], 'approved_historical_hire_default')
        self.assertIn('AQABA!B66', source['source_reference'])

    def test_approved_example_reconciles_cost_revenue_tce_and_surplus(self):
        report = self.prepare(charter_case())
        base = {k: D(v) for k, v in report['baseline'].items()}
        self.assertEqual(base['total_days'], D(10))
        self.assertEqual(base['hire_days'], D(10))
        self.assertEqual(base['bunker_usd'], D(60000))
        self.assertEqual(base['port_other_usd'], D(20000))
        self.assertEqual(base['voyage_expenses_usd'], D(80000))
        self.assertEqual(base['hire_usd'], D(130000))
        self.assertEqual(base['total_cash_cost_usd'], D(210000))
        self.assertEqual(base['freight_usd_mt'], D('11.50'))
        self.assertEqual(base['net_revenue_usd'], D(230000))
        self.assertEqual(base['contribution_usd'], D(20000))
        self.assertEqual(base['tce_usd_day'], D(15000))
        self.assertEqual(base['tce_usd_day'], (base['net_revenue_usd'] - base['voyage_expenses_usd']) / base['total_days'])
        self.assertEqual(base['contribution_usd'], base['net_revenue_usd'] - base['voyage_expenses_usd'] - base['hire_usd'])
        self.assertNotIn('running_usd', base)
        self.assertNotIn('tce_before_running_usd_day', base)
        self.assertNotIn('running_per_mt_usd', report['pricing_diagnostics'])

    def test_hire_changes_surplus_and_impas_but_not_indication_or_tce(self):
        case = charter_case()
        first = self.prepare(case)
        for hire, surplus in [('13000', '20000'), ('15000', '0'), ('17000', '-20000')]:
            changed = case.values()['hire_usd_day'] != hire
            edit(case, hire_usd_day=hire)
            if changed:
                self.assertIsNone(case.preparation)
            report = self.prepare(case)
            self.assertEqual(D(report['baseline']['contribution_usd']), D(surplus))
            self.assertEqual(report['baseline']['freight_usd_mt'], first['baseline']['freight_usd_mt'])
            self.assertEqual(report['baseline']['tce_usd_day'], first['baseline']['tce_usd_day'])
            self.assertEqual(D(report['metrics']['freight_break_even_usd_mt']), (D(80000) + D(hire) * 10) / 20000)

    def test_hire_is_preserved_on_profile_switch_and_market_refresh(self):
        case = charter_case()
        edit(case, hire_usd_day='14234.56789')
        profiles = active_catalog(ROOT)
        for profile in profiles['profiles']:
            self.assertNotIn('running_usd_day', profile['fields'])
            self.assertNotIn('running_usd_day', profile['source_cells'])
            apply_profile(case, profile, profiles['policy'])
            apply_market(case, case.context['market_snapshot'], preserve_manual=True)
            self.assertEqual(case.values()['hire_usd_day'], '14234.56789')
            report = self.prepare(case)
            self.assertEqual(D(report['baseline']['hire_usd']), D('14234.56789') * D(report['baseline']['hire_days']))

    def test_both_classes_have_the_same_approved_default_not_a_fake_quote(self):
        case = charter_case()
        profiles = active_catalog(ROOT)
        for profile in profiles['profiles']:
            apply_profile(case, profile, profiles['policy'])
            self.assertEqual(case.values()['hire_usd_day'], '13000')
            self.assertEqual(case.context['pricing']['target_tce']['value'],
                             case.context['market_snapshot']['tc_rates'][profile['market_family']]['value'])

    def test_nonmanual_index_follows_class_independently_of_hire(self):
        case = new_market_case(ROOT, latest_saved(ROOT), dynamic_route=True)
        profiles = active_catalog(ROOT)
        for profile in profiles['profiles']:
            apply_profile(case, profile, profiles['policy'])
            self.assertEqual(case.context['pricing']['target_tce']['value'],
                             case.context['market_snapshot']['tc_rates'][profile['market_family']]['value'])
            self.assertEqual(case.values()['hire_usd_day'], '13000')

    def test_delay_uses_additional_hire_and_holds_baseline_freight(self):
        case = charter_case()
        case.context['scenarios'] = [{'scenario_id': 'delay', 'label': 'Delay',
            'fuel_price_increase_fraction': '0', 'extra_port_days': '2', 'source_status': 'test_fixture'}]
        report = self.prepare(case)
        base, shock = report['baseline'], report['fixed_freight_sensitivities'][0]['economics']
        self.assertEqual(shock['freight_usd_mt'], base['freight_usd_mt'])
        self.assertEqual(D(shock['hire_usd']) - D(base['hire_usd']), D(26000))
        self.assertEqual(D(shock['contribution_usd']), D(-6000))
        self.assertLess(D(shock['tce_usd_day']), D(base['tce_usd_day']))

    def test_bunker_shock_holds_freight_without_extra_hire(self):
        case = charter_case()
        case.context['scenarios'] = [{'scenario_id': 'bunker', 'label': 'Bunker',
            'fuel_price_increase_fraction': '0.5', 'extra_port_days': '0', 'source_status': 'test_fixture'}]
        report = self.prepare(case)
        shock = report['fixed_freight_sensitivities'][0]['economics']
        self.assertEqual(shock['freight_usd_mt'], report['baseline']['freight_usd_mt'])
        self.assertEqual(shock['hire_usd'], report['baseline']['hire_usd'])
        self.assertEqual(D(shock['contribution_usd']), D(-10000))

    def test_invalid_hire_and_running_edits_are_atomic(self):
        for changes in ({'hire_usd_day': '-1'}, {'hire_usd_day': 'NaN'},
                        {'hire_usd_day': ''}, {'running_usd_day': '5200'}):
            case = charter_case()
            before = case.fingerprint
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                edit(case, **changes)
            self.assertEqual(case.fingerprint, before)

    def test_package_preserves_hire_source_precision_results_and_sensitivity(self):
        case = charter_case()
        edit(case, hire_usd_day='14234.56789')
        payload = export_case(case)
        self.assertEqual(json.loads(payload)['package_version'], 'PILOG-CASE.2')
        restored = import_case(payload)
        self.assertEqual(restored.values(), case.values())
        self.assertEqual(restored.rows, case.rows)
        self.assertIsNone(restored.preparation)
        first, replay = self.prepare(case), self.prepare(restored)
        self.assertEqual(first['baseline'], replay['baseline'])
        self.assertEqual(first['fixed_freight_sensitivities'], replay['fixed_freight_sensitivities'])

    def test_package_rejects_wrong_hire_unit_missing_hire_and_running_in_new_schema(self):
        for mutation in ('unit', 'missing', 'running', 'version'):
            data = json.loads(export_case(charter_case()))
            row = next(r for r in data['rows'] if r['key'] == 'hire_usd_day')
            if mutation == 'unit': row['unit'] = 'USD/MT'
            elif mutation == 'missing': data['rows'].remove(row)
            elif mutation == 'running': row['key'] = 'running_usd_day'
            else: data['package_version'] = 'PILOG-CASE.1'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                import_case(json.dumps(data).encode())

    def test_legacy_packages_keep_owned_costs_and_can_replay_without_conversion(self):
        legacy = InteractiveCase.read(ROOT / 'data/processed/case_template.json')
        restored = import_case(export_case(legacy))
        self.assertEqual(restored.values()['vessel_mode'], 'owned')
        self.assertIn('running_usd_day', restored.values())
        self.assertNotIn('hire_usd_day', restored.values())
        self.assertEqual(self.prepare(restored)['baseline'], self.prepare(legacy)['baseline'])

    def test_fixed_quote_hire_reforecast_preserves_quote_and_updates_only_cost(self):
        case = charter_case()
        with TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = case.prepare(root)
            case.fix_freight(root)
            quote = deepcopy(case.context['freight_tender'])
            forecast = case.reforecast_costs({'hire_usd_day': '17000'}, 'New owner indication')
            report = forecast.prepare(root)
        self.assertEqual(forecast.context['freight_tender'], quote)
        self.assertEqual(report['baseline']['freight_usd_mt'], baseline['baseline']['freight_usd_mt'])
        self.assertEqual(D(report['baseline']['contribution_usd']), D(-20000))
        self.assertEqual(report['commercial_review']['drivers'][-1]['component'], 'hire_usd')
        with self.assertRaises(ValueError):
            forecast.reforecast_costs({'running_usd_day': '5200'}, 'Wrong model')

    def test_zero_hire_remains_explicit_and_does_not_fall_back_to_owned_cost(self):
        case = charter_case()
        edit(case, hire_usd_day='0')
        report = self.prepare(case)
        self.assertEqual(D(report['baseline']['hire_usd']), D(0))
        self.assertEqual(D(report['baseline']['contribution_usd']), D(150000))

    def test_each_operating_input_reaches_its_expected_calculation(self):
        cases = [
            ('cargo_mt', '21000', 'loading_days'),
            ('distance_nm', '1500', 'sea_days'),
            ('speed_knots', '13', 'sea_days'),
            ('loading_rate_mt_day', '10000', 'loading_days'),
            ('discharge_rate_mt_day', '10000', 'discharge_days'),
            ('waiting_days', '2', 'total_days'),
            ('sea_fo_mt_day', '21', 'fo_cost_usd'),
            ('sea_do_mt_day', '0.2', 'do_cost_usd'),
            ('port_do_mt_day', '1', 'do_cost_usd'),
            ('fo_price_usd_mt', '650', 'bunker_usd'),
            ('do_price_usd_mt', '950', 'bunker_usd'),
            ('port_other_total_usd', '21000', 'voyage_expenses_usd'),
            ('hire_usd_day', '14000', 'hire_usd'),
        ]
        for key, value, output in cases:
            with self.subTest(key=key):
                case = charter_case()
                if key == 'do_price_usd_mt':
                    edit(case, port_do_mt_day='1')
                first = self.prepare(case)
                edit(case, **{key: value})
                second = self.prepare(case)
                self.assertNotEqual(D(first['baseline'][output]), D(second['baseline'][output]))

    def test_capacity_inputs_change_capacity_without_inventing_cost(self):
        for key, value in [('dwt_mt', '39000'), ('bunkers_allowance_mt', '1900'),
                           ('constants_allowance_mt', '600')]:
            with self.subTest(key=key):
                case = charter_case()
                first = self.prepare(case)
                edit(case, **{key: value})
                second = self.prepare(case)
                self.assertNotEqual(first['pricing_diagnostics']['capacity_headroom_mt'],
                                    second['pricing_diagnostics']['capacity_headroom_mt'])
                self.assertEqual(first['baseline'], second['baseline'])

    def test_index_edit_changes_indication_and_surplus_without_changing_cost(self):
        case = charter_case()
        first = self.prepare(case)
        case.apply_inputs({}, target_tce='17000', observations={}, oe_hps=case.context['oe_hps']['value'])
        second = self.prepare(case)
        self.assertGreater(D(second['baseline']['freight_usd_mt']), D(first['baseline']['freight_usd_mt']))
        self.assertEqual(second['baseline']['total_cash_cost_usd'], first['baseline']['total_cash_cost_usd'])
        self.assertEqual(D(second['baseline']['contribution_usd']), D(40000))

    def test_allowance_and_zero_commission_guards_still_apply(self):
        case = charter_case()
        edit(case, cargo_mt=case.values()['dwt_mt'])
        with self.assertRaisesRegex(ValueError, 'CAPACITY_AFTER_ALLOWANCES'):
            self.prepare(case)
        for key in ('freight_commission_fraction', 'broker_fraction', 'additional_commission_fraction'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'COMMISSION_MUST_BE_ZERO'):
                edit(charter_case(), **{key: '0.01'})

    def test_zero_result_rounding_is_not_an_artificial_material_profit(self):
        case = charter_case()
        edit(case, hire_usd_day='15000', cargo_mt='21001', waiting_days='0.123')
        report = self.prepare(case)
        surplus = D(report['baseline']['contribution_usd'])
        self.assertGreaterEqual(surplus, 0)
        # Pricing retains the historical ceiling at 0.0001 USD/MT.
        self.assertLess(surplus, D('0.0001') * D(21001))

