import os

from motor.motor_inventario import executar_motor_inventario
from storage.base_inventario_lake import salvar_fechamento_inventario

PASTA_DADOS = "analytics/dados_inventario"

if not os.path.exists(PASTA_DADOS):
    raise Exception("Pasta analytics/dados_inventario não encontrada")

arquivos = [f for f in os.listdir(PASTA_DADOS) if f.endswith(".zip")]

if len(arquivos) == 0:
    raise Exception("Nenhum ZIP encontrado em analytics/dados_inventario")

for arquivo in sorted(arquivos):

    caminho = os.path.join(PASTA_DADOS, arquivo)

    print("Processando:", arquivo)

    df_final, _ = executar_motor_inventario(caminho)

    salvar_fechamento_inventario(df_final)

    print("Salvo:", arquivo)

print("Processamento concluído.")
