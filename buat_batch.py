"""
Buat banyak Origination berturut-turut, masing-masing dengan nama customer yang berbeda.

    .venv\\Scripts\\python buat_batch.py --rencana     # buat/lihat rencana saja, tanpa menjalankan
    .venv\\Scripts\\python buat_batch.py               # jalankan (atau teruskan) rencana
    .venv\\Scripts\\python buat_batch.py --headless
    .venv\\Scripts\\python buat_batch.py --baru        # buang rencana lama, buat rencana baru

Komposisi ada di KOMPOSISI di bawah (bawaan: 2 Konven, 2 Syariah, 6 Konven + Syariah).

Setiap run memakai nama perusahaan dasar yang berbeda dari daftar PERUSAHAAN (tidak ada yang
dipakai dua kali) ditambah kode acak 4 huruf yang juga unik, mis. "Pelindo Samudra Oto KQXM".
Rencana (nama, skenario, berkas jejak, status) disimpan di jejak_batch.json, dan tiap run punya
jejak sendiri (jejak_batch_NN.json), jadi run yang gagal bisa diteruskan tanpa membuat customer baru.

Run dijalankan satu per satu (akunnya sama), sebagai proses terpisah. Batch BERHENTI pada run
pertama yang gagal; perbaiki penyebabnya lalu jalankan buat_batch.py lagi: run yang sudah
selesai dilewati dan run yang gagal diteruskan dengan --lanjut.
"""
import argparse
import json
import random
import subprocess
import sys
import time

from buat_origination import PERUSAHAAN
from los import FOLDER, log

KOMPOSISI = [
    ('Konven', 'buat_origination.py', 2),
    ('Syariah', 'buat_origination_syariah.py', 2),
    ('Konven + Syariah', 'buat_origination_konven_syariah.py', 6),
]
BERKAS_RENCANA = FOLDER / 'jejak_batch.json'


def buat_rencana() -> list[dict]:
    jumlah = sum(n for _, _, n in KOMPOSISI)
    if jumlah > len(PERUSAHAAN):
        raise SystemExit(f'Butuh {jumlah} nama perusahaan berbeda, PERUSAHAAN hanya punya {len(PERUSAHAAN)}.')
    dasar = random.sample(PERUSAHAAN, jumlah)
    kode = set()
    while len(kode) < jumlah:
        kode.add(''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=4)))
    nama = [f'{d} Oto {k}' for d, k in zip(dasar, kode)]

    rencana = []
    for skenario, skrip, n in KOMPOSISI:
        for _ in range(n):
            no = len(rencana) + 1
            rencana.append({'no': no, 'skenario': skenario, 'skrip': skrip, 'nama': nama[no - 1],
                            'jejak': f'jejak_batch_{no:02d}.json', 'status': 'belum'})
    return rencana


def simpan(rencana: list[dict]):
    BERKAS_RENCANA.write_text(json.dumps(rencana, indent=1, ensure_ascii=False), encoding='utf-8')


def tampilkan(rencana: list[dict]):
    for r in rencana:
        j = FOLDER / r['jejak']
        fas = json.loads(j.read_text(encoding='utf-8')).get('fas_id', '') if j.exists() else ''
        print(f"  {r['no']:>2}. {r['skenario']:<17} {r['nama']:<34} {r['status']:<8} {fas}")


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
        for lama in FOLDER.glob('jejak_batch_*.json'):
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
        log(f"##### Run {r['no']}/{len(rencana)}: {r['skenario']} — {r['nama']} #####")
        perintah = [sys.executable, str(FOLDER / r['skrip']), '--nama', r['nama'], '--jejak', r['jejak']]
        if (FOLDER / r['jejak']).exists():
            perintah.append('--lanjut')
        if arg.headless:
            perintah.append('--headless')
        # stdin ditutup supaya run yang gagal tidak menunggu Enter; batch langsung berhenti.
        hasil = subprocess.run(perintah, cwd=FOLDER, stdin=subprocess.DEVNULL)
        r['status'] = 'selesai' if hasil.returncode == 0 else 'gagal'
        simpan(rencana)
        if hasil.returncode != 0:
            log(f"Run {r['no']} GAGAL. Perbaiki penyebabnya, lalu jalankan buat_batch.py lagi untuk meneruskan.")
            break

    log(f'Total waktu batch: {int(time.time() - mulai) // 60} menit')
    tampilkan(rencana)
    if any(r['status'] != 'selesai' for r in rencana):
        sys.exit(1)


if __name__ == '__main__':
    main()
