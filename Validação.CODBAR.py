import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Validador de Boletos", layout="wide")

st.title("🔎 Validador de Boletos - Linha Digitável x Valor Total")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload do arquivo Excel", type=["xlsx", "xls"])

if uploaded_file:

    # 🔹 Ler tudo como texto (evita bugs de Excel)
    df = pd.read_excel(uploaded_file, dtype=str)

    # 🔹 Normaliza colunas
    df.columns = df.columns.str.strip().str.lower()

    # 🔹 Validação de colunas
    colunas_obrigatorias = ["cod.barras", "total", "forma pgto.", "filial", "no. titulo", "situacao"]
    faltando = [col for col in colunas_obrigatorias if col not in df.columns]

    if faltando:
        st.error(f"O arquivo deve conter as colunas: {', '.join(faltando)}")
        st.stop()

    # 🔹 Renomear
    df = df.rename(columns={
        "cod.barras": "CodBarras",
        "total": "Total",
        "forma pgto.": "FormaPgto",
        "filial": "Filial",
        "no. titulo": "NoTitulo",
        "situacao": "Situacao"
    })

    # =========================
    # 🔥 CORREÇÃO DO CODBARRAS
    # =========================
    df["CodBarras"] = (
        df["CodBarras"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(44)
    )

    # =========================
    # 🔥 CORREÇÃO DO TOTAL
    # =========================
    def converter_total(valor):
        try:
            if pd.isna(valor):
                return None

            valor = str(valor).strip()

            if valor == "":
                return None

            # padrão BR
            if "," in valor:
                valor = valor.replace(".", "").replace(",", ".")
            # padrão US já correto
            else:
                valor = valor

            return float(valor)
        except:
            return None

    df["Total"] = df["Total"].apply(converter_total)

    # =========================
    # 🔹 Normalizações extras
    # =========================
    df["FormaPgto"] = df["FormaPgto"].fillna("").astype(str).str.strip()
    df["Situacao"] = df["Situacao"].fillna("").astype(str)

    # 🔹 Filtra títulos não baixados
    df = df[df["Situacao"].str.strip().str.lower() != "titulo baixado"]

    # =========================
    # 🔥 EXTRAÇÃO DO VALOR
    # =========================
    def extrair_valor(codbarras, forma):
        try:
            codbarras = str(codbarras)

            if len(codbarras) < 44:
                return None

            # padrão boleto bancário
            if forma in ["30", "31"]:
                valor_centavos = int(codbarras[9:19])
            elif forma in ["19", "91", "11", "13"]:
                valor_centavos = int(codbarras[9:19])
            else:
                return None

            return valor_centavos / 100

        except:
            return None

    df["Valor_CodBarras"] = df.apply(
        lambda x: extrair_valor(x["CodBarras"], x["FormaPgto"]),
        axis=1
    )

    # =========================
    # 🔹 Cálculo diferença
    # =========================
    df["Diferenca"] = df["Total"] - df["Valor_CodBarras"]

    df["Status"] = df.apply(
        lambda x: "OK"
        if pd.notnull(x["Valor_CodBarras"]) and round(x["Total"], 2) == round(x["Valor_CodBarras"], 2)
        else "Divergente",
        axis=1
    )

    # 🔹 Filtro formas válidas
    formas_validas = ["30", "31", "19", "91", "11", "13"]
    df = df[df["FormaPgto"].isin(formas_validas)]

    # =========================
    # 🔹 Formatação BR
    # =========================
    def formatar_real(x):
        if pd.isnull(x):
            return ""
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    df["Valor_Total_Titulo"] = df["Total"].apply(formatar_real)
    df["Valor_CodBarras_Formatado"] = df["Valor_CodBarras"].apply(formatar_real)
    df["Diferenca_ft"] = df["Diferenca"].apply(formatar_real)

    # =========================
    # 🔹 Filtros tela
    # =========================
    filtro = st.radio("Filtrar resultados:", ["Todos", "Somente Divergentes", "Somente OK"])

    if filtro == "Somente Divergentes":
        df_filtrado = df[df["Status"] == "Divergente"]
    elif filtro == "Somente OK":
        df_filtrado = df[df["Status"] == "OK"]
    else:
        df_filtrado = df.copy()

    # =========================
    # 🔹 Exibição
    # =========================
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

    # =========================
    # 🔹 Download Excel
    # =========================
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
