# Contenido completo para app.py (versión con sesiones persistentes)

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

DB_FILE = "coinflip_log.db"

# --- Lógica de Base de Datos ---

def get_db_connection():
    """Conecta con la DB y se asegura de que ambas tablas existan."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tiradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, email TEXT NOT NULL,
            tirada_num INTEGER NOT NULL, apuesta REAL NOT NULL, eleccion TEXT NOT NULL,
            resultado TEXT NOT NULL, saldo_anterior REAL NOT NULL, saldo_nuevo REAL NOT NULL,
            timestamp DATETIME NOT NULL
        );
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS partidas (
            email TEXT PRIMARY KEY, saldo REAL NOT NULL,
            tiradas_realizadas INTEGER NOT NULL, game_over INTEGER NOT NULL DEFAULT 0,
            last_updated DATETIME NOT NULL
        );
    ''')
    return conn

def cargar_partida(email):
    """Carga el estado de una partida desde la DB para un email dado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo, tiradas_realizadas, game_over FROM partidas WHERE email = ?", (email,))
    partida = cursor.fetchone()
    conn.close()
    if partida:
        return {"saldo": partida[0], "tiradas_realizadas": partida[1], "game_over": bool(partida[2])}
    return None

def guardar_partida(email, saldo, tiradas, game_over_status):
    """Guarda o actualiza el estado de una partida en la DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO partidas (email, saldo, tiradas_realizadas, game_over, last_updated) VALUES (?, ?, ?, ?, ?)",
        (email, saldo, tiradas, int(game_over_status), datetime.now())
    )
    conn.commit()
    conn.close()

def log_tirada_en_db(session_id, email, tirada_num, apuesta, eleccion, resultado, saldo_anterior, saldo_nuevo):
    """Guarda el registro de una tirada en la tabla de tiradas."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tiradas (session_id, email, tirada_num, apuesta, eleccion, resultado, saldo_anterior, saldo_nuevo, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, email, tirada_num, apuesta, eleccion, resultado, saldo_anterior, saldo_nuevo, datetime.now())
    )
    conn.commit()
    conn.close()
    
# --- Lógica de Google Sheets ---

def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1RRA_N34InULYrNma-eF6QLNtPt6ZaqRfQ87gjShfTTg").sheet1
    return sheet

# --- Lógica del Juego ---

def login_o_registro(email):
    """Maneja el login: carga una partida existente o crea una nueva."""
    partida_existente = cargar_partida(email)
    
    if partida_existente:
        st.info("Cargando tu partida anterior...")
        st.session_state.saldo = partida_existente['saldo']
        st.session_state.tiradas_realizadas = partida_existente['tiradas_realizadas']
        st.session_state.game_over = partida_existente['game_over']
        st.session_state.historial_saldo = [partida_existente['saldo']] # Simplificado, se podría guardar/cargar el historial completo
    else:
        st.info("¡Bienvenido! Creando una nueva partida para ti...")
        # Registrar en Google Sheets solo la primera vez
        try:
            sheet = get_gsheet()
            lista_emails = sheet.col_values(1)
            if email not in lista_emails:
                 sheet.append_row([email, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Iniciado"])
        except Exception as e:
            st.error("No se pudo contactar con el registro de Google Sheets.")
            st.exception(e)
            return

        # Inicializar partida nueva
        st.session_state.saldo = 25.00
        st.session_state.tiradas_realizadas = 0
        st.session_state.game_over = False
        st.session_state.historial_saldo = [25.00]
        guardar_partida(email, st.session_state.saldo, st.session_state.tiradas_realizadas, st.session_state.game_over)

    st.session_state.email_registrado = email
    st.session_state.session_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"


def realizar_tirada(monto_apuesta, eleccion_usuario):
    if monto_apuesta <= 0 or monto_apuesta > st.session_state.saldo:
        st.error("Apuesta inválida.")
        return

    saldo_anterior = st.session_state.saldo
    es_cara = random.random() < 0.6
    resultado_moneda = "Cara" if es_cara else "Cruz"
    st.session_state.tiradas_realizadas += 1
    
    if (eleccion_usuario == resultado_moneda):
        st.session_state.saldo += monto_apuesta
    else:
        st.session_state.saldo -= monto_apuesta
    
    st.session_state.historial_saldo.append(st.session_state.saldo)
    log_tirada_en_db(st.session_state.session_id, st.session_state.email_registrado, st.session_state.tiradas_realizadas, monto_apuesta, eleccion_usuario, resultado_moneda, saldo_anterior, st.session_state.saldo)

    game_over_check = (st.session_state.saldo < 0.01 or st.session_state.tiradas_realizadas >= 100)
    st.session_state.game_over = game_over_check
    
    guardar_partida(st.session_state.email_registrado, st.session_state.saldo, st.session_state.tiradas_realizadas, game_over_check)
    
    if game_over_check:
        # Actualizar el resultado final en Google Sheets
        try:
            sheet = get_gsheet()
            cell = sheet.find(st.session_state.email_registrado)
            if cell:
                sheet.update_cell(cell.row, 3, f"Finalizado - ${st.session_state.saldo:,.2f}")
        except Exception:
            st.warning("No se pudo actualizar el estado final en Google Sheets.")


# --- Interfaz de Usuario (UI) ---

st.title("🪙 Reto CoinFlip")

# Pantalla de Login/Registro
if 'email_registrado' not in st.session_state:
    st.subheader("Introduce tu email para jugar o continuar tu partida")
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="tu.email@ejemplo.com")
        submitted = st.form_submit_button("Jugar")
        if submitted and email:
            login_o_registro(email)
            st.rerun()

# Pantalla de Juego o Fin de Juego
else:
    # PANTALLA DE JUEGO ACTIVO
    if not st.session_state.game_over:
        c1, c2 = st.columns(2)
        c1.metric("💰 Saldo Actual", f"${st.session_state.saldo:,.2f}")
        c2.metric("🔄 Tiradas Restantes", f"{100 - st.session_state.tiradas_realizadas}")
        
        st.subheader("Cantidad a apostar")
        monto_apuesta = st.number_input("Monto a apostar:", label_visibility="collapsed", min_value=0.01, max_value=st.session_state.saldo, value=max(0.01, round(st.session_state.saldo * 0.1, 2)), step=0.01, format="%.2f")
        
        c1, c2 = st.columns(2)
        if c1.button("Apostar a Cara (60%)", use_container_width=True, type="primary"):
            realizar_tirada(monto_apuesta, "Cara")
            st.rerun()
        if c2.button("Apostar a Cruz (40%)", use_container_width=True):
            realizar_tirada(monto_apuesta, "Cruz")
            st.rerun()

        st.markdown("---")
        st.subheader("Reglas del Juego:")
        st.markdown("- Comienzas con **$25**.\n- Tienes **100 tiradas**.\n- Cara (60%), Cruz (40%).\n- El juego termina al llegar a 100 tiradas o si el saldo es cero.")
        
        st.subheader("Premios:")
        st.markdown("- **🥇 1er Puesto:** 12 meses Bolsa Academy + Curso Diseño Sistemas + Tutoría.\n- **🥈 2º Puesto:** 6 meses Bolsa Academy + Curso Avanzado Programación + Tutoría.\n- **🥉 3er Puesto:** 1 mes Bolsa Academy + Tutoría.")

    # PANTALLA DE FIN DE JUEGO
    else:
        st.header("🏁 ¡Juego Terminado! 🏁")
        st.balloons()
        st.metric("🏆 Saldo Final", f"${st.session_state.saldo:,.2f}")
        
        st.subheader("Evolución de tu Capital")
        chart_data = pd.DataFrame({'Tirada': range(len(st.session_state.historial_saldo)), 'Saldo': st.session_state.historial_saldo})
        st.line_chart(chart_data, x='Tirada', y='Saldo')

        st.success("✅ ¡Gracias por participar! Tu puntuación final ha sido registrada.")
        st.markdown("---")
        st.subheader("¿Quieres aprender a invertir con un sistema probado?")
        st.markdown("Da el siguiente paso y mejora tu operativa con mi curso gratuito de **Turbobolsa Lite**.")
        st.link_button("¡Apuntarme al Curso Gratuito!", "https://formacionenbolsa.com/turbobolsa-lite/", type="primary")
