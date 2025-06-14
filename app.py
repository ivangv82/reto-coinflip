# Contenido completo para app.py (versión para Streamlit Cloud con Google Sheets)

import streamlit as st
import random
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Configuración de la Página y Conexiones ---
st.set_page_config(page_title="Reto CoinFlip", page_icon="🪙", layout="centered")

# Usamos cache para las conexiones para no reconectar en cada rerun
@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource
def get_sheets(_client):
    spreadsheet = _client.open_by_key("1RRA_N34InULYrNma-eF6QLNtPt6ZaqRfQ87gjShfTTg")
    registros_sheet = spreadsheet.worksheet("Registros")
    partidas_sheet = spreadsheet.worksheet("Partidas")
    return registros_sheet, partidas_sheet

# Obtenemos los clientes y hojas
client = get_gspread_client()
registros_sheet, partidas_sheet = get_sheets(client)

# --- Lógica de la Partida (usando Google Sheets) ---

# En app.py, reemplaza la función cargar_partida por esta nueva versión:

def cargar_partida(email):
    """
    Carga el estado de una partida en modo "detective",
    imprimiendo cada paso en pantalla.
    """
    st.info("--- Iniciando Cargar Partida ---")
    st.write(f"1. Buscando email: '{email}' en la hoja 'Partidas'...")

    try:
        # Buscamos la celda que contiene el email
        cell = partidas_sheet.find(email)

        # Si `find` no devuelve nada, es un jugador nuevo.
        if not cell:
            st.success("2. Email no encontrado. Se tratará como un jugador nuevo.")
            return None

        st.write(f"2. Email encontrado en la fila: {cell.row}")
        row_values = partidas_sheet.row_values(cell.row)
        st.write(f"3. Contenido de la fila: `{row_values}`")

        # Comprobación de seguridad: la fila debe tener al menos 4 columnas
        if len(row_values) < 4:
            st.warning("4. La fila está incompleta (tiene menos de 4 columnas). Se tratará como partida nueva.")
            return None

        st.write("4. La fila parece completa. Intentando procesar los datos...")

        # Intentar convertir los datos uno por uno para encontrar el error exacto
        try:
            saldo_str = row_values[1]
            tiradas_str = row_values[2]
            game_over_str = row_values[3]

            st.write(f"  - Saldo leído: '{saldo_str}'")
            st.write(f"  - Tiradas leídas: '{tiradas_str}'")
            st.write(f"  - Game Over leído: '{game_over_str}'")

            # Conversión a los tipos correctos
            saldo = float(saldo_str) if saldo_str else 0.0
            tiradas = int(tiradas_str) if tiradas_str else 0
            game_over = bool(int(game_over_str)) if game_over_str else False

            st.success("5. Datos procesados con éxito.")
            return {
                "row": cell.row, "saldo": saldo,
                "tiradas_realizadas": tiradas, "game_over": game_over
            }

        except (ValueError, IndexError) as e:
            st.error(f"5. ERROR al procesar los datos de la fila. Falla la conversión de tipos. Error: {e}")
            st.warning("Se tratará como una partida nueva para evitar un fallo.")
            return None

    except gspread.CellNotFound:
        st.success("2. Excepción 'CellNotFound'. Se tratará como un jugador nuevo.")
        return None
    except Exception as e:
        st.error("Ha ocurrido un error inesperado en `cargar_partida`.")
        st.exception(e)
        return None


def guardar_partida(row, email, saldo, tiradas, game_over_status):
    """Guarda o actualiza el estado de una partida en la hoja 'Partidas'."""
    data = [email, saldo, tiradas, int(game_over_status)]
    if row:
        partidas_sheet.update(f'A{row}:D{row}', [data])
    else:
        partidas_sheet.append_row(data, value_input_option='USER_ENTERED')

# --- Lógica Principal del Juego ---

def login_o_registro(email):
    """Maneja el login: carga una partida existente o crea una nueva."""
    partida_existente = cargar_partida(email)
    
    if partida_existente:
        st.info("Cargando tu partida anterior...")
        st.session_state.partida_row = partida_existente['row']
        st.session_state.saldo = partida_existente['saldo']
        st.session_state.tiradas_realizadas = partida_existente['tiradas_realizadas']
        st.session_state.game_over = partida_existente['game_over']
    else:
        st.info("¡Bienvenido! Creando una nueva partida para ti...")
        registros_sheet.append_row([email, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Iniciado"])
        
        st.session_state.partida_row = None # Se creará en el primer guardado
        st.session_state.saldo = 25.00
        st.session_state.tiradas_realizadas = 0
        st.session_state.game_over = False
        guardar_partida(None, email, st.session_state.saldo, st.session_state.tiradas_realizadas, False)
        st.session_state.partida_row = len(partidas_sheet.get_all_values()) # Asignar la nueva fila

    st.session_state.email_registrado = email
    st.session_state.historial_saldo = [st.session_state.saldo]


def realizar_tirada(monto_apuesta, eleccion_usuario):
    if monto_apuesta <= 0 or monto_apuesta > st.session_state.saldo:
        st.error("Apuesta inválida.")
        return

    es_cara = random.random() < 0.6
    st.session_state.tiradas_realizadas += 1
    
    if (eleccion_usuario == ("Cara" if es_cara else "Cruz")):
        st.session_state.saldo += monto_apuesta
    else:
        st.session_state.saldo -= monto_apuesta
    
    game_over_check = (st.session_state.saldo < 0.01 or st.session_state.tiradas_realizadas >= 100)
    st.session_state.game_over = game_over_check
    
    guardar_partida(st.session_state.partida_row, st.session_state.email_registrado, st.session_state.saldo, st.session_state.tiradas_realizadas, game_over_check)
    
    if game_over_check:
        try:
            cell = registros_sheet.find(st.session_state.email_registrado)
            if cell:
                registros_sheet.update_cell(cell.row, 3, f"Finalizado - ${st.session_state.saldo:,.2f}")
        except Exception:
            st.warning("No se pudo actualizar el estado final en la hoja de Registros.")


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
else:
    # PANTALLA DE JUEGO ACTIVO
    if not st.session_state.game_over:
        # ... (El resto de la UI es idéntico al anterior, lo omito por brevedad) ...
        # ... (Puedes copiarlo de la versión anterior si quieres, pero no cambia) ...
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
    # PANTALLA DE FIN DE JUEGO
    else:
        st.header("🏁 ¡Juego Terminado! 🏁")
        st.balloons()
        st.metric("🏆 Saldo Final", f"${st.session_state.saldo:,.2f}")
        st.success("✅ ¡Gracias por participar! Tu puntuación final ha sido registrada.")
        st.markdown("---")
        st.subheader("¿Quieres aprender a invertir con un sistema probado?")
        st.markdown("Da el siguiente paso y mejora tu operativa con mi curso gratuito de **Turbobolsa Lite**.")
        st.link_button("¡Apuntarme al Curso Gratuito!", "https://formacionenbolsa.com/turbobolsa-lite/", type="primary")
