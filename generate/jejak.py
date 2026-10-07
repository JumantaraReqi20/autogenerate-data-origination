import json
from pathlib import Path


class Jejak:
    """
    Catatan satu run (customer, pipeline_id, fas_id, fase_selesai) di sebuah berkas JSON.
    Dibaca ulang dari disk setiap kali, supaya --lanjut melihat keadaan terakhir walau run
    sebelumnya berhenti di tengah.
    """

    def __init__(self, berkas: Path):
        self.berkas = berkas

    def baca(self) -> dict:
        return json.loads(self.berkas.read_text(encoding='utf-8')) if self.berkas.exists() else {}

    def __getitem__(self, kunci: str):
        return self.baca()[kunci]

    def simpan(self, **isi):
        j = self.baca()
        j.update(isi)
        self.berkas.parent.mkdir(parents=True, exist_ok=True)
        self.berkas.write_text(json.dumps(j, indent=1, ensure_ascii=False), encoding='utf-8')

    def hapus(self):
        self.berkas.unlink(missing_ok=True)

    def fase_selesai(self) -> list[str]:
        return self.baca().get('fase_selesai', [])

    def tandai_selesai(self, fase: str):
        self.simpan(fase_selesai=self.fase_selesai() + [fase])
