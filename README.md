# mi-proyecto

## Skill: `codigo-ingeniero-civil`

Skill de Claude con mi estilo de código Python para ingeniería civil en Perú:
estructuras (E.060, E.030, E.020 y ACI 318 / ASCE 7), metrados, costos y
presupuestos (APU tipo S10) y programación de obras (CPM, Gantt, curva S).

Ubicación: `.claude/skills/codigo-ingeniero-civil/`. Claude Code la carga sola
al trabajar en este repositorio.

```
codigo-ingeniero-civil/
├── SKILL.md                 Reglas de estilo y flujo de trabajo
├── references/              Normas y criterios por especialidad
│   ├── estructuras.md       E.060, E.030, E.020, ACI 318 / ASCE 7
│   ├── metrados.md          Norma Técnica de Metrados, planilla de acero
│   ├── costos.md            APU, presupuesto, fórmula polinómica
│   └── programacion.md      CPM, calendario, curva S, valorizaciones
├── assets/
│   ├── plantilla_calculo.py Memoria de cálculo de una viga, ejecutable
│   └── ruff.toml            Linter con la notación de la norma permitida
└── scripts/
    ├── civil/               Librería probada (unidades, acero, E.060, E.030,
    │                        metrados, APU, CPM)
    └── tests/               Tests con casos verificados a mano
```

En la raíz del repositorio:

```
instalar_windows.bat         Instalador para Windows (doble clic)
instalar_mac_linux.sh        Instalador para Mac y Linux
verificar_instalacion.py     Revisa que todo funcione y dice qué corregir
requirements.txt             Paquetes de Python necesarios
```

## Instalar en una laptop nueva

### Lo que necesita la laptop

| Para usar... | Necesita |
|---|---|
| La skill en la app o la web de Claude | Solo iniciar sesión con **tu misma cuenta** y guardar el archivo `codigo-ingeniero-civil.skill` (botón "Save skill"). No necesita Python. |
| La skill en Claude Code | Claude Code instalado y con sesión iniciada, y la carpeta de la skill en `~/.claude/skills/` (el instalador la copia). |
| La librería `civil` en tus scripts | Python 3.10 o más nuevo y los paquetes de `requirements.txt` (el instalador los instala). |

### Pasos

1. **Python:** si no lo tienes, descárgalo de https://www.python.org/downloads/.
   En Windows, en la primera pantalla del instalador marca
   **"Add python.exe to PATH"**.
2. **Descarga este repositorio completo:** en GitHub, **Code → Download ZIP**, y
   descomprímelo. La carpeta `.claude` es **oculta**:
   - Windows: Explorador → Vista → Mostrar → Elementos ocultos.
   - Mac: en el Finder pulsa `Cmd + Shift + .`
3. **Ejecuta el instalador** desde la carpeta descomprimida:
   - Windows: doble clic en **`instalar_windows.bat`**.
   - Mac / Linux: en la Terminal, `bash instalar_mac_linux.sh`.

El instalador instala los paquetes y ejecuta `verificar_instalacion.py`, que
revisa todo (Python, archivos, paquetes, librería, 33 tests y la plantilla) y
dice en español qué corregir si algo falla. Al final ofrece copiar la skill a
Claude Code.

Para revisar sin instalar nada: `python verificar_instalacion.py`
(en Windows: `py verificar_instalacion.py`).

### Problemas comunes

| Mensaje | Causa y solución |
|---|---|
| `"python" no se reconoce...` o se abre la Microsoft Store | Python no está instalado o falta "Add to PATH". Reinstálalo marcando esa casilla. |
| `ModuleNotFoundError: No module named 'pandas'` (u otro) | Faltan paquetes: ejecuta el instalador. |
| `ModuleNotFoundError: No module named 'civil'` | El script no encuentra la librería: copia la carpeta `scripts/civil` junto a tu script. |
| Solo veo `README.md` | La carpeta `.claude` está oculta (ver paso 2). |
| `PermissionError` al exportar a Excel | El archivo `.xlsx` está abierto en Excel: ciérralo y vuelve a ejecutar. |
| `error: externally-managed-environment` (Mac/Linux) | Usa `instalar_mac_linux.sh`, que crea un entorno `.venv`. |
| La skill no aparece en Claude | Inicia sesión con la misma cuenta donde la guardaste, o reinicia Claude Code después de copiarla. |

Los valores normativos marcados **(verificar)** en `references/` deben
contrastarse con el texto oficial vigente antes de usarlos en un expediente.
