"""SME customers, suppliers, invoices, payments and ageing workspace."""
from datetime import date, timedelta
import streamlit as st
from ng_ui import hero
from services.sme_store import get_or_create_user, list_businesses, list_accounts
from services.sme_ar_ap import list_counterparties, create_counterparty, create_invoice, invoices_df, record_payment, post_invoice_to_ledger, ageing

def _money(x): return f"₦{float(x):,.0f}"

def render():
    hero("Customers, Suppliers & AR/AP", "Manage counterparties, invoices, collections and supplier obligations without losing the accounting trail.", "SME subledger")
    user=get_or_create_user(); businesses=list_businesses(user)
    if not businesses: st.info("Create a business profile in SME Financial Intelligence first."); return
    labels=[f"{b['name']} · {b['currency']}" for b in businesses]; label=st.selectbox("Active business",labels); business=businesses[labels.index(label)]; bid=int(business['id'])
    accounts=list_accounts(bid); account_map={a['name']:int(a['id']) for a in accounts}
    parties=list_counterparties(bid); inv=invoices_df(bid)
    if not parties.empty:
        cust=float(inv.loc[inv.party_type=='Customer','outstanding_amount'].sum()) if not inv.empty else 0
        supp=float(inv.loc[inv.party_type=='Supplier','outstanding_amount'].sum()) if not inv.empty else 0
    else: cust=supp=0
    overdue=0 if inv.empty else float(inv.loc[(inv.status.isin(['Open','Partially Paid'])) & (inv.due_date.dt.date < date.today()),'outstanding_amount'].sum())
    c1,c2,c3,c4=st.columns(4); c1.metric("Receivables",_money(cust)); c2.metric("Payables",_money(supp)); c3.metric("Overdue",_money(overdue)); c4.metric("Open invoices",0 if inv.empty else int(inv.status.isin(['Open','Partially Paid']).sum()))
    tabs=st.tabs(["Customers & Suppliers","Invoices","Payments","Ageing"])
    with tabs[0]:
        st.markdown("### Add customer or supplier")
        with st.form("party_form",clear_on_submit=True):
            p1,p2=st.columns(2); ptype=p1.selectbox("Type",["Customer","Supplier"]); name=p2.text_input("Name *")
            p3,p4=st.columns(2); email=p3.text_input("Email"); phone=p4.text_input("Phone")
            p5,p6=st.columns(2); tax=p5.text_input("TIN / Tax ID"); terms=p6.number_input("Payment terms (days)",min_value=0,value=30)
            credit=st.number_input("Credit limit (₦)",min_value=0.0,step=10000.0); address=st.text_input("Address")
            if st.form_submit_button("Save party",use_container_width=True,type="primary"):
                try: create_counterparty(bid,ptype,name,email=email,phone=phone,tax_id=tax,payment_terms_days=terms,credit_limit=credit,address=address); st.success("Party created."); st.rerun()
                except ValueError as e: st.error(str(e))
        st.dataframe(parties[["party_type","name","phone","email","tax_id","payment_terms_days","credit_limit"]] if not parties.empty else parties,use_container_width=True,hide_index=True)
    with tabs[1]:
        st.markdown("### Create invoice")
        customers=parties[parties.party_type=='Customer'] if not parties.empty else parties; suppliers=parties[parties.party_type=='Supplier'] if not parties.empty else parties
        with st.form("invoice_form",clear_on_submit=True):
            i1,i2=st.columns(2); itype=i1.selectbox("Invoice type",["Sales","Purchase"]); plist=customers if itype=="Sales" else suppliers
            party_options={f"{r['name']} (#{int(r['id'])})":int(r['id']) for _,r in plist.iterrows()} if not plist.empty else {}
            party_label=i2.selectbox("Customer / Supplier",list(party_options) if party_options else ["Create a party first"])
            i3,i4,i5=st.columns(3); number=i3.text_input("Invoice number *"); inv_date=i4.date_input("Invoice date",date.today()); due=i5.date_input("Due date",date.today()+timedelta(days=30))
            i6,i7=st.columns(2); subtotal=i6.number_input("Subtotal (₦)",min_value=0.0,step=1000.0); tax=i7.number_input("Tax / VAT (₦)",min_value=0.0,step=100.0); notes=st.text_input("Notes")
            if st.form_submit_button("Create invoice",use_container_width=True,type="primary"):
                if not party_options: st.error("Create at least one matching customer or supplier first.")
                else:
                    try: create_invoice(bid,party_options[party_label],number,inv_date.isoformat(),due.isoformat(),itype,subtotal,tax,notes); st.success("Invoice created. It remains operational until posted to the ledger."); st.rerun()
                    except ValueError as e: st.error(str(e))
        if not inv.empty:
            view=inv.copy(); view["Total"]=view.total_amount.map(_money); view["Paid"]=view.paid_amount.map(_money); view["Outstanding"]=view.outstanding_amount.map(_money)
            st.dataframe(view[["invoice_number","invoice_type","party_name","invoice_date","due_date","status","Total","Paid","Outstanding"]],use_container_width=True,hide_index=True)
            open_inv=view[view.status.isin(['Open','Partially Paid'])]
            if not open_inv.empty:
                opts={f"{r.invoice_number} · {r.party_name} · {_money(r.outstanding_amount)}":int(r.id) for _,r in open_inv.iterrows()}; selected=st.selectbox("Invoice workflow",list(opts)); selected_id=opts[selected]
                if st.button("Post invoice to accounting",use_container_width=True):
                    try: post_invoice_to_ledger(bid,selected_id); st.success("Invoice posted to the double-entry ledger."); st.rerun()
                    except ValueError as e: st.error(str(e))
    with tabs[2]:
        st.markdown("### Record invoice payment")
        open_inv=inv[inv.status.isin(['Open','Partially Paid'])] if not inv.empty else inv
        if open_inv.empty: st.info("No open invoices require payment.")
        else:
            opts={f"{r.invoice_number} · {r.party_name} · outstanding {_money(r.outstanding_amount)}":int(r.id) for _,r in open_inv.iterrows()}; sel=st.selectbox("Invoice",list(opts),key="payment_invoice"); iid=opts[sel]; row=open_inv[open_inv.id==iid].iloc[0]
            with st.form("payment_form"):
                amount=st.number_input("Payment amount (₦)",min_value=0.01,max_value=float(row.outstanding_amount),value=float(row.outstanding_amount)); pdate=st.date_input("Payment date",date.today()); acc=st.selectbox("Cash / bank account",list(account_map)); ref=st.text_input("Reference")
                if st.form_submit_button("Record payment",use_container_width=True,type="primary"):
                    try: record_payment(bid,iid,pdate.isoformat(),amount,account_map[acc],ref); st.success("Payment recorded and linked to the accounting ledger."); st.rerun()
                    except ValueError as e: st.error(str(e))
    with tabs[3]:
        st.markdown("### Outstanding ageing")
        age=ageing(bid)
        if age.empty: st.info("No outstanding invoices.")
        else: st.dataframe(age,use_container_width=True,hide_index=True); st.bar_chart(age.set_index("Bucket")["Amount"])
