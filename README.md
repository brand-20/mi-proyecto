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

### Probar

```bash
cd .claude/skills/codigo-ingeniero-civil
pip install pytest pandas openpyxl matplotlib
python -m pytest scripts/                          # 33 tests
PYTHONPATH=scripts python assets/plantilla_calculo.py   # memoria de la viga V-101
```

Los valores normativos marcados **(verificar)** en `references/` deben
contrastarse con el texto oficial vigente antes de usarlos en un expediente.
