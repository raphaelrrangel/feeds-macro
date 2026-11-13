"""Gera RSS a partir de paginas sem feed (JCER, NRI) e espelha feeds que o Inoreader nao atualiza (RIETI filtrado, Daiwa DIR).
Uso: python3 code/27_feeds_jcer_nri.py  -> docs/jcer_en.xml, nri_kiuchi.xml, nri_finsights.xml
Sem dependencias alem de requests. Rodar de tempos em tempos; o leitor (Inoreader) precisa de uma URL publica."""
import requests,re,html,datetime as dt
from xml.sax.saxutils import escape
H={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
HOJE=dt.date.today()
import time,sys
def get(u,tentativas=3):
    # tentativas com espera: o GitHub Actions as vezes recebe timeout/403/5xx temporario dos sites
    ult=None
    for i in range(tentativas):
        try:
            r=requests.get(u,headers=H,timeout=(10,25));r.raise_for_status();return r.text
        except Exception as e:
            ult=e;print(f'aviso: {u} tentativa {i+1}/{tentativas}: {type(e).__name__} {e}',file=sys.stderr);time.sleep(5*(i+1))
    raise ult
def seguro(f,*a):
    # uma fonte que falha nao derruba as outras: devolve [] e o minimo abaixo preserva o feed antigo
    try: return f(*a)
    except Exception as e:
        print(f'ERRO {f.__name__}: {type(e).__name__} {e}',file=sys.stderr);return []
def clean(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip()
def jcer():
    t=get('https://www.jcer.or.jp/en');out=[];seen=set()
    for h,body in re.findall(r'<a href="(https://www\.jcer\.or\.jp/english/[^"]+)">(.*?)</a>',t,re.S):
        d=re.findall(r'<dt>(\d\d)/(\d\d)',body);ti=re.findall(r'<dd>(.*?)</dd>',body,re.S)
        if not d or not ti or h in seen: continue
        seen.add(h);m,dd=int(d[0][0]),int(d[0][1]);y=HOJE.year if dt.date(HOJE.year,m,dd)<=HOJE else HOJE.year-1
        out.append((dt.date(y,m,dd),clean(ti[0]),h))
    return out
def nri(url,pat):
    t=get(url);out=[];seen=set()
    for h,body in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>',t,re.S):
        m=re.search(pat,h)
        if not m or h in seen: continue
        seen.add(h);ds=m.group(1);ti=clean(body).split(' Oct.')[0].split(' Nov.')[0]
        ti=re.sub(r"\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\. \d\d, \d{4}.*$",'',ti)
        out.append((dt.date(int(ds[:4]),int(ds[4:6]),int(ds[6:8])),ti,'https://www.nri.com'+h if h.startswith('/') else h))
    return out
def rss(nome,link,items):
    items=sorted(items,reverse=True)
    x=['<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>',f'<title>{escape(nome)}</title><link>{link}</link><description>{escape(nome)} (feed gerado a partir da pagina)</description>']
    for d,ti,h in items:
        x.append(f'<item><title>{escape(ti)}</title><link>{escape(h)}</link><guid>{escape(h)}</guid><pubDate>{d.strftime("%a, %d %b %Y 00:00:00 GMT")}</pubDate></item>')
    x.append('</channel></rss>');return '\n'.join(x)
def rieti():
    t=get('https://www.rieti.go.jp/en/rss/index.rdf');out=[];tot=0
    drop=('Symposiums','Workshops','Recent Activities','(Japanese)')
    K=re.compile(r'inflation|\byen\b|\bJGBs?\b|government bond|\bbonds?\b|interest rate|monetary|bank of japan|\bBOJ\b|central bank|fiscal|exchange rate|currenc|macroeconom|franc|oil price|tariff|\bwages?\b|current account|imbalances|\bFed\b|Balassa',re.I)
    for it in re.findall(r'<item .*?</item>',t,re.S):
        g=lambda p:(re.findall(p,it,re.S) or [''])[0]
        ti=clean(g(r'<title>(.*?)</title>'));ln=g(r'<link>(.*?)</link>').replace('http://','https://').replace('?ref=rss','');sj=clean(g(r'<dc:subject>(.*?)</dc:subject>'));d=g(r'<dc:date>(.*?)</dc:date>')[:10]
        tot+=1
        if any(x in sj for x in drop) or not K.search(ti) or not d: continue
        out.append((dt.date.fromisoformat(d),ti,ln))
    return out,tot
def daiwa():
    t=get('https://www.dir.co.jp/english/research/report/feed/rss.atom');out=[]
    for it in re.findall(r'<item>(.*?)</item>',t,re.S):
        g=lambda p:(re.findall(p,it,re.S) or [''])[0]
        ti=clean(re.sub(r'<!\[CDATA\[|\]\]>','',g(r'<title>(.*?)</title>')));ln=g(r'<link>(.*?)</link>').strip();pd=g(r'<pubDate>(.*?)</pubDate>').strip()
        try: d=dt.datetime.strptime(pd[:16],'%a, %d %b %Y').date()
        except ValueError: continue
        if ti and ln: out.append((d,ti,ln))
    return out
# minimos esperados: abaixo disso o feed antigo e preservado e o workflow falha (GitHub avisa por e-mail)
MIN={'jcer_en':6,'nri_kiuchi':50,'nri_finsights':50,'rieti_macro':10,'daiwa_en':5}
fontes={'jcer_en':('JCER (English)','https://www.jcer.or.jp/en',seguro(jcer)),
'nri_kiuchi':("Takahide Kiuchi's View (NRI)",'https://www.nri.com/en/media/journal/kiuchi',seguro(nri,'https://www.nri.com/en/media/journal/kiuchi',r'/kiuchi/(\d{8})\.html')),
'nri_finsights':('NRI Financial IT Focus / NRI FinSights','https://www.nri.com/en/media/column/nri_finsights',seguro(nri,'https://www.nri.com/en/media/column/nri_finsights',r'/nri_finsights/(\d{8})(?:_\d)?\.html'))}
try:
    r_it,r_tot=rieti();print('rieti bruto',r_tot)
    fontes['rieti_macro']=('RIETI (macro, filtrado por titulo)','https://www.rieti.go.jp/en/',r_it if r_tot>=100 else [])
except Exception as e:
    print('rieti erro',e);fontes['rieti_macro']=('RIETI (macro)','https://www.rieti.go.jp/en/',[])
try:
    fontes['daiwa_en']=('Daiwa Institute of Research (English reports)','https://www.dir.co.jp/english/research/report/',daiwa())
except Exception as e:
    print('daiwa erro',e);fontes['daiwa_en']=('Daiwa Institute of Research (English reports)','https://www.dir.co.jp/english/research/report/',[])
falhas=[]
for k,(n,l,it) in fontes.items():
    if len(it)<MIN[k]:
        falhas.append(f'{k}: {len(it)} itens < minimo {MIN[k]}');print('FALHA',falhas[-1]);continue
    open(f'docs/{k}.xml','w',encoding='utf-8').write(rss(n,l,it));print(k,len(it),'itens; mais recente:',max(it)[0],'|',max(it)[1][:70])
if falhas: raise SystemExit('Feeds com poucos itens (layout mudou?): '+'; '.join(falhas))
