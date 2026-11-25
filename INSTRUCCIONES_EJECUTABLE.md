# Instrucciones para el Ejecutable de Calculadora 3D

## Ubicación del Ejecutable

El archivo ejecutable ya está compilado y listo para usar:

```
dist/Calculadora3D.exe
```

## Cómo Usar el Ejecutable

1. **Ubicar el archivo**: Navega a la carpeta `dist`
2. **Ejecutar**: Haz doble clic en `Calculadora3D.exe`
3. **Usar normalmente**: La aplicación se abrirá como cualquier programa de Windows

## Distribución

Puedes copiar el archivo `Calculadora3D.exe` a cualquier computadora Windows sin necesidad de tener Python instalado. El ejecutable es completamente independiente.

### Pasos para Distribuir:
1. Copia `Calculadora3D.exe` desde la carpeta `dist`
2. Pégalo en cualquier ubicación (escritorio, carpeta de programas, USB, etc.)
3. Ejecuta directamente haciendo doble clic

## Recompilar el Ejecutable

Si realizas cambios en `main.py` o `calculator_logic.py` y necesitas actualizar el ejecutable:

### Opción 1: Script Automático (Recomendado)
Simplemente ejecuta el script de compilación:
```bash
build_exe.bat
```

Este script:
- Limpia compilaciones anteriores
- Genera un nuevo ejecutable
- Te notifica si hubo algún error

### Opción 2: Manual
Ejecuta el siguiente comando en la terminal:
```bash
pyinstaller --onefile --windowed --name Calculadora3D main.py
```

Parámetros utilizados:
- `--onefile`: Crea un único archivo ejecutable (más fácil de distribuir)
- `--windowed`: No muestra la consola de comandos (solo la GUI)
- `--name Calculadora3D`: Nombre del ejecutable resultante

## Requisitos para Compilar

Solo necesitas tener instalado PyInstaller:
```bash
pip install pyinstaller
```

## Notas Importantes

### Tamaño del Ejecutable
- El archivo `.exe` pesa aproximadamente 8-10 MB
- Esto es normal porque incluye todo el intérprete de Python y las bibliotecas necesarias

### Antivirus
- Algunos antivirus pueden marcar el ejecutable como sospechoso
- Esto es un falso positivo común con PyInstaller
- Si ocurre, agrega una excepción en tu antivirus

### Historial de Cálculos
- El archivo `historial_calculos.txt` se crea en la misma carpeta donde se ejecuta el `.exe`
- Si mueves el ejecutable, se creará un nuevo archivo de historial en la nueva ubicación

## Estructura de Archivos del Proyecto

```
Calculadora 3D/
├── main.py                      # Código fuente principal
├── calculator_logic.py          # Lógica de cálculos
├── build_exe.bat                # Script de compilación
├── Calculadora3D.spec           # Configuración de PyInstaller
├── dist/
│   └── Calculadora3D.exe        # ⭐ EJECUTABLE FINAL
├── build/                       # Archivos temporales de compilación
└── historial_calculos.txt       # Historial (se crea al usar la app)
```

## Solución de Problemas

### El ejecutable no abre
- Verifica que no esté bloqueado por el antivirus
- Intenta ejecutar como administrador (clic derecho → "Ejecutar como administrador")

### Error al compilar
- Asegúrate de tener PyInstaller instalado: `pip install pyinstaller`
- Verifica que no haya errores en el código fuente: `python main.py`

### La aplicación no guarda el historial
- Verifica que tengas permisos de escritura en la carpeta donde está el `.exe`
- Si está en "Archivos de programa", muévelo a otra ubicación (como el escritorio)

## Contacto

Si tienes problemas o preguntas, revisa el archivo README.md principal del proyecto.
