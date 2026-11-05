"""Portable editable cases. No paths, quotes or decisions executed on import."""
import csv
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.validation.case import load_case, unique_object
from pilog_cfr_dss.models.case import is_chartered

MAX_BYTES = 5 * 1024 * 1024


def export_case(case: InteractiveCase) -> bytes:
    version = 'PILOG-CASE.2' if is_chartered(case.context) else 'PILOG-CASE.1'
    return json.dumps({'package_version': version, 'context': case.context, 'rows': case.rows},
                      ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')


def import_case(content: bytes) -> InteractiveCase:
    if len(content) > MAX_BYTES:
        raise ValueError('CASE_PACKAGE_TOO_LARGE')
    data = json.loads(content.decode('utf-8-sig'), object_pairs_hook=unique_object)
    if not isinstance(data, dict) or data.get('package_version') not in {'PILOG-CASE.1', 'PILOG-CASE.2'}:
        raise ValueError('INVALID_CASE_PACKAGE_VERSION')
    context, rows = data.get('context'), data.get('rows')
    if not isinstance(context, dict) or not isinstance(rows, list) or not rows or len(rows) > 100:
        raise ValueError('INVALID_CASE_PACKAGE')
    if data['package_version'] != ('PILOG-CASE.2' if is_chartered(context) else 'PILOG-CASE.1'):
        raise ValueError('CASE_PACKAGE_COST_MODEL_MISMATCH')
    if any(not isinstance(row, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in row.items()) for row in rows):
        raise ValueError('INVALID_CASE_PACKAGE_ROWS')
    context = deepcopy(context)
    # A package never controls filesystem paths, including Windows drive paths.
    context['voyage_dataset'] = 'voyage_inputs.csv'
    with TemporaryDirectory(prefix='pilog_case_import_') as folder:
        root = Path(folder)
        with (root / 'voyage_inputs.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        fixture = root / 'case_fixture.json'
        fixture.write_text(json.dumps(context, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        load_case(fixture, pre_tender=True)
    return InteractiveCase(context, deepcopy(rows))
