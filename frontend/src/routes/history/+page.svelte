<script>
	// @ts-nocheck
	import { onMount } from 'svelte';
	import { History, CheckCircle, XCircle, Clock, Dumbbell } from 'lucide-svelte';

	let sessions = $state([]);
	let isLoading = $state(true);
	let errorMsg  = $state(null);

	const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

	const loadHistory = async () => {
		isLoading = true;
		errorMsg  = null;
		try {
			const res  = await fetch(`${API_BASE}/sessions/history?limit=50`);
			const data = await res.json();
			sessions   = data.sessions ?? [];
		} catch {
			errorMsg = 'Tidak dapat menghubungi server atau database.';
		} finally {
			isLoading = false;
		}
	};

	const formatDate = (iso) => {
		const d = new Date(iso);
		return d.toLocaleDateString('id-ID', { day:'2-digit', month:'short', year:'numeric' })
			+ ' · '
			+ d.toLocaleTimeString('id-ID', { hour:'2-digit', minute:'2-digit' });
	};

	const formatDuration = (sec) => {
		const m = Math.floor(sec / 60);
		const s = Math.round(sec % 60);
		return m > 0 ? `${m}m ${s}s` : `${s}s`;
	};

	onMount(loadHistory);
</script>

<svelte:head>
	<title>Session History | PushupPro</title>
</svelte:head>

<div class="container page-container animate-fade-in">
	<div class="header">
		<h1><History size={28} style="display:inline;vertical-align:middle;margin-right:8px;" />Session History</h1>
		<p>Riwayat sesi pushup yang pernah kamu lakukan.</p>
	</div>

	{#if isLoading}
		<div class="empty-state glass-panel">
			<span class="spinner"></span>
			<p>Memuat data...</p>
		</div>
	{:else if errorMsg}
		<div class="empty-state glass-panel text-danger">{errorMsg}</div>
	{:else if sessions.length === 0}
		<div class="empty-state glass-panel">
			<Dumbbell size={48} style="opacity:0.4;margin-bottom:1rem;" />
			<p>Belum ada sesi tersimpan. Mulai tracking dan selesaikan sesimu!</p>
		</div>
	{:else}
		<div class="sessions-list">
			{#each sessions as s, i}
				<div class="session-card glass-panel animate-fade-in" style="animation-delay:{i * 0.04}s">
					<div class="session-meta">
						<span class="session-date">
							<Clock size={14} style="display:inline;vertical-align:middle;margin-right:4px;" />
							{formatDate(s.start_time)}
						</span>
						<span class="session-duration">{formatDuration(s.duration_sec)}</span>
					</div>

					<div class="session-stats">
						<div class="stat-block total">
							<span class="stat-value">{s.total_reps}</span>
							<span class="stat-label">Total Reps</span>
						</div>
						<div class="stat-block correct">
							<CheckCircle size={20} />
							<span class="stat-value">{s.correct_reps}</span>
							<span class="stat-label">Correct</span>
						</div>
						<div class="stat-block incorrect">
							<XCircle size={20} />
							<span class="stat-value">{s.incorrect_reps}</span>
							<span class="stat-label">Incorrect</span>
						</div>
					</div>

					{#if s.total_reps > 0}
						<div class="accuracy-bar-wrap">
							<div class="accuracy-bar">
								<div
									class="accuracy-fill"
									style="width:{Math.round(s.correct_reps / s.total_reps * 100)}%"
								></div>
							</div>
							<span class="accuracy-pct">
								{Math.round(s.correct_reps / s.total_reps * 100)}% correct
							</span>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.page-container { padding: 2rem; }

	.header { margin-bottom: 2rem; text-align: center; }

	.empty-state {
		padding: 4rem 2rem;
		text-align: center;
		display: flex; flex-direction: column;
		align-items: center; gap: 1rem;
		border-radius: var(--radius-md);
	}

	.sessions-list {
		display: flex; flex-direction: column; gap: 1.25rem;
	}

	.session-card {
		padding: 1.5rem;
		border-radius: var(--radius-md);
		display: flex; flex-direction: column; gap: 1rem;
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}
	.session-card:hover {
		transform: translateY(-2px);
		box-shadow: var(--shadow-glow);
	}

	.session-meta {
		display: flex; justify-content: space-between; align-items: center;
		font-size: 0.85rem; color: var(--text-muted);
	}

	.session-duration {
		background: rgba(255,255,255,0.06);
		padding: 0.25rem 0.75rem;
		border-radius: var(--radius-full);
		font-size: 0.8rem;
	}

	.session-stats {
		display: flex; gap: 1rem;
	}

	.stat-block {
		flex: 1;
		display: flex; flex-direction: column; align-items: center;
		padding: 1rem; border-radius: var(--radius-sm);
		gap: 0.25rem; text-align: center;
	}
	.stat-block.total    { background: rgba(255,255,255,0.05); border: 1px solid var(--surface-border); }
	.stat-block.correct  { background: rgba(16,185,129,0.1);  border: 1px solid rgba(16,185,129,0.25); color: var(--success); }
	.stat-block.incorrect{ background: rgba(239,68,68,0.1);   border: 1px solid rgba(239,68,68,0.25);  color: var(--danger); }

	.stat-value { font-size: 1.75rem; font-weight: 700; line-height: 1; }
	.stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; }

	.accuracy-bar-wrap {
		display: flex; align-items: center; gap: 1rem;
	}
	.accuracy-bar {
		flex: 1; height: 8px;
		background: rgba(239,68,68,0.3);
		border-radius: 4px; overflow: hidden;
	}
	.accuracy-fill {
		height: 100%; background: var(--success);
		border-radius: 4px; transition: width 0.6s ease;
	}
	.accuracy-pct { font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; }

	/* Spinner */
	.spinner {
		width: 2rem; height: 2rem;
		border: 3px solid rgba(255,255,255,0.1);
		border-radius: 50%; border-top-color: var(--primary);
		animation: spin 1s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
	
	@media (max-width: 768px) {
		.page-container { padding: 1rem 0; }
		.session-card { padding: 1rem; }
		.session-meta { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
	}
	
	@media (max-width: 500px) {
		.session-stats {
			flex-wrap: wrap;
		}
		.stat-block {
			min-width: 45%;
		}
	}
</style>
