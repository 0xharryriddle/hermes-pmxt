# hermes-pmxt

Integración de mercados de predicción para [Hermes Agent](https://github.com/NousResearch/hermes-agent).
Busque mercados, compare precios, detecte arbitrajes y opere en múltiples intercambios de mercados de predicción a través de [pmxt](https://github.com/pmxt-dev/pmxt) (>= 2.50.0).

## Qué es esto

Una habilidad de Hermes + un conjunto de herramientas de Python que otorga a cualquier agente de Hermes acceso en tiempo real a los mercados de predicción. En lugar de alucinar probabilidades, el agente verifica los precios reales del mercado.

```
Usuario: "¿Ganará Trump en 2028?"
Agente: *llama a pmxt_search + pmxt_quote*
Agente: "El mercado implica una probabilidad del 1.9% (No: 98.1%). Polymarket está valorando esto muy bajo."
```

## Instalación

El paquete de PyPI ya está disponible. Para la mayoría de los usuarios, esta es la instalación completa:

```bash
pip install hermes-pmxt
```

Verifique que funcione:

```bash
python3 -c "from hermes_pmxt import pmxt_runtime_status; print(pmxt_runtime_status())"
```

### Configuración de la Habilidad de Hermes

Instale el archivo de habilidad de Hermes para que su agente sepa cuándo utilizar el paquete:

```bash
mkdir -p ~/.hermes/skills/pmxt
curl -fsSL https://raw.githubusercontent.com/0xharryriddle/hermes-pmxt/main/skill/SKILL.md \
  -o ~/.hermes/skills/pmxt/SKILL.md
```

Si su instalación de Hermes admite la instalación de habilidades/plugins respaldados por GitHub, use:

```text
https://github.com/0xharryriddle/hermes-pmxt
```

### Actualización

```bash
pip install --upgrade hermes-pmxt
```

### Instalación para Desarrollo

Solo clone el repositorio si va a modificar hermes-pmxt:

```bash
git clone https://github.com/0xharryriddle/hermes-pmxt.git
cd hermes-pmxt
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Modos

hermes-pmxt admite tres modos de ejecución:

| Modo | Configuración | Comportamiento |
|------|--------|----------|
| **Hosted** | Establezca `PMXT_API_KEY` | Se comunica con `https://api.pmxt.dev`. Gestiona las conexiones a los intercambios, el almacenamiento en caché y los límites de tasa automáticamente. Recomendado para la mayoría de los usuarios. |
| **Custom** | Establezca `PMXT_API_URL` o `PMXT_BASE_URL` | Apunta a cualquier servidor compatible con PMXT. |
| **Local Sidecar** | Sin clave/URL de API configurada | Asume que el núcleo de PMXT se está ejecutando en `http://localhost:3847`. Para auto-hospedaje / desarrollo. |

Verifique su modo actual:
```python
from hermes_pmxt import pmxt_runtime_status
print(pmxt_runtime_status())
```

## Inicio Rápido

```python
from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_runtime_status

# Verificar estado
print(pmxt_runtime_status())

# Buscar
result = pmxt_search("bitcoin", exchange="polymarket", limit=5)
for m in result["data"]:
    prices = m.get("outcomes", [])
    if prices:
        print(f"{m['title'][:60]}: YES={prices[0]['price']*100:.1f}%")

# Cotización
quote = pmxt_quote("bitcoin reach", exchange="polymarket")
print(f"YES: {quote['data']['yes_pct']}  NO: {quote['data']['no_pct']}")
```

## Modelo de Datos

```
  Evento (tema amplio)
    └── Mercado (pregunta negociable)
          ├── Resultado "Yes"
          └── Resultado "No"
```

Cuando los usuarios pregunten sobre un tema, comience con eventos (`pmxt_events`), luego profundice en mercados y resultados.

## Herramientas

### Descubrimiento e Investigación

| Función | Auth | Descripción |
|----------|------|-------------|
| `pmxt_search(query, exchange?, limit?, sort?, search_in?, slug?)` | No* | Buscar mercados por palabra clave |
| `pmxt_events(query, exchange?, limit?, sort?, search_in?, slug?)` | No* | Buscar grupos de eventos |
| `pmxt_quote(identifier, exchange)` | No* | Obtener probabilidades YES/NO |
| `pmxt_order_book(outcome_id, exchange, limit?)` | No* | Profundidad del libro de órdenes |
| `pmxt_ohlcv(outcome_id, exchange, resolution?, limit?)` | No* | Velas de precio |
| `pmxt_trades(outcome_id, exchange, limit?)` | No* | Operaciones recientes |
| `pmxt_execution_price(outcome_id, exchange, side, amount)` | No* | Estimación de deslizamiento (slippage) |

### Inter-Plataforma y Arbitraje

| Función | Auth | Descripción |
|----------|------|-------------|
| `pmxt_compare_market(query, exchanges?, limit?)` | No* | Comparar precios entre intercambios |
| `pmxt_arbitrage_scan(query, exchanges?, threshold?)` | No* | Detectar oportunidades de arbitraje |
| `pmxt_call("compareMarketPrices", "router", ...)` | No* | Comparación nativa del enrutador |
| `pmxt_call("fetchArbitrage", "router", ...)` | No* | Búsqueda de arbitraje nativa |
| `pmxt_call("fetchHedges", "router", ...)` | No* | Oportunidades de cobertura (hedging) |

### Portafolio y Cuenta

| Función | Auth | Descripción |
|----------|------|-------------|
| `pmxt_balance(exchange)` | Yes | Balance de la cuenta |
| `pmxt_positions(exchange)` | Yes | Posiciones abiertas |
| `pmxt_portfolio(exchanges?)` | Yes | Portafolio multi-intercambio |

### Trading (Todas destructivas -- Requieren Confirmación Explícita)

| Función | Auth | Descripción |
|----------|------|-------------|
| `pmxt_build_order(...)` | Yes | Construir/firmar orden sin enviarla (SEGURO) |
| `pmxt_submit_order(built, exchange, confirmed=True)` | Yes | Enviar una orden pre-construida |
| `pmxt_cancel_order(order_id, exchange, confirmed=True)` | Yes | Cancelar una orden abierta |
| `pmxt_order(...)` | Yes | Orden heredada de un solo paso (se prefiere build+submit) |

### Llamada Genérica a la API

| Función | Auth | Descripción |
|----------|------|-------------|
| `pmxt_call(method, exchange, ...)` | Varía | Llamada genérica a la API de PMXT con comprobaciones de seguridad |

### Servidor y Diagnósticos

| Función | Auth | Descripción |
|----------|------|-------------|
| `pmxt_runtime_status()` | No | Estado completo del tiempo de ejecución |
| `pmxt_list_exchanges()` | No | Intercambios conocidos/disponibles |
| `pmxt_server_status()` | No | Diagnósticos del sidecar |
| `pmxt_server_start()` | No | Iniciar sidecar |
| `pmxt_server_stop()` | No | Detener sidecar |

\* Las herramientas de solo lectura funcionan sin credenciales en el modo sidecar local. El modo Hosted requiere `PMXT_API_KEY` para todas las operaciones.

## Seguridad en el Trading

**Las operaciones destructivas (crear, enviar, cancelar órdenes) requieren la confirmación explícita del usuario.**

```python
# SEGURO: Construir orden para previsualización (NO coloca ninguna orden)
built = pmxt_build_order(
    market_id="market-uuid",
    outcome="yes",
    side="buy",
    order_type="limit",
    amount=10,
    price=0.55,
    exchange="polymarket",
)

# DESTRUCTIVO: El envío requiere confirmed=True
result = pmxt_submit_order(built, "polymarket", confirmed=True)

# Sin confirmed=True:
result = pmxt_submit_order(built, "polymarket")
# => {"success": False, "error": "Operation 'submit_order' is destructive..."}
```

## Intercambios Compatibles

hermes-pmxt conoce 17 plataformas, incluyendo:

- `polymarket` / `polymarket_us`
- `kalshi` / `kalshi-demo`
- `limitless`
- `probable` / `baozi` / `myriad` / `opinion`
- `metaculus` / `smarkets`
- `gemini-titan` / `hyperliquid` / `suibets` / `rain`
- `mock` / `router`

La disponibilidad real depende de la versión de `pmxt` instalada. Ejecute `pmxt_list_exchanges()` para verificarlo.

## Variables de Entorno

```bash
# Modo Hosted (recomendado)
export PMXT_API_KEY="pmxt_live_..."
export PMXT_WALLET_ADDRESS="0x..."
export PMXT_PRIVATE_KEY="0x..."

# Servidor personalizado
export PMXT_API_URL="https://your-server.com"
# o
export PMXT_BASE_URL="https://your-server.com"

# Específicos de la plataforma (modo auto-hospedado)
export POLYMARKET_PRIVATE_KEY="0x..."
export POLYMARKET_PROXY_ADDRESS="0x..."  # Opcional
export KALSHI_API_KEY="..."
export KALSHI_PRIVATE_KEY="..."
export LIMITLESS_API_KEY="..."
export LIMITLESS_PRIVATE_KEY="..."
export POLYMARKET_US_API_KEY="..."
export POLYMARKET_US_PRIVATE_KEY="..."
```

## Estructura del Proyecto

```
hermes-pmxt/
├── hermes_pmxt/
│   ├── __init__.py          # Exportaciones de la API pública
│   ├── config.py            # Configuración de ejecución y detección de modo
│   ├── exchanges.py         # Inicialización + normalización de intercambios
│   ├── registry.py          # Registro de herramientas con anotaciones de seguridad
│   ├── shaper.py            # Moldeado de resultados para el contexto del LLM
│   └── tools.py             # Funciones principales de las herramientas
├── skill/
│   └── SKILL.md             # Instrucciones de la habilidad del agente Hermes
├── examples/
│   └── demo.py              # Demo interactiva
├── tests/
│   ├── conftest.py          # Configuración de rutas de prueba
│   ├── test_exchanges.py    # Pruebas unitarias de conexión de intercambios
│   └── test_tools.py        # Pruebas unitarias + de integración
├── pyproject.toml
└── README.md
```

## Pruebas

```bash
# Pruebas unitarias (no requiere pmxt)
python3 -m pytest -q -m unit

# Todas las pruebas no destructivas
python3 -m pytest -q -m "not trading"

# Pruebas de integración (requiere pmxt + sidecar/API)
python3 -m pytest -q -m integration
```

## Licencia

MIT
