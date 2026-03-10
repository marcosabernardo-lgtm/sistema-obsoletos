import pandas as pd

df = pd.read_excel("base_obsolescencia.xlsx")

print(df.groupby("Fechamento").size())