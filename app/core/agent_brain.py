import json
import logging
import time
from typing import List, Dict, Any
from mistralai.client import Mistral
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgentBrain:
    def __init__(self):
        self.api_key = settings.MISTRAL_API_KEY
        self.base_url = settings.MISTRAL_BASE_URL
        
        if self.api_key:
            if self.base_url and "api.mistral.ai" not in self.base_url:
                self.client = Mistral(api_key=self.api_key, server_url=self.base_url)
            else:
                self.client = Mistral(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("Mistral AI API key is missing!")

    def _get_candidate_models(self) -> List[str]:
        configured = settings.MISTRAL_MODEL or "open-mistral-nemo"
        candidates = [
            configured,
            "open-mistral-nemo",
            "ministral-8b-latest",
            "open-mistral-7b",
            "mistral-small-latest",
        ]
        # Remove duplicates while preserving priority order
        return list(dict.fromkeys(candidates))

    def _complete_json(self, system_prompt: str, user_content: str) -> Dict[str, Any]:
        """
        Executes chat completion with json_object response format, automatically falling back
        to alternative Mistral models if rate-limited (429), quota-exceeded, or temporarily unavailable.
        """
        if not self.client:
            raise ValueError("Mistral AI client belum dikonfigurasi. Pastikan MISTRAL_API_KEY terisi di .env")

        models = self._get_candidate_models()
        last_error = None

        for model in models:
            for attempt in range(2):
                try:
                    response = self.client.chat.complete(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1
                    )
                    raw_text = response.choices[0].message.content.strip()
                    
                    # Strip markdown json fences if any
                    if raw_text.startswith("```"):
                        lines = raw_text.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        raw_text = "\n".join(lines).strip()

                    parsed = json.loads(raw_text)
                    return parsed
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    logger.warning(f"Mistral AI model '{model}' (attempt {attempt+1}) encounter error: {err_str}")
                    
                    # If rate limited (429) or tier forbidden (403), skip immediately to the next candidate model
                    if any(indicator in err_str.lower() for indicator in ["429", "rate_limited", "rate limit", "403", "tier_not_allowed"]):
                        break
                    
                    time.sleep(0.5)

        logger.error(f"Semua model fallback Mistral gagal dipanggil. Error terakhir: {last_error}")
        raise last_error

    def parse_sph_instruction(self, text: str) -> dict:
        """
        Extracts structured SPH entities from free-text user prompt using Mistral AI.
        """
        system_prompt = (
            "Anda adalah AI Agent extractor untuk sistem ERP PT Anugrah Djaya Tunggal.\n"
            "Tugas Anda adalah membaca instruksi pembuatan Surat Penawaran Harga (SPH) dari pengguna "
            "dan mengekstrak data berikut dalam format JSON:\n"
            "{\n"
            "  \"company_name\": \"Nama PT / Perusahaan tujuan (misal PT Dellifood Sentosa, PT Astari Niagara Internasional, dll, atau null jika tidak ada)\",\n"
            "  \"up_name\": \"Nama kontak person setelah UP (misal Bpk. Eko, Ibu Nana, Bpk. Tirta, atau null jika tidak ada)\",\n"
            "  \"items\": [\n"
            "    {\n"
            "      \"description\": \"Deskripsi dan Spesifikasi Teknis barang (misal: Shaft Fessa 20x627 mm, SPROCKET RS40BX1X15T BAUT ADJUSTER, dll)\",\n"
            "      \"price\": 580000\n"
            "    }\n"
            "  ],\n"
            "  \"has_warranty\": false,\n"
            "  \"warranty_days\": 14\n"
            "}\n"
            "Aturan:\n"
            "1. Jika nama PT tidak ditemukan, isi null.\n"
            "2. Jika UP tidak ditemukan, isi null.\n"
            "3. Bersihkan deskripsi barang agar bernada profesional, rapi, dan sesuai ejaan teknis.\n"
            "4. Harga satuan harus diekstrak sebagai angka integer/float bersih murni (misal: 580000).\n"
            "5. Hanya keluarkan JSON yang valid, tanpa teks penjelasan tambahan di luar JSON."
        )

        data = self._complete_json(system_prompt, text)
        
        # Ensure fallback data structure integrity
        if not isinstance(data, dict):
            data = {}
        if "items" not in data or not isinstance(data["items"], list):
            data["items"] = []
            
        return data

    def parse_sph_user_prompt(self, text: str) -> dict:
        """Alias for parse_sph_instruction."""
        return self.parse_sph_instruction(text)

    def parse_sph_pdf_text(self, text: str) -> dict:
        """
        Extracts structured SPH entities from raw PDF text of existing SPH documents.
        """
        system_prompt = (
            "Anda adalah AI Agent extractor untuk membaca dokumen Surat Penawaran Harga (SPH) PT Anugrah Djaya Tunggal.\n"
            "Tugas Anda adalah membaca teks hasil ekstraksi file PDF SPH dan mengekstrak data ke dalam format JSON berikut:\n"
            "{\n"
            "  \"company_name\": \"Nama PT / Perusahaan tujuan penawaran (misal PT Dellifood Sentosa, PT Astari Niagara Internasional, dll)\",\n"
            "  \"up_name\": \"Nama kontak person setelah UP (misal Bpk. Fikri, Ibu Nana, Bpk. Tirta)\",\n"
            "  \"items\": [\n"
            "    {\n"
            "      \"description\": \"Deskripsi dan Spesifikasi Teknis barang\",\n"
            "      \"price\": 235000\n"
            "    }\n"
            "  ],\n"
            "  \"has_warranty\": false,\n"
            "  \"warranty_days\": 14\n"
            "}\n"
            "Aturan:\n"
            "1. Ekstrak nama perusahaan tujuan dan kontak UP dengan teliti.\n"
            "2. Ekstrak seluruh daftar item barang dan harga satuannya sebagai angka integer/float murni tanpa titik atau Rp.\n"
            "3. Jika ada klausul garansi yang disebutkan, set has_warranty ke true dan catat jumlah harinya pada warranty_days.\n"
            "4. Hanya keluarkan JSON valid tanpa teks tambahan di luar JSON."
        )

        data = self._complete_json(system_prompt, f"Berikut adalah teks isi dokumen PDF SPH:\n\n{text[:8000]}")
        if not isinstance(data, dict):
            data = {}
        if "items" not in data or not isinstance(data["items"], list):
            data["items"] = []
        return data

    def parse_po_pdf_text(self, text: str) -> dict:
        """
        Extracts structured Purchase Order (PO) entities from raw PDF text using Mistral AI.
        """
        system_prompt = (
            "Anda adalah AI Agent extractor untuk membaca dokumen Purchase Order (PO) resmi dari klien PT Anugrah Djaya Tunggal.\n"
            "Tugas Anda adalah membaca teks hasil ekstraksi file PDF Purchase Order dan mengekstrak entitas berikut ke dalam format JSON:\n"
            "{\n"
            "  \"po_number\": \"Nomor PO resmi dari klien (misal 6500288236, PO-DEL/2026/089)\",\n"
            "  \"client_name\": \"Nama Perusahaan Klien pembeli/penerbit PO (misal PT DELLIFOOD SENTOSA CORPINDO)\",\n"
            "  \"po_date\": \"Tanggal terbit PO (format YYYY-MM-DD jika bisa ditebak, atau teks tanggal aslinya)\",\n"
            "  \"total_po_amount\": 15000000,\n"
            "  \"items\": [\n"
            "    {\n"
            "      \"description\": \"Nama/spesifikasi barang\",\n"
            "      \"qty\": 1,\n"
            "      \"price\": 300000\n"
            "    }\n"
            "  ],\n"
            "  \"notes\": \"Catatan penting seperti syarat pembayaran (misal TOP 30 hari), lokasi kirim, atau terms lainnya.\"\n"
            "}\n"
            "Aturan:\n"
            "1. Cari nomor PO dengan sangat teliti. Pada PO sistem SAP (seperti PT DELLIFOOD), nomor PO adalah deretan 10 digit (contoh: 6500288236, 6500288789, 6500291183). Jangan gunakan kode vendor 6-digit (seperti 849136) sebagai nomor PO.\n"
            "2. Total PO amount harus berupa angka integer/float murni tanpa titik atau Rp.\n"
            "3. Hanya keluarkan JSON yang valid tanpa teks penjelasan tambahan di luar JSON."
        )

        data = self._complete_json(system_prompt, f"Berikut adalah isi teks dari dokumen PDF PO:\n\n{text[:8000]}")
        if not isinstance(data, dict):
            data = {}
        return data
