"""Gera RSS a partir de paginas sem feed: JCER (ingles) e NRI (Kiuchi's View, NRI Finsights).
Uso: python3 code/27_feeds_jcer_nri.py  -> docs/jcer_en.xml, nri_kiuchi.xml, nri_finsights.xml
Sem dependencias alem de requests. Rodar de tempos em tempos; o leitor (Inoreader) precisa de uma URL publica."""
import requests,re,html,datetime as dt
from xml.sax.saxutils import escape
H={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
HOJE=dt.date.today()
def get(u): return requests.get(u,headers=H,timeout=30).text
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
fontes={'jcer_en':('JCER (English)','https://www.jcer.or.jp/en',jcer()),
'nri_kiuchi':("Takahide Kiuchi's View (NRI)",'https://www.nri.com/en/media/journal/kiuchi',nri('https://www.nri.com/en/media/journal/kiuchi',r'/kiuchi/(\d{8})\.html')),
'nri_finsights':('NRI Financial IT Focus / NRI FinSights','https://www.nri.com/en/media/column/nri_finsights',nri('https://www.nri.com/en/media/column/nri_finsights',r'/nri_finsights/(\d{8})(?:_\d)?\.html'))}
for k,(n,l,it) in fontes.items():
    open(f'docs/{k}.xml','w',encoding='utf-8').write(rss(n,l,it));print(k,len(it),'itens; mais recente:',max(it)[0] if it else None, '|', max(it)[1][:70] if it else '')
