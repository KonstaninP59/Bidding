import { useState } from "react";
import api from "../api/axios";

export default function CompareTable({ requestId }) {
  const [data, setData] = useState([]);

  const compare = async () => {
    const res = await api.get(
      `/requests/${requestId}/compare-rounds?round1_id=1&round2_id=2`
    );
    setData(res.data);
  };

  return (
    <div>
      <button onClick={compare}>Сравнить</button>

      <table>
        <thead>
          <tr>
            <th>Поставщик</th>
            <th>Раунд 1</th>
            <th>Раунд 2</th>
            <th>Экономия</th>
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.supplier_id}>
              <td>{row.supplier_id}</td>
              <td>{row.round1_total}</td>
              <td>{row.round2_total}</td>
              <td>{row.savings_abs} ({row.savings_pct}%)</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
