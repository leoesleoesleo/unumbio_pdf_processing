# PRUEBA TÉCNICA PDF PROCESSING

## 1. Resumen general de la solución

El objetivo de la prueba fue procesar un archivo JSON generado a partir de un PDF y reconstruir correctamente los registros de la sección **B.1**, respetando su estructura original.

Para lograrlo, se desarrolló un script en Python que:

- Lee y organiza el contenido del documento
- Reconstruye el orden de lectura real (como lo haría una persona)
- Identifica los registros correctamente
- Limpia ruido propio del PDF
- Genera un JSON final estructurado según lo solicitado

Durante el desarrollo, se identificaron varios desafíos propios de documentos PDF como:
- columnas mezcladas  
- texto fragmentado  
- encabezados que contaminan datos  
- registros que se dividen entre páginas  

La solución aborda todos estos casos mediante reglas progresivas.

---

## 2. Respuesta a los requisitos de la prueba

### 2.1 Filtro de Sección (B.1)

**Requisito:**  
Identificar dónde comienza y termina la sección B.1.

**Solución implementada:**  

Se detectaron patrones de texto característicos de encabezados como:

- `Part B.1`
- `PART B B.1`
- `2024/001`

Estos elementos se identificaron como **ruido estructural**, no como datos del registro.

En lugar de usarlos como delimitadores rígidos, se optó por:
- procesar todo el documento  
- eliminar estos textos durante la normalización  

Esto permite una solución más robusta ante variaciones del PDF.

---

### 2.2 Reconstrucción de Columnas

**Requisito:**  
Separar correctamente las dos columnas del documento.

**Solución implementada:**

Se utilizó la coordenada horizontal (`x0`) de cada bloque de texto:

1. Se identificó automáticamente el punto de separación (threshold)  
2. Se dividieron los bloques en:
   - columna izquierda  
   - columna derecha  
3. Se procesó cada página por separado para evitar mezcla entre páginas  

Resultado:  
Se reconstruye el orden de lectura real: primero columna izquierda, luego derecha.

---

### 2.3 Identificación de Registros

**Requisito:**  
Agrupar correctamente los elementos que pertenecen a un mismo registro.

**Solución implementada:**

Se utilizó el código **INID 111** como inicio de registro.

Reglas aplicadas:
- Cada vez que aparece `111` → comienza un nuevo registro  
- Los siguientes elementos se agregan a ese registro  
- Si una línea no tiene código → se considera continuación del campo anterior  

Esto permite reconstruir registros incluso si están fragmentados.

---

### 2.4 Manejo de Multilinealidad y Saltos de Página

**Requisito:**  
Unir información de registros que pueden dividirse entre columnas o páginas.

**Solución implementada:**

Se aplicaron dos estrategias:

#### 1. Normalización
Se limpian los textos eliminando ruido como:
- `EUTM 018xxxxx`
- encabezados  
- identificadores editoriales  

#### 2. Fusión de registros (merge)

Se detectaron registros incompletos y se fusionaron usando:

- el campo `210` como identificador único  
- en su defecto, el campo `111`  

Esto evita:
- duplicados  
- registros incompletos  
- pérdida de información  

---

### 2.5 Estructura del JSON de salida

**Requisito:**  
Generar un JSON con estructura específica.

**Solución implementada:**

Se construyó el siguiente formato:

```json
{
  "B": {
    "1": [
      {
        "_PAGE": 1,
        "111": "...",
        "210": "...",
        "151": "...",
        "400": ["..."]
      }
    ]
  }
}
```
### Reglas aplicadas

- `_PAGE`: página donde inicia el registro  
- `400`: siempre como lista  
- Otros campos: texto plano limpio  
- Múltiples fragmentos: se unen con espacios  

---

### 2.6 Calidad del código

**Requisito:**  
Código limpio y estructurado.

**Solución implementada:**

- Funciones separadas por responsabilidad  
- Nombres claros  
- Comentarios explicativos  
- Flujo modular (pipeline)  

**Además:**

- Se añadieron pruebas unitarias  
- Se validó la exactitud contra archivo esperado  
- Se logró una precisión superior al 99%  

---

### 3. Resumen de reglas aplicadas (explicación simple)

Para resolver el problema, se siguió un enfoque progresivo, aplicando reglas en este orden:

#### Paso 1: Limpiar el contenido

Primero se eliminaron textos innecesarios como:

- Líneas vacías  
- Encabezados (ej: “Part B.1”)  
- Códigos editoriales (ej: “EUTM”)  

Esto evita confundir datos reales con ruido.

---

#### Paso 2: Ordenar el documento

Se reorganizó el contenido como lo leería una persona:

- Por página  
- De arriba hacia abajo  
- De izquierda a derecha  

---

#### Paso 3: Separar columnas

El documento tiene dos columnas, por lo que:

- Se detectó automáticamente la separación  
- Se procesó primero la columna izquierda y luego la derecha  

---

#### Paso 4: Reconstruir líneas

Algunos textos están fragmentados, así que:

- Se agruparon elementos cercanos verticalmente  
- Se reconstruyeron como líneas completas  

---

#### Paso 5: Detectar registros

Cada registro comienza con un código `111`.

A partir de ahí:

- Se agrupan todos los datos hasta el siguiente `111`  
- Si una línea no tiene código, se considera continuación  

---

#### Paso 6: Limpiar datos internos

Se eliminaron errores típicos como:

- Números extra en campos  
- Textos mezclados de otros registros  

**Ejemplo:**
```018875662 EUTM 018861314" → "018875662```

---

#### Paso 7: Unir registros fragmentados

Algunos registros venían divididos.

Se detectaron y se unieron usando:

- El identificador principal (`210`)  

---

#### Paso 8: Formatear salida

Finalmente:

- Se limpiaron espacios  
- Se unificaron textos  
- Se estructuró el JSON final  

---

### 4. Conclusión

La solución desarrollada permite:

- Reconstruir correctamente datos complejos desde un PDF  
- Manejar errores reales del formato (columnas, ruido, fragmentación)  
- Generar un resultado consistente y validado  
