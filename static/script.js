
const chatMessages = document.getElementById("chat-messages");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-btn");
const newChatButton = document.getElementById("new-chat");
const typingIndicator = document.getElementById("typing-indicator");

let isSending = false;

// Menampilkan pesan ke area chat
function addMessage(text, sender) {
    const message = document.createElement("div");
    message.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = sender === "user" ? "K" : "AI";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    message.appendChild(avatar);
    message.appendChild(content);

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Mengirim pertanyaan ke backend
async function sendMessage() {
    const message = userInput.value.trim();

    if (!message || isSending) return;

    isSending = true;
    addMessage(message, "user");

    userInput.value = "";
    sendButton.disabled = true;

    if (typingIndicator) {
        typingIndicator.style.display = "block";
    }

    // Batas waktu menunggu respons 30 detik
    const controller = new AbortController();

    const timeout = setTimeout(() => {
        controller.abort();
    }, 30000);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            }),
            signal: controller.signal
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.response || "Gagal menghubungi server."
            );
        }

        addMessage(
            data.response || "Chatbot belum memberikan jawaban.",
            "bot"
        );

        console.log("Sumber jawaban:", data.source);
        console.log("Waktu proses:", data.processing_time);

    } catch (error) {
        console.error("Error:", error);

        if (error.name === "AbortError") {
            addMessage(
                "Maaf, chatbot membutuhkan waktu terlalu lama. Silakan coba kembali.",
                "bot"
            );
        } else {
            addMessage(
                "Maaf, terjadi kesalahan: " + error.message,
                "bot"
            );
        }

    } finally {
        clearTimeout(timeout);

        isSending = false;
        sendButton.disabled = false;

        if (typingIndicator) {
            typingIndicator.style.display = "none";
        }

        userInput.focus();
    }
}

// Klik tombol kirim
sendButton.addEventListener("click", sendMessage);

// Tekan Enter untuk mengirim
userInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// Percakapan baru
if (newChatButton) {
    newChatButton.addEventListener("click", function() {
        if (isSending) return;

        chatMessages.innerHTML = "";

        addMessage(
            "Halo! Saya Chatbot Jadwal Kuliah Informatika. Ada yang bisa saya bantu?",
            "bot"
        );
    });
}
