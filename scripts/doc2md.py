"""把资料库导出的组件化 XML 转成干净 Markdown。

原始格式是 HTML 风格的组件树（标签有裸属性如 `readonly rowHeader`，
不是合法 XML），所以用 html.parser 建树再递归渲染。
只处理本项目实际用到的组件。
"""
import re
import sys
from html.parser import HTMLParser

VOID = {"divider", "br", "hr"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parts")

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []
        # parts 按文档顺序混装字符串与子节点，raw_text 才能正确拼接
        self.parts = []

    def append_text(self, s):
        self.parts.append(s)

    def append_child(self, n):
        self.parts.append(n)
        self.children.append(n)

    def raw_text(self):
        out = []
        for p in self.parts:
            if isinstance(p, str):
                out.append(p)
            else:
                out.append(p.raw_text())
        return "".join(out)

    def get(self, k, d=None):
        return self.attrs.get(k, d)


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict(attrs))
        self.stack[-1].append_child(n)
        if tag.lower() not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, dict(attrs))
        self.stack[-1].append_child(n)

    def handle_endtag(self, tag):
        if tag.lower() in VOID:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag.lower() == tag.lower():
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].append_text(data)


def clean(s):
    s = s.replace("\\_", "_").replace("\\*", "*").replace("\\`", "`")
    s = s.replace("\\<", "<").replace("\\>", ">")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


LIST_TAGS = {"bulletedlist", "numberedlist"}


def render(node, out):
    for ch in node.children:
        render_node(ch, out)


def render_node(el, out):
    t = el.tag

    if t == "heading":
        lvl = int(el.get("level", "2"))
        out.append("")
        out.append("#" * lvl + " " + clean(el.raw_text()))
        out.append("")

    elif t == "paragraph":
        s = clean(el.raw_text())
        if s:
            out.append(s)
            out.append("")

    elif t == "code":
        lang = el.get("language", "")
        body = el.raw_text()
        ls = body.split("\n")
        while ls and not ls[0].strip():
            ls.pop(0)
        while ls and not ls[-1].strip():
            ls.pop()
        ind = [len(x) - len(x.lstrip()) for x in ls if x.strip()]
        pad = min(ind) if ind else 0
        body = "\n".join(x[pad:] if len(x) >= pad else x.lstrip() for x in ls)
        body = re.sub(r"^\s*```[a-z]*\s*\n?", "", body)
        body = re.sub(r"\n?```\s*$", "", body)
        # 逐行去公共缩进后，整体再左移（XML 里内容比 fence 多缩进 2 空格）
        body = "\n".join(x.lstrip() if not x.strip() else x for x in body.split("\n"))
        out.append("```" + lang)
        out.append(body.rstrip())
        out.append("```")
        out.append("")

    elif t == "divider":
        out.append("---")
        out.append("")

    elif t == "blockquote":
        sub = []
        render(el, sub)
        parts = [x for x in sub if x.strip()]
        if parts:
            out.append("")
            out.append("> " + "\n> ".join(x for x in parts if x.strip()))
            out.append("")

    elif t == "table":
        rows = []
        for tr in el.children:
            if tr.tag.lower() != "tablerow":
                continue
            cells = []
            for tc in tr.children:
                if tc.tag.lower() != "tablecell":
                    continue
                sub = []
                render(tc, sub)
                cells.append(" ".join(x.strip() for x in sub if x.strip()))
            rows.append(cells)
        if not rows:
            return
        w = max(len(r) for r in rows)
        rows = [r + [""] * (w - len(r)) for r in rows]
        out.append("")
        out.append("| " + " | ".join(x.replace("|", "\\|") for x in rows[0]) + " |")
        out.append("|" + "|".join([" --- "] * w) + "|")
        for r in rows[1:]:
            out.append("| " + " | ".join(x.replace("|", "\\|") for x in r) + " |")
        out.append("")

    elif t in LIST_TAGS:
        ordered = t == "NumberedList"
        n = 0
        for li in el.children:
            if li.tag.lower() != "listitem":
                continue
            sub = []
            render(li, sub)
            parts = [x.rstrip() for x in sub if x.strip()]
            if not parts:
                continue
            n += 1
            marker = f"{n}. " if ordered else "- "
            out.append(marker + parts[0].strip())
            pad = " " * len(marker)
            for r in parts[1:]:
                if r.startswith("|"):
                    out.append(pad + r)
                elif r.startswith("```"):
                    out.append(r)
                elif re.match(r"^(---+)$", r):
                    out.append(r)
                else:
                    out.append(pad + r.strip())
        out.append("")

    else:
        render(el, out)


def main():
    raw = open(sys.argv[1], encoding="utf-8").read()
    raw = raw.split("\nKS_DOC_REPLY")[0].split("\nKS_DOC_REVIEWS")[0]
    raw = re.sub(r"\A---\n.*?\n---\n", "", raw, flags=re.S)

    b = Builder()
    b.feed(raw)
    out = []
    render(b.root, out)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    print(text.strip())


if __name__ == "__main__":
    main()
