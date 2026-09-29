import { useState } from "react";
import DashboardPage from "./pages/DashboardPage";
import LocationsPage from "./pages/LocationsPage";
import ImportsPage from "./pages/ImportsPage";
import CloudPage from "./pages/CloudPage";
import ManualsPage from "./pages/ManualsPage";
import VisitsPage from "./pages/VisitsPage";
import AssetsPage from "./pages/AssetsPage";
import AlertsPage from "./pages/AlertsPage";
import ChatPage from "./pages/ChatPage";
import StockPage from "./pages/StockPage";
import WorkOrdersPage from "./pages/WorkOrdersPage";
import SettingsPage from "./pages/SettingsPage";
import DevicesPage from "./pages/DevicesPage";

type Tab =
  | "dashboard"
  | "locations"
  | "visits"
  | "assets"
  | "alerts"
  | "chat"
  | "workorders"
  | "stock"
  | "imports"
  | "cloud"
  | "manuals"
  | "devices"
  | "settings";

const TABS: { id: Tab; label: string }[] = [
  { id: "dashboard", label: "لوحة المتابعة" },
  { id: "locations", label: "شجرة المواقع" },
  { id: "visits", label: "الزيارات" },
  { id: "assets", label: "الأصول" },
  { id: "alerts", label: "التنبيهات" },
  { id: "chat", label: "المساعد الذكي" },
  { id: "workorders", label: "أوامر العمل" },
  { id: "stock", label: "المخزون" },
  { id: "imports", label: "الحزم المستوردة" },
  { id: "cloud", label: "المزامنة السحابية" },
  { id: "manuals", label: "المانوالات" },
  { id: "devices", label: "الأجهزة" },
  { id: "settings", label: "الإعدادات" },
];

function LogoMark() {
  return (
    <svg width="30" height="30" viewBox="0 0 108 108" aria-hidden="true">
      <path d="M54,33 L77.5,73 L30.5,73 Z" fill="#FFFFFF" />
      <path d="M51.5,43.5 L43.5,64.5" stroke="#D2262C" strokeWidth="4.4" strokeLinecap="round" />
      <path d="M56.5,43.5 L64.5,64.5" stroke="#D2262C" strokeWidth="4.4" strokeLinecap="round" />
      <path d="M46.5,57 L61.5,57" stroke="#D2262C" strokeWidth="4.4" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <LogoMark />
          </div>
          <div>
            <div className="brand-title">AccTracker</div>
            <div className="brand-sub">لوحة المهندس — نظام متابعة المواقع والصيانة الميدانية</div>
          </div>
          <div className="header-spacer" />
          <div className="header-badge">Advanced Construction Co.</div>
        </div>
      </header>

      <nav className="nav">
        <div className="nav-inner">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? "active" : ""}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="main">
        {tab === "dashboard" && <DashboardPage />}
        {tab === "locations" && <LocationsPage />}
        {tab === "visits" && <VisitsPage />}
        {tab === "assets" && <AssetsPage />}
        {tab === "alerts" && <AlertsPage />}
        {tab === "chat" && <ChatPage />}
        {tab === "workorders" && <WorkOrdersPage />}
        {tab === "stock" && <StockPage />}
        {tab === "imports" && <ImportsPage />}
        {tab === "cloud" && <CloudPage />}
        {tab === "manuals" && <ManualsPage />}
        {tab === "devices" && <DevicesPage />}
        {tab === "settings" && <SettingsPage />}
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <span>© 2026 Advanced Construction Co. — AccTracker</span>
          <span className="sig">By Ahmed Ismail</span>
        </div>
      </footer>
    </div>
  );
}
