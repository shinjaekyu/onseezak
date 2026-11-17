#!/usr/bin/env python3
"""오늘시작 공홈 부위별 가이드 글 추가 도구 (완성된 HTML을 직접 만듭니다).

사용법 (저장소 onseezak 폴더 안에서 실행):
  python3 guide_add.py <글.json> [--date 2026-11-17]

글.json 키: slug, area(예: '상체'), read(예: '5분'), title, desc, summary[3], img, img_alt,
            sections[[소제목,[문단...]],...], related[제품 slug...], faq[문항 번호...]
틀: guide/full-body-liposuction-garment/index.html 을 복사해 내용만 바꿉니다.
함께 고치는 곳: /guide/ 목록과 부위 버튼, /guide/area/ 모음, sitemap.xml, llms.txt, rss.xml
"""
import re, json, glob, html, sys, os, argparse, datetime, email.utils

USER_SITES = ('cashdoc', 'danawa', 'realself', 'reddit', 'cafe.naver', 'blog.naver', 'babitalk', 'gangnamunni')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('json'); ap.add_argument('--date', default=str(datetime.date.today()))
    a = ap.parse_args(); A = json.load(open(a.json, encoding='utf-8')); D = a.date
    esc = lambda t: html.escape(t, quote=False); escq = lambda t: html.escape(t, quote=True)
    T_SLUG = 'full-body-liposuction-garment'
    s = open(f'guide/{T_SLUG}/index.html', encoding='utf-8').read()
    slug, title, desc = A['slug'], A['title'], A['desc']
    url = f'https://onseezak.com/guide/{slug}/'; img = f"/assets/img/{A['img']}"
    assert os.path.exists('.' + img), img
    # 관련 FAQ
    faqs = {}
    for p in glob.glob('faq/*/index.html'):
        t = open(p, encoding='utf-8').read()
        for m in re.finditer(r'<details class="faq__item" id="q(\d+)" data-q="([^"]*)">.*?<div class="faq__a">(.*?)</div></details>', t, re.S):
            faqs[int(m.group(1))] = (m.group(2), m.group(3))
    mini, cites = [], []
    for n in A['faq']:
        q, body = faqs[n]
        src = re.search(r'<p class="faq__src">.*?</p>', body, re.S)
        if src:
            for href, name in re.findall(r'<a href="([^"]+)"[^>]*>([^<]*)</a>', src.group(0)):
                if href not in [c[0] for c in cites]: cites.append((href, name))
            body = body.replace(src.group(0), '')
        body = re.sub(r'href="#q(\d+)"', lambda m: f'href="/faq/#q{m.group(1)}"', body)
        mini.append(f'<details><summary>{q}</summary>{body}</details>')
    inst = [c for c in cites if not any(u in c[0] for u in USER_SITES)]
    user = [c for c in cites if any(u in c[0] for u in USER_SITES)]
    li = lambda cs: ''.join(f'<li><a href="{h}" target="_blank" rel="noopener nofollow">{n}</a></li>' for h, n in cs)
    refs = (f'<section class="refs" aria-labelledby="refs-title"><h2 id="refs-title">참고 자료</h2><p class="refs__lead">이 페이지의 내용은 아래 공개 자료 {len(cites)}건을 바탕으로 정리했습니다. '
            '국내 의료기관이 공개한 환자 안내문도 함께 확인했으며, 의료광고로 오해받지 않도록 기관명은 적지 않았습니다. '
            + ('이용자 경험담은 실제로 겪는 불편을 파악하는 데만 참고했습니다. ' if user else '')
            + '자료는 최신 수정일 기준으로 확인했고, 내용은 바뀔 수 있습니다.</p>'
            + f'<h3 class="refs__h">의료기관·학회·공공기관·전문 매체·논문·법령 {len(inst)}건</h3><ol>{li(inst)}</ol>'
            + (f'<h3 class="refs__h">이용자 경험담(참고용) {len(user)}건</h3><ol>{li(user)}</ol>' if user else '') + '</section>')
    # 관련 제품 카드: 다른 가이드에 있는 카드를 가져옴
    cards = {}
    for p in glob.glob('guide/*/index.html'):
        for m in re.finditer(r'<li class="pcard"><a class="pcard__link" href="/product/([a-z0-9-]+)/">.*?</a></li>', open(p, encoding='utf-8').read(), re.S):
            cards.setdefault(m.group(1), m.group(0))
    missing = [r for r in A['related'] if r not in cards]; assert not missing, f'제품 카드 없음: {missing}'
    rel = ''.join(cards[r] for r in A['related'])
    # 본문
    toc = ''.join(f'<li><a href="#s{i}">{esc(h)}</a></li>' for i, (h, _) in enumerate(A['sections'], 1))
    secs = ''.join(f'<section id="s{i}" class="art__sec"><h2>{esc(h)}</h2>' + ''.join(f'<p>{esc(p)}</p>' for p in ps) + '</section>' for i, (h, ps) in enumerate(A['sections'], 1))
    summ = ''.join(f'<li>{esc(x)}</li>' for x in A['summary'])
    def sub(pat, rep, text, count=1, flags=re.S):
        new, n = re.subn(pat, lambda m: rep, text, count=count, flags=flags); assert n, pat; return new
    # head
    old_title = re.search(r'<title>(.*?) \| 오늘시작 압박복</title>', s).group(1)
    old_desc = re.search(r'<meta name="description" content="([^"]*)">', s).group(1)
    old_img = re.search(r'<meta property="og:image" content="https://onseezak.com([^"]*)">', s).group(1)
    s = s.replace(f'/guide/{T_SLUG}/', f'/guide/{slug}/')
    s = sub(r'<meta property="article:modified_time" content="[^"]*">', f'<meta property="article:modified_time" content="{D}">', s)
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S); ld = json.loads(m.group(1))
    for x in ld:
        if x.get('@type') == 'WebPage': x['name'] = title; x['dateModified'] = D
        if x.get('@type') == 'BreadcrumbList': x['itemListElement'][-1]['name'] = title
        if x.get('@type') == 'Article':
            x.update(headline=title, description=A['summary'][0], image='https://onseezak.com' + img, dateModified=D, datePublished=D, citation=[c[0] for c in cites])
    s = s[:m.start(1)] + json.dumps(ld, ensure_ascii=False) + s[m.end(1):]
    head_end = s.find('</head>'); head, body = s[:head_end], s[head_end:]
    head = head.replace(escq(old_title), escq(title)).replace(old_title, escq(title)).replace(old_desc, escq(desc)).replace(old_img, img)
    # body
    body = sub(r'<p class="art__eyebrow">.*?</p>', f'<p class="art__eyebrow">부위별 · 읽는 시간 {A["read"]}</p>', body)
    body = sub(r'<h1 class="art__title">.*?</h1>', f'<h1 class="art__title">{esc(title)}</h1>', body)
    body = sub(r'(<p class="art__summary-label">3줄 요약</p><ul>).*?(</ul>)', f'<p class="art__summary-label">3줄 요약</p><ul>{summ}</ul>', body)
    body = sub(r'최신 수정 \d{4}-\d{2}-\d{2} · 글쓴이', f'최신 수정 {D} · 글쓴이', body)
    body = sub(r'(<aside class="art__toc" aria-label="목차"><p>목차</p><ol>).*?(</ol>)', f'<aside class="art__toc" aria-label="목차"><p>목차</p><ol>{toc}</ol>', body)
    body = sub(r'<figure class="art__fig">.*?</figure>', f'<figure class="art__fig"><img src="{img}" alt="{escq(A["img_alt"])}" width="900" height="1200" loading="lazy"></figure>', body)
    body = sub(r'<section id="s1" class="art__sec">.*?</section>(?=\s*<aside class="art__notice">)', secs, body)
    body = sub(r'(<div class="faqmini">).*?(<a class="btn btn--secondary btn--sm" href="/faq/")', '<div class="faqmini">' + ''.join(mini) + '<a class="btn btn--secondary btn--sm" href="/faq/"', body)
    body = sub(r'<section class="refs".*?</section>', refs, body)
    body = sub(r'(<ul class="rel__grid">).*?(</ul>)', f'<ul class="rel__grid">{rel}</ul>', body)
    out = head + body
    for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>', out, re.S): json.loads(j)
    os.makedirs(f'guide/{slug}', exist_ok=True); open(f'guide/{slug}/index.html', 'w', encoding='utf-8').write(out)
    # 목록·모음
    card = lambda thumb: (f'<li><a class="ghub__card" href="/guide/{slug}/"><div class="ghub__thumb"><img src="{img}" alt="" width="900" height="1200" loading="lazy"></div>'
            f'<div class="ghub__body"><p class="ghub__meta">{A["area"]} · {A["read"]}</p><h2 class="ghub__title">{esc(title)}</h2><p class="ghub__desc">{esc(A["summary"][0])}</p><span class="ghub__more">읽기 →</span></div></a></li>')
    for p in ('guide/index.html', 'guide/area/index.html'):
        t = open(p, encoding='utf-8').read()
        k = t.find(f'<a class="ghub__card" href="/guide/{T_SLUG}/">'); assert k > 0, p
        e = t.find('</a></li>', k) + len('</a></li>'); t = t[:e] + card(img) + t[e:]
        chip = f'<li><a class="chip ghub-area__chip" href="/guide/{T_SLUG}/">전신</a></li>'
        t = t.replace(chip, chip + f'<li><a class="chip ghub-area__chip" href="/guide/{slug}/">{A["area"]}</a></li>')
        t = re.sub(r'(ghub__updated">최신 수정 )\d{4}-\d{2}-\d{2}', rf'\g<1>{D}', t)
        mm = re.search(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
        if mm:
            l2 = json.loads(mm.group(1))
            for x in l2:
                if x.get('@type') == 'WebPage' and 'dateModified' in x: x['dateModified'] = D
            t = t[:mm.start(1)] + json.dumps(l2, ensure_ascii=False) + t[mm.end(1):]
        open(p, 'w', encoding='utf-8').write(t)
    # sitemap, llms, rss
    t = open('sitemap.xml', encoding='utf-8').read()
    line = re.search(rf'<url><loc>https://onseezak\.com/guide/{T_SLUG}/</loc>.*?</url>\n?', t).group(0)
    t = t.replace(line, line + line.replace(T_SLUG, slug).replace(re.search(r'<lastmod>(.*?)</lastmod>', line).group(1), D))
    for u in ('guide/', 'guide/area/'):
        t = re.sub(rf'(<loc>https://onseezak\.com/{u}</loc><lastmod>)\d{{4}}-\d{{2}}-\d{{2}}', rf'\g<1>{D}', t)
    open('sitemap.xml', 'w', encoding='utf-8').write(t)
    t = open('llms.txt', encoding='utf-8').read()
    line = [x for x in t.split('\n') if f'/guide/{T_SLUG}/)' in x][0]
    t = t.replace(line, line + f'\n- [{title} | 오늘시작 압박복]({url}): {desc}')
    open('llms.txt', 'w', encoding='utf-8').write(t)
    t = open('rss.xml', encoding='utf-8').read()
    pub = email.utils.format_datetime(datetime.datetime.fromisoformat(D + 'T09:00:00+09:00'))
    item = re.search(rf'<item><title>[^<]*</title><link>https://onseezak\.com/guide/{T_SLUG}/</link>.*?</item>\n?', t, re.S).group(0)
    new = f'<item><title>{esc(title)} | 오늘시작 압박복</title><link>{url}</link><guid isPermaLink="true">{url}</guid><description>{esc(desc)}</description><pubDate>{pub}</pubDate></item>\n'
    t = t.replace(item, item + new); t = re.sub(r'<lastBuildDate>[^<]*', f'<lastBuildDate>{pub}', t)
    open('rss.xml', 'w', encoding='utf-8').write(t)
    print(f'추가: /guide/{slug}/ | 관련 FAQ {len(mini)} | 참고 자료 {len(cites)}(기관 {len(inst)}, 경험담 {len(user)}) | 제품 카드 {len(A["related"])}')

if __name__ == '__main__':
    main()
