// ============================================================
// PLACEME - INTELLIGENT PLACEMENT PLATFORM
// Complete React Frontend Application
// ============================================================

const { useState, useEffect, createContext, useContext, useRef } = React;
const API = '/api';

// ============================================================
// CONTEXT PROVIDERS
// ============================================================

const AuthContext = createContext(null);
const ToastContext = createContext(null);
const useAuth = () => useContext(AuthContext);
const useToast = () => useContext(ToastContext);

const decodeJWT = (token) => {
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch { return null; }
};

const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('token'));
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (token) {
            const decoded = decodeJWT(token);
            if (decoded && decoded.exp * 1000 > Date.now()) {
                setUser({ ...decoded, token });
            } else { logout(); }
        }
        setLoading(false);
    }, []);

    const login = async (email, password) => {
        const res = await fetch(`${API}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Login failed');
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setUser({ ...decodeJWT(data.access_token), ...data, token: data.access_token });
        return data;
    };

    const register = async (email, password, role) => {
        const res = await fetch(`${API}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, role })
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Registration failed');
        return res.json();
    };

    const logout = () => { localStorage.removeItem('token'); setToken(null); setUser(null); };

    const authFetch = async (url, options = {}) => {
        const headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
        if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
        const res = await fetch(url, { ...options, headers });
        if (res.status === 401) { logout(); throw new Error('Session expired'); }
        return res;
    };

    return (<AuthContext.Provider value={{ user, token, login, register, logout, authFetch, loading }}>{children}</AuthContext.Provider>);
};

const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);
    const toast = (message, type = 'info') => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
    };
    const colors = { success: 'bg-green-500', error: 'bg-red-500', warning: 'bg-amber-500', info: 'bg-blue-500' };
    return (
        <ToastContext.Provider value={toast}>
            {children}
            <div className="fixed top-4 right-4 z-50 space-y-2">
                {toasts.map(t => (<div key={t.id} className={`toast px-5 py-3 rounded-xl text-white shadow-lg ${colors[t.type]}`}>{t.message}</div>))}
            </div>
        </ToastContext.Provider>
    );
};

// ============================================================
// REUSABLE COMPONENTS
// ============================================================

const Spinner = ({ size = 'md' }) => {
    const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' };
    return <div className={`${sizes[size]} border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin`} />;
};

const Button = ({ children, onClick, variant = 'primary', disabled, loading, className = '', type = 'button' }) => {
    const variants = { primary: 'btn-primary text-white', secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200', outline: 'border-2 border-blue-600 text-blue-600 hover:bg-blue-50', danger: 'bg-red-500 text-white hover:bg-red-600', success: 'bg-emerald-500 text-white hover:bg-emerald-600' };
    return (<button type={type} onClick={onClick} disabled={disabled || loading} className={`px-5 py-2.5 rounded-xl font-medium transition-all flex items-center justify-center gap-2 ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>{loading && <Spinner size="sm" />}{children}</button>);
};

const Input = ({ label, error, icon, className = '', ...props }) => (
    <div className="space-y-1.5">
        {label && <label className="block text-sm font-medium text-gray-700">{label}</label>}
        <div className="relative">
            {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">{icon}</div>}
            <input {...props} className={`w-full px-4 py-3 ${icon ? 'pl-11' : ''} border border-gray-200 rounded-xl input-styled outline-none transition-all ${error ? 'border-red-400' : ''} ${className}`} />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
);

const Card = ({ children, className = '', hover = false }) => (<div className={`bg-white rounded-2xl shadow-sm border border-gray-100 ${hover ? 'card-lift cursor-pointer' : ''} ${className}`}>{children}</div>);

const Badge = ({ children, variant = 'default' }) => {
    const variants = { default: 'bg-gray-100 text-gray-700', primary: 'bg-blue-100 text-blue-700', success: 'bg-emerald-100 text-emerald-700', warning: 'bg-amber-100 text-amber-700', danger: 'bg-red-100 text-red-700', purple: 'bg-purple-100 text-purple-700' };
    return <span className={`px-3 py-1 rounded-full text-xs font-semibold ${variants[variant]}`}>{children}</span>;
};

const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade" onClick={onClose}>
            <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[85vh] overflow-auto animate-slide-up" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between p-5 border-b">
                    <h3 className="text-xl font-bold">{title}</h3>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                </div>
                <div className="p-5">{children}</div>
            </div>
        </div>
    );
};

const StatCard = ({ title, value, icon, color = 'blue', subtitle }) => {
    const colors = { blue: 'from-blue-500 to-blue-600', green: 'from-emerald-500 to-emerald-600', purple: 'from-purple-500 to-purple-600', amber: 'from-amber-500 to-amber-600' };
    return (<Card className="p-5" hover><div className="flex items-start justify-between"><div><p className="text-sm text-gray-500 mb-1">{title}</p><p className="text-3xl font-bold text-gray-900">{value}</p>{subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}</div><div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colors[color]} flex items-center justify-center text-white shadow-lg`}>{icon}</div></div></Card>);
};

const Navbar = () => {
    const { user, logout } = useAuth();
    return (
        <nav className="glass sticky top-0 z-40 border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16 items-center">
                    <a href="#" className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg"><svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg></div>
                        <span className="text-xl font-bold font-display text-gray-900">PlaceMe</span>
                    </a>
                    {user && (
                        <div className="flex items-center gap-4">
                            <div className="hidden sm:flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-xl">
                                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-medium">{user.email?.[0]?.toUpperCase()}</div>
                                <div className="text-left"><p className="text-sm font-medium text-gray-900 truncate max-w-[150px]">{user.email}</p><p className="text-xs text-gray-500 capitalize">{user.role}</p></div>
                            </div>
                            <Button variant="secondary" onClick={logout} className="!px-4"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg></Button>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    );
};

const Sidebar = ({ items, active, onSelect }) => (
    <aside className="w-64 bg-white border-r min-h-[calc(100vh-4rem)] p-4 hidden lg:block">
        <nav className="space-y-1">
            {items.map(item => (<button key={item.id} onClick={() => onSelect(item.id)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-left ${active === item.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}>{item.icon}{item.label}</button>))}
        </nav>
    </aside>
);

// ============================================================
// AUTH PAGES
// ============================================================

const AuthPage = () => {
    const [isLogin, setIsLogin] = useState(true);
    return isLogin ? <LoginForm onSwitch={() => setIsLogin(false)} /> : <RegisterForm onSwitch={() => setIsLogin(true)} />;
};

const LoginForm = ({ onSwitch }) => {
    const { login } = useAuth();
    const toast = useToast();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try { await login(email, password); toast('Welcome back!', 'success'); }
        catch (err) { toast(err.message, 'error'); }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex">
            <div className="hidden lg:flex lg:w-1/2 gradient-hero items-center justify-center p-12">
                <div className="max-w-lg text-white animate-fade">
                    <h1 className="text-5xl font-display font-bold mb-6 leading-tight">Your Career Journey Starts Here</h1>
                    <p className="text-xl opacity-90 mb-8 leading-relaxed">AI-powered placement platform connecting talented students with leading companies.</p>
                    <div className="grid grid-cols-3 gap-4">
                        {[{ num: '500+', label: 'Companies' }, { num: '10K+', label: 'Students' }, { num: '95%', label: 'Placement Rate' }].map((stat, i) => (<div key={i} className="bg-white/10 rounded-xl p-4 backdrop-blur"><div className="text-2xl font-bold">{stat.num}</div><div className="text-sm opacity-80">{stat.label}</div></div>))}
                    </div>
                </div>
            </div>
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 gradient-mesh">
                <div className="max-w-md w-full animate-slide-up">
                    <div className="text-center mb-8">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center mx-auto mb-4 shadow-lg"><svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg></div>
                        <h2 className="text-3xl font-display font-bold text-gray-900">Welcome Back</h2>
                        <p className="text-gray-500 mt-2">Sign in to continue your journey</p>
                    </div>
                    <Card className="p-8">
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <Input label="Email Address" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required />
                            <Input label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
                            <Button type="submit" loading={loading} className="w-full">Sign In</Button>
                        </form>
                    </Card>
                    <p className="text-center mt-6 text-gray-500">New here? <button onClick={onSwitch} className="text-blue-600 font-semibold hover:underline">Create account</button></p>
                </div>
            </div>
        </div>
    );
};

const RegisterForm = ({ onSwitch }) => {
    const { register, login } = useAuth();
    const toast = useToast();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('student');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password.length < 8) { toast('Password must be at least 8 characters', 'error'); return; }
        setLoading(true);
        try { await register(email, password, role); toast('Account created!', 'success'); await login(email, password); }
        catch (err) { toast(err.message, 'error'); }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex">
            <div className="hidden lg:flex lg:w-1/2 gradient-hero items-center justify-center p-12">
                <div className="max-w-lg text-white animate-fade">
                    <h1 className="text-5xl font-display font-bold mb-6">Join PlaceMe Today</h1>
                    <p className="text-xl opacity-90 mb-8">Create your account and unlock opportunities.</p>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white/10 rounded-xl p-5 backdrop-blur"><div className="text-3xl mb-2">🎓</div><h3 className="font-semibold mb-1">For Students</h3><p className="text-sm opacity-80">Upload resume, get AI recommendations</p></div>
                        <div className="bg-white/10 rounded-xl p-5 backdrop-blur"><div className="text-3xl mb-2">🏢</div><h3 className="font-semibold mb-1">For Companies</h3><p className="text-sm opacity-80">Post jobs, find talent, track analytics</p></div>
                    </div>
                </div>
            </div>
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 gradient-mesh">
                <div className="max-w-md w-full animate-slide-up">
                    <div className="text-center mb-8">
                        <h2 className="text-3xl font-display font-bold text-gray-900">Create Account</h2>
                        <p className="text-gray-500 mt-2">Start your placement journey</p>
                    </div>
                    <Card className="p-8">
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div className="grid grid-cols-2 gap-3">
                                {[{ value: 'student', icon: '🎓', label: 'Student' }, { value: 'company', icon: '🏢', label: 'Company' }].map(r => (<button key={r.value} type="button" onClick={() => setRole(r.value)} className={`p-4 rounded-xl border-2 transition-all ${role === r.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}><div className="text-2xl mb-1">{r.icon}</div><div className="font-medium">{r.label}</div></button>))}
                            </div>
                            <Input label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required />
                            <Input label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Min. 8 characters" required />
                            <Button type="submit" loading={loading} className="w-full">Create Account</Button>
                        </form>
                    </Card>
                    <p className="text-center mt-6 text-gray-500">Have an account? <button onClick={onSwitch} className="text-blue-600 font-semibold hover:underline">Sign in</button></p>
                </div>
            </div>
        </div>
    );
};

// ============================================================
// CREATE PROFILE (Shared between Student/Company)
// ============================================================

const CreateProfile = ({ onSuccess, type }) => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState(
        type === 'student' 
            ? { full_name: '', phone: '', university: '', degree: '', major: '', graduation_year: 2025, cgpa: '' }
            : { company_name: '', industry: '', company_size: 'medium', website: '', headquarters: '' }
    );

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const endpoint = type === 'student' ? '/students/profile' : '/companies/profile';
            const body = type === 'student' ? { ...form, cgpa: form.cgpa ? parseFloat(form.cgpa) : null } : form;
            const res = await authFetch(`${API}${endpoint}`, { method: 'POST', body: JSON.stringify(body) });
            if (res.ok) { toast('Profile created!', 'success'); onSuccess(); }
            else throw new Error((await res.json()).detail);
        } catch (err) { toast(err.message, 'error'); }
        setLoading(false);
    };

    return (
        <Card className="p-8 animate-slide-up">
            <div className="text-center mb-8">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center mx-auto mb-4 text-4xl">{type === 'student' ? '🎓' : '🏢'}</div>
                <h2 className="text-2xl font-display font-bold">Complete Your Profile</h2>
                <p className="text-gray-500 mt-2">Let's get you set up!</p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
                {type === 'student' ? (
                    <>
                        <div className="grid grid-cols-2 gap-4">
                            <Input label="Full Name" value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} required />
                            <Input label="Phone" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} />
                        </div>
                        <Input label="University" value={form.university} onChange={e => setForm({...form, university: e.target.value})} />
                        <div className="grid grid-cols-2 gap-4">
                            <Input label="Degree" value={form.degree} onChange={e => setForm({...form, degree: e.target.value})} />
                            <Input label="Major" value={form.major} onChange={e => setForm({...form, major: e.target.value})} />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <Input label="Graduation Year" type="number" value={form.graduation_year} onChange={e => setForm({...form, graduation_year: parseInt(e.target.value)})} />
                            <Input label="CGPA" type="number" step="0.01" value={form.cgpa} onChange={e => setForm({...form, cgpa: e.target.value})} />
                        </div>
                    </>
                ) : (
                    <>
                        <Input label="Company Name" value={form.company_name} onChange={e => setForm({...form, company_name: e.target.value})} required />
                        <div className="grid grid-cols-2 gap-4">
                            <Input label="Industry" value={form.industry} onChange={e => setForm({...form, industry: e.target.value})} />
                            <div className="space-y-1.5">
                                <label className="block text-sm font-medium text-gray-700">Company Size</label>
                                <select value={form.company_size} onChange={e => setForm({...form, company_size: e.target.value})} className="w-full px-4 py-3 border border-gray-200 rounded-xl">
                                    <option value="startup">Startup</option><option value="small">Small</option><option value="medium">Medium</option><option value="large">Large</option><option value="enterprise">Enterprise</option>
                                </select>
                            </div>
                        </div>
                        <Input label="Website" value={form.website} onChange={e => setForm({...form, website: e.target.value})} />
                        <Input label="Headquarters" value={form.headquarters} onChange={e => setForm({...form, headquarters: e.target.value})} />
                    </>
                )}
                <Button type="submit" loading={loading} className="w-full">Create Profile</Button>
            </form>
        </Card>
    );
};

// ============================================================
// STUDENT DASHBOARD
// ============================================================

const StudentDashboard = () => {
    const { authFetch } = useAuth();
    const [tab, setTab] = useState('overview');
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [hasProfile, setHasProfile] = useState(false);

    useEffect(() => { fetchProfile(); }, []);

    const fetchProfile = async () => {
        try {
            const res = await authFetch(`${API}/students/profile`);
            if (res.ok) { setProfile(await res.json()); setHasProfile(true); }
            else if (res.status === 404) setHasProfile(false);
        } catch (err) { console.error(err); }
        setLoading(false);
    };

    const sidebarItems = [
        { id: 'overview', label: 'Dashboard', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6z" /></svg> },
        { id: 'profile', label: 'Profile', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg> },
        { id: 'resume', label: 'Resume', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg> },
        { id: 'jobs', label: 'Browse Jobs', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg> },
        { id: 'recommendations', label: 'For You', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg> },
        { id: 'applications', label: 'Applications', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg> },
    ];

    if (loading) return <div className="min-h-screen flex items-center justify-center"><Spinner size="lg" /></div>;
    if (!hasProfile) return (<div className="min-h-screen bg-gray-50"><Navbar /><div className="max-w-2xl mx-auto px-4 py-12"><CreateProfile onSuccess={() => { setHasProfile(true); fetchProfile(); }} type="student" /></div></div>);

    return (
        <div className="min-h-screen bg-gray-50">
            <Navbar />
            <div className="flex">
                <Sidebar items={sidebarItems} active={tab} onSelect={setTab} />
                <main className="flex-1 p-6 lg:p-8">
                    {tab === 'overview' && <StudentOverview profile={profile} />}
                    {tab === 'profile' && <StudentProfileView profile={profile} onUpdate={fetchProfile} />}
                    {tab === 'resume' && <ResumeSection profile={profile} onUpdate={fetchProfile} />}
                    {tab === 'jobs' && <JobsSection />}
                    {tab === 'recommendations' && <RecommendationsSection profile={profile} />}
                    {tab === 'applications' && <ApplicationsSection />}
                </main>
            </div>
        </div>
    );
};

const StudentOverview = ({ profile }) => {
    const { authFetch } = useAuth();
    const [summary, setSummary] = useState(null);
    const [apps, setApps] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [sumRes, appRes] = await Promise.all([authFetch(`${API}/recommendations/student-summary`), authFetch(`${API}/students/applications`)]);
                if (sumRes.ok) setSummary(await sumRes.json());
                if (appRes.ok) setApps(await appRes.json());
            } catch {}
        };
        fetchData();
    }, []);

    return (
        <div className="space-y-6 animate-fade">
            <div><h1 className="text-2xl font-display font-bold text-gray-900">Welcome, {profile?.full_name?.split(' ')[0]}! 👋</h1><p className="text-gray-500">Here's your placement overview</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Skills" value={summary?.total_skills || profile?.skills?.length || 0} color="blue" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707" /></svg>} />
                <StatCard title="Applications" value={summary?.total_applications || 0} color="purple" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>} />
                <StatCard title="Shortlisted" value={summary?.shortlisted_count || 0} color="green" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
                <StatCard title="Offers" value={summary?.offers_received || 0} color="amber" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" /></svg>} />
            </div>
            {!profile?.resume_uploaded && (<Card className="p-5 border-l-4 border-amber-400 bg-amber-50"><div className="flex items-center gap-4"><div className="text-3xl">📄</div><div><h3 className="font-semibold text-amber-800">Upload Your Resume</h3><p className="text-sm text-amber-700">Get AI-powered job recommendations!</p></div></div></Card>)}
            <Card className="p-6">
                <h2 className="font-display font-bold text-lg mb-4">Recent Applications</h2>
                {apps.length > 0 ? (<div className="space-y-3">{apps.slice(0, 5).map(app => (<div key={app.application_id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl"><div><h3 className="font-medium">{app.job_title}</h3><p className="text-sm text-gray-500">{app.company_name}</p></div><Badge variant={app.status === 'shortlisted' ? 'success' : app.status === 'rejected' ? 'danger' : app.status === 'offered' ? 'warning' : 'default'}>{app.status}</Badge></div>))}</div>) : (<div className="text-center py-8 text-gray-400"><p>No applications yet</p></div>)}
            </Card>
        </div>
    );
};

const StudentProfileView = ({ profile, onUpdate }) => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [editing, setEditing] = useState(false);
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({ ...profile });

    const handleSave = async () => {
        setLoading(true);
        try {
            const res = await authFetch(`${API}/students/profile`, { method: 'PUT', body: JSON.stringify(form) });
            if (res.ok) { toast('Profile updated!', 'success'); setEditing(false); onUpdate(); }
            else throw new Error((await res.json()).detail);
        } catch (err) { toast(err.message, 'error'); }
        setLoading(false);
    };

    return (
        <div className="space-y-6 animate-fade">
            <div className="flex justify-between items-center"><h1 className="text-2xl font-display font-bold">My Profile</h1><Button variant={editing ? 'secondary' : 'primary'} onClick={() => setEditing(!editing)}>{editing ? 'Cancel' : 'Edit'}</Button></div>
            <Card className="p-6">
                <div className="flex items-center gap-6 mb-6 pb-6 border-b">
                    <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-4xl font-bold shadow-lg">{profile?.full_name?.[0]}</div>
                    <div><h2 className="text-2xl font-bold">{profile?.full_name}</h2><p className="text-gray-500">{profile?.email}</p><div className="flex gap-2 mt-2">{profile?.resume_uploaded && <Badge variant="success">Resume ✓</Badge>}<Badge variant="primary">{profile?.skills?.length || 0} Skills</Badge></div></div>
                </div>
                {editing ? (<div className="grid grid-cols-2 gap-4"><Input label="Full Name" value={form.full_name || ''} onChange={e => setForm({...form, full_name: e.target.value})} /><Input label="Phone" value={form.phone || ''} onChange={e => setForm({...form, phone: e.target.value})} /><Input label="University" value={form.university || ''} onChange={e => setForm({...form, university: e.target.value})} /><Input label="Degree" value={form.degree || ''} onChange={e => setForm({...form, degree: e.target.value})} /><Input label="Major" value={form.major || ''} onChange={e => setForm({...form, major: e.target.value})} /><Input label="Graduation Year" type="number" value={form.graduation_year || ''} onChange={e => setForm({...form, graduation_year: parseInt(e.target.value)})} /><Input label="CGPA" type="number" step="0.01" value={form.cgpa || ''} onChange={e => setForm({...form, cgpa: parseFloat(e.target.value)})} /><div className="col-span-2"><Button onClick={handleSave} loading={loading}>Save Changes</Button></div></div>) : (<div className="grid grid-cols-2 md:grid-cols-3 gap-6">{[{ label: 'University', value: profile?.university }, { label: 'Degree', value: profile?.degree }, { label: 'Major', value: profile?.major }, { label: 'Graduation', value: profile?.graduation_year }, { label: 'CGPA', value: profile?.cgpa }, { label: 'Phone', value: profile?.phone }].map((item, i) => (<div key={i}><p className="text-sm text-gray-500">{item.label}</p><p className="font-medium">{item.value || '-'}</p></div>))}</div>)}
            </Card>
            <Card className="p-6"><h3 className="font-display font-bold mb-4">Skills</h3>{profile?.skills?.length > 0 ? (<div className="flex flex-wrap gap-2">{profile.skills.map((skill, i) => (<span key={i} className="px-4 py-2 bg-blue-50 text-blue-700 rounded-full font-medium">{skill}</span>))}</div>) : (<p className="text-gray-400">Upload your resume to extract skills</p>)}</Card>
        </div>
    );
};

const ResumeSection = ({ profile, onUpdate }) => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);

    const handleUpload = async (file) => {
        if (!file) return;
        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await authFetch(`${API}/students/resume/upload`, { method: 'POST', body: formData });
            if (res.ok) { const data = await res.json(); setResult(data); toast(`Resume uploaded! ${data.skills_synced} skills extracted.`, 'success'); onUpdate(); }
            else throw new Error((await res.json()).detail);
        } catch (err) { toast(err.message, 'error'); }
        setUploading(false);
    };

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">Resume Upload</h1>
            <Card className="p-8">
                <div className="border-2 border-dashed border-gray-300 rounded-2xl p-12 text-center hover:border-blue-400 transition-colors">
                    {uploading ? (<div className="flex flex-col items-center"><Spinner size="lg" /><p className="mt-4 text-gray-600">Uploading & parsing with AI...</p></div>) : (<><div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center mx-auto mb-4"><svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg></div><h3 className="text-lg font-semibold mb-2">Upload your resume</h3><p className="text-gray-500 mb-4">PDF, DOCX, or TXT (Max 5MB)</p><input type="file" accept=".pdf,.docx,.txt" onChange={e => handleUpload(e.target.files[0])} className="hidden" id="resume-input" /><label htmlFor="resume-input"><span className="btn-primary text-white px-6 py-3 rounded-xl font-medium cursor-pointer inline-block">Choose File</span></label></>)}
                </div>
            </Card>
            {result && (<Card className="p-6 border-l-4 border-green-500"><h3 className="text-lg font-semibold text-green-700 mb-4">✓ Resume Parsed Successfully</h3><div className="space-y-4"><div><p className="text-sm text-gray-500">Extracted Skills ({result.extracted_skills?.length})</p><div className="flex flex-wrap gap-2 mt-2">{result.extracted_skills?.map((skill, i) => <Badge key={i} variant="primary">{skill}</Badge>)}</div></div></div></Card>)}
            <Card className="p-6"><h3 className="font-semibold mb-3">Status</h3><div className="flex items-center gap-3">{profile?.resume_uploaded ? (<><div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center text-green-600">✓</div><div><p className="font-medium text-green-700">Resume uploaded</p><p className="text-sm text-gray-500">{profile?.skills?.length || 0} skills extracted</p></div></>) : (<><div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-600">!</div><div><p className="font-medium text-amber-700">No resume uploaded</p><p className="text-sm text-gray-500">Upload to get recommendations</p></div></>)}</div></Card>
        </div>
    );
};

const JobsSection = () => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selected, setSelected] = useState(null);

    useEffect(() => { fetchJobs(); }, []);
    const fetchJobs = async () => { try { const params = search ? `?search=${search}` : ''; const res = await fetch(`${API}/jobs${params}`); if (res.ok) setJobs((await res.json()).jobs || []); } catch {} setLoading(false); };
    const applyToJob = async (jobId) => { try { const res = await authFetch(`${API}/jobs/${jobId}/apply`, { method: 'POST', body: JSON.stringify({ job_id: jobId }) }); if (res.ok) { toast('Applied successfully!', 'success'); setSelected(null); } else throw new Error((await res.json()).detail); } catch (err) { toast(err.message, 'error'); } };

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">Browse Jobs</h1>
            <Card className="p-4"><div className="flex gap-4"><Input placeholder="Search jobs..." value={search} onChange={e => setSearch(e.target.value)} className="flex-1" /><Button onClick={fetchJobs}>Search</Button></div></Card>
            {loading ? (<div className="flex justify-center py-12"><Spinner size="lg" /></div>) : jobs.length > 0 ? (<div className="grid gap-4">{jobs.map(job => (<Card key={job.job_id} className="p-6" hover><div className="flex justify-between items-start"><div><div className="flex items-center gap-3 mb-2"><h3 className="text-lg font-semibold">{job.title}</h3>{job.is_remote && <Badge variant="purple">Remote</Badge>}</div><p className="text-gray-600 mb-2">{job.company_name}</p><div className="flex flex-wrap gap-3 text-sm text-gray-500 mb-3">{job.location && <span>📍 {job.location}</span>}<span>💼 {job.min_experience}-{job.max_experience || '+'} yrs</span>{job.min_salary && <span>💰 ₹{(job.min_salary/100000).toFixed(0)}-{(job.max_salary/100000).toFixed(0)}L</span>}</div><div className="flex flex-wrap gap-2">{job.required_skills?.slice(0, 4).map((s, i) => <Badge key={i}>{s}</Badge>)}{job.required_skills?.length > 4 && <Badge>+{job.required_skills.length - 4}</Badge>}</div></div><Button onClick={() => setSelected(job)}>View</Button></div></Card>))}</div>) : (<Card className="p-12 text-center"><p className="text-gray-400">No jobs found</p></Card>)}
            <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={selected?.title}>{selected && (<div className="space-y-4"><p className="font-medium">{selected.company_name}</p><p className="text-gray-500">{selected.location} {selected.is_remote && '• Remote'}</p>{selected.description && <p className="text-sm text-gray-600">{selected.description}</p>}<div><p className="font-medium mb-2">Required Skills</p><div className="flex flex-wrap gap-2">{selected.required_skills?.map((s, i) => <Badge key={i} variant="primary">{s}</Badge>)}</div></div><Button onClick={() => applyToJob(selected.job_id)} className="w-full">Apply Now</Button></div>)}</Modal>
        </div>
    );
};

const RecommendationsSection = ({ profile }) => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [recs, setRecs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);

    useEffect(() => { fetchRecs(); }, []);
    const fetchRecs = async () => { try { const res = await authFetch(`${API}/recommendations`); if (res.ok) setRecs((await res.json()).recommendations || []); } catch {} setLoading(false); };
    const generate = async () => { if (!profile?.resume_uploaded) { toast('Upload resume first!', 'warning'); return; } setGenerating(true); try { const res = await authFetch(`${API}/recommendations/generate`, { method: 'POST' }); if (res.ok) { toast((await res.json()).message, 'success'); fetchRecs(); } } catch (err) { toast(err.message, 'error'); } setGenerating(false); };
    const applyToJob = async (jobId) => { try { const res = await authFetch(`${API}/jobs/${jobId}/apply`, { method: 'POST', body: JSON.stringify({ job_id: jobId }) }); if (res.ok) { toast('Applied!', 'success'); fetchRecs(); } else throw new Error((await res.json()).detail); } catch (err) { toast(err.message, 'error'); } };

    return (
        <div className="space-y-6 animate-fade">
            <div className="flex justify-between items-center"><div><h1 className="text-2xl font-display font-bold">AI Recommendations</h1><p className="text-gray-500">Jobs matched to your profile</p></div><Button onClick={generate} loading={generating}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>Generate</Button></div>
            {!profile?.resume_uploaded && (<Card className="p-5 border-l-4 border-amber-400 bg-amber-50"><p className="text-amber-800">Upload your resume to get AI recommendations!</p></Card>)}
            {loading ? (<div className="flex justify-center py-12"><Spinner size="lg" /></div>) : recs.length > 0 ? (<div className="grid gap-4">{recs.map(rec => (<Card key={rec.recommendation_id} className="p-6" hover><div className="flex justify-between items-start"><div><div className="flex items-center gap-3 mb-2"><h3 className="text-lg font-semibold">{rec.job_title}</h3><div className="px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white text-xs font-bold rounded-full">{Math.round(rec.match_score * 100)}% Match</div></div><p className="text-gray-600 mb-2">{rec.company_name}</p><p className="text-sm text-gray-500">{rec.recommendation_reason}</p></div>{!rec.is_applied ? <Button onClick={() => applyToJob(rec.job_id)}>Apply</Button> : <Badge variant="success">Applied</Badge>}</div></Card>))}</div>) : (<Card className="p-12 text-center"><p className="text-gray-400 mb-4">No recommendations yet</p><Button onClick={generate} loading={generating}>Generate Recommendations</Button></Card>)}
        </div>
    );
};

const ApplicationsSection = () => {
    const { authFetch } = useAuth();
    const [apps, setApps] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => { const fetch = async () => { try { const res = await authFetch(`${API}/students/applications`); if (res.ok) setApps(await res.json()); } catch {} setLoading(false); }; fetch(); }, []);
    const statusColors = { applied: 'default', under_review: 'primary', shortlisted: 'success', interviewed: 'purple', offered: 'warning', accepted: 'success', rejected: 'danger' };

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">My Applications</h1>
            {loading ? (<div className="flex justify-center py-12"><Spinner size="lg" /></div>) : apps.length > 0 ? (<div className="space-y-4">{apps.map(app => (<Card key={app.application_id} className="p-6"><div className="flex items-center justify-between"><div><h3 className="font-semibold">{app.job_title}</h3><p className="text-gray-500">{app.company_name}</p><p className="text-xs text-gray-400 mt-1">Applied: {new Date(app.applied_at).toLocaleDateString()}</p></div><Badge variant={statusColors[app.status] || 'default'}>{app.status.replace('_', ' ')}</Badge></div></Card>))}</div>) : (<Card className="p-12 text-center"><p className="text-gray-400">No applications yet</p></Card>)}
        </div>
    );
};

// ============================================================
// COMPANY DASHBOARD
// ============================================================

const CompanyDashboard = () => {
    const { authFetch } = useAuth();
    const [tab, setTab] = useState('overview');
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [hasProfile, setHasProfile] = useState(false);

    useEffect(() => { fetchProfile(); }, []);

    const fetchProfile = async () => {
        try {
            const res = await authFetch(`${API}/companies/profile`);
            if (res.ok) { setProfile(await res.json()); setHasProfile(true); }
            else if (res.status === 404) setHasProfile(false);
        } catch {}
        setLoading(false);
    };

    const sidebarItems = [
        { id: 'overview', label: 'Dashboard', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6z" /></svg> },
        { id: 'profile', label: 'Company Profile', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5" /></svg> },
        { id: 'post-job', label: 'Post Job', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg> },
        { id: 'jobs', label: 'My Jobs', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg> },
        { id: 'applications', label: 'Applications', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg> },
        { id: 'analytics', label: 'Analytics', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg> },
    ];

    if (loading) return <div className="min-h-screen flex items-center justify-center"><Spinner size="lg" /></div>;
    if (!hasProfile) return (<div className="min-h-screen bg-gray-50"><Navbar /><div className="max-w-2xl mx-auto px-4 py-12"><CreateProfile onSuccess={() => { setHasProfile(true); fetchProfile(); }} type="company" /></div></div>);

    return (
        <div className="min-h-screen bg-gray-50">
            <Navbar />
            <div className="flex">
                <Sidebar items={sidebarItems} active={tab} onSelect={setTab} />
                <main className="flex-1 p-6 lg:p-8">
                    {tab === 'overview' && <CompanyOverview profile={profile} />}
                    {tab === 'profile' && <CompanyProfileView profile={profile} />}
                    {tab === 'post-job' && <PostJobSection />}
                    {tab === 'jobs' && <CompanyJobsSection />}
                    {tab === 'applications' && <CompanyApplicationsSection />}
                    {tab === 'analytics' && <AnalyticsSection />}
                </main>
            </div>
        </div>
    );
};

const CompanyOverview = ({ profile }) => {
    const { authFetch } = useAuth();
    const [stats, setStats] = useState(null);

    useEffect(() => {
        const fetch = async () => { try { const res = await authFetch(`${API}/companies/stats`); if (res.ok) setStats(await res.json()); } catch {} };
        fetch();
    }, []);

    return (
        <div className="space-y-6 animate-fade">
            <div><h1 className="text-2xl font-display font-bold text-gray-900">Welcome, {profile?.company_name}! 🏢</h1><p className="text-gray-500">Your hiring dashboard</p></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Jobs Posted" value={stats?.total_jobs_posted || 0} color="blue" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01" /></svg>} />
                <StatCard title="Applications" value={stats?.total_applications_received || 0} color="purple" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>} />
                <StatCard title="Shortlisted" value={stats?.candidates_shortlisted || 0} color="green" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
                <StatCard title="Hired" value={stats?.hires_completed || 0} color="amber" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" /></svg>} />
            </div>
            {stats && (<Card className="p-6"><h3 className="font-display font-bold mb-4">Hiring Funnel</h3><div className="flex items-center justify-between text-center">{[{ label: 'Applications', value: stats.total_applications_received || 0, color: 'bg-blue-500' },{ label: 'Shortlisted', value: stats.candidates_shortlisted || 0, color: 'bg-purple-500' },{ label: 'Offers', value: stats.offers_extended || 0, color: 'bg-amber-500' },{ label: 'Hired', value: stats.hires_completed || 0, color: 'bg-green-500' }].map((step, i) => (<React.Fragment key={i}><div className="flex-1"><div className={`w-16 h-16 rounded-full ${step.color} flex items-center justify-center text-white text-xl font-bold mx-auto mb-2`}>{step.value}</div><p className="text-sm text-gray-600">{step.label}</p></div>{i < 3 && <div className="text-gray-300 text-2xl">→</div>}</React.Fragment>))}</div></Card>)}
        </div>
    );
};

const CompanyProfileView = ({ profile }) => (
    <div className="space-y-6 animate-fade">
        <h1 className="text-2xl font-display font-bold">Company Profile</h1>
        <Card className="p-6">
            <div className="flex items-center gap-6 mb-6 pb-6 border-b">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-3xl font-bold">{profile?.company_name?.[0]}</div>
                <div><h2 className="text-2xl font-bold">{profile?.company_name}</h2><p className="text-gray-500">{profile?.industry}</p>{profile?.is_verified && <Badge variant="success">Verified ✓</Badge>}</div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">{[{ label: 'Size', value: profile?.company_size }, { label: 'Headquarters', value: profile?.headquarters }, { label: 'Website', value: profile?.website }, { label: 'Email', value: profile?.email }].map((item, i) => (<div key={i}><p className="text-sm text-gray-500">{item.label}</p><p className="font-medium">{item.value || '-'}</p></div>))}</div>
        </Card>
    </div>
);

const PostJobSection = () => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({ title: '', description: '', job_type: 'full-time', location: '', is_remote: false, min_experience: 0, max_experience: 5, min_salary: '', max_salary: '', required_skills: '', preferred_skills: '' });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const body = { ...form, min_salary: form.min_salary ? parseFloat(form.min_salary) : null, max_salary: form.max_salary ? parseFloat(form.max_salary) : null, required_skills: form.required_skills.split(',').map(s => s.trim()).filter(Boolean), preferred_skills: form.preferred_skills.split(',').map(s => s.trim()).filter(Boolean) };
            const res = await authFetch(`${API}/jobs`, { method: 'POST', body: JSON.stringify(body) });
            if (res.ok) { toast('Job posted successfully!', 'success'); setForm({ title: '', description: '', job_type: 'full-time', location: '', is_remote: false, min_experience: 0, max_experience: 5, min_salary: '', max_salary: '', required_skills: '', preferred_skills: '' }); }
            else throw new Error((await res.json()).detail);
        } catch (err) { toast(err.message, 'error'); }
        setLoading(false);
    };

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">Post a Job</h1>
            <Card className="p-6">
                <form onSubmit={handleSubmit} className="space-y-5">
                    <Input label="Job Title" value={form.title} onChange={e => setForm({...form, title: e.target.value})} placeholder="e.g., Senior Software Engineer" required />
                    <div><label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label><textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})} rows={4} className="w-full px-4 py-3 border border-gray-200 rounded-xl input-styled outline-none" placeholder="Job description..." /></div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5"><label className="block text-sm font-medium text-gray-700">Job Type</label><select value={form.job_type} onChange={e => setForm({...form, job_type: e.target.value})} className="w-full px-4 py-3 border border-gray-200 rounded-xl"><option value="full-time">Full-time</option><option value="part-time">Part-time</option><option value="internship">Internship</option><option value="contract">Contract</option></select></div>
                        <Input label="Location" value={form.location} onChange={e => setForm({...form, location: e.target.value})} placeholder="e.g., Bangalore" />
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={form.is_remote} onChange={e => setForm({...form, is_remote: e.target.checked})} className="w-4 h-4" /><span>Remote position</span></label>
                    <div className="grid grid-cols-2 gap-4">
                        <Input label="Min Experience (years)" type="number" value={form.min_experience} onChange={e => setForm({...form, min_experience: parseInt(e.target.value) || 0})} />
                        <Input label="Max Experience (years)" type="number" value={form.max_experience} onChange={e => setForm({...form, max_experience: parseInt(e.target.value) || 0})} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <Input label="Min Salary (₹)" type="number" value={form.min_salary} onChange={e => setForm({...form, min_salary: e.target.value})} placeholder="e.g., 1500000" />
                        <Input label="Max Salary (₹)" type="number" value={form.max_salary} onChange={e => setForm({...form, max_salary: e.target.value})} placeholder="e.g., 2500000" />
                    </div>
                    <Input label="Required Skills (comma-separated)" value={form.required_skills} onChange={e => setForm({...form, required_skills: e.target.value})} placeholder="Python, FastAPI, PostgreSQL" />
                    <Input label="Preferred Skills (comma-separated)" value={form.preferred_skills} onChange={e => setForm({...form, preferred_skills: e.target.value})} placeholder="Docker, AWS" />
                    <Button type="submit" loading={loading} className="w-full">Post Job</Button>
                </form>
            </Card>
        </div>
    );
};

const CompanyJobsSection = () => {
    const { authFetch } = useAuth();
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => { fetchJobs(); }, []);
    const fetchJobs = async () => { try { const res = await authFetch(`${API}/companies/jobs`); if (res.ok) setJobs(await res.json()); } catch {} setLoading(false); };

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">My Job Postings</h1>
            {loading ? (<div className="flex justify-center py-12"><Spinner size="lg" /></div>) : jobs.length > 0 ? (<div className="grid gap-4">{jobs.map(job => (<Card key={job.job_id} className="p-6"><div className="flex justify-between items-start"><div><div className="flex items-center gap-3 mb-2"><h3 className="text-lg font-semibold">{job.title}</h3><Badge variant={job.status === 'open' ? 'success' : 'default'}>{job.status}</Badge></div><div className="flex gap-4 text-sm text-gray-500">{job.location && <span>📍 {job.location}</span>}<span>💼 {job.job_type}</span><span>👥 {job.openings} openings</span></div></div></div></Card>))}</div>) : (<Card className="p-12 text-center"><p className="text-gray-400">No jobs posted yet</p></Card>)}
        </div>
    );
};

const CompanyApplicationsSection = () => {
    const { authFetch } = useAuth();
    const toast = useToast();
    const [apps, setApps] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => { fetchApps(); }, []);
    const fetchApps = async () => { try { const res = await authFetch(`${API}/companies/applications`); if (res.ok) setApps(await res.json()); } catch {} setLoading(false); };
    const updateStatus = async (appId, status) => { try { const res = await authFetch(`${API}/companies/applications/${appId}/status`, { method: 'PUT', body: JSON.stringify({ status }) }); if (res.ok) { toast(`Status updated to ${status}`, 'success'); fetchApps(); } else throw new Error((await res.json()).detail); } catch (err) { toast(err.message, 'error'); } };

    const statusColors = { applied: 'default', under_review: 'primary', shortlisted: 'success', interviewed: 'purple', offered: 'warning', accepted: 'success', rejected: 'danger' };

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">Applications Received</h1>
            {loading ? (<div className="flex justify-center py-12"><Spinner size="lg" /></div>) : apps.length > 0 ? (<div className="space-y-4">{apps.map(app => (<Card key={app.application_id} className="p-6"><div className="flex items-start justify-between"><div><h3 className="font-semibold">{app.student_name}</h3><p className="text-gray-500">Applied for: {app.job_title}</p><p className="text-xs text-gray-400 mt-1">{new Date(app.applied_at).toLocaleDateString()}</p></div><div className="flex items-center gap-3"><Badge variant={statusColors[app.status] || 'default'}>{app.status.replace('_', ' ')}</Badge><select value={app.status} onChange={e => updateStatus(app.application_id, e.target.value)} className="px-3 py-2 border rounded-lg text-sm"><option value="applied">Applied</option><option value="under_review">Under Review</option><option value="shortlisted">Shortlisted</option><option value="interviewed">Interviewed</option><option value="offered">Offered</option><option value="rejected">Rejected</option></select></div></div></Card>))}</div>) : (<Card className="p-12 text-center"><p className="text-gray-400">No applications received yet</p></Card>)}
        </div>
    );
};

const AnalyticsSection = () => {
    const { authFetch } = useAuth();
    const [stats, setStats] = useState(null);
    const [skills, setSkills] = useState([]);
    const chartRef = useRef(null);
    const chartInstance = useRef(null);

    useEffect(() => {
        const fetchData = async () => { try { const [statsRes, skillsRes] = await Promise.all([authFetch(`${API}/companies/stats`), fetch(`${API}/recommendations/skills-analysis?limit=10`)]); if (statsRes.ok) setStats(await statsRes.json()); if (skillsRes.ok) setSkills(await skillsRes.json()); } catch {} };
        fetchData();
    }, []);

    useEffect(() => {
        if (stats && chartRef.current) {
            if (chartInstance.current) chartInstance.current.destroy();
            chartInstance.current = new Chart(chartRef.current, {
                type: 'doughnut',
                data: { labels: ['Applications', 'Shortlisted', 'Offers', 'Hired'], datasets: [{ data: [Math.max(0, (stats.total_applications_received || 0) - (stats.candidates_shortlisted || 0)), Math.max(0, (stats.candidates_shortlisted || 0) - (stats.offers_extended || 0)), Math.max(0, (stats.offers_extended || 0) - (stats.hires_completed || 0)), stats.hires_completed || 0], backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981'] }] },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        }
        return () => { if (chartInstance.current) chartInstance.current.destroy(); };
    }, [stats]);

    return (
        <div className="space-y-6 animate-fade">
            <h1 className="text-2xl font-display font-bold">Hiring Analytics</h1>
            {stats && (<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6"><h3 className="font-semibold mb-4">Hiring Funnel</h3><div className="aspect-square max-w-xs mx-auto"><canvas ref={chartRef}></canvas></div></Card>
                <Card className="p-6"><h3 className="font-semibold mb-4">Key Metrics</h3><div className="space-y-4"><div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl"><span>Offer Rate</span><span className="font-bold text-lg">{(stats.offer_rate_percentage || 0).toFixed(1)}%</span></div><div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl"><span>Active Jobs</span><span className="font-bold text-lg">{stats.active_jobs || 0}</span></div><div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl"><span>Total Hired</span><span className="font-bold text-lg text-green-600">{stats.hires_completed || 0}</span></div></div></Card>
            </div>)}
            <Card className="p-6"><h3 className="font-semibold mb-4">Market Skill Demand (from SQL View)</h3>{skills.length > 0 ? (<div className="space-y-3">{skills.map(skill => (<div key={skill.skill_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl"><div><span className="font-medium">{skill.skill_name}</span><span className="text-sm text-gray-500 ml-2">({skill.skill_category || 'uncategorized'})</span></div><div className="flex items-center gap-4"><span className="text-sm">Demand: {skill.total_job_demand}</span><Badge variant={skill.market_status === 'High Demand - Skill Shortage' ? 'danger' : skill.market_status === 'Balanced' ? 'success' : 'default'}>{skill.market_status}</Badge></div></div>))}</div>) : (<p className="text-gray-400 text-center py-8">No skill data available</p>)}</Card>
        </div>
    );
};

// ============================================================
// MAIN APP
// ============================================================

const App = () => {
    const { user, loading } = useAuth();
    if (loading) return (<div className="min-h-screen flex items-center justify-center gradient-mesh"><div className="text-center"><Spinner size="lg" /><p className="mt-4 text-gray-500">Loading...</p></div></div>);
    if (!user) return <AuthPage />;
    if (user.role === 'student') return <StudentDashboard />;
    if (user.role === 'company') return <CompanyDashboard />;
    return <AuthPage />;
};

// ============================================================
// RENDER
// ============================================================

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<AuthProvider><ToastProvider><App /></ToastProvider></AuthProvider>);