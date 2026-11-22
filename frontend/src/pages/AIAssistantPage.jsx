
import { useEffect, useRef, useState } from "react";
import {
  Bot,
  Send,
  User,
  Sparkles,
  AlertCircle,
  LoaderCircle,
  Trash2,
} from "lucide-react";
import "./AIAssistantPage.css";

const API_URL = `${
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
}/api/ai-assistant/chat`;

function AIAssistantPage() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your Smart HealthGuard AI Assistant. You can ask me educational questions about medicines, ingredients, common warnings, and health products.",
    },
  ]);

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (event) => {
    event.preventDefault();

    const userQuestion = question.trim();

    if (!userQuestion || loading) return;

    setMessages((previous) => [
      ...previous,
      { role: "user", content: userQuestion },
    ]);

    setQuestion("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ question: userQuestion }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to get a response. Please try again."
        );
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer || "The assistant returned an empty response.",
        },
      ]);
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Cannot connect to the backend. Please make sure the FastAPI server is running."
          : err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="ai-assistant-page">
      <div className="ai-assistant-header">
        <div className="ai-assistant-heading">
          <div className="ai-assistant-icon">
            <Bot size={28} />
          </div>

          <div>
            <h2>HealthGuard AI Assistant</h2>
            <p>Educational medicine and health-product information</p>
          </div>
        </div>

        <span className="ai-online-status">
          <span className="ai-online-dot"></span>
          AI Connected
        </span>
      </div>

      <div className="ai-chat-container">
        <div className="ai-chat-welcome">
          <div className="ai-welcome-icon">
            <Sparkles size={25} />
          </div>
          <h3>How can I help you today?</h3>
          <p>
            Ask a question about medicine ingredients, common warnings,
            or general health-product information.
          </p>
        </div>

        <div className="ai-chat-messages">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`ai-message ${
                message.role === "user" ? "user-message" : "assistant-message"
              }`}
            >
              <div className="ai-message-avatar">
                {message.role === "user" ? (
                  <User size={19} />
                ) : (
                  <Bot size={19} />
                )}
              </div>

              <div className="ai-message-content">
                <strong>
                  {message.role === "user" ? "You" : "HealthGuard AI"}
                </strong>
                <p>{message.content}</p>
              </div>
            </div>
          ))}

          {loading && (
            <div className="ai-message assistant-message">
              <div className="ai-message-avatar">
                <Bot size={19} />
              </div>
              <div className="ai-message-content">
                <strong>HealthGuard AI</strong>
                <p className="ai-typing">
                  <LoaderCircle size={16} className="ai-spinner" />
                  Thinking...
                </p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="ai-error-message">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form className="ai-chat-input-area" onSubmit={handleSend}>
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask your medicine or health-product question..."
            disabled={loading}
            maxLength={2000}
          />

          <button
            type="submit"
            disabled={loading || !question.trim()}
            aria-label="Send message"
          >
            {loading ? (
              <LoaderCircle size={20} className="ai-spinner" />
            ) : (
              <Send size={20} />
            )}
            <span>Send</span>
          </button>
        </form>

        <div className="ai-disclaimer">
          <AlertCircle size={16} />
          <p>
            Educational information only. This assistant does not provide
            medical diagnosis, prescriptions, or personal treatment advice.
            Consult a qualified healthcare professional for medical decisions.
          </p>
        </div>
      </div>
    </section>
  );
}

export default AIAssistantPage;
