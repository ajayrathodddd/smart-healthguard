
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function analyzeMedicineImage(imageFile) {
  const formData = new FormData();

  formData.append("file", imageFile);

  const response = await fetch(`${API_BASE_URL}/api/ocr/scan`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      `OCR analysis failed: ${response.status} ${errorText}`
    );
  }

  return await response.json();
}
