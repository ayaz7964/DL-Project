import axios from "axios";

const API_URL = "http://127.0.0.1:8000";  // change to your backend URL after deploy

export async function askBackend(query) {
  try {
    const res = await axios.post(`${API_URL}/ask`, { query });
    return res.data.answer; // backend returns { answer: "..." }
  } catch (err) {
    console.error("API Error:", err);
    return "❌ Server error. Please try again.";
  }
}
