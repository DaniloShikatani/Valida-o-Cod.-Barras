df = pd.read_excel(uploaded_file, dtype=str)

df.columns = df.columns.str.strip().str.lower()

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
    .astype(str)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)
df["Total"] = pd.to_numeric(df["Total"], errors="coerce")

def extrair_valor(codbarras, forma):
    try:
        codbarras = str(codbarras).strip()
        forma = str(forma).strip()

        if len(codbarras) < 44:
            return None

        if forma in ["30", "31"]:
            valor_centavos = int(codbarras[9:19])
        elif forma in ["19", "91", "11", "13"]:
            # revisar esse slice conforme sua regra real
            valor_centavos = int(codbarras[8:18])
        else:
            return None

        return valor_centavos / 100
    except:
        return None
