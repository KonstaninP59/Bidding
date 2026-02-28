import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import api from "../api/axios";
import CompareTable from "../components/CompareTable";
import CreateRoundModal from "../components/CreateRoundModal";

export default function RequestDetailPage() {
  const { id } = useParams();
  const [request, setRequest] = useState(null);
  const [activeTab, setActiveTab] = useState("details");

  useEffect(() => {
    api.get(`/requests/${id}`)
      .then(res => setRequest(res.data));
  }, [id]);

  if (!request) return <div>Loading...</div>;

  return (
    <div>
      <h2>{request.subject}</h2>

      <button onClick={() => setActiveTab("details")}>Детали</button>
      <button onClick={() => setActiveTab("rounds")}>Раунды</button>
      <button onClick={() => setActiveTab("offers")}>Предложения</button>

      {activeTab === "details" && (
        <div>
          <h4>Спецификация</h4>
          <table>
            <tbody>
              {request.items.map(i => (
                <tr key={i.id}>
                  <td>{i.name}</td>
                  <td>{i.quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "rounds" && (
        <CreateRoundModal requestId={id} />
      )}

      {activeTab === "offers" && (
        <CompareTable requestId={id} />
      )}
    </div>
  );
}
