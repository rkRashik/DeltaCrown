function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `px-4 py-2 rounded shadow text-sm text-white ${
    type === "success" ? "bg-green-600" :
    type === "error" ? "bg-red-600" : "bg-gray-700"
  }`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
