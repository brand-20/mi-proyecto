# Metrados

Base: Norma Técnica de Metrados para Obras de Edificación y Habilitaciones
Urbanas (RD N° 073-2010-VIVIENDA). Implementado en `civil/metrados.py`.

## Principios

- **El metrado es neto.** Desperdicios, esponjamiento y traslapes "de
  seguridad" no van aquí: los desperdicios van en el APU, el esponjamiento en
  la partida de eliminación como factor declarado.
- **Cada número sale de una medición visible.** Veces × largo × ancho × alto,
  con la descripción del elemento y del eje. Nunca un total escrito a mano.
- **Intersecciones una sola vez.** Decide qué elemento se queda con el volumen
  del nudo (p. ej. la columna pasa corrida y la viga se mide entre caras de
  columna; la losa se mide descontando vigas) y escribe ese criterio en la
  cabecera del script. Un metrado sin criterio declarado no se puede revisar.
- **Descuentos como filas negativas** (`veces=-1`), no restas escondidas.

## Organización

Por especialidad (Estructuras, Arquitectura, Instalaciones Sanitarias,
Instalaciones Eléctricas, ...) y dentro de cada una por ítems jerárquicos
`01.00.00 > 01.01.00 > 01.01.01`, en el mismo orden que el presupuesto y el
cronograma para que los tres cuadren por ítem.

Unidades usuales en estructuras:

| Partida | Und |
|---|---|
| Excavación, relleno, eliminación | m³ |
| Solado, nivelación | m² |
| Concreto (simple o armado) por elemento | m³ |
| Encofrado y desencofrado | m² (área de contacto) |
| Acero de refuerzo fy = 4200 | kg |
| Ladrillo de techo (losa aligerada) | und |

## Formato de la hoja

| Item | Descripción | Und | Veces | Largo | Ancho | Alto | Parcial | Total |
|---|---|---|---|---|---|---|---|---|
| 05.03.01 | Concreto f'c = 210 kg/cm² en columnas | m3 | | | | | | 1.65 |
| | C-1 (ejes A-1, A-2, B-1, B-2) | | 4 | 0.30 | 0.50 | 2.80 | 1.68 | |
| | Descuento ducto | | -1 | 0.10 | 0.10 | 2.80 | -0.03 | |

`Partida` valida que cada medición tenga las dimensiones que pide su unidad
(3 para m³, 2 para m², 1 para m, ninguna para und); un error de este tipo es
el más común en hojas de Excel.

```python
from civil.metrados import Partida, exportar_excel

concreto_columnas = (
    Partida("05.03.01", "Concreto f'c = 210 kg/cm² en columnas", "m3")
    .agregar("C-1 (ejes A-1, A-2, B-1, B-2)", veces=4, largo=0.30, ancho=0.50, alto=2.80)
    .agregar("Descuento ducto", veces=-1, largo=0.10, ancho=0.10, alto=2.80)
)
encofrado_columnas = (
    Partida("05.03.02", "Encofrado y desencofrado en columnas", "m2")
    .agregar("C-1: perímetro × altura", veces=4, largo=2 * (0.30 + 0.50), alto=2.80)
)
exportar_excel([concreto_columnas, encofrado_columnas], "metrado_estructuras.xlsx")
```

## Losa aligerada (unidireccional, ladrillo 30 × 30, viguetas de 10 cm cada 40 cm)

Calcula las cuantías por m² en vez de copiarlas de una tabla: así sirve para
cualquier geometría.

```python
def aligerado_por_m2(h_ladrillo: float, e_losa: float = 0.05, b_vigueta: float = 0.10,
                     ancho_ladrillo: float = 0.30, largo_ladrillo: float = 0.30) -> dict[str, float]:
    """Concreto [m³/m²] y ladrillos [und/m²] de una losa aligerada en una dirección."""
    viguetas_por_m = 1 / (ancho_ladrillo + b_vigueta)
    concreto = e_losa + viguetas_por_m * b_vigueta * h_ladrillo
    ladrillos = viguetas_por_m / largo_ladrillo
    return {"concreto": concreto, "ladrillos": ladrillos}
```

| h total | Ladrillo | Concreto m³/m² | Ladrillos und/m² |
|---|---|---|---|
| 17 cm | 12 cm | 0.0800 | 8.33 |
| 20 cm | 15 cm | 0.0875 | 8.33 |
| 25 cm | 20 cm | 0.1000 | 8.33 |
| 30 cm | 25 cm | 0.1125 | 8.33 |

El encofrado de la losa aligerada se mide por el área de techo (m²),
descontando vigas.

## Encofrado (área de contacto)

- Columnas: perímetro × altura, descontando caras que llegan a muros vaciados juntos.
- Vigas: fondo + 2 costados; el costado se mide hasta el fondo de la losa
  (h − espesor de losa) cuando la losa se vacía con la viga.
- Zapatas: solo laterales si se vacían contra encofrado; contra terreno, no se encofra.

## Planilla de acero

| Elemento | ø | N° piezas | N° elementos | Long. pieza (m) | Long. total (m) | kg |
|---|---|---|---|---|---|---|

- La longitud por pieza incluye ganchos y empalmes de diseño, según los
  detalles de los planos.
- Peso = longitud total × peso nominal (kg/m) de `civil/acero.py`.
- El resumen por diámetro sirve para pedir acero; el desperdicio por corte va
  en el APU.

```python
from civil.metrados import PlanillaAcero

planilla = (
    PlanillaAcero()
    .agregar("Columna C-1 longitudinal", '5/8"', n_piezas=6, n_elementos=4, longitud=3.60)
    .agregar("Columna C-1 estribos", '3/8"', n_piezas=20, n_elementos=4, longitud=1.45)
)
planilla.resumen_por_diametro()   # {'5/8"': {'longitud': 86.4, 'peso': 134.09}, ...}
planilla.total_kg
```
