import unittest
from unittest.mock import Mock, patch
from pilog_cfr_dss.sources.baltic_profiles import read_snapshot, verify_benchmarks


PAGE = """
<p>Baltic Supramax vessel for Timecharter routes</p>
<p>63,500mt DWT on 13.418m SSW – TPC 61.4</p>
<p>GRAIN: 80,500cbm BALE: 76,200cbm</p>
<p>14 knots on 29 mt laden, 25mt ballast. Marine Fuel Oil, no Marine Gas Oil at sea</p>
<h3>Handysize Index</h3>
<p>Baltic Handysize 38 vessel for Timecharter routes</p>
<p>38,200mt dwt on 10.538m SSW / TPC 49</p>
<p>47,125 cbm grain / 45,300 cbm bale</p>
<p>12 knots on 18mt IFO (380 CST) laden/17mt IFO (380 CST) ballast + 0.1 MDO at sea</p>
<h3>Sale &amp; Purchase</h3>
"""


def response(html, content_type="text/html"):
    return Mock(text=html, content=html.encode("utf-8"), headers={"Content-Type": content_type})


class BalticProfilesTests(unittest.TestCase):
    def test_snapshot_has_source_and_two_profiles(self):
        data=read_snapshot()
        self.assertEqual(data['document_version'],'8.8')
        self.assertEqual(data['profiles']['Supramax']['dwt_mt'],'63500')
        self.assertEqual(data['profiles']['Handysize']['dwt_mt'],'38200')

    def test_rejects_non_html(self):
        with patch('pilog_cfr_dss.sources.baltic_profiles.requests.get',
                   return_value=response("%PDF-", "application/pdf")):
            with self.assertRaisesRegex(ValueError,'BALTIC_INVALID_DOCUMENT'):
                verify_benchmarks()

    def test_checks_every_profile_against_its_own_section(self):
        with patch('pilog_cfr_dss.sources.baltic_profiles.requests.get', side_effect=[
            response(PAGE), response(PAGE.replace("14 knots on 29 mt", "14 knots on 30 mt")),
            response(PAGE.replace("TPC 49", "TPC 42")),
        ]):
            self.assertEqual(verify_benchmarks()["status"], "verified")
            with self.assertRaisesRegex(ValueError, 'BALTIC_BENCHMARK_CHANGED:Supramax'):
                verify_benchmarks()
            with self.assertRaisesRegex(ValueError, 'BALTIC_BENCHMARK_CHANGED:Handysize'):
                verify_benchmarks()
