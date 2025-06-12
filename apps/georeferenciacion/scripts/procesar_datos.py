import pandas as pd
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def limpiar_nombre(nombre):
    return re.sub(r"^\s*\d+\.\s*", "", str(nombre)).strip()

def corregir_escala(series):
    s = pd.to_numeric(series, errors="coerce")
    s = s.apply(lambda x: x / 1e14 if x > 1e4 else x)
    return s

def procesar_datos():
    print("📥 Cargando archivo: puntos_artes.xlsx...")
    df_cultura = pd.read_excel(os.path.join(DATA_DIR, "puntos_artes.xlsx"), header=2)
    df_cultura = df_cultura.iloc[:, [3, 6, 7, 8]]
    df_cultura.columns = ["NOMBRE", "DIRECCION", "LATITUD", "LONGITUD"]
    df_cultura["NOMBRE"] = df_cultura["NOMBRE"].apply(limpiar_nombre)
    df_cultura["LATITUD"] = corregir_escala(df_cultura["LATITUD"])
    df_cultura["LONGITUD"] = corregir_escala(df_cultura["LONGITUD"])
    df_cultura["TIPO"] = "Cultura"

    print("📥 Cargando archivo: puntos_deportes.xlsx...")
    df_deportes = pd.read_excel(os.path.join(DATA_DIR, "puntos_deportes.xlsx"), header=1)
    df_deportes = df_deportes.iloc[:, [4, 5, 7, 8]]
    df_deportes.columns = ["NOMBRE", "DIRECCION", "LATITUD", "LONGITUD"]
    df_deportes["NOMBRE"] = df_deportes["NOMBRE"].apply(limpiar_nombre)
    df_deportes["LATITUD"] = corregir_escala(df_deportes["LATITUD"])
    df_deportes["LONGITUD"] = corregir_escala(df_deportes["LONGITUD"])
    df_deportes["TIPO"] = "Deporte"

    df_final = pd.concat([df_cultura, df_deportes], ignore_index=True)
    df_final = df_final[
        df_final["LATITUD"].between(4.55, 4.75) &
        df_final["LONGITUD"].between(-74.25, -74.00)
    ]

    output_file = os.path.join(DATA_DIR, "escuelas.csv")
    df_final.to_csv(output_file, index=False)
    print(f"✅ Archivo '{output_file}' generado correctamente.")
