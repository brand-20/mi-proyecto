#!/usr/bin/env bash
# Instalador para Mac y Linux. Ejecutar en la Terminal:  bash instalar_mac_linux.sh
# Crea un entorno virtual .venv (Mac y Linux recientes no dejan instalar paquetes
# en el Python del sistema), instala los paquetes y verifica la skill.
set -u
cd "$(dirname "$0")" || exit 1

PY=""
for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1 &&
        "$candidato" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
        PY="$candidato"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[X] No se encontró Python 3.10 o más nuevo."
    echo "    Mac:   descárgalo de https://www.python.org/downloads/"
    echo "    Linux: sudo apt install python3 python3-venv"
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "Creando entorno virtual .venv ..."
    "$PY" -m venv .venv || { echo "[X] No se pudo crear .venv. En Linux: sudo apt install python3-venv"; exit 1; }
fi

echo "Instalando paquetes (pytest, pandas, openpyxl, matplotlib)..."
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt ||
    { echo "[X] Falló la instalación de paquetes. Revisa tu conexión a internet."; exit 1; }

.venv/bin/python verificar_instalacion.py
estado=$?
echo
echo "Para usar la librería en tus scripts, activa el entorno con:  source .venv/bin/activate"
exit $estado
