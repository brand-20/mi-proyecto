"""Verifica que esta computadora tenga todo para usar la skill codigo-ingeniero-civil.

Uso:  python verificar_instalacion.py        (en Windows también: py verificar_instalacion.py)

Revisa Python, los archivos de la skill, los paquetes, la librería `civil`, los
tests y la plantilla. Por cada falla dice qué hacer. Al final ofrece copiar la
skill a Claude Code de esta computadora.
"""
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SKILL = RAIZ / ".claude" / "skills" / "codigo-ingeniero-civil"
LIBRERIA = SKILL / "scripts"
PAQUETES = ("pytest", "pandas", "openpyxl", "matplotlib")
DESTINO_CLAUDE = Path.home() / ".claude" / "skills" / "codigo-ingeniero-civil"


def ok(mensaje):
    print(f"  [OK] {mensaje}")


def falla(mensaje, solucion):
    print(f"  [X]  {mensaje}")
    print(f"       Solución: {solucion}")


def comando_pip():
    return f'"{sys.executable}" -m pip install -r "{RAIZ / "requirements.txt"}"'


def ejecutar(argumentos):
    """Corre un comando con salida UTF-8 (evita errores con φ, ρ, ² en Windows)."""
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return subprocess.run(
        argumentos, cwd=SKILL, env=entorno, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def verificar_python():
    print("\n1. Python")
    version = ".".join(map(str, sys.version_info[:3]))
    if sys.version_info < (3, 10):  # noqa: UP036 -- debe avisar justamente en Python antiguo
        falla(
            f"Python {version} es muy antiguo; se necesita 3.10 o más nuevo.",
            "instala la última versión desde https://www.python.org/downloads/ "
            'y marca "Add python.exe to PATH" durante la instalación.',
        )
        return False
    ok(f"Python {version} en {sys.executable}")
    return True


def verificar_archivos():
    print("\n2. Archivos de la skill")
    if not (SKILL / "SKILL.md").is_file() or not (LIBRERIA / "civil").is_dir():
        falla(
            f"No se encuentra la skill en {SKILL}",
            "descarga el repositorio completo y deja este archivo en la carpeta principal. "
            "La carpeta .claude es oculta: en Mac pulsa Cmd+Shift+. en el Finder; "
            "en Windows, Explorador > Vista > Mostrar > Elementos ocultos.",
        )
        return False
    ok(f"Skill encontrada en {SKILL}")
    return True


def verificar_paquetes():
    print("\n3. Paquetes de Python")
    faltan = []
    for nombre in PAQUETES:
        try:
            modulo = importlib.import_module(nombre)
            ok(f"{nombre} {getattr(modulo, '__version__', '')}")
        except ImportError:
            faltan.append(nombre)
    if faltan:
        falla(
            f"Faltan: {', '.join(faltan)}",
            f"haz doble clic en instalar_windows.bat (Windows), o ejecuta:\n       {comando_pip()}",
        )
    return not faltan


def verificar_libreria():
    print("\n4. Librería civil")
    sys.path.insert(0, str(LIBRERIA))
    try:
        from civil.concreto_e060 import As_flexion
        from civil.unidades import TONF_M_A_KGF_CM
    except Exception as e:  # cualquier error de importación se reporta igual
        falla(f"No se pudo importar civil: {e}", "vuelve a descargar la carpeta .claude completa.")
        return False
    As = As_flexion(12 * TONF_M_A_KGF_CM, f_c=210, fy=4200, b=25, d=44)
    if abs(As - 7.88) > 0.01:
        falla(f"Resultado inesperado: As = {As:.2f} cm² (esperado 7.88)", "vuelve a descargar los archivos.")
        return False
    ok(f"Viga 25x50, Mu = 12 tonf·m -> As = {As:.2f} cm² (correcto)")
    return True


def verificar_tests():
    print("\n5. Tests")
    r = ejecutar([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "scripts"])
    ultima = (r.stdout.strip().splitlines() or ["sin salida"])[-1]
    if r.returncode != 0:
        falla(f"Fallaron tests: {ultima}", "envía este mensaje completo para revisarlo:\n" + r.stdout[-1500:])
        return False
    ok(ultima)
    return True


def verificar_plantilla():
    print("\n6. Plantilla de memoria de cálculo")
    r = ejecutar([sys.executable, str(SKILL / "assets" / "plantilla_calculo.py")])
    if r.returncode != 0 or "CUMPLE" not in r.stdout:
        falla("La plantilla no se ejecutó", "envía este error para revisarlo:\n" + (r.stderr or r.stdout)[-1500:])
        return False
    diseno = next((linea.strip() for linea in r.stdout.splitlines() if "As requerido" in linea), "")
    ok(f"Memoria generada: {diseno}")
    return True


def ofrecer_copia_claude_code():
    """Copia la skill a ~/.claude/skills si Claude Code está instalado en esta computadora."""
    if not (Path.home() / ".claude").is_dir():
        print("\n   Claude Code no está instalado aquí. En la app o la web de Claude usa el archivo")
        print("   codigo-ingeniero-civil.skill (botón 'Save skill'); ese método no necesita Python.")
        return
    estado = "actualizar" if DESTINO_CLAUDE.exists() else "instalar"
    try:
        respuesta = input(f"\n¿{estado.capitalize()} la skill en Claude Code de esta computadora? (s/n): ")
    except EOFError:
        respuesta = "n"
    if respuesta.strip().lower() not in ("s", "si", "sí", "y"):
        print(f"   No se copió. Para hacerlo luego, copia {SKILL} a {DESTINO_CLAUDE.parent}")
        return
    shutil.copytree(SKILL, DESTINO_CLAUDE, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    ok(f"Skill copiada a {DESTINO_CLAUDE}. Reinicia Claude Code para que la cargue.")


def main():
    print("=== Verificación: skill codigo-ingeniero-civil ===")
    if not verificar_python() or not verificar_archivos():
        return 1
    pasos = [verificar_paquetes()]
    if pasos[0]:
        pasos += [verificar_libreria(), verificar_tests(), verificar_plantilla()]
    if all(pasos):
        print("\nTODO FUNCIONA en esta computadora.")
        ofrecer_copia_claude_code()
        return 0
    print("\nHay problemas: corrige los [X] de arriba y vuelve a ejecutar este archivo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
