import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.core.config import settings
from app.core.agent_brain import AgentBrain
from app.db.database import SessionLocal
from app.db import crud
from app.services.pdf_service import generate_sph_pdf
from app.services.chat_assistant import chat_assistant

logger = logging.getLogger(__name__)

# User state storage for bot conversation
user_states = {}
brain = AgentBrain()

async def check_authorization(update: Update) -> bool:
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if settings.AUTHORIZED_USER_ID != 0 and user_id != settings.AUTHORIZED_USER_ID:
        await update.message.reply_text(
            f"❌ Akses Ditolak. User ID Anda ({user_id}) belum diotorisasi di sistem PT ADT."
        )
        return False
    return True

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return
    chat_id = update.effective_chat.id
    user_states[chat_id] = {"state": "WAITING_INSTRUCTION", "data": None}
    
    welcome_text = (
        "👋 **Halo! Selamat datang di Sistem ADT (PT Anugrah Djaya Tunggal).**\n\n"
        "Saya dapat membantu Anda membuat Surat Penawaran Harga (SPH) atau mengecek rekapitulasi usaha.\n\n"
        "📌 **Perintah yang tersedia:**\n"
        "• /rekap - Ringkasan omzet, laba bersih, dan bagi hasil saat ini\n"
        "• /sph - Lihat 5 SPH terakhir\n\n"
        "💡 **Untuk membuat SPH**, langsung kirimkan instruksi Anda, contoh:\n"
        "_\"Tolong buatkan SPH untuk PT Dellifood Sentosa, UP Bpk. Fikri, barang SPROCKET RS40 harga 235.000, garansi 14 hari\"_"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def rekap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return
    db = SessionLocal()
    try:
        summary = crud.get_dashboard_summary(db)
        rekap_text = (
            "📊 **REKAPITULASI KEUANGAN & OPERASIONAL PT ADT**\n\n"
            f"📦 **Total SPH:** {summary['total_sph']}\n"
            f"📑 **PO Berjalan:** {summary['active_po']} (Total {summary['total_po']} PO)\n"
            f"💰 **Total Omzet:** Rp {summary['total_omzet']:,.0f}\n"
            f"📉 **Total Pengeluaran:** Rp {summary['total_expense']:,.0f}\n"
            f"💵 **Total Laba Bersih:** Rp {summary['total_laba_bersih']:,.0f}\n\n"
            "👥 **Akumulasi Bagi Hasil:**\n"
            f"• Karyawan 1 (25%): Rp {summary['total_k1']:,.0f}\n"
            f"• Karyawan 2 (25%): Rp {summary['total_k2']:,.0f}\n"
            f"• Kas Perusahaan (50%): Rp {summary['total_kas']:,.0f}"
        ).replace(",", ".")
        await update.message.reply_text(rekap_text, parse_mode="Markdown")
    finally:
        db.close()


async def tanya_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("?? Gunakan format: `/tanya <pertanyaan Anda>`\n\nContoh:\n`/tanya apakah pernah buat penawaran untuk barang sprocket?`", parse_mode="Markdown")
        return
    
    await update.message.reply_text("?? _Mencari jawaban di database MySQL..._", parse_mode="Markdown")
    reply = chat_assistant.answer_query(query)
    await update.message.reply_text(reply, parse_mode="Markdown")

async def sph_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return
    db = SessionLocal()
    try:
        sphs = crud.get_sph_list(db, limit=5)
        if not sphs:
            await update.message.reply_text("Belum ada SPH yang tercatat.")
            return
        text = "📄 **5 SPH Terakhir:**\n\n"
        for s in sphs:
            text += f"• {s.sph_number}\n  🏢 {s.company_name} | Nilai: Rp {s.total_sph_amount:,.0f} | Status: *{s.status}*\n"
        text = text.replace(",", ".")
        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    if chat_id not in user_states:
        user_states[chat_id] = {"state": "WAITING_INSTRUCTION", "data": None}
    state_info = user_states[chat_id]

    if state_info["state"] == "WAITING_INSTRUCTION":
        await update.message.reply_text("🤖 _Menganalisis instruksi penawaran dengan Mistral AI..._", parse_mode="Markdown")
        try:
            extracted = brain.parse_sph_instruction(text)
        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan Mistral AI: {e}")
            return

        if not extracted or not extracted.get("company_name") or not extracted.get("items"):
            await update.message.reply_text("⚠️ Tidak dapat mendeteksi informasi penting (Nama PT / Barang / Harga). Silakan lengkapi instruksi Anda.")
            return

        state_info["state"] = "CONFIRMING"
        state_info["data"] = extracted

        items_str = ""
        for i, it in enumerate(extracted["items"], 1):
            items_str += f"{i}. {it.get('description')} - Rp {it.get('price', 0):,.0f}\n".replace(",", ".")

        confirm_msg = (
            "🔍 **Data SPH Terdeteksi:**\n\n"
            f"🏢 **Perusahaan:** {extracted.get('company_name')}\n"
            f"👤 **UP:** {extracted.get('up_name') or '-'}\n"
            f"📦 **Barang:**\n{items_str}"
            f"🛡️ **Garansi:** {'Ya (' + str(extracted.get('warranty_days', 14)) + ' hari)' if extracted.get('has_warranty') else 'Tidak'}\n\n"
            "Ketik **ya** untuk membuat SPH & PDF, atau ketik instruksi baru untuk mengoreksi."
        )
        await update.message.reply_text(confirm_msg, parse_mode="Markdown")

    elif state_info["state"] == "CONFIRMING":
        if text.lower() in ["ya", "ok", "yes", "benar", "buat", "sip"]:
            await update.message.reply_text("📄 _Menyimpan ke MySQL & membuat PDF SPH..._", parse_mode="Markdown")
            db = SessionLocal()
            try:
                data = state_info["data"]
                record = crud.create_sph(
                    db=db,
                    company_name=data["company_name"],
                    up_name=data.get("up_name") or "-",
                    items=data["items"],
                    has_warranty=data.get("has_warranty", False),
                    warranty_days=data.get("warranty_days")
                )
                pdf_path = os.path.join(settings.PDF_OUTPUT_DIR, record.pdf_filename)
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        await update.message.reply_document(
                            document=f,
                            filename=record.pdf_filename,
                            caption=(
                                "✅ **SPH Berhasil Dibuat & Tersimpan di Web Dashboard!**\n\n"
                                f"📝 **No. SPH:** {record.sph_number}\n"
                                f"📅 **Tanggal:** {record.date_str}\n"
                                f"🏢 **Tujuan:** {record.company_name}"
                            ),
                            parse_mode="Markdown"
                        )
                else:
                    await update.message.reply_text("❌ Berhasil simpan data tapi file PDF tidak ditemukan.")
            except Exception as e:
                await update.message.reply_text(f"❌ Terjadi kesalahan: {e}")
            finally:
                db.close()
                state_info["state"] = "WAITING_INSTRUCTION"
                state_info["data"] = None
        else:
            state_info["state"] = "WAITING_INSTRUCTION"
            state_info["data"] = None
            await handle_message(update, context)

def build_bot_app():
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("rekap", rekap_cmd))
    app.add_handler(CommandHandler("sph", sph_cmd))
    app.add_handler(CommandHandler("tanya", tanya_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
