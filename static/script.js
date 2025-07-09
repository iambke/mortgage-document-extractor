const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
let droppedFile = null;

['dragenter', 'dragover'].forEach(event => {
  dropZone.addEventListener(event, e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(event => {
  dropZone.addEventListener(event, e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  });
});

dropZone.addEventListener('drop', e => {
  const files = e.dataTransfer.files;
  if (files.length) {
    droppedFile = files[0];
    fileInput.files = files; // sync with file input for fallback
  }
});

document.getElementById('uploadBtn').addEventListener('click', async () => {
  const status = document.getElementById('status');
  const result = document.getElementById('result');

  result.classList.add('hidden');
  status.textContent = '';
  status.className = 'status';

  const file = droppedFile || fileInput.files[0];
  if (!file) {
    status.textContent = "Please upload a file.";
    status.classList.add('error');
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  status.textContent = "Extracting data...";
  status.classList.remove('error', 'success');

  try {
    const res = await fetch("/extract/", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      status.textContent = data.detail || "Extraction failed.";
      status.classList.add('error');
      return;
    }

    document.getElementById('borrower').textContent = data.borrower_name;
    document.getElementById('loan').textContent = data.loan_amount;
    document.getElementById('address').textContent = data.property_address;

    result.classList.remove('hidden');
    status.textContent = "Extraction complete.";
    status.classList.add('success');

    fileInput.value = "";
    droppedFile = null;

    setTimeout(() => {
      result.scrollIntoView({ behavior: "smooth" });
    }, 200);
  } catch (err) {
    status.textContent = "Error: " + err.message;
    status.classList.add('error');
  }
});
