import React, { useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";

export default function PublicOfferPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [prices, setPrices] = useState({});
  const [files, setFiles] = useState([]);

  useEffect(() => {
    axios.get(`/api/public/offer/${token}`)
      .then(res => setData(res.data))
      .catch(() => alert("Invalid or expired link"));
  }, [token]);

  if (!data) return <div>Loading...</div>;

  const handleSubmit = async () => {
    const formData = new FormData();

    formData.append("payment_terms", "");
    formData.append("comment", "");

    Object.entries(prices).forEach(([key, value]) => {
      formData.append(`price_${key}`, value);
    });

    files.forEach(file => formData.append("files", file));

    await axios.post(`/api/public/offer/${token}`, formData, {
      headers: { "Content-Type": "multipart/form-data" }
    });

    alert("Предложение отправлено");
  };

  return (
    <div>
      <h2>{data.request_number}</h2>
      <p>Deadline: {new Date(data.deadline).toLocaleString()}</p>

      <table>
        <thead>
          <tr>
            <th>Позиция</th>
            <th>Количество</th>
            <th>Цена</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map(item => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td>{item.quantity}</td>
              <td>
                <input
                  type="number"
                  onChange={(e) =>
                    setPrices({...prices, [item.id]: e.target.value})
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.previous_offer && (
        <div>
          <h4>Предыдущее предложение</h4>
          <pre>{JSON.stringify(data.previous_offer, null, 2)}</pre>
        </div>
      )}

      <input type="file" multiple onChange={e => setFiles([...e.target.files])} />

      <button onClick={handleSubmit}>Отправить</button>
    </div>
  );
}
