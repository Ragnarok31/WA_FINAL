import { useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("");  // User input message
  const [response, setResponse] = useState("");  // Response from backend
  const [sentMessage, setSentMessage] = useState("");  // Sent message from user

  const handleMessageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Show the message the user sent
    setSentMessage(message);

    // Make API call to your Flask backend
    const res = await fetch("https://3b58-115-242-248-226.ngrok-free.app/whatsapp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    // Check if the response is OK
    if (!res.ok) {
      console.error("Failed to fetch:", res.statusText);
      return;
    }

    
    const data = await res.json();

    // Set the response text 
    setResponse(data.reply);
  };

  return (
    <div>
      <h1>WhatsApp AI Bot</h1>
      <form onSubmit={handleMessageSubmit}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message"
        />
        <button type="submit">Send</button>
      </form>

      {}
      {sentMessage && (
        <div>
          <h3>Message Sent:</h3>
          <p>{sentMessage}</p>
        </div>
      )}

      {}
      {response && (
        <div>
          <h3>Response:</h3>
          <p>{response}</p>
        </div>
      )}
    </div>
  );
}
