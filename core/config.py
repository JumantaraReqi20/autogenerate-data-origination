import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
BERKAS_KONFIG = FOLDER / 'config.json'
BERKAS_PDF = FOLDER / 'assets' / 'dokumen.pdf'

# Jejak run & bukti kegagalan — berisi data run dan isi halaman aplikasi, tidak di-commit.
FOLDER_RUN = FOLDER / 'runs'
ARTEFAK = FOLDER_RUN / 'artefak'


def baca_konfig(berkas: Path = BERKAS_KONFIG) -> dict:
    if not berkas.exists():
        raise SystemExit(f'{berkas.name} tidak ada. Salin config.example.json menjadi config.json lalu isi.')
    return json.loads(berkas.read_text(encoding='utf-8'))
