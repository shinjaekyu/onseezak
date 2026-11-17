#!/usr/bin/env python3
"""오늘시작 공홈 FAQ 문항 추가 도구 (완성된 HTML을 직접 고칩니다).

사용법 (저장소 onseezak 폴더 안에서 실행):
  python3 faq_add.py <주제> "<질문>" "<문단1>" ["<문단2>" ...] [--src "근거 문구"] [--date 2026-11-17]

주제: wear size care daily warn men repair buy area concern special material cost
하는 일: 주제 페이지에 문항 추가(번호 자동), 검색엔진용 FAQ 데이터, 주제별 문항 수,
        전체 문항 수(○○가지), FAQ 첫 화면 목록, llms.txt, 수정일, sitemap 날짜를 함께 고칩니다.
끝나면 qa.js로 점검하고, 대표가 "올려"라고 한 뒤에만 commit·push 합니다.
"""
import re, json, glob, html, sys, argparse, datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cat'); ap.add_argument('q'); ap.add_argument('paras', nargs='+')
    ap.add_argument('--src', default=None); ap.add_argument('--date', default=str(datetime.date.today()))
    a = ap.parse_args()
    src = a.src or f'오늘시작 운영 기준({a.date[:7]} 확인)'
    esc = lambda t: html.escape(t, quote=True)
    pages = glob.glob('**/*.html', recursive=True)
    F = {p: open(p, encoding='utf-8').read() for p in pages}
    for x in ('llms.txt', 'rss.xml', 'sitemap.xml'):
        F[x] = open(x, encoding='utf-8').read()
    idx, page = 'faq/index.html', f'faq/{a.cat}/index.html'
    assert page in F, f'주제 없음: {a.cat}'
    nums = [int(n) for p in F if p.startswith('faq/') for n in re.findall(r'<details class="faq__item" id="q(\d+)"', F[p])]
    n, total = max(nums) + 1, len(nums)
    m = re.search(rf'<section class="faq-idx__sec" id="{a.cat}"><h2><a href="/faq/{a.cat}/">([^<]*)</a><span>(\d+)</span>', F[idx])
    label, cnt = m.group(1), int(m.group(2))
    # 1) 주제 페이지
    s = F[page]
    item = (f'<details class="faq__item" id="q{n}" data-q="{esc(a.q)}"><summary><span class="faq__num">Q{n}</span>'
            f'<h3 class="faq__q">{esc(a.q)}</h3></summary><div class="faq__a">'
            + ''.join(f'<p>{esc(x)}</p>' for x in a.paras)
            + f'<p class="faq__src"><b>근거</b> {esc(src)}</p></div></details>')
    k = s.rfind('</details></div>'); assert k > 0
    s = s[:k + 10] + item + s[k + 10:]
    mm = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    ld = json.loads(mm.group(1))
    for x in ld:
        if x.get('@type') == 'FAQPage':
            x['mainEntity'].append({"@type": "Question", "name": a.q,
                                    "acceptedAnswer": {"@type": "Answer", "text": ' '.join(a.paras)}})
        if x.get('@type') == 'WebPage' and 'dateModified' in x:
            x['dateModified'] = a.date
    s = s[:mm.start(1)] + json.dumps(ld, ensure_ascii=False) + s[mm.end(1):]
    s = s.replace(f'{cnt}문항', f'{cnt+1}문항')
    s = re.sub(r'수정 \d{4}-\d{2}-\d{2}', f'수정 {a.date}', s)
    F[page] = s
    # 2) llms.txt 주제 줄
    lines = F['llms.txt'].split('\n')
    for i, l in enumerate(lines):
        if f'](https://onseezak.com/faq/{a.cat}/)' in l:
            lines[i] = l.replace(f'{cnt}문항', f'{cnt+1}문항')
    F['llms.txt'] = '\n'.join(lines)
    # 3) 모든 페이지의 주제 메뉴 숫자
    a1 = f'<a href="/faq/{a.cat}/">{label}<span>{cnt}</span>'
    b1 = f'<a href="/faq/{a.cat}/">{label}</a><span>{cnt}</span>'
    for p in pages:
        F[p] = F[p].replace(a1, a1.replace(f'<span>{cnt}<', f'<span>{cnt+1}<')).replace(b1, b1.replace(f'<span>{cnt}<', f'<span>{cnt+1}<'))
    # 4) FAQ 첫 화면 목록
    t = F[idx]; sec = t.find(f'<section class="faq-idx__sec" id="{a.cat}">'); e = t.find('</ul>', sec)
    t = t[:e] + f'<li class="faq-idx__q" data-q="{esc(a.q)}"><a href="/faq/{a.cat}/#q{n}"><span class="faq__num">Q{n}</span>{esc(a.q)}</a></li>' + t[e:]
    t = re.sub(r'수정 \d{4}-\d{2}-\d{2}', f'수정 {a.date}', t)
    F[idx] = t
    # 5) 전체 문항 수
    for p in F:
        F[p] = F[p].replace(f'{total}가지', f'{total+1}가지').replace(f'{total}개 질문', f'{total+1}개 질문')
    # 6) sitemap 날짜
    for u in ('faq/', f'faq/{a.cat}/'):
        F['sitemap.xml'] = re.sub(rf'(<loc>https://onseezak\.com/{u}</loc><lastmod>)\d{{4}}-\d{{2}}-\d{{2}}', rf'\g<1>{a.date}', F['sitemap.xml'])
    # 검증 후 저장
    for p, t in F.items():
        for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
            json.loads(j)
        open(p, 'w', encoding='utf-8').write(t)
    print(f'추가: Q{n} → /faq/{a.cat}/#q{n} | {label} {cnt}→{cnt+1}문항 | 전체 {total}→{total+1}가지')

if __name__ == '__main__':
    main()
