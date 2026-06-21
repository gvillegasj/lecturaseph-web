import streamlit as st
import pandas as pd
import io
import datetime
import time

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Lecturas EPH - Gestión de Agua", layout="wide", page_icon="💧")

# Inyección de CSS para tema de Acueducto (Verde, Blanco, Rojo)
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://img.freepik.com/free-photo/abstract-blue-water-surface-with-ripples-soft-gradient-background_10307-550.jpg");
        background-size: cover;
    }
    
    .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 40px !important;
        margin-top: 20px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1);
    }

    h1, h2, h3 { color: #004d40 !important; font-family: 'Segoe UI', sans-serif; }
    
    .stButton>button {
        background-color: #2e7d32 !important; /* Verde */
        color: white !important;
        border-radius: 25px;
        border: none;
        padding: 10px 25px;
        transition: 0.3s;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #d32f2f !important; /* Rojo */
        transform: scale(1.02);
    }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #e8f5e9;
        border-radius: 10px 10px 0 0;
        padding: 12px 24px;
        color: #1b5e20;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #2e7d32 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
if 'ingresado' not in st.session_state:
    st.session_state.ingresado = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'file_locked' not in st.session_state:
    st.session_state.file_locked = False
if 'historial_lecturas' not in st.session_state:
    st.session_state.historial_lecturas = {}  # {codigo: [lista de dicts]}
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'hora_cargue' not in st.session_state:
    st.session_state.hora_cargue = None
if 'mes_actual' not in st.session_state:
    st.session_state.mes_actual = ""
if 'anio_actual' not in st.session_state:
    st.session_state.anio_actual = ""

# --- FUNCIONES DE CONTROL ---
def registrar_log(accion):
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append({"Fecha/Hora": ahora, "Acción": accion})

def finalizar_y_regresar_inicio():
    # Registrar evento de exportación final
    ahora = datetime.datetime.now()
    duracion = ahora - st.session_state.hora_cargue
    horas, rem = divmod(duracion.seconds, 3600)
    minutos, segundos = divmod(rem, 60)
    tiempo_str = f"{horas}h {minutos}m {segundos}s"
    
    registrar_log(f"Exportación realizada con éxito. Proceso total completado en: {tiempo_str}")
    
    # Resetear variables de proceso manteniendo historial y logs activos
    st.session_state.df = None
    st.session_state.file_locked = False
    st.session_state.ingresado = False

# --- VISTA 1: PÁGINA DE INICIO ---
if not st.session_state.ingresado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3105/3105807.png", width=120)
        st.title("💧 Sistema Lecturas EPH")
        st.subheader("Control Operativo de Acueducto")
        st.write("Plataforma profesional para validación y registro de micromedición.")
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            st.session_state.ingresado = True
            registrar_log("Usuario ingresó al sistema principal.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- VISTA 2: APLICACIÓN PRINCIPAL (CON LOGICA DE PESTAÑAS SECUENCIALES) ---
else:
    st.sidebar.title("💧 Menú de Control")
    if st.sidebar.button("Cerrar Sesión / Inicio"):
        registrar_log("Usuario cerró sesión de forma manual.")
        st.session_state.ingresado = False
        st.rerun()

    # Configuración dinámica de pestañas según el cumplimiento de procesos
    lista_pestanas = ["📁 Cargue de Archivo"]
    
    if st.session_state.file_locked:
        lista_pestanas.extend(["🔍 Edición de Lecturas", "📊 Histórico de Suscriptores"])
        
        # Validar si el 100% de las lecturas fueron procesadas
        total_registros = len(st.session_state.df) if st.session_state.df is not None else 0
        leidos = st.session_state.df['leido'].sum() if st.session_state.df is not None else 0
        if total_registros > 0 and leidos == total_registros:
            lista_pestanas.append("📥 Exportar e Informes")
            
    lista_pestanas.append("📑 Logs del Sistema")
    
    # Creación de los objetos de pestañas correspondientes
    objetos_pestanas = st.tabs(lista_pestanas)
    mapeo_pestanas = dict(zip(lista_pestanas, objetos_pestanas))

    # ==========================================
    # PESTAÑA: CARGUE DE ARCHIVO
    # ==========================================
    if "📁 Cargue de Archivo" in mapeo_pestanas:
        with mapeo_pestanas["📁 Cargue de Archivo"]:
            st.header("Cargue y Validación de Base de Datos")
            
            if not st.session_state.file_locked:
                col_mes, col_anio = st.columns(2)
                
                with col_mes:
                    meses_lista = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    mes_sel = st.selectbox("Seleccione el mes a procesar:", meses_lista)
                
                with col_anio:
                    anio_actual_sistema = datetime.datetime.now().year
                    anios_lista = [anio_actual_sistema, anio_actual_sistema + 1]
                    anio_sel = st.selectbox("Seleccione el año correspondiente:", anios_lista)
                
                archivo_subido = st.file_uploader("Subir archivo Excel con la ruta mensual", type=["xlsx"])
                
                if archivo_subido:
                    if st.button("Procesar y Bloquear Base de Datos"):
                        try:
                            df_temp = pd.read_excel(archivo_subido)
                            df_temp.columns = df_temp.columns.str.lower().str.strip()
                            
                            # Validar consistencia temporal con el historial acumulado
                            archivo_obsoleto = False
                            for _, fila in df_temp.iterrows():
                                cod_sus = str(fila['codigosuscriptor'])
                                lect_ant_archivo = fila['lectura anterior']
                                
                                if cod_sus in st.session_state.historial_lecturas:
                                    registros_historicos = st.session_state.historial_lecturas[cod_sus]
                                    if registros_historicos:
                                        ultima_lectura_real = registros_historicos[-1]['Lectura']
                                        if lect_ant_archivo < ultima_lectura_real:
                                            archivo_obsoleto = True
                                            st.error(f"❌ Error Crítico: El suscriptor {cod_sus} registra una lectura histórica de {ultima_lectura_real}, pero el archivo cargado indica una lectura anterior de {lect_ant_archivo}. El archivo está obsoleto.")
                                            registrar_log(f"Intento de cargue fallido: Archivo obsoleto en suscriptor {cod_sus}.")
                                            break
                            
                            if not archivo_obsoleto:
                                # Inicializar estructura de operación interna
                                df_temp['lectura_actual'] = pd.NA
                                df_temp['estado_actual'] = df_temp['estado del medidor']
                                df_temp['nota'] = ""
                                df_temp['leido'] = False
                                
                                st.session_state.df = df_temp
                                st.session_state.mes_actual = mes_sel
                                st.session_state.anio_actual = anio_sel
                                st.session_state.hora_cargue = datetime.datetime.now()
                                st.session_state.file_locked = True
                                
                                registrar_log(f"Cargue exitoso y bloqueo de archivo para el periodo {mes_sel} {anio_sel}.")
                                st.success(f"✅ Base de datos bloqueada para {mes_sel} {anio_sel}. Pestaña de edición habilitada.")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error al estructurar el archivo: {e}")
            else:
                st.info(f"✅ Archivo bloqueado actualmente para el periodo: **{st.session_state.mes_actual} de {st.session_state.anio_actual}**")
                st.write(f"Fecha de inicio del procesamiento: {st.session_state.hora_cargue.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if st.button("🔄 Modificar / Eliminar Archivo Cargado"):
                    registrar_log(f"Se eliminó el archivo del periodo {st.session_state.mes_actual} para reconfiguración.")
                    st.session_state.df = None
                    st.session_state.file_locked = False
                    st.rerun()

    # ==========================================
    # PESTAÑA: EDICIÓN DE LECTURAS
    # ==========================================
    if "🔍 Edición de Lecturas" in mapeo_pestanas:
        with mapeo_pestanas["🔍 Edición de Lecturas"]:
            df = st.session_state.df
            total = len(df)
            leidos = df['leido'].sum()
            prog = leidos / total
            
            st.write(f"**Progreso Operativo:** {leidos} de {total} Suscriptores Procesados ({int(prog*100)}%)")
            st.progress(prog)
            
            st.markdown("---")
            codigo_buscar = st.text_input("Ingrese Código de Suscriptor para Registrar Lectura:", key="buscador_operativo")
            
            if codigo_buscar:
                df['codigosuscriptor'] = df['codigosuscriptor'].astype(str)
                suscriptor_match = df[df['codigosuscriptor'] == str(codigo_buscar)]
                
                if not suscriptor_match.empty:
                    idx = suscriptor_match.index[0]
                    
                    st.info(f"👤 **Suscriptor:** {df.at[idx, 'nombre']}  |  📍 **Dirección:** {df.at[idx, 'direccion']}")
                    lect_ant = df.at[idx, 'lectura anterior']
                    
                    with st.form("formulario_ingreso_lectura", clear_on_submit=True):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"Lectura Anterior registrada: **{int(lect_ant)}**")
                            nueva_lect = st.number_input("Ingrese Lectura Actual:", value=float(lect_ant), step=1.0)
                        
                        with col_b:
                            nuevo_estado = st.selectbox("Estado del Medidor:", [1, 2], 
                                                      format_func=lambda x: "1 - Bueno" if x == 1 else "2 - Dañado")
                        
                        # Restricción Dinámica: Nota visible SOLO si el medidor está bueno y la diferencia es cero
                        nota_final = ""
                        if nuevo_estado == 1 and nueva_lect == lect_ant:
                            st.warning("Diferencia de consumo igual a cero. Seleccione justificación:")
                            nota_final = st.selectbox("Nota de campo:", ["Casa sola", "Desocupada", "Otro"])
                        
                        btn_guardar = st.form_submit_button("Guardar Registro")
                        
                        if btn_guardar:
                            if nueva_lect < lect_ant:
                                st.error("❌ Validación fallida: La lectura actual no puede ser menor a la anterior.")
                            else:
                                # Almacenar en estructura principal (Conversión implícita a Enteros)
                                st.session_state.df.at[idx, 'lectura_actual'] = int(nueva_lect)
                                st.session_state.df.at[idx, 'estado_actual'] = nuevo_estado
                                st.session_state.df.at[idx, 'nota'] = nota_final
                                st.session_state.df.at[idx, 'leido'] = True
                                
                                # Inserción automática en la base histórica indexada
                                cod_str = str(codigo_buscar)
                                registro_historia = {
                                    "Mes": st.session_state.mes_actual,
                                    "Año": st.session_state.anio_actual,
                                    "Lectura": int(nueva_lect),
                                    "Consumo M³": int(nueva_lect - lect_ant)
                                }
                                if cod_str not in st.session_state.historial_lecturas:
                                    st.session_state.historial_lecturas[cod_str] = []
                                st.session_state.historial_lecturas[cod_str].append(registro_historia)
                                
                                registrar_log(f"Lectura registrada para suscriptor {cod_str}. Nueva Lectura: {int(nueva_lect)}, Estado: {nuevo_estado}.")
                                st.success("✅ Datos validados y guardados.")
                                time.sleep(0.5)
                                st.rerun() # Reinicia la pestaña limpiando el formulario y dejando solo el buscador
                else:
                    st.error("El código del suscriptor no se encuentra en el archivo actual.")

    # ==========================================
    # PESTAÑA: HISTÓRICO DE SUSCRIPTORES
    # ==========================================
    if "📊 Histórico de Suscriptores" in mapeo_pestanas:
        with mapeo_pestanas["📊 Histórico de Suscriptores"]:
            st.header("Consulta de Historial y Consumos Anteriores")
            cod_consulta = st.text_input("Buscar historial por Código de Suscriptor:")
            
            if cod_consulta:
                if cod_consulta in st.session_state.historial_lecturas:
                    datos_hist = pd.DataFrame(st.session_state.historial_lecturas[cod_consulta])
                    st.markdown(f"### Historial Acumulado para Suscriptor: **{cod_consulta}**")
                    st.dataframe(datos_hist, use_container_width=True)
                    
                    # Gráfico evolutivo de metros cúbicos consumidos
                    st.line_chart(datos_hist.set_index("Mes")["Consumo M³"])
                else:
                    st.info("No se registran datos históricos guardados en esta sesión para el código ingresado.")

    # ==========================================
    # PESTAÑA: EXPORTAR E INFORMES
    # ==========================================
    if "📥 Exportar e Informes" in mapeo_pestanas:
        with mapeo_pestanas["📥 Exportar e Informes"]:
            st.header("Panel de Cierre e Informes Operativos")
            df_final = st.session_state.df
            
            # Cálculo exacto de métricas obligatoriamente enteras
            df_final['consumo_m3'] = (df_final['lectura_actual'] - df_final['lectura anterior']).astype(int)
            total_m3 = df_final['consumo_m3'].sum()
            buenos = int(len(df_final[df_final['estado_actual'] == 1]))
            danados = int(len(df_final[df_final['estado_actual'] == 2]))
            
            # --- MÓDULO DE INFORME SOLICITADO ---
            st.markdown("### 📋 Resumen de Métricas Operativas")
            col1, col2, col3 = st.columns(3)
            col1.metric("Suscriptores Leídos", len(df_final))
            col2.metric("Medidores en Buen Estado", buenos)
            col3.metric("Medidores Dañados", danados)
            
            st.markdown("---")
            st.markdown("### ⏱️ Control de Tiempos del Proceso")
            
            # Tiempos de Auditoría
            hora_cargue_f = st.session_state.hora_cargue
            hora_exporte_f = datetime.datetime.now() # Hora actual calculada en caliente
            duracion_proceso = hora_exporte_f - hora_cargue_f
            
            horas, rem = divmod(duracion_proceso.seconds, 3600)
            minutos, segundos = divmod(rem, 60)
            tiempo_ejecucion_str = f"{horas}h {minutos}m {segundos}s"
            
            col_inf1, col_inf2 = st.columns(2)
            with col_inf1:
                st.write(f"**Mes de Gestión:** {st.session_state.mes_actual}")
                st.write(f"**Año de Gestión:** {st.session_state.anio_actual}")
                st.write(f"**Fecha y Hora de Cargue:** {hora_cargue_f.strftime('%Y-%m-%d %H:%M:%S')}")
            with col_inf2:
                st.write(f"**Fecha y Hora de Exportación:** {hora_exporte_f.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Consumo General Cargado:** {total_m3} M³")
                st.write(f"**Tiempo Total del Proceso (100%):** {tiempo_ejecucion_str}")
            
            st.markdown("---")
            
            # Generación de la descarga Excel
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Resultados_EPH')
            
            st.download_button(
                label="📥 GENERAR Y DESCARGAR EXCEL FINAL",
                data=output_excel.getvalue(),
                file_name=f"Informe_Final_{st.session_state.mes_actual}_{st.session_state.anio_actual}.xlsx",
                mime="application/vnd.ms-excel",
                on_click=finalizar_y_regresar_inicio
            )

    # ==========================================
    # PESTAÑA: LOGS DEL SISTEMA
    # ==========================================
    if "📑 Logs del Sistema" in mapeo_pestanas:
        with mapeo_pestanas["📑 Logs del Sistema"]:
            st.header("Auditoría de Procesos en Tiempo Real")
            st.write("Registro cronológico estructurado de las operaciones llevadas a cabo en la sesión:")
            
            if st.session_state.logs:
                df_logs = pd.DataFrame(st.session_state.logs)
                st.dataframe(df_logs, use_container_width=True)
            else:
                st.info("No se han registrado acciones en la sesión actual.")
