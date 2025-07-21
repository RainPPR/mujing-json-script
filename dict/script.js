document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");
    const wordContainer = document.getElementById("word-container");
    const uploadSection = document.getElementById("upload-section");
    const wordListTitle = document.getElementById("word-list-title");

    const progressIndicator = document.getElementById("progress-indicator");
    const jumpInput = document.getElementById("jump-to-word");
    const fontScaler = document.getElementById("font-scaler");
    const root = document.documentElement;
    let wordsData = [];
    let wordCards = [];

    fileInput.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (data && data.wordList) {
                    wordsData = data.wordList;
                    wordListTitle.textContent = data.name || "单词列表";
                    wordListTitle.style.display = "block";
                    renderWords();
                    uploadSection.style.display = "none";
                } else {
                    alert('JSON 文件格式不正确，缺少 "wordList" 键。');
                }
            } catch (error) {
                alert(
                    "解析 JSON 文件失败，请检查文件内容是否为有效的 JSON 格式。"
                );
                console.error(error);
            }
        };
        reader.readAsText(file);
    });

    function convertToParagraphs(text) {
        const lines = text.split("\n");
        const paragraphs = lines
            .filter((line) => line.trim() !== "")
            .map((line) => `<p>${line}</p>`)
            .join("");
        return paragraphs;
    }

    function renderWords() {
        wordContainer.innerHTML = "";
        wordsData.forEach((word, index) => {
            const card = document.createElement("div");
            card.className = "word-card";
            card.id = `word-${index}`;
            const trans = convertToParagraphs(word.translation);

            card.innerHTML = `
                        <div class="word-value">${word.value}</div>
                        <div class="phonetics">
                            <div class="phonetic-block" data-word="${
                                word.value
                            }" data-type="0">
                                <span class="speaker-icon">🔊</span>
                                <span class="phone">美: ${
                                    word.usphone || "N/A"
                                }</span>
                            </div>
                            <div class="phonetic-block" data-word="${
                                word.value
                            }" data-type="1">
                                <span class="speaker-icon">🔊</span>
                                <span class="phone">英: ${
                                    word.ukphone || "N/A"
                                }</span>
                            </div>
                        </div>
                        <div class="translation">${trans || "无释义"}</div>
                        <div class="frequency">
                            <span>BNC: ${word.bnc || "N/A"}</span> | 
                            <span>FRQ: ${word.frq || "N/A"}</span>
                        </div>
                    `;
            wordContainer.appendChild(card);
        });
        wordCards = Array.from(document.querySelectorAll(".word-card"));
        updateStatus(1, wordsData.length);
        jumpInput.max = wordsData.length;
        setupIntersectionObserver();
    }

    wordContainer.addEventListener("click", (event) => {
        const phoneticBlock = event.target.closest(".phonetic-block");
        if (phoneticBlock) {
            const word = phoneticBlock.dataset.word;
            const type = phoneticBlock.dataset.type; // 0 for US, 1 for UK
            if (word) {
                playAudio(word, type);
            }
        }
    });

    function playAudio(word, type) {
        const baseUrl = "https://dict.youdao.com/dictvoice";
        const audioUrl = `${baseUrl}?&audio=${encodeURIComponent(
            word
        )}&type=${type}`;
        const audio = new Audio(audioUrl);
        audio.play().catch((e) => console.error("音频播放失败:", e));
    }

    fontScaler.addEventListener("input", (e) => {
        root.style.setProperty("--base-font-size", `${e.target.value}px`);
    });

    jumpInput.addEventListener("change", (e) => {
        const index = parseInt(e.target.value, 10) - 1;
        if (index >= 0 && index < wordCards.length) {
            wordCards[index].scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }
    });
    function updateStatus(current, total) {
        progressIndicator.textContent = `${current} / ${total}`;
        if (total > 0 && jumpInput.valueAsNumber !== current) {
            jumpInput.value = current;
        }
    }

    let observer;

    // 需要修改滚动策略，不精准
    function setupIntersectionObserver() {
        if (observer) {
            observer.disconnect();
        }
        const options = {
            root: null,
            rootMargin: "0px",
            threshold: 0.5 // 元素 50% 可见时触发
        };
        observer = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const cardIndex = wordCards.indexOf(entry.target);
                    if (cardIndex !== -1) {
                        updateStatus(cardIndex + 1, wordsData.length);
                    }
                }
            });
        }, options);
        wordCards.forEach((card) => observer.observe(card));
    }
});
