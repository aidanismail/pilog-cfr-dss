import io
import unittest
from unittest.mock import patch
from pilog_cfr_dss.sources.baltic_profiles import read_snapshot, verify_benchmarks


class BalticProfilesTests(unittest.TestCase):
    def test_snapshot_has_source_and_two_profiles(self):
        data=read_snapshot()
        self.assertEqual(data['document_version'],'8.8')
        self.assertEqual(data['profiles']['Supramax']['dwt_mt'],'63500')
        self.assertEqual(data['profiles']['Handysize']['dwt_mt'],'38200')

    def test_rejects_non_pdf(self):
        with patch('pilog_cfr_dss.sources.baltic_profiles.urlopen',return_value=io.BytesIO(b'<html>')):
            with self.assertRaisesRegex(ValueError,'BALTIC_INVALID_DOCUMENT'):
                verify_benchmarks()

    def test_rejects_changed_benchmark(self):
        with patch('pilog_cfr_dss.sources.baltic_profiles.urlopen',return_value=io.BytesIO(b'%PDF-x')), \
             patch('pilog_cfr_dss.sources.baltic_profiles.pypdfium2.PdfDocument') as pdf:
            pdf.return_value.__len__.return_value=1
            pdf.return_value.__getitem__.return_value.get_textpage.return_value.get_text_range.return_value='changed'
            with self.assertRaisesRegex(ValueError,'BALTIC_BENCHMARK_CHANGED'):
                verify_benchmarks()
