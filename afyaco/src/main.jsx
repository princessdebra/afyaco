import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './styles.css';
import Landing from './pages/Landing';
import Login from './pages/Login';
import PortalLayout from './components/PortalLayout';
import ProviderLayout from './components/ProviderLayout';
import RequireAuth from './components/RequireAuth';
import Dashboard from './pages/Dashboard';
import FindCare from './pages/FindCare';
import Appointments from './pages/Appointments';
import Consultations from './pages/Consultations';
import Prescriptions from './pages/Prescriptions';
import LabTests from './pages/LabTests';
import Claims from './pages/Claims';
import MyHealth from './pages/MyHealth';
import Dependants from './pages/Dependants';
import Support from './pages/Support';
import AppointmentDetail from './pages/AppointmentDetail';
import LabTestDetail from './pages/LabTestDetail';
import ClaimDetail from './pages/ClaimDetail';
import Enroll from './pages/Enroll';
import VerifyVisit from './pages/VerifyVisit';
import ProviderHospitalEncounter from './pages/provider/HospitalEncounter';
import ProviderAppointments from './pages/provider/Appointments';
import ProviderChat from './pages/provider/Chat';
import ProviderDashboard from './pages/provider/Dashboard';
import ProviderClaims from './pages/provider/Claims';
import ProviderVideoCall from './pages/provider/VideoCall';
import VideoCall from './pages/VideoCall';
import ChatConsultation from './pages/ChatConsultation';
import Notifications from './pages/Notifications';
import { FACILITY_ROLES, MEMBER_ROLES } from './constants/roles';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/portal" element={<RequireAuth roles={MEMBER_ROLES}><PortalLayout /></RequireAuth>}>
          <Route index element={<Dashboard />} />
          <Route path="find-care" element={<FindCare />} />
          <Route path="appointments" element={<Appointments />} />
          <Route path="appointments/:id" element={<AppointmentDetail />} />
          <Route path="consultations" element={<Consultations />} />
          <Route path="prescriptions" element={<Prescriptions />} />
          <Route path="lab-tests" element={<LabTests />} />
          <Route path="lab-tests/:id" element={<LabTestDetail />} />
          <Route path="claims" element={<Claims />} />
          <Route path="claims/:id" element={<ClaimDetail />} />
          <Route path="my-health" element={<MyHealth />} />
          <Route path="dependants" element={<Dependants />} />
          <Route path="support" element={<Support />} />
          <Route path="enroll" element={<Enroll />} />
          <Route path="verify-visit" element={<VerifyVisit />} />
          <Route path="call/:appointmentId" element={<VideoCall />} />
          <Route path="chat/:appointmentId" element={<ChatConsultation />} />
          <Route path="notifications" element={<Notifications />} />
        </Route>
        <Route path="/provider" element={<RequireAuth roles={FACILITY_ROLES}><ProviderLayout /></RequireAuth>}>
          <Route index element={<ProviderDashboard />} />
          <Route path="appointments" element={<ProviderAppointments />} />
          <Route path="claims" element={<ProviderClaims />} />
          <Route path="chat/:appointmentId" element={<ProviderChat />} />
          <Route path="call/:appointmentId" element={<ProviderVideoCall />} />
          <Route path="hospital/encounter" element={<ProviderHospitalEncounter />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="support" element={<Support />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
