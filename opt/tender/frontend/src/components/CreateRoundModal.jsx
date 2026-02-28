import { useState } from "react";
import api from "../api/axios";

export default function CreateRoundModal({ requestId }) {
  const [deadline, setDeadline] = useState("");

  const createRound = async () => {
    await api.post(`/requests/${requestId}/rounds`, {
      deadline,
      supplier_ids: []
    });
    alert("Раунд создан");
  };

  return (
    <div>
      <h4>Создать раунд</h4>
      <input
        type="datetime-local"
        onChange={e => setDeadline(e.target.value)}
      />
      <button onClick={createRound}>Создать</button>
    </div>
  );
}
