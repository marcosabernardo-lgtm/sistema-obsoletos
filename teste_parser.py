@'
import re

def to_float(s):
    if not s: return None
    s = str(s).strip().replace(".", "").replace(",", ".")
    try: return float(s)
    except: return None

def parse_linha(line):
    partes = [p.strip() for p in line.split("|")]
    partes = [p for p in partes if p != ""]
    if len(partes) < 4: return None
    cod_idx = None
    for i, p in enumerate(partes):
        if re.match(r"^[\d.]+\s*-\s*.+", p):
            cod_idx = i
            break
    if cod_idx is None: return None
    match_cod = re.match(r"^([\d.]+)\s*-\s*(.*)", partes[cod_idx])
    if not match_cod: return None
    codigo, descricao = match_cod.groups()
    remaining = partes[cod_idx+1:]
    if len(remaining) < 2: return None
    qtd_str = remaining[1]
    valores = remaining[2:]
    quantidade = to_float(qtd_str)
    if len(valores) >= 3:
        vlr_unit = to_float(valores[0])
        parcial  = to_float(valores[1])
        total    = to_float(valores[2])
        if total is None and parcial is not None: total = parcial
    elif len(valores) >= 2:
        vlr_unit = to_float(valores[0])
        total    = to_float(valores[1])
    else: return None
    if quantidade is None or vlr_unit is None: return None
    return codigo.strip()

with open("07_Service.txt", "r", encoding="latin-1") as f:
    lines = f.readlines()

codigos = []
for l in lines:
    if l.strip().startswith("|") and "D I S C R I M I N A" not in l:
        r = parse_linha(l)
        if r:
            codigos.append(r)

print("Total extraido:", len(codigos))
for cod in ["008287", "008271", "008273", "008283"]:
    print(cod, "encontrado:", cod in codigos)
'@ | Set-Content teste_parser.py -Encoding UTF8
python teste_parser.py
