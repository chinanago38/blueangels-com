"""本文を、カード・アイコン付きの見出し・表・比べる表・流れの図・注意の箱・数字の箱に組み替える。
文は変えない・順も変えない。足すのは、本文にある語の短い見出し（tools/design/headings.json・段落の中の語だけ）と、飾り（SVG・class）だけ。"""
import hashlib, html, json, os, re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOID = {"area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# すでに形ができている部品の中は触らない
SKIP = {"cards", "gallery", "nextshow", "bars", "bar-row", "faq", "points", "steps", "sources", "page-hero", "tophero",
        "news-list", "ytcards", "ytbtns", "ns-list", "yt", "live-box", "crumb", "art", "chips", "cta"}

class Raw(str):
    """文字参照・コメント（字の置き換えの対象にしない）"""

class Node:
    def __init__(self, tag, start="", void=False):
        self.tag, self.start, self.void, self.kids = tag, start, void, []
    def classes(self):
        m = re.search(r'\sclass="([^"]*)"', self.start)
        return m.group(1).split() if m else []
    def add_class(self, *names):
        have = self.classes()
        new = " ".join(have + [n for n in names if n not in have])
        if re.search(r'\sclass="', self.start):
            self.start = re.sub(r'(\sclass=")[^"]*(")', lambda m: m.group(1) + new + m.group(2), self.start, count=1)
        else:
            self.start = self.start.replace("<" + self.tag, f'<{self.tag} class="{new}"', 1)
    def add_attr(self, name, value):
        self.start = re.sub(r"(/?>)$", lambda m: f' {name}="{html.escape(value, quote=True)}"' + m.group(1), self.start)
    def elements(self, tag=None):
        return [k for k in self.kids if isinstance(k, Node) and (tag is None or k.tag == tag)]
    def walk(self):
        for k in self.kids:
            if isinstance(k, Node):
                yield k
                yield from k.walk()
    def text(self):
        return "".join(k.text() if isinstance(k, Node) else ("" if k.startswith("<!") else html.unescape(k)) for k in self.kids if not (isinstance(k, Node) and k.tag in ("script", "style", "svg")))
    def inner(self):
        return "".join(k.out() if isinstance(k, Node) else k for k in self.kids)
    def out(self):
        if self.tag is None: return self.inner()
        return self.start + ("" if self.void else self.inner() + f"</{self.tag}>")

class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Node(None)
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        n = Node(tag, self.get_starttag_text(), tag in VOID)
        self.stack[-1].kids.append(n)
        if not n.void: self.stack.append(n)
    def handle_startendtag(self, tag, attrs):
        self.stack[-1].kids.append(Node(tag, self.get_starttag_text(), True))
    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return
    def handle_data(self, data): self.stack[-1].kids.append(data)
    def handle_entityref(self, name): self.stack[-1].kids.append(Raw(f"&{name};"))
    def handle_charref(self, name): self.stack[-1].kids.append(Raw(f"&#{name};"))
    def handle_comment(self, data): self.stack[-1].kids.append(Raw(f"<!--{data}-->"))

def parse(s):
    t = Tree(); t.feed(s); t.close()
    return t.root

def wrap(tag, cls, kids, attrs=""):
    n = Node(tag, f'<{tag} class="{cls}"{attrs}>')
    n.kids = list(kids)
    return n

PATHS = {
    "plane": "M2 13l8-2 4-8 2 1-2 7 7-1 1 2-7 3-1 6-2 1-2-6-6 0z",
    "ship": "M3 15h18l-2.5 5h-13zM6 15V9h5V5h3v4h4v6M4 22c2 0 2-1 4-1s2 1 4 1 2-1 4-1 2 1 4 1",
    "calendar": "M4 6h16v14H4zM4 10h16M8 3v5M16 3v5",
    "pin": "M12 21s7-6.2 7-11.5a7 7 0 10-14 0C5 14.8 12 21 12 21zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z",
    "chart": "M4 20V4M4 20h16M8 17v-5M12 17V8M16 17v-8",
    "yen": "M6 4l6 8 6-8M12 12v8M8 13h8M8 17h8",
    "cross": "M9 3h6v6h6v6h-6v6H9v-6H3V9h6z",
    "question": "M12 22a10 10 0 100-20 10 10 0 000 20zM9.2 9a3 3 0 115 2.2c-1.4 1-2.2 1.5-2.2 3M12 17.6v.1",
    "warn": "M12 3l10 18H2zM12 10v5M12 18v.1",
    "flow": "M5 3h6v5H5zM13 16h6v5h-6zM8 8v5h8v3",
    "people": "M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2.5 20a6.5 6.5 0 0113 0M17 11a3 3 0 000-6M18 14a6 6 0 014 6",
    "shield": "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
    "tool": "M14.5 6.5a4 4 0 005 5L11 20a2.1 2.1 0 01-3-3l8.5-8.5M14.5 6.5l3-3a5 5 0 00-6.5 6.5",
    "check": "M4 12.5l5 5L20 6.5",
    "mail": "M3 6h18v12H3zM3 7l9 6 9-6",
    "book": "M4 5h6a2 2 0 012 2v13a2 2 0 00-2-2H4zM20 5h-6a2 2 0 00-2 2v13a2 2 0 012-2h6z",
    "star": "M12 3l2.7 5.8 6.3.8-4.6 4.4 1.2 6.3L12 17.2 6.4 20.3l1.2-6.3L3 9.6l6.3-.8z",
}
RULES = [
    ("mail", r"連絡|問い合わせ|メール|お受け|お答え"), ("shield", r"プライバシー|個人情報|Cookie|広告|アクセス解析|著作権|免責"), ("book", r"出典|方針|運営|情報の|参考|訂正"),
    ("question", r"よくある|質問|ですか|FAQ"), ("warn", r"注意|気をつけ|気を付け|中止"),
    ("yen", r"費用|料金|金額|限度|高額|保険|支払"), ("cross", r"病院|手術|医療|治療|術|診療|入院"),
    ("calendar", r"日程|予定|スケジュール|歴史|歩み|年度|いつ|経緯|時期|季節|月"), ("pin", r"場所|行き方|基地|空港|会場|地域|国|日本|拠点|見に行"),
    ("chart", r"回数|数字|推移|データ|統計|内訳|多い|比べ"), ("flow", r"流れ|手順|しくみ|仕組み|決まり方|準備|方法|とは"),
    ("people", r"隊員|パイロット|チーム|人|乗員|メンバー|窓口|相談"), ("ship", r"空母|艦|海|打撃群"),
    ("plane", r"機|飛行|展示|航空|戦闘"), ("tool", r"整備|訓練|装備"), ("shield", r"防衛|安全|任務|自衛"),
]
def icon(name):
    return parse(f'<span class="dz-ic dz-ic-{name}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="{PATHS[name]}"/></svg></span>').kids[0]

def pick_icon(text, fallback="star"):
    for name, rx in RULES:
        if re.search(rx, text): return name
    return fallback

NUM = re.compile(r"(?<![0-9,.年月])((?:約)?[0-9][0-9,.]*(?:万|億)?(?:円|点|回|件|人|機|か月|か所|%|％|km|項目|例|隻|台|名))(?![0-9])")
def big_numbers(node):
    """数字を大きく見せる（字は足さない）。リンクの中は触らない"""
    out = []
    for k in node.kids:
        if isinstance(k, Node):
            if k.tag not in ("a", "script", "svg"): big_numbers(k)
            out.append(k)
        elif isinstance(k, Raw):
            out.append(k)
        else:
            for i, part in enumerate(NUM.split(k)):
                if not part: continue
                out.append(wrap("span", "dz-n", [part]) if i % 2 else part)
    node.kids = out

def do_table(t):
    if t.classes(): return
    rows = [n for n in t.walk() if n.tag == "tr"]
    cells = [[c for c in r.elements() if c.tag in ("th", "td")] for r in rows]
    if not rows or not cells[0]: return
    has_head = all(c.tag == "th" for c in cells[0]) and len(cells[0]) > 1
    kv = all(len(c) == 2 and c[0].tag == "th" and c[1].tag == "td" for c in cells)
    if kv and not has_head:
        t.add_class("dz-kv")
        for c in cells:
            if len(c[1].text()) <= 60: big_numbers(c[1])
        return
    t.add_class("dz-cmp")
    if has_head and len(cells[0]) >= 3:
        head = [c.text().strip() for c in cells[0]]
        lens = [len(c.text()) for r in cells[1:] for c in r]
        if lens and sum(lens) / len(lens) > 13:
            t.add_class("dz-stack")
            rows[0].add_class("dz-headrow")
            for r in cells[1:]:
                for i, c in enumerate(r):
                    if i < len(head): c.add_attr("data-label", head[i])
                    if i and len(c.text().strip()) <= 9: c.add_class("dz-s")

def split_label(li):
    """「名前：説明」の項目は、名前を見出しの形にする（「：」は残して見えなくする）"""
    first = next((k for k in li.kids if not (isinstance(k, str) and not k.strip())), None)
    if isinstance(first, Node) and first.tag == "strong":
        i = li.kids.index(first)
        first.add_class("dz-lb")
        if i + 1 < len(li.kids) and isinstance(li.kids[i + 1], str) and li.kids[i + 1].startswith("："):
            rest = li.kids[i + 1][1:]
            li.kids[i + 1:i + 2] = [wrap("span", "dz-co", ["："]), rest]
        return True
    if isinstance(first, str) and not isinstance(first, Raw) and "：" in first and 0 < first.index("：") <= 40:
        i = li.kids.index(first)
        a, b = first.split("：", 1)
        li.kids[i:i + 1] = [wrap("strong", "dz-lb", [a]), wrap("span", "dz-co", ["："]), b]
        return True
    return False

def do_list(ul, heading):
    if ul.classes(): return
    items = ul.elements("li")
    if not items or any(i.classes() for i in items): return
    if any(n.tag in ("ul", "ol") for i in items for n in i.walk()): return
    texts = [i.text().strip() for i in items]
    strong = all((i.elements() and i.elements()[0].tag == "strong" and i.text().strip().startswith(i.elements()[0].text().strip())) for i in items)
    colon = all("：" in x and x.index("：") <= 40 for x in texts)
    if re.search(r"チェック|持ち物|確かめること", heading) and ul.tag == "ul":
        for i in items:
            split_label(i); i.kids.insert(0, icon("check"))
        ul.add_class("dz-check")
    elif ul.tag == "ol":
        for i in items:
            if strong or colon: split_label(i)
            i.kids = [wrap("div", "dz-step", i.kids)]
        ul.add_class("dz-flow")
    elif (strong or colon) and len(items) >= 2:
        for i in items:
            if split_label(i):
                j = 0
                i.kids.insert(j, icon(pick_icon(i.text(), "check")))
        ul.add_class("dz-compare" if len(items) <= 3 and colon else "dz-tiles")
    elif len(items) >= 4 and max(len(x) for x in texts) <= 42:
        ul.add_class("dz-pills")
    else:
        for i in items:
            i.kids = [icon("check"), wrap("span", "dz-t", i.kids)]
        ul.add_class("dz-marks")

def sentences(p):
    """段落を「。」で区切る（かっこの中とタグの中では区切らない）"""
    out, cur, depth = [], [], 0
    for k in p.kids:
        if isinstance(k, Node) or isinstance(k, Raw):
            cur.append(k); continue
        buf = ""
        for ch in k:
            buf += ch
            if ch in "「（『(": depth += 1
            elif ch in "」）』)": depth = max(0, depth - 1)
            elif ch == "。" and depth == 0:
                cur.append(buf); out.append(cur); cur, buf = [], ""
        if buf: cur.append(buf)
    if cur: out.append(cur)
    return out

def length(parts):
    return sum(len(x.text()) if isinstance(x, Node) else len(html.unescape(x)) for x in parts)

def split_paragraph(p):
    if len(p.text()) <= 150 or p.classes(): return [p]
    chunks, cur = [], []
    for s in sentences(p):
        cur += s
        if length(cur) >= 70: chunks.append(cur); cur = []
    if cur:
        if chunks and length(cur) < 45: chunks[-1] += cur
        elif cur: chunks.append(cur)
    if len(chunks) < 2: return [p]
    out = []
    for c in chunks:
        n = Node("p", "<p>"); n.kids = c; out.append(n)
    return out

def key_of(text):
    return hashlib.md5(re.sub(r"\s+", "", text).encode("utf-8")).hexdigest()[:12]

def load_headings():
    f = os.path.join(ROOT, "tools", "design", "headings.json")
    if not os.path.exists(f): return {}
    return json.load(open(f, encoding="utf-8"))

CAUTION = re.compile(r"注意してください|気をつけ|気を付け|中止|変わることがあ|変更になる|変更されることがあ|確かめてください|確認してください|相談してください|ご相談ください")

def collect(heading, text):
    f = os.environ.get("DZ_COLLECT")
    if f: print(json.dumps({"k": key_of(text), "s": heading, "t": text}, ensure_ascii=False), file=open(f, "a", encoding="utf-8"))

def lead_blocks(root):
    """見出しの前にならぶ素の段落は、導入の箱にまとめる"""
    for box in [root] + [n for n in root.walk() if n.tag == "div" and "wrap" in n.classes()]:
        new, run = [], []
        def close():
            if run:
                kids = []
                for p in [x for x in run if isinstance(x, Node)]: kids += split_paragraph(p)
                new.append(wrap("div", "block lead-block", kids)); run.clear()
        for k in box.kids:
            if isinstance(k, Node) and k.tag == "p" and not k.classes(): run.append(k)
            elif run and isinstance(k, str) and not k.strip(): continue
            else: close(); new.append(k)
        close()
        box.kids = new

def do_section(sec, state):
    kids = [k for k in sec.kids if not (isinstance(k, str) and not k.strip())]
    h2 = next((k for k in kids if isinstance(k, Node) and k.tag == "h2"), None)
    heading = h2.text().strip() if h2 else ""
    if h2 and not h2.classes():
        name = pick_icon(heading)
        h2.add_class("dz-h2"); h2.kids = [icon(name), wrap("span", "dz-h2t", h2.kids)]
        state["n"] += 1
        sec.add_class("dz-sec", f"dz-tone{state['n'] % 3}")
    for n in list(sec.walk()):
        if set(n.classes()) & SKIP: continue
        if n.tag == "table": do_table(n)
    def lists(node):
        for n in node.elements():
            if set(n.classes()) & SKIP: continue
            if n.tag in ("ul", "ol"): do_list(n, heading)
            else: lists(n)
    lists(sec)
    h3s = sec.elements("h3")
    direct_p = [p for p in sec.elements("p") if not p.classes()]
    long_p = [p for p in direct_p if len(p.text()) >= 80]
    for p in direct_p:
        t = p.text()
        if state["caution"] < 3 and len(t) <= 200 and CAUTION.search(t):
            p.add_class("dz-caution"); p.kids = [icon("warn"), wrap("span", "dz-t", p.kids)]; state["caution"] += 1
    if len(h3s) >= 2:
        new, card, cards = [], None, []
        def close():
            if cards:
                short = all(len(c.text()) <= 330 and not any(n.tag == "table" for n in c.walk()) for c in cards)
                new.append(wrap("div", "dz-h3grid" + (" dz-two" if short else ""), cards))
                cards.clear()
        for k in sec.kids:
            if isinstance(k, Node) and k.tag == "h3":
                k.kids = [icon(pick_icon(k.text(), "star")), wrap("span", "dz-t", k.kids)]
                k.add_class("dz-h3")
                card = wrap("div", "dz-h3card", [k]); cards.append(card)
            elif isinstance(k, Node) and (set(k.classes()) & SKIP or k.tag in ("h2", "section")):
                close(); card = None; new.append(k)
            elif card is not None:
                card.kids += split_paragraph(k) if isinstance(k, Node) and k.tag == "p" else [k]
            else:
                new.append(k)
        close()
        sec.kids = new
        return
    new = []
    for k in sec.kids:
        if isinstance(k, Node) and k.tag == "p" and not k.classes():
            head = state["headings"].get(key_of(k.text()))
            parts = split_paragraph(k)
            if len(long_p) >= 2 and k in long_p:
                if head and head in k.text() and head not in state["used"] and head != heading:
                    state["used"].add(head)
                    h = wrap("p", "dz-gh", [icon(pick_icon(head, "star")), wrap("span", "dz-t", [html.escape(head)])], ' data-dz="add"')
                    new.append(wrap("div", "dz-pcard dz-has-h", [h] + parts))
                else:
                    collect(heading, k.text())
                    new.append(wrap("div", "dz-pcard", parts))
            else:
                new += parts
        else:
            new.append(k)
    sec.kids = new

def extra_photos(url, root, main):
    """写真が1枚も本文に無い面は、その面に割り当ててある2枚目より後の写真（picked.tsv）を節に置く"""
    f = os.path.join(ROOT, "tools", "photos", "picked.tsv")
    if "<img " in main or not os.path.exists(f): return
    rows = [c for c in (l.split("	") for l in open(f, encoding="utf-8").read().splitlines()[1:]) if len(c) >= 7 and c[0] == url and c[1].startswith("https://")]
    rows = [c for c in rows[1:] if c[1] not in main][:2]
    secs = [n for n in root.walk() if "dz-sec" in n.classes()]
    spots = [secs[i] for i in (1, 3) if i < len(secs)]
    for sec, row in zip(spots, rows):
        c = [html.escape(x) for x in row]
        fig = parse(f'<figure class="photo dz-photo" data-dz="add"><img src="{c[1]}" alt="{c[6]}の写真" loading="lazy" decoding="async">'
                    f'<figcaption>写真：{c[6]} {c[3]} / <a href="{c[5] or c[2]}" rel="noopener license" target="_blank">{c[4]}</a>'
                    f'（<a href="{c[2]}" rel="noopener" target="_blank">Wikimedia Commons</a>）</figcaption></figure>').kids[0]
        i = next((j + 1 for j, k in enumerate(sec.kids) if isinstance(k, Node) and k.tag == "h2"), 0)
        sec.kids.insert(i, fig)

def page_photo(url, root):
    """面に割り当てた写真（tools/design/photos.json）を、見出しの下に置く。出典は写真のすぐ下"""
    f = os.path.join(ROOT, "tools", "design", "photos.json")
    if not os.path.exists(f): return
    p = json.load(open(f, encoding="utf-8")).get(url)
    if not p: return
    e = {k: html.escape(v, quote=True) for k, v in p.items()}
    lic = f'<a href="{e["licenseUrl"]}" rel="noopener license" target="_blank">{e["license"]}</a>' if e.get("licenseUrl") else e["license"]
    fig = parse(f'<figure class="photo dz-photo" data-dz="add"><img src="{e["src"]}" alt="{e["alt"]}" loading="lazy" decoding="async">'
                f'<figcaption>写真：{e["author"]}／<a href="{e["page"]}" rel="noopener" target="_blank">Wikimedia Commons</a>（{lic}）</figcaption></figure>').kids[0]
    for box in [root] + list(root.walk()):
        for i, k in enumerate(box.kids):
            if isinstance(k, Node) and "page-hero" in k.classes():
                box.kids.insert(i + 1, fig); return
    box = next((n for n in root.walk() if "wrap" in n.classes()), root)
    i = next((j for j, k in enumerate(box.kids) if isinstance(k, Node) and k.tag == "section"), 0)
    box.kids.insert(i, fig)

def credit_html(e):
    v = {k: html.escape(str(e.get(k, "")), quote=True) for k in ("author", "license", "licenseUrl", "page")}
    lic = f'<a href="{v["licenseUrl"]}" rel="noopener license" target="_blank">{v["license"]}</a>' if v["licenseUrl"].startswith("http") else v["license"]
    return f'写真：{v["author"]}／<a href="{v["page"]}" rel="noopener" target="_blank">Wikimedia Commons</a>（{lic}）'

def curated_figure(e, cap=True):
    a = html.escape(e["alt"], quote=True)
    img = f'<img src="{html.escape(e["src"], quote=True)}" alt="{a}" loading="lazy" decoding="async">'
    return parse(f'<figure class="photo dz-photo" data-dz="add">{img}<figcaption>{a}　{credit_html(e)}</figcaption></figure>' if cap else f'<figure>{img}</figure>').kids[0]

def parent_of(root, node):
    for box in [root] + list(root.walk()):
        if node in box.kids: return box
    return None

def drop(root, node):
    p = parent_of(root, node)
    if p is not None: p.kids.remove(node)

def commons_photo(n):
    return n.tag == "figure" and any("wikimedia.org" in i.start for i in n.walk() if i.tag == "img")

def curate(url, root):
    """面ごとの写真を tools/design/curate.json のとおりにする（中身を1枚ずつ見て決めた表）。表にある面は、前の仕組みが置いた Commons の写真を全部外してから置く"""
    f = os.path.join(ROOT, "tools", "design", "curate.json")
    if not os.path.exists(f): return
    data = json.load(open(f, encoding="utf-8"))
    page = data.get(url)
    if page is None: return
    hero = next((n for n in root.walk() if "page-hero" in n.classes()), None)
    if "hero" in page and hero is not None:
        h = page["hero"]
        for k in [k for k in hero.kids if isinstance(k, Node) and "credit" in k.classes()]: hero.kids.remove(k)
        hero.start = re.sub(r'\sstyle="[^"]*"', "", hero.start).replace(" photo-hero", "")
        if h:
            hero.add_class("photo-hero")
            hero.add_attr("style", f'background-image:linear-gradient(180deg,rgba(6,22,44,.35),rgba(6,22,44,.88)),url({h["src"]})')
            hero.kids.append(parse(f'<p class="credit">{html.escape(h["alt"])}　{credit_html(h)}</p>').kids[0])
    for n in [n for n in root.walk() if commons_photo(n)]:
        drop(root, n)
    # 節の写真
    heads = [n for n in root.walk() if n.tag == "h2"]
    for e in page.get("sec", []):
        if e["head"] == "":
            box = parent_of(root, hero) if hero is not None else next((n for n in root.walk() if "wrap" in n.classes()), root)
            i = box.kids.index(hero) + 1 if hero is not None else 0
        else:
            h2 = next((n for n in heads if e["head"] in n.text()), None)
            if h2 is None: raise ValueError(f'{url}：見出し「{e["head"]}」が無い')
            box = parent_of(root, h2)
            i = box.kids.index(h2) + 1
        while i < len(box.kids) and isinstance(box.kids[i], Node) and "dz-photo" in box.kids[i].classes(): i += 1
        box.kids.insert(i, curated_figure(e))
    # ギャラリー（無くなったら節ごと外す）
    grids = [n for n in root.walk() if n.tag == "div" and "gallery" in n.classes()]
    gal = page.get("gallery", [])
    figs = []
    for e in gal:
        fig = curated_figure(e, cap=False)
        a = html.escape(e["alt"], quote=True)
        fig.kids.append(parse(f'<figcaption><b>{a}</b> {credit_html(e)}</figcaption>').kids[0])
        figs.append(fig)
    if figs:
        if grids:
            grids[0].kids = figs
        else:
            sec = parse(f'<section class="block dz-gal" data-dz="add"><h2>写真ギャラリー</h2><div class="gallery"></div></section>').kids[0]
            next(n for n in sec.walk() if "gallery" in n.classes()).kids = figs
            src = next((n for n in root.walk() if "sources" in n.classes() and n.tag == "section"), None)
            if src is None:
                next((n for n in root.walk() if "wrap" in n.classes()), root).kids.append(sec)
            else:
                box = parent_of(root, src)
                box.kids.insert(box.kids.index(src), sec)
    for g in grids[0 if not figs else 1:]:
        sec = parent_of(root, g)
        drop(root, sec if sec is not None and sec.tag == "section" else g)
    # 一覧のカードの写真（下の面とは別の写真）。出典は一覧のすぐ下
    cards = page.get("cards", {})
    if cards:
        for box in [n for n in root.walk() if n.tag == "div" and "cards" in n.classes()]:
            used = []
            for a in box.elements("a"):
                m = re.search(r'\shref="([^"]*)"', a.start)
                e = cards.get(m.group(1)) if m else None
                img = next((k for k in a.elements("img")), None)
                if img is not None: a.kids.remove(img)
                a.start = a.start.replace(" has-thumb", "")
                if e:
                    a.add_class("has-thumb")
                    a.kids.insert(0, parse(f'<img class="thumb" src="{html.escape(e["src"], quote=True)}" alt="{html.escape(e["alt"], quote=True)}" loading="lazy">').kids[0])
                    used.append(e)
            if used:
                lines = "".join(f'<li>{html.escape(e["alt"])}　{credit_html(e)}</li>' for e in used)
                p = parent_of(root, box)
                p.kids.insert(p.kids.index(box) + 1, parse(f'<details class="dz-credits" data-dz="add"><summary>一覧の写真の出典</summary><ul>{lines}</ul></details>').kids[0])

def apply(url, main):
    root = parse(main)
    state = {"n": 0, "caution": 0, "headings": load_headings(), "used": set()}
    for n in list(root.walk()):
        c = n.classes()
        if n.tag == "section" and "block" in c and not (set(c) & SKIP):
            do_section(n, state)
        elif n.tag == "div" and "lead-block" in c:
            ps = [p for p in n.elements("p") if not p.classes()]
            if ps:
                kids = []
                for k in n.kids:
                    kids += split_paragraph(k) if k in ps else [k]
                n.kids = kids
    lead_blocks(root)
    extra_photos(url, root, main)
    page_photo(url, root)
    curate(url, root)
    return root.out()
