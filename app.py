
import time

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Membaca konfigurasi .env terlebih dahulu
load_dotenv()

from chatbot.retrieval import retrieve_documents
from chatbot.llm import ask_openai, UNKNOWN_ANSWER

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    start_time = time.perf_counter()

    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({
                "response": "Silakan masukkan pertanyaan terlebih dahulu."
            }), 400

        # Tahap 1: Pencarian Knowledge Base
        retrieval_start = time.perf_counter()

        result = retrieve_documents(user_message)

        retrieval_time = time.perf_counter() - retrieval_start

        print(f"Waktu retrieval: {retrieval_time:.2f} detik")
        print(f"Mode pencarian: {result['mode']}")

        # Tahap 2: Jawaban langsung dari Knowledge Base
        if result["mode"] == "direct":
            answer = result["answer"]
            source = "knowledge_base"

        # Tahap 3: Mengirim konteks ke LLM
        elif result["mode"] == "context":
            llm_start = time.perf_counter()

            print("Mengirim pertanyaan ke LLM...")

            answer = ask_openai(
                user_message,
                result["contexts"]
            )

            llm_time = time.perf_counter() - llm_start

            print(f"Waktu LLM: {llm_time:.2f} detik")

            source = "llm_with_context"

        # Tahap 4: Informasi tidak ditemukan
        else:
            answer = UNKNOWN_ANSWER
            source = "no_context"

        total_time = time.perf_counter() - start_time

        print(f"Total waktu: {total_time:.2f} detik")

        return jsonify({
            "response": answer,
            "source": source,
            "score": round(result.get("score", 0), 3),
            "processing_time": round(total_time, 2)
        })

    except Exception as error:
        print("Terjadi kesalahan:", error)

        return jsonify({
            "response": (
                "Maaf, terjadi kesalahan pada chatbot. "
                "Silakan coba kembali."
            )
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
