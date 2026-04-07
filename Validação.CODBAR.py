import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Validador de Boletos", layout="wide")

st.title("🔎 Validador de Boletos - Linha Digitável x Valor Total")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload do arquivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    # Carregar planilha
    df = pd.read_excel(uploaded_file, dtype=str)

    # Normaliza nomes de colunas
    df.columns = df.columns.str.strip().str.lower()

    # Verifica colunas obrigatórias
    colunas_obrigatorias = ["cod.barras", "total", "forma pgto.", "filial", "no. titulo", "situacao"]
    faltando = [col for col in colunas_obrigatorias if col not in df.columns]

    if faltando:
        st.error(f"O arquivo deve conter as colunas: {', '.join(faltando)}")
    else:
        df = df.rename(columns={
            "cod.barras": "CodBarras",
            "total": "Total",
            "forma pgto.": "FormaPgto",
            "filial": "Filial",
            "no. titulo": "NoTitulo",
            "situacao": "Situacao"
        })

        df["CodBarras"] = (
            df["CodBarras"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .str.replace(r"\D", "", regex=True)
            .str.zfill(44)
        )

        df["Total"] = (
            df["Total"]
            .fillna("")
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce")

        df["FormaPgto"] = df["FormaPgto"].fillna("").astype(str).str.strip()
        df["Situacao"] = df["Situacao"].fillna("").astype(str)

        # Filtra títulos não baixados
        df = df[df["Situacao"].str.strip().str.lower() != "titulo baixado"]

        def extrair_valor(codbarras, forma):
            try:
                codbarras = str(codbarras).strip()
                forma = str(forma).strip()

                if len(codbarras) < 44:
                    return None

                if forma in ["30", "31"]:
                    valor_centavos = int(codbarras[9:19])
                elif forma in ["19", "91", "11", "13"]:
                    # revisar essa posição conforme sua regra real
                    valor_centavos = int(codbarras[8:18])
                else:
                    return None

                return valor_centavos / 100
            except:
                return None

        df["Valor_CodBarras"] = df.apply(
            lambda x: extrair_valor(x["CodBarras"], x["FormaPgto"]),
            axis=1
        )

        df["Diferenca"] = df["Total"] - df["Valor_CodBarras"]

        df["Status"] = df.apply(
            lambda x: "OK" if pd.notnull(x["Valor_CodBarras"]) and round(x["Total"], 2) == round(x["Valor_CodBarras"], 2) else "Divergente",
            axis=1
        )

        formas_validas = ["30", "31", "19", "91", "11", "13"]
        df = df[df["FormaPgto"].isin(formas_validas)]

        df["Valor_Total_Titulo"] = df["Total"].map(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else ""
        )
        df["Valor_CodBarras_Formatado"] = df["Valor_CodBarras"].map(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else ""
        )
        df["Diferenca_ft"] = df["Diferenca"].map(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else ""
        )

        filtro = st.radio("Filtrar resultados:", ["Todos", "Somente Divergentes", "Somente OK"])

        if filtro == "Somente Divergentes":
            df_filtrado = df[df["Status"] == "Divergente"]
        elif filtro == "Somente OK":
            df_filtrado = df[df["Status"] == "OK"]
        else:
            df_filtrado = df.copy()

        st.dataframe(
            df_filtrado[[
                "Filial",
                "NoTitulo",
                "FormaPgto",
                "CodBarras",
                "Valor_Total_Titulo",
                "Valor_CodBarras_Formatado",
                "Diferenca_ft",
                "Status",
                "Situacao"
            ]],
            use_container_width=True
        )

        def to_excel(dataframe):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                dataframe.to_excel(writer, index=False, sheet_name="Validacao")
            return output.getvalue()

        excel_file = to_excel(
            df_filtrado[[
                "Filial",
                "NoTitulo",
                "FormaPgto",
                "CodBarras",
                "Valor_Total_Titulo",
                "Valor_CodBarras_Formatado",
                "Diferenca_ft",
                "Status",
                "Situacao"
            ]]
        )

        st.download_button(
            label="📥 Baixar Excel",
            data=excel_file,
            file_name="boletos_validacao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
