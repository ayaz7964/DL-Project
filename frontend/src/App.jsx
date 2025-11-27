import React, { useState, useLayoutEffect, useRef } from "react";
import { askBackend } from "./api";

// Helper function to render text with line breaks and clickable links
function renderTextWithBreaks(text) {
  // Use <br/> for \n characters
  const lines = text.split("\n").map((line, index) => {
    // Basic link detection for professional responses
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = line.split(urlRegex);

    return (
      <React.Fragment key={index}>
        {parts.map((part, partIndex) => {
          if (part.match(urlRegex)) {
            // Render as an external link
            return (
              <a
                key={partIndex}
                href={part}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {part}
              </a>
            );
          }
          return part;
        })}
        {index < text.split("\n").length - 1 && <br />}
      </React.Fragment>
    );
  });
  return lines;
}

// 📚 Enhanced Knowledge Base (KB)
const kb = [
  {
    triggers: ["admission", "admission date", "deadline", "apply"],
    reply:
      "Admissions are typically open until **July 31st**. For the exact schedule and application process, please visit our official admissions portal:\n\nhttps://siba.edu.pk/admissions-schedule",
  },
  {
    triggers: ["fee", "fees", "tuition", "cost"],
    reply:
      "The annual tuition for undergraduate programs is generally between **PKR 80,000–120,000**. \n\nWe recommend checking the detailed fee structure for your specific program on the university website: \nhttps://siba.edu.pk/fee-structure",
  },
  {
    triggers: ["courses", "programs", "departments"],
    reply:
      "Sukkur IBA University offers a variety of programs, including:\n\n* BBA (Business Administration)\n* BS Computer Science\n* BS Accounting & Finance\n* BS Economics\n* BE Electrical Engineering",
  },
  {
    triggers: ["scholarship", "financial aid", "aid"],
    reply:
      "We offer several **scholarship and financial aid** options to support our students, including need-based and merit-based programs. \n\nDetails can be found here: https://siba.edu.pk/scholarships-and-aid",
  },
  {
    triggers: ["hello", "hi", "hey", "greetings"],
    reply:
      "Hello! 👋 I'm the SIBA Student Assistant. I specialize in answering questions about **admissions, fees, programs, and scholarships**.",
  },
];

function getReply(msg) {
  const lower = msg.toLowerCase();
  for (const k of kb) {
    if (k.triggers.some((t) => lower.includes(t))) return k.reply;
  }
  // Enhanced professional fallback message
  return "I apologize, I currently only have information regarding **admissions, fees, programs, or scholarships**. Please rephrase your question or select one of these topics to get a specific answer.";
}

// 🤖 Professional Typing Indicator Component
const TypingIndicator = () => (
  <div className="flex items-center">
    <div className="flex-shrink-0 mr-3">
      <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-lg">
        <span className="text-2xl">🤖</span>
      </div>
    </div>
    <div className="bg-gray-100 px-4 py-2 rounded-2xl rounded-bl-none">
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '0s' }} />
        <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
        <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
      </div>
    </div>
  </div>
);

// 💬 Message Bubble Component
const ChatMessage = ({ m }) => (
  <div
    key={m.id}
    className={`flex items-end ${m.role === "user" ? "justify-end" : "justify-start"}`}
  >
    {m.role === "assistant" && (
      <div className="flex-shrink-0 mr-3">
        {/* Formal Assistant Avatar */}
        <div className="w-10 h-10 rounded-full bg-indigo-500 text-white flex items-center justify-center text-lg shadow-md">
          <span className="font-serif text-xl">S</span>
        </div>
      </div>
    )}

    <div className={`max-w-[80%]`}>
      <div
        className={`inline-block px-4 py-3 rounded-2xl break-words whitespace-pre-wrap ${
          m.role === "user"
            ? "bg-blue-600 text-white rounded-br-md shadow-md"
            : "bg-gray-100 text-gray-800 rounded-bl-md shadow-sm"
        }`}
        style={{ fontSize: 15, wordBreak: "break-word", lineHeight: "1.5" }}
      >
        {m.role === "user" ? m.text : renderTextWithBreaks(m.text)}
      </div>
      <div className={`text-xs text-gray-400 mt-1 ${m.role === "user" ? "text-right" : "text-left"}`}>
        {m.time}
      </div>
    </div>
  </div>
);

// 🚀 Main Component
export default function SibaChat() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      text: "Welcome to **Sukkur IBA University** 🎓\nI'm your dedicated Student Assistant, ready to help you with **admissions, fees, programs, and scholarships**.",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const feedRef = useRef(null);
  const taRef = useRef(null);

  // Auto-scroll to bottom on new message or typing indicator change
  useLayoutEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isTyping]);

  // Auto-expand textarea for a better typing experience
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (taRef.current) {
      taRef.current.style.height = "auto";
      taRef.current.style.height = Math.min(taRef.current.scrollHeight, 100) + "px"; // Limit to 100px
    }
  };

 const send = async () => {
  const text = input.trim();
  if (!text || isTyping) return;

  const userMsg = {
    id: Date.now(),
    role: "user",
    text,
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };

  setMessages((m) => [...m, userMsg]);
  setInput("");
  if (taRef.current) taRef.current.style.height = "auto";

  setIsTyping(true);

  // 🔥 Ask backend instead of local KB
  const reply = await askBackend(text);

  const botMsg = {
    id: Date.now() + 1,
    role: "assistant",
    text: reply,
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };

  setMessages((m) => [...m, botMsg]);
  setIsTyping(false);
};

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Fixed Header: Cleaner, more professional look */}
      <header className="fixed top-0 left-0 w-full bg-white border-b shadow-lg py-4 px-6 z-10">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          {/* Formal University Logo Placeholder */}
          <div className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center font-serif text-xl shadow-md">
            S
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">SIBA Student Assistant</h1>
            <p className="text-sm text-gray-500">Official Helpdesk Bot</p>
          </div>
        </div>
      </header>

      {/* Scrollable Chat Area */}
      <main
        ref={feedRef}
        className="flex-1 overflow-y-auto px-4 md:px-8 py-6 mt-20 mb-28 w-full flex justify-center"
      >
        <div className="w-full max-w-4xl space-y-6 pt-4 pb-2">
          {messages.map((m) => (
            <ChatMessage key={m.id} m={m} />
          ))}

          {isTyping && <TypingIndicator />}
        </div>
      </main>

      {/* Fixed Input Footer: Cleaner, centered, professional */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4 px-4 md:px-8 z-10">
        <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
            <textarea
                ref={taRef}
                rows={1}
                placeholder="Ask about admissions, fees, programs, or scholarships..."
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKey}
                disabled={isTyping} // Disable input while bot is typing
                className="flex-1 resize-none rounded-xl border-2 border-gray-200 p-3 text-base focus:ring-2 focus:ring-indigo-300 focus:border-indigo-500 focus:outline-none transition"
                style={{ maxHeight: 100 }}
            />
            <button
                onClick={send}
                disabled={!input.trim() || isTyping}
                className="flex-shrink-0 w-12 h-12 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center disabled:opacity-50 transition shadow-lg"
            >
                {/* Send Icon: Rotated for a modern look */}
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M12 19l9-7-9-7-9 7 9 7z"
                        className="transform rotate-90"
                    />
                </svg>
            </button>
            </div>
            <div className="text-xs text-gray-400 mt-2 flex justify-between">
                <span>
                    Press <b>Enter</b> to send &nbsp;|&nbsp; <b>Shift+Enter</b> for new line
                </span>
                <span>Powered by Sukkur IBA</span>
            </div>
        </div>
      </footer>
    </div>
  );
}