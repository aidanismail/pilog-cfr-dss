import collections,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
from unittest.mock import patch
from pilog_cfr_dss.sources.route_distance import ports,distance,catalog_coordinate,searoute_port_coordinate
root=Path.cwd(); ods=root/'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx'
allports=ports(root/'data/raw/Ports.xlsx'); result=[]
with patch('pilog_cfr_dss.sources.route_distance.geocode_port',side_effect=ValueError('offline_audit')):
    for i,origin in enumerate(allports,1):
        for dest in allports:
            if origin==dest: continue
            try:
                x=distance(origin,dest,ods)
                result.append({'origin':origin[0],'destination':dest[0],'status':x['source_status'],'nm':x['value']})
            except Exception as exc:
                result.append({'origin':origin[0],'destination':dest[0],'status':'manual_required','reason':str(exc)})
        print('Checked origin',i,origin[0],flush=True)
out=root/'outputs/route_coverage_audit_i5.json'
out.write_text(json.dumps({'scope':'all directed pairs of 50 ports, offline; live Nominatim not used','routes':result},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('TOTAL',len(result),'counts',dict(collections.Counter(x['status'] for x in result)),flush=True)
catalog=root/'data/processed/port_locations_unlocode.json'
print('PORTS_WITHOUT_LOCAL_COORDINATES',[p for p in allports if not catalog_coordinate(catalog,*p) and not searoute_port_coordinate(*p)],flush=True)
