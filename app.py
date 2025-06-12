import streamlit as st
import random
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlite3
from datetime import datetime

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Reto CoinFlip",
    page_icon="🪙",
    layout="centered"
)

# --- Conexión a Google Sheets y DB ---
def get_gsheet():
    """Conecta con Google Sheets usando los secretos de Streamlit."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["google_credentials"], scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1RRA_N34InULYrNma-eF6QLNtPt6ZaqRfQ87gjShfTTg").sheet1
    return sheet

def get_db_connection():
    """Conecta con la base de datos SQLite."""
    conn = sqlite3.connect('coinflip_log.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tiradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            email TEXT NOT NULL,
            tirada_num INTEGER NOT NULL,
            apuesta REAL NOT NULL,
            eleccion TEXT NOT NULL,
            resultado TEXT NOT NULL,
            saldo_anterior REAL NOT NULL,
            saldo_nuevo REAL NOT NULL,
            timestamp DATETIME NOT NULL
        );
    ''')
    return conn

# --- Lógica del Juego ---
def inicializar_juego():
    """Configura o resetea el estado inicial del juego."""
    st.session_state.saldo = 25.00
    st.session_state.tiradas_realizadas = 0
    st.session_state.game_over = False
    st.session_state.mensajes = []
    st.session_state.historial_saldo = [25.00] # Para el gráfico
    st.session_state.session_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"

#  función registrar_usuario 

def registrar_usuario(email):
    """
    Registra el email del usuario.
    Devuelve True si tiene éxito, False si hay un error.
    """
    try:
        st.info("Paso 1: Intentando conectar con Google Sheets...")
        sheet = get_gsheet()
        st.info("Paso 2: Conexión exitosa. Intentando escribir en la hoja...")
        
        fila = [email, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Iniciado"]
        sheet.append_row(fila, value_input_option='USER_ENTERED')
        
        st.info("Paso 3: Escritura en la hoja exitosa. Configurando el juego...")
        st.session_state.email_registrado = email
        inicializar_juego()
        st.success("¡Email registrado! Comienza el reto.")
        st.info("Paso 4: Refrescando la aplicación...")
        return True  # Devuelve True si todo fue bien

    except Exception as e:
        st.error(f"❌ Ocurrió un error al registrar el usuario.")
        st.exception(e) # Muestra el error técnico completo
        return False # Devuelve False si hubo un error
def log_tirada_en_db(monto_apuesta, eleccion, resultado, saldo_anterior, saldo_nuevo):
    """Guarda el registro de una tirada en la base de datos SQLite."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tiradas (session_id, email, tirada_num, apuesta, eleccion, resultado, saldo_anterior, saldo_nuevo, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (st.session_state.session_id, st.session_state.email_registrado, st.session_state.tiradas_realizadas, monto_apuesta, eleccion, resultado, saldo_anterior, saldo_nuevo, datetime.now())
    )
    conn.commit()
    conn.close()

def realizar_tirada(monto_apuesta, eleccion_usuario):
    if monto_apuesta <= 0 or monto_apuesta > st.session_state.saldo:
        st.error("Apuesta inválida.")
        return

    saldo_anterior = st.session_state.saldo
    es_cara = random.random() < 0.6
    resultado_moneda = "Cara" if es_cara else "Cruz"
    st.session_state.tiradas_realizadas += 1
    ganador = (eleccion_usuario == resultado_moneda)

    if ganador:
        st.session_state.saldo += monto_apuesta
    else:
        st.session_state.saldo -= monto_apuesta

    st.session_state.historial_saldo.append(st.session_state.saldo)
    log_tirada_en_db(monto_apuesta, eleccion_usuario, resultado_moneda, saldo_anterior, st.session_state.saldo)

    if st.session_state.saldo < 0.01 or st.session_state.tiradas_realizadas >= 100:
        st.session_state.game_over = True
        # Actualizar el resultado final en Google Sheets
        sheet = get_gsheet()
        cell = sheet.find(st.session_state.email_registrado)
        sheet.update_cell(cell.row, 3, f"Finalizado - ${st.session_state.saldo:,.2f}")


# --- Interfaz de Usuario ---
st.title("🪙 Reto CoinFlip")

if 'email_registrado' not in st.session_state:
    st.subheader("Paso 1: Regístrate para empezar")
    with st.form("registro_form"):
        email = st.text_input("Introduce tu email", placeholder="tu.email@ejemplo.com")
        submitted = st.form_submit_button("¡Empezar a Jugar!")
        if submitted and email:
            # Llamamos a la función y guardamos su resultado
            registro_exitoso = registrar_usuario(email)
            # Solo refrescamos la página si el registro tuvo éxito
            if registro_exitoso:
                st.rerun()
else:
    # PANTALLA DE JUEGO
    if not st.session_state.game_over:
        st.metric("💰 Saldo Actual", f"${st.session_state.saldo:,.2f}")
        st.metric("🔄 Tiradas Restantes", f"{100 - st.session_state.tiradas_realizadas}")

        monto_apuesta = st.number_input("Monto a apostar:", min_value=0.01, max_value=st.session_state.saldo, value=max(0.01, round(st.session_state.saldo * 0.1, 2)), step=0.01, format="%.2f")

        c1, c2 = st.columns(2)
        if c1.button("Apostar a Cara (60%)", use_container_width=True, type="primary"):
            realizar_tirada(monto_apuesta, "Cara")
            st.rerun()
        if c2.button("Apostar a Cruz (40%)", use_container_width=True):
            realizar_tirada(monto_apuesta, "Cruz")
            st.rerun()

    # PANTALLA DE FIN DE JUEGO
    else:
        st.header("🏁 ¡Juego Terminado! 🏁")
        st.balloons()
        st.metric("🏆 Saldo Final", f"${st.session_state.saldo:,.2f}")

        st.subheader("Evolución de tu Capital")
        chart_data = pd.DataFrame({
            'Tirada': range(len(st.session_state.historial_saldo)),
            'Saldo': st.session_state.historial_saldo
        })
        st.line_chart(chart_data, x='Tirada', y='Saldo')

        st.info("Gracias por participar. Tu puntuación ha sido registrada.")
        if st.button("Jugar de Nuevo con otro email"):
            # Limpiar solo el email para permitir nuevo registro
            del st.session_state.email_registrado
            st.rerun()
