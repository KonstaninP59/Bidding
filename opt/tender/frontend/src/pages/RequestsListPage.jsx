import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import api from "../api/axios";
import { setRequests } from "../features/requests/requestSlice";
import { Link } from "react-router-dom";

export default function RequestsListPage() {
  const dispatch = useDispatch();
  const requests = useSelector((state) => state.requests.list);

  useEffect(() => {
    api.get("/requests")
      .then(res => dispatch(setRequests(res.data)));
  }, []);

  return (
    <div>
      <h2>Заявки</h2>
      <Link to="/requests/new">Создать заявку</Link>
      <table>
        <thead>
          <tr>
            <th>№</th>
            <th>Предмет</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {requests.map(r => (
            <tr key={r.id}>
              <td>
                <Link to={`/requests/${r.id}`}>
                  {r.request_number}
                </Link>
              </td>
              <td>{r.subject}</td>
              <td>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
