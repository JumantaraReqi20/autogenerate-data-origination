"""
Buat satu Origination dari nol sampai berstatus "Completed".

    .venv\\Scripts\\python -m generate.jalankan                            # skenario Konven, browser terlihat
    .venv\\Scripts\\python -m generate.jalankan --skenario syariah
    .venv\\Scripts\\python -m generate.jalankan --skenario konven-syariah  # dua fasilitas dalam satu pipeline
    .venv\\Scripts\\python -m generate.jalankan --lanjut                   # teruskan run yang gagal di tengah
    .venv\\Scripts\\python -m generate.jalankan --headless --sampai 3

MEMBUAT DATA SUNGGUHAN di base_url (config.json): customer baru, pipeline, origination
(FAS-xxxxx), dan dokumen.
"""
import argparse
import sys

from core.config import FOLDER_RUN, baca_konfig
from generate.alur import FASE, jalankan
from generate.skenario import SKENARIO


def main():
    ap = argparse.ArgumentParser(description='Buat satu Origination sampai Completed.')
    ap.add_argument('--skenario', choices=SKENARIO, default='konven', help='skenario pembiayaan (bawaan: konven)')
    ap.add_argument('--lanjut', action='store_true', help='teruskan run sebelumnya (lewati fase yang sudah selesai)')
    ap.add_argument('--headless', action='store_true', help='jalankan tanpa jendela browser')
    ap.add_argument('--sampai', type=int, default=len(FASE), help='berhenti setelah fase ke-N (1-based)')
    ap.add_argument('--nama', help='nama customer baru (bawaan: acak); dipakai generate.batch supaya unik')
    ap.add_argument('--jejak', help='berkas jejak run di runs/ (bawaan: per skenario)')
    arg = ap.parse_args()

    skenario = SKENARIO[arg.skenario]
    berhasil = jalankan(baca_konfig(), skenario, FOLDER_RUN / (arg.jejak or skenario.berkas_jejak),
                        lanjut=arg.lanjut, headless=arg.headless, sampai=arg.sampai, nama_customer=arg.nama)
    sys.exit(0 if berhasil else 1)


if __name__ == '__main__':
    main()
