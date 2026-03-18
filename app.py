import streamlit as st
import google.generativeai as genai
import requests

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="AURA - Caraballeda", page_icon="🛰️", layout="centered")

# --- 2. CONFIGURACIÓN DE GEMINI ---
# Validar si existe la llave en st.secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Falla de configuración: No se encontró la GEMINI_API_KEY en st.secrets. Si estás probando localmente, crea un archivo .streamlit/secrets.toml")
    st.stop()
    
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 3. HERRAMIENTAS (CONEXIÓN A ARCGIS) ---
def consultar_clima_caraballeda():
    """Consulta la lluvia acumulada actual y la fecha de los sensores en Caraballeda."""
    url = "https://services8.arcgis.com/2jmdYNQsteiDSgjD/arcgis/rest/services/weather_data_gdb_v2/FeatureServer/0/query?where=Ciudad=%27Caraballeda%27&outFields=*&orderByFields=OBJECTID+DESC&resultRecordCount=1&f=json"
    respuesta = requests.get(url)
    return respuesta.json()

def consultar_alerta_huracanes():
    """Consulta si hay alertas de huracanes activas en la región costera."""
    url = "https://services8.arcgis.com/2jmdYNQsteiDSgjD/arcgis/rest/services/VenShapes_gdb/FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=False&f=json"
    respuesta = requests.get(url)
    return respuesta.json()

# --- 4. SYSTEM MESSAGE (INSTRUCCIONES DE AURA) ---
INSTRUCCIONES_AURA = """
Eres AURA (Asistente de Gestión de Riesgos Atmosféricos) para Caraballeda, estado La Guaira. Eres una profesional venezolana experta en protección civil.

<OBJETIVO_PRINCIPAL>
Informar el riesgo cruzando datos locales (lluvia) y regionales (huracanes) usando tus herramientas. SIEMPRE redirige al Monitor Oficial.

<CONOCIMIENTO_LOCAL_CARABALLEDA>
- Zonas más vulnerables (Riesgo Muy Alto): Zona de protección del Río San Julián, laderas y cauces de quebradas. Ámbitos: Palmar Este y Oeste, Los Corales, Caribe, Corapal, San Julián y Tarigua.
- Protocolos: Si llueve fuerte por más de 4h cerca de colinas, alejarse. Vigilar si el caudal del río baja bruscamente mientras llueve (posible represamiento).
- Cierra con: "Para ver el protocolo completo, revisa nuestra Guía Oficial: https://storymaps.arcgis.com/stories/b649f5d8425443198bbad65eb39528f5#ref-n-0VE7BJ"

<REGLAS_DE_DATOS>
1. FECHA: Viene en Unix Timestamp (milisegundos). Conviértelo a hora de Venezuela (UTC-4) "DD de Mes de YYYY, HH:MM AM/PM".
2. HURACANES: Si "huracan" != 0, RIESGO MÁXIMO (Ciclón).
3. LLUVIA: Si huracán es 0, evalúa: <90mm (🟢 VERDE), 90-150mm (🟡 AMARILLO), 150-210mm (🟠 NARANJA), >210mm (🔴 ROJO).

<FORMATO_OBLIGATORIO_REPORTE>
🛰️ **Sistema AURA — Monitoreo**
*[Fecha convertida]*
🌀 **Influencia Ciclónica:** [Dato]
🌧️ **Lluvia Acumulada:** [Dato] mm
🚦 **ESTADO GENERAL:** [Color y Nivel]
📢 **Recomendación:** [Consejo breve adaptado al perfil]
🖥️ **Monitor en vivo:** [AQUÍ](https://lsigma.maps.arcgis.com/apps/dashboards/c37a4bbf182a49c2b135672004bdf1e4)
💡 **Guías Oficiales:** [AQUÍ](https://storymaps.arcgis.com/stories/b649f5d8425443198bbad65eb39528f5#ref-n-0VE7BJ)
"""

# Inicializar el modelo con las herramientas
modelo = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    system_instruction=INSTRUCCIONES_AURA,
    tools=[consultar_clima_caraballeda, consultar_alerta_huracanes]
)

# --- 5. INTERFAZ DE USUARIO (STREAMLIT) ---
st.title("🛰️ AURA - Monitor de Riesgos")
st.markdown("Hola, soy AURA. Estoy aquí para informarte sobre el clima y los riesgos atmosféricos en Caraballeda. ¿En qué te puedo ayudar hoy?")

# Inicializar memoria del chat
if "chat" not in st.session_state:
    st.session_state.chat = modelo.start_chat(enable_automatic_function_calling=True)

# Mostrar historial de mensajes (CORREGIDO)
for mensaje in st.session_state.chat.history:
    rol = "assistant" if mensaje.role == "model" else "user"
    
    # El principal error de este script suele ocurrir al intentar iterar directamente 
    # sobre partes que son funciones de herramientas (function_call/function_response).
    texto_mostrar = ""
    for part in mensaje.parts:
        try:
            # Si tiene texto, lo extraemos. Si es una función, text levanta un ValueError
            if part.text:
                texto_mostrar += part.text
        except ValueError:
            pass
            
    # Solo mostramos en pantalla si hay texto válido
    if texto_mostrar.strip():
        with st.chat_message(rol):
            st.markdown(texto_mostrar)

# Caja de texto para el usuario
if prompt := st.chat_input("Ej: ¿Cuál es el reporte del clima actual?"):
    # Mostrar lo que escribió el usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Procesar respuesta con AURA
    with st.chat_message("assistant"):
        with st.spinner("AURA está consultando los sensores de ArcGIS..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
            except Exception as e:
                st.error(f"Ocurrió un error al procesar tu solicitud: {e}")
