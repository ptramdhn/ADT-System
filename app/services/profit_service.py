from app.db.models import PurchaseOrder, ProfitSplit
from app.core.config import settings

def recalculate_profit_split(po: PurchaseOrder, db_session) -> ProfitSplit:
    """
    Calculates net profit (PO revenue - Total expenses) and splits according to percentages.
    """
    total_revenue = po.total_po_amount
    total_expense = sum(exp.amount for exp in po.expenses)
    net_profit = max(0.0, total_revenue - total_expense) # Or allow negative if deficit
    
    split = po.profit_split
    if not split:
        split = ProfitSplit(
            po_id=po.id,
            karyawan_1_name="Karyawan 1",
            karyawan_1_percent=settings.DEFAULT_KARYAWAN_1_PERCENT,
            karyawan_2_name="Karyawan 2",
            karyawan_2_percent=settings.DEFAULT_KARYAWAN_2_PERCENT,
            kas_perusahaan_percent=settings.DEFAULT_KAS_PERUSAHAAN_PERCENT
        )
        db_session.add(split)
        db_session.flush()

    # Calculate nominal based on net profit
    split.karyawan_1_amount = (split.karyawan_1_percent / 100.0) * net_profit
    split.karyawan_2_amount = (split.karyawan_2_percent / 100.0) * net_profit
    split.kas_perusahaan_amount = (split.kas_perusahaan_percent / 100.0) * net_profit

    db_session.commit()
    db_session.refresh(split)
    return split
