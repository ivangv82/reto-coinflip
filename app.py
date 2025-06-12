import streamlit as st
import random
import time

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Reto CoinFlip",
    page_icon="🪙",
    layout="centered"
)

# --- Lógica del Juego ---

def inicializar_juego():
    """Configura o resetea el estado inicial del juego."""
    st.session_state.saldo = 25.00
    st.session_state.tiradas_realizadas = 0
    st.session_state.game_over = False
    st.session_state.mensajes = []

def realizar_tirada(monto_apuesta, eleccion_usuario):
    """Procesa una ronda del juego: lanza la moneda, calcula el resultado y actualiza el estado."""
    if monto_apuesta <= 0:
        st.session_state.mensajes.append(("error", "La apuesta debe ser mayor que cero."))
        return
    
    if monto_apuesta > st.session_state.saldo:
        st.session_state.mensajes.append(("error", "No puedes apostar más de tu saldo actual."))
        return

    # Simulación de la moneda cargada
    es_cara = random.random() < 0.6  # 60% de probabilidad de ser Cara
    resultado_moneda = "Cara" if es_cara else "Cruz"
    
    st.session_state.tiradas_realizadas += 1
    
    ganador = (eleccion_usuario == resultado_moneda)
    
    mensaje_resultado = f"Tirada {st.session_state.tiradas_realizadas}: Salió **{resultado_moneda}**. "
    
    if ganador:
        st.session_state.saldo += monto_apuesta
        st.session_state.mensajes.append(("success", f"{mensaje_resultado} ¡Ganaste ${monto_apuesta:,.2f}! Tu nuevo saldo es ${st.session_state.saldo:,.2f}."))
    else:
        st.session_state.saldo -= monto_apuesta
        st.session_state.mensajes.append(("warning", f"{mensaje_resultado} Perdiste ${monto_apuesta:,.2f}. Tu nuevo saldo es ${st.session_state.saldo:,.2f}."))
        
    # Comprobar si el juego ha terminado
    if st.session_state.saldo < 0.01 or st.session_state.tiradas_realizadas >= 100:
        st.session_state.game_over = True


# --- Inicialización del Estado de la Sesión ---
if 'saldo' not in st.session_state:
    inicializar_juego()

# --- Interfaz de Usuario ---

st.title("🪙 Reto CoinFlip")
st.markdown("""
Bienvenido al reto. Empiezas con **$25** y tienes **100 tiradas** para maximizar tu saldo.
La moneda está cargada: **60% de probabilidad de Cara** y 40% de Cruz.
¡Piensa bien tu estrategia y que tengas suerte!
""")

st.divider()

# --- Panel de Estado y Apuestas ---
if not st.session_state.game_over:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Saldo Actual", f"${st.session_state.saldo:,.2f}")
    with col2:
        st.metric("🔄 Tiradas Restantes", f"{100 - st.session_state.tiradas_realizadas}")
        
    st.subheader("Realiza tu apuesta")
    
    monto_apuesta = st.number_input(
        "¿Cuánto quieres apostar?", 
        min_value=0.01, 
        max_value=st.session_state.saldo, 
        value=max(0.01, round(st.session_state.saldo * 0.1, 2)), # Sugerencia del 10%
        step=0.01,
        format="%.2f"
    )
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Apostar a Cara (60%)", use_container_width=True, type="primary"):
            realizar_tirada(monto_apuesta, "Cara")
            st.rerun()

    with c2:
        if st.button("Apostar a Cruz (40%)", use_container_width=True):
            realizar_tirada(monto_apuesta, "Cruz")
            st.rerun()

# --- Pantalla de Fin de Juego ---
else:
    st.header("🏁 ¡Juego Terminado! 🏁")
    st.balloons()
    st.metric("🏆 Saldo Final", f"${st.session_state.saldo:,.2f}")
    st.metric("Tiradas Realizadas", st.session_state.tiradas_realizadas)
    
    st.info("Gracias por participar. ¡No olvides apuntarte a la Masterclass para analizar las estrategias y anunciar a los ganadores!")

    if st.button("Jugar de Nuevo"):
        inicializar_juego()
        st.rerun()

# --- Historial de Mensajes ---
st.divider()
st.write("**Historial de jugadas:**")

if not st.session_state.mensajes:
    st.caption("Aún no has realizado ninguna jugada.")

# Mostrar mensajes en orden inverso (el más nuevo arriba)
for tipo, msg in reversed(st.session_state.mensajes):
    if tipo == "success":
        st.success(msg, icon="🎉")
    elif tipo == "warning":
        st.warning(msg, icon="📉")
    elif tipo == "error":
t.error(msg, icon="❗")
