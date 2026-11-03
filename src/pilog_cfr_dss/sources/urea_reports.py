"""Extract explicitly labelled FOB SEA granular urea assessments from PDFs."""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re
import pypdfium2


def _text(path, page):
    doc = pypdfium2.PdfDocument(str(path))
    try:
        return doc[page].get_textpage().get_text_range()
    finally:
        doc.close()


def read_reports(root: Path):
    files = list((root/'public').glob('*Nitrogen*.pdf'))
    argus = [p for p in files if p.name.lower().startswith('argus')]
    fert = [p for p in files if p.name.lower().startswith('fertecon')]
    if len(argus) != 1 or len(fert) != 1:
        raise ValueError('UREA_REPORTS_NOT_UNIQUE')
    a0, a1, f0 = _text(argus[0],0), _text(argus[0],1), _text(fert[0],0)
    date_a = re.search(r'Issue\s+\S+\s*\|\s*\w+\s+(\d{1,2}\s+\w+\s+\d{4})', a0)
    date_f = re.search(r'Volume\s+\d+\s*/\s*Issue\s+\d+\s*/\s*(\w+\s+\d{1,2},\s*\d{4})', f0)
    section = a1.split('Granular urea - fob bulk', 1)
    if len(section) != 2 or not date_a or not date_f:
        raise ValueError('UREA_REPORT_LAYOUT_UNRECOGNISED')
    matches_a = re.findall(r'(?m)^Southeast Asia\s+(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s', section[1])
    matches_f = re.findall(r'(?m)^FOB SE Asia urea \(granular\) FGUAA04\s+\S+\s+(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)', f0)
    if len(matches_a) != 1 or len(matches_f) != 1:
        raise ValueError('UREA_REPORT_SERIES_NOT_UNIQUE')
    def item(path, values, date, series, page):
        return {'low':values[0], 'high':values[1], 'unit':'USD/MT', 'basis':'FOB SEA granular',
                'series':series, 'observation_date':date, 'source_status':'observed_report',
                'source_reference':f'public/{path.name} :: PDF page {page}', 'sha256':sha256(path.read_bytes()).hexdigest()}
    return {'argus':item(argus[0],matches_a[0],datetime.strptime(date_a.group(1),'%d %B %Y').date().isoformat(), 'Granular urea FOB bulk Southeast Asia',2),
            'fertecon':item(fert[0],matches_f[0],datetime.strptime(date_f.group(1),'%B %d, %Y').date().isoformat(), 'FOB SE Asia urea granular FGUAA04',1)}
