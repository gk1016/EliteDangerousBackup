import re
import tkinter as tk
import tkinter.font as tkfont

def render_markdown(text_widget: tk.Text, md: str):
    text_widget.config(state="normal")
    text_widget.delete("1.0", "end")

    base = tkfont.nametofont("TkDefaultFont")
    h1 = tkfont.Font(family=base.cget("family"), size=base.cget("size")+6, weight="bold")
    h2 = tkfont.Font(family=base.cget("family"), size=base.cget("size")+3, weight="bold")
    codef = tkfont.Font(family="Consolas", size=base.cget("size"))

    text_widget.tag_configure("h1", font=h1, spacing1=8, spacing3=6)
    text_widget.tag_configure("h2", font=h2, spacing1=6, spacing3=4)
    text_widget.tag_configure("p", spacing1=2, spacing3=6)
    text_widget.tag_configure("li", lmargin1=24, lmargin2=24, spacing3=2)
    text_widget.tag_configure("code", font=codef)
    text_widget.tag_configure("codeblock", font=codef, background="#f5f5f5",
                              lmargin1=12, lmargin2=12, spacing1=4, spacing3=6)
    text_widget.tag_configure("hr", spacing1=8, spacing3=8)

    lines = md.splitlines()
    i = 0
    in_code = False
    code_buf = []
    inline_code_re = re.compile(r"`([^`]+)`")

    def flush_codeblock():
        if code_buf:
            text_widget.insert("end", "\n".join(code_buf) + "\n", ("codeblock",))
            code_buf.clear()

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                in_code = False
                flush_codeblock()
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line); i += 1; continue

        if line.strip() == "---":
            text_widget.insert("end", "────────────────────────────────\n", ("hr",))
            i += 1; continue

        if line.startswith("# "):
            text_widget.insert("end", line[2:].strip() + "\n", ("h1",)); i += 1; continue
        if line.startswith("## "):
            text_widget.insert("end", line[3:].strip() + "\n", ("h2",)); i += 1; continue

        stripped = line.lstrip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
            pos = 0
            while True:
                m = inline_code_re.search(content, pos)
                if not m:
                    text_widget.insert("end", "• " + content[pos:] + "\n", ("li",)); break
                if m.start() > pos:
                    text_widget.insert("end", "• " + content[pos:m.start()], ("li",))
                text_widget.insert("end", m.group(1), ("li", "code"))
                pos = m.end()
                if pos >= len(content):
                    text_widget.insert("end", "\n", ("li",)); break
            i += 1; continue

        if stripped.startswith("> "):
            text_widget.insert("end", stripped + "\n", ("p",)); i += 1; continue

        if not line.strip():
            text_widget.insert("end", "\n", ("p",)); i += 1; continue

        content = line; last = 0
        while True:
            m = inline_code_re.search(content, last)
            if not m:
                text_widget.insert("end", content[last:] + "\n", ("p",)); break
            if m.start() > last:
                text_widget.insert("end", content[last:m.start()], ("p",))
            text_widget.insert("end", m.group(1), ("p", "code"))
            last = m.end()
        i += 1

    text_widget.config(state="disabled")
