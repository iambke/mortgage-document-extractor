document.getElementById('uploadBtn').addEventListener('click', async () => {
  const fileInput = document.getElementById('fileInput');
  const status = document.getElementById('status');
  const result = document.getElementById('result');

  result.classList.add('hidden');
  status.textContent = '';

  if (!fileInput.files.length) {
    status.textContent = "Please upload a file.";
    return;
  }

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);

  status.textContent = "Extracting data...";

  try {
    const res = await fetch("/extract/", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      status.textContent = data.detail || "Extraction failed.";
      return;
    }

    document.getElementById('borrower').textContent = data.borrower_name;
    document.getElementById('loan').textContent = data.loan_amount;
    document.getElementById('address').textContent = data.property_address;

    result.classList.remove('hidden');
    status.textContent = "Extraction complete.";
  } catch (err) {
    status.textContent = "Error: " + err.message;
  }
});
