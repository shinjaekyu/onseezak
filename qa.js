// 배포 전 점검: 화면 넘침, 큰 제목(H1) 1개, 구조화 데이터(JSON-LD) 정상 여부
// 사용법: 저장소 폴더에서 `python3 -m http.server 8765 &` 실행 후
//         node qa.js /faq/ /faq/repair/ /ja/   (점검할 주소를 나열)
const { chromium } = require('playwright');
(async () => {
  const paths = process.argv.slice(2); if (!paths.length) paths.push('/');
  const b = await chromium.launch(); let bad = 0;
  for (const path of paths) for (const w of [320, 375, 1280]) {
    const p = await b.newPage({ viewport: { width: w, height: 800 } });
    await p.goto('http://localhost:8765' + path, { waitUntil: 'domcontentloaded' });
    const r = await p.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > innerWidth,
      h1: document.querySelectorAll('h1').length,
      ld: [...document.querySelectorAll('script[type="application/ld+json"]')].every(s => { try { JSON.parse(s.textContent); return true } catch (e) { return false } })
    }));
    const ok = !r.overflow && r.h1 === 1 && r.ld; if (!ok) bad++;
    console.log(ok ? '통과' : '지적', path, w + 'px', JSON.stringify(r));
    await p.close();
  }
  await b.close(); process.exit(bad ? 1 : 0);
})();
