import re

with open("07_Service.txt", "rb") as f:
    raw = f.read()

texto = raw.decode("utf-8-sig")
lines = texto.split("\n")

count = 0
for i, l in enumerate(lines):
    stripped = l.strip()
    if stripped.startswith("|") and "D I S C R I M I N A" not in l:
        partes = [p.strip() for p in l.split("|")]
        partes = [p for p in partes if p != ""]
        for p in partes:
            if re.match(r"^[\d.]+\s*-\s*.+", p):
                count += 1
                break

print("Total linhas com produto:", count)
