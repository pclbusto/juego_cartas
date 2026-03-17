# Yu-Gi-Oh Style Card Game - Deck Builder

Sistema completo de gestión de decks para tu juego de cartas estilo Yu-Gi-Oh.

## Características

### Modelos de Base de Datos
- **SavedDeck**: Gestiona decks guardados con nombre y fecha de creación
- **DeckEntry**: Almacena las cartas en cada deck con cantidades (máximo 3 copias por carta)
- **Card**: Base de datos de todas las cartas disponibles

### Vistas de Arcade

1. **MenuView** (`menu_view.py`)
   - Menú principal del juego
   - Navegación a todas las secciones

2. **DeckBuilderView** (`deck_builder_view.py`)
   - Visualización de todas las cartas disponibles con sus imágenes
   - Sistema de scroll para navegar entre cartas
   - Agregar/quitar cartas del deck actual
   - Vista detallada de cartas al hacer clic derecho
   - Límites de Yu-Gi-Oh aplicados:
     - Máximo 60 cartas por deck
     - Máximo 3 copias de cada carta

3. **DeckManagementView** (`deck_management_view.py`)
   - Ver todos los decks guardados
   - Seleccionar y eliminar decks
   - Ver información de cada deck (nombre, cantidad de cartas, fecha)

4. **GameView** (`game_view.py`)
   - Vista del juego actualizada para cargar el deck seleccionado
   - Botón de regreso al menú

## Instalación y Uso

### 1. Inicializar la Base de Datos

```bash
python init_database.py
```

Este script:
- Carga todas las cartas desde `normal_monsters.json`
- Crea un deck de ejemplo con 10 cartas
- Verifica que todo funcione correctamente

### 2. Ejecutar el Juego

```bash
python main.py
```

## Controles

### En el Deck Builder:
- **Click Izquierdo en carta disponible**: Agregar carta al deck
- **Click Izquierdo en carta del deck**: Quitar carta del deck
- **Click Derecho**: Ver detalles de la carta
- **Rueda del Ratón**: Scroll por las cartas disponibles
- **ESC**: Volver al menú

### En el Juego:
- **Click Izquierdo**: Arrastrar cartas
- **Click Derecho**: Rotar carta (posición de ataque/defensa)
- **ESC**: Volver al menú

## Estructura de la Base de Datos

### Tabla: saved_decks
```sql
- id: INTEGER (Primary Key)
- name: STRING (Unique)
- created_at: STRING (ISO format)
```

### Tabla: deck_entries
```sql
- id: INTEGER (Primary Key)
- deck_id: INTEGER (Foreign Key -> saved_decks.id)
- card_cid: STRING (Foreign Key -> cards.cid)
- quantity: INTEGER (1-3)
```

### Tabla: cards
```sql
- cid: STRING (Primary Key)
- type: STRING
- name: STRING
- image_name: STRING
- attribute: STRING
- level: STRING
- atk: STRING
- def: STRING
- text: STRING
- image_url: STRING
```

## Métodos Principales del DatabaseManager

### Gestión de Decks
- `create_deck(name)`: Crea un nuevo deck
- `get_all_decks()`: Obtiene lista de todos los decks
- `delete_deck(deck_id)`: Elimina un deck
- `get_deck_cards(deck_id)`: Obtiene cartas de un deck específico
- `get_deck_card_count(deck_id)`: Cuenta total de cartas en un deck

### Gestión de Cartas en Decks
- `add_card_to_deck(deck_id, card_cid)`: Agrega carta (respeta límite de 3 copias)
- `remove_card_from_deck(deck_id, card_cid)`: Quita una copia de la carta
- `get_cards()`: Obtiene todas las cartas disponibles

## Imágenes de Cartas

Las imágenes deben estar en la carpeta `images/` con el formato:
- Nombre del archivo: `{image_name}` (del campo en la base de datos)
- Formato recomendado: JPG o PNG
- Las cartas sin imagen mostrarán un placeholder azul

## Próximas Mejoras Sugeridas

1. **Sistema de búsqueda y filtros**
   - Buscar cartas por nombre
   - Filtrar por atributo, tipo, ATK, DEF

2. **Gestión avanzada de decks**
   - Renombrar decks
   - Duplicar decks
   - Exportar/importar decks

3. **Extra Deck y Side Deck**
   - Soporte para Extra Deck (15 cartas máximo)
   - Side Deck para torneos

4. **Estadísticas**
   - Distribución de tipos de cartas
   - Curva de niveles
   - ATK/DEF promedio

5. **Validación de reglas**
   - Lista de cartas prohibidas/limitadas
   - Validación de deck legal antes de jugar

## Archivos Creados/Modificados

### Nuevos Archivos:
- `deck_builder_view.py`: Vista principal del constructor de decks
- `menu_view.py`: Menú principal
- `deck_management_view.py`: Gestión de decks guardados
- `init_database.py`: Script de inicialización

### Archivos Modificados:
- `database.py`: Extendido con modelos SavedDeck y DeckEntry, nuevos métodos
- `game_view.py`: Añadido botón de menú y carga de decks guardados
- `main.py`: Cambiado para iniciar con el menú principal

## Notas Técnicas

- La base de datos usa SQLite con SQLAlchemy ORM
- Las vistas usan Arcade GUI para botones e interfaz
- El sistema de scroll es manual para mejor control
- Las imágenes se escalan automáticamente al tamaño de carta definido
- Todos los cambios en decks se guardan automáticamente en la base de datos
