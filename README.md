# Calculadora 3D - 3D Printing Calculator

Una aplicación de escritorio completa para calcular costos, tiempos y materiales de impresión 3D.

A comprehensive desktop application for calculating 3D printing costs, times, and materials.

## Características / Features

- **Cálculo de Costo por Pieza**: Calcula el precio de venta considerando:
  - Costo del filamento por gramo
  - Tiempo de impresión en minutos
  - Consumo eléctrico
  - Margen de ganancia personalizable

- **Conversión de Material**: Convierte entre:
  - Peso del filamento (gramos)
  - Longitud del filamento (metros)
  - Volumen (cm³)


## Requisitos / Requirements

- Python 3.7 o superior / Python 3.7 or higher
- tkinter (incluido con Python / included with Python)

## Instalación / Installation

1. Clona o descarga este repositorio:
```bash
git clone <repository-url>
cd "Calculadora 3D"
```

2. No se requieren dependencias externas. Tkinter viene incluido con Python.

## Uso / Usage

Ejecuta la aplicación:
```bash
python main.py
```

### Pestañas de la Aplicación / Application Tabs

1. **Costo por Pieza**: Ingresa el precio del filamento, tiempo de impresión, peso usado, y obtén el precio de venta recomendado.

2. **Material**: Convierte entre diferentes medidas de filamento (peso, longitud, volumen).



## Estructura del Proyecto / Project Structure

```
Calculadora 3D/
├── main.py                 # Aplicación GUI principal
├── calculator_logic.py     # Lógica de cálculos
├── requirements.txt        # Dependencias (ninguna requerida)
└── README.md              # Este archivo
```

## Valores por Defecto / Default Values

- **Diámetro de filamento**: 1.75 mm
- **Densidad PLA**: 1.24 g/cm³
- **Consumo de impresora**: 150W
- **Costo electricidad**: $0.15 por kWh
- **Margen de ganancia**: 30%

## Materiales Comunes / Common Materials

| Material | Densidad (g/cm³) |
|----------|------------------|
| PLA      | 1.24             |
| ABS      | 1.04             |
| PETG     | 1.27             |
| TPU      | 1.21             |
| Nylon    | 1.14             |

## Desarrollo / Development

Para contribuir al proyecto:

1. Haz un fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -m 'Añadir nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

## Licencia / License

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## Autor / Author

Creado para facilitar el cálculo de costos en impresión 3D.

## Futuras Mejoras / Future Enhancements

- [ ] Guardar/cargar configuraciones personalizadas
- [ ] Historial de cálculos
- [ ] Exportar resultados a PDF/Excel
- [ ] Base de datos de materiales
- [ ] Múltiples perfiles de impresora
- [ ] Calculadora de soporte material
- [ ] Integración con slicers (importar datos de Cura/PrusaSlicer)
