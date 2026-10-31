import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import { RequireAuth } from "./lib/auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import RoleHome from "./pages/RoleHome";
import CollegeDashboard from "./pages/CollegeDashboard";
import CentralDashboard from "./pages/CentralDashboard";
import UploadWizard from "./pages/UploadWizard";
import FindingsPage from "./pages/FindingsPage";
import FindingDetail from "./pages/FindingDetail";
import DuplicatesPage from "./pages/DuplicatesPage";
import AnomaliesPage from "./pages/AnomaliesPage";
import InstitutionsPage from "./pages/InstitutionsPage";
import CredentialsPage from "./pages/CredentialsPage";
import AuditPage from "./pages/AuditPage";
import VerifyPage from "./pages/VerifyPage";
import ConsentPage from "./pages/ConsentPage";
import EnrolmentsPage from "./pages/EnrolmentsPage";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/verify/:credentialId" element={<VerifyPage />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<RoleHome />} />
        <Route
          path="college"
          element={
            <RequireAuth roles={["institution_operator", "institution_admin"]}>
              <CollegeDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="central"
          element={
            <RequireAuth roles={["central_reviewer", "sysadmin"]}>
              <CentralDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="upload"
          element={
            <RequireAuth roles={["institution_operator", "institution_admin"]}>
              <UploadWizard />
            </RequireAuth>
          }
        />
        <Route path="findings" element={<FindingsPage />} />
        <Route path="findings/:findingId" element={<FindingDetail />} />
        <Route path="duplicates" element={<DuplicatesPage />} />
        <Route
          path="anomalies"
          element={
            <RequireAuth roles={["central_reviewer", "sysadmin"]}>
              <AnomaliesPage />
            </RequireAuth>
          }
        />
        <Route
          path="institutions"
          element={
            <RequireAuth roles={["central_reviewer", "sysadmin"]}>
              <InstitutionsPage />
            </RequireAuth>
          }
        />
        <Route path="credentials" element={<CredentialsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="consent" element={<ConsentPage />} />
        <Route path="enrolments" element={<EnrolmentsPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export function LandingRedirect() {
  return <Navigate to="/" replace />;
}
