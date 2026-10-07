"""
Buat banyak Origination berturut-turut, masing-masing dengan nama customer yang berbeda.

    .venv\\Scripts\\python -m generate.batch --rencana     # buat/lihat rencana saja, tanpa menjalankan
    .venv\\Scripts\\python -m generate.batch               # jalankan (atau teruskan) rencana
    .venv\\Scripts\\python -m generate.batch --headless
    .venv\\Scripts\\python -m generate.batch --baru        # buang rencana lama, buat rencana baru

Komposisi ada di KOMPOSISI di bawah (bawaan: 2 Konven, 2 Syariah, 6 Konven + Syariah).

Setiap run memakai nama perusahaan dasar yang berbeda dari daftar PERUSAHAAN (tidak ada yang
dipakai dua kali) ditambah kode acak 4 huruf yang juga unik, mis. "Pelindo Samudra Oto KQXM".
Rencana (nama, skenario, berkas jejak, status) disimpan di runs/jejak_batch.json, dan tiap run
punya jejak sendiri (runs/jejak_batch_NN.json), jadi run yang gagal bisa diteruskan tanpa
membuat customer baru.

Run dijalankan satu per satu (akunnya sama), masing-masing sebagai proses generate.jalankan terpisah.
Batch BERHENTI pada run pertama yang gagal; perbaiki penyebabnya lalu jalankan generate.batch lagi:
run yang sudah selesai dilewati dan run yang gagal diteruskan dengan --lanjut.
"""
import argparse
import json
import random
import subprocess
import sys
import time

from core.config import FOLDER, FOLDER_RUN
from core.data_uji import PERUSAHAAN, kode_acak, nama_customer
from core.util import log
from generate.jejak import Jejak
from generate.skenario import SKENARIO

KOMPOSISI = [
    ('konven', 2),
    ('syariah', 2),
    ('konven-syariah', 6),
]
BERKAS_RENCANA = FOLDER_RUN / 'jejak_batch.json'


def buat_rencana() -> list[dict]:
    jumlah = sum(n for _, n in KOMPOSISI)
    if jumlah > len(PERUSAHAAN):
        raise SystemExit(f'Butuh {jumlah} nama perusahaan berbeda, PERUSAHAAN hanya punya {len(PERUSAHAAN)}.')
    dasar = random.sample(PERUSAHAAN, jumlah)
    kode = set()
    while len(kode) < jumlah:
        kode.add(kode_acak())
    nama = [nama_customer(d, k) for d, k in zip(dasar, kode)]

    rencana = []
    for skenario, n in KOMPOSISI:
        for _ in range(n):
            no = len(rencana) + 1
            rencana.append({'no': no, 'skenario': skenario, 'nama': nama[no - 1],
                            'jejak': f'jejak_batch_{no:02d}.json', 'status': 'belum'})
    return rencana


def simpan(rencana: list[dict]):
    FOLDER_RUN.mkdir(exist_ok=True)
    BERKAS_RENCANA.write_text(json.dumps(rencana, indent=1, ensure_ascii=False), encoding='utf-8')


def tampilkan(rencana: list[dict]):
    for r in rencana:
        fas = Jejak(FOLDER_RUN / r['jejak']).baca().get('fas_id', '')
        print(f"  {r['no']:>2}. {SKENARIO[r['skenario']].label:<17} {r['nama']:<34} {r['status']:<8} {fas}")


def main():
    ap = argparse.ArgumentParser(description='Buat banyak Origination dengan nama customer unik.')
    ap.add_argument('--rencana', action='store_true', help='hanya buat/tampilkan rencana, tanpa menjalankan')
    ap.add_argument('--baru', action='store_true', help='buang rencana lama dan buat rencana baru')
    ap.add_argument('--headless', action='store_true', help='jalankan browser tanpa jendela')
    arg = ap.parse_args()

    if BERKAS_RENCANA.exists() and not arg.baru:
        rencana = json.loads(BERKAS_RENCANA.read_text(encoding='utf-8'))
        log(f'Meneruskan rencana di {BERKAS_RENCANA.name}')
    else:
        for lama in FOLDER_RUN.glob('jejak_batch_*.json'):
            lama.unlink()
        rencana = buat_rencana()
        simpan(rencana)
        log(f'Rencana baru disimpan di {BERKAS_RENCANA.name}')
    tampilkan(rencana)
    if arg.rencana:
        return

    mulai = time.time()
    for r in rencana:
        if r['status'] == 'selesai':
            continue
        log(f"##### Run {r['no']}/{len(rencana)}: {SKENARIO[r['skenario']].label} — {r['nama']} #####")
        perintah = [sys.executable, '-m', 'generate.jalankan', '--skenario', r['skenario'],
                    '--nama', r['nama'], '--jejak', r['jejak']]
        if (FOLDER_RUN / r['jejak']).exists():
            perintah.append('--lanjut')
        if arg.headless:
            perintah.append('--headless')
        # stdin ditutup supaya run yang gagal tidak menunggu Enter; batch langsung berhenti.
        hasil = subprocess.run(perintah, cwd=FOLDER, stdin=subprocess.DEVNULL)
        r['status'] = 'selesai' if hasil.returncode == 0 else 'gagal'
        simpan(rencana)
        if hasil.returncode != 0:
            log(f"Run {r['no']} GAGAL. Perbaiki penyebabnya, lalu jalankan generate.batch lagi untuk meneruskan.")
            break

    log(f'Total waktu batch: {int(time.time() - mulai) // 60} menit')
    tampilkan(rencana)
    if any(r['status'] != 'selesai' for r in rencana):
        sys.exit(1)


if __name__ == '__main__':
    main()
