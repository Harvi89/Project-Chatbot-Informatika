
import json
import re
import random
from pathlib import Path

# Library untuk mengolah teks dan menghitung kemiripan dokumen
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ==========================================
# PENGATURAN PENCARIAN KNOWLEDGE BASE
# ==========================================

# Batas skor untuk menentukan jawaban langsung dari Knowledge Base
DIRECT_THRESHOLD = 0.45

# Skor minimal agar dokumen dapat digunakan sebagai konteks
MIN_CONTEXT_SCORE = 0.10

# Jumlah maksimal dokumen yang diambil sebagai konteks
TOP_K = 3


# ==========================================
# MENENTUKAN LOKASI FOLDER KNOWLEDGE BASE
# ==========================================

# Mengambil lokasi folder utama proyek
BASE_DIR = Path(__file__).resolve().parent.parent

# Menentukan lokasi folder data
DATA_DIR = BASE_DIR / "data"


# ==========================================
# DAFTAR EMPAT KNOWLEDGE BASE AWAL
# ==========================================

# Nama file JSON yang akan dibaca oleh chatbot
KB_FILES = [
    "kb_jadwal.json",
    "kb_akademik.json",
    "kb_kemahasiswaan.json",
    "kb_informasi_kampus.json",
    "kb_fakultas.json",
    "kb_dosen.json"
]


# ==========================================
# FUNGSI PREPROCESSING
# ==========================================

def preprocess(text):
    """
    Membersihkan teks sebelum proses pencarian.
    Mengubah huruf menjadi kecil dan menghapus tanda baca.
    """

    # Mengubah teks menjadi huruf kecil
    text = str(text).lower()

    # Menghapus karakter selain huruf, angka, dan spasi
    text = re.sub(r"[^\w\s]", " ", text)

    # Menghapus spasi berlebihan
    return re.sub(r"\s+", " ", text).strip()


# ==========================================
# MEMBACA KNOWLEDGE BASE
# ==========================================

def load_knowledge_base():
    """
    Membaca seluruh file Knowledge Base dari folder data.
    Data dari setiap file digabungkan menjadi satu kumpulan.
    """

    all_documents = []

    # Membaca setiap file JSON yang terdaftar
    for filename in KB_FILES:

        # Menggabungkan lokasi folder dengan nama file
        file_path = DATA_DIR / filename

        # Memastikan file Knowledge Base tersedia
        if not file_path.exists():
            raise FileNotFoundError(
                f"File Knowledge Base tidak ditemukan: {file_path}"
            )

        # Membuka dan membaca file JSON
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Mendukung format JSON yang menggunakan pembungkus knowledge_base
        if isinstance(data, dict) and "knowledge_base" in data:
            data = data["knowledge_base"]

        # Memproses JSON dengan format list
        if isinstance(data, list):

            for item in data:

                # Mengabaikan data yang bukan dictionary
                if not isinstance(item, dict):
                    continue

                # Mengambil daftar jawaban alternatif
                responses = item.get("responses", [])

                # Mengambil jawaban utama
                answer = item.get("answer", "")

                # Memilih jawaban alternatif jika jawaban utama kosong
                if not answer and responses:
                    answer = random.choice(responses)

                # Menyimpan informasi ke kumpulan dokumen
                all_documents.append({
                    "id": item.get("id", ""),
                    "category": item.get("category", ""),
                    "content": item.get("content", ""),
                    "patterns": item.get("patterns", []),
                    "answer": answer
                })

        # Mendukung format JSON lama berupa dictionary
        elif isinstance(data, dict):

            for intent, item in data.items():

                # Mengabaikan data yang bukan dictionary
                if not isinstance(item, dict):
                    continue

                responses = item.get("responses", [])
                answer = item.get("answer", "")

                # Memilih jawaban alternatif jika jawaban utama kosong
                if not answer and responses:
                    answer = random.choice(responses)

                # Mengubah data dictionary menjadi format dokumen
                all_documents.append({
                    "id": intent,
                    "category": intent,
                    "content": item.get("content", answer),
                    "patterns": item.get("patterns", []),
                    "answer": answer
                })

    # Mengembalikan seluruh data Knowledge Base
    return all_documents


# ==========================================
# MEMUAT KNOWLEDGE BASE SATU KALI
# ==========================================

# Membaca seluruh Knowledge Base saat modul pertama kali dijalankan
documents = load_knowledge_base()


# ==========================================
# MENYIAPKAN DATA UNTUK TF-IDF
# ==========================================

# Menyediakan tempat untuk menyimpan teks yang akan dicari
searchable_texts = []

# Mengolah setiap dokumen Knowledge Base
for document in documents:

    # Mengambil pola pertanyaan dari dokumen
    patterns = document.get("patterns", [])

    # Memastikan pola pertanyaan berbentuk list
    if not isinstance(patterns, list):
        patterns = []

    # Menggabungkan konten, jawaban, kategori, dan pola pertanyaan
    searchable = " ".join([
        str(document.get("content", "")),
        str(document.get("answer", "")),
        str(document.get("category", "")),
        *[str(pattern) for pattern in patterns]
    ])

    # Membersihkan teks sebelum disimpan
    searchable_texts.append(preprocess(searchable))


# ==========================================
# MEMBUAT MODEL TF-IDF SATU KALI
# ==========================================

# Membuat objek TF-IDF Vectorizer
vectorizer = TfidfVectorizer()

# Memastikan data Knowledge Base tidak kosong
if searchable_texts and any(searchable_texts):

    # Mengubah seluruh dokumen menjadi matriks TF-IDF
    tfidf_matrix = vectorizer.fit_transform(searchable_texts)

else:

    # Memberikan nilai kosong jika tidak ada data
    tfidf_matrix = None


# ==========================================
# FUNGSI PENCARIAN DOKUMEN
# ==========================================

def retrieve_documents(user_question):
    """
    Mencari informasi yang sesuai dengan pertanyaan pengguna.

    Mode pencarian:
    1. direct  : Memberikan jawaban langsung dari Knowledge Base.
    2. context : Mengambil Top-K dokumen untuk dikirim ke LLM.
    3. none    : Tidak menemukan informasi yang relevan.
    """

    # Membersihkan pertanyaan pengguna
    question = preprocess(user_question)

    # Memeriksa apakah pertanyaan dan Knowledge Base tersedia
    if not question or not documents or tfidf_matrix is None:
        return {
            "mode": "none",
            "answer": None,
            "contexts": []
        }

    try:

        # Mengubah pertanyaan menjadi vektor TF-IDF
        question_vector = vectorizer.transform([question])

        # Menghitung kemiripan pertanyaan dengan seluruh dokumen
        similarities = cosine_similarity(
            question_vector,
            tfidf_matrix
        ).flatten()

    except ValueError:

        # Mengembalikan mode none jika terjadi kesalahan pencarian
        return {
            "mode": "none",
            "answer": None,
            "contexts": []
        }

    # Mengurutkan dokumen berdasarkan skor tertinggi
    ranked_indices = similarities.argsort()[::-1]

    # Mengambil indeks dokumen dengan skor tertinggi
    best_index = int(ranked_indices[0])

    # Mengambil skor kemiripan tertinggi
    best_score = float(similarities[best_index])


    # ======================================
    # MODE 1: JAWABAN LANGSUNG
    # ======================================

    # Jika skor memenuhi batas, gunakan jawaban dari Knowledge Base
    if best_score >= DIRECT_THRESHOLD:

        # Mengambil jawaban dari dokumen paling relevan
        answer = documents[best_index].get("answer")

        # Memastikan jawaban tersedia
        if answer:
            return {
                "mode": "direct",
                "answer": answer,
                "score": best_score,
                "contexts": []
            }


    # ======================================
    # MODE 2: MENGAMBIL TOP-K KONTEKS
    # ======================================

    # Menyediakan tempat untuk menyimpan dokumen relevan
    contexts = []

    # Mengambil maksimal TOP_K dokumen dengan skor tertinggi
    for index in ranked_indices[:TOP_K]:

        # Mengambil skor kemiripan setiap dokumen
        score = float(similarities[index])

        # Mengabaikan dokumen dengan skor di bawah batas minimal
        if score < MIN_CONTEXT_SCORE:
            continue

        # Mengambil dokumen berdasarkan indeks
        document = documents[int(index)]

        # Menyimpan informasi sebagai konteks untuk LLM
        contexts.append({
            "id": document.get("id"),
            "category": document.get("category"),
            "content": document.get("content"),
            "answer": document.get("answer"),
            "score": score
        })


    # ======================================
    # MODE 3: INFORMASI TIDAK DITEMUKAN
    # ======================================

    # Jika tidak ada konteks relevan, kembalikan mode none
    if not contexts:
        return {
            "mode": "none",
            "answer": None,
            "contexts": []
        }

    # Mengembalikan konteks untuk diproses oleh LLM
    return {
        "mode": "context",
        "answer": None,
        "score": best_score,
        "contexts": contexts
    }
