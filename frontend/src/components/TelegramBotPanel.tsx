import { useState, useEffect } from "react";
import { startTelegramBot, stopTelegramBot, getTelegramBotStatus } from "../api";

export function TelegramBotPanel() {
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const { running: isRunning } = await getTelegramBotStatus();
      setRunning(isRunning);
    } catch {
      // API may not be available
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await startTelegramBot();
      if (result.status === "error") {
        setError(result.message || "Failed to start bot");
      } else {
        setRunning(true);
      }
    } catch (e) {
      setError("Failed to start bot");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError(null);
    try {
      await stopTelegramBot();
      setRunning(false);
    } catch {
      setError("Failed to stop bot");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="telegram-bot-panel">
      <h4>Telegram Bot</h4>
      <div className="telegram-bot-controls">
        <span className={`telegram-bot-status ${running ? "running" : "stopped"}`}>
          {running ? "Running" : "Stopped"}
        </span>
        {running ? (
          <button
            className="telegram-bot-btn stop"
            onClick={handleStop}
            disabled={loading}
          >
            {loading ? "Stopping..." : "Stop"}
          </button>
        ) : (
          <button
            className="telegram-bot-btn start"
            onClick={handleStart}
            disabled={loading}
          >
            {loading ? "Starting..." : "Start"}
          </button>
        )}
      </div>
      {error && <div style={{ color: "#e53e3e", fontSize: "0.75rem", marginTop: 4 }}>{error}</div>}
      <div className="telegram-bot-info">
        Send Facebook Marketplace links to your Telegram bot.
        Listings will be scraped and added with AI-extracted fields.
      </div>
    </div>
  );
}
