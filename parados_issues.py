"""Abre uma issue por fonte parada e fecha quando a fonte volta a publicar (le docs/parados.json; usa o gh do runner).
Titulo fixo: 'Fonte parada: <feed>' (uma issue aberta por fonte; sem repeticao diaria)."""
import json,os,subprocess,datetime as dt
PREF='Fonte parada: '
def gh(*a): return subprocess.run(['gh',*a],capture_output=True,text=True,check=True).stdout
try: pa=json.load(open('docs/parados.json',encoding='utf-8'))
except Exception: pa={}
abertas={i['title'][len(PREF):]:i['number'] for i in json.loads(gh('issue','list','--state','open','--limit','100','--json','number,title')) if i['title'].startswith(PREF)}
hoje=dt.date.today()
for k,v in pa.items():
    if k in abertas: continue
    idade=(hoje-dt.date.fromisoformat(v['ultimo_item'])).days
    corpo=(f"O item mais recente do feed `{k}` e de {v['ultimo_item']} ({idade} dias; limite desta fonte: {v['limite_dias']} dias).\n\n"
           "O script gerou o feed normalmente: a fonte pode ter parado de publicar, ou o site mudou o layout e so itens antigos aparecem. "
           "Abra o site da fonte e confira. Esta issue fecha sozinha quando o feed voltar a ter item novo dentro do limite.")
    gh('issue','create','--title',PREF+k,'--body',corpo);print('issue aberta:',k)
for k,n in abertas.items():
    if k not in pa:
        gh('issue','close',str(n),'--comment','A fonte voltou a publicar dentro do limite; fechando.');print('issue fechada:',k)
