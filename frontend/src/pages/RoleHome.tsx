import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import CollegeDashboard from "./CollegeDashboard";
import CentralDashboard from "./CentralDashboard";
import ConsentPage from "./ConsentPage";

export default function RoleHome() {
  const { me } = useAuth();
  if (!me) return null;
  switch (me.user.role) {
    case "institution_operator":
    case "institution_admin":
      return <CollegeDashboard />;
    case "central_reviewer":
    case "sysadmin":
      return <CentralDashboard />;
    case "verifier":
    case "student":
      return <ConsentPage />;
    default:
      return <Navigate to="/login" replace />;
  }
}
