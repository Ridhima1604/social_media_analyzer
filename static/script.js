analyzeBtn.addEventListener("click", async () => {
  const text = contentInput.value.trim();
  const file = pdfFileInput.files[0];

  let response;

  try {
    if (file) {
      // Case 1: PDF Upload
      const formData = new FormData();
      formData.append("file", file);
      response = await fetch("/analyze", {
        method: "POST",
        body: formData
      });

    } else if (text.length > 0) {
      // Case 2: Text input (JSON request)
      response = await fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // ✅ added the simpler JSON payload here
        body: JSON.stringify({ text: text })
      });
    } else {
      alert("Please enter some text or upload a PDF.");
      return;
    }

    const data = await response.json();
    if (response.ok) {
      renderResults(data);
    } else {
      alert(data.error || "Error analyzing text");
    }

  } catch (err) {
    console.error("Error:", err);
    alert("Something went wrong!");
  }
});
