import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.database import Base

class SPHRecord(Base):
    __tablename__ = "sph_records"

    id = Column(Integer, primary_key=True, index=True)
    sph_seq_number = Column(Integer, index=True, nullable=False)
    sph_number = Column(String(100), unique=True, index=True, nullable=False)
    date_str = Column(String(100), nullable=False)
    company_name = Column(String(255), index=True, nullable=False)
    up_name = Column(String(255), default="-")
    items_json = Column(Text, nullable=False)
    has_warranty = Column(Boolean, default=False)
    warranty_days = Column(Integer, nullable=True)
    pdf_filename = Column(String(255), nullable=False)
    status = Column(String(50), default="PENAWARAN", index=True)
    total_sph_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    purchase_orders = relationship("PurchaseOrder", back_populates="sph")

    @property
    def items(self):
        try:
            return json.loads(self.items_json) if self.items_json else []
        except Exception:
            return []

    @items.setter
    def items(self, val):
        self.items_json = json.dumps(val, ensure_ascii=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    sph_id = Column(Integer, ForeignKey("sph_records.id", ondelete="SET NULL"), nullable=True)
    po_number = Column(String(100), unique=True, index=True, nullable=False)
    po_date = Column(DateTime, default=datetime.now, nullable=False)
    client_name = Column(String(255), index=True, nullable=False)
    total_po_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="DALAM_PENGERJAAN", index=True)
    po_pdf_filename = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    items_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    sph = relationship("SPHRecord", back_populates="purchase_orders")
    expenses = relationship("Expense", back_populates="po", cascade="all, delete-orphan")
    profit_split = relationship("ProfitSplit", back_populates="po", uselist=False, cascade="all, delete-orphan")

    @property
    def items(self):
        if self.sph and self.sph.items:
            return self.sph.items
        if self.items_json:
            try:
                return json.loads(self.items_json)
            except Exception:
                pass
        return []

    @property
    def item_summary(self) -> str:
        all_items = self.items
        if all_items:
            descriptions = [it.get("description", "").strip() for it in all_items if it.get("description")]
            if descriptions:
                return ", ".join(descriptions)
        if self.notes:
            return self.notes.strip()
        return "Pengadaan Barang"

    @property
    def total_expense(self) -> float:
        return sum(exp.amount for exp in self.expenses)

    @property
    def net_profit(self) -> float:
        return self.total_po_amount - self.total_expense

    @property
    def margin_percentage(self) -> float:
        if self.total_po_amount > 0:
            return (self.net_profit / self.total_po_amount) * 100
        return 0.0


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    expense_date = Column(DateTime, default=datetime.now, nullable=False)
    category = Column(String(100), default="Material")
    description = Column(String(255), nullable=False)
    amount = Column(Float, default=0.0, nullable=False)
    vendor_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    po = relationship("PurchaseOrder", back_populates="expenses")


class ProfitSplit(Base):
    __tablename__ = "profit_splits"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    karyawan_1_name = Column(String(100), default="Karyawan 1")
    karyawan_1_percent = Column(Float, default=25.0)
    karyawan_1_amount = Column(Float, default=0.0)

    karyawan_2_name = Column(String(100), default="Karyawan 2")
    karyawan_2_percent = Column(Float, default=25.0)
    karyawan_2_amount = Column(Float, default=0.0)

    kas_perusahaan_percent = Column(Float, default=50.0)
    kas_perusahaan_amount = Column(Float, default=0.0)

    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    po = relationship("PurchaseOrder", back_populates="profit_split")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    karyawan_name = Column(String(100), nullable=False, index=True) # "Karyawan 1" or "Karyawan 2"
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Float, default=0.0, nullable=False)
    withdrawal_date = Column(DateTime, default=datetime.now, nullable=False)
    payment_method = Column(String(50), default="Transfer Bank") # Transfer Bank, Tunai, Lainnya
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    po = relationship("PurchaseOrder")
