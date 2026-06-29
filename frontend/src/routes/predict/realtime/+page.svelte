<script>
	// @ts-nocheck
	import { onDestroy } from 'svelte';
	import { Video, Square, Play, RefreshCw, Lightbulb, AlertTriangle, Save } from 'lucide-svelte';

	let videoElement = $state();
	let captureCanvas = $state();
	let overlayCanvas = $state();
	let ws = null;
	let sessionId = null;

	let isTracking = $state(false);
	let isSaving   = $state(false);
	let saveMsg    = $state(null);
	let stream     = null;
	let captureInterval = null;
	let startTime  = null;

	const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
	const WS_BASE  = API_BASE.replace(/^http/, 'ws');

	let state = $state({
		pose_detected:   false,
		label:           'unknown',
		confidence:      0,
		rep_count:       0,
		correct_count:   0,
		incorrect_count: 0,
		last_rep_label:  null,
		pushup_state:    'idle',
		avg_elbow_angle: 0,
		message:         'Waiting to start...',
		alignment:       null,
	});

	// ── Camera ────────────────────────────────────────────────────────────────
	const startCamera = async () => {
		stream = await navigator.mediaDevices.getUserMedia({
			video: { width: 640, height: 480, facingMode: 'user' }
		});
		videoElement.srcObject = stream;
		videoElement.play();
	};

	const stopCamera = () => {
		stream?.getTracks().forEach(t => t.stop());
		if (captureInterval) clearInterval(captureInterval);
	};

	// ── WebSocket ─────────────────────────────────────────────────────────────
	const initWebSocket = async () => {
		const res  = await fetch(`${API_BASE}/session/new`);
		const data = await res.json();
		sessionId  = data.session_id;

		ws = new WebSocket(`${WS_BASE}/ws/realtime/${sessionId}`);

		ws.onmessage = (event) => {
			const response = JSON.parse(event.data);
			if (!response.error) {
				state = { ...state, ...response };
				if (state.landmarks) drawLandmarks(state.landmarks);
				else clearOverlay();
			}
		};

		ws.onerror  = () => { state.message = 'Connection error.'; isTracking = false; };
		ws.onclose  = () => { isTracking = false; };
	};

	const sendFrame = () => {
		if (!ws || ws.readyState !== WebSocket.OPEN || !isTracking) return;
		const ctx = captureCanvas.getContext('2d');
		ctx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
		ws.send(JSON.stringify({ action: 'frame', frame: captureCanvas.toDataURL('image/jpeg', 0.5) }));
	};

	// ── Tracking toggle ───────────────────────────────────────────────────────
	const toggleTracking = async () => {
		if (isTracking) {
			isTracking = false;
			clearInterval(captureInterval);
			stopCamera();
			if (ws) ws.close();
			state.message = 'Tracking stopped.';
			clearOverlay();
			await saveSession();
		} else {
			saveMsg = null;
			state.message = 'Initializing camera...';
			await startCamera();
			await initWebSocket();
			startTime = new Date().toISOString();
			setTimeout(() => {
				if (ws.readyState === WebSocket.OPEN) {
					isTracking = true;
					state.message = 'Tracking active...';
					captureInterval = setInterval(sendFrame, 1000 / 15);
				}
			}, 1000);
		}
	};

	const resetCounter = () => {
		if (ws && ws.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify({ action: 'reset' }));
		}
	};

	// ── Save session ──────────────────────────────────────────────────────────
	const saveSession = async () => {
		if (!startTime || state.rep_count === 0) return;
		isSaving = true;
		try {
			const res = await fetch(`${API_BASE}/session/save`, {
				method:  'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					start_time:     startTime,
					end_time:       new Date().toISOString(),
					total_reps:     state.rep_count,
					correct_reps:   state.correct_count,
					incorrect_reps: state.incorrect_count,
				}),
			});
			if (res.ok) {
				saveMsg = { type: 'success', text: `Sesi tersimpan — ${state.rep_count} rep(s)` };
			} else {
				saveMsg = { type: 'error', text: 'Gagal menyimpan sesi ke database.' };
			}
		} catch {
			saveMsg = { type: 'error', text: 'Database tidak terhubung.' };
		} finally {
			isSaving = false;
		}
	};

	// ── Landmark drawing ──────────────────────────────────────────────────────
	const clearOverlay = () => {
		if (!overlayCanvas) return;
		overlayCanvas.getContext('2d').clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
	};

	const drawLandmarks = (landmarks) => {
		if (!overlayCanvas) return;
		const ctx = overlayCanvas.getContext('2d');
		const w = overlayCanvas.width;
		const h = overlayCanvas.height;
		ctx.clearRect(0, 0, w, h);

		const color = state.last_rep_label === 'correct'
			? '#10b981'
			: state.last_rep_label === 'wrong'
			? '#ef4444'
			: '#3b82f6';

		const connections = [
			[11,12],[11,13],[13,15],[12,14],[14,16],
			[11,23],[12,24],[23,24],
			[23,25],[25,27],[24,26],[26,28]
		];

		ctx.lineWidth   = 3;
		ctx.strokeStyle = color;
		ctx.lineCap     = 'round';

		connections.forEach(([a, b]) => {
			const p1 = landmarks[a], p2 = landmarks[b];
			if (!p1 || !p2) return;
			ctx.beginPath();
			ctx.moveTo(p1.x * w, p1.y * h);
			ctx.lineTo(p2.x * w, p2.y * h);
			ctx.stroke();
		});

		ctx.fillStyle = '#ffffff';
		landmarks.forEach(lm => {
			ctx.beginPath();
			ctx.arc(lm.x * w, lm.y * h, 4, 0, 2 * Math.PI);
			ctx.fill();
			ctx.strokeStyle = color;
			ctx.lineWidth   = 1.5;
			ctx.stroke();
		});
	};

	onDestroy(() => {
		stopCamera();
		ws?.close();
	});
</script>

<svelte:head>
	<title>Real-time Tracker | PushupPro</title>
</svelte:head>

<div class="container page-container animate-fade-in">
	<div class="header">
		<h1>Real-time Tracker</h1>
		<p>Position your camera so your full body is visible for accurate tracking and rep counting.</p>
	</div>

	<div class="grid layout-grid">
		<!-- Left: Camera Feed -->
		<div class="video-section glass-panel">
			<div class="video-container" class:active={isTracking}>
				<!-- svelte-ignore a11y_media_has_caption -->
				<video bind:this={videoElement} autoplay playsinline muted></video>
				<canvas bind:this={overlayCanvas} width="640" height="480" class="overlay-canvas"></canvas>
				<canvas bind:this={captureCanvas} width="640" height="480" style="display:none;"></canvas>

				{#if !isTracking}
					<div class="video-overlay">
						<span class="icon-large opacity-50"><Video size={48} /></span>
						<p>Camera is off</p>
					</div>
				{/if}
			</div>

			<div class="action-bar">
				<button
					class="btn {isTracking ? 'btn-danger' : 'btn-primary'} flex-1"
					onclick={toggleTracking}
					disabled={isSaving}
				>
					<span class="icon">
						{#if isTracking}
							<Square size={20} style="display:inline;vertical-align:middle;margin-right:4px;" />
						{:else}
							<Play size={20} style="display:inline;vertical-align:middle;margin-right:4px;" />
						{/if}
					</span>
					{isTracking ? 'Stop & Save' : 'Start Tracking'}
				</button>

				<button class="btn btn-secondary" onclick={resetCounter} disabled={!isTracking}>
					<RefreshCw size={20} style="display:inline;vertical-align:middle;margin-right:4px;" /> Reset
				</button>

				<a href="/history" class="btn btn-secondary">History</a>
			</div>

			{#if isSaving}
				<div class="save-banner saving">
					<Save size={16} /> Menyimpan sesi...
				</div>
			{:else if saveMsg}
				<div class="save-banner {saveMsg.type}">
					{saveMsg.text}
				</div>
			{/if}
		</div>

		<!-- Right: Live Dashboard -->
		<div class="dashboard-section glass-panel">
			<div class="status-banner {state.last_rep_label === 'correct' ? 'bg-success-soft text-success' : state.last_rep_label === 'wrong' ? 'bg-danger-soft text-danger' : 'bg-secondary-soft text-muted'}">
				{#if !state.pose_detected}
					<span style="display:flex;align-items:center;gap:8px;"><AlertTriangle size={24} /> {state.message}</span>
				{:else}
					<span>{(state.last_rep_label ?? 'TRACKING').toUpperCase()} FORM</span>
					<span class="confidence">{(state.confidence * 100).toFixed(0)}%</span>
				{/if}
			</div>

			<!-- Rep counter -->
			<div class="rep-counter">
				<span class="counter-label">Repetitions</span>
				<div class="counter-value">{state.rep_count}</div>
				<div class="state-badge">
					<span class="dot {state.pushup_state === 'down' ? 'active' : ''}"></span>
					{state.pushup_state.toUpperCase()}
				</div>
			</div>

			<!-- Correct / Incorrect breakdown -->
			<div class="rep-breakdown">
				<div class="breakdown-box correct">
					<span class="breakdown-count">{state.correct_count}</span>
					<span class="breakdown-label">Correct</span>
				</div>
				<div class="breakdown-box incorrect">
					<span class="breakdown-count">{state.incorrect_count}</span>
					<span class="breakdown-label">Incorrect</span>
				</div>
			</div>

			{#if state.message && state.pose_detected}
				<div class="feedback-card {state.last_rep_label === 'correct' ? 'text-success' : 'text-danger'}">
					<span class="icon"><Lightbulb size={20} /></span> {state.message}
				</div>
			{/if}

			<div class="metrics-grid">
				<div class="metric-box">
					<span class="metric-label">Elbow Angle</span>
					<span class="metric-value">{state.avg_elbow_angle ? Math.round(state.avg_elbow_angle) + '°' : '--'}</span>
					<div class="progress-bar">
						<div class="progress-fill" style="width: {state.avg_elbow_angle ? Math.min(100, Math.max(0, (state.avg_elbow_angle - 60) / 120 * 100)) : 0}%"></div>
					</div>
				</div>
				<div class="metric-box">
					<span class="metric-label">Back Alignment</span>
					<span class="metric-value">{state.alignment ? Math.round(state.alignment.back_angle) + '°' : '--'}</span>
					<span class="metric-sub {state.alignment && state.alignment.back_angle < 150 ? 'text-danger' : 'text-success'}">
						{state.alignment ? (state.alignment.back_angle >= 150 ? 'Straight' : 'Curved') : 'N/A'}
					</span>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.page-container { padding: 2rem; }
	.header { margin-bottom: 2rem; text-align: center; }

	.layout-grid {
		grid-template-columns: 3fr 2fr;
		align-items: stretch;
	}
	@media (max-width: 992px) {
		.layout-grid { grid-template-columns: 1fr; }
	}

	.video-section, .dashboard-section {
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		min-height: 620px;
	}

	@media (max-width: 768px) {
		.page-container { padding: 1rem 0; }
		.video-section, .dashboard-section {
			padding: 1rem;
			min-height: auto;
		}
	}

	.video-container {
		width: 100%;
		aspect-ratio: 4/3;
		background: #000;
		border-radius: var(--radius-md);
		overflow: hidden;
		position: relative;
		border: 2px solid var(--surface-border);
		transition: border-color 0.3s ease;
	}
	.video-container.active {
		border-color: var(--primary);
		box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
	}
	video {
		width: 100%; height: 100%;
		object-fit: cover;
		transform: scaleX(-1);
	}
	.overlay-canvas {
		position: absolute; top: 0; left: 0;
		width: 100%; height: 100%;
		pointer-events: none;
		transform: scaleX(-1);
	}
	.video-overlay {
		position: absolute; inset: 0;
		background: rgba(0,0,0,0.7);
		display: flex; flex-direction: column;
		align-items: center; justify-content: center;
		color: var(--text-muted);
	}

	.action-bar { display: flex; gap: 1rem; flex-wrap: wrap; }
	.flex-1 { flex: 1; min-width: 200px; }
	
	@media (max-width: 500px) {
		.action-bar { flex-direction: column; }
		.action-bar .btn { width: 100%; }
	}

	.btn-danger { background: var(--danger); color: white; }
	.btn-danger:hover { background: #dc2626; transform: translateY(-2px); }

	/* Save banner */
	.save-banner {
		padding: 0.75rem 1rem;
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-weight: 500;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.save-banner.saving  { background: rgba(59,130,246,0.15); color: var(--primary); }
	.save-banner.success { background: rgba(16,185,129,0.15); color: var(--success); }
	.save-banner.error   { background: rgba(239,68,68,0.15);  color: var(--danger);  }

	/* Dashboard */
	.status-banner {
		padding: 1rem 1.5rem;
		border-radius: var(--radius-md);
		display: flex; justify-content: space-between; align-items: center;
		font-weight: 700; font-size: 1.25rem;
	}
	.bg-secondary-soft { background: rgba(255,255,255,0.05); }

	.rep-counter {
		display: flex; flex-direction: column;
		align-items: center; justify-content: center;
		padding: 2rem 0;
	}
	.counter-label {
		text-transform: uppercase; letter-spacing: 2px;
		color: var(--text-muted); font-size: 0.875rem; font-weight: 600;
	}
	.counter-value {
		font-size: 7rem; font-weight: 700; line-height: 1;
		background: linear-gradient(135deg, #fff, #94a3b8);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}
	.state-badge {
		margin-top: 0.75rem;
		display: inline-flex; align-items: center; gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: rgba(0,0,0,0.3);
		border-radius: var(--radius-full);
		font-size: 0.875rem; color: var(--text-muted);
		border: 1px solid var(--surface-border);
	}
	.dot {
		width: 8px; height: 8px; border-radius: 50%;
		background: var(--text-muted); transition: background 0.3s;
	}
	.dot.active { background: var(--primary); box-shadow: 0 0 10px var(--primary); }

	/* Correct / Incorrect breakdown */
	.rep-breakdown {
		display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
	}
	.breakdown-box {
		padding: 1rem; border-radius: var(--radius-md);
		text-align: center; display: flex; flex-direction: column; gap: 0.25rem;
	}
	.breakdown-box.correct   { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25); }
	.breakdown-box.incorrect { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.25); }
	.breakdown-count {
		font-size: 2.5rem; font-weight: 700; line-height: 1;
	}
	.breakdown-box.correct   .breakdown-count { color: var(--success); }
	.breakdown-box.incorrect .breakdown-count { color: var(--danger); }
	.breakdown-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); }

	.feedback-card {
		padding: 1rem;
		background: rgba(0,0,0,0.2);
		border-left: 4px solid currentColor;
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
		display: flex; align-items: center; gap: 0.75rem; font-weight: 500;
	}

	.metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
	.metric-box {
		background: rgba(0,0,0,0.2); padding: 1.25rem;
		border-radius: var(--radius-md); border: 1px solid var(--surface-border);
		display: flex; flex-direction: column; gap: 0.5rem;
	}
	.progress-bar {
		width: 100%; height: 6px;
		background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; margin-top: 0.5rem;
	}
	.progress-fill { height: 100%; background: var(--primary); transition: width 0.1s linear; }

	.icon-large { font-size: 3rem; margin-bottom: 1rem; }
	.opacity-50 { opacity: 0.5; }
	@media (max-width: 500px) {
		.rep-breakdown, .metrics-grid {
			grid-template-columns: 1fr;
		}
		
		.counter-value {
			font-size: 5rem;
		}
		
		.status-banner {
			font-size: 1rem;
			padding: 0.75rem 1rem;
		}
	}
</style>
