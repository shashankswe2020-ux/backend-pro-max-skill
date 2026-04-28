import express from "express";

const app = express();

app.post("/api/orders", (req, res) => {
  // BPM-L008: POST without idempotency key
  console.log("creating order"); // BPM-L012: console.log
  const query = "SELECT * FROM orders WHERE user_id = " + req.body.userId; // BPM-L009, BPM-L016
  res.json({ ok: true });
});

async function fetchData() {
  const result = await fetch("/api").then((r) => r.json()); // BPM-L018: .then without .catch
  return result;
}

// Should NOT trigger BPM-L012 (console.error is fine)
console.error("startup error");
