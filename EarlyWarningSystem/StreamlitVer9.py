import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import sqlite3
import uuid

from PreprocessingVer3 import (
    extract_dkn_file,
    preprocess_dataframe,
    build_indikator,
    apply_fuzzy
)

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Dashboard Early Warning Akademik",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

.block-container{
    padding-top:1rem;
    padding-bottom:2rem;
}

.metric-card{
    background:#111827;
    padding:20px;
    border-radius:18px;
    color:white;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE
# =========================================================

DB = "sdum.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

# =========================================================
# KOLOM YANG DITAMPILKAN (tanpa user_id, jumlah_data_nilai,
# jumlah_mapel_nilai_rendah)
# =========================================================

DISPLAY_COLS = [
    "nama_siswa",
    "kelas",
    "rata_rata_nilai",
    "nilai_min",
    "delta_nilai",
    "tren_nilai",
    "skor_risiko_fuzzy",
    "kategori_risiko_fuzzy",
    "makna_lapangan",
    "alasan_risiko",
    "rekomendasi_tindakan",
    "mapel_catatan",
]

# =========================================================
# INIT DB
# =========================================================

def init_db():

    c = conn()
    cur = c.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # NILAI DATA
    cur.execute("""
    CREATE TABLE IF NOT EXISTS nilai_data(
        user_id INTEGER,
        nama_siswa TEXT,
        nama_key TEXT,
        kelas TEXT,
        tahun_ajaran TEXT,
        semester TEXT,
        mata_pelajaran TEXT,
        jenis_nilai TEXT,
        nilai REAL,
        siswa_id TEXT,
        source_file TEXT
    )
    """)

    # HASIL DATA
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hasil_data(
        user_id INTEGER,
        siswa_id TEXT,
        nama_siswa TEXT,
        kelas TEXT,
        rata_rata_nilai REAL,
        nilai_min REAL,
        delta_nilai REAL,
        tren_nilai TEXT,
        skor_risiko_fuzzy REAL,
        kategori_risiko_fuzzy TEXT,
        makna_lapangan TEXT,
        alasan_risiko TEXT,
        rekomendasi_tindakan TEXT,
        mapel_catatan TEXT
    )
    """)

    c.commit()
    c.close()

init_db()

# =========================================================
# HELPER
# =========================================================

def format_number(x):

    try:
        return f"{float(x):.2f}"

    except:
        return "-"


def get_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Kembalikan df hanya dengan kolom yang perlu ditampilkan."""
    cols = [c for c in DISPLAY_COLS if c in df.columns]
    return df[cols]

# =========================================================
# DETAIL SISWA
# =========================================================

def display_student_detail(df: pd.DataFrame):

    if df.empty or "nama_siswa" not in df.columns:
        return

    st.subheader("👤 Detail Siswa")

    options = (
        df.assign(
            label=
            df["nama_siswa"].astype(str)
            + " — "
            + df["kelas"].astype(str)
        )["label"].tolist()
    )

    selected_label = st.selectbox(
        "Pilih siswa untuk melihat detail",
        options
    )

    selected_row = df[
        (
            df["nama_siswa"].astype(str)
            + " — "
            + df["kelas"].astype(str)
        ) == selected_label
    ].head(1)

    if selected_row.empty:
        return

    row = selected_row.iloc[0]

    with st.expander(
        "Lihat detail alasan risiko dan rekomendasi",
        expanded=True
    ):

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Kategori",
            row.get(
                "kategori_risiko_fuzzy",
                "-"
            )
        )

        c2.metric(
            "Skor Risiko",
            format_number(
                row.get(
                    "skor_risiko_fuzzy",
                    "-"
                )
            )
        )

        c3.metric(
            "Rata-rata",
            format_number(
                row.get(
                    "rata_rata_nilai",
                    "-"
                )
            )
        )

        c4.metric(
            "Nilai Minimum",
            format_number(
                row.get(
                    "nilai_min",
                    "-"
                )
            )
        )

        st.markdown(
            f"**Nama:** {row.get('nama_siswa', '-')}"
        )

        st.markdown(
            f"**Kelas:** {row.get('kelas', '-')}"
        )

        st.markdown(
            f"**Tren nilai:** {row.get('tren_nilai', '-')}"
        )

        st.markdown(
            f"**Alasan risiko:** {row.get('alasan_risiko', '-')}"
        )

        st.markdown(
            f"**Rekomendasi tindakan:** "
            f"{row.get('rekomendasi_tindakan', '-')}"
        )

        if str(
            row.get(
                "mapel_catatan",
                ""
            )
        ).strip():

            st.markdown(
                f"**Catatan mata pelajaran:** "
                f"{row.get('mapel_catatan', '-')}"
            )

# =========================================================
# LOAD USER DATA
# =========================================================

def load_user_data(user_id):

    c = conn()

    try:

        nilai_df = pd.read_sql_query(
            f"""
            SELECT * FROM nilai_data
            WHERE user_id={user_id}
            """,
            c
        )

    except:
        nilai_df = pd.DataFrame()

    try:

        hasil_df = pd.read_sql_query(
            f"""
            SELECT * FROM hasil_data
            WHERE user_id={user_id}
            """,
            c
        )

    except:
        hasil_df = pd.DataFrame()

    c.close()

    return nilai_df, hasil_df

# =========================================================
# SAVE USER DATA
# =========================================================

def save_user_data(user_id, nilai_df, hasil_df):

    c = conn()
    cur = c.cursor()

    cur.execute(
        "DELETE FROM nilai_data WHERE user_id=?",
        (user_id,)
    )

    cur.execute(
        "DELETE FROM hasil_data WHERE user_id=?",
        (user_id,)
    )

    if not nilai_df.empty:

        save_nilai = nilai_df.copy()
        save_nilai["user_id"] = user_id

        save_nilai.to_sql(
            "nilai_data",
            c,
            if_exists="append",
            index=False
        )

    if not hasil_df.empty:

        save_hasil = hasil_df.copy()
        save_hasil["user_id"] = user_id

        # Simpan hanya kolom yang ada di schema DB
        db_cols = [
            "user_id", "siswa_id", "nama_siswa", "kelas",
            "rata_rata_nilai", "nilai_min",
            "delta_nilai", "tren_nilai",
            "skor_risiko_fuzzy", "kategori_risiko_fuzzy",
            "makna_lapangan", "alasan_risiko",
            "rekomendasi_tindakan", "mapel_catatan"
        ]

        save_cols = [c2 for c2 in db_cols if c2 in save_hasil.columns]

        save_hasil[save_cols].to_sql(
            "hasil_data",
            c,
            if_exists="append",
            index=False
        )

    c.commit()
    c.close()

# =========================================================
# AUTH
# =========================================================

def auth_page():

    st.title("Login")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:

        username = st.text_input(
            "Username",
            key="login_user"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_pass"
        )

        if st.button("Login"):

            c = conn()
            cur = c.cursor()

            cur.execute(
                "SELECT id FROM users WHERE username=? AND password=?",
                (username, password)
            )

            user = cur.fetchone()

            c.close()

            if user:

                st.session_state.login = True
                st.session_state.user_id = user[0]
                st.session_state.sid = str(uuid.uuid4())

                nilai_df, hasil_df = load_user_data(user[0])

                st.session_state.nilai_df = nilai_df
                st.session_state.hasil_df = hasil_df

                st.success("Login berhasil")
                st.rerun()

            else:

                st.error("Login gagal")

    with tab2:

        new_user = st.text_input(
            "Username baru",
            key="reg_user"
        )

        new_pass = st.text_input(
            "Password baru",
            type="password",
            key="reg_pass"
        )

        if st.button("Buat Akun"):

            try:

                c = conn()
                cur = c.cursor()

                cur.execute(
                    "INSERT INTO users(username,password) VALUES(?,?)",
                    (new_user, new_pass)
                )

                c.commit()
                c.close()

                st.success("Akun berhasil dibuat")

            except:

                st.error("Username sudah dipakai")

# =========================================================
# SESSION
# =========================================================

if "login" not in st.session_state:
    st.session_state.login = False

if "hasil_df" not in st.session_state:
    st.session_state.hasil_df = pd.DataFrame()

if "nilai_df" not in st.session_state:
    st.session_state.nilai_df = pd.DataFrame()

if not st.session_state.login:
    auth_page()
    st.stop()

# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div style="
background:linear-gradient(135deg,#0f172a,#1d4ed8);
padding:30px;
border-radius:24px;
margin-bottom:24px;
">

<h1 style="color:white;">
Dashboard Monitoring Akademik
</h1>

<p style="color:#dbeafe;">
Sistem Early Warning berbasis Fuzzy Logic
</p>

</div>
""", unsafe_allow_html=True)

# =========================================================
# LOGOUT
# =========================================================

c1, c2, c3 = st.columns([6,1,1])

with c3:

    if st.button("🚪 Logout"):

        st.session_state.login = False
        st.rerun()

# =========================================================
# MENU
# =========================================================

menu = option_menu(
    None,
    ["Dashboard", "Upload"],
    icons=["bar-chart", "upload"],
    orientation="horizontal"
)

# =========================================================
# UPLOAD
# =========================================================

if menu == "Upload":

    st.subheader("📤 Upload File DKN")

    uploaded_files = st.file_uploader(
        "Upload file DKN",
        type=["xls", "xlsx"],
        accept_multiple_files=True
    )

    if uploaded_files:

        all_df = []

        progress = st.progress(0)

        for i, f in enumerate(uploaded_files):

            try:

                df = extract_dkn_file(f)

                df["source_file"] = f.name

                df = preprocess_dataframe(df)

                all_df.append(df)

                st.success(f"{f.name} berhasil diproses")

            except Exception as e:

                st.error(f"{f.name} gagal")
                st.exception(e)

            progress.progress((i + 1) / len(uploaded_files))

        if len(all_df) > 0:

            nilai_df = pd.concat(
                all_df,
                ignore_index=True
            )

            nilai_df = nilai_df.drop_duplicates()

            nilai_df["siswa_id"] = (
                nilai_df["nama_key"]
                + "_"
                + nilai_df["kelas"]
            )

            indikator_df = build_indikator(nilai_df)

            hasil_df = apply_fuzzy(
                indikator_df,
                nilai_df
            )

            st.session_state.nilai_df = nilai_df
            st.session_state.hasil_df = hasil_df

            save_user_data(
                st.session_state.user_id,
                nilai_df,
                hasil_df
            )

            st.success("Semua file selesai diproses 🚀")

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    hasil_df = st.session_state.hasil_df

    nilai_df = st.session_state.nilai_df

    if hasil_df.empty:

        st.warning("Belum ada data upload")
        st.stop()

    total_siswa = len(hasil_df)

    total_sedang = len(
        hasil_df[
            hasil_df["kategori_risiko_fuzzy"] == "Sedang"
        ]
    )

    total_tinggi = len(
        hasil_df[
            hasil_df["kategori_risiko_fuzzy"] == "Tinggi"
        ]
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Total Siswa", total_siswa)

    with c2:
        st.metric("Risiko Sedang", total_sedang)

    with c3:
        st.metric("Risiko Tinggi", total_tinggi)

    st.divider()

    f1, f2 = st.columns(2)

    with f1:

        kelas_list = sorted(
            hasil_df["kelas"].dropna().unique()
        )

        selected_kelas = st.selectbox(
            "Filter Kelas",
            ["Semua"] + kelas_list
        )

    with f2:

        selected_risk = st.multiselect(
            "Filter Risiko",
            ["Rendah", "Sedang", "Tinggi"],
            default=["Rendah", "Sedang", "Tinggi"]
        )

    filtered_df = hasil_df.copy()

    if selected_kelas != "Semua":

        filtered_df = filtered_df[
            filtered_df["kelas"] == selected_kelas
        ]

    filtered_df = filtered_df[
        filtered_df["kategori_risiko_fuzzy"].isin(selected_risk)
    ]

    st.subheader("⚠️ Prioritas Monitoring")

    prioritas_df = filtered_df[
        filtered_df["kategori_risiko_fuzzy"].isin(
            ["Sedang", "Tinggi"]
        )
    ]

    st.dataframe(
        get_display_df(prioritas_df),
        use_container_width=True
    )

    st.subheader("📄 Semua Data")

    selected_rows = st.dataframe(
        get_display_df(filtered_df),
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row"
    )

    # =====================================================
    # HAPUS DATA TERPILIH
    # =====================================================

    selected_index = selected_rows["selection"]["rows"]

    if len(selected_index) > 0:

        st.warning(
            f"{len(selected_index)} data dipilih"
        )

        if st.button("🗑️ Hapus Data Terpilih"):

            selected_df = filtered_df.iloc[
                selected_index
            ]

            selected_ids = selected_df[
                "siswa_id"
            ].tolist()

            st.session_state.hasil_df = (
                st.session_state.hasil_df[
                    ~st.session_state.hasil_df[
                        "siswa_id"
                    ].isin(selected_ids)
                ]
            )

            st.session_state.nilai_df = (
                st.session_state.nilai_df[
                    ~st.session_state.nilai_df[
                        "siswa_id"
                    ].isin(selected_ids)
                ]
            )

            save_user_data(
                st.session_state.user_id,
                st.session_state.nilai_df,
                st.session_state.hasil_df
            )

            st.success("Data berhasil dihapus")

            st.rerun()


    display_student_detail(filtered_df)

    csv = get_display_df(filtered_df).to_csv(index=False)

    st.download_button(
        "⬇️ Download CSV",
        csv,
        file_name="hasil_fuzzy.csv",
        mime="text/csv"
    )

    st.divider()

    st.subheader("📊 Visualisasi")

    a1, a2 = st.columns(2)

    with a1:

        pie = (
            filtered_df[
                "kategori_risiko_fuzzy"
            ]
            .value_counts()
            .reset_index()
        )

        pie.columns = [
            "Kategori",
            "Jumlah"
        ]

        fig1 = px.pie(
            pie,
            names="Kategori",
            values="Jumlah",
            title="Distribusi Risiko"
        )

        st.plotly_chart(
            fig1,
            use_container_width=True
        )

    with a2:

        avg = filtered_df.groupby(
            "kelas"
        )["rata_rata_nilai"].mean().reset_index()

        fig2 = px.bar(
            avg,
            x="kelas",
            y="rata_rata_nilai",
            title="Rata-rata Nilai per Kelas"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    b1, b2 = st.columns(2)

    with b1:

        fig3 = px.histogram(
            filtered_df,
            x="rata_rata_nilai",
            nbins=20,
            title="Distribusi Nilai"
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )

    with b2:

        fig4 = px.box(
            filtered_df,
            x="kelas",
            y="rata_rata_nilai",
            color="kelas",
            title="Sebaran Nilai per Kelas"
        )

        st.plotly_chart(
            fig4,
            use_container_width=True
        )

    c1, c2 = st.columns(2)

    with c1:

        fig5 = px.scatter(
            filtered_df,
            x="nilai_min",
            y="rata_rata_nilai",
            color="kategori_risiko_fuzzy",
            hover_data=["nama_siswa"],
            title="Scatter Risiko"
        )

        st.plotly_chart(
            fig5,
            use_container_width=True
        )

    with c2:

        fig6 = px.treemap(
            filtered_df,
            path=["kelas", "kategori_risiko_fuzzy"],
            title="Treemap Risiko"
        )

        st.plotly_chart(
            fig6,
            use_container_width=True
        )

    # =====================================================
    # HAPUS DATA PER FILE
    # =====================================================

    st.divider()

    st.subheader("🗂️ Hapus Data Berdasarkan File")

    if "source_file" in nilai_df.columns:

        file_list = sorted(
            nilai_df["source_file"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_file = st.selectbox(
            "Pilih file yang ingin dihapus",
            ["-"] + file_list
        )

        if selected_file != "-":

            total_file_data = len(
                nilai_df[
                    nilai_df["source_file"]
                    == selected_file
                ]
            )

            st.info(
                f"Jumlah data pada file ini: {total_file_data}"
            )

            if st.button("❌ Hapus Semua Data File"):

                new_nilai_df = (
                    st.session_state.nilai_df[
                        st.session_state.nilai_df[
                            "source_file"
                        ] != selected_file
                    ]
                )

                if not new_nilai_df.empty:

                    indikator_df = build_indikator(
                        new_nilai_df
                    )

                    new_hasil_df = apply_fuzzy(
                        indikator_df,
                        new_nilai_df
                    )

                else:

                    new_hasil_df = pd.DataFrame()

                st.session_state.nilai_df = new_nilai_df
                st.session_state.hasil_df = new_hasil_df

                save_user_data(
                    st.session_state.user_id,
                    st.session_state.nilai_df,
                    st.session_state.hasil_df
                )

                st.success(
                    f"Semua data dari file {selected_file} berhasil dihapus"
                )

                st.rerun()
