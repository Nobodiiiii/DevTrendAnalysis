import { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("正在向后端请求数据...");
  const [error, setError] = useState("");

  useEffect(() => {
    // 这里的 URL 对应你 FastAPI 的接口，比如 /api/hello
    fetch("http://127.0.0.1:8000/api/hello")
      .then((res) => {
        if (!res.ok) {
          throw new Error("HTTP error " + res.status);
        }
        return res.json();
      })
      .then((data) => {
        // 假设后端返回 {"message": "..."}
        setMessage(data.message || JSON.stringify(data));
      })
      .catch((err) => {
        console.error(err);
        setError("请求失败，请检查后端是否启动以及接口路径是否正确。");
      });
  }, []);

  return (
    <div style={{ fontFamily: "sans-serif", padding: "24px" }}>
      <h1>DevTrendAnalysis 前端</h1>
      <p>下面这一行是从 FastAPI 拿到的数据：</p>

      <div
        style={{
          marginTop: "12px",
          padding: "12px 16px",
          borderRadius: "8px",
          border: "1px solid #ddd",
          display: "inline-block",
          minWidth: "280px",
        }}
      >
        {error ? <span style={{ color: "red" }}>{error}</span> : message}
      </div>
    </div>
  );
}

export default App;
