"""Construye notebooks/AstroShield.ipynb a partir del código del repositorio.

El notebook es autocontenido para Google Colab: sus primeras celdas recrean el
paquete `astroshield`, las pruebas y los datos de referencia con %%writefile,
así que el código que corre en Colab es byte a byte el de este repositorio.
Toda la información (globo, gráficas, pruebas e interpretaciones) vive en el
centro de control; el notebook solo tiene las celdas que necesitan Python.

Uso:  python herramientas/construir_notebook.py [--ejecutar]
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import sys
import textwrap
from pathlib import Path

import nbformat as nbf

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

RAIZ = Path(__file__).resolve().parents[1]
RUTA_NB = RAIZ / "notebooks" / "AstroShield.ipynb"
MODULOS = ["__init__", "geometria", "escenario", "evaluacion", "algoritmo_genetico", "referencias", "experimentos",
           "visualizacion", "plantilla_centro_control", "centro_control"]
PRUEBAS = ["test_modelo", "test_algoritmo_genetico", "test_visualizacion", "test_centro_control"]

celdas = []


def md(texto):
    celdas.append(nbf.v4.new_markdown_cell(textwrap.dedent(texto).strip("\n")))


def codigo(fuente, oculta=False):
    c = nbf.v4.new_code_cell(textwrap.dedent(fuente).strip("\n"))
    if oculta:
        c.metadata["cellView"] = "form"
    celdas.append(c)


def datos_referencia_b64() -> str:
    """Datos del centro de control de la ejecución de referencia, comprimidos."""
    ruta_datos = RAIZ / "outputs" / "datos_centro_control.json"
    if not ruta_datos.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta_datos}.\n"
            "Debes ejecutar primero 'python herramientas/ejecutar_experimentos.py' "
            "para generar los datos necesarios."
        )
    
    crudo = ruta_datos.read_bytes()
    
    b64 = base64.b64encode(gzip.compress(crudo, mtime=0)).decode("ascii")
    return "\n".join(textwrap.wrap(b64, 100))


def construir(R):
    e2, e7 = R["E2"], R["E7"]["resumen"]
    md(f"""
    # 🛰️ AstroShield — Centro de control

    Algoritmo genético que diseña una constelación de **8 satélites** para observar **6 regiones prioritarias**,
    respetando **zonas de desechos espaciales** y **posiciones ocupadas**. Ejecución de referencia: fitness
    **{e2['fitness']:.4f}** ({100 * e2['fitness'] / e2['cota']:.2f}% de la cota de referencia), {e2['regiones_cubiertas']}/6 regiones,
    0 violaciones; {e7['ag_aceptadas']}/{e7['n_ejecuciones']} semillas aceptadas.

    **Cómo usarlo en Colab:** `Entorno de ejecución → Ejecutar todo`. Si Colab avisa que el notebook no es de Google,
    elige **Ejecutar de todos modos** (no usa tu Drive ni pide permisos).

    1. **Instalación** (celdas ocultas): crea el paquete `astroshield`, las pruebas y los datos de referencia.
    2. **Configuración:** elige el modo de ejecución.
    3. **Centro de control:** aparece **al instante** con la ejecución de referencia. Globo 3D o mapa 2D (interruptor
       arriba a la derecha), línea de tiempo de la evolución y una pestaña por cada prueba (E1–E10).
    4. **Ejecutar:** corre el algoritmo de verdad (≈ 4 min en modo completo) y **actualiza el mismo centro de control**
       con los datos nuevos.
    5. **Laboratorio** (opcional): cambia las condiciones y observa el efecto.
    6. **Descargar** los resultados y el centro de control como página HTML.
    """)

    md("""
    ## 1. Instalación del paquete `astroshield`

    Cada celda escribe un archivo del repositorio. Están ocultas para no estorbar; ábrelas para revisar el código.
    """)
    codigo("import os\nfor carpeta in ('astroshield', 'pruebas', 'outputs'):\n    os.makedirs(carpeta, exist_ok=True)")
    for m in MODULOS:
        fuente = (RAIZ / "astroshield" / f"{m}.py").read_text(encoding="utf-8")
        codigo(f"%%writefile astroshield/{m}.py\n{fuente}", oculta=True)
    for t in PRUEBAS:
        fuente = (RAIZ / "pruebas" / f"{t}.py").read_text(encoding="utf-8")
        codigo(f"%%writefile pruebas/{t}.py\n{fuente}", oculta=True)
    codigo("%%writefile pytest.ini\n[pytest]\ntestpaths = pruebas\npythonpath = .", oculta=True)
    codigo("#@title Datos de la ejecución de referencia (comprimidos)\n"
           "import base64, gzip\n"
           f'REFERENCIA_B64 = """\n{datos_referencia_b64()}\n"""\n'
           'with open("outputs/datos_referencia.json", "wb") as fh:\n'
           '    fh.write(gzip.decompress(base64.b64decode("".join(REFERENCIA_B64.split()))))\n'
           'print("Datos de referencia listos.")', oculta=True)

    md("## 2. Configuración")
    codigo("""
    #@title Configuración de la ejecución { display-mode: "form" }
    MODO = "completo"  #@param ["completo", "rápido", "solo referencia"]
    #@markdown **completo** ≈ 4 min (parámetros finales, 10 semillas) · **rápido** ≈ 1 min · **solo referencia** no ejecuta el AG.
    import importlib, importlib.util, json, subprocess, sys, warnings
    EN_COLAB = "google.colab" in sys.modules
    REQUERIDAS = ["numpy", "scipy", "pandas", "matplotlib", "pytest"]
    faltan = [m for m in REQUERIDAS if importlib.util.find_spec(m) is None]
    if faltan:
        print("Instalando:", faltan)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *faltan])
    warnings.filterwarnings("ignore")
    sys.path.insert(0, ".")
    for _m in [m for m in sys.modules if m == "astroshield" or m.startswith("astroshield.")]:
        del sys.modules[_m]  # al volver a ejecutar, toma los cambios de las celdas %%writefile
    import numpy as np
    import astroshield
    from astroshield import experimentos as X
    from astroshield import centro_control as CC
    from astroshield.algoritmo_genetico import ParametrosAG, ejecutar_ag
    from astroshield.escenario import Zona, escenario_base
    if MODO == "completo":
        PARAMETROS, N_SEMILLAS, N_ABLACION = ParametrosAG(), 10, 5
    else:
        PARAMETROS, N_SEMILLAS, N_ABLACION = ParametrosAG(generaciones=120, tam_poblacion=80), 4, 2
    print(f"AstroShield {astroshield.__version__} · modo: {MODO} · Python {sys.version.split()[0]} · Colab: {EN_COLAB}")
    """)

    md("""
    ## 3. Centro de control

    Se abre con la **ejecución de referencia** y la sección 4 lo actualiza con tu ejecución. Usa el selector
    *Configuración en el mapa* para ver cualquier prueba en el globo, el botón ▶ para reproducir la evolución y
    *Comparar con inicial* para ver qué cambió. Todos los textos de interpretación se calculan con los datos mostrados.
    """)
    codigo("""
    with open("outputs/datos_referencia.json", encoding="utf-8") as fh:
        DATOS = json.load(fh)
    DATOS["modo"] = "referencia"
    PANEL = CC.mostrar_centro_control(DATOS)
    """)

    md("## 4. Ejecutar el algoritmo y actualizar el centro de control")
    codigo("""
    if MODO == "solo referencia":
        print("Modo «solo referencia»: el centro de control muestra la ejecución de referencia.")
    else:
        TODO = X.ejecutar_todo(PARAMETROS, n_semillas=N_SEMILLAS, n_ablacion=N_ABLACION, progreso=True)
        print("Pruebas unitarias...", flush=True)
        PRUEBAS = CC.ejecutar_pruebas_unitarias(".")
        print(" ", PRUEBAS["resumen"])
        DATOS = CC.datos_centro_control(TODO, PRUEBAS, modo=MODO)
        CC.mostrar_centro_control(DATOS, PANEL)
        CC.guardar_centro_control(DATOS, "outputs/centro_control.html")
        with open("outputs/resultados.json", "w", encoding="utf-8") as fh:
            json.dump(X.resumen_resultados(TODO), fh, ensure_ascii=False, indent=2, default=str)
        b = TODO["base"].eval_mejor
        print(f"\\nEjecución principal: fitness {b.fitness:.4f}, {b.n_cubiertas}/6 regiones, válida: {b.factible}.")
        print("↑ El centro de control de la sección 3 ya muestra esta ejecución.")
    """)

    md("""
    ## 5. Laboratorio (opcional)

    Cambia las condiciones y ejecuta la celda. La solución de la ejecución principal se **revalida** con las nuevas
    condiciones y luego se reoptimiza; ambas aparecen en el centro de control, en el grupo *Laboratorio*.
    """)
    codigo("""
    #@title Escenario personalizado { run: "manual", display-mode: "form" }
    prioridad_australia = "alta"  #@param ["alta", "media", "normal"]
    techo_altitud_km = 2000  #@param {type:"slider", min:600, max:2000, step:100}
    nueva_zona_lat = 36.0  #@param {type:"number"}
    nueva_zona_lon = 138.0  #@param {type:"number"}
    nueva_zona_radio = 0.0  #@param {type:"slider", min:0, max:20, step:0.5}
    generaciones = 200  #@param {type:"slider", min:20, max:600, step:20}
    semilla = 42  #@param {type:"integer"}
    ejecutar_laboratorio = False  #@param {type:"boolean"}
    #@markdown Marca la casilla y ejecuta esta celda para probar tu escenario.

    anterior = escenario_base()
    lab = anterior.con_prioridad("Interior de Australia", prioridad_australia, nombre="Laboratorio")
    lab = lab.con_parametros(alt_max_km=float(techo_altitud_km))
    if nueva_zona_radio > 0:
        lab = lab.con_zona(Zona("Zona del laboratorio", nueva_zona_lat, nueva_zona_lon, nueva_zona_radio), nombre="Laboratorio")
    if not ejecutar_laboratorio:
        print("Laboratorio desactivado: marca «ejecutar_laboratorio» y vuelve a ejecutar esta celda.")
    else:
        final_base = next(v for v in DATOS["vistas"] if v["id"] == "base")["cuadros"][-1]
        solucion_base = np.array([s[:3] for s in final_base["s"]])
        print("Solución base revalidada:", X.revalidar(solucion_base, anterior, lab))
        r_lab = ejecutar_ag(lab, ParametrosAG(generaciones=generaciones), semilla=semilla)
        print(f"Reoptimizada: fitness {r_lab.eval_mejor.fitness:.4f}, {r_lab.eval_mejor.n_cubiertas}/6 regiones, "
              f"válida: {r_lab.eval_mejor.factible}.")
        DATOS = CC.agregar_laboratorio(DATOS, r_lab, solucion_base, anterior)
        CC.mostrar_centro_control(DATOS, PANEL)
        print("↑ Revisa el grupo «Laboratorio» en el centro de control de la sección 3.")
    """)

    md("## 6. Descargar los resultados\n\nEmpaqueta el centro de control (HTML que se abre en cualquier navegador), "
       "`resultados.json` y el código en un `.zip`. En Colab se descarga automáticamente.")
    codigo("""
    import zipfile
    CC.guardar_centro_control(DATOS, "outputs/centro_control.html")
    with zipfile.ZipFile("astroshield_resultados.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for carpeta in ("outputs", "astroshield", "pruebas"):
            for raiz, _, archivos in os.walk(carpeta):
                for f in archivos:
                    if not f.endswith(".pyc"):
                        z.write(os.path.join(raiz, f))
    print("Creado astroshield_resultados.zip con", len(zipfile.ZipFile("astroshield_resultados.zip").namelist()), "archivos")
    if EN_COLAB:
        from google.colab import files
        files.download("astroshield_resultados.zip")
    """)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ejecutar", action="store_true", help="ejecuta el notebook para guardar sus salidas")
    args = ap.parse_args()
    
    ruta_resultados = RAIZ / "outputs" / "resultados.json"
    if not ruta_resultados.exists():
        print(f"Error: No se encontró '{ruta_resultados}'.")
        print("Por favor, ejecuta primero: python herramientas/ejecutar_experimentos.py")
        sys.exit(1)
        
    R = json.loads(ruta_resultados.read_text(encoding="utf-8"))
    
    construir(R)
    nb = nbf.v4.new_notebook()
    nb.cells = celdas
    nb.metadata.update({
        "colab": {"provenance": [], "toc_visible": True, "name": "AstroShield.ipynb"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    })
    RUTA_NB.parent.mkdir(exist_ok=True)
    if args.ejecutar:
        import tempfile

        from nbclient import NotebookClient

        with tempfile.TemporaryDirectory() as tmp:
            NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": tmp}}).execute()
    nbf.write(nb, RUTA_NB)
    print("escrito", RUTA_NB, "celdas:", len(nb.cells))


if __name__ == "__main__":
    sys.exit(main())