"""Generate one portable HTML file from maintainable source files and the catalog."""
import json
from pathlib import Path
import twin
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    data=twin.status()
    data['project_path']=str(twin.ROOT)
    data['prompts']={c['id']:twin.deletion_prompt(c,data) for c in data['cases']}
    data['batch_header']=twin.batch_prompt([],data)
    snapshot=json.dumps(data,ensure_ascii=False,indent=2).replace('<','\\u003c')
    template=(HERE/'template.html').read_text()
    html=template.replace('__STYLE__',(HERE/'style.css').read_text()).replace('__SCRIPT__',(HERE/'app.js').read_text()).replace('__SNAPSHOT__',snapshot)
    (HERE/'index.html').write_text(html)
    print('Digitaler Zwilling erstellt:',len(data['cases']),'Use Cases,',data['inventory']['route_count'],'API-Routen')
