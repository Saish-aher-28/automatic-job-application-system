import React, { useState, useEffect } from "react";
import { initializeApp } from "firebase/app";
import {
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from "firebase/auth";
import type { User as FirebaseUser } from "firebase/auth";
import { api } from "./api";

// ── TYPES ───────────────────────────────────────────────────────────────────

interface Profile {
  name: string;
  degree_title: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
  summary: string;
}

interface Project {
  _id?: string;
  name: string;
  year: string;
  technologies: string[];
  description: string;
  resume_bullets: string[];
  keywords: string[];
  categories: string[];
  enabled: boolean;
  priority: number;
}

interface Skill {
  id?: string;
  name: string;
  category: string;
  sort_order: number;
}

interface Job {
  job_id: string;
  company: string;
  job_title: string;
  application_url: string;
  jd_text: string;
  location: string;
  source: string;
  status: string;
  jd_document_id?: string;
  match_id?: string;
  tailored_resume_id?: string;
  created_at: string;
}

interface Application {
  id: string;
  user_id: string;
  job_id: string;
  opportunity_id?: string;
  job_match_id?: string;
  job_title: string;
  company: string;
  application_url: string;
  status: string;
  match_score: number;
  resume_path?: string;
  resume_filename?: string;
  resume_generated_at?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  submitted_at?: string;
  source?: {
    type: string;
    name: string;
    url: string;
  };
  submission?: {
    method: string;
    confirmation: boolean;
  };
  notes?: string;
}

interface ApplicationEvent {
  id: string;
  event: string;
  timestamp: string;
  user_id: string;
  from?: string;
  to?: string;
  notes?: string;
}

interface MatchResult {
  job_title?: string;
  overall_match_score?: number;
  required_skill_match_score?: number;
  preferred_skill_match_score?: number;
  technology_match_score?: number;
  project_relevance_score?: number;
  matched_required_skills?: string[];
  missing_required_skills?: string[];
  matched_preferred_skills?: string[];
  missing_preferred_skills?: string[];
  scores?: {
    overall?: number;
    required_skills?: number;
    preferred_skills?: number;
    technologies?: number;
    projects?: number;
  };
  skill_match?: {
    matched_required?: string[];
    missing_required?: string[];
    matched_preferred?: string[];
    missing_preferred?: string[];
  };
  ranked_projects?: Array<{
    project_name: string;
    final_project_score: number;
    reason: string;
  }>;
}


// ── APP COMPONENT ───────────────────────────────────────────────────────────

export default function App() {
  const [firebaseInitialized, setFirebaseInitialized] = useState(false);
  const [authInstance, setAuthInstance] = useState<any>(null);
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [isSingleUserMode, setIsSingleUserMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  // Routing and Navigation
  const [currentHash, setCurrentHash] = useState(window.location.hash || "#/dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Auth Inputs
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  // Bootstrap Firebase from Go Endpoint
  useEffect(() => {
    async function init() {
      try {
        // Fetch config from Go API Config endpoint
        const res = await fetch("http://localhost:8080/api/v1/auth/config");
        const body = await res.json();
        if (body.success) {
          const isSingle = !!body.data.singleUserMode;
          setIsSingleUserMode(isSingle);
          if (isSingle) {
            setUser({ email: "saishaher28@gmail.com", uid: "saish-aher-dev" } as any);
            setLoading(false);
          } else {
            const app = initializeApp(body.data);
            const auth = getAuth(app);
            setAuthInstance(auth);

            onAuthStateChanged(auth, (usr) => {
              setUser(usr);
              setLoading(false);
            });
            setFirebaseInitialized(true);
          }
        } else {
          throw new Error("Failed to load Firebase auth configuration");
        }
      } catch (err: any) {
        console.error("Initialization error:", err);
        // Fallback for single-user dev mode (bypass firebase auth loading)
        setLoading(false);
      }
    }
    init();
  }, []);

  // Hash route listener
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentHash(window.location.hash || "#/dashboard");
      setMobileMenuOpen(false);
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authInstance) return;
    setAuthLoading(true);
    setAuthError("");
    try {
      await signInWithEmailAndPassword(authInstance, emailInput, passwordInput);
    } catch (err: any) {
      setAuthError(err.message || "Invalid credentials");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    if (!authInstance) {
      // Mock logout for dev bypass
      setUser(null);
      return;
    }
    await signOut(authInstance);
  };

  if (loading) {
    return (
      <div className="login-container">
        <div>Loading dashboard services...</div>
      </div>
    );
  }

  // Enforce auth unless SingleUserMode is true and we bypass it
  const isMockDev = isSingleUserMode || !firebaseInitialized || !authInstance;
  const isAuthenticated = user || isMockDev;

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="card login-card">
          <div className="login-logo">AutoResume Dashboard</div>
          <h3 style={{ marginBottom: "1.5rem", textAlign: "center" }}>Sign In</h3>
          {authError && <div className="alert alert-danger">{authError}</div>}
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                className="form-control"
                required
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                className="form-control"
                required
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: "100%", marginTop: "1rem" }} disabled={authLoading}>
              {authLoading ? "Signing In..." : "Login"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const navigateTo = (hash: string) => {
    window.location.hash = hash;
  };

  // Render view router based on hash
  const renderView = () => {
    if (currentHash.startsWith("#/jobs/")) {
      const id = currentHash.split("/")[2];
      return <JobDetailPage jobId={id} navigateTo={navigateTo} />;
    }
    if (currentHash.startsWith("#/applications/")) {
      const id = currentHash.split("/")[2];
      return <ApplicationDetailPage applicationId={id} navigateTo={navigateTo} />;
    }

    switch (currentHash) {
      case "#/dashboard":
        return <DashboardView navigateTo={navigateTo} />;
      case "#/jobs":
        return <JobsListView navigateTo={navigateTo} />;
      case "#/applications":
        return <ApplicationsListView navigateTo={navigateTo} />;
      case "#/opportunities":
        return <OpportunitiesListView navigateTo={navigateTo} />;
      case "#/sources":
      case "#/runs":
        return <SourcesView />;
      case "#/profile":
        return <ProfileView />;
      case "#/projects":
        return <ProjectsView />;
      case "#/skills":
        return <SkillsView />;
      case "#/education":
      case "#/experience":
      case "#/certifications":
      case "#/languages":
      case "#/interests":
        return <ProfileSubcollectionsView section={currentHash.substring(2)} />;
      default:
        return <DashboardView navigateTo={navigateTo} />;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Nav */}
      <aside className={`sidebar ${mobileMenuOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-logo">
          <span>AutoResume DB</span>
        </div>
        <nav className="sidebar-nav">
          <a onClick={() => navigateTo("#/dashboard")} className={`nav-item ${currentHash === "#/dashboard" ? "active" : ""}`}>
            Dashboard
          </a>
          <a onClick={() => navigateTo("#/applications")} className={`nav-item ${currentHash.startsWith("#/applications") ? "active" : ""}`}>
            Applications Tracker
          </a>
          <a onClick={() => navigateTo("#/jobs")} className={`nav-item ${currentHash.startsWith("#/jobs") ? "active" : ""}`}>
            Job Pipeline
          </a>
          <a onClick={() => navigateTo("#/opportunities")} className={`nav-item ${currentHash.startsWith("#/opportunities") ? "active" : ""}`}>
            Job Opportunities
          </a>
          <a onClick={() => navigateTo("#/sources")} className={`nav-item ${currentHash.startsWith("#/sources") ? "active" : ""}`}>
            Job Sources
          </a>
          <a onClick={() => navigateTo("#/runs")} className={`nav-item ${currentHash === "#/runs" ? "active" : ""}`}>
            Ingestion Runs
          </a>

          <a onClick={() => navigateTo("#/profile")} className={`nav-item ${currentHash === "#/profile" ? "active" : ""}`}>
            My Profile
          </a>
          <a onClick={() => navigateTo("#/projects")} className={`nav-item ${currentHash === "#/projects" ? "active" : ""}`}>
            Projects
          </a>
          <a onClick={() => navigateTo("#/skills")} className={`nav-item ${currentHash === "#/skills" ? "active" : ""}`}>
            Skills
          </a>
          <a onClick={() => navigateTo("#/experience")} className={`nav-item ${currentHash === "#/experience" ? "active" : ""}`}>
            Experience
          </a>
          <a onClick={() => navigateTo("#/education")} className={`nav-item ${currentHash === "#/education" ? "active" : ""}`}>
            Education
          </a>
          <a onClick={() => navigateTo("#/certifications")} className={`nav-item ${currentHash === "#/certifications" ? "active" : ""}`}>
            Certifications
          </a>
          <a onClick={() => navigateTo("#/languages")} className={`nav-item ${currentHash === "#/languages" ? "active" : ""}`}>
            Languages
          </a>
          <a onClick={() => navigateTo("#/interests")} className={`nav-item ${currentHash === "#/interests" ? "active" : ""}`}>
            Interests
          </a>
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">{user?.email || "Saish Aher (Developer)"}</div>
          <button className="btn btn-secondary" style={{ width: "100%" }} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      {/* Main Panel */}
      <div className="main-wrapper">
        <header className="top-bar">
          <button className="hamburger-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            ☰
          </button>
          <div className="top-bar-title">Automatic Job Application System</div>
          <div style={{ display: "flex", gap: "1rem" }}>
            {isMockDev && <span className="badge badge-new">Dev Mode</span>}
          </div>
        </header>
        <main className="content-body">
          <ErrorBoundary>{renderView()}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

// ── ERROR BOUNDARY ──────────────────────────────────────────────────────────

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Uncaught React ErrorBoundary caught an exception:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="view-container" style={{ padding: "2rem" }}>
          <div className="card" style={{ padding: "2rem", borderLeft: "4px solid var(--danger-color)" }}>
            <h2 style={{ marginTop: 0, color: "var(--danger-color)" }}>Something went wrong</h2>
            <p style={{ color: "var(--text-muted)" }}>
              An unexpected error occurred while rendering this view.
            </p>
            {this.state.error && (
              <pre style={{ background: "rgba(0,0,0,0.4)", padding: "1rem", borderRadius: "6px", overflowX: "auto", fontSize: "0.85rem" }}>
                {this.state.error.message}
              </pre>
            )}
            <div style={{ display: "flex", gap: "1rem", marginTop: "1.5rem" }}>
              <button className="btn btn-primary" onClick={() => this.setState({ hasError: false, error: null })}>
                Try Again
              </button>
              <button className="btn btn-secondary" onClick={() => (window.location.hash = "#/dashboard")}>
                Go to Dashboard
              </button>
              <button className="btn btn-outline" onClick={() => window.location.reload()}>
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}


// ── 1. DASHBOARD VIEW ────────────────────────────────────────────────────────

function DashboardView({ navigateTo }: { navigateTo: (h: string) => void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Job[]>("/jobs")
      .then(setJobs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading dashboard analytics...</div>;

  // Compute Metrics
  const total = jobs.length;
  const newJobs = jobs.filter((j) => j.status === "NEW").length;
  const matched = jobs.filter((j) => j.status === "MATCHED").length;
  const resumeReady = jobs.filter((j) => j.status === "RESUME_READY").length;
  const applied = jobs.filter((j) => j.status === "APPLIED").length;
  const interviews = jobs.filter((j) => j.status === "INTERVIEW").length;

  return (
    <div>
      <h2 style={{ marginBottom: "1.5rem" }}>Dashboard Summary</h2>
      
      <div className="metrics-grid">
        <div className="card metric-card">
          <div className="metric-val">{total}</div>
          <div className="metric-lbl">Total Jobs</div>
        </div>
        <div className="card metric-card" style={{ borderLeft: "3px solid var(--accent-primary)" }}>
          <div className="metric-val">{newJobs}</div>
          <div className="metric-lbl">New</div>
        </div>
        <div className="card metric-card" style={{ borderLeft: "3px solid var(--color-info)" }}>
          <div className="metric-val">{matched}</div>
          <div className="metric-lbl">Matched</div>
        </div>
        <div className="card metric-card" style={{ borderLeft: "3px solid var(--color-success)" }}>
          <div className="metric-val">{resumeReady}</div>
          <div className="metric-lbl">Resume Ready</div>
        </div>
        <div className="card metric-card" style={{ borderLeft: "3px solid var(--accent-secondary)" }}>
          <div className="metric-val">{applied}</div>
          <div className="metric-lbl">Applied</div>
        </div>
        <div className="card metric-card" style={{ borderLeft: "3px solid var(--color-warning)" }}>
          <div className="metric-val">{interviews}</div>
          <div className="metric-lbl">Interviews</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "2rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Recent Applications</h3>
        {jobs.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: "2rem" }}>
            No applications added yet. Go to Job Applications to add your first job.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Job Title</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 5).map((job) => (
                  <tr key={job.job_id}>
                    <td><strong>{job.company}</strong></td>
                    <td>{job.job_title}</td>
                    <td>{job.location || "Remote"}</td>
                    <td>
                      <span className={`badge badge-${job.status.toLowerCase()}`}>{job.status}</span>
                    </td>
                    <td>
                      <button className="btn btn-secondary" onClick={() => navigateTo(`#/jobs/${job.job_id}`)}>
                        Manage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── 2. JOBS LIST VIEW ────────────────────────────────────────────────────────

function JobsListView({ navigateTo }: { navigateTo: (h: string) => void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [showAddModal, setShowAddModal] = useState(false);

  // New Job Inputs
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [location, setLocation] = useState("");
  const [jdText, setJdText] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");

  const fetchJobs = () => {
    api.get<Job[]>("/jobs")
      .then(setJobs)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLoading(true);
    setAddError("");
    try {
      await api.post<Job>("/jobs", {
        company,
        job_title: title,
        application_url: urlInput,
        location,
        jd_text: jdText,
      });
      fetchJobs();
      setShowAddModal(false);
      // Reset inputs
      setCompany("");
      setTitle("");
      setUrlInput("");
      setLocation("");
      setJdText("");
    } catch (err: any) {
      setAddError(err.message || "Failed to add job application");
    } finally {
      setAddLoading(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.company.toLowerCase().includes(search.toLowerCase()) ||
      job.job_title.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || job.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2>Job Applications</h2>
        <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          + Add New Job
        </button>
      </div>

      {/* Filters card */}
      <div className="card" style={{ marginBottom: "1.5rem", padding: "1rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
          <div style={{ flexGrow: 1, minWidth: "200px" }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search by company or role..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ width: "150px" }}>
            <select className="form-control" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="ALL">All Statuses</option>
              <option value="NEW">New</option>
              <option value="ANALYZED">Analyzed</option>
              <option value="MATCHED">Matched</option>
              <option value="RESUME_READY">Resume Ready</option>
              <option value="APPLIED">Applied</option>
              <option value="INTERVIEW">Interview</option>
              <option value="REJECTED">Rejected</option>
              <option value="OFFER">Offer</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div>Loading application tracker...</div>
        ) : filteredJobs.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: "2rem" }}>
            No applications match your filter settings.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job) => (
                  <tr key={job.job_id}>
                    <td><strong>{job.company}</strong></td>
                    <td>{job.job_title}</td>
                    <td>{job.location || "Remote"}</td>
                    <td>
                      <span className={`badge badge-${job.status.toLowerCase()}`}>{job.status}</span>
                    </td>
                    <td>
                      <button className="btn btn-secondary" onClick={() => navigateTo(`#/jobs/${job.job_id}`)}>
                        Manage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Job Modal */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="card modal-content">
            <div className="modal-header">
              <h3>Add Job Application</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>
                &times;
              </button>
            </div>
            {addError && <div className="alert alert-danger">{addError}</div>}
            <form onSubmit={handleAddJob}>
              <div className="form-group">
                <label>Company Name*</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  placeholder="e.g. Google"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Job Title*</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  placeholder="e.g. Frontend Engineer"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Application URL</label>
                <input
                  type="url"
                  className="form-control"
                  placeholder="https://company.com/jobs/123"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Bangalore, Remote"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Job Description*</label>
                <textarea
                  className="form-control"
                  required
                  placeholder="Paste raw JD text here..."
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={addLoading}>
                  {addLoading ? "Saving..." : "Save Application"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 3. JOB DETAIL PAGE ───────────────────────────────────────────────────────

function JobDetailPage({ jobId, navigateTo }: { jobId: string; navigateTo?: (hash: string) => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [opLoading, setOpLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchJobDetails = async () => {
    try {
      const jobData = await api.get<Job>(`/jobs/${jobId}`);
      setJob(jobData);

      if (jobData.match_id) {
        try {
          const rawMatch = await api.get<any>(`/jobs/${jobId}/match-result`);
          const res = (rawMatch && rawMatch.data) ? rawMatch.data : rawMatch;
          setMatchResult(res);
        } catch (err) {
          console.warn("Could not fetch match result yet:", err);
        }
      }

    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load job details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobDetails();
  }, [jobId]);

  const handleAnalyze = async () => {
    setOpLoading(true);
    setErrorMsg("");
    try {
      await api.post(`/jobs/${jobId}/analyze`, {});
      await fetchJobDetails();
    } catch (err: any) {
      setErrorMsg(err.message || "Subprocess analysis failed");
      await fetchJobDetails();
    } finally {
      setOpLoading(false);
    }
  };

  const handleMatch = async () => {
    setOpLoading(true);
    setErrorMsg("");
    try {
      await api.post(`/jobs/${jobId}/match`, {});
      await fetchJobDetails();
    } catch (err: any) {
      setErrorMsg(err.message || "Subprocess match failed");
      await fetchJobDetails();
    } finally {
      setOpLoading(false);
    }
  };

  const handleGenerate = async () => {
    setOpLoading(true);
    setErrorMsg("");
    try {
      await api.post(`/jobs/${jobId}/generate-resume`, {});
      await fetchJobDetails();
    } catch (err: any) {
      setErrorMsg(err.message || "Subprocess tailoring failed");
      await fetchJobDetails();
    } finally {
      setOpLoading(false);
    }
  };

  const handleUpdateStatus = async (status: string) => {
    try {
      await api.patch(`/jobs/${jobId}/status`, { status });
      await fetchJobDetails();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update status");
    }
  };

  if (loading) return <div>Loading application details...</div>;
  if (!job) return <div className="alert alert-danger">Job application not found.</div>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", alignItems: "center", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <a href="#/jobs" style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            &larr; Back to Applications
          </a>
          <h2>{job.job_title} at {job.company}</h2>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", alignItems: "center" }}>
            <span className={`badge badge-${job.status.toLowerCase()}`}>{job.status}</span>
            {job.location && <span style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>&bull; {job.location}</span>}
          </div>
        </div>

        {/* Action Panel */}
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button
            className="btn btn-success"
            onClick={async () => {
              try {
                const appData = await api.post<Application>("/applications", { job_id: job.job_id });
                if (appData && appData.id) {
                  if (navigateTo) navigateTo(`#/applications/${appData.id}`);
                  else window.location.hash = `#/applications/${appData.id}`;
                } else {
                  if (navigateTo) navigateTo("#/applications");
                  else window.location.hash = "#/applications";
                }
              } catch (err: any) {
                alert(err.message || "Failed to open application tracker");
              }

            }}
          >
            Open Application Tracker
          </button>

          {job.status === "NEW" || job.status === "FAILED" ? (
            <button className="btn btn-primary" onClick={handleAnalyze} disabled={opLoading}>
              {opLoading ? "Analyzing..." : "Analyze JD"}
            </button>
          ) : null}

          {job.status === "ANALYZED" ? (
            <button className="btn btn-primary" onClick={handleMatch} disabled={opLoading}>
              {opLoading ? "Matching..." : "Run Match"}
            </button>
          ) : null}

          {job.status === "MATCHED" ? (
            <button className="btn btn-primary" onClick={handleGenerate} disabled={opLoading}>
              {opLoading ? "Tailoring..." : "Generate Tailored Resume"}
            </button>
          ) : null}

          {job.status === "RESUME_READY" ? (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <a href={api.getResumePDFURL(job.job_id)} className="btn btn-primary" target="_blank" rel="noopener noreferrer">
                Download PDF
              </a>
              <button className="btn btn-secondary" onClick={handleGenerate} disabled={opLoading}>
                {opLoading ? "Tailoring..." : "Regenerate"}
              </button>
              <button className="btn btn-secondary" onClick={() => handleUpdateStatus("APPLIED")}>
                Mark Applied
              </button>
            </div>
          ) : null}

          {job.status === "APPLIED" && (
            <button className="btn btn-secondary" onClick={() => handleUpdateStatus("INTERVIEW")}>
              Mark Interview Invitation
            </button>
          )}

          {job.status === "INTERVIEW" && (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-primary" onClick={() => handleUpdateStatus("OFFER")}>
                Mark Offer Received
              </button>
              <button className="btn btn-danger" onClick={() => handleUpdateStatus("REJECTED")}>
                Mark Rejected
              </button>
            </div>
          )}

          {(job.status === "ANALYZING" || job.status === "MATCHING" || job.status === "RESUME_GENERATING") && (
            <button className="btn btn-secondary" onClick={() => handleUpdateStatus("NEW")} disabled={opLoading}>
              Reset Status to NEW
            </button>
          )}
        </div>

      </div>

      {errorMsg && <div className="alert alert-danger" style={{ marginBottom: "1.5rem" }}>{errorMsg}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
        {/* JD & URL Details */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div className="card">
            <h3 style={{ marginBottom: "1rem" }}>Application Info</h3>
            {job.application_url ? (
              <div style={{ marginBottom: "1rem" }}>
                <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-secondary)" }}>URL</strong>
                <a href={job.application_url} target="_blank" rel="noopener noreferrer" style={{ wordBreak: "break-all" }}>
                  {job.application_url}
                </a>
              </div>
            ) : null}
            <div>
              <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>Job Description</strong>
              <div
                style={{
                  maxHeight: "350px",
                  overflowY: "auto",
                  fontSize: "0.9rem",
                  whiteSpace: "pre-wrap",
                  backgroundColor: "rgba(0,0,0,0.3)",
                  padding: "1rem",
                  borderRadius: "8px",
                  border: "1px solid var(--border-color)",
                }}
              >
                {job.jd_text}
              </div>
            </div>
          </div>
        </div>

        {/* Match breakdown & score */}
        <div>
          {matchResult ? (() => {
            const m = (matchResult as any).data || matchResult;
            const rawOverall = m.scores?.overall ?? m.overall_match_score ?? m.overall ?? 0;
            const rawReq = m.scores?.required_skills ?? m.required_skill_match_score ?? m.required_skills ?? 0;
            const rawPref = m.scores?.preferred_skills ?? m.preferred_skill_match_score ?? m.preferred_skills ?? 0;

            const overallNum = typeof rawOverall === 'number' ? rawOverall : (parseFloat(rawOverall) || 0);
            const reqNum = typeof rawReq === 'number' ? rawReq : (parseFloat(rawReq) || 0);
            const prefNum = typeof rawPref === 'number' ? rawPref : (parseFloat(rawPref) || 0);

            const matchedReq = m.skill_match?.matched_required ?? m.matched_required_skills ?? [];
            const missingReq = m.skill_match?.missing_required ?? m.missing_required_skills ?? [];

            return (
              <div className="card">
                <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>Match Score</div>
                  <div style={{ fontSize: "3rem", fontWeight: 700, color: "var(--accent-primary)" }}>{overallNum.toFixed(1)}%</div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
                  <div style={{ textAlign: "center", padding: "0.5rem", borderRight: "1px solid var(--border-color)" }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Required Skills</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>{reqNum.toFixed(1)}%</div>
                  </div>
                  <div style={{ textAlign: "center", padding: "0.5rem" }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Preferred Skills</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>{prefNum.toFixed(1)}%</div>
                  </div>
                </div>


                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                  <div>
                    <h4 style={{ color: "var(--color-success)", fontSize: "0.9rem", marginBottom: "0.5rem" }}>Matched Required</h4>
                    {matchedReq.length === 0 ? (
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>None</div>
                    ) : (
                      <ul style={{ paddingLeft: "1.25rem", fontSize: "0.85rem" }}>
                        {matchedReq.map((s: string, idx: number) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h4 style={{ color: "var(--color-danger)", fontSize: "0.9rem", marginBottom: "0.5rem" }}>Missing Required</h4>
                    {missingReq.length === 0 ? (
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>None</div>
                    ) : (
                      <ul style={{ paddingLeft: "1.25rem", fontSize: "0.85rem", color: "#f87171" }}>
                        {missingReq.map((s: string, idx: number) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>

                {(matchResult.ranked_projects || []).length > 0 && (
                  <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                    <h4 style={{ marginBottom: "0.5rem" }}>Ranked Projects</h4>
                    <ol style={{ paddingLeft: "1.25rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {(matchResult.ranked_projects || []).slice(0, 3).map((p: any, idx: number) => (
                        <li key={idx}>
                          <strong>{p.project_name}</strong> - Score: {typeof p.final_project_score === 'number' ? p.final_project_score.toFixed(1) : p.final_project_score}%
                          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", fontStyle: "italic" }}>
                            {p.reason}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            );
          })() : (
            <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "250px" }}>
              <div style={{ textAlign: "center", color: "var(--text-secondary)" }}>
                Match scoring is not executed yet. Click <strong>Run Match</strong> to start scoring.
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
// ── 3.5 OPPORTUNITIES VIEW ──────────────────────────────────────────────────

interface JobOpportunity {
  id?: string;
  source: string;
  source_type: string;
  source_name: string;
  source_url: string;
  company: string;
  job_title: string;
  description: string;
  location: string;
  employment_type: string;
  experience: string;
  salary: string;
  skills: string[];
  technologies: string[];
  discovered_at: string;
  ingestion_status: string;
}

function OpportunitiesListView({ navigateTo }: { navigateTo: (h: string) => void }) {
  const [opportunities, setOpportunities] = useState<JobOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [importingId, setImportingId] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchOpportunities = () => {
    api.get<JobOpportunity[]>("/opportunities")
      .then((data) => {
        setOpportunities(data);
        setLastUpdated(new Date());
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchOpportunities();
  }, []);

  // Polling for live updates without backend restart
  useEffect(() => {
    let interval: any = null;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchOpportunities();
      }, 15000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const handleImport = async (id: string) => {
    setImportingId(id);
    try {
      const res = await api.post<any>(`/opportunities/${id}/import`, {});
      alert("Opportunity imported successfully! Redirecting to job details...");
      fetchOpportunities();
      if (res && res.job_id) {
        navigateTo(`#/jobs/${res.job_id}`);
      } else if (res && res.data && res.data.job_id) {
        navigateTo(`#/jobs/${res.data.job_id}`);
      } else {
        navigateTo("#/jobs");
      }
    } catch (err: any) {
      alert(err.message || "Failed to import opportunity");
    } finally {
      setImportingId(null);
    }
  };

  const filtered = opportunities.filter((op) => {
    const matchesSearch =
      (op.company || "").toLowerCase().includes(search.toLowerCase()) ||
      (op.job_title || "").toLowerCase().includes(search.toLowerCase()) ||
      (op.description || "").toLowerCase().includes(search.toLowerCase());
    return matchesSearch;
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <h2>Discovered Opportunities</h2>
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            Last updated: {lastUpdated.toLocaleTimeString()}
          </span>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button className="btn btn-secondary btn-sm" onClick={() => fetchOpportunities()}>
            Refresh
          </button>
          <button
            className={`btn btn-sm ${autoRefresh ? "btn-success" : "btn-outline"}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto-refresh: {autoRefresh ? "ON" : "OFF"}
          </button>
        </div>
      </div>


      <div className="card" style={{ marginBottom: "1.5rem", padding: "1rem" }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by company, title, or keywords..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="card">
        {loading ? (
          <div>Loading opportunities list...</div>
        ) : filtered.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: "2rem" }}>
            No opportunities found.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Title</th>
                  <th>Location</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((op) => (
                  <tr key={op.id}>
                    <td><strong>{op.company || "Unknown"}</strong></td>
                    <td>{op.job_title || "Unknown"}</td>
                    <td>{op.location || "Remote"}</td>
                    <td>
                      {op.source_url ? (
                        <a href={op.source_url} target="_blank" rel="noopener noreferrer">
                          {op.source_name}
                        </a>
                      ) : (
                        op.source_name
                      )}
                    </td>
                    <td>
                      <span className={`badge badge-${(op.ingestion_status || "stored").toLowerCase()}`}>
                        {op.ingestion_status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={op.ingestion_status === "IMPORTED" || importingId === op.id}
                          onClick={() => op.id && handleImport(op.id)}
                        >
                          {op.ingestion_status === "IMPORTED" ? "Imported" : importingId === op.id ? "Importing..." : "Import"}
                        </button>
                        <button
                          className="btn btn-success btn-sm"
                          onClick={async () => {
                            if (!op.id) return;
                            try {
                              let targetJobId = "";
                              if (op.ingestion_status !== "IMPORTED") {
                                const imp = await api.post<any>(`/opportunities/${op.id}/import`, {});
                                targetJobId = imp?.job_id || imp?.data?.job_id;
                              }
                              if (!targetJobId) {
                                // fetch jobs to locate imported job
                                const jobsList = await api.get<Job[]>("/jobs");
                                const found = (jobsList || []).find((j: any) => j.company === op.company && j.job_title === op.job_title);
                                if (found) targetJobId = found.job_id;
                              }
                              if (targetJobId) {
                                const appData = await api.post<Application>("/applications", { job_id: targetJobId, opportunity_id: op.id });
                                if (appData && appData.id) {
                                  navigateTo(`#/applications/${appData.id}`);
                                } else {
                                  navigateTo("#/applications");
                                }
                              } else {
                                alert("Failed to resolve job record");
                              }

                            } catch (err) {
                              alert("Failed to prepare application");
                            }
                          }}
                        >
                          Prepare Application
                        </button>
                      </div>
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── JOB SOURCES MANAGEMENT VIEW ──────────────────────────────────────────────

interface JobSource {
  id?: string;
  user_id?: string;
  name: string;
  type: "telegram" | "website";
  adapter_mode?: string;
  identifier?: string;
  url?: string;
  enabled: boolean;
  state: string;
  last_run_at?: string;
  last_success_at?: string;
  last_error?: string;
  configuration?: Record<string, any>;
  created_at?: string;
}

interface IngestionRun {
  id: string;
  source_id: string;
  user_id?: string;
  source_type: string;
  source_name: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  messages_scanned: number;
  jobs_detected: number;
  jobs_created: number;
  duplicates_skipped: number;
  non_jobs_skipped: number;
  retry_count: number;
}

function SourcesView() {
  const [sources, setSources] = useState<JobSource[]>([]);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSource, setEditingSource] = useState<JobSource | null>(null);

  // Form Fields
  const [name, setName] = useState("");
  const [type, setType] = useState<"telegram" | "website">("telegram");
  const [adapterMode, setAdapterMode] = useState<"public_web" | "api">("public_web");
  const [identifier, setIdentifier] = useState("");
  const [url, setUrl] = useState("");

  // Test and Run states
  const [testingId, setTestingId] = useState<string | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; details?: string } | null>(null);

  const fetchSources = () => {
    api.get<JobSource[]>("/sources")
      .then(setSources)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const fetchRuns = () => {
    api.get<IngestionRun[]>("/runs")
      .then((data) => setRuns(data || []))
      .catch(console.error);
  };

  useEffect(() => {
    fetchSources();
    fetchRuns();
  }, []);

  // Poll background runs every 5 seconds if active runs exist
  useEffect(() => {
    const hasActive = runs.some((r) => r.status === "QUEUED" || r.status === "RUNNING");
    if (!hasActive) return;

    const timer = setInterval(() => {
      fetchSources();
      fetchRuns();
    }, 5000);

    return () => clearInterval(timer);
  }, [runs]);

  const openAddModal = () => {
    setEditingSource(null);
    setName("");
    setType("telegram");
    setAdapterMode("public_web");
    setIdentifier("");
    setUrl("");
    setTestResult(null);
    setShowModal(true);
  };

  const openEditModal = (s: JobSource) => {
    setEditingSource(s);
    setName(s.name);
    setType(s.type);
    setAdapterMode((s.adapter_mode as any) || "public_web");
    setIdentifier(s.identifier || "");
    setUrl(s.url || "");
    setTestResult(null);
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name,
      type,
      adapter_mode: type === "telegram" ? adapterMode : "",
      identifier: type === "telegram" ? identifier : "",
      url: type === "website" ? url : "",
      enabled: editingSource ? editingSource.enabled : true,
      state: editingSource ? editingSource.state : "ENABLED",
      configuration: editingSource ? editingSource.configuration : {},
    };

    try {
      if (editingSource && editingSource.id) {
        await api.put(`/sources/${editingSource.id}`, payload);
      } else {
        await api.post("/sources", payload);
      }
      setShowModal(false);
      fetchSources();
    } catch (err: any) {
      alert(err.message || "Failed to save job source");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this source? Discovered jobs will NOT be deleted.")) {
      return;
    }
    try {
      await api.delete(`/sources/${id}`);
      fetchSources();
    } catch (err: any) {
      alert(err.message || "Failed to delete source");
    }
  };

  const handleToggleEnable = async (s: JobSource) => {
    if (!s.id) return;
    try {
      if (s.enabled) {
        await api.post(`/sources/${s.id}/disable`, {});
      } else {
        await api.post(`/sources/${s.id}/enable`, {});
      }
      fetchSources();
    } catch (err: any) {
      alert(err.message || "Failed to toggle source status");
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const res = await api.post<any>(`/sources/${id}/test`, {});
      setTestResult({
        success: res.success,
        message: res.message || (res.success ? "Connection successful!" : "Connection failed"),
        details: res.details,
      });
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || "Source validation test failed",
      });
    } finally {
      setTestingId(null);
    }
  };

  const handleRunNow = async (id: string) => {
    setRunningId(id);
    try {
      const res = await api.post<any>(`/sources/${id}/run`, {});
      setTestResult({
        success: true,
        message: res.message || "Ingestion task queued (202 Accepted). Background worker is processing.",
      });
      fetchSources();
      fetchRuns();
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || "Ingestion run failed",
      });
    } finally {
      setRunningId(null);
    }
  };

  const formatTime = (isoString?: string) => {
    if (!isoString) return "Never";
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2>Job Discovery Sources</h2>
        <button className="btn btn-primary" onClick={openAddModal}>
          + Add New Source
        </button>
      </div>

      {testResult && (
        <div className={`alert ${testResult.success ? "alert-success" : "alert-danger"}`} style={{ display: "block", marginBottom: "1.5rem", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(255, 255, 255, 0.1)", backgroundColor: "var(--bg-secondary)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <strong style={{ color: testResult.success ? "var(--color-success)" : "var(--color-danger)" }}>
                {testResult.success ? "Status Update" : "Execution Error"}:
              </strong>{" "}
              {testResult.message}
            </div>
            <button className="modal-close" style={{ fontSize: "1rem" }} onClick={() => setTestResult(null)}>×</button>
          </div>
          {testResult.details && (
            <pre style={{ marginTop: "0.5rem", padding: "0.5rem", backgroundColor: "rgba(0,0,0,0.4)", borderRadius: "4px", fontSize: "0.8rem", overflowX: "auto", whiteSpace: "pre-wrap", maxHeight: "150px" }}>
              {testResult.details}
            </pre>
          )}
        </div>
      )}

      <div className="card" style={{ marginBottom: "2rem" }}>
        {loading ? (
          <div>Loading discovery sources...</div>
        ) : sources.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: "2rem" }}>
            No sources configured. Click "+ Add New Source" to begin.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Source Name</th>
                  <th>Type</th>
                  <th>Identifier / URL</th>
                  <th>Status</th>
                  <th>Last Success Run</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{s.name}</strong>
                    </td>
                    <td>
                      <span className={`badge ${s.type === "telegram" ? "badge-applied" : "badge-analyzed"}`}>
                        {s.type}
                      </span>
                      {s.type === "telegram" && (
                        <span className="badge badge-secondary" style={{ marginLeft: "0.25rem" }}>
                          {s.adapter_mode === "api" ? "API" : "Public"}
                        </span>
                      )}
                    </td>
                    <td>
                      {s.type === "telegram" ? (
                        <code>{s.identifier}</code>
                      ) : (
                        <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ wordBreak: "break-all" }}>
                          {s.url}
                        </a>
                      )}
                    </td>
                    <td>
                      <span className={`badge badge-${(s.state || "enabled").toLowerCase()}`}>
                        {s.state}
                      </span>
                    </td>
                    <td>
                      <small style={{ color: "var(--text-secondary)" }}>
                        {formatTime(s.last_success_at)}
                      </small>
                      {s.last_error && (
                        <div style={{ color: "var(--color-danger)", fontSize: "0.75rem", marginTop: "0.25rem", wordBreak: "break-all" }}>
                          Error: {s.last_error}
                        </div>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={runningId === s.id || testingId === s.id}
                          onClick={() => s.id && handleTest(s.id)}
                        >
                          {testingId === s.id ? "Testing..." : "Test"}
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={!s.enabled || runningId === s.id || testingId === s.id || s.state === "RUNNING" || s.state === "QUEUED"}
                          onClick={() => s.id && handleRunNow(s.id)}
                        >
                          {s.state === "RUNNING" || runningId === s.id ? "Running..." : s.state === "QUEUED" ? "Queued" : "Run Now"}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleToggleEnable(s)}
                        >
                          {s.enabled ? "Disable" : "Enable"}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => openEditModal(s)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => s.id && handleDelete(s.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Ingestion History Table */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h3>Background Ingestion History</h3>
      </div>
      <div className="card">
        {runs.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: "1.5rem" }}>
            No background ingestion runs recorded yet. Click "Run Now" on any enabled source to trigger a job.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Queued / Started</th>
                  <th>Items Scanned</th>
                  <th>Jobs Created</th>
                  <th>Duplicates Skipped</th>
                  <th>Non-Jobs Skipped</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{r.source_name || r.source_id}</strong></td>
                    <td>
                      <span className={`badge ${r.source_type === "telegram" ? "badge-applied" : "badge-analyzed"}`}>
                        {r.source_type}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-${r.status.toLowerCase()}`}>
                        {r.status}
                      </span>
                    </td>
                    <td>
                      <small style={{ color: "var(--text-secondary)" }}>
                        {formatTime(r.started_at || r.created_at)}
                      </small>
                    </td>
                    <td>{r.messages_scanned}</td>
                    <td><strong style={{ color: "var(--color-success)" }}>{r.jobs_created}</strong></td>
                    <td>{r.duplicates_skipped}</td>
                    <td>{r.non_jobs_skipped}</td>
                    <td>
                      {r.error ? (
                        <span style={{ color: "var(--color-danger)", fontSize: "0.8rem", wordBreak: "break-all" }}>
                          {r.error}
                        </span>
                      ) : (
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="card modal-content" style={{ backgroundColor: "var(--bg-secondary)" }}>
            <div className="modal-header">
              <h3>{editingSource ? "Edit Discover Source" : "Add Discover Source"}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSave}>
              <div className="form-group">
                <label>Source Name</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  placeholder="e.g. Pune Python Jobs"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Source Type</label>
                <select
                  className="form-control"
                  value={type}
                  onChange={(e) => setType(e.target.value as any)}
                  disabled={!!editingSource}
                >
                  <option value="telegram">Telegram Channel/Group</option>
                  <option value="website">Static Job Board URL</option>
                </select>
              </div>

              {type === "telegram" && (
                <div className="form-group">
                  <label>Telegram Adapter Mode</label>
                  <select
                    className="form-control"
                    value={adapterMode}
                    onChange={(e) => setAdapterMode(e.target.value as any)}
                  >
                    <option value="public_web">Public Web Feed (No credentials)</option>
                    <option value="api">Private API (Telethon credentials)</option>
                  </select>
                </div>
              )}

              {type === "telegram" ? (
                <div className="form-group">
                  <label>Telegram Channel Identifier</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    placeholder="e.g. @reactjsjobs or reactjsjobs"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                  />
                  <small style={{ color: "var(--text-secondary)", marginTop: "0.25rem", display: "block" }}>
                    Include '@' for channels or public groups (e.g. @reactjsjobs).
                  </small>
                </div>
              ) : (
                <div className="form-group">
                  <label>Website Listing URL</label>
                  <input
                    type="url"
                    className="form-control"
                    required
                    placeholder="e.g. https://company.com/careers"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                </div>
              )}

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Source
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 4. PROFILE VIEW ──────────────────────────────────────────────────────────


function ProfileView() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    api.get<Profile>("/profile")
      .then(setProfile)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setSaving(true);
    setSuccessMsg("");
    setErrorMsg("");
    try {
      await api.put("/profile", profile);
      setSuccessMsg("Profile saved successfully");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Loading profile data...</div>;
  if (!profile) return <div className="alert alert-danger">Could not load profile.</div>;

  return (
    <div style={{ maxWidth: "800px" }}>
      <h2 style={{ marginBottom: "1.5rem" }}>Personal Information (Master Profile)</h2>
      {successMsg && <div className="alert alert-success" style={{ backgroundColor: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)", color: "#34d399", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>{successMsg}</div>}
      {errorMsg && <div className="alert alert-danger" style={{ marginBottom: "1rem" }}>{errorMsg}</div>}

      <div className="card">
        <form onSubmit={handleUpdate}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                className="form-control"
                required
                value={profile.name}
                onChange={(e) => setProfile({ ...profile, name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                className="form-control"
                required
                value={profile.degree_title}
                onChange={(e) => setProfile({ ...profile, degree_title: e.target.value })}
              />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                className="form-control"
                required
                value={profile.email}
                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Phone Number</label>
              <input
                type="text"
                className="form-control"
                required
                value={profile.phone}
                onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Location</label>
            <input
              type="text"
              className="form-control"
              required
              value={profile.location}
              onChange={(e) => setProfile({ ...profile, location: e.target.value })}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label>LinkedIn Profile URL</label>
              <input
                type="url"
                className="form-control"
                value={profile.linkedin}
                onChange={(e) => setProfile({ ...profile, linkedin: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>GitHub Profile URL</label>
              <input
                type="url"
                className="form-control"
                value={profile.github}
                onChange={(e) => setProfile({ ...profile, github: e.target.value })}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Professional Summary</label>
            <textarea
              className="form-control"
              style={{ minHeight: "150px" }}
              required
              value={profile.summary}
              onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1.5rem" }}>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Save Master Profile"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── 5. PROJECTS VIEW ─────────────────────────────────────────────────────────

function ProjectsView() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editProject, setEditProject] = useState<Project | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [year, setYear] = useState("");
  const [technologies, setTechnologies] = useState("");
  const [description, setDescription] = useState("");
  const [bullets, setBullets] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [priority, setPriority] = useState(1);
  const [opLoading, setOpLoading] = useState(false);

  const fetchProjects = () => {
    api.get<Project[]>("/projects")
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleOpenAdd = () => {
    setEditProject(null);
    setName("");
    setYear("");
    setTechnologies("");
    setDescription("");
    setBullets("");
    setEnabled(true);
    setPriority(1);
    setShowModal(true);
  };

  const handleOpenEdit = (p: Project) => {
    setEditProject(p);
    setName(p.name);
    setYear(p.year);
    setTechnologies(p.technologies.join(", "));
    setDescription(p.description);
    setBullets(p.resume_bullets.join("\n"));
    setEnabled(p.enabled);
    setPriority(p.priority);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOpLoading(true);

    const payload = {
      name,
      year,
      technologies: technologies.split(",").map((s) => s.trim()).filter((s) => s !== ""),
      description,
      resume_bullets: bullets.split("\n").map((s) => s.trim()).filter((s) => s !== ""),
      keywords: [],
      categories: [],
      enabled,
      priority: Number(priority),
    };

    try {
      if (editProject?._id) {
        await api.put(`/projects/${editProject._id}`, payload);
      } else {
        await api.post("/projects", payload);
      }
      fetchProjects();
      setShowModal(false);
    } catch (err) {
      console.error(err);
    } finally {
      setOpLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this project from your profile?")) return;
    try {
      await api.delete(`/projects/${id}`);
      fetchProjects();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2>Projects Inventory (Master Profile)</h2>
        <button className="btn btn-primary" onClick={handleOpenAdd}>
          + Add Project
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div>Loading projects...</div>
        ) : projects.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "2rem" }}>
            No projects added. Click **Add Project** to register your projects.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Year</th>
                  <th>Technologies</th>
                  <th>Priority</th>
                  <th>Enabled</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => (
                  <tr key={p._id}>
                    <td><strong>{p.name}</strong></td>
                    <td>{p.year}</td>
                    <td>{p.technologies.slice(0, 4).join(", ") + (p.technologies.length > 4 ? "..." : "")}</td>
                    <td>{p.priority}</td>
                    <td>
                      <span className={`badge ${p.enabled ? "badge-resume_ready" : "badge-new"}`}>
                        {p.enabled ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button className="btn btn-secondary" onClick={() => handleOpenEdit(p)}>
                          Edit
                        </button>
                        <button className="btn btn-danger" style={{ padding: "0.5rem" }} onClick={() => p._id && handleDelete(p._id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="card modal-content" style={{ maxWidth: "650px" }}>
            <div className="modal-header">
              <h3>{editProject ? "Edit Project" : "Add Project"}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                &times;
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}>
                <div className="form-group">
                  <label>Project Name*</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>Year*</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    placeholder="e.g. 2024"
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Technologies Used* (comma separated)</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  placeholder="e.g. Python, Flask, AWS Lambda"
                  value={technologies}
                  onChange={(e) => setTechnologies(e.target.value)}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div className="form-group">
                  <label>Sorting Priority (lower first)</label>
                  <input
                    type="number"
                    className="form-control"
                    value={priority}
                    onChange={(e) => setPriority(Number(e.target.value))}
                  />
                </div>
                <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1.75rem" }}>
                  <input
                    type="checkbox"
                    id="enabled"
                    checked={enabled}
                    onChange={(e) => setEnabled(e.target.checked)}
                  />
                  <label htmlFor="enabled" style={{ margin: 0, textTransform: "none", cursor: "pointer" }}>
                    Include on generic resume
                  </label>
                </div>
              </div>
              <div className="form-group">
                <label>Short Description*</label>
                <textarea
                  className="form-control"
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Resume Bullets (one bullet per line)</label>
                <textarea
                  className="form-control"
                  style={{ minHeight: "100px" }}
                  placeholder="e.g. Developed cloud backend APIs supporting 10k users..."
                  value={bullets}
                  onChange={(e) => setBullets(e.target.value)}
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={opLoading}>
                  {opLoading ? "Saving..." : "Save Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 6. SKILLS VIEW ───────────────────────────────────────────────────────────

function SkillsView() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Programming Languages");
  const [sortOrder, setSortOrder] = useState(1);
  const [opLoading, setOpLoading] = useState(false);

  const fetchSkills = () => {
    api.get<Skill[]>("/skills")
      .then(setSkills)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSkills();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim() === "") return;
    setOpLoading(true);
    try {
      await api.post("/skills", {
        name,
        category,
        sort_order: Number(sortOrder),
      });
      setName("");
      setSortOrder(sortOrder + 1);
      fetchSkills();
    } catch (err) {
      console.error(err);
    } finally {
      setOpLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this skill?")) return;
    try {
      await api.delete(`/skills/${id}`);
      fetchSkills();
    } catch (err) {
      console.error(err);
    }
  };

  // Group skills by category
  const categories: Record<string, Skill[]> = {};
  skills.forEach((s) => {
    if (!categories[s.category]) {
      categories[s.category] = [];
    }
    categories[s.category].push(s);
  });

  return (
    <div>
      <h2 style={{ marginBottom: "1.5rem" }}>Skills Inventory (Master Profile)</h2>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "2rem" }}>
        {/* Form add card */}
        <div>
          <div className="card">
            <h3 style={{ marginBottom: "1rem" }}>Add Skill</h3>
            <form onSubmit={handleAdd}>
              <div className="form-group">
                <label>Skill Name*</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  placeholder="e.g. Terraform"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Category*</label>
                <select className="form-control" value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="Programming Languages">Programming Languages</option>
                  <option value="Web Development">Web Development</option>
                  <option value="Databases">Databases</option>
                  <option value="AI/ML">AI/ML</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label>Order (priority)</label>
                <input
                  type="number"
                  className="form-control"
                  value={sortOrder}
                  onChange={(e) => setSortOrder(Number(e.target.value))}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: "100%", marginTop: "0.5rem" }} disabled={opLoading}>
                {opLoading ? "Saving..." : "Add Skill"}
              </button>
            </form>
          </div>
        </div>

        {/* Display Grouped list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {loading ? (
            <div>Loading skills list...</div>
          ) : Object.keys(categories).length === 0 ? (
            <div className="card" style={{ color: "var(--text-secondary)", textAlign: "center" }}>
              No skills added yet. Use the form on the left to add skills.
            </div>
          ) : (
            Object.keys(categories).map((catName) => (
              <div key={catName} className="card">
                <h3 style={{ marginBottom: "1rem", fontSize: "1.1rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.5rem" }}>
                  {catName}
                </h3>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {categories[catName].map((sk) => (
                    <span
                      key={sk.id}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        padding: "0.4rem 0.8rem",
                        backgroundColor: "rgba(255,255,255,0.05)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "30px",
                        fontSize: "0.85rem",
                      }}
                    >
                      {sk.name}
                      <button
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--color-danger)",
                          cursor: "pointer",
                          fontWeight: "bold",
                          lineHeight: 1,
                        }}
                        onClick={() => sk.id && handleDelete(sk.id)}
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ── 7. OTHER PROFILE SUB-COLLECTIONS VIEW (BOILERPLATE CRUD FOR EDUCATION/EXP) 

function ProfileSubcollectionsView({ section }: { section: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<any | null>(null);

  // Generic field states for non-education subcollections
  const [field1, setField1] = useState(""); // Company (exp) / Name (cert) / Language (lang) / Name (int)
  const [field2, setField2] = useState(""); // Role (exp) / Authority (cert) / Proficiency (lang)
  const [field3, setField3] = useState(""); // Location (exp) / Year (cert)
  const [field4, setField4] = useState(""); // Start Year (exp) / URL (cert)
  const [field5, setField5] = useState(""); // Bullets (exp)
  const [checkVal, setCheckVal] = useState(true); // Enabled (exp)

  // Dedicated education states (avoids hardcoded defaults, covers all Phase 1 fields)
  const [eduInstitution, setEduInstitution] = useState("");
  const [eduDegree, setEduDegree] = useState("");
  const [eduField, setEduField] = useState("");
  const [eduSpecialization, setEduSpecialization] = useState("");
  const [eduLocation, setEduLocation] = useState("");
  const [eduStartYear, setEduStartYear] = useState("");
  const [eduGradYear, setEduGradYear] = useState("");
  const [eduDetails, setEduDetails] = useState("");
  const [eduCGPA, setEduCGPA] = useState("");
  const [eduHSCScore, setEduHSCScore] = useState("");
  const [eduHSCYear, setEduHSCYear] = useState("");
  const [eduSSCScore, setEduSSCScore] = useState("");
  const [eduSSCYear, setEduSSCYear] = useState("");

  const fetchItems = () => {
    api.get<any[]>(`/${section}`)
      .then(setItems)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchItems();
  }, [section]);

  const handleOpenAdd = () => {
    setEditingItem(null);
    // Reset education-specific states
    setEduInstitution(""); setEduDegree(""); setEduField(""); setEduSpecialization("");
    setEduLocation(""); setEduStartYear(""); setEduGradYear(""); setEduDetails("");
    setEduCGPA(""); setEduHSCScore(""); setEduHSCYear(""); setEduSSCScore(""); setEduSSCYear("");
    // Reset generic states
    setField1("");
    setField2("");
    setField3("");
    setField4("");
    setField5("");
    setCheckVal(true);
    setShowModal(true);
  };

  const handleOpenEdit = (item: any) => {
    setEditingItem(item);
    if (section === "education") {
      setEduInstitution(item.institution || "");
      setEduDegree(item.degree || "");
      setEduField(item.field || "");
      setEduSpecialization(item.specialization || "");
      setEduLocation(item.location || "");
      setEduStartYear(String(item.start_year || ""));
      setEduGradYear(String(item.graduation_year || ""));
      setEduDetails(item.details ? item.details.join("\n") : "");
      setEduCGPA(item.cgpa != null ? String(item.cgpa) : "");
      setEduHSCScore(item.hsc_score != null ? String(item.hsc_score) : "");
      setEduHSCYear(item.hsc_year != null ? String(item.hsc_year) : "");
      setEduSSCScore(item.ssc_score != null ? String(item.ssc_score) : "");
      setEduSSCYear(item.ssc_year != null ? String(item.ssc_year) : "");
    } else if (section === "experience") {
      setField1(item.company || "");
      setField2(item.role || "");
      setField3(item.location || "");
      setField4(String(item.start_year || ""));
      setField5(item.bullets ? item.bullets.join("\n") : "");
      setCheckVal(item.enabled);
    } else if (section === "certifications") {
      setField1(item.name || "");
      setField2(item.authority || "");
      setField3(String(item.year || ""));
      setField4(item.url || "");
    } else if (section === "languages") {
      setField1(item.language || "");
      setField2(item.proficiency || "");
    } else if (section === "interests") {
      setField1(item.name || "");
    }
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    let payload: any = {};
    if (section === "education") {
      payload = {
        institution: eduInstitution,
        degree: eduDegree,
        field: eduField,
        specialization: eduSpecialization,
        location: eduLocation,
        start_year: Number(eduStartYear) || 0,
        graduation_year: eduGradYear ? Number(eduGradYear) : null,
        details: eduDetails.split("\n").map((s) => s.trim()).filter((s) => s !== ""),
        cgpa: eduCGPA !== "" ? Number(eduCGPA) : null,
        hsc_score: eduHSCScore !== "" ? Number(eduHSCScore) : null,
        hsc_year: eduHSCYear !== "" ? Number(eduHSCYear) : null,
        ssc_score: eduSSCScore !== "" ? Number(eduSSCScore) : null,
        ssc_year: eduSSCYear !== "" ? Number(eduSSCYear) : null,
      };
    } else if (section === "experience") {
      payload = {
        company: field1,
        role: field2,
        location: field3,
        start_year: Number(field4),
        end_year: null,
        description: "",
        bullets: field5.split("\n").map((s) => s.trim()).filter((s) => s !== ""),
        enabled: checkVal,
      };
    } else if (section === "certifications") {
      payload = {
        name: field1,
        authority: field2,
        year: Number(field3),
        url: field4,
      };
    } else if (section === "languages") {
      payload = {
        language: field1,
        proficiency: field2,
      };
    } else if (section === "interests") {
      payload = {
        name: field1,
      };
    }

    try {
      if (editingItem?.id) {
        await api.put(`/${section}/${editingItem.id}`, payload);
      } else {
        await api.post(`/${section}`, payload);
      }
      fetchItems();
      setShowModal(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Delete this ${section} item?`)) return;
    try {
      await api.delete(`/${section}/${id}`);
      fetchItems();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2 style={{ textTransform: "capitalize" }}>{section} (Master Profile)</h2>
        <button className="btn btn-primary" onClick={handleOpenAdd}>
          + Add Item
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div>Loading list...</div>
        ) : items.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "2rem" }}>
            No records in this category. Click **Add Item** to populate.
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
              {section === "education" && (
                  <tr>
                    <th>Institution</th>
                    <th>Degree</th>
                    <th>CGPA</th>
                    <th>Start Year</th>
                    <th>Graduation Year</th>
                    <th>Actions</th>
                  </tr>
                )}
                {section === "experience" && (
                  <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Location</th>
                    <th>Active</th>
                    <th>Actions</th>
                  </tr>
                )}
                {section === "certifications" && (
                  <tr>
                    <th>Name</th>
                    <th>Authority</th>
                    <th>Year</th>
                    <th>URL</th>
                    <th>Actions</th>
                  </tr>
                )}
                {section === "languages" && (
                  <tr>
                    <th>Language</th>
                    <th>Proficiency</th>
                    <th>Actions</th>
                  </tr>
                )}
                {section === "interests" && (
                  <tr>
                    <th>Interest</th>
                    <th>Actions</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    {section === "education" && (
                      <>
                        <td><strong>{item.institution}</strong></td>
                        <td>{item.degree}</td>
                        <td>{item.cgpa != null ? item.cgpa : "—"}</td>
                        <td>{item.start_year}</td>
                        <td>{item.graduation_year || "Present"}</td>
                      </>
                    )}
                    {section === "experience" && (
                      <>
                        <td><strong>{item.company}</strong></td>
                        <td>{item.role}</td>
                        <td>{item.location}</td>
                        <td>
                          <span className={`badge ${item.enabled ? "badge-resume_ready" : "badge-new"}`}>
                            {item.enabled ? "Active" : "Disabled"}
                          </span>
                        </td>
                      </>
                    )}
                    {section === "certifications" && (
                      <>
                        <td><strong>{item.name}</strong></td>
                        <td>{item.authority}</td>
                        <td>{item.year}</td>
                        <td>
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noopener noreferrer">
                              View Link
                            </a>
                          ) : (
                            "-"
                          )}
                        </td>
                      </>
                    )}
                    {section === "languages" && (
                      <>
                        <td><strong>{item.language}</strong></td>
                        <td>{item.proficiency}</td>
                      </>
                    )}
                    {section === "interests" && (
                      <>
                        <td><strong>{item.name}</strong></td>
                      </>
                    )}
                    <td>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button className="btn btn-secondary" onClick={() => handleOpenEdit(item)}>
                          Edit
                        </button>
                        <button className="btn btn-danger" style={{ padding: "0.5rem" }} onClick={() => item.id && handleDelete(item.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="card modal-content">
            <div className="modal-header">
              <h3 style={{ textTransform: "capitalize" }}>
                {editingItem ? "Edit " : "Add "} {section}
              </h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                &times;
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              {section === "education" && (
                <>
                  <div className="form-group">
                    <label>Institution Name*</label>
                    <input id="edu-institution" type="text" className="form-control" required value={eduInstitution} onChange={(e) => setEduInstitution(e.target.value)} placeholder="e.g. MIT" />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>Degree*</label>
                      <input id="edu-degree" type="text" className="form-control" required value={eduDegree} onChange={(e) => setEduDegree(e.target.value)} placeholder="e.g. Bachelor of Engineering" />
                    </div>
                    <div className="form-group">
                      <label>Field of Study</label>
                      <input id="edu-field" type="text" className="form-control" value={eduField} onChange={(e) => setEduField(e.target.value)} placeholder="e.g. Computer Science" />
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>Specialization</label>
                      <input id="edu-specialization" type="text" className="form-control" value={eduSpecialization} onChange={(e) => setEduSpecialization(e.target.value)} placeholder="e.g. Artificial Intelligence" />
                    </div>
                    <div className="form-group">
                      <label>Location</label>
                      <input id="edu-location" type="text" className="form-control" value={eduLocation} onChange={(e) => setEduLocation(e.target.value)} placeholder="e.g. Mumbai" />
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>Start Year*</label>
                      <input id="edu-start-year" type="number" className="form-control" required value={eduStartYear} onChange={(e) => setEduStartYear(e.target.value)} placeholder="2019" />
                    </div>
                    <div className="form-group">
                      <label>Graduation Year (blank = Present)</label>
                      <input id="edu-grad-year" type="number" className="form-control" value={eduGradYear} onChange={(e) => setEduGradYear(e.target.value)} placeholder="2023" />
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>CGPA (out of 10)</label>
                      <input id="edu-cgpa" type="number" step="0.01" min="0" max="10" className="form-control" value={eduCGPA} onChange={(e) => setEduCGPA(e.target.value)} placeholder="8.50" />
                    </div>
                    <div className="form-group">
                      <label>HSC Score (%)</label>
                      <input id="edu-hsc-score" type="number" step="0.01" min="0" max="100" className="form-control" value={eduHSCScore} onChange={(e) => setEduHSCScore(e.target.value)} placeholder="85.60" />
                    </div>
                    <div className="form-group">
                      <label>HSC Year</label>
                      <input id="edu-hsc-year" type="number" className="form-control" value={eduHSCYear} onChange={(e) => setEduHSCYear(e.target.value)} placeholder="2019" />
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>SSC Score (%)</label>
                      <input id="edu-ssc-score" type="number" step="0.01" min="0" max="100" className="form-control" value={eduSSCScore} onChange={(e) => setEduSSCScore(e.target.value)} placeholder="92.20" />
                    </div>
                    <div className="form-group">
                      <label>SSC Year</label>
                      <input id="edu-ssc-year" type="number" className="form-control" value={eduSSCYear} onChange={(e) => setEduSSCYear(e.target.value)} placeholder="2017" />
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Details / Bullets (one per line)</label>
                    <textarea id="edu-details" className="form-control" value={eduDetails} onChange={(e) => setEduDetails(e.target.value)} placeholder="e.g. CGPA: 8.5/10&#10;HSC: 85.60% (2019)" />
                  </div>
                </>
              )}

              {section === "experience" && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>Company Name*</label>
                      <input type="text" className="form-control" required value={field1} onChange={(e) => setField1(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label>Role*</label>
                      <input type="text" className="form-control" required value={field2} onChange={(e) => setField2(e.target.value)} />
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>Location</label>
                      <input type="text" className="form-control" value={field3} onChange={(e) => setField3(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label>Start Year*</label>
                      <input type="number" className="form-control" required value={field4} onChange={(e) => setField4(e.target.value)} />
                    </div>
                  </div>
                  <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <input type="checkbox" id="enabled-exp" checked={checkVal} onChange={(e) => setCheckVal(e.target.checked)} />
                    <label htmlFor="enabled-exp" style={{ margin: 0, textTransform: "none", cursor: "pointer" }}>
                      Include on generic resume
                    </label>
                  </div>
                  <div className="form-group" style={{ marginTop: "1rem" }}>
                    <label>Bullets (one per line)</label>
                    <textarea className="form-control" value={field5} onChange={(e) => setField5(e.target.value)} />
                  </div>
                </>
              )}

              {section === "certifications" && (
                <>
                  <div className="form-group">
                    <label>Certification Name*</label>
                    <input type="text" className="form-control" required value={field1} onChange={(e) => setField1(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Issuing Authority*</label>
                    <input type="text" className="form-control" required value={field2} onChange={(e) => setField2(e.target.value)} />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "1rem" }}>
                    <div className="form-group">
                      <label>Year*</label>
                      <input type="number" className="form-control" required value={field3} onChange={(e) => setField3(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label>Certificate URL</label>
                      <input type="url" className="form-control" value={field4} onChange={(e) => setField4(e.target.value)} />
                    </div>
                  </div>
                </>
              )}

              {section === "languages" && (
                <>
                  <div className="form-group">
                    <label>Language Name*</label>
                    <input type="text" className="form-control" required placeholder="e.g. English" value={field1} onChange={(e) => setField1(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>Proficiency*</label>
                    <input type="text" className="form-control" required placeholder="e.g. Full Professional / Native" value={field2} onChange={(e) => setField2(e.target.value)} />
                  </div>
                </>
              )}

              {section === "interests" && (
                <>
                  <div className="form-group">
                    <label>Interest Name*</label>
                    <input type="text" className="form-control" required placeholder="e.g. Cloud Security" value={field1} onChange={(e) => setField1(e.target.value)} />
                  </div>
                </>
              )}

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── APPLICATIONS LIST VIEW ──────────────────────────────────────────────────

function ApplicationsListView({ navigateTo }: { navigateTo: (hash: string) => void }) {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Submit confirmation modal state
  const [submittingAppId, setSubmittingAppId] = useState<string | null>(null);
  const [confirmingSubmit, setConfirmingSubmit] = useState(false);
  const [submitNotes, setSubmitNotes] = useState("");

  const fetchApplications = async () => {
    setLoading(true);
    setError("");
    try {
      let path = "/applications";
      if (statusFilter !== "ALL") {
        path += `?status=${encodeURIComponent(statusFilter)}`;
      }
      const data = await api.get<Application[]>(path);
      setApps(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load applications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [statusFilter]);

  const handleOpenURL = async (app: Application, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.post(`/applications/${app.id}/open`, {});
      if (app.application_url) {
        window.open(app.application_url, "_blank", "noopener,noreferrer");
      }
      fetchApplications();
    } catch (err: any) {
      alert(err.message || "Error opening application URL");
    }
  };

  const triggerSubmitModal = (appId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSubmittingAppId(appId);
    setSubmitNotes("");
  };

  const handleConfirmSubmit = async () => {
    if (!submittingAppId) return;
    setConfirmingSubmit(true);
    try {
      await api.post(`/applications/${submittingAppId}/submit`, { confirmation: true, notes: submitNotes });
      setSubmittingAppId(null);
      fetchApplications();
    } catch (err: any) {
      alert(`Submit failed: ${err.message}`);
    } finally {
      setConfirmingSubmit(false);
    }
  };


  const filteredApps = apps.filter((a) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return a.company.toLowerCase().includes(q) || a.job_title.toLowerCase().includes(q);
  });

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Applications Tracker</h2>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Manage application prep, resume packages, and submission lifecycle</p>
        </div>
        <button className="btn btn-secondary" onClick={fetchApplications}>
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {/* Filters Toolbar */}
      <div className="card" style={{ marginBottom: "1.5rem", padding: "1rem" }}>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ flex: 1, minWidth: "200px" }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search by company or role title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div>
            <select className="form-control" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="ALL">All Statuses</option>
              <option value="DISCOVERED">DISCOVERED</option>
              <option value="ANALYZED">ANALYZED</option>
              <option value="MATCHED">MATCHED</option>
              <option value="RESUME_GENERATED">RESUME_GENERATED</option>
              <option value="READY_TO_APPLY">READY_TO_APPLY</option>
              <option value="APPLICATION_STARTED">APPLICATION_STARTED</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="INTERVIEW">INTERVIEW</option>
              <option value="OFFER">OFFER</option>
              <option value="REJECTED">REJECTED</option>
              <option value="WITHDRAWN">WITHDRAWN</option>
            </select>
          </div>
        </div>
      </div>

      {/* Applications Table */}
      {loading ? (
        <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
          Loading applications...
        </div>
      ) : filteredApps.length === 0 ? (
        <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
          No applications found. You can create applications directly from Job Opportunities or Job Pipeline!
        </div>
      ) : (
        <div className="card table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Status</th>
                <th>Match Score</th>
                <th>Resume</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredApps.map((a) => (
                <tr key={a.id} style={{ cursor: "pointer" }} onClick={() => navigateTo(`#/applications/${a.id}`)}>
                  <td>
                    <strong>{a.company}</strong>
                  </td>
                  <td>{a.job_title}</td>
                  <td>
                    <span className={`badge ${a.status === "SUBMITTED" ? "badge-applied" : a.status === "READY_TO_APPLY" ? "badge-analyzed" : "badge-secondary"}`}>
                      {a.status}
                    </span>
                  </td>
                  <td>{a.match_score > 0 ? `${a.match_score.toFixed(1)}%` : "N/A"}</td>
                  <td>
                    {a.resume_path ? (
                      <span className="badge badge-success">Generated</span>
                    ) : (
                      <span className="badge badge-secondary">Pending</span>
                    )}
                  </td>
                  <td>{new Date(a.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: "0.5rem" }} onClick={(e) => e.stopPropagation()}>
                      <button className="btn btn-sm btn-primary" onClick={() => navigateTo(`#/applications/${a.id}`)}>
                        Details
                      </button>
                      {a.status !== "SUBMITTED" && a.application_url && (
                        <button className="btn btn-sm btn-outline" onClick={(e) => handleOpenURL(a, e)}>
                          Open Portal
                        </button>
                      )}
                      {a.status !== "SUBMITTED" && (
                        <button className="btn btn-sm btn-success" onClick={(e) => triggerSubmitModal(a.id, e)}>
                          Mark Submitted
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Submit Confirmation Modal */}
      {submittingAppId && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "450px" }}>
            <h3 style={{ marginTop: 0 }}>Confirm Application Submission</h3>
            <p style={{ color: "var(--text-muted)" }}>
              <strong>Did you actually submit this application on the portal?</strong>
            </p>
            <div className="alert alert-warning">
              This action will mark the application state as <strong>SUBMITTED</strong> and lock manual status updates.
            </div>
            <div className="form-group">
              <label>Submission Notes (Optional)</label>
              <textarea
                className="form-control"
                placeholder="e.g. Submitted via company portal. Confirmation #12345"
                value={submitNotes}
                onChange={(e) => setSubmitNotes(e.target.value)}
              />
            </div>
            <div className="modal-footer" style={{ marginTop: "1.5rem" }}>
              <button className="btn btn-secondary" onClick={() => setSubmittingAppId(null)} disabled={confirmingSubmit}>
                Cancel
              </button>
              <button className="btn btn-success" onClick={handleConfirmSubmit} disabled={confirmingSubmit}>
                {confirmingSubmit ? "Submitting..." : "Yes, I Submitted This Application"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── APPLICATION DETAIL PAGE ──────────────────────────────────────────────────

function ApplicationDetailPage({ applicationId, navigateTo }: { applicationId: string; navigateTo: (hash: string) => void }) {
  const [app, setApp] = useState<Application | null>(null);
  const [events, setEvents] = useState<ApplicationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // Notes state
  const [newNote, setNewNote] = useState("");
  const [submittingNote, setSubmittingNote] = useState(false);

  // Status update state
  const [statusInput, setStatusInput] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Confirmation Modal State
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmNotes, setConfirmNotes] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const [appData, eventsData] = await Promise.all([
        api.get<Application>(`/applications/${applicationId}`),
        api.get<ApplicationEvent[]>(`/applications/${applicationId}/events`),
      ]);
      setApp(appData);
      setStatusInput(appData.status);
      setEvents(eventsData || []);
    } catch (err: any) {
      setError(err.message || "Failed to load application details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [applicationId]);

  // Auto-poll when resume generation or task is in progress
  useEffect(() => {
    let interval: any = null;
    if (app && app.status === "RESUME_GENERATING") {
      interval = setInterval(() => {
        fetchData();
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [app?.status, applicationId]);


  const handlePrepare = async () => {
    setActionLoading(true);
    try {
      await api.post(`/applications/${applicationId}/prepare`, {});
      alert("Application package prepared and validated!");
      fetchData();
    } catch (err: any) {
      alert(`Preparation error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenerateResume = async () => {
    setActionLoading(true);
    try {
      await api.post(`/applications/${applicationId}/generate-resume`, {});
      alert("Tailored resume generation queued in background!");
      fetchData();
    } catch (err: any) {
      alert(`Resume generation error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenPortal = async () => {
    try {
      await api.post(`/applications/${applicationId}/open`, {});
      if (app?.application_url) {
        window.open(app.application_url, "_blank", "noopener,noreferrer");
      }
      fetchData();
    } catch (err: any) {
      alert("Failed to record opening application URL");
    }
  };

  const handleConfirmSubmit = async () => {
    setActionLoading(true);
    try {
      await api.post(`/applications/${applicationId}/submit`, { confirmation: true, notes: confirmNotes });
      setShowConfirmModal(false);
      fetchData();
    } catch (err: any) {
      alert(`Submit error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStatusChange = async () => {
    setUpdatingStatus(true);
    try {
      await api.patch(`/applications/${applicationId}/status`, { status: statusInput });
      fetchData();
    } catch (err: any) {
      alert(`Status update error: ${err.message}`);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    setSubmittingNote(true);
    try {
      await api.post(`/applications/${applicationId}/notes`, { notes: newNote });
      setNewNote("");
      fetchData();
    } catch (err: any) {
      alert(`Add note error: ${err.message}`);
    } finally {
      setSubmittingNote(false);
    }
  };


  if (loading) {
    return (
      <div className="view-container">
        <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
          Loading application details...
        </div>
      </div>
    );
  }

  if (error || !app) {
    return (
      <div className="view-container">
        <button className="btn btn-secondary" onClick={() => navigateTo("#/applications")}>
          &larr; Back to Applications
        </button>
        <div className="alert alert-danger" style={{ marginTop: "1rem" }}>
          {error || "Application not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="view-container">
      <div style={{ marginBottom: "1rem" }}>
        <button className="btn btn-secondary" onClick={() => navigateTo("#/applications")}>
          &larr; Back to Applications
        </button>
      </div>

      <div className="view-header">
        <div>
          <h2>
            {app.company} — {app.job_title}
          </h2>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Application ID: {app.id}</p>
        </div>
        <div>
          <span className={`badge ${app.status === "SUBMITTED" ? "badge-applied" : "badge-analyzed"}`} style={{ fontSize: "1rem", padding: "0.5rem 1rem" }}>
            {app.status}
          </span>
        </div>
      </div>

      {/* Action Controls Bar */}
      <div className="card" style={{ marginBottom: "1.5rem", padding: "1rem" }}>
        <h4 style={{ marginTop: 0, marginBottom: "1rem" }}>Pipeline Action Panel</h4>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
          <button className="btn btn-outline" onClick={handlePrepare} disabled={actionLoading || app.status === "SUBMITTED"}>
            Prepare Package
          </button>
          <button className="btn btn-primary" onClick={handleGenerateResume} disabled={actionLoading || app.status === "SUBMITTED"}>
            Generate Tailored Resume
          </button>
          {app.application_url && (
            <button className="btn btn-outline" onClick={handleOpenPortal} disabled={actionLoading}>
              Open Portal URL
            </button>
          )}
          {app.status !== "SUBMITTED" && (
            <button className="btn btn-success" onClick={() => setShowConfirmModal(true)} disabled={actionLoading}>
              Mark as Submitted
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem" }}>
        {/* Main Details */}
        <div>
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3>Application Information</h3>
            <table className="table" style={{ marginTop: "1rem" }}>
              <tbody>
                <tr>
                  <td>
                    <strong>Company</strong>
                  </td>
                  <td>{app.company}</td>
                </tr>
                <tr>
                  <td>
                    <strong>Role / Title</strong>
                  </td>
                  <td>{app.job_title}</td>
                </tr>
                <tr>
                  <td>
                    <strong>Match Score</strong>
                  </td>
                  <td>
                    {app.match_score > 0 ? (
                      <span className="badge badge-success" style={{ fontSize: "0.9rem" }}>
                        {app.match_score.toFixed(1)}% Score
                      </span>
                    ) : (
                      "Not scored yet"
                    )}
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>Application URL</strong>
                  </td>
                  <td>
                    {app.application_url ? (
                      <a href={app.application_url} target="_blank" rel="noopener noreferrer" style={{ wordBreak: "break-all" }}>
                        {app.application_url}
                      </a>
                    ) : (
                      <span style={{ color: "var(--danger-color)" }}>No URL provided</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>Source</strong>
                  </td>
                  <td>
                    {app.source?.name || "Ingested Source"} ({app.source?.type || "feed"})
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>Created At</strong>
                  </td>
                  <td>{new Date(app.created_at).toLocaleString()}</td>
                </tr>
                {app.submitted_at && (
                  <tr>
                    <td>
                      <strong>Submitted At</strong>
                    </td>
                    <td>{new Date(app.submitted_at).toLocaleString()}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Tailored Resume Package Card */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3>Tailored Resume Package</h3>
            {app.resume_path ? (
              <div style={{ marginTop: "1rem" }}>
                <p>
                  <strong>Resume File:</strong> <code>{app.resume_filename || "resume.pdf"}</code>
                </p>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Path: {app.resume_path}</p>
                {app.resume_generated_at && (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                    Generated at: {new Date(app.resume_generated_at).toLocaleString()}
                  </p>
                )}
                {app.job_id && (
                  <a href={api.getResumePDFURL(app.job_id)} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
                    Download Tailored PDF
                  </a>
                )}

              </div>
            ) : (
              <div style={{ marginTop: "1rem", color: "var(--text-muted)" }}>
                No tailored resume has been generated yet for this application. Click <strong>Generate Tailored Resume</strong> to produce a customized PDF!
              </div>
            )}
          </div>

          {/* Notes Section */}
          <div className="card">
            <h3>Notes & Documentation</h3>
            {app.notes ? (
              <pre
                style={{
                  background: "var(--bg-secondary)",
                  padding: "1rem",
                  borderRadius: "6px",
                  whiteSpace: "pre-wrap",
                  fontFamily: "inherit",
                }}
              >
                {app.notes}
              </pre>
            ) : (
              <p style={{ color: "var(--text-muted)" }}>No notes added yet.</p>
            )}

            <form onSubmit={handleAddNote} style={{ marginTop: "1rem" }}>
              <div className="form-group">
                <textarea
                  className="form-control"
                  placeholder="Add a new note..."
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn-secondary btn-sm" disabled={submittingNote}>
                {submittingNote ? "Saving..." : "Add Note"}
              </button>
            </form>
          </div>
        </div>

        {/* Sidebar: Status & Event History */}
        <div>
          {/* Status Update Card */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h4>Update Status</h4>
            <div className="form-group">
              <select className="form-control" value={statusInput} onChange={(e) => setStatusInput(e.target.value)}>
                <option value="DISCOVERED">DISCOVERED</option>
                <option value="ANALYZED">ANALYZED</option>
                <option value="MATCHED">MATCHED</option>
                <option value="RESUME_GENERATED">RESUME_GENERATED</option>
                <option value="READY_TO_APPLY">READY_TO_APPLY</option>
                <option value="APPLICATION_STARTED">APPLICATION_STARTED</option>
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="INTERVIEW">INTERVIEW</option>
                <option value="OFFER">OFFER</option>
                <option value="REJECTED">REJECTED</option>
                <option value="WITHDRAWN">WITHDRAWN</option>
              </select>
            </div>
            <button className="btn btn-primary btn-sm" style={{ width: "100%" }} onClick={handleStatusChange} disabled={updatingStatus}>
              {updatingStatus ? "Updating..." : "Update Status"}
            </button>
          </div>

          {/* Audit Event History Card */}
          <div className="card">
            <h4>Audit Event History</h4>
            {events.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No recorded events yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
                {events.map((evt) => (
                  <div
                    key={evt.id}
                    style={{
                      padding: "0.75rem",
                      background: "var(--bg-secondary)",
                      borderRadius: "6px",
                      borderLeft: "3px solid var(--accent-color)",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{evt.event}</div>
                    {evt.from && evt.to && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        {evt.from} &rarr; {evt.to}
                      </div>
                    )}
                    {evt.notes && <div style={{ fontSize: "0.8rem", marginTop: "0.25rem" }}>{evt.notes}</div>}
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                      {new Date(evt.timestamp).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: "450px" }}>
            <h3 style={{ marginTop: 0 }}>Confirm Application Submission</h3>
            <p style={{ color: "var(--text-muted)" }}>
              Did you actually submit this application on the portal for <strong>{app.company}</strong>?
            </p>
            <div className="form-group">
              <label>Submission Confirmation Notes</label>
              <textarea
                className="form-control"
                placeholder="e.g. Confirmed submission via portal"
                value={confirmNotes}
                onChange={(e) => setConfirmNotes(e.target.value)}
              />
            </div>
            <div className="modal-footer" style={{ marginTop: "1.5rem" }}>
              <button className="btn btn-secondary" onClick={() => setShowConfirmModal(false)} disabled={actionLoading}>
                Cancel
              </button>
              <button className="btn btn-success" onClick={handleConfirmSubmit} disabled={actionLoading}>
                {actionLoading ? "Submitting..." : "Yes, Mark as Submitted"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

