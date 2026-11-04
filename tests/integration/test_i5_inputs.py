from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from pilog_cfr_dss.application.market_case import new_market_case, active_catalog, apply_profile, apply_route
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.sources.route_distance import ports, distance
from pilog_cfr_dss.sources.urea_reports import read_reports

ROOT = Path(__file__).resolve().parents[2]


class Iteration5Inputs(unittest.TestCase):
    def test_reports(self):
        reports = read_reports(ROOT)
        self.assertEqual((reports['argus']['low'],reports['argus']['high']), ('415','425'))
        self.assertEqual((reports['fertecon']['low'],reports['fertecon']['high']), ('410.00','410.00'))
        self.assertEqual(reports['argus']['observation_date'], '2026-09-10')

    def test_ports_and_no_od_fallback(self):
        choices = ports(ROOT/'data/raw/Ports.xlsx')
        self.assertIn(('Bontang','Indonesia'), choices)
        self.assertIn(('Antwerp','Belgium'), choices)
        with patch('pilog_cfr_dss.sources.route_distance.catalog_coordinate',return_value=None), patch('pilog_cfr_dss.sources.route_distance.searoute_port_coordinate',return_value=None), patch('pilog_cfr_dss.sources.route_distance.geocode_port',side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError, 'DISTANCE_UNAVAILABLE_ENTER_MANUALLY'):
                distance(('Bontang','Indonesia'),('Mundra','India'),ROOT/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
            with self.assertRaises(ValueError):
                distance(('Bontang','Indonesia'),('Antwerp','Belgium'),ROOT/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')

    def test_geocoding_rejects_city_instead_of_port(self):
        from pilog_cfr_dss.sources.route_distance import geocode_port
        geocode_port.cache_clear()
        city = SimpleNamespace(longitude=117.5,latitude=0.1,raw={'type':'administrative'})
        with patch('geopy.geocoders.Nominatim') as provider:
            provider.return_value.geocode.return_value = [city]
            with self.assertRaisesRegex(ValueError, 'PORT_NOT_FOUND'):
                geocode_port('Bontang','Indonesia')
        geocode_port.cache_clear()

    def test_geocoding_filters_irrelevant_results_and_preserves_ambiguity(self):
        from pilog_cfr_dss.sources.route_distance import geocode_port
        def result(name, typ, category='landuse'):
            return SimpleNamespace(longitude=1.2,latitude=3.4,address=name,raw={'type':typ,'class':category,
                'display_name':name,'address':{'country_code':'id'}})
        pharmacy=result('Bontang Port Pharmacy, Indonesia','pharmacy','shop')
        facility=result('Bontang Port, Indonesia','industrial')
        alternative=result('Bontang Harbour, Indonesia','harbour')
        geocode_port.cache_clear()
        with patch('geopy.geocoders.Nominatim') as provider, patch('pilog_cfr_dss.sources.route_distance.sleep'):
            provider.return_value.geocode.return_value=[pharmacy,facility]
            self.assertEqual(geocode_port('Bontang','Indonesia'),(1.2,3.4))
            geocode_port.cache_clear()
            provider.return_value.geocode.return_value=[facility,alternative]
            with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):
                geocode_port('Bontang','Indonesia')
        geocode_port.cache_clear()

    def test_local_catalog_routes_without_network(self):
        with patch('pilog_cfr_dss.sources.route_distance.geocode_port',side_effect=AssertionError('unexpected network')):
            ref=distance(('Bontang','Indonesia'),('Antwerp','Belgium'),ROOT/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
            aqaba=distance(('Aqaba','Jordan'),('Hai Phong','Vietnam'),ROOT/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
        self.assertEqual(ref['origin_locode'],'IDBXT')
        self.assertEqual(ref['destination_locode'],'BEANR')
        self.assertGreater(float(ref['value']), 0)
        self.assertEqual(aqaba['origin_locode'], 'JOAQB')
        self.assertEqual(aqaba['destination_locode'], 'VNHPH')
        self.assertGreater(float(aqaba['value']), 0)

    def test_approved_spelling_variants_use_unique_port_codes(self):
        from pilog_cfr_dss.sources.route_distance import searoute_port_coordinate
        for port,country,code in [('Brunsbuettel','Germany','DEBRB'),('Zhanjiang','China','CNZHA'),('Mersa Al Brega','Libya','LYLMQ')]:
            self.assertEqual(searoute_port_coordinate(port,country)[1],code)
        self.assertIsNone(searoute_port_coordinate('Davao','Philippines'))

    def test_confirmed_davao_and_jose_coordinates_are_used(self):
        with patch('pilog_cfr_dss.sources.route_distance.geocode_port',side_effect=AssertionError('unexpected network')):
            result=distance(('Davao','Philippines'),('Jose','Venezuela'),ROOT/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
        self.assertEqual(result['origin_coordinates'],(125.633333,7.066667))
        self.assertEqual(result['destination_coordinates'],(-64.85,10.1))
        self.assertEqual((result['origin_locode'],result['destination_locode']),('PHDVO','VEJOT'))
        self.assertGreater(float(result['value']),0)

    def test_route_estimate_runs_in_engine(self):
        with patch('pilog_cfr_dss.sources.route_distance.geocode_port', side_effect=AssertionError('unexpected network')):
            ref=distance(('Bontang','Indonesia'),('Antwerp','Belgium'),ROOT/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
        case=new_market_case(ROOT,latest_saved(ROOT))
        apply_route(case,('Bontang','Indonesia'),('Antwerp','Belgium'),ref)
        data=active_catalog(ROOT);apply_profile(case,data['profiles'][0],data['policy'])
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as d:
            report=case.prepare(Path(d))
        self.assertAlmostEqual(float(report['route_distance']['value']),float(ref['value']))
        self.assertGreater(float(report['baseline']['total_days']),0)

    def test_profiles_and_manual_route_prepare(self):
        case = new_market_case(ROOT, latest_saved(ROOT))
        ref = {'value':'4000','unit':'NM','loading_port':'Bontang','discharging_port':'Antwerp',
               'source_status':'simulation_only_user_input','source_reference':'Input jarak manual'}
        apply_route(case,('Bontang','Indonesia'),('Antwerp','Belgium'),ref)
        data = active_catalog(ROOT)
        self.assertEqual([p['fields']['dwt_mt'] for p in data['profiles']],['38200','63500'])
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as d:
            for profile in data['profiles']:
                apply_profile(case,profile,data['policy'])
                result = case.prepare(Path(d))
                self.assertGreater(float(result['baseline']['total_days']),0)

    def test_prepare_rejects_cargo_over_dwt(self):
        case=new_market_case(ROOT, latest_saved(ROOT))
        ref=case.context['distance_reference']
        apply_route(case,(case.values()['loading_port'],''),(case.values()['discharging_port'],''),ref)
        for row in case.rows:
            if row['key']=='cargo_mt': row['value']='40000'
        self.assertLess(float(case.values()['dwt_mt']),40000)
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as d:
            with self.assertRaisesRegex(ValueError,'CARGO_EXCEEDS_CASE_GROSS_DWT'):
                case.prepare(Path(d))
        self.assertIsNone(case.preparation)

    def test_ui_blocks_cargo_over_dwt(self):
        from streamlit.testing.v1 import AppTest
        with patch('pilog_cfr_dss.ui.views._fresh_market', return_value=latest_saved(ROOT)), patch('pilog_cfr_dss.ui.views._baltic_check', return_value={'source_status':'test'}):
            app=AppTest.from_file(str(ROOT/'apps/streamlit_app.py'),default_timeout=30).run()
            case = app.session_state['case']
            key = f'inputs_table_{case.draft_id}_{case.revision}_None'
            app.session_state[key] = {'edited_rows': {0: {'Nilai': 40000.0}}, 'added_rows': [], 'deleted_rows': []}
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(next(x for x in app.button if x.label=='Hitung ekonomi voyage').disabled)
            self.assertTrue(any('melebihi DWT' in str(x.value) for x in app.error))

    def test_table_edits_apply_together_and_invalidate_old_result(self):
        from streamlit.testing.v1 import AppTest
        with patch('pilog_cfr_dss.ui.views._fresh_market', return_value=latest_saved(ROOT)), patch('pilog_cfr_dss.ui.views._baltic_check', return_value={'source_status':'test'}):
            app = AppTest.from_file(str(ROOT/'apps/streamlit_app.py'), default_timeout=30).run()
            next(x for x in app.button if x.label == 'Hitung ekonomi voyage').click().run()
            case = app.session_state['case']
            self.assertIsNotNone(case.preparation)
            key = f'inputs_table_{case.draft_id}_{case.revision}_None'
            app.session_state[key] = {'edited_rows': {0: {'Nilai': 28000.0}, 2: {'Nilai': 4500.0}}, 'added_rows': [], 'deleted_rows': []}
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['case'].values()['cargo_mt'], '28000')
            self.assertEqual(app.session_state['case'].values()['loading_rate_mt_day'], '4500')
            self.assertIsNone(app.session_state['case'].preparation)

    def test_unavailable_route_requires_manual_input_without_reusing_old_distance(self):
        from streamlit.testing.v1 import AppTest
        def selective_distance(origin, destination, workbook):
            if destination[0] == 'Antwerp':
                raise ValueError('offline')
            return distance(origin, destination, workbook)
        with patch('pilog_cfr_dss.ui.views._fresh_market', return_value=latest_saved(ROOT)), patch('pilog_cfr_dss.ui.views._baltic_check', return_value={'source_status':'test'}), patch('pilog_cfr_dss.ui.views.distance',side_effect=selective_distance):
            app=AppTest.from_file(str(ROOT/'apps/streamlit_app.py'),default_timeout=30).run()
            next(x for x in app.selectbox if x.label=='Pelabuhan bongkar (PoD)').set_value(('Antwerp','Belgium')).run()
            self.assertFalse(app.exception)
            self.assertTrue(next(x for x in app.button if x.label=='Hitung ekonomi voyage').disabled)
            case = app.session_state['case']
            route = (('Bontang', 'Indonesia'), ('Antwerp', 'Belgium'))
            key = f'inputs_table_{case.draft_id}_{case.revision}_{route}'
            app.session_state[key] = {'edited_rows': {1: {'Nilai': 4000.0}}, 'added_rows': [], 'deleted_rows': []}
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['case'].values()['discharging_port'],'Antwerp')
            self.assertEqual(app.session_state['case'].values()['distance_nm'],'4000')

    def test_ui_hides_tender_and_calculates(self):
        from streamlit.testing.v1 import AppTest
        with patch('pilog_cfr_dss.ui.views._fresh_market', return_value=latest_saved(ROOT)), patch('pilog_cfr_dss.ui.views._baltic_check', return_value={'source_status':'test'}):
            app = AppTest.from_file(str(ROOT/'apps/streamlit_app.py'), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertFalse(any(x.label == 'Evaluasi tender & DSS' for x in app.button))
            self.assertEqual(app.session_state['case'].context['distance_reference']['source_status'], 'estimated_sea_route')
            self.assertEqual(len(next(x for x in app.selectbox if x.label=='Pilih profil kapal').options), 2)
            next(x for x in app.button if x.label=='Hitung ekonomi voyage').click().run()
            self.assertFalse(app.exception)
            self.assertIsNotNone(app.session_state['case'].preparation)
            self.assertTrue(any(x.label == 'TCE hasil voyage (USD/hari)' for x in app.metric))
            self.assertTrue(any(x.label == 'Freight impas (USD/MT)' for x in app.metric))

    def test_report_comparables_preserve_route_and_assessment_basis(self):
        from pilog_cfr_dss.sources.market_comparables import read_comparables, voyage_matches, comparison_delta
        data = read_comparables(ROOT)
        self.assertEqual((data['cfr']['Brazil']['low'], data['cfr']['Brazil']['high']), ('459.00', '469.00'))
        self.assertEqual(data['cfr']['Vietnam']['low'], '450.00')
        self.assertEqual(data['cfr']['Indonesia']['code'], 'FGUAC04')
        self.assertNotIn('India', data['cfr'])
        found = voyage_matches(data['voyages'], 'Jubail', 'Mundra')
        self.assertEqual([(x['cargo_mt'], x['low'], x['high']) for x in found], [(45000, '139.00', '141.00')])
        self.assertEqual(tuple(str(x) for x in comparison_delta('140', found[0])), ('-1.00', '1.00'))
        contextual = voyage_matches(data['voyages'], 'Bontang', 'Mundra')
        self.assertTrue(contextual)
        self.assertTrue(all(item['match_scope'] == 'tujuan_kawasan_asal_berbeda' for item in contextual))

    def test_aqaba_hai_phong_dropdown_automatically_updates(self):
        from streamlit.testing.v1 import AppTest
        with patch('pilog_cfr_dss.ui.views._fresh_market', return_value=latest_saved(ROOT)), patch('pilog_cfr_dss.ui.views._baltic_check', return_value={'source_status':'test'}), patch('pilog_cfr_dss.sources.route_distance.geocode_port',side_effect=AssertionError('unexpected network')):
            app=AppTest.from_file(str(ROOT/'apps/streamlit_app.py'),default_timeout=30).run()
            next(x for x in app.selectbox if x.label=='Pelabuhan muat (PoL)').set_value(('Aqaba','Jordan')).run()
            self.assertFalse(app.exception)
            next(x for x in app.selectbox if x.label=='Pelabuhan bongkar (PoD)').set_value(('Hai Phong','Vietnam')).run()
            self.assertFalse(app.exception)
            values=app.session_state['case'].values()
            self.assertEqual((values['loading_port'],values['discharging_port']),('Aqaba','Hai Phong'))
            self.assertGreater(float(values['distance_nm']),0)
            self.assertFalse(any(x.label=='Terapkan rute' for x in app.button))
            selector = next(x for x in app.selectbox if x.label == 'Pilih profil kapal')
            selector.set_value('ve_godau').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['case'].values()['dwt_mt'], '63500')
            self.assertIsNone(app.session_state['case'].preparation)
            next(x for x in app.button if x.label=='Hitung ekonomi voyage').click().run()
            self.assertFalse(app.exception)
            self.assertIsNotNone(app.session_state['case'].preparation)
            destination = next(x for x in app.selectbox if x.label == 'Pelabuhan bongkar (PoD)')
            destination.set_value(('Antwerp', 'Belgium')).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.exception)
            self.assertFalse(any(x.label == 'Terapkan rute' for x in app.button))
            self.assertEqual(app.session_state['case'].values()['discharging_port'], 'Antwerp')
            self.assertIsNone(app.session_state['case'].preparation)
            next(x for x in app.button if x.label=='Hitung ekonomi voyage').click().run()
            self.assertFalse(app.exception)
            self.assertIsNotNone(app.session_state['case'].preparation)

if __name__ == '__main__':
    unittest.main()
