"""Customer, supplier, invoice and payment subledger for SME finance."""
from __future__ import annotations
from datetime import date
import sqlite3
import pandas as pd
from services.sme_store import connect, init_db
from services.sme_accounting import ensure_standard_accounts, post_journal_entry

SCHEMA = """
CREATE TABLE IF NOT EXISTS counterparties (id INTEGER PRIMARY KEY AUTOINCREMENT,business_id INTEGER NOT NULL,party_type TEXT NOT NULL CHECK(party_type IN ('Customer','Supplier')),name TEXT NOT NULL,email TEXT,phone TEXT,address TEXT,tax_id TEXT,payment_terms_days INTEGER NOT NULL DEFAULT 30,credit_limit REAL NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,UNIQUE(business_id,party_type,name));
CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT,business_id INTEGER NOT NULL,party_id INTEGER NOT NULL,invoice_number TEXT NOT NULL,invoice_date TEXT NOT NULL,due_date TEXT NOT NULL,invoice_type TEXT NOT NULL CHECK(invoice_type IN ('Sales','Purchase')),subtotal REAL NOT NULL CHECK(subtotal >= 0),tax_amount REAL NOT NULL DEFAULT 0 CHECK(tax_amount >= 0),total_amount REAL NOT NULL CHECK(total_amount >= 0),status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Draft','Open','Partially Paid','Paid','Void')),notes TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,FOREIGN KEY(party_id) REFERENCES counterparties(id) ON DELETE RESTRICT,UNIQUE(business_id,invoice_number));
CREATE TABLE IF NOT EXISTS invoice_payments (id INTEGER PRIMARY KEY AUTOINCREMENT,business_id INTEGER NOT NULL,invoice_id INTEGER NOT NULL,payment_date TEXT NOT NULL,amount REAL NOT NULL CHECK(amount > 0),account_id INTEGER NOT NULL,reference TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT);
CREATE INDEX IF NOT EXISTS idx_counterparty_business ON counterparties(business_id,party_type); CREATE INDEX IF NOT EXISTS idx_invoice_business_due ON invoices(business_id,due_date,status);
"""

def ensure_schema():
    init_db()
    with connect() as conn: conn.executescript(SCHEMA); conn.commit()

def list_counterparties(business_id:int, party_type:str|None=None)->pd.DataFrame:
    ensure_schema(); sql="SELECT * FROM counterparties WHERE business_id=? AND active=1"; params=[business_id]
    if party_type: sql+=" AND party_type=?"; params.append(party_type)
    sql+=" ORDER BY name"
    with connect() as conn: return pd.read_sql_query(sql,conn,params=params)

def create_counterparty(business_id:int,party_type:str,name:str,**fields)->int:
    ensure_schema(); name=str(name).strip()
    if party_type not in {"Customer","Supplier"} or not name: raise ValueError("A valid party type and name are required.")
    days=int(fields.get("payment_terms_days",30)); limit=float(fields.get("credit_limit",0))
    if days<0 or limit<0: raise ValueError("Payment terms and credit limit cannot be negative.")
    with connect() as conn:
        try:
            cur=conn.execute("INSERT INTO counterparties(business_id,party_type,name,email,phone,address,tax_id,payment_terms_days,credit_limit) VALUES(?,?,?,?,?,?,?,?,?)",(business_id,party_type,name,fields.get("email",""),fields.get("phone",""),fields.get("address",""),fields.get("tax_id",""),days,limit)); conn.commit(); return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc: raise ValueError("A party with this name already exists for this business.") from exc

def create_invoice(business_id:int,party_id:int,invoice_number:str,invoice_date:str,due_date:str,invoice_type:str,subtotal:float,tax_amount:float=0,notes:str="")->int:
    ensure_schema(); ensure_standard_accounts(business_id)
    if invoice_type not in {"Sales","Purchase"}: raise ValueError("Invoice type must be Sales or Purchase.")
    try: date.fromisoformat(str(invoice_date)); date.fromisoformat(str(due_date))
    except ValueError as exc: raise ValueError("Invoice dates must be valid YYYY-MM-DD dates.") from exc
    subtotal=float(subtotal); tax_amount=float(tax_amount); total=round(subtotal+tax_amount,2)
    if subtotal<0 or tax_amount<0 or total<=0 or not str(invoice_number).strip(): raise ValueError("Invoice number and positive invoice amount are required.")
    with connect() as conn:
        party=conn.execute("SELECT party_type FROM counterparties WHERE id=? AND business_id=? AND active=1",(party_id,business_id)).fetchone(); expected="Customer" if invoice_type=="Sales" else "Supplier"
        if not party or party["party_type"]!=expected: raise ValueError("Selected party does not match invoice type.")
        try: cur=conn.execute("INSERT INTO invoices(business_id,party_id,invoice_number,invoice_date,due_date,invoice_type,subtotal,tax_amount,total_amount,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(business_id,party_id,str(invoice_number).strip(),invoice_date,due_date,invoice_type,subtotal,tax_amount,total,notes)); conn.commit(); return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc: raise ValueError("Invoice number already exists for this business.") from exc

def invoices_df(business_id:int)->pd.DataFrame:
    ensure_schema()
    with connect() as conn: df=pd.read_sql_query("SELECT i.*,c.name AS party_name,c.party_type,COALESCE((SELECT SUM(p.amount) FROM invoice_payments p WHERE p.invoice_id=i.id),0) AS paid_amount FROM invoices i JOIN counterparties c ON c.id=i.party_id WHERE i.business_id=? ORDER BY date(i.due_date),i.id",conn,params=(business_id,),parse_dates=["invoice_date","due_date"])
    df["outstanding_amount"]=(df["total_amount"]-df["paid_amount"]).round(2); return df

def record_payment(business_id:int,invoice_id:int,payment_date:str,amount:float,account_id:int,reference:str="")->int:
    ensure_schema(); ensure_standard_accounts(business_id); amount=round(float(amount),2)
    try: date.fromisoformat(str(payment_date))
    except ValueError as exc: raise ValueError("Payment date must be valid YYYY-MM-DD.") from exc
    if amount<=0: raise ValueError("Payment amount must be positive.")
    with connect() as conn:
        inv=conn.execute("SELECT * FROM invoices WHERE id=? AND business_id=? AND status!='Void'",(invoice_id,business_id)).fetchone()
        if not inv: raise ValueError("Invoice not found or voided.")
        paid=float(conn.execute("SELECT COALESCE(SUM(amount),0) AS total FROM invoice_payments WHERE invoice_id=?",(invoice_id,)).fetchone()["total"]); outstanding=round(float(inv["total_amount"])-paid,2)
        if amount>outstanding+0.01: raise ValueError(f"Payment exceeds outstanding balance of ₦{outstanding:,.2f}.")
        if not conn.execute("SELECT id FROM accounts WHERE id=? AND business_id=? AND active=1",(account_id,business_id)).fetchone(): raise ValueError("Payment account does not belong to the active business.")
        cur=conn.execute("INSERT INTO invoice_payments(business_id,invoice_id,payment_date,amount,account_id,reference) VALUES(?,?,?,?,?,?)",(business_id,invoice_id,payment_date,amount,account_id,reference)); payment_id=int(cur.lastrowid)
        status="Paid" if abs((paid+amount)-float(inv["total_amount"]))<0.01 else "Partially Paid"; conn.execute("UPDATE invoices SET status=? WHERE id=?",(status,invoice_id)); conn.commit()
    with connect() as conn: accounts={r["name"]:int(r["id"]) for r in conn.execute("SELECT id,name FROM accounts WHERE business_id=?",(business_id,)).fetchall()}
    ar=accounts["Accounts Receivable"] if inv["invoice_type"]=="Sales" else accounts["Accounts Payable"]
    lines=[{"account_id":account_id,"debit":amount},{"account_id":ar,"credit":amount}] if inv["invoice_type"]=="Sales" else [{"account_id":ar,"debit":amount},{"account_id":account_id,"credit":amount}]
    post_journal_entry(business_id,payment_date,f"Payment for {inv['invoice_number']}",lines,reference=f"Payment:{payment_id}",source="AR/AP payment"); return payment_id

def post_invoice_to_ledger(business_id:int,invoice_id:int)->int:
    ensure_schema(); ensure_standard_accounts(business_id)
    with connect() as conn:
        inv=conn.execute("SELECT i.*,c.name AS party_name FROM invoices i JOIN counterparties c ON c.id=i.party_id WHERE i.id=? AND i.business_id=?",(invoice_id,business_id)).fetchone()
        if not inv: raise ValueError("Invoice not found.")
        marker=conn.execute("SELECT id FROM journal_entries WHERE reference=? AND business_id=?",(f"Invoice:{inv['invoice_number']}",business_id)).fetchone()
        if marker: return int(marker["id"])
        accounts={r["name"]:int(r["id"]) for r in conn.execute("SELECT id,name FROM accounts WHERE business_id=?",(business_id,)).fetchall()}
    amount=float(inv["total_amount"]); subtotal=float(inv["subtotal"]); tax=float(inv["tax_amount"])
    if inv["invoice_type"]=="Sales":
        lines=[{"account_id":accounts["Accounts Receivable"],"debit":amount},{"account_id":accounts["Sales Revenue"],"credit":subtotal}]
        if tax: lines.append({"account_id":accounts["Tax Payable"],"credit":tax})
    else:
        lines=[{"account_id":accounts["Operating Expenses"],"debit":subtotal},{"account_id":accounts["Accounts Payable"],"credit":amount}]
        if tax: lines.insert(1,{"account_id":accounts["Tax Expense"],"debit":tax})
    return post_journal_entry(business_id,inv["invoice_date"],f"Invoice {inv['invoice_number']} — {inv['party_name']}",lines,reference=f"Invoice:{inv['invoice_number']}",source="AR/AP invoice")

def ageing(business_id:int,as_of=None)->pd.DataFrame:
    as_of=pd.Timestamp(as_of or date.today()); df=invoices_df(business_id); df=df[df["status"].isin(["Open","Partially Paid"])].copy()
    if df.empty: return pd.DataFrame(columns=["Bucket","Amount"])
    df["days_overdue"]=(as_of-df["due_date"]).dt.days; buckets=[("Current",df["days_overdue"]<=0),("1–30",df["days_overdue"].between(1,30)),("31–60",df["days_overdue"].between(31,60)),("61–90",df["days_overdue"].between(61,90)),("90+",df["days_overdue"]>90)]
    return pd.DataFrame([{"Bucket":b,"Amount":float(df.loc[m,"outstanding_amount"].sum())} for b,m in buckets])
