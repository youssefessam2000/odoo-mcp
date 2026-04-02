import re
import sys
from fpdf import FPDF, XPos, YPos

class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def clean(text):
    # Remove markdown symbols we handle manually
    return text.strip()


def sanitize(text):
    """Replace unicode characters unsupported by built-in fonts."""
    replacements = {
        "\u2014": "-",    # em dash
        "\u2013": "-",    # en dash
        "\u2019": "'",    # right single quote
        "\u2018": "'",    # left single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2022": "*",    # bullet
        "\u2192": "->",   # right arrow
        "\u2190": "<-",   # left arrow
        "\u2191": "^",    # up arrow
        "\u2193": "v",    # down arrow
        "\u25bc": "v",    # downward triangle
        "\u25b2": "^",    # upward triangle
        "\u25ba": ">",    # right triangle
        "\u25c4": "<",    # left triangle
        "\u2500": "-",    # box horizontal
        "\u2502": "|",    # box vertical
        "\u251c": "+",    # box left tee
        "\u2524": "+",    # box right tee
        "\u252c": "+",    # box top tee
        "\u2534": "+",    # box bottom tee
        "\u2514": "+",    # box bottom-left
        "\u2510": "+",    # box top-right
        "\u250c": "+",    # box top-left
        "\u2518": "+",    # box bottom-right
        "\u253c": "+",    # box cross
        "\u2588": "#",    # full block
        "\u2550": "=",    # double horizontal
        "\u2554": "+",    # double top-left
        "\u2557": "+",    # double top-right
        "\u255a": "+",    # double bottom-left
        "\u255d": "+",    # double bottom-right
        "\u2560": "+",    # double left tee
        "\u2563": "+",    # double right tee
        "\u2566": "+",    # double top tee
        "\u2569": "+",    # double bottom tee
        "\u256c": "+",    # double cross
        "\u2501": "-",    # heavy horizontal
        "\u2503": "|",    # heavy vertical
        "\u2517": "+",    # heavy bottom-left
        "\u251b": "+",    # heavy bottom-right
        "\u250f": "+",    # heavy top-left
        "\u2513": "+",    # heavy top-right
        "\u2523": "+",    # heavy left tee
        "\u252b": "+",    # heavy right tee
        "\u2533": "+",    # heavy top tee
        "\u253b": "+",    # heavy bottom tee
        "\u254b": "+",    # heavy cross
        "\u2578": "-",    # light left
        "\u2579": "|",    # light up
        "\u257a": "-",    # light right
        "\u257b": "|",    # light down
        "\u2713": "v",    # checkmark
        "\u2717": "x",    # ballot x
        "\u00a0": " ",    # non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Replace any remaining non-latin-1 chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


def parse_table(lines):
    rows = []
    for line in lines:
        if re.match(r"\|[-| :]+\|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def render_pdf(md_file, out_file):
    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pdf = PDF()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")

        line = sanitize(line)
        pdf.set_x(20)

        # ── H1
        if line.startswith("# ") and not line.startswith("## "):
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(0, 80, 180)
            pdf.multi_cell(0, 10, line[2:].strip())
            pdf.set_draw_color(0, 80, 180)
            pdf.set_line_width(0.6)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)

        # ── H2
        elif line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 15)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 9, line[3:].strip())
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.3)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(2)

        # ── H3
        elif line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 80, 180)
            pdf.multi_cell(0, 8, line[4:].strip())

        # ── HR
        elif line.startswith("---"):
            pdf.ln(2)
            pdf.set_draw_color(220, 220, 220)
            pdf.set_line_width(0.3)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)

        # ── Code block
        elif line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(sanitize(lines[i].rstrip("\n")))
                i += 1
            pdf.ln(2)
            pdf.set_fill_color(245, 247, 250)
            pdf.set_draw_color(0, 80, 180)
            pdf.set_line_width(0.4)
            code_text = "\n".join(code_lines)
            pdf.set_font("Courier", "", 9)
            pdf.set_text_color(36, 41, 46)
            pdf.multi_cell(170, 5, code_text, border=0, fill=True)
            pdf.ln(2)

        # ── Table
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(sanitize(lines[i].rstrip("\n")))
                i += 1
            rows = parse_table(table_lines)
            if not rows:
                continue
            pdf.ln(2)
            col_count = len(rows[0])
            col_w = 170 / col_count
            # Header row
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(0, 80, 180)
            pdf.set_text_color(255, 255, 255)
            for cell in rows[0]:
                pdf.cell(col_w, 8, cell, border=0, fill=True)
            pdf.ln()
            # Data rows
            pdf.set_font("Helvetica", "", 9)
            for r_idx, row in enumerate(rows[1:]):
                if r_idx % 2 == 0:
                    pdf.set_fill_color(246, 248, 250)
                else:
                    pdf.set_fill_color(255, 255, 255)
                pdf.set_text_color(30, 30, 30)
                for cell in row:
                    pdf.cell(col_w, 7, cell[:60], border=0, fill=True)
                pdf.ln()
            pdf.ln(2)
            continue

        # ── Blockquote
        elif line.startswith("> "):
            print(f"BLOCKQUOTE LINE: {repr(line)}")
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(160, 7, "  " + line[2:].strip())
            pdf.ln(1)

        # ── Bullet list
        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            text = re.sub(r"\*\*(.*?)\*\*", r"\1", line[2:].strip())
            text = re.sub(r"`(.*?)`", r"\1", text)
            pdf.multi_cell(170, 7, "- " + text)

        # ── Numbered list
        elif re.match(r"^\d+\. ", line):
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            text = re.sub(r"\*\*(.*?)\*\*", r"\1", re.sub(r"^\d+\. ", "", line).strip())
            text = re.sub(r"`(.*?)`", r"\1", text)
            num = re.match(r"^(\d+)\.", line).group(1)
            pdf.multi_cell(170, 7, f"{num}. {text}")

        # ── Blank line
        elif line.strip() == "":
            pdf.ln(3)

        # ── Normal paragraph
        else:
            text = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
            text = re.sub(r"`(.*?)`", r"\1", text)
            text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
            text = text.strip()
            if text:
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(30, 30, 30)
                pdf.multi_cell(0, 7, text)

        i += 1

    pdf.output(out_file)
    print(f"PDF saved: {out_file}")


files = {
    "mcp_guide.md": "MCP_Beginners_Guide.pdf",
    "README.md": "Odoo_Timesheet_MCP_Documentation.pdf",
}

target = sys.argv[1] if len(sys.argv) > 1 else "mcp_guide.md"
render_pdf(target, files[target])
