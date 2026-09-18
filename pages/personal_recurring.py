from datetime import date
import streamlit as st
from services import personal_finance as pf
from services import personal_recurring as recurring

def render():
    pf.ensure_schema(); recurring.ensure_schema()
    st.title("🔁 Recurring Finance")
    st.caption("Track recurring income and obligations without silently creating transactions.")
    due=recurring.due_rules()
    a,b=st.columns(2)
    a.metric("Active Rules",len(recurring.rules()))
    b.metric("Due for Review",len(due))
    if not due.empty:
        st.warning("Recurring items are due. Review them before posting.")
        st.dataframe(due[["description","amount","transaction_type","frequency","next_due_date","account_name"]],use_container_width=True,hide_index=True)
        if st.button("Post All Due Items",type="primary"):
            ids=recurring.post_due()
            st.success(f"{len(ids)} recurring transaction(s) posted.")
            st.rerun()
    st.divider()
    st.subheader("Add Recurring Rule")
    accts=pf.accounts()
    cats=pf.categories()
    with st.form("recurring_form"):
        c1,c2=st.columns(2)
        desc=c1.text_input("Description")
        amount=c2.number_input("Amount",min_value=0.01,step=100.0)
        c3,c4,c5=st.columns(3)
        typ=c3.selectbox("Type",pf.PERSONAL_TYPES)
        category=c4.selectbox("Category",cats["name"].tolist())
        account=c5.selectbox("Account",accts["name"].tolist())
        c6,c7=st.columns(2)
        freq=c6.selectbox("Frequency",recurring.FREQUENCIES)
        due_date=c7.date_input("First / next due date",date.today())
        notes=st.text_input("Notes")
        if st.form_submit_button("Save Recurring Rule"):
            try:
                aid=int(accts.loc[accts.name==account,"id"].iloc[0])
                recurring.add_rule(desc,amount,typ,category,aid,freq,due_date.isoformat(),notes)
                st.success("Recurring rule saved.")
                st.rerun()
            except Exception as exc: st.error(str(exc))
    st.subheader("Active Rules")
    all_rules=recurring.rules()
    if all_rules.empty:
        st.info("No recurring rules configured.")
    else:
        st.dataframe(all_rules[["id","description","amount","transaction_type","category","frequency","next_due_date","account_name"]],use_container_width=True,hide_index=True)
        rule_id=st.number_input("Rule ID to archive",min_value=1,step=1)
        if st.button("Archive Rule"):
            try:
                recurring.delete_rule(int(rule_id)); st.success("Rule archived."); st.rerun()
            except Exception as exc: st.error(str(exc))
