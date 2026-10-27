"""PDF/HTML report generation from the current library database.

build_fee_receipt_pdf() renders a downloadable book-fee receipt (Rs. 4000 per
issue) as a real PDF via fpdf2 — served by /api/fees/<id>/receipt.pdf.

build_report_html() still produces the print-optimized library report
(report.html): open it in a browser and press Ctrl+P -> "Save as PDF".

    python generate_pdf.py
"""
from datetime import datetime

from controllers.app_controller import LibraryController

STYLES = """
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #1c2433; margin: 40px; }
    h1 { color: #1a365d; text-align: center; border-bottom: 2px solid #2b6cb0; padding-bottom: 10px; }
    h2 { color: #2b6cb0; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; }
    th, td { border: 1px solid #cbd5e0; padding: 8px 10px; text-align: left; }
    th { background-color: #ebf8ff; color: #2c5282; }
    tr:nth-child(even) { background-color: #f7fafc; }
    .cards { display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }
    .card { flex: 1 1 150px; border: 1px solid #cbd5e0; border-radius: 10px; padding: 14px; background: #f8fafc; }
    .card b { display: block; font-size: 24px; color: #2b6cb0; }
    .meta { color: #64748b; text-align: center; }
    .page-break { page-break-after: always; }
    @media print { .no-print { display: none; } }
"""


def _table(headers, rows):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    if not body:
        body = f'<tr><td colspan="{len(headers)}" style="text-align:center;color:#64748b">No records found</td></tr>'
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_report_html():
    controller = LibraryController()
    summary = controller.report_summary()
    borrowed = controller.list_transactions()
    overdue = controller.borrow_dao.get_overdue_transactions()
    top_books = controller.borrow_dao.most_borrowed_books(limit=10)
    reservations = controller.list_reservations()
    students = controller.get_users_by_role("student")
    fines = controller.list_fines()

    cards = "".join(
        f'<div class="card"><b>{value}</b>{label}</div>'
        for label, value in (
            ("Total books", summary["total_books"]),
            ("Available copies", summary["available_copies"]),
            ("Total students", summary["total_students"]),
            ("Currently borrowed", summary["borrowed"]),
            ("Overdue", summary["overdue"]),
            ("Pending reservations", summary["pending_reservations"]),
            ("Unpaid fines (Rs.)", summary["unpaid_fines"]),
        )
    )

    books_rows = [
        (b["id"], b["isbn"], b["title"], b["author"], b["category"],
         b["total_copies"], b["available_copies"], b["shelf_no"])
        for b in controller.list_books()
    ]
    borrowed_rows = [
        (t["id"], t["student_name"] or t["student_id"], t["book_title"],
         t["issue_date"], t["due_date"], t["return_date"] or "—", t["status"], f"Rs. {t['fine_amount']}")
        for t in borrowed[:100]
    ]
    overdue_rows = [
        (t["id"], t["student_name"] or t["student_id"], t["book_title"], t["due_date"],
         f"{t.get('overdue_days', 0)} days", f"Rs. {(t.get('overdue_days') or 0) * 10.0}")
        for t in overdue
    ]
    top_rows = [(b["title"], b["author"], b["borrow_count"]) for b in top_books]
    reservation_rows = [
        (r["id"], r["student_name"] or r["student_id"], r["book_title"],
         r["request_date"], r["status"]) for r in reservations
    ]
    fine_rows = [
        (f["id"], f["student_name"] or f["student_id"], f["book_title"],
         f"{f.get('overdue_days') or 0} days", f"Rs. {f['amount']:.2f}", f["status"],
         f["payment_date"] or f.get("waived_at") or "—") for f in fines
    ]
    student_rows = [
        (s["user_id"], s["name"], s["email"], s["department"] or "—",
         s["semester"] or "—", s["status"]) for s in students
    ]

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Smart Library — Library Report</title>
<style>{STYLES}</style>
</head>
<body>
    <h1>Smart Library Management System — Library Report</h1>
    <p class="meta">Generated on {summary['generated_at']} &middot; Data source: library.db (live)</p>

    <h2>1. Summary</h2>
    <div class="cards">{cards}</div>

    <h2>2. Catalog ({len(books_rows)} titles)</h2>
    {_table(("ID", "ISBN", "Title", "Author", "Category", "Total", "Available", "Shelf"), books_rows)}

    <div class="page-break"></div>

    <h2>3. Borrowing Records (latest {min(len(borrowed), 100)} of {len(borrowed)})</h2>
    {_table(("Txn", "Student", "Book", "Issued", "Due", "Returned", "Status", "Fine"), borrowed_rows)}

    <h2>4. Overdue Books ({len(overdue_rows)})</h2>
    {_table(("Txn", "Student", "Book", "Due date", "Overdue", "Fine so far"), overdue_rows)}

    <h2>5. Most Borrowed Books</h2>
    {_table(("Title", "Author", "Times borrowed"), top_rows)}

    <h2>6. Fine Report ({len(fine_rows)})</h2>
    {_table(("Fine", "Member", "Book", "Overdue", "Amount", "Status", "Paid / Waived"), fine_rows)}

    <h2>7. Reservations ({len(reservation_rows)})</h2>
    {_table(("ID", "Student", "Book", "Requested", "Status"), reservation_rows)}

    <h2>8. Registered Students ({len(student_rows)})</h2>
    {_table(("Student ID", "Name", "Email", "Department", "Semester", "Status"), student_rows)}

    <p class="no-print" style="text-align:center;color:#64748b;margin-top:30px">
        Print this page (Ctrl+P) and choose "Save as PDF" to export a PDF copy.
    </p>
</body>
</html>"""


def build_fee_receipt_pdf(fee: dict):
    """Render a book-fee receipt as PDF bytes. Returns (bytes, error)."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None, "PDF support is missing. Run: pip install fpdf2"

    try:
        from services.settings_service import SettingsService
        library_name = SettingsService().get("library_name", "Smart Library")
    except Exception:
        library_name = "Smart Library"

    amount = float(fee.get("amount") or 0)
    status = str(fee.get("status") or "unpaid").upper()
    paid_line = "-"
    if status == "PAID":
        paid_line = f"{fee.get('payment_date') or '-'}    Collected by: {fee.get('collected_by') or '-'}"

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, library_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Book Fee Receipt", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_draw_color(43, 108, 176)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    def info_row(label, value):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(55, 8, label, align="L")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 8, str(value), align="L", new_x="LMARGIN", new_y="NEXT")

    info_row("Receipt No:", f"BF-{int(fee.get('id') or 0):06d}")
    info_row("Issued On:", str(fee.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    info_row("Member ID:", fee.get("student_id") or "-")
    info_row("Member Name:", fee.get("student_name") or "-")
    info_row("Book Title:", fee.get("book_title") or "General Library Book Fee")
    info_row("Book Author:", fee.get("book_author") or "-")
    info_row("ISBN:", fee.get("book_isbn") or "-")
    info_row("Loan Ref:", f"Transaction #{fee.get('transaction_id')}" if fee.get("transaction_id") else "-")

    pdf.ln(6)
    pdf.set_fill_color(235, 248, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 12, f"Book Fee Amount:  Rs. {amount:,.2f}", border=1, fill=True,
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Payment Status:  {status}", align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, f"Payment Date / Collected By:  {paid_line}", align="L",
                   new_x="LMARGIN", new_y="NEXT")

    pdf.ln(14)
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(
        0, 6,
        "The library book fee (Rs. 4000 by default) is uploaded by the library administrator. "
        "Books can only be issued once this fee is paid; this receipt is generated by the "
        "Smart Library Management System.",
        align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="L",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Library Staff Signature: ______________________", align="R")
    return bytes(pdf.output()), None


if __name__ == "__main__":
    html = build_report_html()
    with open("report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Live library report generated: report.html ({datetime.now():%Y-%m-%d %H:%M:%S})")
    print("[INFO] Open it in a browser and press Ctrl+P -> Save as PDF for a PDF copy.")
    print("[INFO] Fee receipts download as PDF from the Fines page or /api/fees/<id>/receipt.pdf.")
