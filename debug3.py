import re

with open("07_Service.txt", "rb") as f:
    raw = f.read()

texto = raw.decode("utf-8-sig")
lines = texto.split("\n")

empresa = None
filial = None
data = None
produtos = []

for l in lines:
    if "FIRMA:" in l:
        conteudo = l.split(":", 1)[1]
        texto2 = conteudo.replace("|","").strip()
        partes = re.split(r"\s{2,}", texto2)
        if len(partes) >= 2:
            empresa = partes[0].strip()
            filial = partes[1].strip()
    elif "ESTOQUES EXISTENTES EM:" in l:
        data = l.split("EM:", 1)[1].replace("|","").strip()
    elif l.strip().startswith("|") and "D I S C R I M I N A" not in l:
        partes = [p.strip() for p in l.split("|")]
        partes = [p for p in partes if p != ""]
        for p in partes:
            m = re.match(r"^([\d.]+)\s*-\s*.+", p)
            if m:
                key = f"{data}|{empresa}|{filial}|{m.group(1).strip()}"
                produtos.append(key)
                break

from collections import Counter
dup = {k: v for k, v in Counter(produtos).items() if v > 1}
print(f"Total: {len(produtos)}, Unicos: {len(set(produtos))}, Duplicatas: {len(dup)}")
for k, v in list(dup.items())[:10]:
    print(f"  {k} -> {v}x")
