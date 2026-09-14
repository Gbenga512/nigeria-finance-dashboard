from services.ifrs_framework import classify_cash_flow, framework_summary, invoice_tax_control, supplier_tax_treatment


def test_framework_contains_core_ifrs_controls():
    standards = {row["Standard"] for row in framework_summary()}
    assert {"IAS 1", "IAS 7", "IFRS 15", "IFRS 9", "IFRS 16", "IAS 12"}.issubset(standards)


def test_ias7_cash_flow_classification():
    assert classify_cash_flow({"Revenue"}) == "Operating"
    assert classify_cash_flow({"Expense"}) == "Operating"
    assert classify_cash_flow({"Asset"}) == "Investing"
    assert classify_cash_flow({"Liability"}) == "Financing"
    assert classify_cash_flow({"Equity"}) == "Financing"


def test_recoverable_supplier_vat_is_asset_control():
    assert supplier_tax_treatment(15000, True) == ("VAT Recoverable", 15000.0)
    assert invoice_tax_control(15000, is_sales=False, recoverable_input_tax=True)["classification"] == "Asset"


def test_sales_tax_is_liability_control():
    result = invoice_tax_control(7500, is_sales=True)
    assert result == {"account": "Tax Payable", "amount": 7500.0, "classification": "Liability"}
