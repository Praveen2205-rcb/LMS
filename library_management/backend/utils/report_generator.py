from __future__ import annotations
import os
import datetime
from fpdf import FPDF
from backend.database import get_connection
from backend.models.models import get_all_transactions, get_dashboard_stats, get_all_books, get_all_members
from dotenv import load_dotenv

load_dotenv()
REPORTS_DIR = os.getenv("REPORTS_DIR", "database/reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class LibraryPDF(FPDF):
    def header(self):
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 210, 30, "F")
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(245, 158, 11)
        self.set_xy(0, 8)
        self.cell(210, 10, "LIBRARY MANAGEMENT SYSTEM", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(148, 163, 184)
        self.set_xy(0, 20)
        self.cell(210, 6, f"Generated: {datetime.datetime.now().strftime('%d %b %Y  %H:%M')}", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        self.set_fill_color(30, 41, 59)
        self.set_text_color(245, 158, 11)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def table_header(self, cols: list[tuple[str, int]]):
        self.set_fill_color(51, 65, 85)
        self.set_text_color(226, 232, 240)
        self.set_font("Helvetica", "B", 9)
        for label, width in cols:
            self.cell(width, 8, label, border=0, fill=True)
        self.ln()

    def table_row(self, values: list[str], widths: list[int], fill: bool = False):
        if fill:
            self.set_fill_color(15, 23, 42)
        else:
            self.set_fill_color(22, 33, 62)
        self.set_text_color(203, 213, 225)
        self.set_font("Helvetica", "", 8)
        for val, w in zip(values, widths):
            self.cell(w, 7, str(val)[:30], border=0, fill=True)
        self.ln()


def generate_full_report(generated_by: int | None = None) -> str:
    pdf = LibraryPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    stats = get_dashboard_stats()

    # ── Summary Stats ────────────────────────────────────────────
    pdf.section_title("SYSTEM OVERVIEW")
    stat_items = [
        ("Total Books", stats["total_books"]),
        ("Available Books", stats["available_books"]),
        ("Total Members", stats["total_members"]),
        ("Active Issues", stats["active_issues"]),
        ("Overdue Books", stats["overdue_count"]),
        ("Pending Fines (₹)", f"{stats['total_fines']:.2f}"),
    ]
    pdf.set_font("Helvetica", "", 10)
    for i, (label, value) in enumerate(stat_items):
        fill = i % 2 == 0
        pdf.set_fill_color(22, 33, 62) if fill else pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(203, 213, 225)
        pdf.cell(100, 8, f"  {label}", fill=True)
        pdf.set_text_color(245, 158, 11)
        pdf.cell(90, 8, str(value), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── Books ────────────────────────────────────────────────────
    pdf.section_title("BOOK INVENTORY")
    cols = [("ID",10),("Title",70),("Author",50),("Category",30),("Copies",15),("Avail",15)]
    widths = [c[1] for c in cols]
    pdf.table_header(cols)
    books = get_all_books()
    for i, b in enumerate(books):
        pdf.table_row([str(b["id"]),b["title"],b["author"],
                       b.get("category_name",""),
                       str(b["total_copies"]),str(b["available_copies"])],
                      widths, fill=i%2==0)

    # ── Members ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("MEMBERS LIST")
    cols2 = [("ID",15),("Member ID",25),("Name",60),("Email",60),("Active Borrows",30)]
    widths2 = [c[1] for c in cols2]
    pdf.table_header(cols2)
    members = get_all_members()
    for i, m in enumerate(members):
        pdf.table_row([str(m["id"]),m.get("member_id",""),m["full_name"],
                       m.get("email",""),str(m.get("active_borrows",0))],
                      widths2, fill=i%2==0)

    # ── Transactions ─────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("RECENT TRANSACTIONS (Last 50)")
    cols3 = [("TXN",12),("Book",65),("Member",45),("Issued",20),("Due",20),("Status",18),("Fine",10)]
    widths3 = [c[1] for c in cols3]
    pdf.table_header(cols3)
    txns = get_all_transactions()[:50]
    for i, t in enumerate(txns):
        pdf.table_row([str(t["id"]),t.get("book_title",""),t.get("member_name",""),
                       str(t["issue_date"]),str(t["due_date"]),
                       t["status"],f"₹{t.get('fine_amount',0):.0f}"],
                      widths3, fill=i%2==0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"library_report_{ts}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    pdf.output(filepath)

    # Save report record
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO reports (title,report_type,file_path,generated_by) VALUES (%s,%s,%s,%s)",
                    (f"Full Library Report {ts}", "full", filepath, generated_by))
        cur.close(); conn.close()
    except Exception:
        pass

    return filepath
