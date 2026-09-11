# ADT-System (Sistem Operasional & Keuangan PT Anugrah Djaya Tunggal)

Sistem ERP & Pendataan Operasional Usaha untuk **PT Anugrah Djaya Tunggal**, mencakup:
1. **Surat Penawaran Harga (SPH)**: Pembuatan otomatis dengan AI (Mistral AI) langsung dari teks prompt di Web Dashboard, penomoran Romawi otomatis, dan pembuatan PDF resmi kop surat perusahaan.
2. **Purchase Order (PO)**: Eskalasi status dari SPH ke PO setelah deal kontrak.
3. **Pencatatan Biaya (HPP/Expenses)**: Pencatatan biaya material, jasa bubut/fabrikasi, ongkir Lalamove, dan operasional per PO.
4. **Kalkulasi Laba Bersih & Bagi Hasil**: Perhitungan otomatis Laba Bersih = PO - Pengeluaran, serta pembagian porsi keuntungan (Karyawan 1, Karyawan 2, dan Kas Perusahaan).
5. **Database**: MySQL lokal (port 3306, database dt_system).
6. **Dual-Mode**: Web Dashboard modern (Mobile/Desktop) + Bot Telegram terintegrasi.

---

## 🚀 Cara Menjalankan Sistem di Komputer Lokal

1. **Buka Terminal / PowerShell di folder ini:**
   `powershell
   cd "D:\ADITYA PUTRA\MyProjects\ADT-System"
   `

2. **Jalankan Aplikasi:**
   `powershell
   .\.venv\Scripts\python.exe run.py
   `
   *(atau cukup python run.py jika virtual environment sudah diaktifkan)*

3. **Buka Web Dashboard di Browser:**
   - **Dashboard Utama**: [http://localhost:8000](http://localhost:8000)
   - **Manajemen SPH**: [http://localhost:8000/sph](http://localhost:8000/sph)
   - **Manajemen PO**: [http://localhost:8000/po](http://localhost:8000/po)
   - **Laporan Laba & Bagi Hasil**: [http://localhost:8000/financial](http://localhost:8000/financial)
   - **Dokumentasi API Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
