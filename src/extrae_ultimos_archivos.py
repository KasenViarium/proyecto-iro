import os
import json
import time
from pathlib import Path

def obtener_ultimo_watermark(config_file):
    """Lee el timestamp de la última ejecución exitosa desde el archivo de control."""
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f).get("ultima_ejecucion_exitosa", 0)
        except:
            return 0
    return 0

def buscar_novedades(ruta_origen, timestamp_referencia, margen_segundos):
    """Escanea la ruta de origen buscando carpetas modificadas después del timestamp de referencia."""
    novedades = []
    # Capturamos el inicio real del escaneo
    tiempo_inicio_scan = time.time()
    
    # El nuevo watermark será el inicio del scan menos el margen de seguridad
    # Esto protege contra archivos que entren MIENTRAS el glob está trabajando
    proximo_watermark = tiempo_inicio_scan - margen_segundos

    print(f"📂 Escaneando: {ruta_origen}...")
    # Nivel 4: IATA/Año/Mes/Empresa
    for p_empresa in ruta_origen.glob("*/*/*/*"): 
        if p_empresa.is_dir():
            try:
                mtime = p_empresa.stat().st_mtime
                if mtime > timestamp_referencia:
                    partes = p_empresa.relative_to(ruta_origen).parts
                    novedades.append({
                        "ruta_completa": str(p_empresa),
                        "iata": partes[0],
                        "anio": partes[1],
                        "mes": partes[2],
                        "empresa": partes[3],
                        "mtime_carpeta": mtime
                    })
            except Exception as e:
                print(f"⚠️ No se pudo leer {p_empresa}: {e}")
    
    return novedades, proximo_watermark

def actualizar_control(config_file, ts, comentario_extra=""):
    """Actualiza el archivo de control con el nuevo timestamp y un comentario."""
    with open(config_file, 'w') as f:
        json.dump({
            "ultima_ejecucion_exitosa": ts,
            "comentario": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} | {comentario_extra}"
        }, f, indent=4)

if __name__ == "__main__":
    # 1. Cargar Configuración
    with open("config.json", 'r') as f:
        config = json.load(f)
    
    ORIGEN = Path(config["RUTA_ORIGEN"])
    FILE_CONTROL = config["CONFIG_FILE"]
    FILE_OUT = config["OUTPUT_FILE"]
    MARGEN = config.get("TIEMPO_MARGEN_SEGUNDOS", 300) # 5 min por defecto

    # 2. Obtener Watermark actual
    watermark = obtener_ultimo_watermark(FILE_CONTROL)
    print(f"🔍 Buscando cambios desde: {time.ctime(watermark)}")

    # 3. Detectar Novedades
    lista_novedades, nuevo_ts = buscar_novedades(ORIGEN, watermark, MARGEN)

    # 4. Procesar Resultados
    if lista_novedades:
        with open(FILE_OUT, 'w', encoding='utf-8') as f:
            json.dump(lista_novedades, f, indent=4)
        
        print(f"✅ Identificadas {len(lista_novedades)} rutas nuevas.")
        # Y solo si la copia termina bien, actualizas el Watermark
        actualizar_control(FILE_CONTROL, nuevo_ts, "Cambios detectados")
    else:
        print("💤 No hay carpetas modificadas.")
        # Actualizamos para mantener el pipeline "vivo"
        actualizar_control(FILE_CONTROL, nuevo_ts, "Ejecución sin novedades")