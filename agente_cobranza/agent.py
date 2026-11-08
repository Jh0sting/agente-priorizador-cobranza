import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

# Permite importar el paquete "cobranza" al ejecutar `adk run` / `adk web`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cobranza.herramientas import resumen_cartera, priorizar_cartera, detalle_credito  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 0. Modelo: Gemini mediante la API de Google AI Studio.
# ADK lee GOOGLE_API_KEY del entorno. GOOGLE_GENAI_USE_VERTEXAI=FALSE indica
# que se usa AI Studio y no Vertex AI.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not (os.getenv("GOOGLE_API_KEY") or "").strip():
    raise RuntimeError(
        "Falta la variable GOOGLE_API_KEY. Crea una llave en https://aistudio.google.com/apikey "
        "y agrégala al archivo .env de la raíz del proyecto (formato: GOOGLE_API_KEY=...)."
    )


# 1. Agente analista: consulta la cartera con las herramientas deterministas.
analista_cartera = Agent(
    name="analista_cartera",
    model=GEMINI_MODEL,
    description="Consulta la cartera ficticia y devuelve rankings, resúmenes y detalles de créditos.",
    instruction="""
    Eres el agente "analista_cartera" del área de Recuperaciones de una caja municipal.
    Trabajas SOLO con una cartera de créditos ficticia y con tus herramientas:
    - `resumen_cartera`: panorama por tramo de mora y por distrito.
    - `priorizar_cartera`: ranking de créditos a gestionar primero, con filtros de tramo, distrito y producto.
    - `detalle_credito`: datos completos y puntaje desglosado de un crédito.

    Reglas:
    1. Nunca inventes montos, clientes ni puntajes: todo número sale de una herramienta.
    2. El puntaje de prioridad (0 a 100) combina 35% urgencia (cercanía al siguiente tramo de mora),
       35% recuperabilidad (historial de pagos, promesas incumplidas, días de atraso, garantía)
       y 30% exposición (saldo de capital). Explícalo con esos términos cuando te lo pidan.
    3. Devuelve los datos ordenados y legibles, sin opinar sobre las personas.
    """,
    tools=[
        FunctionTool(resumen_cartera),
        FunctionTool(priorizar_cartera),
        FunctionTool(detalle_credito),
    ],
)

# 2. Agente redactor: prepara el mensaje de contacto para el cliente.
redactor_mensajes = Agent(
    name="redactor_mensajes",
    model=GEMINI_MODEL,
    description="Redacta mensajes de cobranza respetuosos y personalizados según el tramo y el canal.",
    instruction="""
    Eres el agente "redactor_mensajes". Recibes los datos de un crédito (cliente, tramo de mora,
    días de atraso, cuota, canal sugerido y acción sugerida) y redactas el mensaje o el guion
    de llamada para contactar al cliente.

    Reglas de cobranza responsable:
    1. Tono cordial y respetuoso. Nada de amenazas, presión, burla ni lenguaje que avergüence.
    2. No menciones a terceros (familiares, vecinos, empleadores) ni difundas la deuda.
    3. Ofrece siempre una salida: fecha de compromiso, reprogramación o acercarse a la agencia.
    4. Adapta el formato al canal: WhatsApp/SMS en menos de 400 caracteres; Llamada como guion
       breve con saludo, motivo, propuesta y cierre; Visita como puntos a tratar.
    5. Firma como "Área de Recuperaciones" sin inventar nombres de personas ni teléfonos.
    """,
)

# 3. Agente coordinador.
root_agent = Agent(
    name="agente_cobranza",
    model=GEMINI_MODEL,
    instruction="""
    Eres el asistente de un gestor de Recuperaciones (cobranza) de una caja municipal.
    Tu objetivo es ayudarle a decidir a quién contactar primero, por qué y cómo.

    Tienes dos sub-agentes:
    - `analista_cartera`: consulta la cartera, rankings y detalles de créditos.
    - `redactor_mensajes`: redacta el mensaje o guion de contacto para un crédito concreto.

    Flujo sugerido:
    1. Para "¿a quién llamo hoy?", "dame el top", "¿cómo está la cartera?" o preguntas por un
       crédito, delega en `analista_cartera`.
    2. Si el gestor pide el mensaje o guion para un cliente, primero obtén su detalle con
       `analista_cartera` y luego pásale esos datos a `redactor_mensajes`.
    3. Presenta los rankings en tablas markdown con: crédito, cliente, tramo, días de atraso,
       saldo, prioridad y acción sugerida. Explica en una o dos líneas los motivos de los primeros.
    4. Responde en español, con tono profesional y empático.
    5. Recuerda, si te preguntan, que los datos son ficticios y que el puntaje es una ayuda para
       el gestor, no una decisión automática sobre el cliente.
    """,
    tools=[
        AgentTool(agent=analista_cartera),
        AgentTool(agent=redactor_mensajes),
    ],
)
