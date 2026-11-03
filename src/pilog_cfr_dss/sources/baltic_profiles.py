"""Fetch official benchmark PDF when accessible; retain a sourced offline snapshot."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
import json
import re
import pypdfium2

URL = 'https://www.balticexchange.com/content/dam/balticexchange/consumer/documents/data-services/documentation/ocean-bulk-guides-policies/GMB.pdf'
SNAPSHOT = Path(__file__).resolve().parents[3]/'data/processed/baltic_vessel_benchmarks.json'


def read_snapshot():
    data=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    if set(data['profiles']) != {'Handysize','Supramax'}:
        raise ValueError('INVALID_BALTIC_SNAPSHOT')
    return data


def verify_benchmarks():
    req=Request(URL,headers={'User-Agent':'PILOG-CFR-DSS/1.0'})
    with urlopen(req,timeout=8) as response:
        content=response.read(8_000_001)
    if not content.startswith(b'%PDF-') or len(content)>8_000_000:
        raise ValueError('BALTIC_INVALID_DOCUMENT')
    try:
        pdf=pypdfium2.PdfDocument(content)
    except pypdfium2.PdfiumError as error:
        raise ValueError('BALTIC_INVALID_DOCUMENT') from error
    try:
        text=' '.join(' '.join(pdf[i].get_textpage().get_text_range().split()) for i in range(len(pdf)))
    finally:
        pdf.close()
    checks=(r'63,500\s*mt\s*DWT',r'12\s*knots\s+on\s+20\s*mt\s+laden',
            r'38,200\s*mt\s*dwt',r'12\s*knots\s+on\s+18\s*mt\s+IFO')
    if not all(re.search(p,text,re.IGNORECASE) for p in checks):
        raise ValueError('BALTIC_BENCHMARK_CHANGED')
    return {'url':URL,'verified_at':datetime.now(timezone.utc).isoformat(),
            'sha256':sha256(content).hexdigest(),'source_status':'live_document_verified'}
