"""Build a small, traceable UN/LOCODE location catalog from an official release ZIP."""
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile
import pycountry
import searoute
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'data/raw/unlocode_2025_1.zip'
OUTPUT = ROOT/'data/processed/port_locations_unlocode.json'
ALIASES = {'South Korea':'KR', 'Russia':'RU', 'Vietnam':'VN', 'Taiwan':'TW',
           'Turkey':'TR', 'Brunei':'BN', 'Venezuela':'VE', 'United Kingdom':'GB',
           'United States':'US', 'Libya':'LY'}


def normalized(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def coordinate(value):
    match = re.fullmatch(r'(\d{2})(\d{2})([NS])\s+(\d{3})(\d{2})([EW])', value.strip())
    if not match:
        return None
    a,b,ns,c,d,ew = match.groups()
    lat = (int(a)+int(b)/60) * (-1 if ns=='S' else 1)
    lon = (int(c)+int(d)/60) * (-1 if ew=='W' else 1)
    if int(b)>=60 or int(d)>=60 or abs(lat)>90 or abs(lon)>180:
        return None
    return [round(lon,6), round(lat,6)]


def build():
    raw = ARCHIVE.read_bytes(); records = []; aliases=[]
    with ZipFile(ARCHIVE) as archive:
        for filename in sorted(x for x in archive.namelist() if 'UNLOCODE CodeListPart' in x and x.endswith('.csv')):
            for row in csv.reader(StringIO(archive.read(filename).decode('cp1252', errors='replace'))):
                if len(row) >= 11 and row[0]=='=' and '=' in row[3]:
                    aliases.append((row[1],*[normalized(s) for s in row[3].split('=',1)]))
                if len(row) < 11 or not row[2] or '1' not in row[6]:
                    continue
                records.append(row)
    wb=load_workbook(ROOT/'data/raw/Ports.xlsx',read_only=True,data_only=True)
    try:
        requested = [(str(r[1]).strip(),str(r[0]).strip()) for r in list(wb.active.values)[1:] if r[0] and r[1]]
    finally:
        wb.close()
    matches=[];unresolved=[]
    graph=searoute.setup_P()
    for port,country in requested:
        try:
            code=ALIASES.get(country) or pycountry.countries.lookup(country).alpha_2
        except LookupError:
            unresolved.append({'port':port,'country':country,'reason':'country_unresolved'});continue
        names={normalized(port)}
        names.update(target for c,alias,target in aliases if c==code and alias==normalized(port))
        candidates=[r for r in records if r[1]==code and any(n.replace(' ','') in {normalized(r[3]).replace(' ',''),normalized(r[4]).replace(' ',''),normalized(r[3].split(',')[0]).replace(' ',''),normalized(r[4].split(',')[0]).replace(' ','')} for n in names)]
        if len(candidates)!=1:
            unresolved.append({'port':port,'country':country,'reason':'no_exact_match' if not candidates else 'multiple_exact_matches','candidates':len(candidates)});continue
        r=candidates[0]; locode=r[1]+r[2]; coords=coordinate(r[10]); coord_source='UN/LOCODE'
        if not coords:
            graph_points=[list(node) for node,attrs in graph.nodes(data=True) if attrs.get('port')==locode]
            if len(graph_points)!=1:
                unresolved.append({'port':port,'country':country,'locode':locode,'reason':'coordinate_unavailable_or_ambiguous','candidates':len(graph_points)});continue
            coords=graph_points[0];coord_source='Searoute 1.6.0 port catalog'
        matches.append({'port':port,'country':country,'locode':locode, 'coordinates':coords,
            'unlocode_name':r[3], 'function':r[6], 'status':r[7], 'source_coordinate':r[10], 'coordinate_source':coord_source})
    output={'source':'UN/LOCODE 2025-1','source_url':'https://unlocode.unece.org/publications/',
            'license':'CC BY 4.0','source_archive_sha256':sha256(raw).hexdigest(),
            'note':'Coordinates from UN/LOCODE or the Searoute 1.6.0 port catalog are indicative, not verified berth coordinates.',
            'matched':matches,'unresolved':unresolved}
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'matched':len(matches),'unresolved':unresolved},ensure_ascii=False))


if __name__=='__main__': build()
