import { type ReactNode, useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  Activity,
  Bell,
  Bot,
  Check,
  ChevronLeft,
  CircleAlert,
  CircleCheck,
  Coins,
  Headphones,
  LayoutDashboard,
  ListChecks,
  LockKeyhole,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Plus,
  Radio,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Server,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Ticket,
  UsersRound,
  Wifi,
  WifiOff,
  X,
  Zap,
} from 'lucide-react';
import { Link, Route, Switch, useLocation, Router as WouterRouter } from 'wouter';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { useGetAlythiaStatus, type AlythiaStatus } from '@workspace/api-client-react';

const queryClient = new QueryClient();
const DASHBOARD_READ_ONLY = true;

type ToggleField =
  | 'welcomeEnabled'
  | 'logsEnabled'
  | 'automodEnabled'
  | 'economyEnabled'
  | 'levelEnabled';

type ActivityItem = {
  id: string;
  title: string;
  detail: string;
  time: string;
  tone: 'mint' | 'amber' | 'coral' | 'blue';
};

type DashboardState = {
  dataAvailable: boolean;
  lastUpdated: string | null;
  botOnline: boolean;
  serverName: string | null;
  serverId: string | null;
  memberCount: number | null;
  commandCount: number | null;
  voiceStatus: string | null;
  activeModules: number | null;
  recentActivity: ActivityItem[];
  moderationCounts: { blocked: number | null; warned: number | null; muted: number | null; banned: number | null };
  welcomeEnabled: boolean;
  logsEnabled: boolean;
  automodEnabled: boolean;
  ticketCount: number | null;
  suggestionCount: number | null;
  economyEnabled: boolean;
  levelEnabled: boolean;
  economyUserCount: number | null;
  levelUserCount: number | null;
};

const initialState: DashboardState = {
  dataAvailable: false,
  lastUpdated: null,
  botOnline: false,
  serverName: null,
  serverId: null,
  memberCount: null,
  commandCount: null,
  voiceStatus: null,
  activeModules: null,
  moderationCounts: { blocked: null, warned: null, muted: null, banned: null },
  welcomeEnabled: false,
  logsEnabled: false,
  automodEnabled: false,
  ticketCount: null,
  suggestionCount: null,
  economyEnabled: false,
  levelEnabled: false,
  economyUserCount: null,
  levelUserCount: null,
  recentActivity: [],
};

function displayValue(value: number | string | null | undefined, suffix = '') {
  if (value === null || value === undefined || value === '') return '—';
  return `${typeof value === 'number' ? value.toLocaleString('ar-SA') : value}${suffix}`;
}

function formatUpdatedAt(value: string | null) {
  if (!value) return 'لم تصل بيانات من البوت بعد';
  return `آخر تحديث: ${new Intl.DateTimeFormat('ar-IQ', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))}`;
}

function createDashboardState(status?: AlythiaStatus): DashboardState {
  const guild = status?.guilds[0];
  if (!status || !guild) return initialState;
  const enabledSettings = Object.values(guild.settings).filter(Boolean).length;
  return {
    ...initialState,
    dataAvailable: true,
    lastUpdated: status.updatedAt,
    botOnline: status.botOnline,
    serverName: guild.name,
    serverId: guild.id,
    memberCount: guild.memberCount,
    commandCount: status.commandCount,
    voiceStatus: guild.voiceConnected ? `متصل في ${guild.voiceChannel ?? 'روم صوتي'}` : 'غير متصل',
    activeModules: enabledSettings,
    welcomeEnabled: guild.settings.welcomeEnabled,
    logsEnabled: guild.settings.logsEnabled,
    automodEnabled: guild.settings.automodEnabled,
    suggestionCount: guild.stats.pendingSuggestionCount,
    economyUserCount: guild.stats.economyUserCount,
    levelUserCount: guild.stats.levelUserCount,
    economyEnabled: guild.stats.economyUserCount > 0,
    levelEnabled: guild.stats.levelUserCount > 0,
    moderationCounts: {
      blocked: null,
      warned: guild.stats.warningCount,
      muted: null,
      banned: null,
    },
  };
}

const navItems = [
  { href: '/', label: 'نظرة عامة', hint: 'المركز', icon: LayoutDashboard },
  { href: '/moderation', label: 'الإشراف', hint: 'الحماية', icon: ShieldCheck },
  { href: '/community', label: 'المجتمع', hint: 'التفاعل', icon: UsersRound },
  { href: '/economy', label: 'الاقتصاد', hint: 'النمو', icon: Coins },
  { href: '/voice', label: 'الصوت', hint: 'الحضور', icon: Headphones },
  { href: '/settings', label: 'الإعدادات', hint: 'التفضيلات', icon: Settings2 },
];

function Toggle({
  checked,
  onToggle,
  label,
  testId,
}: {
  checked: boolean;
  onToggle: () => void;
  label: string;
  testId: string;
}) {
  return (
    <button
      type="button"
      disabled={DASHBOARD_READ_ONLY}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      data-testid={testId}
      onClick={onToggle}
      className={`relative h-6 w-11 shrink-0 rounded-full border transition-colors duration-200 ${
        checked ? 'border-[#61bda7] bg-[#61bda7]' : 'border-[#b4c1c3] bg-[#dbe2e3]'
      }`}
      title={DASHBOARD_READ_ONLY ? 'التحكم غير متاح حتى يتم ربط API التعديلات' : undefined}
    >
      <span
        className={`absolute top-[3px] h-4 w-4 rounded-full bg-[#f8fbfa] shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-[-20px]' : 'translate-x-[-3px]'
        }`}
      />
    </button>
  );
}

function StatusPill({ online, label }: { online: boolean; label: string }) {
  return (
    <span
      data-testid={`status-${online ? 'online' : 'offline'}`}
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${
        online ? 'bg-[#dcefe9] text-[#287461]' : 'bg-[#f7dfdb] text-[#9e443c]'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${online ? 'bg-[#41a88e]' : 'bg-[#c45f56]'}`} />
      {label}
    </span>
  );
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  accent,
  testId,
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  accent: 'mint' | 'amber' | 'blue' | 'coral';
  testId: string;
}) {
  const colors = {
    mint: 'bg-[#e0f1ec] text-[#2c7e6b]',
    amber: 'bg-[#fbedd2] text-[#ad7024]',
    blue: 'bg-[#ddebf3] text-[#44758f]',
    coral: 'bg-[#f6e0dc] text-[#a9564a]',
  };
  return (
    <div data-testid={`card-${testId}`} className="panel-shadow rounded-2xl border border-[#d9e3e3] bg-[#f9fbfa] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[12px] font-medium text-[#668087]" data-testid={`text-${testId}-label`}>{label}</p>
          <p className="mt-2 font-mono-data text-[25px] font-bold tracking-[-0.04em] text-[#1d3840]" data-testid={`value-${testId}`}>{value}</p>
          <p className="mt-1 text-[11px] text-[#789097]" data-testid={`text-${testId}-detail`}>{detail}</p>
        </div>
        <span className={`rounded-xl p-2.5 ${colors[accent]}`}><Icon size={17} strokeWidth={1.8} /></span>
      </div>
    </div>
  );
}

function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p className="mb-2 text-[11px] font-bold tracking-[0.18em] text-[#4a9e8a]" data-testid="text-page-eyebrow">{eyebrow}</p>
        <h1 className="text-[28px] font-bold leading-tight tracking-[-0.04em] text-[#1c363e] sm:text-[34px]" data-testid="text-page-title">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm text-[#70858b]" data-testid="text-page-description">{description}</p>
      </div>
      {action}
    </div>
  );
}

function SectionCard({
  title,
  description,
  children,
  className = '',
  testId,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  testId: string;
}) {
  return (
    <section data-testid={`section-${testId}`} className={`panel-shadow rounded-2xl border border-[#d9e3e3] bg-[#f9fbfa] ${className}`}>
      <div className="flex items-start justify-between gap-4 border-b border-[#e2e9e8] px-5 py-4">
        <div>
          <h2 className="text-sm font-bold text-[#27434b]" data-testid={`text-${testId}-title`}>{title}</h2>
          {description && <p className="mt-1 text-[11px] text-[#819399]" data-testid={`text-${testId}-description`}>{description}</p>}
        </div>
        <MoreHorizontal size={18} className="mt-0.5 text-[#9aabad]" />
      </div>
      {children}
    </section>
  );
}

function Sidebar({ mobileOpen, close, state }: { mobileOpen: boolean; close: () => void; state: DashboardState }) {
  const [location] = useLocation();
  return (
    <>
      {mobileOpen && <button type="button" aria-label="إغلاق القائمة" data-testid="button-close-overlay" onClick={close} className="fixed inset-0 z-30 bg-[#122b32]/35 lg:hidden" />}
      <aside className={`fixed inset-y-0 right-0 z-40 flex w-[274px] flex-col border-l border-[#243c43] bg-[#162d35] text-[#dbe9e6] transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between border-b border-[#2b464c] px-5 py-5">
          <Link href="/" data-testid="link-sidebar-brand" onClick={close} className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-[13px] bg-[#9be4d0] text-[#173b3d] shadow-[0_8px_20px_rgba(155,228,208,0.16)]">
              <Bot size={21} strokeWidth={2.2} />
            </span>
            <span>
              <span className="block text-[16px] font-bold tracking-[-0.03em] text-[#f0f6f4]">Alythia</span>
              <span className="mt-0.5 block text-[10px] text-[#91b0ae]">مركز التحكم</span>
            </span>
          </Link>
          <button type="button" onClick={close} aria-label="إغلاق القائمة" data-testid="button-close-sidebar" className="rounded-lg p-1.5 text-[#8eaca9] hover:bg-[#25434a] lg:hidden">
            <X size={18} />
          </button>
        </div>
        <div className="mx-4 mt-5 rounded-xl border border-[#2c4b4e] bg-[#1c3940] px-3.5 py-3">
          <div className="flex items-center gap-2 text-[10px] font-semibold text-[#8eaeaa]">
            <span className={`h-1.5 w-1.5 rounded-full ${state.botOnline ? 'bg-[#81d0b5]' : 'bg-[#d77867]'}`} />
            {state.botOnline ? 'البوت متصل' : 'البوت غير متصل'}
          </div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-sm font-semibold text-[#e9f3ef]" data-testid="text-sidebar-server">{state.serverName ?? 'غير متاح'}</span>
            <span className="font-mono-data text-[10px] text-[#86aaa4]" data-testid="text-sidebar-server-id">{state.serverId ?? '—'}</span>
          </div>
        </div>
        <nav className="mt-7 flex-1 px-3" aria-label="التنقل الرئيسي">
          <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.16em] text-[#668b89]">مساحات العمل</p>
          <div className="space-y-1">
            {navItems.map(({ href, label, hint, icon: Icon }) => {
              const active = location === href;
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={close}
                  data-testid={`link-nav-${href === '/' ? 'overview' : href.slice(1)}`}
                  className={`group flex items-center gap-3 rounded-xl px-3 py-3 transition-colors ${active ? 'bg-[#9be4d0] text-[#173b3d]' : 'text-[#a7c0bd] hover:bg-[#203e45] hover:text-[#e8f3ef]'}`}
                >
                  <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
                  <span className="flex-1 text-sm font-semibold">{label}</span>
                  <span className={`text-[10px] ${active ? 'text-[#397b6d]' : 'text-[#648985]'}`}>{hint}</span>
                </Link>
              );
            })}
          </div>
        </nav>
        <div className="border-t border-[#2b464c] p-4">
          <div className="flex items-center justify-between rounded-xl bg-[#1b3740] px-3 py-3">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#d6e9e3] text-[11px] font-bold text-[#2b695d]">م</span>
              <div>
                <p className="text-[11px] font-semibold text-[#e4f0ed]" data-testid="text-user-name">مالك الخادم</p>
                <p className="text-[10px] text-[#789a98]">صلاحيات كاملة</p>
              </div>
            </div>
            <Link href="/settings" onClick={close} aria-label="إعدادات الملف الشخصي" data-testid="link-profile-settings" className="text-[#719592] hover:text-[#b7d7ce]"><Settings2 size={15} /></Link>
          </div>
        </div>
      </aside>
    </>
  );
}

function Shell({ children, state }: { children: ReactNode; state: DashboardState }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [location] = useLocation();
  const current = navItems.find((item) => item.href === location) ?? navItems[0];
  return (
    <div className="dashboard-shell">
      <Sidebar mobileOpen={mobileOpen} close={() => setMobileOpen(false)} state={state} />
      <div className="min-h-[100dvh] lg:pr-[274px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-[#dce6e5]/90 bg-[#edf2f3]/90 px-4 backdrop-blur-md sm:px-7 lg:px-10">
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setMobileOpen(true)} aria-label="فتح القائمة" data-testid="button-open-sidebar" className="rounded-xl border border-[#d6e2e2] bg-[#f8fbfa] p-2.5 text-[#35626a] lg:hidden"><Menu size={19} /></button>
            <div className="hidden h-8 w-px bg-[#d7e1e1] sm:block" />
            <div>
              <p className="text-[10px] font-bold tracking-[0.14em] text-[#75a19b]">غرفة العمليات / {current.label}</p>
              <p className="mt-0.5 text-sm font-bold text-[#28454d]" data-testid="text-current-location">{current.label}</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="relative hidden md:block">
              <Search size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8da2a5]" />
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ابحث في الخادم" aria-label="البحث في الخادم" data-testid="input-global-search" className="h-10 w-[210px] rounded-xl border border-[#d6e2e2] bg-[#f8fbfa] pr-9 pl-3 text-xs text-[#29464d] outline-none placeholder:text-[#9aaeb1] focus:border-[#79bbaa]" />
            </div>
            <button type="button" onClick={() => setNotificationsOpen(!notificationsOpen)} aria-label="التنبيهات" data-testid="button-notifications" className="relative rounded-xl border border-[#d6e2e2] bg-[#f8fbfa] p-2.5 text-[#537178] hover:bg-[#e4f0ed]">
              <Bell size={17} />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#d77867]" />
            </button>
            {notificationsOpen && <div data-testid="panel-notifications" className="absolute left-4 top-[59px] w-[255px] rounded-2xl border border-[#d6e2e2] bg-[#f9fbfa] p-4 text-right shadow-[0_14px_35px_rgba(40,62,69,0.12)] sm:left-7 lg:left-10"><p className="text-xs font-bold text-[#34545b]">التنبيهات</p><p className="mt-2 text-[11px] text-[#809499]">لا توجد تنبيهات حرجة. كل شيء تحت السيطرة.</p></div>}
            <div className="hidden items-center gap-2 border-r border-[#d7e1e1] pr-3 sm:flex">
              <span className="text-left">
                <span className="block text-[11px] font-bold text-[#36545a]" data-testid="text-header-server">{state.serverName ?? 'غير متاح'}</span>
                <span className="block text-[10px] text-[#8a9da1]">{state.botOnline ? 'متصل الآن' : 'غير متصل'}</span>
              </span>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#d7ebe5] text-[#397e6e]"><Server size={16} /></span>
            </div>
          </div>
        </header>
        <main className="page-enter mx-auto max-w-[1500px] px-4 py-7 sm:px-7 lg:px-10 lg:py-9">{children}</main>
      </div>
    </div>
  );
}

function OverviewPage({ state, toggle, refresh }: { state: DashboardState; toggle: (field: ToggleField) => void; refresh: () => void }) {
  const [refreshed, setRefreshed] = useState(false);
  const knownModeration = Object.values(state.moderationCounts).filter((count): count is number => count !== null);
  const totalModeration = knownModeration.reduce((sum, count) => sum + count, 0);
  const systems: Array<{ label: string; enabled: boolean; icon: typeof Bot }> = [
    { label: 'البوت الأساسي', enabled: state.botOnline, icon: Bot },
    { label: 'الحماية التلقائية', enabled: state.automodEnabled, icon: ShieldCheck },
    { label: 'سجلات الأحداث', enabled: state.logsEnabled, icon: ListChecks },
    { label: 'الترحيب', enabled: state.welcomeEnabled, icon: Radio },
  ];
  return (
    <>
      <PageHeader
        eyebrow="بيانات البوت المباشرة"
        title={`نظرة عامة — ${state.serverName ?? 'بانتظار الاتصال'}`}
        description={formatUpdatedAt(state.lastUpdated)}
        action={
          <div className="flex items-center gap-2">
            <StatusPill online={state.botOnline} label={state.botOnline ? 'البوت متصل' : 'البوت متوقف'} />
            <button type="button" onClick={() => { setRefreshed(true); refresh(); }} data-testid="button-refresh-overview" className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-[#cfdddd] bg-[#f8fbfa] px-4 text-xs font-bold text-[#41636a] shadow-sm transition hover:-translate-y-0.5 hover:bg-[#e7f2ef]">
              <RefreshCw size={15} className={refreshed ? 'animate-spin' : ''} />
              {refreshed ? 'تم التحديث' : 'تحديث البيانات'}
            </button>
          </div>
        }
      />
      <div className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <MetricCard label="أعضاء الخادم" value={displayValue(state.memberCount)} detail="القيمة الحالية من Discord" icon={UsersRound} accent="mint" testId="member-count" />
        <MetricCard label="أوامر Slash" value={displayValue(state.commandCount)} detail="عدد الأوامر المحملة في البوت" icon={Zap} accent="amber" testId="command-count" />
        <MetricCard label="حالة الصوت" value={state.voiceStatus ?? '—'} detail="الحالة الحالية لاتصال البوت" icon={Headphones} accent="blue" testId="voice-status" />
        <MetricCard label="إعدادات مفعلة" value={displayValue(state.activeModules)} detail="من إعدادات السيرفر المعروفة" icon={Activity} accent="coral" testId="active-modules" />
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        <SectionCard title="نبض الخادم" description="آخر الأحداث التي تحتاج انتباهك" testId="recent-activity">
          <div className="divide-y divide-[#e7edec]">
            {state.recentActivity.length === 0 && (
              <div className="px-5 py-8 text-center text-xs text-[#809398]">لا توجد بيانات أحداث موثقة من البوت حتى الآن.</div>
            )}
            {state.recentActivity.map((item) => (
              <div key={item.id} data-testid={`row-activity-${item.id}`} className="flex items-center gap-3 px-5 py-4 transition hover:bg-[#f1f6f4]">
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${item.tone === 'mint' ? 'bg-[#def0e9] text-[#39846f]' : item.tone === 'amber' ? 'bg-[#f9ecd5] text-[#ad742c]' : item.tone === 'coral' ? 'bg-[#f7e2dd] text-[#b45e52]' : 'bg-[#deebf2] text-[#4a7991]'}`}>
                  {item.tone === 'mint' ? <CircleCheck size={17} /> : item.tone === 'amber' ? <MessageSquare size={17} /> : item.tone === 'coral' ? <ShieldCheck size={17} /> : <Headphones size={17} />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-bold text-[#315058]" data-testid={`text-activity-title-${item.id}`}>{item.title}</p>
                  <p className="mt-1 truncate text-[11px] text-[#809398]" data-testid={`text-activity-detail-${item.id}`}>{item.detail}</p>
                </div>
                <span className="shrink-0 text-[10px] text-[#97a8ab]" data-testid={`text-activity-time-${item.id}`}>{item.time}</span>
              </div>
            ))}
          </div>
          <div className="border-t border-[#e7edec] px-5 py-3">
            <Link href="/moderation" data-testid="link-view-all-activity" className="inline-flex items-center gap-1 text-[11px] font-bold text-[#398674] hover:text-[#226956]">عرض سجل الإشراف <ChevronLeft size={14} /></Link>
          </div>
        </SectionCard>
        <SectionCard title="حالة الأنظمة" description="الحالة المستلمة من إعدادات البوت" testId="system-health">
          <div className="subtle-grid relative m-5 overflow-hidden rounded-xl border border-[#dfe9e6] bg-[#edf7f3] p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] font-bold text-[#4f7476]">حالة الاتصال</p>
                <p className="mt-1 font-mono-data text-2xl font-bold text-[#276858]" data-testid="value-uptime">{state.botOnline ? 'متصل' : 'غير متصل'}</p>
              </div>
              <span className="flex h-11 w-11 items-center justify-center rounded-full border-[5px] border-[#78c4ae] border-l-[#d0e7e0] text-[#337c6b]"><Check size={18} /></span>
            </div>
            <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-[#d2e6df]"><div className={`h-full w-full rounded-full ${state.botOnline ? 'bg-[#67bba6]' : 'bg-[#d77867]'}`} /></div>
            <div className="mt-2 flex justify-between text-[10px] text-[#789794]"><span>{formatUpdatedAt(state.lastUpdated)}</span><span className="font-mono-data">{state.serverId ?? '—'}</span></div>
          </div>
          <div className="space-y-1 px-5 pb-4">
            {systems.map(({ label, enabled, icon: Icon }, index) => (
              <div key={String(label)} data-testid={`row-system-${index}`} className="flex items-center gap-3 rounded-xl px-2 py-2.5">
                <Icon size={15} className={enabled ? 'text-[#479b84]' : 'text-[#be6d62]'} />
                <span className="flex-1 text-xs font-semibold text-[#49666b]">{label as string}</span>
                <span className={`text-[10px] font-bold ${enabled ? 'text-[#45977e]' : 'text-[#b25d53]'}`}>{enabled ? 'يعمل' : 'متوقف'}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="ملخص الإشراف" description="الأرقام المعروفة من قاعدة البيانات" testId="moderation-summary">
          <div className="flex items-center gap-6 px-5 py-5">
            <div className="flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-full border border-dashed border-[#b9d6cd] bg-[#eef7f3]">
              <span className="font-mono-data text-xl font-bold text-[#2c4b52]" data-testid="value-moderation-total">{totalModeration}</span>
              <span className="text-[10px] text-[#8b9d9f]">تحذير معروف</span>
            </div>
            <div className="grid flex-1 grid-cols-2 gap-y-3">
              {Object.entries(state.moderationCounts).map(([key, value], index) => {
                const labels = ['محظور', 'تحذير', 'كتم', 'حظر نهائي'];
                const colors = ['#d27668', '#e7b65b', '#65bba5', '#769eaf'];
                return <div key={key} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: colors[index] }} /><span className="text-[11px] text-[#70868b]">{labels[index]}</span><span className="font-mono-data mr-auto text-xs font-bold text-[#416169]" data-testid={`value-moderation-${key}`}>{displayValue(value)}</span></div>;
              })}
            </div>
          </div>
        </SectionCard>
        <SectionCard title="تبديلات سريعة" description="أكثر الوحدات استخداماً" testId="quick-controls">
          <div className="grid gap-2 p-4 sm:grid-cols-3">
            {[
              { key: 'automodEnabled' as const, icon: ShieldCheck, label: 'الحماية التلقائية', detail: 'فلترة فورية' },
              { key: 'welcomeEnabled' as const, icon: UsersRound, label: 'رسائل الترحيب', detail: 'العضو الجديد' },
              { key: 'logsEnabled' as const, icon: ListChecks, label: 'سجل الأحداث', detail: 'مراقبة النشاط' },
            ].map(({ key, icon: Icon, label, detail }) => (
              <div key={key} data-testid={`control-quick-${key}`} className="flex items-center gap-3 rounded-xl border border-[#e1e9e7] bg-[#f4f8f7] px-3 py-3">
                <span className="rounded-lg bg-[#e1eee9] p-2 text-[#438d78]"><Icon size={15} /></span>
                <div className="min-w-0 flex-1"><p className="truncate text-[11px] font-bold text-[#466269]">{label}</p><p className="mt-0.5 text-[10px] text-[#8ba0a3]">{detail}</p></div>
                <Toggle checked={state[key]} onToggle={() => toggle(key)} label={`تبديل ${label}`} testId={`toggle-${key}`} />
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </>
  );
}

function ControlRow({ title, description, checked, onToggle, icon: Icon, testId }: { title: string; description: string; checked: boolean; onToggle: () => void; icon: typeof ShieldCheck; testId: string }) {
  return (
    <div data-testid={`row-control-${testId}`} className="flex items-center gap-3 px-5 py-4">
      <span className={`rounded-xl p-2.5 ${checked ? 'bg-[#e0f1ec] text-[#37846f]' : 'bg-[#edf1f1] text-[#87999d]'}`}><Icon size={17} /></span>
      <div className="min-w-0 flex-1"><p className="text-xs font-bold text-[#3c5960]">{title}</p><p className="mt-1 text-[11px] text-[#8b9da0]">{description}</p></div>
      <Toggle checked={checked} onToggle={onToggle} label={`تبديل ${title}`} testId={`toggle-${testId}`} />
    </div>
  );
}

function ModerationPage({ state, toggle }: { state: DashboardState; toggle: (field: ToggleField) => void }) {
  const [filterLinks, setFilterLinks] = useState(true);
  const [filterSpam, setFilterSpam] = useState(true);
  const [slowMode, setSlowMode] = useState(false);
  const [ruleAdded, setRuleAdded] = useState(false);
  const [exported, setExported] = useState(false);
  return (
    <>
      <PageHeader eyebrow="الحماية والانضباط" title="الإشراف" description="قواعد واضحة، قرارات أسرع، وسجل يشرح ما حدث دون ضجيج." action={<button type="button" onClick={() => setRuleAdded(true)} data-testid="button-add-moderation-rule" className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#367e6d] px-4 text-xs font-bold text-[#f5fbf8] shadow-sm hover:bg-[#2d6f60]"><Plus size={15} /> {ruleAdded ? 'تمت إضافة قاعدة' : 'قاعدة جديدة'}</button>} />
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="تم حظره" value={displayValue(state.moderationCounts.blocked)} detail="غير متاح من المصدر الحالي" icon={ShieldCheck} accent="coral" testId="blocked-count" />
        <MetricCard label="تحذيرات" value={displayValue(state.moderationCounts.warned)} detail="من سجل التحذيرات في قاعدة البيانات" icon={CircleAlert} accent="amber" testId="warned-count" />
        <MetricCard label="حالات كتم" value={displayValue(state.moderationCounts.muted)} detail="غير متاح من المصدر الحالي" icon={LockKeyhole} accent="blue" testId="muted-count" />
        <MetricCard label="حظر نهائي" value={displayValue(state.moderationCounts.banned)} detail="غير متاح من المصدر الحالي" icon={CircleCheck} accent="mint" testId="banned-count" />
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="قواعد الحماية" description="الحالة الحالية فقط؛ التعديل الفعلي يحتاج API إضافي" testId="moderation-rules">
          <div className="divide-y divide-[#e7edec]">
            <ControlRow title="الحماية التلقائية" description="التقاط السلوك المزعج قبل أن ينتشر" checked={state.automodEnabled} onToggle={() => toggle('automodEnabled')} icon={ShieldCheck} testId="automod" />
            <ControlRow title="فلترة الروابط" description="منع الروابط غير الموثوقة للأعضاء الجدد" checked={filterLinks} onToggle={() => setFilterLinks(!filterLinks)} icon={LockKeyhole} testId="link-filter" />
            <ControlRow title="حماية السبام" description="رصد التكرار والرسائل المتتالية" checked={filterSpam} onToggle={() => setFilterSpam(!filterSpam)} icon={Zap} testId="spam-filter" />
            <ControlRow title="الوضع البطيء الذكي" description="اقتراح تباطؤ القناة عند ارتفاع النشاط" checked={slowMode} onToggle={() => setSlowMode(!slowMode)} icon={Activity} testId="slow-mode" />
          </div>
          <div className="border-t border-[#e7edec] bg-[#f4f8f7] px-5 py-3 text-[11px] text-[#6e878b]">مصدر الحالة: <span className="font-semibold text-[#47746d]" data-testid="text-moderation-last-edit">{formatUpdatedAt(state.lastUpdated)}</span></div>
        </SectionCard>
        <SectionCard title="إعدادات السجل" description="ما الذي يظهر في قناة المراجعة؟" testId="moderation-logs">
          <div className="space-y-1 px-5 py-4">
            <ControlRow title="تسجيل الأحداث" description="احتفظ بسجل كامل للإجراءات" checked={state.logsEnabled} onToggle={() => toggle('logsEnabled')} icon={ListChecks} testId="logs" />
            <div className="mt-3 border-t border-[#e7edec] pt-4">
              <label htmlFor="log-channel" className="mb-2 block text-[11px] font-bold text-[#537178]">قناة السجل</label>
              <select id="log-channel" data-testid="select-log-channel" className="h-10 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none focus:border-[#69b49f]"><option># سجل-المشرفين</option><option># غرفة-العمليات</option><option># أرشيف-الخادم</option></select>
            </div>
            <button type="button" onClick={() => setExported(true)} data-testid="button-export-moderation-log" className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-[#cee0da] py-2.5 text-[11px] font-bold text-[#3b806e] hover:bg-[#ebf5f1]"><RotateCcw size={14} /> {exported ? 'تم تجهيز الملخص' : 'تصدير ملخص الإجراءات'}</button>
          </div>
        </SectionCard>
      </div>
    </>
  );
}

function CommunityPage({ state, toggle }: { state: DashboardState; toggle: (field: ToggleField) => void }) {
  const [preview, setPreview] = useState(false);
  const [reactionRolesManaged, setReactionRolesManaged] = useState(false);
  const [ticketSystem, setTicketSystem] = useState(true);
  const [ticketAutoClose, setTicketAutoClose] = useState(true);
  const [suggestionReview, setSuggestionReview] = useState(true);
  return (
    <>
      <PageHeader eyebrow="مساحة التفاعل" title="المجتمع" description="اجعل دخول الأعضاء أسهل، وامنح الأفكار مساراً واضحاً من الرسالة إلى القرار." action={<button type="button" onClick={() => setPreview(!preview)} data-testid="button-preview-welcome" className="inline-flex h-10 items-center gap-2 rounded-xl border border-[#cfdddd] bg-[#f8fbfa] px-4 text-xs font-bold text-[#41636a] hover:bg-[#e6f1ee]"><MessageSquare size={15} /> {preview ? 'إخفاء المعاينة' : 'معاينة الترحيب'}</button>} />
      {preview && <div data-testid="panel-welcome-preview" className="mb-5 rounded-2xl border border-[#cfe4dc] bg-[#e9f7f2] px-5 py-4"><p className="text-xs font-bold text-[#347765]">معاينة رسالة #البهو</p><p className="mt-2 text-sm text-[#466c6e]">أهلاً بك في Alythia، يسعدنا وجودك هنا. اختر دورك وابدأ من المكان الذي يناسبك.</p></div>}
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="تذاكر مفتوحة" value={displayValue(state.ticketCount)} detail="غير متاح من المصدر الحالي" icon={Ticket} accent="blue" testId="ticket-count" />
        <MetricCard label="اقتراحات معلقة" value={displayValue(state.suggestionCount)} detail="حالة pending من قاعدة البيانات" icon={MessageSquare} accent="amber" testId="suggestion-count" />
        <MetricCard label="الترحيب" value={state.dataAvailable ? (state.welcomeEnabled ? 'مهيأ' : 'غير مهيأ') : '—'} detail="حسب قناة الترحيب المحفوظة" icon={UsersRound} accent="mint" testId="welcome-status" />
        <MetricCard label="تفاعل الأعضاء" value="—" detail="غير متاح من المصدر الحالي" icon={Activity} accent="coral" testId="engagement-rate" />
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="الترحيب والأدوار" description="الانطباع الأول يبدأ قبل أول رسالة" testId="welcome-settings">
          <div className="divide-y divide-[#e7edec]">
            <ControlRow title="رسائل الترحيب" description="رسالة شخصية لكل عضو جديد" checked={state.welcomeEnabled} onToggle={() => toggle('welcomeEnabled')} icon={UsersRound} testId="welcome" />
            <div className="grid gap-3 px-5 py-4 sm:grid-cols-2">
              <div><label htmlFor="welcome-channel" className="mb-2 block text-[11px] font-bold text-[#537178]">قناة الترحيب</label><select id="welcome-channel" data-testid="select-welcome-channel" className="h-10 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none focus:border-[#69b49f]"><option># البهو</option><option># بداية-الطريق</option></select></div>
              <div><label htmlFor="welcome-style" className="mb-2 block text-[11px] font-bold text-[#537178]">نمط الرسالة</label><select id="welcome-style" data-testid="select-welcome-style" className="h-10 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none focus:border-[#69b49f]"><option>مختصر وودود</option><option>تفصيلي</option></select></div>
            </div>
            <div className="flex items-center gap-3 px-5 py-4"><span className="rounded-xl bg-[#e7edf4] p-2.5 text-[#5e8194]"><SlidersHorizontal size={17} /></span><div className="flex-1"><p className="text-xs font-bold text-[#3c5960]">الأدوار التلقائية</p><p className="mt-1 text-[11px] text-[#8b9da0]">اختيار الدور من رسالة الترحيب</p></div><button type="button" onClick={() => setReactionRolesManaged(!reactionRolesManaged)} data-testid="button-manage-reaction-roles" className="rounded-lg px-2 py-1 text-[11px] font-bold text-[#3c8874] hover:bg-[#e9f4f0]">{reactionRolesManaged ? 'تم الفتح' : 'إدارة الأدوار'}</button></div>
          </div>
        </SectionCard>
        <SectionCard title="التذاكر والاقتراحات" description="قنوات منظمة لصوت المجتمع" testId="community-workflows">
          <div className="divide-y divide-[#e7edec]">
            <ControlRow title="نظام التذاكر" description="افتح مساحة خاصة لكل طلب" checked={ticketSystem} onToggle={() => setTicketSystem(!ticketSystem)} icon={Ticket} testId="tickets" />
            <ControlRow title="الإغلاق التلقائي" description="إغلاق التذاكر الخاملة بعد 72 ساعة" checked={ticketAutoClose} onToggle={() => setTicketAutoClose(!ticketAutoClose)} icon={RotateCcw} testId="ticket-auto-close" />
            <ControlRow title="مراجعة الاقتراحات" description="نشر الاقتراحات بعد موافقة المشرف" checked={suggestionReview} onToggle={() => setSuggestionReview(!suggestionReview)} icon={MessageSquare} testId="suggestion-review" />
              <div className="flex items-center justify-between px-5 py-4"><div><p className="text-xs font-bold text-[#3c5960]">قناة التذاكر</p><p className="mt-1 text-[11px] text-[#8b9da0]">غير متاحة من API الحالي</p></div><button type="button" disabled data-testid="button-open-tickets" className="inline-flex cursor-not-allowed items-center gap-1 rounded-lg bg-[#e6f2ee] px-3 py-2 text-[11px] font-bold text-[#8ca59f]">غير متاح <ChevronLeft size={13} /></button></div>
          </div>
        </SectionCard>
      </div>
    </>
  );
}

function EconomyPage({ state, toggle }: { state: DashboardState; toggle: (field: ToggleField) => void }) {
  const [dailyRewards, setDailyRewards] = useState(true);
  const [currencyName, setCurrencyName] = useState('Lyria');
  const [leaderboardShown, setLeaderboardShown] = useState(false);
  return (
    <>
      <PageHeader eyebrow="النمو والمكافآت" title="الاقتصاد والمستويات" description="حلقة تقدم صغيرة تجعل الأعضاء يعودون، من دون أن تتحول إلى ضوضاء." action={<button type="button" onClick={() => setLeaderboardShown(!leaderboardShown)} data-testid="button-economy-leaderboard" className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#367e6d] px-4 text-xs font-bold text-[#f5fbf8] hover:bg-[#2d6f60]"><Coins size={15} /> {leaderboardShown ? 'إخفاء المتصدرين' : 'لوحة المتصدرين'}</button>} />
      {leaderboardShown && <div data-testid="panel-economy-leaderboard" className="mb-5 rounded-2xl border border-[#d9e7e2] bg-[#edf7f3] p-5 text-center text-xs text-[#6f8986]">لا توجد بيانات متصدرين موثقة في Endpoint الحالة الحالي.</div>}
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="مستخدمو الاقتصاد" value={displayValue(state.economyUserCount)} detail="من جدول الاقتصاد في قاعدة البيانات" icon={Coins} accent="amber" testId="currency-supply" />
        <MetricCard label="رسائل اليوم" value="—" detail="غير متاح من المصدر الحالي" icon={MessageSquare} accent="blue" testId="daily-messages" />
        <MetricCard label="مستخدمو المستويات" value={displayValue(state.levelUserCount)} detail="من جدول المستويات في قاعدة البيانات" icon={Zap} accent="mint" testId="popular-level" />
        <MetricCard label="المكافآت اليومية" value="—" detail="غير متاح من المصدر الحالي" icon={CircleCheck} accent="coral" testId="daily-rewards" />
      </div>
      <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <SectionCard title="المحركات" description="حدد ما يدفع المجتمع إلى الأمام" testId="economy-controls">
          <div className="divide-y divide-[#e7edec]">
            <ControlRow title="نظام الاقتصاد" description="عملة، متجر، وتحويلات بين الأعضاء" checked={state.economyEnabled} onToggle={() => toggle('economyEnabled')} icon={Coins} testId="economy" />
            <ControlRow title="نظام المستويات" description="تقدم مبني على المشاركة المفيدة" checked={state.levelEnabled} onToggle={() => toggle('levelEnabled')} icon={Zap} testId="levels" />
            <ControlRow title="المكافأة اليومية" description="حافز صغير للعودة كل يوم" checked={dailyRewards} onToggle={() => setDailyRewards(!dailyRewards)} icon={CircleCheck} testId="daily-rewards-toggle" />
          </div>
          <div className="border-t border-[#e7edec] px-5 py-4">
            <label htmlFor="currency-name" className="mb-2 block text-[11px] font-bold text-[#537178]">اسم العملة</label>
            <input id="currency-name" value={currencyName} onChange={(event) => setCurrencyName(event.target.value)} data-testid="input-currency-name" className="h-10 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none focus:border-[#69b49f]" />
          </div>
        </SectionCard>
        <SectionCard title="توزيع المستويات" description="لقطة من مسار التقدم داخل Alythia" testId="level-distribution">
          <div className="space-y-4 px-5 py-5">
            <div className="rounded-xl border border-dashed border-[#cbded8] px-4 py-8 text-center text-xs text-[#78908c]">توزيع المستويات التفصيلي غير متاح من Endpoint الحالة الحالي.</div>
          </div>
          <div className="mx-5 mb-5 rounded-xl border border-[#dfe9e6] bg-[#eef7f3] px-4 py-3 text-[11px] text-[#66837f]"><span className="font-bold text-[#337766]">مصدر البيانات:</span> عدد المستخدمين المسجلين فقط متاح حاليًا.</div>
        </SectionCard>
      </div>
    </>
  );
}

function VoicePage({ state }: { state: DashboardState }) {
  const actualVoiceConnected = state.voiceStatus?.startsWith('متصل') ?? false;
  const active = actualVoiceConnected;
  const channel = state.voiceStatus ?? 'غير متاح';
  const [channelsShown, setChannelsShown] = useState(false);
  return (
    <>
      <PageHeader eyebrow="الحضور المباشر" title="الصوت" description="الحالة الفعلية لاتصال البوت بالروم الصوتي." action={<button type="button" disabled data-testid="button-toggle-voice" className={`inline-flex cursor-not-allowed items-center gap-2 rounded-xl px-4 text-xs font-bold shadow-sm ${active ? 'bg-[#367e6d] text-[#f5fbf8]' : 'border border-[#d5e1e0] bg-[#f8fbfa] text-[#567078]'}`}><Radio size={15} /> {active ? 'البوت متصل' : 'البوت غير متصل'}</button>} />
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="حالة اتصال البوت" value={active ? 'متصل' : 'غير متصل'} detail="من الحالة المباشرة" icon={Headphones} accent="mint" testId="voice-members" />
        <MetricCard label="زمن الاستجابة" value="—" detail="غير متاح من المصدر الحالي" icon={Wifi} accent="blue" testId="voice-latency" />
        <MetricCard label="أعلى حضور" value="—" detail="غير متاح من المصدر الحالي" icon={UsersRound} accent="amber" testId="voice-peak" />
        <MetricCard label="جلسات اليوم" value="—" detail="غير متاح من المصدر الحالي" icon={Activity} accent="coral" testId="voice-sessions" />
      </div>
      {channelsShown && <div data-testid="panel-voice-channels" className="mb-5 rounded-2xl border border-[#d9e7e2] bg-[#edf7f3] p-5 text-center text-xs text-[#6f8986]">تفاصيل القنوات الصوتية غير متاحة من Endpoint الحالة الحالي.</div>}
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionCard title="الحضور الآن" description="تحديث حيّ كل 30 ثانية" testId="live-voice-presence">
          <div className="divide-y divide-[#e7edec]">
            <div className="px-5 py-8 text-center text-xs text-[#809398]">لا توجد بيانات حضور أعضاء موثقة من Endpoint الحالة الحالي.</div>
          </div>
          <div className="flex items-center justify-between border-t border-[#e7edec] px-5 py-3"><span className="text-[11px] text-[#829699]" data-testid="text-voice-total">القناة الحالية: {channel}</span><button type="button" onClick={() => setChannelsShown(!channelsShown)} data-testid="button-view-voice-channels" className="text-[11px] font-bold text-[#3a8471]">{channelsShown ? 'إخفاء القنوات' : 'عرض القنوات'} <ChevronLeft size={13} className="mr-1 inline" /></button></div>
        </SectionCard>
        <SectionCard title="التحكم الصوتي" description="اتصال البوت بالقنوات" testId="voice-controls">
          <div className="space-y-4 px-5 py-5">
            <div className={`rounded-xl border p-4 ${active ? 'border-[#cfe4dc] bg-[#eef8f4]' : 'border-[#e7dddd] bg-[#faf1ef]'}`}><div className="flex items-center gap-3"><span className={`rounded-lg p-2 ${active ? 'bg-[#d5ede4] text-[#38836e]' : 'bg-[#f1dcda] text-[#ac5f55]'}`}>{active ? <Wifi size={17} /> : <WifiOff size={17} />}</span><div><p className="text-xs font-bold text-[#3c5960]">{active ? 'الاتصال مستقر' : 'الاتصال متوقف'}</p><p className="mt-1 text-[10px] text-[#829699]">{active ? 'آخر اتصال منذ 42 ثانية' : 'شغّل الاتصال لاستعادة الحضور'}</p></div></div></div>
            <div><label htmlFor="voice-channel" className="mb-2 block text-[11px] font-bold text-[#537178]">القناة الحالية</label><input id="voice-channel" value={channel} readOnly data-testid="select-voice-channel" className="h-10 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none" /></div>
            <ControlRow title="الانضمام التلقائي" description="غير متاح للتعديل من API الحالي" checked={false} onToggle={() => undefined} icon={Headphones} testId="voice-auto-join" />
          </div>
        </SectionCard>
      </div>
    </>
  );
}

function SettingsPage({ state, toggle, setState }: { state: DashboardState; toggle: (field: ToggleField) => void; setState: React.Dispatch<React.SetStateAction<DashboardState>> }) {
  const [saved, setSaved] = useState(false);
  return (
    <>
      <PageHeader eyebrow="تفضيلات المركز" title="الإعدادات" description="اضبط هوية الخادم وسلوك لوحة التحكم بما يناسب فريقك." action={<button type="button" onClick={() => setSaved(true)} data-testid="button-save-settings" className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#367e6d] px-4 text-xs font-bold text-[#f5fbf8] hover:bg-[#2d6f60]"><Save size={15} /> {saved ? 'تم الحفظ' : 'حفظ التغييرات'}</button>} />
      {saved && <div data-testid="status-settings-saved" className="mb-5 flex items-center gap-2 rounded-xl border border-[#c9e4da] bg-[#eaf7f1] px-4 py-3 text-xs font-semibold text-[#347b68]"><Check size={15} /> تم حفظ تفضيلات Alythia محلياً</div>}
      <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <SectionCard title="هوية الخادم" description="كيف يظهر Alythia لفريق الإشراف" testId="server-identity">
          <div className="space-y-4 px-5 py-5">
            <div><label htmlFor="server-name" className="mb-2 block text-[11px] font-bold text-[#537178]">اسم الخادم</label><input id="server-name" value={state.serverName ?? ''} onChange={(event) => { setSaved(false); setState((current) => ({ ...current, serverName: event.target.value })); }} data-testid="input-server-name" className="h-11 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-sm text-[#46646b] outline-none focus:border-[#69b49f]" /></div>
            <div><label htmlFor="timezone" className="mb-2 block text-[11px] font-bold text-[#537178]">المنطقة الزمنية</label><select id="timezone" data-testid="select-timezone" className="h-11 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none focus:border-[#69b49f]"><option>الرياض — GMT+3</option><option>دبي — GMT+4</option><option>القاهرة — GMT+2</option></select></div>
            <div><label htmlFor="language" className="mb-2 block text-[11px] font-bold text-[#537178]">لغة لوحة التحكم</label><select id="language" data-testid="select-dashboard-language" className="h-11 w-full rounded-xl border border-[#d4e0df] bg-[#f6faf9] px-3 text-xs text-[#46646b] outline-none focus:border-[#69b49f]"><option>العربية</option><option>English</option></select></div>
          </div>
        </SectionCard>
        <SectionCard title="سلوك الوحدات" description="تفضيلات تشغيلية خاصة بهذا الخادم" testId="server-preferences">
          <div className="divide-y divide-[#e7edec]">
            <ControlRow title="رسائل الترحيب" description="فعّل استقبال الأعضاء الجدد" checked={state.welcomeEnabled} onToggle={() => toggle('welcomeEnabled')} icon={UsersRound} testId="settings-welcome" />
            <ControlRow title="سجلات الأحداث" description="احفظ القرارات والتغييرات المهمة" checked={state.logsEnabled} onToggle={() => toggle('logsEnabled')} icon={ListChecks} testId="settings-logs" />
            <ControlRow title="الحماية التلقائية" description="راقب المحتوى المزعج تلقائياً" checked={state.automodEnabled} onToggle={() => toggle('automodEnabled')} icon={ShieldCheck} testId="settings-automod" />
          </div>
          <div className="border-t border-[#e7edec] px-5 py-4"><button type="button" onClick={() => setState(initialState)} data-testid="button-reset-settings" className="inline-flex items-center gap-2 rounded-lg px-2 py-1 text-[11px] font-bold text-[#a35c54] hover:bg-[#faece9]"><RotateCcw size={14} /> استعادة الإعدادات الأولية</button></div>
        </SectionCard>
      </div>
      <div className="mt-5 rounded-2xl border border-[#d9e3e3] bg-[#e9f2ef] px-5 py-4"><div className="flex items-start gap-3"><span className="rounded-lg bg-[#d0e8de] p-2 text-[#3c806d]"><Server size={16} /></span><div><p className="text-xs font-bold text-[#3c625f]">اتصال آمن بالخادم</p><p className="mt-1 text-[11px] text-[#76908f]">تُحفظ هذه التفضيلات محلياً في هذه النسخة التجريبية. لن تتأثر إعدادات Discord الحالية.</p></div></div></div>
    </>
  );
}

function Router({ state, toggle, setState, refresh }: { state: DashboardState; toggle: (field: ToggleField) => void; setState: React.Dispatch<React.SetStateAction<DashboardState>>; refresh: () => void }) {
  const [location] = useLocation();
  return (
    <Shell state={state}>
      <ErrorBoundary resetKey={location}>
        <Switch>
          <Route path="/" component={() => <OverviewPage state={state} toggle={toggle} refresh={refresh} />} />
          <Route path="/moderation" component={() => <ModerationPage state={state} toggle={toggle} />} />
          <Route path="/community" component={() => <CommunityPage state={state} toggle={toggle} />} />
          <Route path="/economy" component={() => <EconomyPage state={state} toggle={toggle} />} />
          <Route path="/voice" component={() => <VoicePage state={state} />} />
          <Route path="/settings" component={() => <SettingsPage state={state} toggle={toggle} setState={setState} />} />
          <Route component={NotFound} />
        </Switch>
      </ErrorBoundary>
    </Shell>
  );
}

function AppContent() {
  const { data, isError, refetch } = useGetAlythiaStatus();
  const [state, setState] = useState<DashboardState>(() => createDashboardState(data));
  useEffect(() => {
    setState(createDashboardState(data));
  }, [data]);
  const toggle = (field: ToggleField) => setState((current) => ({ ...current, [field]: !current[field] }));
  return (
    <TooltipProvider>
      <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
        <Router state={state} toggle={toggle} setState={setState} refresh={() => { void refetch(); }} />
      </WouterRouter>
      {isError && <div className="fixed bottom-4 left-4 z-50 rounded-xl border border-[#e8c8c2] bg-[#fff7f5] px-4 py-3 text-xs font-semibold text-[#a45a51] shadow-lg">تعذر جلب حالة البوت من API.</div>}
      <Toaster />
    </TooltipProvider>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
