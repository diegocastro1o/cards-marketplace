# Bitácora de uso de inteligencia artificial

## Criterio de uso

La inteligencia artificial se utilizó como apoyo para revisar la consigna,
organizar documentación, detectar riesgos y proponer preguntas de verificación.
Las decisiones de diseño, la revisión del código y la incorporación final de los
cambios quedaron a cargo del equipo.

---

## Registro 1 - Revisión de requisitos de ética

**Qué se pidió**

Se pidió identificar qué debía contener `ETICA.md` y relacionarlo con el modelo
actual del mercado de cartas.

**Qué devolvió la IA**

La IA indicó que el documento debía incluir los datos manejados por la aplicación,
un riesgo ético concreto con una mitigación de diseño, una norma o licencia citada
y una explicación del uso de IA. Propuso analizar el azar de los sobres, la
transparencia de sus probabilidades y el posible efecto sobre menores.

**Qué se aceptó y por qué**

Se aceptó ese enfoque porque coincide con la consigna del proyecto y con las
clases del programa: `Pack`, `CardDrawer`, `User`, `Market` y el historial de
transacciones.

**Qué se corrigió**

Al principio se consideró que, al no pedir correo electrónico ni dinero real, la
aplicación no manejaba datos personales relevantes. Se corrigió esa afirmación:
el nombre de usuario puede identificar a una persona y el historial permite conocer
sus operaciones. Por eso `ETICA.md` lo trata como información que debe protegerse.

---

## Registro 2 - Verificación de probabilidades de los sobres

**Qué se pidió**

Se pidió revisar si los pesos de rareza podían mostrarse al usuario como
probabilidades.

**Qué devolvió la IA**

La IA propuso mostrar de forma clara la probabilidad de cada rareza antes de abrir
un sobre, junto con el precio y un aviso de que se usa moneda ficticia.

**Error real detectado en la respuesta inicial**

La primera interpretación trató los pesos de rareza como si fueran porcentajes
directos. Al revisar el código se encontró un problema: los pesos de Bronce y Plata
suman 100, pero los de Oro suman 104. Por lo tanto, los valores del sobre Oro no
pueden mostrarse directamente como porcentajes.

**Corrección aplicada**

Se decidió normalizar los pesos antes de presentarlos:

```text
probabilidad = peso_de_la_rareza / suma_de_todos_los_pesos * 100
```

De este modo se evita comunicar una probabilidad incorrecta. Esta corrección también
quedó registrada en `ETICA.md` como parte de la mitigación del riesgo ético.

---

## Registro 3 - Consulta de marco legal

**Qué se pidió**

Se pidió encontrar una fuente oficial uruguaya relacionada con los datos que guarda
la aplicación.

**Qué devolvió la IA**

La IA localizó la Ley N.º 18.331 de Protección de Datos Personales y señaló que su
artículo 12 incluye los principios de privacidad desde el diseño y privacidad por
defecto.

**Qué se aceptó y por qué**

Se utilizó esa fuente porque es oficial y porque el proyecto almacena nombres de
usuario e historial de operaciones. La referencia fue agregada a `ETICA.md`.

Fuente consultada: [IMPO - Ley N.º 18.331, artículo 12](https://www.impo.com.uy/bases/leyes/18331-2008/12).
