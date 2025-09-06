// src/components/SavingsCounter.tsx
import React, { useEffect, useState } from "react";
import { fileService } from "../services/fileService";

export default function SavingsCounter() {
  const [savings, setSavings] = useState(0);
  const [loading, setLoading] = useState(true);

  async function loadSavings() {
    try {
      const data = await fileService.getSavings();
      setSavings(data.total_saved_bytes);
    } catch (err) {
      console.error("Error fetching savings:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSavings();

    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      loadSavings();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  function formatBytes(bytes: number) {
    if (bytes === 0) return "0 Bytes";
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  }

  return (
    <div className="p-4 rounded-2xl shadow bg-green-50 text-green-700 flex items-center justify-between">
      <div>
        <p className="text-xl font-bold">💾 Storage Saved</p>
        <p className="text-2xl">
          {loading ? "Loading..." : formatBytes(savings)}
        </p>
      </div>
      <button
        onClick={loadSavings}
        className="ml-4 px-3 py-1 rounded-xl bg-green-600 text-white hover:bg-green-700 transition"
      >
        Refresh
      </button>
    </div>
  );
}
