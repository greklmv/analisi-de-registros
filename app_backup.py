import streamlit as st
import pandas as pd
import io

# Configuració de la pàgina
st.set_page_config(
    page_title="Anàlisi de Registres",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estils CSS personalitzats per una aparença premium
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stSidebar {
        background-color: #f0f2f6;
    }
    h1 {
        color: #1e3d59;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    .stMultiSelect div[data-baseweb="select"] {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("📊 Anàlisi de Registres")
    st.markdown("---")

    # Sidebar: Pujada de fitxers i configuració
    st.sidebar.header("📁 Gestió de Dades")
    uploaded_file = st.sidebar.file_uploader("Carrega el teu fitxer Excel", type=["xlsx", "xls", "csv"])

    if uploaded_file is not None:
        try:
            # Detectar tipus de fitxer i llegir
            file_type = uploaded_file.name.split('.')[-1]
            
            if file_type in ['xlsx', 'xls']:
                # Si és Excel, preguntar quina fulla llegir
                xl = pd.ExcelFile(uploaded_file)
                sheet_names = xl.sheet_names
                selected_sheet = st.sidebar.selectbox("Selecciona la fulla", sheet_names)
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                st.sidebar.info(f"Fulles detectades: {', '.join(sheet_names)}")
            else:
                df = pd.read_csv(uploaded_file)

            # Informació bàsica al Sidebar
            st.sidebar.success(f"✅ Fitxer carregat: {len(df)} files i {len(df.columns)} columnes")

            # --- SECCIÓ 1: Selecció de Variables ---
            st.subheader("🎯 Selecció de Variables")
            st.info("S'han detectat les següents variables al teu fitxer. Selecciona quines vols analitzar.")
            
            # Autodetección de tipos
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"🔢 **Numèriques ({len(numeric_cols)}):** {', '.join(numeric_cols[:5])}...")
            with col2:
                st.write(f"🔡 **Categòriques ({len(categorical_cols)}):** {', '.join(categorical_cols[:5])}...")

            # Filtre multiselecció
            all_columns = df.columns.tolist()
            selected_vars = st.multiselect(
                "Selecciona les variables a analitzar:",
                options=all_columns,
                default=all_columns[:min(5, len(all_columns))] # Selecciona les 5 primeres per defecte
            )

            if not selected_vars:
                st.warning("⚠️ Has de seleccionar almenys una variable per veure les dades.")
            else:
                # Filtrar el DataFrame
                filtered_df = df[selected_vars]

                # --- SECCIÓ 2: Vista Prèvia i Resum ---
                st.markdown("---")
                st.subheader("🔍 Vista Prèvia de l'Anàlisi Seleccionada")
                
                # Resum de mètriques ràpides
                m1, m2, m3 = st.columns(3)
                m1.metric("Variables seleccionades", len(selected_vars))
                m2.metric("Total de registres", len(filtered_df))
                m3.metric("Valors nuls totals", filtered_df.isna().sum().sum())

                # Mostrar dades
                with st.expander("📝 Veure taula de dades completa", expanded=True):
                    st.dataframe(filtered_df, use_container_width=True)

                # Resum estadístic bàsic
                st.subheader("📈 Resum Estadístic")
                st.write(filtered_df.describe(include='all' if any(c in categorical_cols for c in selected_vars) else None).T)

        except Exception as e:
            st.error(f"❌ Error en processar el fitxer: {e}")
    else:
        # Estat inicial quan no hi ha fitxer
        st.info("👈 Si us plau, carrega un fitxer Excel o CSV des de la barra lateral per començar.")
        
        # Demostració opcional si l'usuari vol veure com funciona
        if st.checkbox("Veure estructura d'exemple (Dades fictícies)"):
            mock_data = {
                'ID': range(1, 11),
                'Data': pd.date_range(start='2024-01-01', periods=10),
                'Vendes': [1200, 1500, 900, 2100, 1800, 1400, 1650, 2050, 1100, 1340],
                'Regió': ['Nord', 'Sud', 'Nord', 'Est', 'Oest', 'Sud', 'Nord', 'Oest', 'Est', 'Sud'],
                'Estat': ['Enviat', 'Retard', 'Enviat', 'Enviat', 'Retard', 'Enviat', 'Enviat', 'Enviat', 'Enviat', 'Retard']
            }
            example_df = pd.DataFrame(mock_data)
            st.write("Estructura detectada en l'exemple:")
            st.dataframe(example_df, use_container_width=True)
            st.multiselect("Selector de Variables Emulat:", options=example_df.columns.tolist(), key="mock_vars_new")

if __name__ == "__main__":
    main()
