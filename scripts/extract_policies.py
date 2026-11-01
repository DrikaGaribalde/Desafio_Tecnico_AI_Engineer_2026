"""Gera seções rastreáveis do PDF: py -3.12 -m scripts.extract_policies.

Requer pdftotext (Poppler); só a preparação requer esse executável.
"""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def extract(pdf: Path, executable: str) -> dict:
    result = subprocess.run([executable, "-raw", "-enc", "UTF-8", str(pdf), "-"],
                            capture_output=True, check=True)
    sections = []
    current = None
    last_number = (0,)
    for page, text in enumerate(result.stdout.decode("utf-8").split("\f"), start=1):
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("Página ") or line == "Empório da Música Manual de Políticas e Procedimentos":
                continue
            match = re.match(r"^(\d+(?:\.\d+)?)\.? ([^\u200b].+)$", line)
            if match:
                number = tuple(int(part) for part in match[1].split("."))
                # Evita confundir os passos numerados do fluxo 7.2 com seções.
                if number > last_number and number[0] <= 10:
                    current = {"id": match[1], "titulo": match[2], "paginas": [], "linhas": []}
                    sections.append(current)
                    last_number = number
                    continue
            if current is not None:
                if page not in current["paginas"]:
                    current["paginas"].append(page)
                current["linhas"].append(line.replace("\u200b", ""))
    for section in sections:
        section["texto"] = "\n".join(section.pop("linhas"))
    sections = [section for section in sections if section["texto"]]
    if not {"2", "3", "3.1", "4.1", "4.4", "5.1", "5.2", "6.2", "8.3"}.issubset({s["id"] for s in sections}):
        raise ValueError("Seções esperadas ausentes; revise a extração antes de usar.")
    return {"fonte": pdf.name, "sha256_pdf": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "extracao": "pdftotext -raw -enc UTF-8; sem resumo; cabeçalhos e rodapés removidos",
            "secoes": sections}


def main():
    executable = shutil.which("pdftotext")
    if not executable:
        raise SystemExit("pdftotext não encontrado. Instale/configure o Poppler para regenerar o arquivo derivado.")
    data = extract(ROOT / "data" / "políticas_da_loja.pdf", executable)
    target = ROOT / "data" / "politicas_secoes.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Geradas {len(data['secoes'])} seções em {target.name}.")


if __name__ == "__main__":
    main()
