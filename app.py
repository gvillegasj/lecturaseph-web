import streamlit as st
import pandas as pd
import io
import time

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Lecturas EPH - Gestión de Agua", layout="wide", page_icon="💧")

# Inyección de CSS para tema de Agua (Verde, Blanco, Rojo)
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://img.freepik.com/free-photo/abstract-blue-water-surface-with-ripples-soft-gradient-background_10307-550.jpg");
        background-size: cover;
    }

    /* Contenedor principal para legibilidad */
    .block-container {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 40px !important;
        margin-top: 20px;
    }

    h1, h2, h3 { color: #004d40 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }

    /* Botones Estilo Agua */
    .stButton>button {
        background-color: #2e7d32 !important; /* Verde */
        color: white !important;
        border-radius: 25px;
        border: none;
        padding: 10px 25px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #d32f2f !important; /* Rojo */
        transform: scale(1.05);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f8e9;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        color: #1b5e20;
    }
    </style>
""", unsafe_allow_html=True)

# --- ESTADO DE SESIÓN ---
if 'ingresado' not in st.session_state:
    st.session_state.ingresado = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'file_locked' not in st.session_state:
    st.session_state.file_locked = False
if 'historial_lecturas' not in st.session_state:
    st.session_state.historial_lecturas = {}  # {id: [lista_de_lecturas]}
if 'form_reset' not in st.session_state:
    st.session_state.form_reset = False


def reiniciar_app():
    st.session_state.df = None
    st.session_state.file_locked = False
    st.session_state.ingresado = False
    st.rerun()


# --- VISTA 1: PÁGINA DE INICIO ---
if not st.session_state.ingresado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/3105/3105807.png", width=150)
        st.title("💧 Bienvenido a LecturasEPH")
        st.subheader("Sistema de Gestión de Consumo de Acueducto")
        st.write("Cargue sus datos mensuales, valide lecturas y genere informes eficientemente.")
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            st.session_state.ingresado = True
            st.rerun()

# --- VISTA 2: APLICACIÓN PRINCIPAL ---
else:
    st.sidebar.title("💧 Menú de Control")
    if st.sidebar.button("Cerrar Sesión / Inicio"):
        st.session_state.ingresado = False
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📁 Cargue", "🔍 Edición", "📊 Histórico", "📥 Exportar"])

    # --- TAB 1: CARGUE ---
    with tab1:
        st.header("Configuración de Mes")
        if not st.session_state.file_locked:
            mes = st.text_input("Mes de facturación:")
            archivo = st.file_uploader("Subir base de datos (Excel)", type=["xlsx"])
            if archivo and mes:
                if st.button("Procesar y Bloquear"):
                    df_temp = pd.read_excel(archivo)
                    df_temp.columns = df_temp.columns.str.lower().str.strip()
                    # Inicializar columnas necesarias
                    df_temp['lectura_actual'] = pd.NA
                    df_temp['estado_actual'] = df_temp['estado del medidor']
                    df_temp['nota'] = ""
                    df_temp['leido'] = False

                    st.session_state.df = df_temp
                    st.session_state.mes_actual = mes
                    st.session_state.file_locked = True
                    st.success(f"Archivo de {mes} cargado con éxito.")
                    st.rerun()
        else:
            st.info(f"✅ Archivo bloqueado: **{st.session_state.mes_actual}**")
            if st.button("🔄 Modificar / Cargar otro archivo"):
                st.session_state.df = None
                st.session_state.file_locked = False
                st.rerun()

    # --- TAB 2: BÚSQUEDA Y EDICIÓN ---
    with tab2:
        if st.session_state.df is not None:
            # Barra de progreso
            total = len(st.session_state.df)
            leidos = st.session_state.df['leido'].sum()
            prog = leidos / total
            st.write(f"Avance: {leidos}/{total} ({int(prog * 100)}%)")
            st.progress(prog)

            st.markdown("### 🔎 Buscar Suscriptor")
            busqueda = st.text_input("Código de Suscriptor:", key="input_busqueda")

            if busqueda:
                df = st.session_state.df
                df['codigosuscriptor'] = df['codigosuscriptor'].astype(str)
                res = df[df['codigosuscriptor'] == busqueda]

                if not res.empty:
                    idx = res.index[0]
                    # Datos precargados
                    st.success(f"Suscriptor: {df.at[idx, 'nombre']} | Dirección: {df.at[idx, 'direccion']}")
                    lect_ant = df.at[idx, 'lectura anterior']

                    with st.form("form_lectura", clear_on_submit=True):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"Lectura Anterior: **{lect_ant}**")
                            nueva_lect = st.number_input("Lectura Actual:", value=float(lect_ant), step=1.0)

                        with col_b:
                            nuevo_estado = st.selectbox("Estado Medidor:", [1, 2],
                                                        format_func=lambda x: "Bueno (1)" if x == 1 else "Dañado (2)")

                        # Lógica de Nota Condicional
                        nota_final = ""
                        if nuevo_estado == 1 and nueva_lect == lect_ant:
                            nota_final = st.selectbox("Situación:", ["Casa sola", "Desocupada", "Otro"])

                        btn_guardar = st.form_submit_button("Guardar y Siguiente")

                        if btn_guardar:
                            if nueva_lect < lect_ant:
                                st.error("La lectura actual no puede ser menor a la anterior.")
                            else:
                                # Guardar en DF principal
                                st.session_state.df.at[idx, 'lectura_actual'] = int(nueva_lect)
                                st.session_state.df.at[idx, 'estado_actual'] = nuevo_estado
                                st.session_state.df.at[idx, 'nota'] = nota_final
                                st.session_state.df.at[idx, 'leido'] = True

                                # Guardar en Historial
                                id_sus = str(busqueda)
                                record = {"Mes": st.session_state.mes_actual, "Lectura": int(nueva_lect),
                                          "Consumo": int(nueva_lect - lect_ant)}
                                if id_sus not in st.session_state.historial_lecturas:
                                    st.session_state.historial_lecturas[id_sus] = []
                                st.session_state.historial_lecturas[id_sus].append(record)

                                st.balloons()
                                time.sleep(1)
                                st.rerun()  # Esto limpia el formulario y vuelve al estado inicial
                else:
                    st.error("Código no registrado.")
        else:
            st.warning("Cargue un archivo primero.")

    # --- TAB 3: HISTÓRICO ---
    with tab3:
        st.header("📚 Historial de Consumos")
        id_hist = st.text_input("Consultar histórico (Código Suscriptor):")
        if id_hist:
            if id_hist in st.session_state.historial_lecturas:
                hist_data = pd.DataFrame(st.session_state.historial_lecturas[id_hist])
                st.table(hist_data)
                # Mini gráfico
                st.line_chart(hist_data.set_index("Mes")["Consumo"])
            else:
                st.info("No hay registros históricos para este código aún.")

    # --- TAB 4: EXPORTAR ---
    with tab4:
        if st.session_state.df is not None:
            df_final = st.session_state.df
            total = len(df_final)
            leidos = df_final['leido'].sum()

            if leidos == total:
                st.header("📥 Descarga de Resultados")

                # Cálculos enteros
                df_final['consumo_m3'] = (df_final['lectura_actual'] - df_final['lectura anterior']).astype(int)
                total_m3 = df_final['consumo_m3'].sum()
                buenos = len(df_final[df_final['estado_actual'] == 1])
                danados = len(df_final[df_final['estado_actual'] == 2])

                col1, col2, col3 = st.columns(3)
                col1.metric("Medidores Buenos", buenos)
                col2.metric("Medidores Dañados", danados)
                col3.metric("Total M³ Consumidos", total_m3)

                # Generar Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False)

                st.download_button(
                    label="DESCARGAR EXCEL FINAL",
                    data=output.getvalue(),
                    file_name=f"Lecturas_{st.session_state.mes_actual}.xlsx",
                    mime="application/vnd.ms-excel",
                    on_click=reiniciar_app  # Al descargar, llama a la función que reinicia a la página de inicio
                )
            else:
                st.warning(f"Faltan {total - leidos} lecturas por ingresar para habilitar la descarga.")