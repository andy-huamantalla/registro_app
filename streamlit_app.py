
# streamlit_app.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import os

# --- CONEXIÓN A SUPABASE DESDE SECRETS ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CARGAR CATEGORÍAS DESDE SUPABASE ---
def cargar_categorias_por_tipo(tipo):
    data = supabase.table("categorias").select("nombre", "tipo").eq("tipo", tipo).execute()
    return [item["nombre"] for item in data.data]

# --- GUARDAR TRANSACCIÓN ---
def guardar_transaccion(tipo, fecha, monto, descripcion, categoria):
    supabase.table("transacciones").insert({
        "tipo": tipo,
        "fecha": fecha.isoformat(),
        "monto": monto,
        "descripcion": descripcion,
        "categoria": categoria
    }).execute()

# --- CARGAR TODAS LAS TRANSACCIONES ---
def cargar_transacciones():
    data = supabase.table("transacciones").select("*").order("fecha", desc=True).execute()
    return pd.DataFrame(data.data)

# --- FILTRAR TRANSACCIONES POR MES ---
def transacciones_por_mes(df, año, mes):
    df["fecha"] = pd.to_datetime(df["fecha"])
    df_filtrado = df[(df["fecha"].dt.year == año) & (df["fecha"].dt.month == mes)]
    return df_filtrado

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Registro de Finanzas", layout="centered")
menu = st.sidebar.selectbox("Menú", ["Registrar", "Historial", "Resumen mensual"])

if menu == "Registrar":
    st.header("Registrar ingreso o gasto")

    st.markdown("### Selecciona el tipo de transacción")
    col1, col2 = st.columns(2)

    if "tipo" not in st.session_state:
        st.session_state.tipo = "Ingreso"

    def estilo_boton(tipo):
        if st.session_state.tipo == tipo:
            # Botón activo
            return f"background-color:#4CAF50; color:white; padding:10px; border-radius:8px; font-weight:bold; text-align:center"
        else:
            # Botón inactivo
            return f"background-color:#f0f0f0; color:#333; padding:10px; border-radius:8px; text-align:center"

    with col1:
        if st.button("💰 Ingreso", use_container_width=True):
            st.session_state.tipo = "Ingreso"
        st.markdown(f"<div style='{estilo_boton('Ingreso')}'>Ingreso</div>", unsafe_allow_html=True)

    with col2:
        if st.button("💸 Gasto", use_container_width=True):
            st.session_state.tipo = "Gasto"
        st.markdown(f"<div style='{estilo_boton('Gasto')}'>Gasto</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    tipo = st.session_state.tipo 

    fecha = st.date_input("Fecha", value=datetime.date.today())
    monto = st.number_input("Monto", min_value=0.0, format="%.2f")
    descripcion = st.text_input("Descripción")
    categorias = cargar_categorias_por_tipo(tipo)
    categoria = st.selectbox("Categoría", categorias)

    if st.button("Guardar transacción"):
        guardar_transaccion(tipo, fecha, monto, descripcion, categoria)
        st.success("Transacción guardada con éxito")

elif menu == "Historial":
    st.header("Historial de transacciones")
    df = cargar_transacciones()
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.sort_values(by="fecha", ascending=False)
        st.dataframe(df)
    else:
        st.info("No hay transacciones registradas.")

elif menu == "Resumen mensual":
    st.header("Resumen del mes")
    df = cargar_transacciones()
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
        año = st.selectbox("Año", sorted(df["fecha"].dt.year.unique(), reverse=True))
        mes = st.selectbox("Mes", list(range(1, 13)))

        df_mes = transacciones_por_mes(df, int(año), mes)
        ingresos = df_mes[df_mes["tipo"] == "Ingreso"]["monto"].sum()
        gastos = df_mes[df_mes["tipo"] == "Gasto"]["monto"].sum()
        ahorro = ingresos - gastos

        st.markdown(f"### 💰 Ahorro del mes: S/ {ahorro:,.2f}")

        if not df_mes.empty:
            resumen = df_mes.groupby("tipo")["monto"].sum().reset_index()
            fig = px.bar(resumen, x="tipo", y="monto", title="Totales de Ingresos y Gastos",
                         color="tipo", text_auto=True)
            click_data = st.plotly_chart(fig, use_container_width=True)

            tipo_click = st.session_state.get("tipo_seleccionado")

            if st.session_state.get("last_click") != st.session_state.get("_click_data"):
                tipo_click = st.session_state["_click_data"] = st.session_state.get("last_click")

            if st.button("Mostrar detalles de ingresos"):
                tipo_click = "Ingreso"
            elif st.button("Mostrar detalles de gastos"):
                tipo_click = "Gasto"

            if tipo_click in ["Ingreso", "Gasto"]:
                df_detalle = df_mes[df_mes["tipo"] == tipo_click]
                df_detalle = df_detalle.groupby("categoria")["monto"].sum().sort_values(ascending=False).reset_index()
                if not df_detalle.empty:
                    fig_detalle = px.bar(df_detalle, x="monto", y="categoria", orientation="h",
                                         title=f"Detalle de {tipo_click}s por Categoría")
                    st.plotly_chart(fig_detalle, use_container_width=True)
                else:
                    st.info(f"No hay datos de {tipo_click.lower()}s para este mes.")
        else:
            st.info("No hay datos para ese mes.")
    else:
        st.info("No hay transacciones registradas.")
