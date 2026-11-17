# Ética y legislación

## Datos que maneja la aplicación

El proyecto guarda los datos mínimos necesarios para que funcione el mercado de
cartas:

- Identificador y nombre de usuario.
- Saldo de moneda ficticia.
- Inventario de cartas de cada usuario.
- Publicaciones activas: carta ofrecida, vendedor y precio.
- Historial de operaciones: identificador de la operación, fecha, participantes,
  cartas involucradas e importes.
- Catálogo de jugadores: nombre, equipo, posición, rareza y rasgo especial.

No se solicitan dinero real, datos bancarios, direcciones, documentos de identidad
ni correo electrónico. Sin embargo, el nombre de usuario puede identificar a una
persona en una aplicación real, y el historial permite conocer sus operaciones. Por
eso se lo trata como un dato que debe protegerse.

## Riesgo ético: azar, transparencia y menores

Abrir sobres entrega cartas mediante azar. Esta mecánica puede incentivar aperturas
repetidas, resultar confusa para usuarios menores de edad y parecerse a una apuesta
si las probabilidades no se comunican de forma clara.

El proyecto reduce ese riesgo porque usa exclusivamente moneda ficticia: no permite
comprar monedas, retirar saldo ni intercambiar cartas por dinero real. Además, cada
usuario recibe tres sobres gratuitos y tiene un límite de cinco aperturas por día.

## Cambio de diseño para mitigarlo

Antes de confirmar la apertura de un sobre, la interfaz debe mostrar:

1. El precio en moneda ficticia.
2. La cantidad de cartas que contiene.
3. La probabilidad normalizada de cada rareza.
4. Un aviso explícito de que el resultado se decide al azar y que no hay dinero real
   involucrado.

Las probabilidades deben ser iguales para todas las personas y no pueden cambiarse
según el saldo, el historial de compras ni las cartas que posea un usuario.

Actualmente cada tipo de sobre guarda pesos de rareza fijos. Estos pesos no siempre
son porcentajes: Bronce y Plata suman 100, pero Oro suma 104. Por lo tanto, al
mostrar la información se debe calcular para cada rareza:

```text
probabilidad = peso_de_la_rareza / suma_de_todos_los_pesos * 100
```

Así se evita comunicar como porcentaje un valor que no lo es. Esta medida hace que
la decisión de abrir un sobre sea informada y verificable.

El historial inmutable de operaciones también permite revisar una apertura sin
volver a sortearla: guarda la fecha, el sobre, el importe pagado y las cartas
recibidas. Esto favorece la trazabilidad del sistema.

## Marco legal consultado

Se consultó la **Ley N.º 18.331 de Protección de Datos Personales** de Uruguay.
La ley reconoce la protección de los datos personales y establece responsabilidades
para quien trata una base de datos. Su artículo 12 también incorpora los principios
de privacidad desde el diseño y privacidad por defecto.

En este proyecto académico aplicamos esos principios mediante minimización de datos:
solo se guardan el identificador, el nombre de usuario y los datos necesarios para
reconstruir el mercado. Si la aplicación se transformara en un producto real, sería
necesario informar la finalidad del tratamiento, proteger el archivo de estado y
permitir el ejercicio de los derechos correspondientes.

Fuente: [IMPO - Ley N.º 18.331, artículo 12](https://www.impo.com.uy/bases/leyes/18331-2008/12), consultada el 17 de noviembre de 2026.

## Uso de inteligencia artificial

Se utilizó inteligencia artificial como apoyo para interpretar la consigna, ordenar
la estructura de este documento y revisar los riesgos vinculados con sobres
aleatorios. Las propuestas se contrastaron con el código del proyecto antes de
incorporarlas.

La IA no tomó decisiones por el equipo ni reemplazó la revisión del código. Por
ejemplo, al revisar los pesos se detectó que los del sobre Oro suman 104; por eso se
decidió no presentarlos directamente como porcentajes y normalizarlos antes de
mostrarlos.
