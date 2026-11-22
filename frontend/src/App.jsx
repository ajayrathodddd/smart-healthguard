import { useEffect, useState } from "react";
import {
  Activity,
  LayoutDashboard,
  Pill,
  ScanLine,
  ShieldCheck,
  Mic,
  Bot,
  History,
  Menu,
  ChevronLeft,
  Upload,
  ImagePlus,
  Clock3,
  FileText,
  AlertTriangle,
  LogOut,
  ArrowUpRight,
} from "lucide-react";

import "./App.css";
import Auth from "./Auth";
import { auth, onAuthStateChanged, signOut } from "./firebase";

import MedicineAnalyzerPage from "./pages/MedicineAnalyzerPage";
import OCRScannerPage from "./pages/OCRScannerPage";
import RiskDetectionPage from "./pages/RiskDetectionPage";
import AIAssistantPage from "./pages/AIAssistantPage";
import InformationVoicePage from "./voice/InformationVoicePage";
import AnalysisHistoryPage from "./pages/AnalysisHistoryPage";

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // CHECK FIREBASE LOGIN STATUS
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      if (currentUser && currentUser.emailVerified) {
        setUser(currentUser);
      } else {
        setUser(null);
      }

      setAuthLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // LOGOUT
  const handleLogout = async () => {
    try {
      await signOut(auth);
      setActivePage("Dashboard");
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  const navigation = [
    {
      title: "MAIN MENU",
      items: [
        { name: "Dashboard", icon: LayoutDashboard },
        { name: "Medicine Analyzer", icon: Pill },
        { name: "OCR Scanner", icon: ScanLine },
        { name: "Risk Detection", icon: ShieldCheck },
      ],
    },
    {
      title: "AI FEATURES",
      items: [
        { name: "Information Voice", icon: Mic },
        { name: "AI Assistant", icon: Bot },
        { name: "Analysis History", icon: History },
      ],
    },
  ];

  const handleQuickAction = (page) => {
    setActivePage(page);

    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };
  const getPageDescription = () => {
    const descriptions = {
      Dashboard: "Your smart medicine information dashboard",
      "Medicine Analyzer": "Explore educational medicine information",
      "OCR Scanner": "Scan medicine packages and extract text",
      "Risk Detection": "Explore medicine safety information",
      "Information Voice": "Access medicine information using voice",
      "AI Assistant": "Ask questions about medicine information",
      "Analysis History": "Review your previous analyses",
    };

    return descriptions[activePage] || "Smart HealthGuard";
  };

  // SHOW LOADING WHILE FIREBASE CHECKS LOGIN
  if (authLoading) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-logo">
            <Activity size={28} />
          </div>
          <h2>Smart HealthGuard</h2>
          <p className="auth-subtitle">Checking your account...</p>
        </div>
      </div>
    );
  }

  // SHOW LOGIN WHEN USER IS NOT AUTHENTICATED
  if (!user) {
    return <Auth />;
  }

  // MAIN APPLICATION
  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <aside className={`sidebar ${sidebarOpen ? "" : "closed"}`}>
        <div className="sidebar-header">
          <div className="logo-box">
            <Activity size={25} />
          </div>

          <div className="brand-info">
            <h2>HealthGuard</h2>
            <span>SMART HEALTH PLATFORM</span>
          </div>
        </div>

        <nav className="sidebar-menu">
          {navigation.map((group) => (
            <div key={group.title}>
              <p className="menu-title">{group.title}</p>

              {group.items.map((item) => {
                const Icon = item.icon;

                return (
                  <button
                    key={item.name}
                    className={`menu-item ${
                      activePage === item.name ? "active" : ""
                    }`}
                    onClick={() => handleQuickAction(item.name)}
                    title={!sidebarOpen ? item.name : ""}
                  >
                    <Icon size={20} />
                    <span>{item.name}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="logout-button" onClick={handleLogout}>
            <LogOut size={19} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main
        className={`main-content ${sidebarOpen ? "" : "sidebar-collapsed"}`}
      >
        {/* TOPBAR */}
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="menu-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <ChevronLeft size={21} /> : <Menu size={21} />}
            </button>

            <div>
              <h1>{activePage}</h1>
              <p>{getPageDescription()}</p>
            </div>
          </div>

          <div className="topbar-right">
            <div className="status-indicator">
              <span className="status-dot"></span>
              <span>System Online</span>
            </div>

            <div className="user-profile">
              <div className="profile-avatar">
                <Activity size={21} />
              </div>

              <div className="profile-info">
                <strong>
                  {user.displayName ||
                    user.email?.split("@")[0] ||
                    "HealthGuard"}
                </strong>
                <span>{user.email}</span>
              </div>
            </div>
          </div>
        </header>

        {/* DASHBOARD */}
        {activePage === "Dashboard" && (
          <section className="dashboard-page">
            <div className="welcome-section">
              <div>
                <div className="welcome-icon">
                  <Activity size={25} />
                </div>

                <h2>Welcome to Smart HealthGuard</h2>

                <p>
                  Your intelligent platform for educational medicine
                  information, OCR scanning, risk insights, and AI assistance.
                </p>
              </div>
            </div>

            {/* QUICK ACTIONS */}
            <div className="section-header">
              <div>
                <h2>Explore Features</h2>
                <p>Choose a feature to get started.</p>
              </div>
            </div>

            <div className="quick-actions-grid">
              <button
                className="quick-action-card"
                onClick={() => handleQuickAction("Medicine Analyzer")}
              >
                <div className="feature-icon">💊</div>
                <h3>Medicine Analyzer</h3>
                <p>Explore medicine information and details.</p>
                <ArrowUpRight size={18} />
              </button>

              <button
                className="quick-action-card"
                onClick={() => handleQuickAction("OCR Scanner")}
              >
                <div className="feature-icon">📷</div>
                <h3>OCR Scanner</h3>
                <p>Scan medicine packages and extract information.</p>
                <ArrowUpRight size={18} />
              </button>

              <button
                className="quick-action-card"
                onClick={() => handleQuickAction("Risk Detection")}
              >
                <div className="feature-icon">🛡️</div>
                <h3>Risk Detection</h3>
                <p>Explore educational medicine safety insights.</p>
                <ArrowUpRight size={18} />
              </button>

              <button
                className="quick-action-card"
                onClick={() => handleQuickAction("AI Assistant")}
              >
                <div className="feature-icon">🤖</div>
                <h3>AI Assistant</h3>
                <p>Ask questions and explore medicine information.</p>
                <ArrowUpRight size={18} />
              </button>
            </div>

            {/* DASHBOARD CARDS */}
            <div
              className="dashboard-cards-layout"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "22px",
                marginTop: "25px",
              }}
            >
              {/* UPLOAD CARD */}
              <div className="dashboard-card">
                <div className="card-header">
                  <div>
                    <h3>Medicine Image Scanner</h3>
                    <p>Identify medicine packages using OCR.</p>
                  </div>

                  <div className="card-header-icon">
                    <ImagePlus size={23} />
                  </div>
                </div>

                <div className="upload-section">
                  <div className="upload-icon">
                    <Upload size={32} />
                  </div>

                  <h4>Scan Medicine Package</h4>

                  <p>
                    Upload a clear image of the medicine package to identify the
                    medicine and extract information.
                  </p>

                  <button
                    className="secondary-button"
                    onClick={() => handleQuickAction("OCR Scanner")}
                  >
                    <Upload size={18} />
                    Choose Image
                  </button>
                </div>
              </div>

              {/* RECENT ANALYSIS */}
              <div className="dashboard-card">
                <div className="card-header">
                  <div>
                    <h3>Recent Analysis</h3>
                    <p>Recently analyzed medicines and products.</p>
                  </div>

                  <Clock3 size={22} />
                </div>

                <div className="recent-analysis-item">
                  <div className="medicine-icon">
                    <FileText size={22} />
                  </div>

                  <div className="recent-analysis-info">
                    <strong>Amoxicillin</strong>
                    <span>Medicine information analyzed</span>
                  </div>

                  <div className="analysis-status">Completed</div>
                </div>
              </div>
            </div>

            {/* DISCLAIMER */}
            <div className="health-disclaimer">
              <AlertTriangle size={20} />

              <div>
                <strong>Educational Information Only</strong>

                <p>
                  Smart HealthGuard provides educational medicine and product
                  information. It is not a diagnostic or prescription system.
                  Always consult a qualified healthcare professional for medical
                  decisions.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* MEDICINE ANALYZER */}
        {activePage === "Medicine Analyzer" && <MedicineAnalyzerPage />}

        {/* OCR SCANNER */}
        {activePage === "OCR Scanner" && <OCRScannerPage />}

        {/* RISK DETECTION */}
        {activePage === "Risk Detection" && <RiskDetectionPage />}

        {/* INFORMATION VOICE */}
        {activePage === "Information Voice" && <InformationVoicePage />}

        {/* AI ASSISTANT */}
        {activePage === "AI Assistant" && <AIAssistantPage />}

        {/* ANALYSIS HISTORY */}
        {activePage === "Analysis History" && <AnalysisHistoryPage />}
      </main>
    </div>
    
  );
  

  
}




export default App;

