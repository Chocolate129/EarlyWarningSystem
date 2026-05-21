import pandas as pd
import numpy as np
import re
from pathlib import Path

# =========================================================
# CLEANING
# =========================================================

def clean_text(x):

    if pd.isna(x):
        return ""

    x = str(x).strip()

    x = re.sub(r"\s+", " ", x)

    return x


def clean_name(x):

    x = clean_text(x)

    x = x.upper()

    x = re.sub(r"\s+", " ", x)

    return x


def make_nama_key(x):

    x = clean_name(x)

    x = re.sub(r"[^A-Z0-9 ]", "", x)

    x = re.sub(r"\s+", " ", x).strip()

    return x


def normalize_kelas(x):

    x = clean_text(x).upper()

    x = x.replace(" ", "")

    m = re.search(r"([789])([A-Z])", x)

    return f"{m.group(1)}{m.group(2)}" if m else x


# =========================================================
# FILE PARSER
# =========================================================

def parse_kelas_from_filename(path):

    name = Path(getattr(path, "name", str(path))).name.upper()

    m = re.search(
        r"DKN_\d{4}_\d{4}_([789])_([A-Z])",
        name
    )

    if m:
        return f"{m.group(1)}{m.group(2)}"

    return ""


def parse_tahun_ajaran_from_filename(path):

    name = Path(getattr(path, "name", str(path))).name

    m = re.search(r"(\d{4})_(\d{4})", name)

    if m:
        return f"{m.group(1)}/{m.group(2)}"

    return "2025/2026"


# =========================================================
# MAPEL
# =========================================================

def standardize_mapel(mapel):

    m = clean_text(mapel)

    low = m.lower()

    if (
        "jasmani" in low
        or "olahraga" in low
        or "olah raga" in low
        or low in ["pjok", "penjas"]
    ):
        return "PJOK"

    if low in ["ipa", "ilmu pengetahuan alam"]:
        return "IPA"

    if low in ["ips", "ilmu pengetahuan sosial"]:
        return "IPS"

    if "pancasila" in low or low in ["pkn", "ppkn"]:
        return "Pendidikan Pancasila"

    if "agama" in low and "budi" in low:
        return "Pendidikan Agama dan Budi Pekerti"

    if "bahasa indonesia" in low:
        return "Bahasa Indonesia"

    if "bahasa inggris" in low:
        return "Bahasa Inggris"

    if "bahasa jawa" in low:
        return "Bahasa Jawa"

    if "matematika" in low:
        return "Matematika"

    if "seni" in low:
        return "Seni Budaya"

    if "informatika" in low:
        return "Informatika"

    if "prakarya" in low:
        return "Prakarya"

    return m


# =========================================================
# SEMESTER
# =========================================================

SEMESTER_ORDER = {
    "Ganjil": 1,
    "Genap": 2,
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6
}


def semester_order(semester):

    return SEMESTER_ORDER.get(str(semester), 99)


# =========================================================
# READ DKN
# =========================================================

def read_dkn_main_table(file):

    tables = pd.read_html(file)

    main = max(
        tables,
        key=lambda t: t.shape[0] * t.shape[1]
    )

    return main


# =========================================================
# EXTRACT DKN 7/8
# =========================================================

def extract_dkn_78(df, file):

    kelas = parse_kelas_from_filename(file)

    tahun_ajaran = parse_tahun_ajaran_from_filename(file)

    records = []

    cols = list(df.columns)

    for _, row in df.iterrows():

        nama = clean_name(
            row.get(("Nama", "Nama"), "")
        )

        if not nama or nama == "NAN":
            continue

        semester = clean_text(
            row.get(("Semester", "Semester"), "")
        )

        jenis_nilai = clean_text(
            row.get(("Aspek", "Aspek"), "Nilai Akhir")
        )

        for col in cols:

            if not isinstance(col, tuple):
                continue

            top, bottom = col

            if bottom in [
                "No",
                "Nama",
                "Semester",
                "Aspek"
            ]:
                continue

            mapel = standardize_mapel(bottom)

            nilai = pd.to_numeric(
                row[col],
                errors="coerce"
            )

            if (
                pd.notna(nilai)
                and 0 < float(nilai) <= 100
            ):

                records.append({

                    "nama_siswa": nama,
                    "nama_key": make_nama_key(nama),
                    "kelas": kelas,
                    "tahun_ajaran": tahun_ajaran,
                    "semester": semester,
                    "mata_pelajaran": mapel,
                    "jenis_nilai": jenis_nilai,
                    "nilai": float(nilai)

                })

    return pd.DataFrame(records)


# =========================================================
# EXTRACT DKN 9
# =========================================================

def extract_dkn_9(df, file):

    kelas = parse_kelas_from_filename(file)

    tahun_ajaran = parse_tahun_ajaran_from_filename(file)

    records = []

    cols = list(df.columns)

    semester_cols = [
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI"
    ]

    for _, row in df.iterrows():

        nama = clean_name(
            row.get(("Nama", "Nama"), "")
        )

        if not nama or nama == "NAN":
            continue

        for col in cols:

            if not isinstance(col, tuple):
                continue

            mapel, semester = col

            mapel = clean_text(mapel)

            semester = clean_text(semester)

            if semester not in semester_cols:
                continue

            if mapel in [
                "No",
                "NISN",
                "NIS",
                "Nama",
                "Tempat Lahir",
                "Tanggal Lahir",
                "Nama Orang Tua"
            ]:
                continue

            nilai = pd.to_numeric(
                row[col],
                errors="coerce"
            )

            if (
                pd.notna(nilai)
                and 0 < float(nilai) <= 100
            ):

                records.append({

                    "nama_siswa": nama,
                    "nama_key": make_nama_key(nama),
                    "kelas": kelas,
                    "tahun_ajaran": tahun_ajaran,
                    "semester": semester,
                    "mata_pelajaran": standardize_mapel(mapel),
                    "jenis_nilai": "Nilai Akhir",
                    "nilai": float(nilai)

                })

    return pd.DataFrame(records)


# =========================================================
# AUTO EXTRACT
# =========================================================

def extract_dkn_file(file):

    df_main = read_dkn_main_table(file)

    flat_cols = [str(c) for c in df_main.columns]

    if any("Semester" in c for c in flat_cols):

        return extract_dkn_78(df_main, file)

    return extract_dkn_9(df_main, file)


# =========================================================
# PREPROCESS
# =========================================================

def preprocess_dataframe(df):

    if df.empty:
        return df

    df["nama_siswa"] = df["nama_siswa"].apply(clean_name)

    df["nama_key"] = df["nama_siswa"].apply(make_nama_key)

    df["kelas"] = df["kelas"].apply(normalize_kelas)

    df["mata_pelajaran"] = df["mata_pelajaran"].apply(
        standardize_mapel
    )

    df["nilai"] = pd.to_numeric(
        df["nilai"],
        errors="coerce"
    )

    # HAPUS NILAI 0
    df = df[
        df["nilai"].notna()
        & (df["nilai"] > 0)
        & (df["nilai"] <= 100)
    ].copy()

    return df


# =========================================================
# BUILD INDIKATOR
# =========================================================

def build_indikator(nilai_df):

    nilai_df = nilai_df.copy()

    nilai_df["semester_order"] = nilai_df[
        "semester"
    ].apply(semester_order)

    nilai_df["siswa_id"] = (
        nilai_df["nama_key"]
        + "_"
        + nilai_df["kelas"]
    )

    agg = nilai_df.groupby(
        ["siswa_id", "nama_siswa", "kelas"],
        as_index=False
    ).agg(

        rata_rata_nilai=("nilai", "mean"),

        nilai_min=("nilai", "min"),

    )

    # =========================
    # DELTA NILAI
    # =========================

    sem_avg = nilai_df.groupby(
        ["siswa_id", "semester", "semester_order"],
        as_index=False
    )["nilai"].mean()

    delta_rows = []

    for sid, g in sem_avg.groupby("siswa_id"):

        g = g.sort_values("semester_order")

        if len(g) >= 2:

            delta = float(
                g.iloc[-1]["nilai"]
                - g.iloc[-2]["nilai"]
            )

            if delta <= -3:
                tren = "Turun"

            elif delta >= 3:
                tren = "Naik"

            else:
                tren = "Stabil"

        else:

            delta = np.nan

            tren = "Belum cukup data"

        delta_rows.append({

            "siswa_id": sid,
            "delta_nilai": delta,
            "tren_nilai": tren

        })

    delta_df = pd.DataFrame(delta_rows)

    agg = agg.merge(
        delta_df,
        on="siswa_id",
        how="left"
    )

    agg["rata_rata_nilai"] = agg[
        "rata_rata_nilai"
    ].round(2)

    agg["nilai_min"] = agg[
        "nilai_min"
    ].round(2)

    agg["delta_nilai"] = agg[
        "delta_nilai"
    ].round(2)

    return agg


# =========================================================
# MAPEL CATATAN
# =========================================================

def get_mapel_catatan(
    nilai_df,
    siswa_id,
    batas=80,
    max_items=5
):

    sub = nilai_df[
        (nilai_df["siswa_id"] == siswa_id)
        & (nilai_df["nilai"] < batas)
    ].copy()

    if sub.empty:
        return ""

    sub = sub.sort_values("nilai").head(max_items)

    return "; ".join([

        f"{r['mata_pelajaran']} {r['semester']} ({int(r['nilai']) if float(r['nilai']).is_integer() else r['nilai']})"

        for _, r in sub.iterrows()

    ])


# =========================================================
# REKOMENDASI TINDAKAN
# =========================================================

def get_rekomendasi(row):

    kategori = row.get("kategori_risiko_fuzzy", "")

    rata = float(row.get("rata_rata_nilai", 0))

    nilai_min = float(row.get("nilai_min", 0))

    tren = row.get("tren_nilai", "")

    mapel_catatan = str(row.get("mapel_catatan", "")).strip()

    if kategori == "Tinggi":

        if nilai_min < 30:
            return (
                "Lakukan konsultasi segera dengan orang tua/wali; "
                "koordinasi dengan guru BK untuk pendampingan intensif; "
                "pertimbangkan program remedial khusus"
            )

        rekomendasi = [
            "Pantau perkembangan nilai secara mingguan",
            "Lakukan bimbingan belajar tambahan"
        ]

        if mapel_catatan:
            rekomendasi.append(
                f"Fokus perbaikan pada: {mapel_catatan}"
            )

        if tren == "Turun":
            rekomendasi.append(
                "Segera konsultasikan dengan orang tua karena tren nilai menurun"
            )

        return "; ".join(rekomendasi)

    elif kategori == "Sedang":

        rekomendasi = []

        if tren == "Turun":
            rekomendasi.append(
                "Pantau tren nilai — terjadi penurunan signifikan"
            )

        if rata < 80:
            rekomendasi.append(
                "Dorong siswa untuk aktif bertanya dan mengikuti remedial jika tersedia"
            )

        if mapel_catatan:
            rekomendasi.append(
                f"Perhatikan mata pelajaran: {mapel_catatan}"
            )

        if not rekomendasi:
            rekomendasi.append(
                "Lakukan pemantauan berkala dan motivasi siswa untuk mempertahankan nilai"
            )

        return "; ".join(rekomendasi)

    else:

        return (
            "Pertahankan prestasi; "
            "lakukan monitoring rutin setiap akhir semester"
        )


# =========================================================
# FUZZY
# =========================================================

def fuzzy_score_row(row):

    rata = float(
        row.get("rata_rata_nilai", 0)
    )

    nilai_min = float(
        row.get("nilai_min", 0)
    )

    delta = row.get(
        "delta_nilai",
        np.nan
    )

    alasan = []

    # =====================================================
    # RISIKO TINGGI
    # =====================================================

    if nilai_min < 75:

        skor = (
            90
            if nilai_min < 30
            else 74 + (75 - nilai_min) * 0.4
        )

        kategori = "Tinggi"

        makna = "Prioritas intervensi akademik"

        alasan.append(
            "nilai minimum di bawah 75"
        )

    # =====================================================
    # RISIKO SEDANG
    # =====================================================

    elif (
        (rata < 86)
        or (75 <= nilai_min < 80)
        or (
            pd.notna(delta)
            and delta <= -3
        )
    ):

        skor = 50

        kategori = "Sedang"

        makna = "Pantauan wali kelas"

        if rata < 86:

            skor += min(
                10,
                (86 - rata) * 2
            )

            alasan.append(
                "rata-rata nilai di bawah 86"
            )

        if 75 <= nilai_min < 80:

            skor += min(
                15,
                (80 - nilai_min) * 3
            )

            alasan.append(
                "nilai minimum mendekati batas rendah"
            )

        if (
            pd.notna(delta)
            and delta <= -3
        ):

            skor += min(
                15,
                abs(delta) * 2
            )

            alasan.append(
                "tren nilai turun signifikan"
            )

        skor = min(skor, 69)

    # =====================================================
    # RISIKO RENDAH
    # =====================================================

    else:

        skor = 0

        kategori = "Rendah"

        makna = "Monitoring rutin"

        alasan.append(
            "nilai akademik masih berada pada rentang aman"
        )

    return pd.Series({

        "skor_risiko_fuzzy": round(
            float(skor),
            2
        ),

        "kategori_risiko_fuzzy": kategori,

        "makna_lapangan": makna,

        "alasan_risiko": "; ".join(alasan)

    })


# =========================================================
# APPLY FUZZY
# =========================================================

def apply_fuzzy(indikator_df, nilai_df):

    hasil = indikator_df.copy()

    fuzzy_cols = hasil.apply(
        fuzzy_score_row,
        axis=1
    )

    hasil = pd.concat(
        [hasil, fuzzy_cols],
        axis=1
    )

    hasil["mapel_catatan"] = hasil[
        "siswa_id"
    ].apply(

        lambda sid: get_mapel_catatan(
            nilai_df,
            sid,
            batas=80
        )

    )

    hasil["alasan_risiko"] = hasil.apply(

        lambda r:
        r["alasan_risiko"]
        + (
            "; mapel catatan: "
            + r["mapel_catatan"]

            if r["mapel_catatan"]
            else ""
        ),

        axis=1
    )

    # REKOMENDASI TINDAKAN — diisi setelah mapel_catatan tersedia
    hasil["rekomendasi_tindakan"] = hasil.apply(
        get_rekomendasi,
        axis=1
    )

    rank = {
        "Tinggi": 3,
        "Sedang": 2,
        "Rendah": 1
    }

    hasil["rank"] = hasil[
        "kategori_risiko_fuzzy"
    ].map(rank)

    hasil = hasil.sort_values(

        [
            "rank",
            "skor_risiko_fuzzy",
            "nilai_min"
        ],

        ascending=[
            False,
            False,
            True
        ]

    )

    hasil = hasil.drop(
        columns=["rank"]
    ).reset_index(drop=True)

    return hasil