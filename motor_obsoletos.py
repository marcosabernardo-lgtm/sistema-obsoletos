import pandas as pd
import zipfile
import io
import os
import shutil
from pathlib import Path
from datetime import datetime


def executar_motor(uploaded_file):

    pasta_base = "temp_upload"

    if os.path.exists(pasta_base):
        shutil.rmtree(pasta_base)

    os.makedirs(pasta_base)

    # Extrai o ZIP enviado pelo usuário
    with zipfile.ZipFile(uploaded_file, 'r') as z:
        z.extractall(pasta_base)

    return None, None
