import re
import glob
import os

files = glob.glob('templates/*.html')

bottom_nav = '''
<nav class="bottom-nav">
  <a class="bottom-nav-item active" href="/">
    <i>🔍</i>
    <span>HOME</span>
  </a>
  <a class="bottom-nav-item" href="/jd-match">
    <i>🎯</i>
    <span>JD MATCH</span>
  </a>
  <a class="bottom-nav-item" href="/market-trends">
    <i>📈</i>
    <span>TRENDS</span>
  </a>
  <a class="bottom-nav-item" href="/role-analyzer">
    <i>📊</i>
    <span>ANALYZE</span>
  </a>
</nav>
'''

css_add = '''
    /* BOTTOM NAV BAR */
    .bottom-nav {
      position: fixed; bottom: 0; left: 0; right: 0;
      background: rgba(10,10,15,0.95);
      backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
      border-top: 1px solid var(--border);
      display: flex; justify-content: space-around; align-items: center;
      padding: 12px 10px 24px; z-index: 9999;
    }
    .bottom-nav-item {
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      color: var(--text-muted); text-decoration: none; font-size: 9px;
      font-family: 'Space Mono', monospace; font-weight: 700;
      transition: all 0.2s; padding: 8px 16px; border-radius: 14px;
    }
    .bottom-nav-item i { font-size: 20px; font-style: normal; margin-bottom: 2px; }
    .bottom-nav-item.active { background: rgba(88,166,255,0.1); color: var(--accent); }
    .bottom-nav-item.active i { color: var(--accent); }
'''

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Remove Top Nav Tabs
    html = re.sub(r'<nav class="nav-tabs">.*?</nav>', '', html, flags=re.DOTALL)

    # 2. Add bottom nav if not already there
    if 'bottom-nav' not in html:
        # replace </body> with bottom_nav + </body>
        # Actually need to set 'active' dynamically per file, but for simplicity, we insert the block.
        # Let's fix active state later per file.
        # But first replace:
        html = html.replace('</body>', bottom_nav + '\n</body>')

    # 3. Add CSS for bottom nav
    if '.bottom-nav' not in html:
        html = html.replace('</style>', css_add + '\n  </style>')

    # 4. Remove AI text across all templates
    html = html.replace('GEMINI IS READING THE REPO', 'AI IS ANALYSING THE CODEBASE')
    html = html.replace('Gemini is analysing', 'AI is analysing')
    html = html.replace('Powered by Groq', 'Powered by Talent Engine')
    html = html.replace('Powered by Groq AI', 'Powered by Talent Engine')
    html = html.replace('Groq is analysing', 'AI is analysing')
    html = html.replace('Groq AI', 'AI Engine')
    html = html.replace('Powered by Gemini', 'Powered by Talent Engine')
    
    # 5. Modify body/main padding to avoid bottom nav overlap
    html = html.replace('main{', 'main{padding-bottom:100px; ')

    with open(file, 'w', encoding='utf-8') as f:
        f.write(html)

print("Applied Global UI changes to all HTML templates.")
