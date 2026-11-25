import React, { useEffect, useRef, useState } from 'react'
import { apiRequest } from './api.js'
import {
  Activity, ArrowDownToLine, ArrowRight, BarChart3, Bell, Boxes, CalendarClock,
  Check, ChevronDown, CircleHelp, Cpu, Database, Gauge, HardDrive, LayoutDashboard,
  ListChecks, LogOut, Menu, Plus, RefreshCw, Server, ShieldCheck, Upload, X,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'

const navigation = [
  { name: 'Dashboard', icon: LayoutDashboard },
  { name: 'Workloads', icon: ListChecks },
  { name: 'Predictions', icon: Activity },
  { name: 'VM Manager', icon: Server },
  { name: 'Scheduler', icon: CalendarClock },
  { name: 'Monitoring', icon: Gauge },
  { name: 'Analytics', icon: BarChart3 },
]

const initialVms = [
  { name: 'vm-burst-01', type: 't3.medium', zone: 'us-east-1', cpu: 32, memory: 48, cost: 0.04, tier: 'basic', status: 'running' },
  { name: 'vm-compute-01', type: 'c5.xlarge', zone: 'ap-south-1', cpu: 64, memory: 32, cost: 0.31, tier: 'premium', status: 'running' },
  { name: 'vm-general-01', type: 't3.large', zone: 'ap-south-1', cpu: 52, memory: 68, cost: 0.08, tier: 'standard', status: 'running' },
  { name: 'vm-memory-01', type: 'r5.xlarge', zone: 'ap-south-1', cpu: 24, memory: 72, cost: 0.25, tier: 'premium', status: 'running' },
]

const chartData = [
  { time: '10:00', cpu: 26, memory: 34 }, { time: '10:05', cpu: 32, memory: 38 },
  { time: '10:10', cpu: 29, memory: 42 }, { time: '10:15', cpu: 44, memory: 40 },
  { time: '10:20', cpu: 38, memory: 48 }, { time: '10:25', cpu: 52, memory: 46 },
  { time: '10:30', cpu: 47, memory: 53 }, { time: '10:35', cpu: 58, memory: 49 },
]

function Metric({ label, value, detail, icon: Icon, tone = 'teal' }) {
  return <div className="metric"><div className="metric-top"><span>{label}</span><Icon size={16} className={`tone-${tone}`} /></div><strong>{value}</strong><small>{detail}</small></div>
}

function Panel({ title, action, children, className = '' }) {
  return <section className={`panel ${className}`}><div className="panel-heading"><h2>{title}</h2>{action}</div>{children}</section>
}

function EmptyRow({ message, columns = 6 }) {
  return <tr><td className="empty-row" colSpan={columns}>{message}</td></tr>
}

function LiveMonitor() {
  const readings = [
    { title: 'CPU utilization', icon: Cpu },
    { title: 'Memory utilization', icon: Database },
    { title: 'Disk utilization', icon: HardDrive },
  ]
  return <Panel title="Live system monitoring" action={<span className="offline"><i /> System monitor offline</span>} className="monitor-panel">
    <div className="live-grid">{readings.map(({ title, icon: Icon }) => <div className="live-reading" key={title}><div className="reading-label"><Icon size={14} />{title}</div><strong>--</strong><small className="unavailable">Unavailable</small></div>)}</div>
    <div className="system-specs"><div><Cpu size={14} /><span>CPU model</span><b>--</b></div><div><Boxes size={14} /><span>CPU cores</span><b>--</b></div><div><Server size={14} /><span>Logical processors</span><b>--</b></div><div><Activity size={14} /><span>System uptime</span><b>--</b></div></div>
    <p className="monitor-note">Smart Memory Allocation and Intelligent Resource Scheduling for Cloud Workloads.</p>
  </Panel>
}

function Dashboard({ workloads, setPage }) {
  return <>
    <div className="page-title"><div><h1>Dashboard</h1><p>Cluster health at a glance</p></div><button className="button ghost"><Bell size={15} /><span>Alerts</span><b className="alert-count">2</b></button></div>
    <div className="metrics-grid">
      <Metric label="Active workloads" value={workloads.filter((item) => item.status === 'Running').length} detail={`${workloads.length} total`} icon={ListChecks} />
      <Metric label="Active VMs" value="4" detail="Across 3 regions" icon={Server} />
      <Metric label="CPU utilization" value="32.5%" detail="+2.4% from last hour" icon={Cpu} />
      <Metric label="Memory utilization" value="36.3%" detail="Within healthy range" icon={Database} />
      <Metric label="Estimated cost" value="$0.54/h" detail="$12.96 projected daily" icon={Activity} />
      <Metric label="SLA compliance" value="100%" detail="No breaches this week" icon={ShieldCheck} />
    </div>
    <LiveMonitor />
    <div className="dashboard-lower">
      <Panel title="Cluster utilization · sample data" action={<button className="select-button">Last 8 hours <ChevronDown size={13} /></button>}>
        <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><defs><linearGradient id="cpuFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#11d2c5" stopOpacity={0.23} /><stop offset="95%" stopColor="#11d2c5" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#25333e" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#8494a2', fontSize: 10 }} /><YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#8494a2', fontSize: 10 }} tickFormatter={(value) => `${value}%`} /><Tooltip contentStyle={{ background: '#101a23', border: '1px solid #2a3944', borderRadius: 6, color: '#e9f1f4', fontSize: 11 }} /><Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 10, color: '#9aaab6' }} /><Area type="monotone" dataKey="cpu" name="CPU" stroke="#12d4c6" strokeWidth={2} fill="url(#cpuFill)" /><Line type="monotone" dataKey="memory" name="Memory" stroke="#bb8cf3" strokeWidth={2} dot={false} /></AreaChart></ResponsiveContainer></div>
      </Panel>
      <Panel title="Recent workloads" action={<button className="text-button" onClick={() => setPage('Workloads')}>View all <ArrowRight size={13} /></button>}>
        {workloads.length ? <div className="recent-list">{workloads.slice(0, 4).map((item) => <div className="recent-item" key={item.name}><span className="workload-dot" /><div><b>{item.name}</b><small>{item.type} · {item.cpu} vCPU · {item.memory} GB</small></div><span className={`status ${item.status.toLowerCase()}`}>{item.status}</span></div>)}</div> : <p className="muted">No workloads yet. Create one on the Workloads page.</p>}
      </Panel>
    </div>
  </>
}

function Workloads({ workloads, onCreateWorkload }) {
  const [form, setForm] = useState({
    name: '',
    type: 'batch',
    sla: 'standard',
    duration: 30,
  })
  const [prediction, setPrediction] = useState(null)
  const [saving, setSaving] = useState(false)
  const [estimating, setEstimating] = useState(false)
  const [error, setError] = useState('')
  const update = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    if (name === 'type') setPrediction(null)
  }
  const requestEstimate = async () => {
    setError('')
    try {
      const categoriesByType = {
        batch: { dataSource: 'Cloud', taskType: 'Data Processing' },
        service: { dataSource: 'Cloud', taskType: 'Cloud Service' },
        inference: { dataSource: 'Cloud', taskType: 'Cloud Service' },
        database: { dataSource: 'Enterprise DB', taskType: 'Database' },
      }
      return await apiRequest('/predictions', {
        method: 'POST',
        body: JSON.stringify({
          ...categoriesByType[form.type],
          activeUsers: 3000,
          processCount: 19,
          vmCpuCores: 4,
          cpuSpeedGHz: 2.5,
          vmMemoryGb: 8,
          memoryRequestedGb: 4,
        }),
      })
    } catch (requestError) {
      setError(requestError.message)
      return null
    }
  }
  const estimateOnly = async () => {
    setEstimating(true)
    const result = await requestEstimate()
    if (result) setPrediction(result)
    setEstimating(false)
  }
  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      let result = prediction
      if (!result) {
        result = await requestEstimate()
        if (!result) return
        setPrediction(result)
      }
      const suggestedCpu = Math.min(4, Math.max(0.1, Math.ceil((result.cpu * 4 / 100) * 10) / 10))
      await onCreateWorkload({
        name: form.name.trim(),
        type: form.type,
        cpu: suggestedCpu,
        memory: result.memory,
        sla: form.sla,
        duration: Number(form.duration),
      })
      setForm((current) => ({ ...current, name: '' }))
      setPrediction(null)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }
  return <>
    <div className="page-title"><div><h1>Workloads</h1><p>Estimate demand and submit jobs through the scheduling pipeline</p></div></div>
    <Panel title="Create workload" className="form-panel">
      <p className="panel-subtitle">Enter the workload basics only. Estimates use a built-in sample profile for the selected type (3,000 active users, 19 processes, 4-core VM, 8 GB memory); actual demand may differ.</p>
      <form className="workload-form" onSubmit={submit}>
        <label>Workload name<input name="name" placeholder="e.g. nightly-etl" value={form.name} onChange={update} required /></label>
        <label>Workload type<select name="type" value={form.type} onChange={update}><option value="batch">batch</option><option value="service">service</option><option value="inference">inference</option><option value="database">database</option></select></label>
        <label>SLA tier<select name="sla" value={form.sla} onChange={update}><option value="standard">standard</option><option value="premium">premium</option><option value="basic">basic</option></select></label>
        <label>Duration (min)<input name="duration" type="number" min="1" value={form.duration} onChange={update} required /></label>
        {prediction && <div className="workload-estimate">
          <b>Estimated CPU utilization: {prediction.cpu}%</b>
          <b>Estimated memory consumption: {prediction.memory} GB</b>
          <span>Resources to be requested: {Math.min(4, Math.max(0.1, Math.ceil((prediction.cpu * 4 / 100) * 10) / 10))} vCPU and {prediction.memory} GB memory.</span>
          {prediction.outOfTrainingRange.length > 0 && <span className="estimate-warning">Outside training range: {prediction.outOfTrainingRange.join(', ')}.</span>}
        </div>}
        <div className="workload-actions">
          <button className="button ghost" type="button" onClick={estimateOnly} disabled={estimating || saving}><Activity size={14} /> {estimating ? 'Estimating…' : 'Estimate only'}</button>
          <button className="button primary" type="submit" disabled={saving || estimating}><Plus size={15} /> {saving ? 'Predicting & creating…' : 'Predict & create workload'}</button>
        </div>
      </form>
      {error && <p className="api-error" role="alert">{error}</p>}
    </Panel>
    <Panel title={`Workload queue · ${workloads.length}`} className="table-panel"><div className="table-scroll"><table><thead><tr><th>Name</th><th>Type</th><th>CPU</th><th>Memory</th><th>Allocated VM</th><th>SLA</th><th>Priority</th><th>Status</th></tr></thead><tbody>{workloads.length ? workloads.map((item, index) => <tr key={`${item.name}-${index}`}><td className="strong-cell">{item.name}</td><td>{item.type}</td><td>{item.cpu} vCPU</td><td>{item.memory} GB</td><td>{item.allocated}</td><td>{item.sla}</td><td>{item.priority}</td><td><span className={`status ${item.status.toLowerCase()}`}>{item.status}</span></td></tr>) : <EmptyRow message="No workloads yet. Submit a job above to get started." columns={8} />}</tbody></table></div></Panel>
  </>
}

function Predictions() {
  const [form, setForm] = useState({
    dataSource: 'Social Media',
    taskType: 'Web/Network',
    activeUsers: 3312,
    processCount: 22,
    vmCpuCores: 16,
    cpuSpeedGHz: 3.5,
    vmMemoryGb: 32,
    memoryRequestedGb: 3.3,
  })
  const [prediction, setPrediction] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState('')
  const [metricsError, setMetricsError] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    let active = true
    apiRequest('/predictions/metrics')
      .then(({ metrics: modelMetrics }) => {
        if (active) setMetrics(modelMetrics)
      })
      .catch((requestError) => {
        if (active) setMetricsError(requestError.message)
      })
    return () => { active = false }
  }, [])

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }
  const estimateDemand = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setPrediction(null)
    try {
      const request = {
        ...form,
        activeUsers: Number(form.activeUsers),
        processCount: Number(form.processCount),
        vmCpuCores: Number(form.vmCpuCores),
        cpuSpeedGHz: Number(form.cpuSpeedGHz),
        vmMemoryGb: Number(form.vmMemoryGb),
        memoryRequestedGb: Number(form.memoryRequestedGb),
      }
      setPrediction(await apiRequest('/predictions', {
        method: 'POST',
        body: JSON.stringify(request),
      }))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return <>
    <div className="page-title"><div><h1>Predictions</h1><p>Estimate CPU and memory demand for one workload</p></div></div>
    {error && <p className="api-error" role="alert">{error}</p>}
    {metricsError && <p className="api-error" role="alert">{metricsError}</p>}
    {metrics && <div className="metrics-grid three">
      <Metric label="CPU validation MAE" value={`${metrics.cpu.mae} points`} detail={`R² ${metrics.cpu.r2}`} icon={Cpu} />
      <Metric label="Memory validation MAE" value={`${metrics.memory.mae} GB`} detail={`R² ${metrics.memory.r2}`} icon={Database} />
      <Metric label="Held-out validation records" value={metrics.validationRecords.toLocaleString()} detail={`${metrics.trainingRecords.toLocaleString()} training records`} icon={BarChart3} />
    </div>}
    <Panel title="Workload demand estimate" className="form-panel">
      <p className="panel-subtitle">Enter the workload and VM details for the trained estimator. These are model inputs, not values inferred from a workload name.</p>
      <form className="prediction-form" onSubmit={estimateDemand}>
        <label>Data source<select name="dataSource" value={form.dataSource} onChange={update}><option>Cloud</option><option>Enterprise DB</option><option>IoT</option><option>Social Media</option></select></label>
        <label>Task type<select name="taskType" value={form.taskType} onChange={update}><option>Cloud Service</option><option>Data Processing</option><option>Database</option><option>Web/Network</option></select></label>
        <label>Active users<input name="activeUsers" type="number" min="0" max="1000000" value={form.activeUsers} onChange={update} required /></label>
        <label>Process count<input name="processCount" type="number" min="1" max="100000" value={form.processCount} onChange={update} required /></label>
        <label>VM CPU cores<input name="vmCpuCores" type="number" min="1" max="4096" value={form.vmCpuCores} onChange={update} required /></label>
        <label>CPU speed (GHz)<input name="cpuSpeedGHz" type="number" min="0.1" max="10" step="0.1" value={form.cpuSpeedGHz} onChange={update} required /></label>
        <label>VM memory (GB)<input name="vmMemoryGb" type="number" min="0.1" max="100000" step="0.1" value={form.vmMemoryGb} onChange={update} required /></label>
        <label>Requested memory (GB)<input name="memoryRequestedGb" type="number" min="0.1" max="100000" step="0.1" value={form.memoryRequestedGb} onChange={update} required /></label>
        <button className="button primary create-button" type="submit" disabled={loading}>{loading ? 'Estimating…' : 'Estimate workload demand'}</button>
      </form>
    </Panel>
    {prediction && <Panel title="Estimated workload demand">
      <div className="metrics-grid three">
        <Metric label="Estimated CPU utilization" value={`${prediction.cpu}%`} detail="Model estimate for this workload" icon={Cpu} />
        <Metric label="Estimated memory consumption" value={`${prediction.memory} GB`} detail="Model estimate for this workload" icon={Database} />
        <Metric label="Model used" value="XGBoost" detail={`${prediction.trainingRecords.toLocaleString()} training records`} icon={Activity} />
      </div>
      {prediction.outOfTrainingRange.length > 0 && <p className="api-error">These inputs are outside the model's training range: {prediction.outOfTrainingRange.join(', ')}. Treat this estimate with extra caution.</p>}
      <p className="muted">Historical validation: CPU MAE {prediction.validationMetrics.cpuMae} percentage points; memory MAE {prediction.validationMetrics.memoryMae} GB. This is an estimate, not a live AWS measurement.</p>
    </Panel>}
  </>
}

function VmManager() {
  const [cpuNeed, setCpuNeed] = useState(1)
  const [memoryNeed, setMemoryNeed] = useState(4)
  const [sla, setSla] = useState('standard')
  const [vms, setVms] = useState([])
  const [choices, setChoices] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    apiRequest('/vms').then(({ vms: inventory }) => {
      if (active) setVms(inventory)
    }).catch((requestError) => {
      if (active) setError(requestError.message)
    })
    return () => { active = false }
  }, [])
  useEffect(() => {
    let active = true
    apiRequest('/vm-selection', {
      method: 'POST',
      body: JSON.stringify({ cpu: Number(cpuNeed), memory: Number(memoryNeed), sla }),
    }).then(({ recommendations }) => {
      if (active) {
        setChoices(recommendations)
        setError('')
      }
    }).catch((requestError) => {
      if (active) setError(requestError.message)
    })
    return () => { active = false }
  }, [cpuNeed, memoryNeed, sla])
  return <>
    <div className="page-title"><div><h1>VM Manager</h1><p>Capacity, cost, and workload fit across your cluster</p></div><button className="button ghost"><ArrowDownToLine size={14} /> Export inventory</button></div>
    {error && <p className="api-error" role="alert">{error}</p>}
    <div className="vm-grid">{vms.map((vm) => <div className="vm-card" key={vm.name}><div className="vm-card-head"><b>{vm.name}</b><span className={`status ${vm.status}`}>{vm.status}</span></div><small>{vm.type} · {vm.zone} · {vm.availableCpu}/{vm.totalCpu} vCPU · {vm.availableMemory}/{vm.totalMemory} GB free</small><div className="vm-meter-label"><span>CPU</span><b>{vm.cpu}%</b></div><div className="progress"><span style={{ width: `${vm.cpu}%` }} /></div><div className="vm-meter-label"><span>Memory</span><b>{vm.memory}%</b></div><div className="progress violet"><span style={{ width: `${vm.memory}%` }} /></div><div className="vm-bottom"><span>${vm.cost.toFixed(2)}/h</span><span>{vm.tier}</span></div></div>)}</div>
    <Panel title="Weighted selection simulator" className="table-panel"><p className="panel-subtitle">Best-fit recommendations rank available capacity, load, cost, and SLA constraints</p><div className="selection-form"><label>vCPU<input type="number" min="0.1" step="0.1" value={cpuNeed} onChange={(event) => setCpuNeed(event.target.value)} /></label><label>Requested memory (GB)<input type="number" min="0.1" step="0.1" value={memoryNeed} onChange={(event) => setMemoryNeed(event.target.value)} /></label><label>SLA<select value={sla} onChange={(event) => setSla(event.target.value)}><option>standard</option><option>premium</option><option>basic</option></select></label></div><div className="table-scroll"><table><thead><tr><th>#</th><th>VM</th><th>CPU fit</th><th>Memory fit</th><th>Cost / h</th><th>Score</th><th>Result</th></tr></thead><tbody>{choices.map((vm, index) => <tr key={vm.vm}><td>{index + 1}</td><td className="strong-cell">{vm.vm}</td><td>{vm.cpuFit}%</td><td>{vm.memoryFit}%</td><td>${vm.cost.toFixed(2)}</td><td>{vm.score.toFixed(3)}</td><td className={vm.feasible ? index === 0 ? 'good-cell' : 'muted' : 'muted'}>{!vm.feasible ? 'Insufficient capacity' : index === 0 ? 'Best fit' : 'Alternative'}</td></tr>)}</tbody></table></div></Panel>
  </>
}

function Scheduler({ workloads, onSchedule }) {
  const queue = workloads.filter((workload) => workload.status === 'Queued')
  const [scheduling, setScheduling] = useState(false)
  const [decisions, setDecisions] = useState([])
  const [error, setError] = useState('')
  const schedule = async () => {
    setScheduling(true)
    setError('')
    try {
      const result = await onSchedule()
      setDecisions(result.decisions)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setScheduling(false)
    }
  }
  return <>
    <div className="page-title"><div><h1>Scheduler</h1><p>Priority queue with weighted best-fit VM placement</p></div><button className="button primary" disabled={!queue.length || scheduling} onClick={schedule}><CalendarClock size={14} /> {scheduling ? 'Scheduling…' : `Schedule queue (${queue.length})`}</button></div>
    {error && <p className="api-error" role="alert">{error}</p>}
    <Panel title="Pending queue" className="table-panel"><div className="table-scroll"><table><thead><tr><th>Rank</th><th>Workload</th><th>Deadline</th><th>SLA</th><th>Resources</th><th>Waiting</th><th>Score</th><th>Status</th></tr></thead><tbody>{queue.length ? queue.map((item, index) => <tr key={item.name}><td>{index + 1}</td><td className="strong-cell">{item.name}</td><td>In {item.duration || 30} min</td><td>{item.sla}</td><td>{item.cpu} vCPU · {item.memory} GB</td><td>Ready</td><td>{(0.92 - index * 0.08).toFixed(2)}</td><td><span className="status queued">Queued</span></td></tr>) : <EmptyRow message="Queue is empty. Create a workload to start scheduling." columns={8} />}</tbody></table></div></Panel>
    <Panel title="Decision log">{decisions.length ? <div className="recent-list">{decisions.map((decision) => <div className="recent-item" key={decision.workloadId}><span className={`workload-dot ${decision.status === 'unscheduled' ? 'unavailable-dot' : ''}`} /><div><b>{decision.workload}</b><small>{decision.status === 'scheduled' ? `Placed on ${decision.vm} · score ${decision.score}` : decision.reason}</small></div><span className={`status ${decision.status === 'scheduled' ? 'running' : 'queued'}`}>{decision.status}</span></div>)}</div> : <p className="muted">No scheduling decisions yet.</p>}</Panel>
  </>
}

function Monitoring({ workloads }) {
  const [samples, setSamples] = useState(true)
  const [telemetry, setTelemetry] = useState(null)
  const [monitorError, setMonitorError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const refreshMonitoring = async () => {
    setRefreshing(true)
    setMonitorError('')
    try {
      setTelemetry(await apiRequest('/monitoring'))
    } catch (requestError) {
      setTelemetry(null)
      setMonitorError(requestError.message)
    } finally {
      setRefreshing(false)
    }
  }
  useEffect(() => {
    refreshMonitoring()
  }, [])
  return <>
    <div className="page-title"><div><h1>Monitoring</h1><p>Your cluster metrics and workload feedback loop</p></div><div className="title-actions"><button className="button ghost" onClick={() => setSamples(!samples)}>{samples ? 'Hide samples' : 'Sample VMs'}</button><button className="button primary" onClick={refreshMonitoring} disabled={refreshing}><RefreshCw size={14} /> {refreshing ? 'Refreshing…' : `Refresh CloudWatch (${workloads.length})`}</button></div></div>
    <Panel title="CloudWatch EC2 metrics" action={<span className={telemetry ? 'online' : 'offline'}><i />{telemetry ? `Connected · ${telemetry.region}` : 'CloudWatch unavailable'}</span>}>
      {monitorError ? <p className="muted">{monitorError}</p> : telemetry?.readings.length ? <div className="live-grid">{telemetry.readings.map((reading) => <div className="live-reading" key={reading.instanceId}><div className="reading-label">{reading.instanceId}</div><strong>{reading.cpu === null ? '--' : `${reading.cpu}%`}</strong><small className={reading.cpu === null ? 'unavailable' : ''}>{reading.cpu === null ? 'No recent datapoint' : reading.timestamp}</small></div>)}</div> : <p className="muted">Configure AWS_REGION and EC2_INSTANCE_IDS to load live CloudWatch CPU metrics.</p>}
      {telemetry && <p className="monitor-note">{telemetry.note}</p>}
    </Panel>
    <Panel title="Utilization · sample data" className="monitor-chart-panel"><p className="muted">CPU and memory utilization, updated from the current cluster sample.</p><div className="chart-wrap compact"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData.slice(-5)} margin={{ top: 8, right: 10, left: -12, bottom: 0 }}><CartesianGrid stroke="#25333e" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#8494a2', fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#8494a2', fontSize: 10 }} /><Area type="monotone" dataKey="cpu" stroke="#12d4c6" fill="#12d4c6" fillOpacity={0.12} /><Area type="monotone" dataKey="memory" stroke="#bb8cf3" fill="#bb8cf3" fillOpacity={0.1} /></AreaChart></ResponsiveContainer></div></Panel>
    {samples && <Panel title="Recent VM samples" action={<span className="source-tag">simulated</span>} className="table-panel"><div className="table-scroll"><table><thead><tr><th>Time</th><th>VM</th><th>CPU %</th><th>Memory GB</th><th>Network Mbps</th><th>Disk IOPS</th><th>Source</th></tr></thead><tbody>{initialVms.map((vm, index) => <tr key={vm.name}><td>10:3{index}:2{index} AM</td><td className="strong-cell">{vm.name}</td><td>{vm.cpu}.2</td><td>{(vm.memory / 10).toFixed(1)}</td><td>{87.5 + index * 21.4}</td><td>{124.1 + index * 20.2}</td><td>simulated</td></tr>)}</tbody></table></div></Panel>}
  </>
}

function Analytics({ workloads }) {
  return <>
    <div className="page-title"><div><h1>Analytics</h1><p>Live CPU forecast accuracy is reported on the Predictions page; this page contains demo-only charts.</p></div><button className="button ghost"><ArrowDownToLine size={14} /> Export report</button></div>
    <div className="metrics-grid three"><Metric label="Sample prediction deviation" value="—" detail="No workload actuals are connected" icon={Activity} /><Metric label="Sample SLA compliance" value="—" detail="No live SLA outcomes are connected" icon={ShieldCheck} /><Metric label="Scheduling decisions" value={workloads.filter((item) => item.status === 'Running').length} detail="This session" icon={ListChecks} /></div>
    <div className="dashboard-lower analytics-panels"><Panel title="Decision mix · illustrative"><div className="decision-bars"><div><span>CPU optimized</span><div className="progress"><span style={{ width: '68%' }} /></div><b>68%</b></div><div><span>Cost optimized</span><div className="progress violet"><span style={{ width: '22%' }} /></div><b>22%</b></div><div><span>SLA prioritized</span><div className="progress amber"><span style={{ width: '10%' }} /></div><b>10%</b></div></div></Panel><Panel title="Prediction deviation · illustrative sample data"><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}><CartesianGrid stroke="#25333e" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#8494a2', fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#8494a2', fontSize: 10 }} /><Tooltip contentStyle={{ background: '#101a23', border: '1px solid #2a3944', borderRadius: 6, color: '#e9f1f4', fontSize: 11 }} /><Line type="monotone" dataKey="cpu" name="Observed (sample)" stroke="#12d4c6" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="memory" name="Forecast (sample)" stroke="#bb8cf3" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></Panel></div>
  </>
}

function WorkbookImport({ onWorkbook }) {
  const inputRef = useRef(null)
  const [error, setError] = useState('')
  const handleFiles = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    setError('')
    try {
      const readExcelFile = await import('read-excel-file/browser')
      const parsedSheets = await readExcelFile.default(file)
      const sheets = parsedSheets.map(({ sheet, data }) => {
        const [headers = [], ...records] = data
        const columns = headers.map((value, index) => String(value || `Column ${index + 1}`))
        const rows = records.map((values) => Object.fromEntries(columns.map((column, index) => {
          const value = values[index]
          return [column, value instanceof Date ? value.toLocaleString() : value ?? '']
        })))
        return { name: sheet, rows, columns }
      })
      onWorkbook({ filename: file.name, sheets })
    } catch {
      setError('Could not read this workbook. Choose a valid .xlsx file.')
    }
    event.target.value = ''
  }
  return <>
      <button className="button ghost import-button" onClick={() => inputRef.current?.click()}><Upload size={14} /> Import workbook</button>
    <input ref={inputRef} className="visually-hidden" type="file" accept=".xlsx" onChange={handleFiles} />
    {error && <div className="import-error">{error}</div>}
  </>
}

function WorkbookDialog({ workbook, onClose }) {
  const [activeSheet, setActiveSheet] = useState(0)
  if (!workbook) return null
  const sheet = workbook.sheets[activeSheet]
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><section className="workbook-modal" role="dialog" aria-modal="true" aria-labelledby="workbook-title" onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><span className="eyebrow">Workbook imported</span><h2 id="workbook-title">{workbook.filename}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close workbook preview"><X size={18} /></button></div><div className="sheet-tabs">{workbook.sheets.map((item, index) => <button key={item.name} className={activeSheet === index ? 'active' : ''} onClick={() => setActiveSheet(index)}>{item.name}<small>{item.rows.length}</small></button>)}</div>{sheet?.rows.length ? <div className="table-scroll workbook-table"><table><thead><tr>{sheet.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{sheet.rows.slice(0, 80).map((row, rowIndex) => <tr key={rowIndex}>{sheet.columns.map((column) => <td key={column}>{String(row[column] ?? '')}</td>)}</tr>)}</tbody></table></div> : <div className="empty-workbook">This sheet has no tabular rows to preview.</div>}<div className="modal-footer"><span>{sheet?.rows.length ?? 0} rows · {sheet?.columns.length ?? 0} columns</span><button className="button primary" onClick={onClose}><Check size={14} /> Done</button></div></section></div>
}

function DataPage({ workbook }) {
  if (!workbook) return <div className="data-empty"><div className="data-icon"><Database size={22} /></div><h2>No workbook loaded</h2><p>Import your workbook to explore its sheets and records.</p><p className="muted">Supported format: .xlsx</p></div>
  return <div className="data-summary"><span className="eyebrow">Workbook loaded</span><h2>{workbook.filename}</h2><div className="metrics-grid three">{workbook.sheets.map((sheet) => <Metric key={sheet.name} label={sheet.name} value={sheet.rows.length.toLocaleString()} detail={`${sheet.columns.length} columns`} icon={Database} />)}</div></div>
}

function AuthScreen({ onAuthenticate }) {
  const [mode, setMode] = useState('signin')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isSignup = mode === 'signup'

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    if (isSignup && password !== confirmation) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await onAuthenticate({ name: name.trim(), email: email.trim(), password, mode })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="auth-shell">
    <section className="auth-brand-panel">
      <div className="brand auth-brand"><span className="brand-mark"><Activity size={17} /></span><span>Smart Cloud<small>Orchestrator</small></span></div>
      <div className="auth-intro"><span className="eyebrow">CLOUD OPERATIONS</span><h1>Capacity with a clearer view.</h1><p>Sign in to manage workloads, explore capacity, and plan your cluster.</p></div>
      <div className="auth-status"><span className="online-dot" /> Demo workspace <span>·</span> 4 sample VMs</div>
    </section>
    <section className="auth-form-panel"><div className="auth-form-wrap">
      <div className="auth-heading"><span className="eyebrow">WORKSPACE ACCESS</span><h2>{isSignup ? 'Create your account' : 'Welcome back'}</h2><p>{isSignup ? 'Set up a profile to enter the dashboard.' : 'Sign in to your Smart Cloud workspace.'}</p></div>
      <div className="auth-tabs" role="tablist" aria-label="Account access"><button role="tab" aria-selected={!isSignup} className={!isSignup ? 'active' : ''} onClick={() => { setMode('signin'); setError('') }}>Sign in</button><button role="tab" aria-selected={isSignup} className={isSignup ? 'active' : ''} onClick={() => { setMode('signup'); setError('') }}>Sign up</button></div>
      <form className="auth-form" onSubmit={submit}>
        {isSignup && <label>Full name<input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" required /></label>}
        <label>Email address<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" required /></label>
        <label>Password<input type="password" autoComplete={isSignup ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" minLength={8} required /></label>
        {isSignup && <label>Confirm password<input type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder="Re-enter your password" minLength={8} required /></label>}
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="button primary auth-submit" type="submit" disabled={submitting}>{submitting ? 'Please wait…' : isSignup ? 'Create account' : 'Sign in'} <ArrowRight size={15} /></button>
      </form>
      <p className="auth-disclaimer">Accounts are stored by the local backend. Configure a production secret and HTTPS before deployment.</p>
    </div></section>
  </main>
}

export default function App() {
  const [page, setPage] = useState('Dashboard')
  const [workloads, setWorkloads] = useState([])
  const [backendError, setBackendError] = useState('')
  const [workbook, setWorkbook] = useState(null)
  const [workbookOpen, setWorkbookOpen] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const [authUser, setAuthUser] = useState(() => {
    try {
      const token = sessionStorage.getItem('sco-demo-token')
      return token ? JSON.parse(sessionStorage.getItem('sco-demo-session')) : null
    } catch {
      return null
    }
  })
  useEffect(() => {
    if (!authUser) {
      setWorkloads([])
      return undefined
    }
    let active = true
    apiRequest('/workloads').then(({ workloads: currentWorkloads }) => {
      if (active) {
        setWorkloads(currentWorkloads)
        setBackendError('')
      }
    }).catch((error) => {
      if (active) {
        setBackendError(error.message)
        if (error.status === 401) {
          sessionStorage.removeItem('sco-demo-token')
          sessionStorage.removeItem('sco-demo-session')
          setAuthUser(null)
        }
      }
    })
    return () => { active = false }
  }, [authUser])
  const createWorkload = async (workload) => {
    try {
      const { workload: created } = await apiRequest('/workloads', { method: 'POST', body: JSON.stringify(workload) })
      setWorkloads((current) => [created, ...current])
      setBackendError('')
    } catch (error) {
      setBackendError(error.message)
      throw error
    }
  }
  const scheduleQueue = async () => {
    try {
      const result = await apiRequest('/schedule', { method: 'POST' })
      setWorkloads(result.workloads)
      setBackendError('')
      return result
    } catch (error) {
      setBackendError(error.message)
      throw error
    }
  }
  const authenticate = async (profile) => {
    const endpoint = profile.mode === 'signup' ? '/auth/register' : '/auth/login'
    const credentials = profile.mode === 'signup'
      ? { name: profile.name, email: profile.email, password: profile.password }
      : { email: profile.email, password: profile.password }
    const result = await apiRequest(endpoint, { method: 'POST', body: JSON.stringify(credentials) })
    sessionStorage.setItem('sco-demo-token', result.token)
    sessionStorage.setItem('sco-demo-session', JSON.stringify(result.user))
    setAuthUser(result.user)
  }
  const signOut = () => {
    sessionStorage.removeItem('sco-demo-token')
    sessionStorage.removeItem('sco-demo-session')
    setAuthUser(null)
  }
  const viewMap = {
    Dashboard: <Dashboard workloads={workloads} setPage={setPage} />,
    Workloads: <Workloads workloads={workloads} onCreateWorkload={createWorkload} />,
    Predictions: <Predictions />,
    'VM Manager': <VmManager />,
    Scheduler: <Scheduler workloads={workloads} onSchedule={scheduleQueue} />,
    Monitoring: <Monitoring workloads={workloads} />,
    Analytics: <Analytics workloads={workloads} />,
    Dataset: <DataPage workbook={workbook} />,
  }
  if (!authUser) return <AuthScreen onAuthenticate={authenticate} />
  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}><div className="brand"><span className="brand-mark"><Activity size={17} /></span><span>Smart Cloud<small>Orchestrator</small></span><button className="mobile-close" onClick={() => setMobileMenu(false)} aria-label="Close navigation"><X size={16} /></button></div><div className="workspace-label">WORKSPACE</div><nav>{navigation.map(({ name, icon: Icon }) => <button key={name} className={`nav-item ${page === name ? 'selected' : ''}`} onClick={() => { setPage(name); setMobileMenu(false) }}><Icon size={15} /><span>{name}</span>{name === 'Workloads' && workloads.length > 0 && <small>{workloads.length}</small>}</button>)}</nav><div className="sidebar-bottom"><div className="cluster-status"><span className="online-dot" /><div><b>Demo cluster</b><small>Sample telemetry</small></div><ChevronDown size={13} /></div><button className={`nav-item ${page === 'Dataset' ? 'selected' : ''}`} onClick={() => setPage('Dataset')}><Database size={15} /><span>Dataset</span></button><div className="user-row"><div className="avatar">{authUser.name.slice(0, 2).toUpperCase()}</div><div><b>{authUser.name}</b><small>{authUser.email}</small></div><button className="signout-button" onClick={signOut} title="Sign out" aria-label="Sign out"><LogOut size={15} /></button></div></div></aside>
    {mobileMenu && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileMenu(false)} />}
    <main className="main-content"><header className="topbar"><button className="mobile-menu" onClick={() => setMobileMenu(true)} aria-label="Open navigation"><Menu size={19} /></button><div className="breadcrumbs">Cloud platform <span>/</span> <b>{page}</b></div><div className="topbar-actions"><span className="region-select"><span className="online-dot" /> US East <ChevronDown size={12} /></span><WorkbookImport onWorkbook={(data) => { setWorkbook(data); setWorkbookOpen(true) }} /><div className="top-avatar">SC</div></div></header>
      {workbook && <button className="loaded-workbook" onClick={() => setWorkbookOpen(true)}><Database size={13} /> {workbook.filename}<span>{workbook.sheets.length} sheets</span></button>}
      <div className="page-content">{backendError && <p className="api-error" role="alert">Backend unavailable: {backendError}</p>}{viewMap[page]}</div><footer className="app-footer"><span>Smart Cloud Orchestrator</span><span>Demo telemetry · Sample workload and chart data</span></footer>
    </main>
    <WorkbookDialog workbook={workbookOpen ? workbook : null} onClose={() => setWorkbookOpen(false)} />
  </div>
}
