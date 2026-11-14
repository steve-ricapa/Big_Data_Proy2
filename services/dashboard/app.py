import os

import httpx
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Threat Intelligence", page_icon="🛡️", layout="wide")
st.title("Threat Intelligence · NIST NVD")
st.caption(
    "Vulnerabilidades publicadas, no ataques confirmados. Fuente local NVD; KPI con fecha de corte explícita."
)
base = os.getenv("API_URL", "http://127.0.0.1:18000")


@st.cache_data(ttl=30, show_spinner=False)
def get(path, **params):
    response = httpx.get(base + path, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


if st.sidebar.button("Actualizar datos"):
    st.cache_data.clear()
view = st.sidebar.radio(
    "Vista",
    [
        "Overview",
        "Vulnerability Explorer",
        "Threat Analytics",
        "Graph Intelligence",
        "Data Pipeline",
    ],
)


def ranking(title, values):
    st.subheader(title)
    st.dataframe(
        pd.DataFrame(values, columns=["Entidad", "CVE únicos"]),
        hide_index=True,
        width="stretch",
    )


try:
    if view in ("Overview", "Threat Analytics"):
        data = get("/api/v1/kpis")
        st.caption("Último cálculo: " + data["as_of"])
        if view == "Overview":
            cols = st.columns(4)
            cols[0].metric("CVE únicos", f"{data['total_cves']:,}")
            cols[1].metric("Críticos", f"{data['severity'].get('CRITICAL', 0):,}")
            cols[2].metric(
                "Modificados en 30 días", f"{data['modified_last_30_days']:,}"
            )
            cols[3].metric(
                "Productos identificables", f"{data['unique_affected_products']:,}"
            )
            st.subheader("CVSS promedio · versiones separadas")
            st.json(data["cvss_by_version"])
            st.subheader("Distribución por severidad")
            st.bar_chart(pd.Series(data["severity"], name="CVE"))
        else:
            cassandra = get("/api/v1/analytics/cassandra/snapshot")
            st.caption(
                "Snapshot consultado directamente en Cassandra: "
                + cassandra["snapshot"]["as_of"]
            )
            if cassandra["snapshot"]["as_of"] != data["as_of"]:
                st.warning("MongoDB y Cassandra tienen snapshots de distinta fecha; revisar el pipeline.")
            ranking("CWE más frecuentes", data["top_cwes"])
            ranking("Fabricantes", data["top_vendors"])
            ranking("Productos (parte / fabricante / producto)", data["top_products"])
        st.subheader("Publicaciones por mes")
        st.line_chart(pd.Series(data["monthly"], name="CVE"))
        if "graph" in data:
            st.json(data["graph"])
    elif view == "Vulnerability Explorer":
        with st.form("filters"):
            left, middle, right = st.columns(3)
            identifier = left.text_input("CVE exacto", placeholder="CVE-2024-0001")
            year = middle.selectbox("Año de publicación", ["Todos", 2024, 2025, 2026])
            severity = right.selectbox(
                "Severidad",
                ["Todas", "CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "UNKNOWN"],
            )
            cwe = left.text_input("CWE exacto", placeholder="CWE-79")
            start = middle.text_input("Publicado desde (AAAA-MM-DD)")
            end = right.text_input("Publicado hasta (AAAA-MM-DD)")
            page = left.number_input("Página", min_value=1, max_value=10000, value=1)
            st.form_submit_button("Buscar")
        filters = {"page": page}
        for key, value in (
            ("cve_id", identifier),
            ("year", year if year != "Todos" else None),
            ("severity", severity if severity != "Todas" else None),
            ("cwe", cwe),
            ("published_from", start),
            ("published_to", end),
        ):
            if value:
                filters[key] = value
        data = get("/api/v1/vulnerabilities", **filters)
        st.caption(f"{data['total']:,} resultados · 25 por página")
        st.dataframe(
            [
                {k: row[k] for k in ("cve_id", "published", "severity", "description")}
                for row in data["items"]
            ],
            hide_index=True,
        )
        chosen = st.selectbox("Detalle", [r["cve_id"] for r in data["items"]])
        if chosen:
            st.json(get("/api/v1/vulnerabilities/" + chosen), expanded=False)
    elif view == "Graph Intelligence":
        examples = get("/api/v1/vulnerabilities", page_size=1)["items"]
        identifier = st.text_input("CVE", examples[0]["cve_id"] if examples else "")
        if st.button("Explorar relaciones"):
            data = get("/api/v1/graph/cve/" + identifier)
            st.dataframe(data["items"], hide_index=True)
            # DOT escapes both quotes and backslashes; no raw HTML from source data.
            import json

            edges = []
            for item in data["items"]:
                entity = item["entity"] or {}
                target = entity.get("id", entity.get("url", "Sin relación"))
                edges.append(
                    f"{json.dumps(identifier)} -> {json.dumps(target)} [label={json.dumps(item['relationship'] or '')}];"
                )
            st.graphviz_chart("digraph { " + " ".join(edges) + " }")
            st.caption(
                "Subgrafo limitado a 250 relaciones salientes. AFFECTS indica asociación NVD, no explotación observada."
            )
    else:
        st.json(get("/api/v1/pipeline/status"))
        st.json(get("/ready"))
        st.caption(
            "Estado del manifiesto más reciente. IN_PROGRESS_OR_INTERRUPTED requiere comprobar tareas y logs; no implica que el proceso siga vivo."
        )
except httpx.HTTPStatusError as error:
    if error.response.status_code == 404:
        st.warning(
            "No se encontraron datos. Compruebe el CVE o ejecute el pipeline si faltan snapshots."
        )
    elif error.response.status_code == 422:
        st.warning("Filtros inválidos: revise formato de CVE, CWE y fechas.")
    else:
        st.error("El servicio devolvió un error. Compruebe API y motores.")
except (httpx.HTTPError, KeyError, ValueError) as error:
    st.error(
        "No se pudieron consultar los datos reales. Compruebe API, motores y ejecución del pipeline."
    )
    st.caption(type(error).__name__)
